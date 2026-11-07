package org.unovyra.uno.core

/** Priority is a transport hint, NEVER permission to dispatch native effects. */
enum class Priority { STOP, REVOKE, PROCESS_DEATH, DEADLINE, READBACK, OWNER, SENSOR, INTERNAL }
data class QueuedEvent(val priority:Priority,val serial:Long,val deadlineNanos:Long,val payload:Any)

/** Bounded, one-way STOP, no automatic resumption; device trust has its own independent gate. */
class BoundedScheduler(private val maxEvents:Int=UnoAbi.MAX_QUEUE) {
    init{ require(maxEvents in 1..UnoAbi.MAX_QUEUE) }
    private val q=java.util.PriorityQueue<QueuedEvent>(compareBy<QueuedEvent> { it.priority.ordinal }.thenBy { it.serial })
    private var serial=0L
    private val stopLatch=java.util.concurrent.atomic.AtomicBoolean(false)
    fun isStopped():Boolean=stopLatch.get()
    fun stop() {
        stopLatch.set(true)
        synchronized(this) { q.clear() } // never deliver stale events after STOP returns
    }
    fun enqueue(priority:Priority,payload:Any,deadlineNanos:Long):Boolean {
        if(priority==Priority.STOP || priority==Priority.REVOKE || priority==Priority.PROCESS_DEATH) {
            stop();return true
        }
        if(deadlineNanos<0) return false
        synchronized(this) {
            if(stopLatch.get() || q.size>=maxEvents || serial==Long.MAX_VALUE)return false
            q.add(QueuedEvent(priority,++serial,deadlineNanos,payload))
            return true
        }
    }
    /** Expired events are discarded, not delivered. Caller still must check STOP before any effect. */
    @Synchronized fun poll(nowNanos:Long=Long.MIN_VALUE):QueuedEvent? {
        if(stopLatch.get())return null
        while(q.isNotEmpty()) {
            val event=q.poll()
            if(nowNanos>=0 && event.deadlineNanos<=nowNanos)continue
            if(stopLatch.get())return null
            return event
        }
        return null
    }
    @Synchronized fun size():Int=q.size
}
