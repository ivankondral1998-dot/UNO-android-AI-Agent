package org.unovyra.uno.core

object UnoProcessStopTest {
    var pass = 0
    private fun verify(x:Boolean) { check(x); pass++ }
    fun run() {
        verify(!UnoProcessStop.isStopped())
        UnoProcessStop.stop()
        verify(UnoProcessStop.isStopped())
        UnoProcessStop.stop()
        verify(UnoProcessStop.isStopped())
        println("UNO_PROCESS_STOP_HOST_PASS=$pass")
    }
}
