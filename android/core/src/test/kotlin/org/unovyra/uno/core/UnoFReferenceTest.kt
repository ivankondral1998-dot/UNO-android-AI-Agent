package org.unovyra.uno.core

import kotlin.math.abs
import kotlin.math.tanh

object UnoFReferenceTest {
    var pass = 0
    private fun test(name: String, block: () -> Unit) {
        block(); pass++; println("PASS UNO_F_REF $name")
    }
    private fun zero(rows: Int, cols: Int) = UnoRefMatrix(rows, cols, DoubleArray(rows * cols))
    private fun matrix(rows: Int, cols: Int, row: Int, col: Int, value: Double): UnoRefMatrix {
        val v = DoubleArray(rows * cols)
        v[row * cols + col] = value
        return UnoRefMatrix(rows, cols, v)
    }
    private fun weights(rec: Boolean = false, memory: Boolean = false) : UnoRefWeights {
        val d=128; val m=128; val hidden=256; val b=64
        return UnoRefWeights(
            "SYNTHETIC_S4S5/1",
            matrix(d, 1, 0, 0, 1.0), zero(d,d), zero(d,d), zero(d,32),
            DoubleArray(d), DoubleArray(d),
            if(memory) matrix(m,d,0,0,1.0) else zero(m,d),
            if(memory) matrix(d,m,0,0,1.0) else zero(d,m),
            (0 until 2).map { branch -> (0 until 2).map { block ->
                UnoRefBranch(
                    if(rec && branch==0 && block==0) matrix(hidden,d,0,0,1.0) else zero(hidden,d),
                    zero(hidden,d),
                    if(rec && branch==0 && block==0) matrix(b,hidden,0,0,0.9) else zero(b,hidden),
                    DoubleArray(hidden),DoubleArray(b)
                )
            } }
        )
    }
    private fun event(f: Double = 1.0, s: Double = 0.0,
                      memory: List<UnoRefMemoryVector> = emptyList()): UnoRefEvent {
        val state=DoubleArray(128); state[0]=s
        return UnoRefEvent(doubleArrayOf(f), DoubleArray(32), state, DoubleArray(128),memory)
    }
    private fun near(actual: Double, expected: Double, tol: Double=1e-12) =
        check(abs(actual - expected) <= tol) { "actual=$actual expected=$expected" }
    private fun fails(block: () -> Unit) {
        var threw=false
        try { block() } catch (_: IllegalArgumentException) { threw=true }
        check(threw)
    }

