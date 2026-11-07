package org.unovyra.uno.core

/** STOP is a separate atomic latch and is never dependent on neural queue capacity. */
enum class Priority { STOP, REVOKE, PROCESS_DEATH, DEADLINE, READBACK, OWNER, SENSOR, INTERNAL }
data class QueuedEvent(val priority:Priority,val serial:Long,val deadlineNanos:Long,val payload:Any)

class BoundedScheduler(private val maxEvents:Int=UnoAbi.MAX_QUEUE) {
    init{require(maxEvents in 1..UnoAbi.MAX_QUEUE)}
    private val q=java.util.PriorityQueue<QueuedEvent>(compareBy<QueuedEvent> { it.priority.ordinal }.thenBy { it.serial })
    private var serial=0L
    val stopLatch=java.util.concurrent.atomic.AtomicBoolean(false)
    fun enqueue(priority:Priority,payload:Any,deadlineNanos:Long):Boolean {
        if (priority==Priority.STOP) { stopLatch.set(true);return true }
        if (q.size>=maxEvents || serial==Long.MAX_VALUE) return false
        q.add(QueuedEvent(priority,++serial,deadlineNanos,payload));return true
    }
    fun poll():QueuedEvent?=q.poll()
    fun size():Int=q.size
}
