package org.unovyra.uno.core

/** Astra A01 §7 + UDC v0.3 + erratum 11: a single host reference session.
 * Not a production executor: fixed F, fixed model identity, no runtime P updates,
 * no proposal or Android privileges, no raw-text GOAL encoder. The owner/controller
 * supplies already projected events, versions and a trusted monotonic clock.
 * Lock order session -> exact -> semantic. Store callbacks must not enter the session.
 */
internal enum class RefSessionStatus {
    COMMITTED, STOPPED, STALE, GOAL_PENDING, DEADLINE, MEMORY_UNAVAILABLE,
    BUDGET_ABORT, COMPUTE_FAILED, INVALID_CONTEXT
}
internal data class RefSessionView(val revision: Long, val goalVersion: Long,
    val consentEpoch: Long, val goalReady: Boolean, val stopped: Boolean,
    val modelDigest: String, val state: DoubleArray, val goal: DoubleArray)
internal data class RefSessionResult(val status: RefSessionStatus,
    val trace: UnoRefKernelTrace? = null,
    val resources: RefCycleUsage? = null,
    val memoryStatus: S4Status? = null, val memoryReason: S4Reason? = null)

internal class UnoRefSession(
    private val reference: UnoFReference,
    private val modelDigest: String,
    private val ports: UnoMemoryPorts,
    private val scope: String,
    initialConsentEpoch: Long,
    private val clockNanos: () -> Long
) {
    init {
        require(modelDigest.length == 64 && modelDigest.all { it in '0'..'9' || it in 'a'..'f' })
        require(scope.isNotBlank() && initialConsentEpoch >= 0L)
        // Known monitor-based reference stores only. A different backend needs its own atomic contract.
        require(ports.exact is ExactMemory || ports.exact is UnoEncryptedExactMemory)
    }
    private var state = DoubleArray(reference.stateWidth)
    private var goal = DoubleArray(reference.stateWidth)
    private var revision = 0L
    private var goalVersion = 0L
    private var consentEpoch = initialConsentEpoch
    private var goalReady = true
    private var stopped = false
    private var serial = 0L
    private var activeAttempt = false
    private var lastNow = -1L
    // Session identity and model identity are fixed by this owner instance; P-version=0
    // (immutable UNO 1.0). No work from another instance can reach the private publisher.
    private data class Stamp(val revision: Long, val cookie: Long, val goalVersion: Long,
        val consentEpoch: Long, val exactGeneration: Long, val semanticGeneration: Long)
    private data class Work(val stamp: Stamp, val event: UnoRefEvent,
        val goalMode: Boolean, val validUntil: Long)

    @Synchronized fun snapshot(): RefSessionView = RefSessionView(revision, goalVersion,
        consentEpoch, goalReady, stopped, modelDigest, state.copyOf(), goal.copyOf())

    @Synchronized fun stop() { stopped = true }

    /** Called by trusted owner control, not model output. No partial g is published. */
    @Synchronized fun changeGoal(newVersion: Long): Boolean {
        if (stopped || newVersion <= goalVersion || revision == Long.MAX_VALUE) return false
        goalVersion = newVersion
        goalReady = false
        revision++
        return true
    }
    @Synchronized fun changeConsentEpoch(newEpoch: Long): Boolean {
        if (stopped || newEpoch <= consentEpoch || revision == Long.MAX_VALUE) return false
        consentEpoch = newEpoch
        revision++
        return true
    }
    private fun freshNow(): Long? = try {
        val n = clockNanos()
        if (n < 0L || n < lastNow) null else n.also { lastNow = it }
    } catch (_: Exception) { null }

    /** One bounded host attempt at a time, with a reservation for BOTH catalogue
     * passes and publication. A newer valid request still invalidates older work,
     * but cannot allocate a second F workspace while the first is in flight.
     * Goal mode remains a single already-projected synthetic goal event.
     * The trusted callbacks are external to the numeric resource contract.
     */
    fun run(features: DoubleArray, metadata: DoubleArray, expectedGoalVersion: Long,
        goalMode: Boolean, deadlineNanos: Long, scanBudget: Int, budget: UnoS6Budget,
        seed: Long, counter: Long,
        logits: (DoubleArray, DoubleArray) -> DoubleArray,
        hazard: (DoubleArray) -> Double, cycleLimits: RefCycleLimits): RefSessionResult {
        synchronized(this) {
            if (stopped) return RefSessionResult(RefSessionStatus.STOPPED)
            if (expectedGoalVersion != goalVersion || serial == Long.MAX_VALUE ||
                revision == Long.MAX_VALUE || scanBudget < 0 ||
                features.size != reference.featureWidth || metadata.size != 32 || seed < 0 || counter < 0)
                return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
            if (goalMode == goalReady) return RefSessionResult(RefSessionStatus.GOAL_PENDING)
            val now = freshNow() ?: return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
            if (now >= deadlineNanos) return RefSessionResult(RefSessionStatus.DEADLINE)
            if (activeAttempt) {
                serial++ // retain the previous newer-cookie invalidation rule, without concurrent F
                return RefSessionResult(RefSessionStatus.BUDGET_ABORT)
            }
            activeAttempt = true
        }
        var validUntil = deadlineNanos
        val meter = RefCycleMeter(cycleLimits) {
            synchronized(this) {
                if (stopped) throw RefCycleAbort(RefSessionStatus.STOPPED)
                val now = freshNow() ?: throw RefCycleAbort(RefSessionStatus.INVALID_CONTEXT)
                if (now >= validUntil) throw RefCycleAbort(RefSessionStatus.DEADLINE)
            }
        }
        try {
            reference.reserveCycle(meter, budget, scanBudget, goalMode)
            return runReserved(features, metadata, expectedGoalVersion, goalMode, deadlineNanos,
                scanBudget, budget, seed, counter, logits, hazard, meter) {
                validUntil = minOf(validUntil, it)
            }.copy(resources = meter.usage())
        } catch (e: RefCycleAbort) {
            return RefSessionResult(e.status, resources = meter.usage())
        } catch (_: ArithmeticException) {
            return RefSessionResult(RefSessionStatus.BUDGET_ABORT, resources = meter.usage())
        } finally {
            synchronized(this) { activeAttempt = false }
        }
    }

    private fun runReserved(features: DoubleArray, metadata: DoubleArray, expectedGoalVersion: Long,
        goalMode: Boolean, deadlineNanos: Long, scanBudget: Int, budget: UnoS6Budget,
        seed: Long, counter: Long, logits: (DoubleArray, DoubleArray) -> DoubleArray,
        hazard: (DoubleArray) -> Double, meter: RefCycleMeter, setValidUntil: (Long) -> Unit): RefSessionResult {
        val x = features.copyOf()
        val meta = metadata.copyOf()
        val work: Work = synchronized(this) {
            if (stopped) return RefSessionResult(RefSessionStatus.STOPPED)
            if (expectedGoalVersion != goalVersion || serial == Long.MAX_VALUE ||
                revision == Long.MAX_VALUE || scanBudget < 0) return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
            if (goalMode == goalReady) return RefSessionResult(RefSessionStatus.GOAL_PENDING)
            val now = freshNow() ?: return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
            if (now >= deadlineNanos) return RefSessionResult(RefSessionStatus.DEADLINE)
            try {
                ports.withVersions { eg, sg ->
                    meter.checkpoint()
                    val bank = if (goalMode) null else ports.withS4Bank(
                        S4Access(scope, now, consentEpoch, scanBudget), reference.memoryWidth) { it }
                    if (bank != null) meter.observeCatalogue(bank.scannedRows)
                    meter.checkpoint()
                    if (bank != null && (bank.status !in setOf(S4Status.COMPLETE, S4Status.EMPTY) ||
                        bank.authorityGeneration != eg || bank.semanticGeneration != sg))
                        return RefSessionResult(RefSessionStatus.MEMORY_UNAVAILABLE, memoryStatus = bank.status, memoryReason = bank.reason)
                    val validUntil = bank?.validUntilNanos ?: Long.MAX_VALUE
                    setValidUntil(validUntil)
                    val checked = freshNow() ?: return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
                    if (checked >= minOf(deadlineNanos, validUntil))
                        return RefSessionResult(RefSessionStatus.DEADLINE)
                    val cookie = ++serial
                    Work(Stamp(revision, cookie, goalVersion, consentEpoch, eg, sg),
                        UnoRefEvent(x, meta,
                            if (goalMode) DoubleArray(reference.stateWidth) else state,
                            if (goalMode) DoubleArray(reference.stateWidth) else goal,
                            bank?.hits?.map { UnoRefMemoryVector(it.vector, it.vector) } ?: emptyList()),
                        goalMode, validUntil)
                }
            } catch (e: RefCycleAbort) { throw e }
            catch (_: Exception) { return RefSessionResult(RefSessionStatus.MEMORY_UNAVAILABLE, memoryStatus = S4Status.UNKNOWN, memoryReason = S4Reason.UNAVAILABLE) }
        }
        val computed = try {
            reference.forwardAdaptiveMetered(work.event, budget, work.stamp.cookie - 1L, seed, counter, logits, hazard, meter = meter)
        } catch (e: RefCycleAbort) { throw e }
        catch (_: Exception) { return RefSessionResult(RefSessionStatus.COMPUTE_FAILED) }
        val next = computed.output ?: return RefSessionResult(RefSessionStatus.BUDGET_ABORT)
        // The model can only return a bounded state vector. No authority is inferred.
        if (next.state.size != reference.stateWidth || next.state.any { it !in -1.0..1.0 })
            return RefSessionResult(RefSessionStatus.COMPUTE_FAILED)
        return publish(work, next, deadlineNanos, scanBudget, meter)
    }

    /** One linearization point. No publish inside withS4Authority's callback: it has
     * a post-callback validation that may fail. Keep the outer store locks instead.
     * Freshness is checked again after the pure catalogue read and before commit.
     */
    @Synchronized private fun publish(work: Work, next: UnoRefOutput,
        deadline: Long, scanBudget: Int, meter: RefCycleMeter): RefSessionResult {
        if (stopped) return RefSessionResult(RefSessionStatus.STOPPED)
        val stamp = work.stamp
        if (stamp.revision != revision || stamp.cookie != serial || stamp.goalVersion != goalVersion ||
            stamp.consentEpoch != consentEpoch || revision == Long.MAX_VALUE)
            return RefSessionResult(RefSessionStatus.STALE)
        return try {
            ports.withVersions { eg, sg ->
                if (stamp.exactGeneration != eg || stamp.semanticGeneration != sg)
                    RefSessionResult(RefSessionStatus.STALE)
                else {
                    val now = freshNow() ?: return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
                    if (now >= minOf(deadline, work.validUntil)) return RefSessionResult(RefSessionStatus.DEADLINE)
                    meter.checkpoint()
                    val bank = if (work.goalMode) null else ports.withS4Bank(
                        S4Access(scope, now, consentEpoch, scanBudget), reference.memoryWidth) { it }
                    if (bank != null) meter.observeCatalogue(bank.scannedRows)
                    meter.checkpoint()
                    if (bank != null && (bank.status !in setOf(S4Status.COMPLETE, S4Status.EMPTY) ||
                        bank.authorityGeneration != eg || bank.semanticGeneration != sg))
                        return RefSessionResult(RefSessionStatus.MEMORY_UNAVAILABLE, memoryStatus = bank.status, memoryReason = bank.reason)
                    val checked = freshNow() ?: return RefSessionResult(RefSessionStatus.INVALID_CONTEXT)
                    if (checked >= minOf(deadline, work.validUntil, bank?.validUntilNanos ?: Long.MAX_VALUE))
                        return RefSessionResult(RefSessionStatus.DEADLINE)
                    // All checks and assignment share the session and store locks.
                    // STOP, goal, consent, other work and memory changes cannot interleave here.
                    val frozen = next.state.copyOf()
                    if (work.goalMode) { goal = frozen; goalReady = true } else state = frozen
                    revision++
                    RefSessionResult(RefSessionStatus.COMMITTED, next.trace)
                }
            }
        } catch (e: RefCycleAbort) { throw e }
        catch (_: Exception) { RefSessionResult(RefSessionStatus.MEMORY_UNAVAILABLE, memoryStatus = S4Status.UNKNOWN, memoryReason = S4Reason.UNAVAILABLE) }
    }
}
