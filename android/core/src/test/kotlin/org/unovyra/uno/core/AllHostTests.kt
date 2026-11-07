package org.unovyra.uno.core

fun main() {
    CoreSelfTest.run()
    ProbeMathTest.run()
    MeasurementTest.run()
    LabProtocolTest.run()
    println("UNO_WP01_HOST_PASS=${CoreSelfTest.pass + ProbeMathTest.pass + MeasurementTest.pass + LabProtocolTest.pass}")
}
