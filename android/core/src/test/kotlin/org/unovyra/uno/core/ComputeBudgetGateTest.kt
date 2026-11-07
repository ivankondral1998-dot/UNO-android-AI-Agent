package org.unovyra.uno.core

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

/** Host-only tests for a resource ADMISSION contract, not the Android/kernel implementation. */
object ComputeBudgetGateTest {
    var pass = 0
    private fun t(label: String, block: () -> Unit) { block(); pass++; println("PASS COMPUTE_GATE $label") }
    private fun gate(mac: Long = 100, tokens: Long = 10, scratch: Long = 1024,
                     deadline: Long = 1000, concurrent: Int = 2) =
        ComputeBudgetGate(ComputeLimits(mac, tokens, scratch, deadline, concurrent))
    fun run() {
        t("MAC_zero_denies_and_skips_expensive_body") {
            val g=gate(mac=0); var called=false
            val x=g.tryRun(ComputeEstimate(1,0,0),{1L}) { called=true }
            check(x is ComputeAttempt.Rejected && !called)
        }
        t("tokens_zero_denies_and_skips_expensive_body") {
            val g=gate(tokens=0); var called=false
            check(g.tryRun(ComputeEstimate(1,1,0),{1L}) { called=true } is ComputeAttempt.Rejected)
            check(!called)
        }
        t("scratch_zero_denies_and_skips_expensive_body") {
            val g=gate(scratch=0); var called=false
            check(g.tryRun(ComputeEstimate(1,0,1),{1L}) { called=true } is ComputeAttempt.Rejected)
            check(!called)
        }
        t("deadline_expiry_denies_and_skips") {
            val g=gate(deadline=10); var called=false
            check(g.tryRun(ComputeEstimate(1,0,0),{10L}) { called=true } is ComputeAttempt.Rejected)
            check(!called)
        }
        t("reserve_is_atomic_across_dimensions") {
            val g=gate(mac=3,tokens=3,scratch=3)
            check(g.admit(ComputeEstimate(2,2,4),1)==null)
            check(g.remaining()==ComputeRemaining(3,3,3,0,false))
        }
        t("consumed_work_not_refunded_on_release") {
            val g=gate(mac=5,tokens=5,scratch=5)
            val p=g.admit(ComputeEstimate(3,2,5),1)!!
            check(g.remaining()==ComputeRemaining(2,3,0,1,false))
            g.release(p);g.release(p)
            check(g.remaining()==ComputeRemaining(2,3,5,0,false))
        }
        t("another_gate_cannot_accept_foreign_permit") {
            val first=gate();val second=gate();val p=first.admit(ComputeEstimate(1,0,0),1)!!
            check(!second.isCurrent(p,1));second.release(p)
            check(first.isCurrent(p,2))
        }
        t("permit_invalid_after_release") {
            val g=gate();val p=g.admit(ComputeEstimate(1,0,0),1)!!
            g.release(p);check(!g.isCurrent(p,2))
        }
        t("STOP_clears_scratch_and_invalidates_old_permits") {
            val g=gate();val p=g.admit(ComputeEstimate(1,0,256),1)!!
            g.stop();check(!g.isCurrent(p,2));check(g.remaining().inFlight==0)
            check(g.admit(ComputeEstimate(1,0,1),2)==null)
        }
        t("monotonic_clock_rollback_is_denied") {
            val g=gate();val p=g.admit(ComputeEstimate(1,0,0),10)!!
            check(!g.isCurrent(p,9));check(g.isCurrent(p,11))
        }
        t("remaining_scratch_is_shared_between_concurrent_permits") {
            val g=gate(scratch=10)
            val p=g.admit(ComputeEstimate(1,0,7),1)!!
            check(g.admit(ComputeEstimate(1,0,4),2)==null)
            g.release(p)
            check(g.admit(ComputeEstimate(1,0,4),3)!=null)
        }
        t("max_concurrency_prevents_parallel_admissions") {
            val g=gate(concurrent=1)
            val p=g.admit(ComputeEstimate(1,0,0),1)!!
            check(g.admit(ComputeEstimate(1,0,0),1)==null)
            g.release(p);check(g.admit(ComputeEstimate(1,0,0),2)!=null)
        }
        t("large_numbers_do_not_overflow") {
            val g=gate(mac=Long.MAX_VALUE,tokens=Long.MAX_VALUE,scratch=Long.MAX_VALUE)
            val p=g.admit(ComputeEstimate(Long.MAX_VALUE,Long.MAX_VALUE,Long.MAX_VALUE),1)!!
            check(g.remaining().mac==0L && g.remaining().tokens==0L && g.remaining().freeScratchBytes==0L)
            g.release(p)
            check(g.admit(ComputeEstimate(1,0,0),2)==null)
        }
        t("body_exception_releases_scratch_without_refunding_MAC") {
            val g=gate(mac=10,scratch=10)
            var failed = false
            try { g.tryRun(ComputeEstimate(2,0,10),{1L}) { throw IllegalStateException("fail") } }
            catch (_:IllegalStateException) { failed = true }
            check(failed && g.remaining()==ComputeRemaining(8,10,10,0,false))
        }
        t("request_with_all_zero_cost_fails_closed") {
            var bad=false
            try { ComputeEstimate(0,0,0) } catch (_:IllegalArgumentException) { bad=true }
            check(bad)
        }
        t("negative_estimates_and_negative_limits_rejected") {
            var denied=0
            try { ComputeEstimate(-1,0,0) } catch (_:IllegalArgumentException) { denied++ }
            try { ComputeLimits(1,-1,0,1,1) } catch (_:IllegalArgumentException) { denied++ }
            check(denied==2)
        }
        t("race_cannot_overspend_MAC_allowance") {
            val g=gate(mac=20_000,tokens=0,scratch=0,concurrent=100)
            val started=CountDownLatch(1);val done=CountDownLatch(8);val granted=AtomicInteger()
            val failure=AtomicReference<Throwable?>(null)
            repeat(8) {
                Thread {
                    try {
                        check(started.await(3,TimeUnit.SECONDS))
                        repeat(3000) {
                            val p=g.admit(ComputeEstimate(1,0,0),1)
                            if(p!=null){granted.incrementAndGet();g.release(p)}
                        }
                    } catch (error: Throwable) { failure.compareAndSet(null, error) }
                    finally {done.countDown()}
                }.start()
            }
            started.countDown();check(done.await(8,TimeUnit.SECONDS))
            check(failure.get()==null && granted.get()==20_000 && g.remaining().mac==0L)
        }
        println("COMPUTE_GATE_HOST_PASS=$pass")
    }
}
fun main() { ComputeBudgetGateTest.run() }
