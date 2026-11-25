package org.unovyra.uno.core

import javax.crypto.KeyGenerator
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

object C4ReferenceSessionTest {
    var pass=0
    private fun verify(name:String, ok:Boolean) { check(ok) { name };pass++;println("PASS C4 $name") }
    private class Fixture(encrypted:Boolean=false) {
        val now=AtomicLong(10)
        private val key=KeyGenerator.getInstance("AES").apply { init(128) }.generateKey()
        private var exactBytes: ByteArray? = null
        val exact:UnoExactMemoryPort = if(encrypted) UnoEncryptedExactMemory(key,"boot",{exactBytes?.copyOf()},{exactBytes=it.copyOf()}){now.get()} else ExactMemory()
        private var indexBytes: ByteArray? = null
        val index=UnoSemanticMemory(key,"boot",{indexBytes?.copyOf()},{indexBytes=it.copyOf()}, dimension=128)
        val ports=UnoMemoryPorts(exact,index)
        val model=UnoFReference(UnoFReferenceTest.weights(rec=true,memory=true))
        var clockReads=0
        var clockHook:(Int)->Unit={}
        val session=UnoRefSession(model,"a".repeat(64),ports,"owner",0){clockHook(++clockReads);now.get()}
        val budget=UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE,1)
        val logits:(DoubleArray,DoubleArray)->DoubleArray={_,_->doubleArrayOf(0.0,-1000.0)}
        fun add(expiry:Long=100L):ExactEntry {
            val row=exact.write("owner","key",byteArrayOf(1),expiry,0,EntryKind.USER_DECLARATION,"OWNER_UI")
            ports.linkSummary(row,DoubleArray(128){if(it==0)0.5 else 0.0},S4Access("owner",now.get(),0,64))
            return row
        }
        fun run(goal:Boolean=false,version:Long=0L,deadline:Long=100L,scan:Int=64,
                b:UnoS6Budget=budget, hook:()->Unit={}):RefSessionResult = session.run(
            doubleArrayOf(1.0),DoubleArray(32),version,goal,deadline,scan,b,3,0,
            { h,z -> hook();logits(h,z) },{0.0},
            RefCycleLimits(Long.MAX_VALUE,Long.MAX_VALUE,Long.MAX_VALUE,Long.MAX_VALUE))
        fun expected(s:DoubleArray,g:DoubleArray,serial:Long,bank:List<UnoRefMemoryVector> = emptyList()) =
            model.forwardAdaptive(UnoRefEvent(doubleArrayOf(1.0),DoubleArray(32),s,g,bank),budget,serial,3,0,logits,{0.0}).output!!.state
    }
    private fun concurrent(name:String, f:Fixture, change:()->Unit,
                           expected:RefSessionStatus=RefSessionStatus.STALE,goal:Boolean=false,version:Long=0L) {
        val entered=CountDownLatch(1);val resume=CountDownLatch(1)
        val result=AtomicReference<RefSessionResult>();val error=AtomicReference<Throwable>()
        val thread=Thread {
            try { result.set(f.run(goal,version,hook={entered.countDown();check(resume.await(5,TimeUnit.SECONDS))})) }
            catch(t:Throwable){error.set(t)}
        }
        val before=f.session.snapshot()
        thread.start()
        try { check(entered.await(5,TimeUnit.SECONDS)); change() } finally {resume.countDown()}
        thread.join(5000)
        val after=f.session.snapshot()
        verify(name, !thread.isAlive && error.get()==null && result.get()?.status==expected && result.get()?.trace==null &&
            before.state.contentEquals(after.state) && before.goal.contentEquals(after.goal))
    }
    fun run() {
        val f=Fixture()
        verify("normal_commit_matches_same_F",f.run().status==RefSessionStatus.COMMITTED &&
            f.session.snapshot().state.contentEquals(f.expected(DoubleArray(128),DoubleArray(128),0)))
        val first=f.session.snapshot();val s=first.state.copyOf();first.state.fill(123.0)
        verify("defensive_state_snapshot",f.session.snapshot().state.contentEquals(s))
        verify("second_event_uses_prior_committed_state",f.run().status==RefSessionStatus.COMMITTED &&
            f.session.snapshot().state.contentEquals(f.expected(s,DoubleArray(128),1)))
        f.add();val saved=f.session.snapshot().state
        verify("goal_switch_blocks_normal_and_stale_version",f.session.changeGoal(1) &&
            f.run(version=1).status==RefSessionStatus.GOAL_PENDING && f.run(goal=true,version=0).status==RefSessionStatus.INVALID_CONTEXT)
        verify("goal_same_F_empty_bank_zero_temporary_state",f.run(goal=true,version=1).status==RefSessionStatus.COMMITTED &&
            f.session.snapshot().goal.contentEquals(f.expected(DoubleArray(128),DoubleArray(128),2)) &&
            f.session.snapshot().state.contentEquals(saved) && f.session.snapshot().goalReady)
        verify("duplicate_goal_reencoding_denied",f.run(goal=true,version=1).status==RefSessionStatus.GOAL_PENDING)
        val staleGoal=Fixture();check(staleGoal.session.changeGoal(1))
        concurrent("stale_goal_encoding_never_publishes",staleGoal,{check(staleGoal.session.changeGoal(2))},goal=true,version=1)
        verify("stale_goal_remains_pending",!staleGoal.session.snapshot().goalReady && staleGoal.session.snapshot().goalVersion==2L)
        val stopped=Fixture();concurrent("stop_during_actual_F",stopped,{stopped.session.stop()},RefSessionStatus.STOPPED)
        verify("stopped_session_no_new_work",stopped.run().status==RefSessionStatus.STOPPED)
        val consent=Fixture();concurrent("consent_epoch_changes",consent,{check(consent.session.changeConsentEpoch(1))})
        val goal=Fixture();concurrent("goal_change_invalidates_normal_work",goal,{check(goal.session.changeGoal(1))})
        val revoked=Fixture();revoked.add();concurrent("exact_and_semantic_revoke_during_F",revoked,{revoked.ports.revoke("owner")})
        verify("revoked_scope_new_work_denied",revoked.run().status==RefSessionStatus.MEMORY_UNAVAILABLE)
        val mutated=Fixture();val row=mutated.add();concurrent("semantic_only_change_invalidates_stamp",mutated,{
            mutated.ports.linkSummary(row,DoubleArray(128){-0.5},S4Access("owner",10,0,64))})
        val aba=Fixture();val abaRow=aba.add();concurrent("semantic_ABA_invalidates_stamp",aba,{
            aba.ports.linkSummary(abaRow,DoubleArray(128){-0.5},S4Access("owner",10,0,64));
            aba.ports.linkSummary(abaRow,DoubleArray(128){if(it==0)0.5 else 0.0},S4Access("owner",10,0,64))})
        val newer=Fixture();concurrent("newer_cookie_aborted_still_invalidates_old",newer,{
            check(newer.run(b=UnoS6Budget(0,0,1)).status==RefSessionStatus.BUDGET_ABORT)})
        val exact=Fixture();concurrent("exact_write_invalidates_stamp",exact,{exact.add()})
        val expires=Fixture();expires.add(expiry=20);concurrent("memory_expiry_before_publish",expires,{expires.now.set(20)},RefSessionStatus.DEADLINE)
        val deadline=Fixture();concurrent("deadline_before_publish",deadline,{deadline.now.set(100)},RefSessionStatus.DEADLINE)
        val clock=Fixture();concurrent("clock_regression_fail_closed",clock,{clock.now.set(9)},RefSessionStatus.INVALID_CONTEXT)
        val budget=Fixture();budget.add();verify("catalogue_budget_denied",budget.run(scan=0).let { it.status==RefSessionStatus.MEMORY_UNAVAILABLE && it.memoryStatus==S4Status.BUDGET_EXCEEDED && it.memoryReason==S4Reason.SCAN_LIMIT })
        verify("S6_budget_abort_no_state_commit",budget.run(b=UnoS6Budget(0,0,1)).status==RefSessionStatus.BUDGET_ABORT && budget.session.snapshot().revision==0L)
        val enc=Fixture(encrypted=true);enc.add();verify("encrypted_reference_store_commit",enc.run().status==RefSessionStatus.COMMITTED)
        concurrent("encrypted_reference_revocation",enc,{enc.ports.revoke("owner")})
        val encExpiry=Fixture(encrypted=true);encExpiry.add(expiry=20);concurrent("encrypted_expiry",encExpiry,{encExpiry.now.set(20)},RefSessionStatus.DEADLINE)
        // Deterministically force the interleaving at the reservation boundary:
        // monitor reentry is used only as a test hook, not a runtime clock policy.
        val earlyConsent=Fixture()
        earlyConsent.clockHook={i->if(i==2)check(earlyConsent.session.changeConsentEpoch(1))}
        val rejectedConsent=earlyConsent.run()
        verify("pre_snapshot_consent_change_cannot_rebase",rejectedConsent.status==RefSessionStatus.STALE &&
            rejectedConsent.resources?.enteredMac==0L && earlyConsent.session.snapshot().state.all{it==0.0})
        val earlyMemory=Fixture()
        earlyMemory.clockHook={i->if(i==2)earlyMemory.add()}
        val rejectedMemory=earlyMemory.run()
        verify("pre_snapshot_memory_change_cannot_rebase",rejectedMemory.status==RefSessionStatus.STALE &&
            rejectedMemory.resources?.enteredMac==0L && earlyMemory.session.snapshot().revision==0L)
        val earlyNewer=Fixture()
        earlyNewer.clockHook={i->if(i==2)check(earlyNewer.run().status==RefSessionStatus.BUDGET_ABORT)}
        val rejectedNewer=earlyNewer.run()
        verify("pre_snapshot_newer_cookie_cannot_rebase",rejectedNewer.status==RefSessionStatus.STALE &&
            rejectedNewer.resources?.enteredMac==0L && earlyNewer.session.snapshot().revision==0L)
        val control=Fixture();check(control.run().status==RefSessionStatus.COMMITTED)
        val lastClock=control.clockReads
        val finalConsent=Fixture()
        finalConsent.clockHook={i->if(i==lastClock)check(finalConsent.session.changeConsentEpoch(1))}
        verify("final_clock_consent_change_never_publishes",finalConsent.run().status==RefSessionStatus.STALE &&
            finalConsent.session.snapshot().state.all{it==0.0})
        val finalStop=Fixture();finalStop.clockHook={i->if(i==lastClock)finalStop.session.stop()}
        verify("final_clock_STOP_never_publishes",finalStop.run().status==RefSessionStatus.STOPPED &&
            finalStop.session.snapshot().revision==0L)
        val finalMemory=Fixture();finalMemory.clockHook={i->if(i==lastClock)finalMemory.add()}
        verify("final_clock_memory_change_never_publishes",finalMemory.run().status==RefSessionStatus.STALE &&
            finalMemory.session.snapshot().revision==0L)
        println("UNO_C4_SESSION_HOST_PASS=$pass")
    }
}
