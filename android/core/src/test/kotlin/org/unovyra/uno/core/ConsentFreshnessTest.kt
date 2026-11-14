package org.unovyra.uno.core

/**
 * C1 regression: approval expiry is a hard upper bound for reference ticket dispatch.
 * Uses a fake native port and injected monotonic time; this is NOT Android OS authority.
 */
object ConsentFreshnessTest {
    var pass = 0
        private set

    private fun test(label: String, body: () -> Unit) {
        body()
        pass++
        println("PASS C1 $label")
    }

    private class FakeNative : NativePort {
        override val trustedSourceTag = "FAKE_C1_CLOCK"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint {
            calls++
            return NativeEndpoint.TRUE
        }
        override fun readback(ticket: Ticket, nowNanos: Long): NativeEvidence =
            NativeEvidence(ticket.id, NativeEndpoint.TRUE, calls.toLong(), nowNanos, trustedSourceTag)
    }

    private fun fixture(
        native: FakeNative,
        clock: () -> Long,
        consentExpires: Long = 20L,
        taskDeadline: Long = 100L
    ): Pair<TrustController, Ticket?> {
        val c = TrustController(
            native, InMemoryLedger(), mapOf(15 to "LOCAL_C1_FIXTURE"),
            trustedClockNanos = clock
        )
        val p = Proposal(15, "local|value".toByteArray(), "C1_FIXTURE", 1L, "CLOCK_TEST")
        val consent = Consent(
            c.proposalDigest(p), "LOCAL_C1_FIXTURE", consentExpires,
            c.epoch, c.nonce, ownerUnlocked = true
        )
        return c to c.prepare(p, consent, 10L, taskDeadline)
    }

    fun run() {
        test("owner consent deadline caps ticket lifetime") {
            var clock = 10L
            val native = FakeNative()
            val (c, ticket) = fixture(native, { clock })
            val t = ticket ?: error("prepare unexpectedly rejected")
            check(t.deadlineNanos == 20L)
            clock = 20L
            val attempt = c.dispatchOutcome(t, 10L)
            check(attempt == DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED))
            check(t.phase == Phase.CANCELLED && native.calls == 0)
        }
        test("fresh time rejects consent already expired during prepare") {
            val native = FakeNative()
            val (_, ticket) = fixture(native, { 21L })
            check(ticket == null && native.calls == 0)
        }
        test("clock advances after admission check but before native call") {
            var clock = 10L
            val native = FakeNative()
            val (c, ticket) = fixture(native, { clock.also { clock += 5L } })
            val t = ticket ?: error("prepare unexpectedly rejected")
            val result = c.dispatchOutcome(t, 10L)
            check(result == DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED))
            check(native.calls == 0 && t.phase == Phase.CANCELLED)
        }
        test("valid call and independent fake readback remain available") {
            var clock = 10L
            val native = FakeNative()
            val (c, ticket) = fixture(native, { clock })
            val t = ticket ?: error("prepare unexpectedly rejected")
            clock = 15L
            check(c.dispatchOutcome(t, 10L) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
            check(native.calls == 1)
            clock = 16L
            check(c.readbackAndCommit(t, 10L))
            check(t.used && t.phase == Phase.COMMITTED && native.calls == 1)
        }
        test("late readback does not commit a success claim") {
            var clock = 10L
            val native = FakeNative()
            val (c, ticket) = fixture(native, { clock })
            val t = ticket ?: error("prepare unexpectedly rejected")
            clock = 15L
            check(c.dispatchOutcome(t, 10L) == DispatchAttempt.Invoked(NativeEndpoint.TRUE))
            clock = 20L
            check(!c.readbackAndCommit(t, 10L))
            check(!t.used && t.readback == null && native.calls == 1)
        }
        test("backward monotonic clock fails closed") {
            var clock = 10L
            val native = FakeNative()
            val (c, ticket) = fixture(native, { clock })
            val t = ticket ?: error("prepare unexpectedly rejected")
            clock = 9L
            check(c.dispatchOutcome(t, 10L) == DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED))
            check(native.calls == 0)
        }
        test("broken trusted clock fails closed") {
            var broken = false
            val native = FakeNative()
            val (c, ticket) = fixture(native, { if (broken) error("clock fault") else 10L })
            val t = ticket ?: error("prepare unexpectedly rejected")
            broken = true
            check(c.dispatchOutcome(t, 10L) == DispatchAttempt.Rejected(DispatchRejection.STOP_OR_EXPIRED))
            check(native.calls == 0)
        }
        test("STOP still prevents native dispatch") {
            val native = FakeNative()
            val (c, ticket) = fixture(native, { 10L })
            val t = ticket ?: error("prepare unexpectedly rejected")
            c.stop()
            check(c.dispatchOutcome(t, 10L) is DispatchAttempt.Rejected)
            check(native.calls == 0)
        }
    }
}

fun main() { ConsentFreshnessTest.run() }
