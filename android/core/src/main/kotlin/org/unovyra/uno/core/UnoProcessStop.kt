package org.unovyra.uno.core

import java.util.concurrent.atomic.AtomicBoolean

/**
 * Same-process fail-closed STOP latch. Not persisted and not a cross-process Android action gate.
 * Android effects are separately deny-all until trusted authority implementation.
 */
object UnoProcessStop {
    private val halted = AtomicBoolean(false)
    fun stop() { halted.set(true) }
    fun isStopped(): Boolean = halted.get()
}
