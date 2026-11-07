package org.unovyra.uno.core

import java.util.IdentityHashMap
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Pure host/Android-independent compute-admission primitive, NOT Android authority.
 * Units: MAC = conservative predicted multiply-accumulates; tokens = admitted tokens;
 * scratchBytes = peak concurrent TEMPORARY allocation estimate, not cumulative IO.
 * Never interpret an admitted request as a physical RAM/energy/time guarantee.
 */
data class ComputeLimits(
    val totalMac: Long,
    val totalTokens: Long,
    val concurrentScratchBytes: Long,
    val deadlineElapsedNanos: Long,
    val maxInFlight: Int
) {
    init {
        require(totalMac >= 0 && totalTokens >= 0 && concurrentScratchBytes >= 0)
        require(deadlineElapsedNanos > 0 && maxInFlight > 0)
    }
}

data class ComputeEstimate(val mac: Long, val tokens: Long, val scratchBytes: Long) {
    init {
        require(mac >= 0 && tokens >= 0 && scratchBytes >= 0)
        require(mac != 0L || tokens != 0L || scratchBytes != 0L)
    }
}

data class ComputeRemaining(
    val mac: Long,
    val tokens: Long,
    val freeScratchBytes: Long,
    val inFlight: Int,
    val stopped: Boolean
)

/** Deliberately non-data type: permits are checked by identity against this gate's registry. */
class ComputePermit internal constructor()

sealed class ComputeAttempt<out T> {
    object Rejected : ComputeAttempt<Nothing>()
    data class Finished<T>(val value: T) : ComputeAttempt<T>()
}

/**
 * Conservative pre-admission; no speculative execution on refusal. Monotonic time is
 * explicitly supplied by the caller and must be from ONE verified clock domain.
 * MAC/tokens never refunded because partial execution cannot be inferred from exceptions.
 */
class ComputeBudgetGate(private val limits: ComputeLimits) {
    private val stopped = AtomicBoolean(false)
    private val active = IdentityHashMap<ComputePermit, Long>()
    private var remainingMac = limits.totalMac
    private var remainingTokens = limits.totalTokens
    private var usedScratch = 0L
    private var lastObservedNanos = -1L

    private fun freshTime(now: Long): Boolean {
        if (now < 0 || now < lastObservedNanos) return false
        lastObservedNanos = now
        return now < limits.deadlineElapsedNanos
    }

    @Synchronized fun admit(cost: ComputeEstimate, nowElapsedNanos: Long): ComputePermit? {
        if (stopped.get() || !freshTime(nowElapsedNanos)) return null
        if (active.size >= limits.maxInFlight || cost.mac > remainingMac ||
            cost.tokens > remainingTokens ||
            cost.scratchBytes > limits.concurrentScratchBytes - usedScratch) return null
        val permit = ComputePermit()
        remainingMac -= cost.mac
        remainingTokens -= cost.tokens
        usedScratch += cost.scratchBytes
        active[permit] = cost.scratchBytes
        // STOP may race admission; the caller MUST call isCurrent immediately before each expensive kernel.
        return permit
    }

    @Synchronized fun isCurrent(permit: ComputePermit, nowElapsedNanos: Long): Boolean =
        !stopped.get() && active.containsKey(permit) && freshTime(nowElapsedNanos)

    /** Idempotent release of temporary scratch reservation. MAC/tokens are NOT refunded. */
    @Synchronized fun release(permit: ComputePermit) {
        val reserved = active.remove(permit) ?: return
        usedScratch -= reserved
    }

    /** One-way STOP. Does not interrupt an already-running native or CPU kernel. */
    fun stop() {
        stopped.set(true)
        synchronized(this) {
            active.clear()
            usedScratch = 0L
        }
    }

    @Synchronized fun remaining(): ComputeRemaining = ComputeRemaining(
        remainingMac, remainingTokens,
        limits.concurrentScratchBytes - usedScratch, active.size, stopped.get()
    )

    /**
     * Runs the body ONLY after successful admission and a fresh pre-execution check.
     * Long-running bodies must cooperatively call isCurrent() at safe checkpoints.
     */
    fun <T> tryRun(
        cost: ComputeEstimate, clockElapsedNanos: () -> Long, body: (ComputePermit) -> T
    ): ComputeAttempt<T> {
        val permit = admit(cost, clockElapsedNanos()) ?: return ComputeAttempt.Rejected
        try {
            if (!isCurrent(permit, clockElapsedNanos())) return ComputeAttempt.Rejected
            return ComputeAttempt.Finished(body(permit))
        } finally {
            release(permit)
        }
    }
}
