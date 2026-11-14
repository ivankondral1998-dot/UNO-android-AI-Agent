package org.unovyra.uno.core

import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/** Original roadmap WP-06-T01. Only a host reference, not Android authority or F. */
enum class FoundationReferenceStatus {
    INVALID_EVENT, BUSY, STOPPED, MEMORY_UNAVAILABLE, MODEL_UNAVAILABLE,
    NO_PROPOSAL, OWNER_DECLINED, TRUST_REJECTED, DISPATCH_REJECTED,
    MAY_HAVE_EXECUTED, READBACK_UNCONFIRMED, REFERENCE_READBACK_CLAIM,
    AUDIO_REJECTED, IMAGE_REJECTED, PLAN_REJECTED
}
data class FoundationReferenceResult(
    val status: FoundationReferenceStatus,
    val revision: Long,
    val memoryGeneration: Long,
    val observedSha256: String?,
    val untrustedModelState: String? = null,
    val proposalDigest: String? = null,
    val nativeCalledInReference: Boolean = false,
    val verifiedAndroidEffect: Boolean = false,
    val observedEventKey: String? = null
)

/**
 * One typed event -> shared in-memory exact observation -> one NeuralPort ->
 * untrusted proposal -> explicit owner check -> TrustController -> typed readback.
 * Fake JVM readback is NEVER trusted Android evidence or VERIFIED_COMPLETION memory.
 * Android still uses DenyAllAndroidPort; no authority or model is installed here.
 */
