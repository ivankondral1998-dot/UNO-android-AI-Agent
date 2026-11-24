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
    internal fun weights(rec: Boolean = false, memory: Boolean = false) : UnoRefWeights {
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
            val key=DoubleArray(128);key[0]=1.0
            val neg=DoubleArray(128);neg[0]=-1.0
            val v1=DoubleArray(128);v1[0]=0.8
            val v2=DoubleArray(128);v2[0]=-0.8
            val out=UnoFReference(weights(memory=true)).forward(event(memory=listOf(
                UnoRefMemoryVector(key,v1),UnoRefMemoryVector(neg,v2))),
                booleanArrayOf(true,true),1,memoryTemperature=1e-5)
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
            check(requireNotNull(result.untrustedModelState).length == 64)
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
                booleanArrayOf(true, false), 1, UnoMemoryPorts(exact, semantic), { S4Access("notes", 5L, 0L, 256) }))
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
        test("s6_matrix_budget_matches_actual_a_c_b_trace") {
            val sampler = UnoS6Sampler(blocks=2, branchCount=2, blockWidth=64, hidden=256)
            val model = UnoFReference(weights())
            for (q in 1..2) for (steps in 1..2) {
                val mask = booleanArrayOf(true, q == 2)
                val trace = model.forward(event(0.0), mask, steps).trace
                val realMac = trace.aCalls.toLong() * 256 * 128 +
                    trace.cCalls.toLong() * 256 * 128 + trace.bCalls.toLong() * 64 * 256
                val estimated = sampler.estimatedCost(q, steps)
                check(estimated.first == realMac) {
                    "q=$q steps=$steps estimate=${estimated.first} real=$realMac"
                }
                val expectedBytes = q.toLong() * 2L * (2L * 256 * 128 + 64L * 256) * 8L
                check(estimated.second == expectedBytes)
            }
            check(sampler.estimatedCost(1, 1).first == 163_840L)
            check(sampler.estimatedCost(1, 2).first == 262_144L)
            check(sampler.estimatedCost(2, 1).first == 327_680L)
        }
        test("s6_exact_mac_boundary_and_inner_step_admission") {
            val sampler = UnoS6Sampler(blocks=2, branchCount=2, blockWidth=64, hidden=256,
                epsilon=0.0)
            val ampleBytes = 10_000_000L
            check(sampler.feasible(UnoS6Budget(163_839L, ampleBytes)).isEmpty())
            check(sampler.feasible(UnoS6Budget(163_840L, ampleBytes)).contentEquals(intArrayOf(1)))
            check(sampler.feasible(UnoS6Budget(327_679L, ampleBytes)).contentEquals(intArrayOf(1)))
            check(sampler.feasible(UnoS6Budget(327_680L, ampleBytes)).contentEquals(intArrayOf(1,2)))
            val sel = sampler.select(doubleArrayOf(0.0, 0.0), 0,
                UnoS6Budget(163_840L, ampleBytes, maxInnerSteps=8), seed=5, counter=0,
                hazard=0.0)
            check(!sel.aborted && sel.q == 1 && sel.steps == 1)
            val twoSteps = sampler.select(doubleArrayOf(0.0, 0.0), 0,
                UnoS6Budget(262_144L, ampleBytes, maxInnerSteps=2), seed=5, counter=0,
                hazard=0.0)
            check(!twoSteps.aborted && twoSteps.q == 1 && twoSteps.steps == 2)
        }
        test("s6_bytes_and_overflow_fail_closed") {
            val sampler = UnoS6Sampler(blocks=2, branchCount=2, blockWidth=64, hidden=256)
            val bytes = sampler.estimatedCost(1,1).second
            check(bytes == 1_310_720L)
            check(sampler.feasible(UnoS6Budget(500_000L, bytes-1)).isEmpty())
            check(sampler.feasible(UnoS6Budget(500_000L, bytes)).contentEquals(intArrayOf(1)))
            val huge = UnoS6Sampler(blocks=1, branchCount=Int.MAX_VALUE,
                blockWidth=Int.MAX_VALUE, hidden=Int.MAX_VALUE)
            check(huge.estimatedCost(1,1).first == Long.MAX_VALUE)
            check(huge.estimatedCost(1,1).second == Long.MAX_VALUE)
            check(huge.feasible(UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE)).isEmpty())
            val refused = huge.select(doubleArrayOf(0.0), 0,
                UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE),seed=0,counter=0)
            check(refused.aborted)
        }
        test("s6_empty_feasible_is_budget_abort") {
            val sampler = UnoS6Sampler(blocks=2, branchCount=2, blockWidth=64, hidden=256)
            val budget = UnoS6Budget(maxMac=0, maxBytes=0)
            val sel = sampler.select(doubleArrayOf(0.0, 0.0), 0, budget, seed=1, counter=0)
            check(sel.aborted && sel.q == 0 && sel.steps == 0)
        }
        test("s6_reproducible_same_seed_counter") {
            val sampler = UnoS6Sampler(blocks=4, branchCount=2, blockWidth=32, hidden=128)
            val budget = UnoS6Budget(maxMac=1_000_000_000, maxBytes=1_000_000_000)
            val logits = doubleArrayOf(0.1, -0.2, 0.3, 0.0)
            val a = sampler.select(logits, 3, budget, seed=42, counter=7)
            val b = sampler.select(logits, 3, budget, seed=42, counter=7)
            check(!a.aborted && a.q == b.q && a.steps == b.steps && a.mask.contentEquals(b.mask))
            check(a.q in 1..4 && a.mask.count { it } == a.q)
        }
        test("s6_selected_mask_skips_inactive_kernels") {
            val sampler = UnoS6Sampler(blocks=2, branchCount=2, blockWidth=64, hidden=256)
            val budget = UnoS6Budget(maxMac=1_000_000_000, maxBytes=1_000_000_000, maxInnerSteps=3)
            val sel = sampler.select(doubleArrayOf(0.5, 0.5), 0, budget, seed=1, counter=0)
            check(!sel.aborted && sel.q >= 1)
            val out = UnoFReference(weights()).forward(
                event(0.0), sel.mask, sel.steps
            )
            val active = sel.mask.count { it }
            check(out.trace.skippedBlocks == 2 - active)
            check(out.trace.aCalls == sel.steps * active * 2)
            check(out.trace.cCalls == active * 2)
            check(out.trace.bCalls == sel.steps * active * 2)
        }
        test("s6_full_and_prefix_differ_in_mac_and_state") {
            val full = booleanArrayOf(true, true)
            val prefix = booleanArrayOf(true, false)
            val w = weights()
            val model = UnoFReference(w)
            val fullOut = model.forward(event(0.3), full, 2)
            val prefOut = model.forward(event(0.3), prefix, 2)
            check(fullOut.trace.aCalls > prefOut.trace.aCalls)
            check(prefOut.trace.skippedBlocks == 1)
            check(fullOut.trace.aCalls != prefOut.trace.aCalls || !fullOut.state.contentEquals(prefOut.state))
        }
        test("s6_v2_seed_sweep_regression_and_replay") {
            val sampler = UnoS6Sampler(2, 2, 64, 256)
            val budget = UnoS6Budget(327_680, 3_000_000, 1)
            var count = 0
            for (seed in 0L..4095L) {
                val sel = sampler.select(doubleArrayOf(0.0, -8.0), 0, budget, seed, 0)
                if (sel.q == 1) count++
                check(sel.counter == 2L && sel.startCounter == 0L && sel.rngVersion == UnoS6Prng.VERSION)
            }
            val observed = count / 4096.0
            val target = .025 + .95 / (1.0 + kotlin.math.exp(-8.0 / kotlin.math.sqrt(2.0)))
            println("S6_V2_SEED_SWEEP q1=$count/4096 observed=$observed ideal=$target")
            check(abs(observed - target) < .015)
            val rng = UnoS6Prng(0, 0)
            check(rng.nextWord() == 0xE220A8397B1DCDAFUL.toLong())
            check(rng.nextWord() == 0x6E789E6AA1B965F4UL.toLong())
            val resumed = UnoS6Prng(0, rng.counter)
            check(rng.nextWord() == resumed.nextWord() && rng.counter == resumed.counter)
            val distinct = (0L..4095L).map { UnoS6Prng(it, 0).nextWord() }.toSet()
            check(distinct.size == 4096)
        }
        test("s6_v2_finite_prefix_and_temperature") {
            val budget = UnoS6Budget(500_000, 4_000_000, 1)
            fails { UnoS6Sampler(2,2,64,256,temperature=Double.POSITIVE_INFINITY) }
            fails { UnoS6Sampler(2,2,64,256).select(doubleArrayOf(1e308,1e308),0,budget,1,0) }
            // Prefix sums remain finite but q=1 and q=4 scores differ by > MAX_DOUBLE.
            fails { UnoS6Sampler(4,2,64,256).select(doubleArrayOf(-1.7e308,1.7e308,1.7e308,0.0),0,
                UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE,1),1,0) }
            val sampler = UnoS6Sampler(2,2,64,256,epsilon=0.0)
            val result = sampler.select(doubleArrayOf(-1000.0,1000.0),0,budget,1,0)
            check(result.q == 2)
            check(sampler.select(doubleArrayOf(1000.0,-1000.0),1,budget,1,0).mask.contentEquals(booleanArrayOf(true,true)))
        }
        test("s6_v2_half_open_cdf_and_unbiased_integer") {
            check(unoS6CdfIndex(doubleArrayOf(0.0,1.0),0.0)==1)
            check(unoS6CdfIndex(doubleArrayOf(1.0,1.0),0.5)==1)
            check(unoS6CdfIndex(doubleArrayOf(1.0,0.0),Math.nextDown(1.0))==0)
            var count=0
            val words=longArrayOf(0,1,2,3)
            check(unoS6UniformIndex(3) { words[count++] } == 1 && count == 2)
            count=0
            val ex=runCatching { unoS6UniformIndex(3) { count++; 0L } }.exceptionOrNull()
            check(ex?.message=="S6_REJECTION_BUDGET_ABORT" && count==32)
        }
        test("s6_v2_counter_never_wraps") {
            val rng = UnoS6Prng(7,Long.MAX_VALUE-1)
            rng.nextWord()
            check(rng.counter==Long.MAX_VALUE)
            check(runCatching { rng.nextWord() }.exceptionOrNull()?.message=="S6_RNG_COUNTER_EXHAUSTED")
            check(rng.counter==Long.MAX_VALUE)
            val sampler=UnoS6Sampler(2,2,64,256)
            val b=UnoS6Budget(163_840,1_310_720,8)
            val sel=sampler.select(doubleArrayOf(0.0,0.0),0,b,7,Long.MAX_VALUE)
            check(sel.q==1 && sel.steps==1 && sel.counter==Long.MAX_VALUE && sel.stopReason==UnoS6StopReason.NEXT_STEP_BUDGET)
        }
        test("s6_v2_actual_post_step_state_hazard") {
            val model=UnoFReference(weights())
            val input=event(0.0,1.0)
            val seen=mutableListOf<Double>()
            val out=model.forwardAdaptive(input,UnoS6Budget(262_144+98_304,1_310_720,3),0,1,7,
                logits={ h,z -> near(h[0],0.5); near(z[0],0.0); doubleArrayOf(0.0,0.0) },
                hazard={ h -> seen.add(h[0]); if(h[0]<=0.125) 1.0 else 0.0 })
            check(seen==listOf(0.25,0.125))
            check(out.selection.steps==2 && out.selection.q==1 && out.selection.counter==7L)
            check(out.selection.stopReason==UnoS6StopReason.HAZARD)
            val fixed=model.forward(input,booleanArrayOf(true,false),2)
            val output = requireNotNull(out.output)
            check(output.state.contentEquals(fixed.state) && output.trace==fixed.trace)
            check(output.trace.aCalls==4 && output.trace.cCalls==2 && output.trace.bCalls==4)
        }
        test("s6_v2_budget_forced_stop_before_hazard") {
            val model=UnoFReference(weights())
            var logitsCalls=0
            val abort=model.forwardAdaptive(event(),UnoS6Budget(163_839,1_310_720),0,1,3,
                logits={_,_->logitsCalls++;error("must not run")},hazard={error("must not run")})
            check(abort.output==null && abort.selection.aborted && abort.selection.counter==3L && logitsCalls==0)
            val out=model.forwardAdaptive(event(),UnoS6Budget(163_840,1_310_720),0,1,3,
                logits={_,_->logitsCalls++;doubleArrayOf(0.0,0.0)},hazard={error("forced stop must not draw")})
            check(logitsCalls==1 && out.selection.steps==1 && out.selection.counter==3L)
            check(out.selection.stopReason==UnoS6StopReason.NEXT_STEP_BUDGET)
            val output = requireNotNull(out.output)
            check(output.trace.aCalls==2 && output.trace.cCalls==2 && output.trace.bCalls==2)
            val limited=model.forwardAdaptive(event(),UnoS6Budget(163_840,1_310_720,1),0,1,3,
                logits={_,_->doubleArrayOf(0.0,0.0)},hazard={error("forced limit must not draw")})
            check(limited.selection.stopReason==UnoS6StopReason.STEP_LIMIT)
        }
        test("s6_v2_adaptive_invalid_hazard_and_callback_isolation") {
            val model=UnoFReference(weights())
            val input=event(0.0,1.0)
            val b=UnoS6Budget(262_144,1_310_720,2)
            fails { model.forwardAdaptive(input,b,0,1,0,logits={_,_->doubleArrayOf(0.0,0.0)},hazard={Double.NaN}) }
            val out=model.forwardAdaptive(input,b,0,1,0,
                logits={h,z->h.fill(99.0);z.fill(99.0);doubleArrayOf(0.0,0.0)},
                hazard={h->h.fill(99.0);0.0})
            check(out.output!!.state.contentEquals(model.forward(input,booleanArrayOf(true,false),2).state))
            check(out.selection.counter==0L && out.selection.stopReason==UnoS6StopReason.STEP_LIMIT)
            val stochastic=model.forwardAdaptive(input,b,0,1,0,logits={_,_->doubleArrayOf(0.0,0.0)},hazard={0.5})
            check(stochastic.selection.counter==1L)
        }
        test("recovered_s4_all_five_eligible_not_prequery_top4") {
            val exact = ExactMemory()
            val secret = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
            var ciphertext: ByteArray? = null
            val semantic = UnoSemanticMemory(secret, "boot-a", { ciphertext?.copyOf() },
                { ciphertext = it.copyOf() }, 128)
            for (idx in 0 until 5) {
                val entry = exact.write("notes", "fact-$idx", "fact-$idx".toByteArray(),
                    500L, 0L, EntryKind.OBSERVED, "LOCAL_UI")
                val value = DoubleArray(128)
                if (idx == 4) value[0] = 1.0
                semantic.link(entry, value)
            }
            check(semantic.eligibleForS4("notes", 256).hits.size == 5)
            val w = weights(memory=true)
            val plain = UnoFReferencePort(UnoFReference(w), w, booleanArrayOf(true, false), 1)
            val memory = UnoFReferencePort(UnoFReference(w), w,
                booleanArrayOf(true, false), 1, UnoMemoryPorts(exact, semantic), { S4Access("notes", 5L, 0L, 256) })
            val percept = Percept(PerceptType.SENSOR, ByteArray(8), "SYNTHETIC_FEATURES", 5L)
            check(memory.perceive(percept).stateDigest != plain.perceive(percept).stateDigest)
        }
        test("recovered_s4_input_width_one_memory_width_128") {
            val exact = ExactMemory()
            val entry = exact.write("notes", "fact", "x".toByteArray(), 500L, 0L,
                EntryKind.OBSERVED, "LOCAL_UI")
            val secret = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
            var ciphertext: ByteArray? = null
            val semantic = UnoSemanticMemory(secret, "boot-a", { ciphertext?.copyOf() },
                { ciphertext = it.copyOf() }, 128)
            val value = DoubleArray(128); value[0] = 1.0
            semantic.link(entry, value)
            val w = weights(memory=true)
            check(w.inputWidth == 1 && w.m == 128)
            val plain = UnoFReferencePort(UnoFReference(w), w, booleanArrayOf(true, false), 1)
            val memory = UnoFReferencePort(UnoFReference(w), w,
                booleanArrayOf(true, false), 1, UnoMemoryPorts(exact, semantic), { S4Access("notes", 5L, 0L, 256) })
            val bits = 1.0.toRawBits()
            val packed = ByteArray(8) { b -> ((bits ushr (8 * b)) and 0xff).toByte() }
            val percept = Percept(PerceptType.SENSOR, packed, "SYNTHETIC_FEATURES", 5L)
            check(memory.perceive(percept).stateDigest != plain.perceive(percept).stateDigest)
        }
        test("recovered_s4_raw_scan_budget_counts_stale_boot") {
            val exact = ExactMemory()
            val old = exact.write("notes", "old", "old".toByteArray(),
                500L, 0L, EntryKind.OBSERVED, "LOCAL_UI")
            val secret = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
            var ciphertext: ByteArray? = null
            val a = UnoSemanticMemory(secret, "boot-a", { ciphertext?.copyOf() },
                { ciphertext = it.copyOf() }, 128)
            val v = DoubleArray(128); v[0] = 1.0
            a.link(old, v)
            val b = UnoSemanticMemory(secret, "boot-b", { ciphertext?.copyOf() },
                { ciphertext = it.copyOf() }, 128)
            val fresh = exact.write("notes", "new", "new".toByteArray(),
                500L, 0L, EntryKind.OBSERVED, "LOCAL_UI")
            b.link(fresh, v)
            check(b.eligibleForS4("notes", 1).status == S4Status.BUDGET_EXCEEDED)
            check(b.eligibleForS4("notes", 2).hits.single().exactId == fresh.id)
            check(b.eligibleForS4("other", 2).status == S4Status.EMPTY)
        }
        println("UNO_F_REFERENCE_HOST_PASS=$pass")
    }
}
fun main() { UnoFReferenceTest.run() }
