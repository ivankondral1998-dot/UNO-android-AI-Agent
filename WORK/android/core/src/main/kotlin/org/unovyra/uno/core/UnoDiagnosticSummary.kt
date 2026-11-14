package org.unovyra.uno.core

/** A bounded lab report is not an acceptance certificate for the UNO agent. */
data class UnoDiagnosticSummary(
    val status: String,
    val total: Int,
    val passed: Int,
    val failed: Int,
    val incomplete: Int,
    val aborted: Int,
    val unrecognized: Int
)

/** Strict, host-testable aggregation independent of Android and the UI. */
object UnoDiagnosticEvaluator {
    private val recognized = setOf(
        "PASS", "FAIL", "ABORTED", "UNKNOWN", "INCONCLUSIVE", "UNSUPPORTED",
        "NOT_RUN", "DENIED", "MANUAL_REQUIRED", "NOT_IMPLEMENTED", "NOT_TESTED"
    )

    fun summarize(checkStatuses: List<String>, stopped: Boolean): UnoDiagnosticSummary {
        val passed = checkStatuses.count { it == "PASS" }
        val failed = checkStatuses.count { it == "FAIL" }
        val aborted = checkStatuses.count { it == "ABORTED" }
        val unrecognized = checkStatuses.count { it !in recognized }
        val incomplete = checkStatuses.size - passed - failed - aborted - unrecognized
        val status = when {
            stopped || aborted > 0 -> "ABORTED"
            checkStatuses.isEmpty() || failed > 0 || unrecognized > 0 -> "FAIL"
            else -> "PARTIAL"
        }
        return UnoDiagnosticSummary(status, checkStatuses.size, passed, failed,
            incomplete, aborted, unrecognized)
    }
}