    fun run() {
        test("zero_state_is_fixed_point") {
            val out=UnoFReference(weights()).forward(event(0.0),booleanArrayOf(true,true),8)
            check(out.state.all { it==0.0 })
            check(out.trace.aCalls==32 && out.trace.cCalls==4 && out.trace.bCalls==32)
        }
        test("empty_semantic_memory_still_applies_second_tanh") {
            val out=UnoFReference(weights()).forward(event(),booleanArrayOf(true,true),1)
            near(out.state[0],0.25*tanh(tanh(1.0)))
        }
        test("mask_skips_block_and_preserves_prior_h") {
            val state=DoubleArray(128);state[64]=0.8
            val input=UnoRefEvent(doubleArrayOf(0.0),DoubleArray(32),state,DoubleArray(128))
            val out=UnoFReference(weights()).forward(input,booleanArrayOf(true,false),3)
            near(out.state[64],0.4)
            check(out.trace.aCalls==6 && out.trace.bCalls==6 && out.trace.cCalls==2 &&
                out.trace.skippedBlocks==1)
        }
        test("synchronous_branch_average_and_leaky_recurrence") {
            val out=UnoFReference(weights(rec=true)).forward(event(0.0,1.0),booleanArrayOf(true,false),1)
            val expected=0.5*0.5+0.5*(tanh(0.9*tanh(0.5))/2.0)
            near(out.state[0],expected)
            near(out.state[64],0.0)
        }
        test("current_input_controls_semantic_query") {
            val key=DoubleArray(128);key[0]=1.0
            val value=DoubleArray(128);value[0]=0.5
            val input=event(1.0,memory=listOf(UnoRefMemoryVector(key,value)))
            val out=UnoFReference(weights(memory=true)).forward(input,booleanArrayOf(true,true),1)
            val expected=0.25*tanh(tanh(1.0)+0.5)
            near(out.state[0],expected)
        }
        test("softmax_is_finite_with_large_finite_scores") {
            val key=DoubleArray(128);key[0]=10000.0
            val neg=DoubleArray(128);neg[0]=-10000.0
            val v1=DoubleArray(128);v1[0]=0.8
            val v2=DoubleArray(128);v2[0]=-0.8
            val out=UnoFReference(weights(memory=true)).forward(event(memory=listOf(
                UnoRefMemoryVector(key,v1),UnoRefMemoryVector(neg,v2))),
                booleanArrayOf(true,true),1)
            check(out.state.all(Double::isFinite))
            near(out.state[0],0.25*tanh(tanh(1.0)+0.8))
        }
        test("cyclic_prefix_not_an_arbitrary_posthoc_mask") {
            check(unoCyclicPrefixMask(2,1,0).contentEquals(booleanArrayOf(true,false)))
            check(unoCyclicPrefixMask(2,1,1).contentEquals(booleanArrayOf(false,true)))
            check(unoCyclicPrefixMask(2,2,999).contentEquals(booleanArrayOf(true,true)))
        }
        test("nonfinite_inputs_and_empty_masks_fail_closed") {
            val model=UnoFReference(weights())
            fails { model.forward(event(),booleanArrayOf(false,false),1) }
            fails { model.forward(event(),booleanArrayOf(true,true),0) }
            fails { model.forward(event(Double.NaN),booleanArrayOf(true,true),1) }
            fails { model.forward(event(),booleanArrayOf(true,true),1,memoryTemperature=0.0) }
        }
        test("row_l1_contract_rejects_expanding_A") {
            val x=weights(rec=true)
            val branch=UnoRefBranch(matrix(256,128,0,0,1.1),zero(256,128),
                zero(64,256),DoubleArray(256),DoubleArray(64))
            fails { UnoRefWeights(x.version,x.projection,x.us,x.ug,x.meta,x.e,x.bias,x.wq,x.wr,
                listOf(listOf(branch,x.branches[0][1]),x.branches[1])) }
        }
        test("double_oracle_is_deterministic_and_does_not_mutate_input") {
            val input=event()
            val model=UnoFReference(weights(rec=true))
            val first=model.forward(input,booleanArrayOf(true,false),4)
            val second=model.forward(input,booleanArrayOf(true,false),4)
            check(first.state.contentEquals(second.state))
            check(input.features[0]==1.0 && input.state.all { it==0.0 })
        }
        test("reference_port_runs_inside_cycle_without_an_action") {
            val w = weights()
            val port = UnoFReferencePort(UnoFReference(w), w, booleanArrayOf(true, false), 2)
            val native = object : NativePort {
                override val trustedSourceTag = "FAKE_JVM"
                var calls = 0
                override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return NativeEndpoint.TRUE }
                override fun readback(ticket: Ticket, nowNanos: Long) = NativeEvidence(
                    ticket.id, NativeEndpoint.TRUE, 1L, nowNanos, trustedSourceTag)
            }
            val memory = ExactMemory()
            val cycle = UnoFoundationReferenceCycle(port, memory,
                TrustController(native, InMemoryLedger()),
                object : AuthenticatedOwnerUi {
                    override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
                })
            val bits = 1.0.toRawBits()
            val packed = ByteArray(8) { byte -> ((bits ushr (8 * byte)) and 0xff).toByte() }
            val result = cycle.accept(Percept(PerceptType.SENSOR, packed, "SYNTHETIC_FEATURES", 5L),
                5L, 100L, "reference", 0L)
            check(result.status == FoundationReferenceStatus.NO_PROPOSAL)
            check(!result.verifiedAndroidEffect && native.calls == 0)
            check(result.untrustedModelState != null && result.untrustedModelState.length == 64)
            check(port.lastTrace?.skippedBlocks == 1 && port.lastTrace?.activeBlocks == 1)
            check(memory.read("reference", "event:1", 1, 4, 6L, 0L).status == ExactStatus.COMPLETE)
            val text = cycle.accept(Percept(PerceptType.TEXT, "Привет".toByteArray(), "LOCAL_UI", 6L),
                6L, 100L, "reference", 0L)
            check(text.status == FoundationReferenceStatus.MODEL_UNAVAILABLE && native.calls == 0)
        }
        println("UNO_F_REFERENCE_HOST_PASS=$pass")
    }
}
fun main() { UnoFReferenceTest.run() }
