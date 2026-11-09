package org.unovyra.uno.core

fun main() {
    CoreSelfTest.run()
    UnoPromptWindowTest.run()
    ProbeMathTest.run()
    MeasurementTest.run()
    LabProtocolTest.run()
    ThemePersonalizationTest.run()
    FoundationHardeningTest.run()
    ComputeBudgetGateTest.run()
    ActionIntentJournalTest.run()
    ActionJournalControllerIntegrationTest.run()
    ActionReceiptRecoveryTest.run()
    ActionAtomicReferenceCommitTest.run()
    println("UNO_WP01_HOST_PASS=${UnoPromptWindowTest.pass + CoreSelfTest.pass + ProbeMathTest.pass + MeasurementTest.pass + LabProtocolTest.pass + ThemePersonalizationTest.pass + FoundationHardeningTest.pass + ComputeBudgetGateTest.pass + ActionIntentJournalTest.pass + ActionJournalControllerIntegrationTest.pass + ActionReceiptRecoveryTest.pass + ActionAtomicReferenceCommitTest.pass}")
}