class UnoFoundationReferenceCycle(
    private val neural: NeuralPort,
    private val memory: UnoExactMemoryPort,
    private val controller: TrustController,
    private val owner: AuthenticatedOwnerUi,
    private val scheduler: BoundedScheduler = BoundedScheduler(32),
    private val audio: PcmFrameGate? = null,
    private val planner: BoundedPlanner = BoundedPlanner(),
    // Host reference may omit this; any real Android caller must inject elapsedRealtimeNanos.
    private val trustedClockNanos: (() -> Long)? = null
) {
    private val stopped = AtomicBoolean(false)
    private val busy = AtomicBoolean(false)
    private var revision = 0L
    fun stop() { stopped.set(true); scheduler.stop(); controller.stop(); planner.stop() }
    fun isStopped() = stopped.get()

    private fun freshNow(callerNow: Long): Long? = try {
        val actual = trustedClockNanos?.invoke() ?: callerNow
        actual.takeIf { it >= callerNow && it >= 0L }
    } catch (_: Exception) { null }

    @Synchronized private fun report(
        status: FoundationReferenceStatus, sha: String? = null, state: String? = null,
        proposal: String? = null, called: Boolean = false,
        eventKey: String? = null
    ) = FoundationReferenceResult(
        status, revision, memory.generation, sha, state, proposal, called,
        verifiedAndroidEffect = false, observedEventKey = eventKey
    )

    fun accept(event: Percept, now: Long, deadline: Long, scope: String, consentEpoch: Long):
        FoundationReferenceResult {
        if (stopped.get()) return report(FoundationReferenceStatus.STOPPED)
        if (!busy.compareAndSet(false, true)) return report(FoundationReferenceStatus.BUSY)
        try {
            if (scope.isBlank() || event.sourceTag.isBlank() || event.data.isEmpty() ||
                event.data.size > 4096 || now < event.monotonicNanos || deadline <= now ||
                consentEpoch < 0) return report(FoundationReferenceStatus.INVALID_EVENT)
            if (event.type == PerceptType.AUDIO) {
                val gate = audio
                if (gate == null || gate.accept(event.data, true) != PcmStatus.ACCEPTED_FRAME) {
                    return report(FoundationReferenceStatus.AUDIO_REJECTED)
                }
            }
            if (event.type == PerceptType.IMAGE) {
                return report(FoundationReferenceStatus.IMAGE_REJECTED)
            }
            val observation: Percept
            var committedEventKey: String? = null
            synchronized(this) {
                if (stopped.get()) return report(FoundationReferenceStatus.STOPPED)
                observation = event.copy(data = event.data.copyOf())
                // Use persisted generation, not activity-local revision; no key reuse
                // after recreation or within a shared vault across event sources.
                val priority = if (event.type == PerceptType.SENSOR) Priority.SENSOR
                               else Priority.INTERNAL
                // Lock the shared port over generation allocation and the actual
                // committed write. Independent cycle instances cannot reuse an
                // event key merely because their local revisions both start at zero.
                synchronized(memory) {
                    if (event.monotonicNanos <= memory.causalFloor())
                        return report(FoundationReferenceStatus.INVALID_EVENT)
                    val next = memory.generation
                    if (next == Long.MAX_VALUE)
                        return report(FoundationReferenceStatus.MEMORY_UNAVAILABLE)
                    val key = "event:" + (next + 1L)
                    if (!scheduler.enqueue(priority, key, deadline))
                        return report(if (stopped.get()) FoundationReferenceStatus.STOPPED
                            else FoundationReferenceStatus.INVALID_EVENT)
                    if (scheduler.poll(now)?.payload != key)
                        return report(FoundationReferenceStatus.STOPPED)
                    try {
                        if (stopped.get()) return report(FoundationReferenceStatus.STOPPED)
                        val entry = memory.write(scope, key, observation.data, deadline,
                            consentEpoch, EntryKind.OBSERVED, event.sourceTag)
                        check(entry.factKey == key) { "EXACT_COMMIT_KEY_MISMATCH" }
                        memory.noteCausalFloor(event.monotonicNanos)
                        committedEventKey = entry.factKey
                    } catch (_: Exception) {
                        return report(FoundationReferenceStatus.MEMORY_UNAVAILABLE)
                    }
                }
                revision++
            }
            val sha = MessageDigest.getInstance("SHA-256").digest(observation.data)
                .joinToString("") { "%02x".format(it) }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            val output = try { neural.perceive(observation.copy(data = observation.data.copyOf())) }
                         catch (_: Exception) {
                             return report(FoundationReferenceStatus.MODEL_UNAVAILABLE, sha,
                                 eventKey = committedEventKey)
                         }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            if (output.stateDigest.isBlank())
                return report(FoundationReferenceStatus.MODEL_UNAVAILABLE, sha,
                    eventKey = committedEventKey)
            val proposal = output.action ?: return report(
                FoundationReferenceStatus.NO_PROPOSAL, sha, output.stateDigest,
                eventKey = committedEventKey)
            val opened = planner.bound(proposal)
            if (opened.status == PlanStatus.STOPPED) {
                return report(FoundationReferenceStatus.STOPPED, sha, output.stateDigest,
                    eventKey = committedEventKey)
            }
            if (opened.status != PlanStatus.HELD) {
                return report(FoundationReferenceStatus.PLAN_REJECTED, sha, output.stateDigest,
                    eventKey = committedEventKey)
            }
            val plan = planner.take()
            if (plan.status == PlanStatus.STOPPED) {
                return report(FoundationReferenceStatus.STOPPED, sha, output.stateDigest,
                    eventKey = committedEventKey)
            }
            val step = plan.steps.singleOrNull()
            if (plan.status != PlanStatus.HELD || step == null || step.reversible ||
                step.verb != proposal.verb ||
                !step.canonicalArgs.contentEquals(proposal.canonicalArgs)) {
                return report(FoundationReferenceStatus.PLAN_REJECTED, sha, output.stateDigest,
                    eventKey = committedEventKey)
            }
            val digest = controller.proposalDigest(proposal)
            val consent = try { owner.showExactProposalAndObtainConsent(proposal) }
                          catch (_: Exception) { null }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            if (consent == null) return report(
                FoundationReferenceStatus.OWNER_DECLINED, sha, output.stateDigest, digest)
            // Owner UI can block for seconds or minutes. Never authorize with the pre-UI event time.
            val approvalNow = freshNow(now) ?: return report(
                FoundationReferenceStatus.TRUST_REJECTED, sha, output.stateDigest, digest)
            val ticket = controller.prepare(proposal, consent, approvalNow, deadline) ?: return report(
                FoundationReferenceStatus.TRUST_REJECTED, sha, output.stateDigest, digest)
            if (stopped.get()) {
                controller.stop()
                return report(FoundationReferenceStatus.STOPPED, sha)
            }
            val dispatchNow = freshNow(approvalNow) ?: return report(
                FoundationReferenceStatus.DISPATCH_REJECTED, sha, output.stateDigest, digest)
            return when (val attempt = controller.dispatchOutcome(ticket, dispatchNow)) {
                is DispatchAttempt.Rejected -> report(
                    FoundationReferenceStatus.DISPATCH_REJECTED, sha, output.stateDigest, digest)
                DispatchAttempt.Unresolved -> report(
                    FoundationReferenceStatus.MAY_HAVE_EXECUTED, sha, output.stateDigest, digest)
                is DispatchAttempt.Invoked -> when {
                    stopped.get() || attempt.nativeReturn == NativeEndpoint.UNKNOWN ->
                        report(FoundationReferenceStatus.MAY_HAVE_EXECUTED, sha,
                            output.stateDigest, digest, true)
                    freshNow(dispatchNow)?.let { controller.readbackAndCommit(ticket, it) } == true ->
                        report(FoundationReferenceStatus.REFERENCE_READBACK_CLAIM, sha,
                            output.stateDigest, digest, true)
                    else -> report(FoundationReferenceStatus.READBACK_UNCONFIRMED, sha,
                        output.stateDigest, digest, true)
                }
            }
        } finally { busy.set(false) }
    }
}
