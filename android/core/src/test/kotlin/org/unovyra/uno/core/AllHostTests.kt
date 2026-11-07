package org.unovyra.uno.core

fun main() {
    CoreSelfTest.run()
    ProbeMathTest.run()
    MeasurementTest.run()
    LabProtocolTest.run()
    ThemePersonalizationTest.run()
    FoundationHardeningTest.run()
    println("UNO_WP01_HOST_PASS=${CoreSelfTest.pass + ProbeMathTest.pass + MeasurementTest.pass + LabProtocolTest.pass + ThemePersonalizationTest.pass + FoundationHardeningTest.pass}")
}
