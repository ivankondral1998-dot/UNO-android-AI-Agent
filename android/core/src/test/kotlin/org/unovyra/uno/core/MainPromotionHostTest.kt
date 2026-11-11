import org.unovyra.uno.core.ProbeMathTest
import org.unovyra.uno.core.UnoDiagnosticSummaryTest

fun main() {
    ProbeMathTest.run()
    UnoDiagnosticSummaryTest.run()
    check(ProbeMathTest.pass == 5 && UnoDiagnosticSummaryTest.pass == 8)
    println("UNO_MAIN_PROMOTION_HOST_PASS=13")
}
