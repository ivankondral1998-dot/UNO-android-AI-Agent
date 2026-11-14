package uno.core

fun main() {
    val q = ControlEventQueue(3)
    check(q.submit(ControlEventKind.INTERNAL))
    check(q.submit(ControlEventKind.SENSOR))
    check(q.submit(ControlEventKind.READBACK))
    check(!q.submit(ControlEventKind.OWNER))
    check(q.next()?.kind == ControlEventKind.READBACK)
    check(q.next()?.kind == ControlEventKind.SENSOR)
    check(q.next()?.kind == ControlEventKind.INTERNAL)
    check(q.next() == null)
    check(q.submit(ControlEventKind.INTERNAL))
    check(q.submit(ControlEventKind.STOP))
    check(q.stopLatched && !q.dispatchPermitted())
    check(q.next() == null)
    val r = ControlEventQueue(1)
    check(r.submit(ControlEventKind.INTERNAL))
    check(r.submit(ControlEventKind.REVOKE)) // cannot be evicted by full queue
    check(!r.dispatchPermitted())
    println("ControlEventsTest PASS")
}
