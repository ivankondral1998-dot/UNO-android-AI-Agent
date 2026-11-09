package org.unovyra.uno.core

import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean

/** Original roadmap WP-06-T01. Only a host reference, not Android authority or F. */
enum class FoundationReferenceStatus {
    INVALID_EVENT, BUSY, STOPPED, MEMORY_UNAVAILABLE, MODEL_UNAVAILABLE,
    NO_PROPOSAL, OWNER_DECLINED, TRUST_REJECTED, DISPATCH_REJECTED,
    MAY_HAVE_EXECUTED, READBACK_UNCONFIRMED, REFERENCE_READBACK_CLAIM
}
data class FoundationReferenceResult(
    val status: FoundationReferenceStatus,
    val revision: Long,
    val memoryGeneration: Long,
    val observedSha256: String?,
    val untrustedModelState: String? = null,
    val proposalDigest: String? = null,
    val nativeCalledInReference: Boolean = false,
    val verifiedAndroidEffect: Boolean = false
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
    private val scheduler: BoundedScheduler = BoundedScheduler(32)
) {
    private val stopped = AtomicBoolean(false)
    private val busy = AtomicBoolean(false)
    private var revision = 0L
    private var lastEventNanos = -1L
    fun stop() { stopped.set(true); scheduler.stop(); controller.stop() }
    fun isStopped() = stopped.get()

    @Synchronized private fun report(
        status: FoundationReferenceStatus, sha: String? = null, state: String? = null,
        proposal: String? = null, called: Boolean = false
    ) = FoundationReferenceResult(
        status, revision, memory.generation, sha, state, proposal, called,
        verifiedAndroidEffect = false
    )

    fun accept(event: Percept, now: Long, deadline: Long, scope: String, consentEpoch: Long):
        FoundationReferenceResult {
        if (stopped.get()) return report(FoundationReferenceStatus.STOPPED)
        if (!busy.compareAndSet(false, true)) return report(FoundationReferenceStatus.BUSY)
        try {
            if (scope.isBlank() || event.sourceTag.isBlank() || event.data.isEmpty() ||
                event.data.size > 4096 || now < event.monotonicNanos || deadline <= now ||
                consentEpoch < 0) return report(FoundationReferenceStatus.INVALID_EVENT)
            val observation: Percept
            synchronized(this) {
                if (stopped.get()) return report(FoundationReferenceStatus.STOPPED)
                if (event.monotonicNanos <= lastEventNanos)
                    return report(FoundationReferenceStatus.INVALID_EVENT)
                observation = event.copy(data = event.data.copyOf())
                val key = "event:" + (revision + 1L)
                if (!scheduler.enqueue(
                    if (event.type == PerceptType.SENSOR) Priority.SENSOR else Priority.INTERNAL,
                    key, deadline)) return report(
                        if (stopped.get()) FoundationReferenceStatus.STOPPED
                        else FoundationReferenceStatus.INVALID_EVENT)
                if (scheduler.poll(now)?.payload != key)
                    return report(FoundationReferenceStatus.STOPPED)
                try {
                    memory.write(scope, key, observation.data, deadline, consentEpoch,
                        EntryKind.OBSERVED, event.sourceTag)
                } catch (_: Exception) {
                    return report(FoundationReferenceStatus.MEMORY_UNAVAILABLE)
                }
                lastEventNanos = event.monotonicNanos
                revision++
            }
            val sha = MessageDigest.getInstance("SHA-256").digest(observation.data)
                .joinToString("") { "%02x".format(it) }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            val output = try { neural.perceive(observation.copy(data = observation.data.copyOf())) }
                         catch (_: Exception) {
                             return report(FoundationReferenceStatus.MODEL_UNAVAILABLE, sha)
                         }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            if (output.stateDigest.isBlank())
                return report(FoundationReferenceStatus.MODEL_UNAVAILABLE, sha)
            val proposal = output.action ?: return report(
                FoundationReferenceStatus.NO_PROPOSAL, sha, output.stateDigest)
            val digest = controller.proposalDigest(proposal)
            val consent = try { owner.showExactProposalAndObtainConsent(proposal) }
                          catch (_: Exception) { null }
            if (stopped.get()) return report(FoundationReferenceStatus.STOPPED, sha)
            if (consent == null) return report(
                FoundationReferenceStatus.OWNER_DECLINED, sha, output.stateDigest, digest)
            val ticket = controller.prepare(proposal, consent, now, deadline) ?: return report(
                FoundationReferenceStatus.TRUST_REJECTED, sha, output.stateDigest, digest)
            if (stopped.get()) {
                controller.stop()
                return report(FoundationReferenceStatus.STOPPED, sha)
            }
            return when (val attempt = controller.dispatchOutcome(ticket, now)) {
                is DispatchAttempt.Rejected -> report(
                    FoundationReferenceStatus.DISPATCH_REJECTED, sha, output.stateDigest, digest)
                DispatchAttempt.Unresolved -> report(
                    FoundationReferenceStatus.MAY_HAVE_EXECUTED, sha, output.stateDigest, digest)
                is DispatchAttempt.Invoked -> when {
                    stopped.get() || attempt.nativeReturn == NativeEndpoint.UNKNOWN ->
                        report(FoundationReferenceStatus.MAY_HAVE_EXECUTED, sha,
                            output.stateDigest, digest, true)
                    controller.readbackAndCommit(ticket, now) ->
                        report(FoundationReferenceStatus.REFERENCE_READBACK_CLAIM, sha,
                            output.stateDigest, digest, true)
                    else -> report(FoundationReferenceStatus.READBACK_UNCONFIRMED, sha,
                        output.stateDigest, digest, true)
                }
            }
        } finally { busy.set(false) }
    }
}
