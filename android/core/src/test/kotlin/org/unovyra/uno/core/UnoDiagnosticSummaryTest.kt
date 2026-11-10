package org.unovyra.uno.core

object UnoDiagnosticSummaryTest {
    var pass = 0
    private fun t(name: String, action: () -> Unit) {
        action(); pass++; println("PASS $name")
    }
    fun run() {
        t("empty diagnostic cannot pass") {
            check(UnoDiagnosticEvaluator.summarize(emptyList(), false).status == "FAIL")
        }
        t("even all green probes are partial, never agent acceptance") {
            val s = UnoDiagnosticEvaluator.summarize(listOf("PASS", "PASS"), false)
            check(s.status == "PARTIAL" && s.passed == 2 && s.total == 2)
        }
        t("failed probe dominates incomplete checks") {
            val s = UnoDiagnosticEvaluator.summarize(listOf("PASS", "FAIL", "MANUAL_REQUIRED"), false)
            check(s.status == "FAIL" && s.failed == 1 && s.incomplete == 1)
        }
        t("unknown test verdict is fail closed") {
            val s = UnoDiagnosticEvaluator.summarize(listOf("PASS", "PASSS"), false)
            check(s.status == "FAIL" && s.unrecognized == 1)
        }
        t("owner STOP overrides green or failed checks") {
            check(UnoDiagnosticEvaluator.summarize(listOf("PASS", "FAIL"), true).status == "ABORTED")
        }
        t("aborted sub-probe cannot be counted as partial completion") {
            val s = UnoDiagnosticEvaluator.summarize(listOf("PASS", "ABORTED"), false)
            check(s.status == "ABORTED" && s.aborted == 1)
        }
        t("nonexecuted consent and neural are not passes") {
            val s = UnoDiagnosticEvaluator.summarize(
                listOf("PASS", "UNKNOWN", "DENIED", "NOT_RUN", "MANUAL_REQUIRED", "NOT_IMPLEMENTED"), false)
            check(s.status == "PARTIAL" && s.passed == 1 && s.incomplete == 5)
        }
    }
}
