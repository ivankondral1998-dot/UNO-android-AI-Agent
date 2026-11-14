package org.unovyra.uno.core

import kotlin.math.ceil
import kotlin.math.sqrt

/** WP-01 measurement math. Counts must be real samples; not inferred from neural MAC. */
object Measurement {
    data class Stats(
        val count: Int, val min: Long, val p50: Long, val p90: Long,
        val p95: Long, val p99: Long, val max: Long,
        val mean: Double, val sampleStdDev: Double, val sum: Double
    )

    fun summarize(samples: List<Long>): Stats {
        require(samples.isNotEmpty() && samples.size <= 100_000)
        require(samples.all { it >= 0L })
        val sorted = samples.sorted()
        fun pct(p: Double): Long = sorted[(ceil(p * sorted.size).toInt() - 1).coerceIn(0, sorted.lastIndex)]
        // Use double accumulation to avoid Long overflow from large durations.
        val mean = samples.sumOf { it.toDouble() } / samples.size
        val variance = if (samples.size == 1) 0.0 else samples.sumOf {
            val deviation = it.toDouble() - mean
            deviation * deviation
        } / (samples.size - 1)
        return Stats(samples.size, sorted.first(), pct(.50), pct(.90), pct(.95),
            pct(.99), sorted.last(), mean, sqrt(variance), mean * samples.size)
    }

    /** Validity-first paired comparison. Never interpret a speedup as model quality. */
    data class Comparison(val result: String, val baselineP95: Long?, val candidateP95: Long?,
                          val ratioCandidateToBaseline: Double?, val notes: String)
    fun compareLatency(baseline: List<Long>, candidate: List<Long>,
                       sameWorkload: Boolean, sameDevice: Boolean): Comparison {
        if (!sameWorkload || !sameDevice) return Comparison("INCOMPARABLE", null, null, null,
            "different workload or device; no performance conclusion")
        if (baseline.size < 20 || candidate.size < 20) return Comparison("INSUFFICIENT", null, null, null,
            "fewer than 20 observations per group; exploratory only")
        val a = summarize(baseline).p95
        val b = summarize(candidate).p95
        return Comparison(if (a == 0L) "INDETERMINATE" else "DESCRIPTIVE_ONLY",
            a, b, if (a == 0L) null else b.toDouble() / a, "not a statistical significance test")
    }
}

/** A scenario result cannot be PASS unless a real independent oracle was recorded. */
enum class EvidenceVerdict { PASS, FAIL, INCONCLUSIVE, NOT_RUN, UNSUPPORTED }
data class ScenarioEvidence(val id: String, val expected: String, val observed: String?,
                            val independentOracle: Boolean, val completed: Boolean) {
    fun verdict(): EvidenceVerdict = when {
        !completed -> EvidenceVerdict.NOT_RUN
        observed == null || !independentOracle -> EvidenceVerdict.INCONCLUSIVE
        observed == expected -> EvidenceVerdict.PASS
        else -> EvidenceVerdict.FAIL
    }
}
