package org.unovyra.uno.core

fun main() {
    CoreSelfTest.run()
    ProbeMathTest.run()
    println("UNO_WP01_HOST_PASS=${CoreSelfTest.pass + ProbeMathTest.pass}")
}
