package org.unovyra.uno.core

import javax.crypto.KeyGenerator
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
        test("summary_changes_reference_state_without_replacing_the_fact") {
            val d = 128
            val hidden = 256
            val block = 64
            val w = UnoRefWeights(
                "SYNTHETIC_S4S5/1",
                matrix(d, d, 0, 0, 1.0), zero(d, d), zero(d, d), zero(d, 32),
                DoubleArray(d), DoubleArray(d),
                matrix(d, d, 0, 0, 1.0), matrix(d, d, 0, 0, 1.0),
                (0 until 2).map { _ -> (0 until 2).map { _ ->
                    UnoRefBranch(zero(hidden, d), zero(hidden, d), zero(block, hidden),
                        DoubleArray(hidden), DoubleArray(block))
                } }
            )
            val exact = ExactMemory()
            val fact = exact.write("notes", "fact", "plus".toByteArray(), 500L, 0L,
                EntryKind.OBSERVED, "LOCAL_UI")
            val query = DoubleArray(d); query[0] = 1.0
            val secret = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
            var stored: ByteArray? = null
            val semantic = UnoSemanticMemory(secret, "boot-a", { stored?.copyOf() },
                { stored = it.copyOf() }, d)
            semantic.link(fact, query)
            val packed = ByteArray(d * 8)
            val bits = 1.0.toRawBits()
            for (byte in 0 until 8) packed[byte] = ((bits ushr (8 * byte)) and 0xff).toByte()
            val percept = Percept(PerceptType.SENSOR, packed, "SYNTHETIC_FEATURES", 5L)
            fun cycle(port: NeuralPort) = UnoFoundationReferenceCycle(port, ExactMemory(),
                TrustController(object : NativePort {
                    override val trustedSourceTag = "FAKE_JVM"
                    var calls = 0
                    override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return NativeEndpoint.TRUE }
                    override fun readback(ticket: Ticket, nowNanos: Long) = NativeEvidence(
                        ticket.id, NativeEndpoint.TRUE, 1L, nowNanos, trustedSourceTag)
                }, InMemoryLedger()),
                object : AuthenticatedOwnerUi {
                    override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
                })
            val withSummary = cycle(UnoFReferencePort(UnoFReference(w), w,
                booleanArrayOf(true, false), 1, semantic, "notes"))
            val without = cycle(UnoFReferencePort(UnoFReference(w), w, booleanArrayOf(true, false), 1))
            val remembered = withSummary.accept(percept, 5L, 100L, "reference", 0L)
            val plain = without.accept(percept, 5L, 100L, "reference", 0L)
            check(remembered.status == FoundationReferenceStatus.NO_PROPOSAL)
            check(plain.status == FoundationReferenceStatus.NO_PROPOSAL)
            check(remembered.untrustedModelState != plain.untrustedModelState)
            check(!remembered.verifiedAndroidEffect)
            check(exact.read("notes", "fact", 1, 4, 6L, 0L).entries.single()
                .raw.contentEquals("plus".toByteArray()))
        }
        test("S4_reads_all_five_eligible_summary_records_no_prequery_top4") {
            val d = 128
            val w = UnoRefWeights(
                "S4_FULL_ELIGIBLE_SYNTHETIC/1",
                matrix(d,d,0,0,1.0), zero(d,d), zero(d,d), zero(d,32),
                DoubleArray(d), DoubleArray(d),
                matrix(d,d,1,0,1.0), matrix(d,d,0,1,1.0),
                (0 until 2).map { (0 until 2).map {
                    UnoRefBranch(zero(256,d), zero(256,d), zero(64,256),
                        DoubleArray(256), DoubleArray(64))
                } }
            )
            val exact = ExactMemory()
            val secret = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
            var saved: ByteArray? = null
            val index = UnoSemanticMemory(secret, "s4-host-boot", { saved?.copyOf() },
                { saved = it.copyOf() }, d)
            fun basis(i: Int) = DoubleArray(d).also { it[i] = 1.0 }
            val vectors = (0 until 4).map { basis(0) } + basis(1)
            vectors.forEachIndexed { j, vector ->
                val entry = exact.write("test-s4", "fact-$j", byteArrayOf(j.toByte()),
                    10_000L, 0L, EntryKind.OBSERVED, "SYNTHETIC")
                index.link(entry, vector)
            }
            val feature = basis(0)
            val early = index.retrieve("test-s4", feature, 4, 64)
            check(early.status == SemanticStatus.TRUNCATED && early.hits.size == 4)
            check(index.eligibleForS4("test-s4", 4).status == SemanticStatus.UNKNOWN)
            val eligible = index.eligibleForS4("test-s4", 256)
            check(eligible.status == SemanticStatus.SUMMARY_ONLY && eligible.hits.size == 5)
            val mask = booleanArrayOf(true,false)
            val reference = UnoFReference(w)
            val full = reference.forward(UnoRefEvent(
                feature, DoubleArray(32), DoubleArray(d), DoubleArray(d),
                vectors.map { UnoRefMemoryVector(it,it) }), mask, 1)
            val partial = reference.forward(UnoRefEvent(
                feature, DoubleArray(32), DoubleArray(d), DoubleArray(d),
                early.hits.map { UnoRefMemoryVector(it.vector,it.vector) }), mask, 1)
            check(full.state[0] - partial.state[0] > 1e-4)
            val port = UnoFReferencePort(reference,w,mask,1,index,"test-s4")
            val packed = ByteArray(d*8)
            feature.forEachIndexed { i, number ->
                var bits = number.toRawBits()
                for (b in 0 until 8) {
                    packed[i*8+b] = (bits and 255).toByte()
                    bits = bits ushr 8
                }
            }
            val observed = port.perceive(Percept(PerceptType.SENSOR,packed,"SYNTHETIC",1L))
            val stateBytes = ByteArray(d*8)
            full.state.forEachIndexed { i, number ->
                var bits = number.toRawBits()
                for (b in 0 until 8) {
                    stateBytes[i*8+b] = (bits and 255).toByte()
                    bits = bits ushr 8
                }
            }
            val expected = java.security.MessageDigest.getInstance("SHA-256")
                .digest(stateBytes).joinToString("") { "%02x".format(it) }
            check(observed.stateDigest == expected && observed.action == null)
            check(port.lastTrace?.skippedBlocks == 1)
            index.dropScope("test-s4")
            check(index.eligibleForS4("test-s4", 256).status == SemanticStatus.DENIED)
        }
        println("UNO_F_REFERENCE_HOST_PASS=$pass")
    }
}
fun main() { UnoFReferenceTest.run() }
