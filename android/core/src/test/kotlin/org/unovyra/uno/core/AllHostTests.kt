package org.unovyra.uno.core

fun main() {
    CoreSelfTest.run()
    UnoPromptWindowTest.run()
    UnoTextCycleTest.run()
    ProbeMathTest.run()
    MeasurementTest.run()
    LabProtocolTest.run()
    UnoDiagnosticSummaryTest.run()
    ThemePersonalizationTest.run()
    FoundationHardeningTest.run()
    ComputeBudgetGateTest.run()
    ActionIntentJournalTest.run()
    ActionJournalControllerIntegrationTest.run()
    ActionReceiptRecoveryTest.run()
    ActionAtomicReferenceCommitTest.run()
    UnoChatCipherTest.run()
    UnoProcessStopTest.run()
    UnoFoundationReferenceCycleTest.run()
    UnoEncryptedExactMemoryTest.run()
    UnoManualFactsTest.run()
    println("UNO_WP01_HOST_PASS=${UnoChatCipherTest.pass + UnoProcessStopTest.pass + UnoFoundationReferenceCycleTest.pass + UnoEncryptedExactMemoryTest.pass + UnoTextCycleTest.pass + UnoPromptWindowTest.pass + CoreSelfTest.pass + ProbeMathTest.pass + MeasurementTest.pass + LabProtocolTest.pass + UnoDiagnosticSummaryTest.pass + ThemePersonalizationTest.pass + FoundationHardeningTest.pass + ComputeBudgetGateTest.pass + ActionIntentJournalTest.pass + ActionJournalControllerIntegrationTest.pass + ActionReceiptRecoveryTest.pass + ActionAtomicReferenceCommitTest.pass + UnoManualFactsTest.pass}")
}
