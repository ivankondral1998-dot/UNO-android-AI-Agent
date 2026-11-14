package uno.core

/** Trusted control-event ordering. No neural output can manufacture these events. */
enum class ControlEventKind(val priority: Int) {
    STOP(0), REVOKE(0), PROCESS_DEATH(0), DEADLINE(1), READBACK(2), OWNER(3),
    SENSOR(4), INTERNAL(5)
}

data class ControlEvent(val sequence: Long, val kind: ControlEventKind)

/** In-memory bounded scheduler. STOP is an out-of-band latch, never a queue entry. */
class ControlEventQueue(private val capacity: Int = 1024) {
    init { require(capacity > 0) }
    private val pending = ArrayList<ControlEvent>()
    private var nextSequence = 0L
    var stopLatched: Boolean = false
        private set

    @Synchronized fun submit(kind: ControlEventKind): Boolean {
        if (kind == ControlEventKind.STOP || kind == ControlEventKind.PROCESS_DEATH) {
            stopLatched = true
            return true
        }
        if (kind == ControlEventKind.REVOKE) {
            stopLatched = true // conservative fail-closed until authority revalidation
            return true
        }
        if (pending.size >= capacity || nextSequence == Long.MAX_VALUE) return false
        pending.add(ControlEvent(nextSequence++, kind))
        return true
    }

    @Synchronized fun next(): ControlEvent? {
        if (stopLatched || pending.isEmpty()) return null
        val index = pending.indices.minWithOrNull(compareBy<Int> { pending[it].kind.priority }
            .thenBy { pending[it].sequence }) ?: return null
        return pending.removeAt(index)
    }

    /** Dispatch must check this immediately before the external native call. */
    @Synchronized fun dispatchPermitted(): Boolean = !stopLatched

    @Synchronized fun size(): Int = pending.size
}
