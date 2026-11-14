package org.unovyra.uno.core

import kotlin.math.ceil

/** Stable statistic definitions for measurements; device data are never inferred from MAC. */
object ProbeMath {
    /** Nearest-rank percentile: ceil(p*N)-1, for p in [0,1]. */
    fun percentile(values: List<Long>, p: Double): Long {
        require(values.isNotEmpty() && p in 0.0..1.0 && !p.isNaN())
        require(values.all { it >= 0L })
        val s = values.sorted()
        return s[(ceil(p * s.size).toInt() - 1).coerceIn(0, s.lastIndex)]
    }

    data class Latency(val p50Nanos: Long, val p95Nanos: Long, val p99Nanos: Long,
                       val minNanos: Long, val maxNanos: Long, val samples: Int)

    fun summarize(values: List<Long>): Latency = Latency(
        percentile(values, .50), percentile(values, .95), percentile(values, .99),
        values.minOrNull()!!, values.maxOrNull()!!, values.size)

    /** Blocked branch is NEVER called. The output parity is checked on host. */
    inline fun <T> conditionalKernel(active: Boolean, onActive: () -> T, onSkip: () -> T): T =
        if (active) onActive() else onSkip()
}
