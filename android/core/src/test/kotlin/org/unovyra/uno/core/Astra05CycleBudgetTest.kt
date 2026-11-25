package org.unovyra.uno.core

import javax.crypto.KeyGenerator
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

/** Fixed synthetic d128 fixture only, not an owner-approved geometry. */
object Astra05CycleBudgetTest {
    var pass = 0
    private fun verify(name: String, ok: Boolean) { check(ok) { name }; pass++; println("PASS ASTRA05 $name") }
    private val generous = RefCycleLimits(Long.MAX_VALUE, Long.MAX_VALUE, Long.MAX_VALUE, Long.MAX_VALUE)
    private const val S4 = 69_760L
    private const val MIN = S4 + 163_840L
    private class Fixture {
        val now = AtomicLong(10L)
        private val key = KeyGenerator.getInstance("AES").apply { init(128) }.generateKey()
        val exact = ExactMemory()
        private var indexBytes: ByteArray? = null
        val index = UnoSemanticMemory(key,"boot",{indexBytes?.copyOf()},{indexBytes=it.copyOf()},dimension=128)
        val ports = UnoMemoryPorts(exact,index)
        val model = UnoFReference(UnoFReferenceTest.weights(rec=true,memory=true))
        val session = UnoRefSession(model,"b".repeat(64),ports,"owner",0){now.get()}
        fun add() {
            val row = exact.write("owner","key",byteArrayOf(1),100,0,EntryKind.USER_DECLARATION,"OWNER_UI")
            ports.linkSummary(row,DoubleArray(128){0.5},S4Access("owner",10,0,64))
        }
        fun run(l: RefCycleLimits = generous, k: Int = 1, scan: Int = 64,
                logits: () -> DoubleArray = {doubleArrayOf(0.0,-1000.0)}, halt: () -> Double = {0.0},
                goal: Boolean = false, ver: Long = 0): RefSessionResult = session.run(
            doubleArrayOf(1.0),DoubleArray(32),ver,goal,100,scan,
            UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE,k),3,0,{_,_->logits()},{halt()},l)
    }
    fun run() {
        val f = Fixture()
        verify("independent_S4_formula",f.model.s4Mac(0)==S4 && f.model.s4Mac(1)==S4+256)
        val denied=f.run(generous.copy(mac=MIN-1))
        verify("minimum_path_rejected_before_S4",denied.status==RefSessionStatus.BUDGET_ABORT &&
            denied.resources!!.enteredMac==0L && denied.resources.kernelEntries.isEmpty() && f.session.snapshot().revision==0L)
        val one=f.run(generous.copy(mac=MIN)); val u=one.resources!!
        verify("exact_minimum_boundary",one.status==RefSessionStatus.COMMITTED && u.enteredMac==MIN)
        verify("S4_entries_and_actual_selected_kernels",u.kernelEntries==mapOf("S4_projection" to 1L,"S4_us" to 1L,"S4_ug" to 1L,
            "S4_meta" to 1L,"S4_wq" to 1L,"S4_wr" to 1L,"S5_C" to 2L,"S5_A" to 2L,"S5_B" to 2L))
        verify("independent_scan_reserve_and_actual",u.catalogueRowsReserved==128L && u.catalogueRowsObserved==0L)
        verify("scalar_payload_reserved",u.scalarReserved>0 && u.numericReservedBytes>2*1_310_720L && u.externalHeadEntries==1L)
        val scalar=Fixture().run(generous.copy(scalarUnits=u.scalarReserved-1))
        verify("scalar_cap_precedes_any_kernel",scalar.status==RefSessionStatus.BUDGET_ABORT && scalar.resources!!.enteredMac==0L)
        val bytes=Fixture().run(generous.copy(numericBytes=u.numericReservedBytes-1))
        verify("numeric_cap_precedes_any_kernel",bytes.status==RefSessionStatus.BUDGET_ABORT && bytes.resources!!.enteredMac==0L)
        val rows=Fixture().run(generous.copy(catalogueRows=127))
        verify("second_scan_reserved_before_first",rows.status==RefSessionStatus.BUDGET_ABORT && rows.resources!!.catalogueRowsObserved==0L)
        val exact=Fixture().run(RefCycleLimits(MIN,u.scalarReserved,u.numericReservedBytes,128))
        verify("all_reservation_boundaries",exact.status==RefSessionStatus.COMMITTED && exact.resources==u)
        val mem=Fixture();mem.add()
        val missing=mem.run(generous.copy(mac=MIN))
        verify("actual_attention_cost_checked_after_catalogue_before_forward",missing.status==RefSessionStatus.BUDGET_ABORT && missing.resources!!.catalogueRowsObserved==2L && missing.resources.enteredMac==0L)
        val got=mem.run(generous.copy(mac=MIN+256))
        verify("memory_both_passes_and_attention",got.status==RefSessionStatus.COMMITTED && got.resources!!.enteredMac==MIN+256 &&
            got.resources.catalogueRowsObserved==4L && got.resources.kernelEntries["S4_scores"]==1L && got.resources.kernelEntries["S4_read"]==1L)
        val k2=Fixture().run(generous.copy(mac=S4+262_144),k=3)
        verify("next_step_uses_total_remaining_budget",k2.status==RefSessionStatus.COMMITTED && k2.trace!!.innerSteps==2 && k2.resources!!.enteredMac==S4+262_144 &&
            k2.resources.kernelEntries["S5_C"]==2L && k2.resources.kernelEntries["S5_A"]==4L && k2.resources.externalHeadEntries==2L)
        val k1=Fixture().run(generous.copy(mac=S4+262_143),k=3,halt={error("forced stop must skip head")})
        verify("one_MAC_below_second_step",k1.status==RefSessionStatus.COMMITTED && k1.trace!!.innerSteps==1 && k1.resources!!.enteredMac==MIN)
        val full=Fixture().run(generous.copy(mac=S4+327_680),logits={doubleArrayOf(-1000.0,2000.0)})
        verify("both_blocks_actual_entries",full.status==RefSessionStatus.COMMITTED && full.trace!!.activeBlocks==2 && full.resources!!.enteredMac==S4+327_680 && full.resources.kernelEntries["S5_C"]==4L)
        val deadline=Fixture();val late=deadline.run(logits={deadline.now.set(100);doubleArrayOf(0.0,-1000.0)})
        verify("deadline_after_selector_no_S5",late.status==RefSessionStatus.DEADLINE && late.resources!!.enteredMac==S4 && "S5_C" !in late.resources.kernelEntries && deadline.session.snapshot().revision==0L)
        val fail=Fixture();val broken=fail.run(logits={error("synthetic callback failure")})
        verify("failed_head_does_not_refund_S4",broken.status==RefSessionStatus.COMPUTE_FAILED && broken.resources!!.enteredMac==S4 && broken.resources.externalHeadEntries==1L)
        val halt=Fixture();val lateHalt=halt.run(k=3,halt={halt.now.set(100);0.0})
        verify("deadline_after_first_recurrent_step",lateHalt.status==RefSessionStatus.DEADLINE && lateHalt.resources!!.enteredMac==MIN && lateHalt.resources.kernelEntries["S5_A"]==2L && halt.session.snapshot().revision==0L)
        val g=Fixture();g.add();check(g.session.changeGoal(1));val goal=g.run(generous.copy(catalogueRows=0),goal=true,ver=1)
        verify("goal_no_catalogue_charge_same_F",goal.status==RefSessionStatus.COMMITTED && goal.resources!!.catalogueRowsReserved==0L && goal.resources.enteredMac==MIN)
        val race=Fixture();val entered=CountDownLatch(1);val release=CountDownLatch(1);val prior=AtomicReference<RefSessionResult>()
        val t=Thread { prior.set(race.run(logits={entered.countDown();check(release.await(5,TimeUnit.SECONDS));doubleArrayOf(0.0,-1000.0)})) }
        t.start();try {check(entered.await(5,TimeUnit.SECONDS));val newer=race.run(logits={error("second workspace")})
            verify("one_workspace_in_flight",newer.status==RefSessionStatus.BUDGET_ABORT && newer.resources==null)
        } finally {release.countDown();t.join(5000)}
        verify("newer_request_invalidates_old_without_second_workspace",!t.isAlive && prior.get()?.status==RefSessionStatus.STALE && race.session.snapshot().revision==0L)
        verify("reservation_released_after_rejection",race.run().status==RefSessionStatus.COMMITTED)
        // Meter cannot be reused/reset, nor spend before reservation.
        val meter=RefCycleMeter(RefCycleLimits(2,3,4,2)) {}
        verify("no_kernel_before_reservation",runCatching{meter.enter("probe",1)}.isFailure)
        verify("negative_reservation_denied",runCatching{meter.reserve(-1,0,0,0)}.isFailure)
        meter.reserve(1,3,4,2);meter.enter("probe",1);meter.observeCatalogue(1)
        verify("second_reservation_cannot_reset_ledger",runCatching{meter.reserve(0,0,0,0)}.isFailure &&
            meter.usage().enteredMac==1L && meter.usage().catalogueRowsObserved==1L)
        verify("no_row_overrun",runCatching{meter.observeCatalogue(2)}.isFailure && meter.usage().catalogueRowsObserved==1L)
        verify("no_mac_overrun",runCatching{meter.enter("probe",2)}.isFailure && meter.usage().enteredMac==1L)
        // A real encrypted authority view is scanned, then its post-callback
        // clock check fails. The completed scans remain charged despite refusal.
        val key=KeyGenerator.getInstance("AES").apply{init(128)}.generateKey()
        var exactBytes:ByteArray?=null;var indexBytes:ByteArray?=null
        var clockReads=0;var regress=false
        val vault=UnoEncryptedExactMemory(key,"boot",{exactBytes?.copyOf()},{exactBytes=it.copyOf()}){
            if(regress && ++clockReads==2) 9L else 10L }
        val index=UnoSemanticMemory(key,"boot",{indexBytes?.copyOf()},{indexBytes=it.copyOf()},dimension=128)
        val ports=UnoMemoryPorts(vault,index)
        val row=vault.write("owner","key",byteArrayOf(1),100,0,EntryKind.OBSERVED,"LOCAL_UI")
        ports.linkSummary(row,DoubleArray(128){0.5},S4Access("owner",10,0,64))
        val abortMeter=RefCycleMeter(generous){};abortMeter.reserve(0,0,0,64)
        regress=true
        verify("post_scan_rejection_keeps_both_catalogue_charges",runCatching{
            ports.withS4BankMetered(S4Access("owner",10,0,64),128,abortMeter::observeCatalogue){it}
        }.isFailure && abortMeter.usage().catalogueRowsObserved==2L)
        println("UNO_ASTRA05_CYCLE_HOST_PASS=$pass")
    }
}
