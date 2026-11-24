package org.unovyra.uno.core

import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.sqrt
import kotlin.math.tanh

/**
 * UNO B2 S4/S5 NUMERICAL ORACLE, not a loaded model, policy, runtime authority,
 * decoder, S6 sampler, or released weight ABI. Double arithmetic deliberately
 * distinguishes this host reference from the required FP32 Android kernel.
 *
 * Synthetic dimensions (e.g. d=128) may be used for equation tests. They are NOT
 * approved B2 architecture choices or trained parameter checkpoints.
 */
class UnoRefMatrix(val rows: Int, val cols: Int, values: DoubleArray) {
    private val numbers = values.copyOf()
    init {
        require(rows > 0 && cols > 0 && rows.toLong() * cols == numbers.size.toLong())
        require(numbers.all(Double::isFinite)) { "NONFINITE_WEIGHTS" }
    }
    operator fun get(row: Int, col: Int): Double = numbers[row * cols + col]
    fun multiply(vector: DoubleArray): DoubleArray = multiply(vector, null, "")
    internal fun multiply(vector: DoubleArray, meter: RefCycleMeter?, kernel: String): DoubleArray {
        require(vector.size == cols && vector.all(Double::isFinite)) { "BAD_VECTOR" }
        meter?.enter(kernel, rows.toLong() * cols)
        val result = DoubleArray(rows)
        for (r in 0 until rows) {
            var sum = 0.0
            val offset = r * cols
            for (c in 0 until cols) sum += numbers[offset + c] * vector[c]
            result[r] = sum
        }
        require(result.all(Double::isFinite)) { "NONFINITE_MATRIX_RESULT" }
        return result
    }
    /** Outward bound of real row-L1 norm of decoded binary64 values. */
    internal fun decodedRowL1Upper(): Double {
        var largest = 0.0
        for (r in 0 until rows) {
            var sum = 0.0
            for (c in 0 until cols) sum = stabilityAdd(sum, abs(get(r, c)))
            largest = maxOf(largest, sum)
        }
        return largest
    }
    fun rowL1Within(limit: Double): Boolean = (0 until rows).all { row ->
        var sum = 0.0
        for (col in 0 until cols) sum += abs(get(row, col))
        sum.isFinite() && sum <= limit + 1e-10
    }
}

class UnoRefBranch(
    val a: UnoRefMatrix, val c: UnoRefMatrix, val b: UnoRefMatrix,
    inputBias: DoubleArray, outputBias: DoubleArray
) {
    private val aBiasData = inputBias.copyOf()
    private val bBiasData = outputBias.copyOf()
    val aBias: DoubleArray get() = aBiasData.copyOf()
    val bBias: DoubleArray get() = bBiasData.copyOf()
    internal fun aBiasAt(i: Int) = aBiasData[i]
    internal fun bBiasAt(i: Int) = bBiasData[i]
    internal fun biasSizesValid(hidden: Int, blockWidth: Int): Boolean =
        aBiasData.size == hidden && bBiasData.size == blockWidth &&
        aBiasData.all { it.isFinite() && abs(it) <= 8.0 } &&
        bBiasData.all { it.isFinite() && abs(it) <= 8.0 }
}

class UnoRefWeights(
    val version: String,
    val projection: UnoRefMatrix,
    val us: UnoRefMatrix,
    val ug: UnoRefMatrix,
    val meta: UnoRefMatrix,
    modalityEmbedding: DoubleArray,
    zBias: DoubleArray,
    val wq: UnoRefMatrix,
    val wr: UnoRefMatrix,
    branches: List<List<UnoRefBranch>>
) {
    val branches: List<List<UnoRefBranch>> = java.util.Collections.unmodifiableList(
        branches.map { java.util.Collections.unmodifiableList(it.toList()) })
    val d: Int = projection.rows
    val inputWidth: Int = projection.cols
    val m: Int = wq.rows
    val blockWidth: Int = 64
    val expansion: Int = 4
    val branchCount: Int = 2
    private val embedding = modalityEmbedding.copyOf()
    private val zBiasData = zBias.copyOf()
    val e: DoubleArray get() = embedding.copyOf()
    val bias: DoubleArray get() = zBiasData.copyOf()
    internal fun eAt(i: Int) = embedding[i]
    internal fun biasAt(i: Int) = zBiasData[i]
    val blocks: Int = d / blockWidth

    init {
        require(version.isNotBlank() && version.length <= 128)
        require(d > 0 && d % blockWidth == 0 && m == 128 &&
            us.rows == d && us.cols == d && ug.rows == d && ug.cols == d &&
            meta.rows == d && meta.cols == 32 && wq.cols == d &&
            wr.rows == d && wr.cols == m && embedding.size == d && zBiasData.size == d &&
            embedding.all(Double::isFinite) && zBiasData.all(Double::isFinite)) { "B2_S4_SHAPE_INVALID" }
        require(branches.size == branchCount && branches.all { it.size == blocks }) {
            "B2_S5_BRANCH_LAYOUT_INVALID"
        }
        val hidden = expansion * blockWidth
        for (branch in branches) for (kernel in branch) {
            require(kernel.a.rows == hidden && kernel.a.cols == d &&
                kernel.c.rows == hidden && kernel.c.cols == d &&
                kernel.b.rows == blockWidth && kernel.b.cols == hidden &&
                kernel.biasSizesValid(hidden, blockWidth)) {
                "B2_S5_SHAPE_INVALID"
            }
            require(kernel.a.rowL1Within(1.0) && kernel.c.rowL1Within(2.0) &&
                kernel.b.rowL1Within(0.9)) { "B2_RECURRENCE_NORM_INVALID" }
        }
        require(us.rowL1Within(1.0) && ug.rowL1Within(1.0) &&
            wq.rowL1Within(2.0) && wr.rowL1Within(2.0) &&
            projection.rowL1Within(8.0) && meta.rowL1Within(8.0) &&
            embedding.all { abs(it) <= 1.0 } && zBiasData.all { abs(it) <= 1.0 }) {
            "B2_S4_NORM_INVALID"
        }
    }
}

/** A semantic representation only. Never an exact observation or verified OS receipt. */
class UnoRefMemoryVector(key: DoubleArray, value: DoubleArray) {
    val key = key.copyOf()
    val value = value.copyOf()
}

/** Caller provides one projected-modality input with fixed metadata slots. */
class UnoRefEvent(
    features: DoubleArray, metadata: DoubleArray, state: DoubleArray,
    goal: DoubleArray, memory: List<UnoRefMemoryVector> = emptyList()
) {
    val features = features.copyOf()
    val metadata = metadata.copyOf()
    val state = state.copyOf()
    val goal = goal.copyOf()
    val memory = memory.toList()
}

data class UnoRefKernelTrace(
    val aCalls: Int, val cCalls: Int, val bCalls: Int, val skippedBlocks: Int,
    val innerSteps: Int, val activeBlocks: Int
)

class UnoRefOutput(state: DoubleArray, val trace: UnoRefKernelTrace) {
    val state: DoubleArray = state.copyOf()
}

/** S6 geometry only: NOT a sampling policy or a learned selector. */
fun unoCyclicPrefixMask(blocks: Int, selected: Int, turnSerial: Long): BooleanArray {
    require(blocks > 0 && selected in 1..blocks && turnSerial >= 0)
    val mask = BooleanArray(blocks)
    val shift = (turnSerial % blocks).toInt()
    for (j in 0 until selected) mask[((j.toLong() + shift) % blocks).toInt()] = true
    return mask
}

/**
 * S6 feasible catalogue and sampling. Geometry remains unoCyclicPrefixMask.
 * Empty feasible set is BUDGET_ABORT, never a fabricated q=0.
 * Sampling uses the Astra ε-mixture + softmax on prefix scores with a recorded PRNG.
 */
class UnoS6Budget(
    val maxMac: Long,
    val maxBytes: Long,
    val maxInnerSteps: Int = 8
) {
    init {
        require(maxMac >= 0 && maxBytes >= 0 && maxInnerSteps in 1..8)
    }
}

data class UnoS6Selection(
    val q: Int,
    val mask: BooleanArray,
    val steps: Int,
    val seed: Long,
    val counter: Long,
    val aborted: Boolean = false,
    val rngVersion: String = UnoS6Prng.VERSION,
    val startCounter: Long = counter,
    val stopReason: UnoS6StopReason = if (aborted) UnoS6StopReason.BUDGET_ABORT else UnoS6StopReason.STEP_LIMIT
)

enum class UnoS6StopReason { BUDGET_ABORT, STEP_LIMIT, NEXT_STEP_BUDGET, HAZARD }

data class UnoS6Execution(val selection: UnoS6Selection, val output: UnoRefOutput?)

class UnoS6Sampler(
    private val blocks: Int,
    private val branchCount: Int,
    private val blockWidth: Int,
    private val hidden: Int,
    private val epsilon: Double = 0.05,
    private val temperature: Double = 1.0
) {
    init {
        require(blocks > 0 && branchCount > 0 && blockWidth > 0 && hidden > 0)
        require(epsilon in 0.0..1.0 && temperature.isFinite() && temperature > 0.0)
    }

    // Saturation is a rejection signal, not a finite cost: never admit MAX_VALUE.
    private fun satMul(a: Long, b: Long): Long {
        require(a >= 0 && b >= 0)
        return if (b != 0L && a > Long.MAX_VALUE / b) Long.MAX_VALUE else a * b
    }
    private fun satAdd(a: Long, b: Long): Long {
        require(a >= 0 && b >= 0)
        return if (a > Long.MAX_VALUE - b) Long.MAX_VALUE else a + b
    }

    /**
     * Cost of S5/S6 *matrix multiplications only*, matching UnoFReference.forward:
     * C*z runs once per admitted block/branch; A*h and B*activated run per inner step.
     * maxBytes limits the nominal FP64 coefficient footprint for selected blocks,
     * NOT allocated RAM (all weight arrays can already be resident) or physical
     * read traffic. Caller accounts for S4, selector,
     * heads, activations and Android separately when enforcing a full-cycle budget.
     */
    fun estimatedCost(q: Int, steps: Int): Pair<Long, Long> {
        require(q in 1..blocks && steps in 1..8)
        val stateWidth = blocks.toLong() * blockWidth.toLong()
        val hd = satMul(hidden.toLong(), stateWidth)
        val bh = satMul(blockWidth.toLong(), hidden.toLong())
        val calls = satMul(q.toLong(), branchCount.toLong())
        val perBranchMac = satAdd(hd, satMul(steps.toLong(), satAdd(hd, bh)))
        val mac = satMul(calls, perBranchMac)
        val matrixElementsPerBranch = satAdd(satMul(2L, hd), bh)
        val matrixBytes = satMul(satMul(calls, matrixElementsPerBranch), 8L)
        return mac to matrixBytes
    }

    fun feasible(budget: UnoS6Budget): IntArray {
        val out = ArrayList<Int>()
        for (q in 1..blocks) {
            val (mac, bytes) = estimatedCost(q, 1)
            if (mac != Long.MAX_VALUE && bytes != Long.MAX_VALUE &&
                mac <= budget.maxMac && bytes <= budget.maxBytes && budget.maxInnerSteps >= 1) {
                out.add(q)
            }
        }
        return out.toIntArray()
    }

    internal fun admits(q: Int, steps: Int, budget: UnoS6Budget): Boolean {
        if (steps !in 1..budget.maxInnerSteps) return false
        val (mac, bytes) = estimatedCost(q, steps)
        return mac != Long.MAX_VALUE && bytes != Long.MAX_VALUE &&
            mac <= budget.maxMac && bytes <= budget.maxBytes
    }

    /** Single checked prefix scan, before any RNG draw. Zero means empty catalogue. */
    internal fun choosePrefix(logits: DoubleArray, turnSerial: Long,
                              budget: UnoS6Budget, rng: UnoS6Prng): Int {
        require(logits.size == blocks && logits.all(Double::isFinite) && turnSerial >= 0)
        val catalogue = feasible(budget)
        if (catalogue.isEmpty()) return 0
        val probabilities = prefixWeights(logits, turnSerial, catalogue)
        if (catalogue.size == 1) return catalogue[0]
        val explore = rng.nextDouble() < epsilon
        return if (explore) catalogue[rng.nextInt(catalogue.size)]
        else catalogue[unoS6CdfIndex(probabilities, rng.nextDouble())]
    }

    /** Same unnormalized weights as runtime; catalogue from feasible(budget).
     * Diagnostic parity hook, no additional inference arrays or RNG words. */
    internal fun prefixWeights(logits: DoubleArray, turnSerial: Long,
                               catalogue: IntArray): DoubleArray {
        val shift = (turnSerial % blocks).toInt()
        val scores = DoubleArray(catalogue.size)
        var sum = 0.0
        var index = 0
        for (j in 0 until catalogue.last()) {
            sum += logits[((j.toLong() + shift) % blocks).toInt()]
            require(sum.isFinite()) { "S6_INVALID_PREFIX_SUM" }
            if (j + 1 == catalogue[index]) {
                scores[index++] = sum / sqrt((j + 1).toDouble())
            }
        }
        val largest = scores.maxOrNull()!!
        return DoubleArray(scores.size) { i ->
            val delta = scores[i] - largest
            require(delta.isFinite()) { "S6_INVALID_SCORE_DIFFERENCE" }
            exp(delta / temperature)
        }
    }

    internal fun stopAfterStep(q: Int, steps: Int, budget: UnoS6Budget,
                              rng: UnoS6Prng, hazard: () -> Double): UnoS6StopReason? {
        if (steps == budget.maxInnerSteps) return UnoS6StopReason.STEP_LIMIT
        if (!admits(q, steps + 1, budget)) return UnoS6StopReason.NEXT_STEP_BUDGET
        val p = hazard()
        require(p.isFinite() && p in 0.0..1.0) { "S6_INVALID_HAZARD" }
        return if (p == 1.0 || (p > 0.0 && rng.nextDouble() < p)) UnoS6StopReason.HAZARD else null
    }

    /** Compatibility for FIXED hazard experiments only. Not the state-dependent S6 path.
     * counter is now the next random WORD index, not the old decision index.
     * Old traces must not be replayed using this version. */
    fun select(logits: DoubleArray, turnSerial: Long, budget: UnoS6Budget,
               seed: Long, counter: Long, hazard: Double = 0.25): UnoS6Selection {
        require(hazard.isFinite() && hazard in 0.0..1.0)
        val rng = UnoS6Prng(seed, counter)
        val q = choosePrefix(logits, turnSerial, budget, rng)
        if (q == 0) return UnoS6Selection(0, BooleanArray(blocks), 0, seed, counter, true)
        for (steps in 1..budget.maxInnerSteps) {
            val reason = stopAfterStep(q, steps, budget, rng) { hazard }
            if (reason != null) return UnoS6Selection(q, unoCyclicPrefixMask(blocks, q, turnSerial),
                steps, seed, rng.counter, startCounter = counter, stopReason = reason)
        }
        error("S6_STOP_INVARIANT")
    }
}

/** Half-open normalized CDF: zero-mass bins never selected, even at u=0. */
internal fun unoS6CdfIndex(weights: DoubleArray, u: Double): Int {
    require(weights.isNotEmpty() && weights.all { it.isFinite() && it >= 0 } && u >= 0 && u < 1)
    val total = weights.sum()
    require(total.isFinite() && total > 0)
    var sum = 0.0
    for (i in weights.indices) {
        sum += weights[i]
        if (u < sum / total) return i
    }
    error("S6_CDF_INVARIANT")
}

/** Exact uniform integer under the conditional uniform-word assumption.
 * Rejection is bounded; no biased fallback on exhaustion. */
internal fun unoS6UniformIndex(bound: Int, draw: () -> Long): Int {
    require(bound > 0)
    val b = bound.toULong()
    val threshold = (0UL - b) % b
    repeat(32) {
        val x = draw().toULong()
        if (x >= threshold) return (x % b).toInt()
    }
    error("S6_REJECTION_BUDGET_ABORT")
}

/** Versioned SplitMix64 word stream. Deterministic, not a proof of independent entropy.
 * Arithmetic in the mixer wraps modulo 2^64 intentionally; counter NEVER wraps.
 * Each actual word advances counter; forced decisions consume no word. */
class UnoS6Prng(private val seed: Long, counter: Long) {
    companion object { const val VERSION = "S6_SPLITMIX64_WORD_V2" }
    var counter: Long = counter
        private set
    init { require(seed >= 0 && counter >= 0) }
    fun nextWord(): Long {
        check(counter < Long.MAX_VALUE) { "S6_RNG_COUNTER_EXHAUSTED" }
        counter++
        var z = seed + counter * 0x9E3779B97F4A7C15UL.toLong()
        z = (z xor (z ushr 30)) * 0xBF58476D1CE4E5B9UL.toLong()
        z = (z xor (z ushr 27)) * 0x94D049BB133111EBUL.toLong()
        return z xor (z ushr 31)
    }
    fun nextDouble(): Double = (nextWord() ushr 11).toDouble() / 9007199254740992.0
    fun nextInt(bound: Int): Int = unoS6UniformIndex(bound, ::nextWord)
}



class UnoFReference(private val weights: UnoRefWeights) {
    /** Offline diagnostic, outside metered inference. */
    internal fun stabilityBounds() = UnoRefStability.from(weights)
    internal val stateWidth get() = weights.d
    internal val memoryWidth get() = weights.m
    internal val featureWidth get() = weights.inputWidth
    internal fun s4Mac(records: Int): Long {
        require(records >= 0)
        val d = weights.d.toLong(); val m = weights.m.toLong()
        return refAdd(refMul(d, weights.inputWidth.toLong()), refMul(2, d, d),
            refMul(32, d), refMul(2, m, d), refMul(2, records.toLong(), m))
    }
    internal fun reserveCycle(meter: RefCycleMeter, budget: UnoS6Budget, scanBudget: Int,
                              goalMode: Boolean) {
        val d = weights.d.toLong(); val m = weights.m.toLong(); val b = weights.blockWidth.toLong()
        val h = weights.expansion * b; val n = weights.blocks.toLong(); val j = weights.branchCount.toLong()
        val k = budget.maxInnerSteps.toLong(); val r = if (goalMode) 0L else scanBudget.toLong()
        val sampler = UnoS6Sampler(weights.blocks, weights.branchCount, weights.blockWidth, h.toInt())
        val (minMac, minBytes) = sampler.estimatedCost(1, 1)
        if (minMac > budget.maxMac || minBytes > budget.maxBytes || minMac == Long.MAX_VALUE)
            throw RefCycleAbort(RefSessionStatus.BUDGET_ABORT)
        // Entire model is resident, not merely selected coefficients. Repeated references
        // to a shared matrix overcount, which is conservative for numeric payload.
        val resident = refAdd(s4Mac(0), refMul(2,d),
            refMul(j,n,refAdd(refMul(2,h,d),refMul(b,h),h,b)))
        // Conservative sum of explicit primitive-array payloads, NOT JVM heap.
        // 6*(D+32): external input + two snapshots + three validation concatenations.
        // 32*d: resident session state/goal, event state/goal copies, temporary GOAL
        // arrays, concatenations, projections, z0/z/h, head args and final copies.
        // 8*m: query/read; 4*r*m: two catalogue copies and key/value event copies.
        // 8*n: selector arrays/mask; J*n*H: cache; per step next/average/hazard
        // copy plus A/activation/B arrays. Treat Int/Boolean as 8 bytes conservatively.
        val vectors = refAdd(refMul(6,refAdd(weights.inputWidth.toLong(),32)),
            refMul(32,d),refMul(8,m),refMul(8,n),refMul(4,r,m),refMul(j,n,h),
            refMul(k,refAdd(refMul(3,d),refMul(j,n,refAdd(refMul(2,h),b)))))
        val numeric = refMul(8,refAdd(resident,vectors))
        // Scalar admission units: conservative quota for numeric validation,
        // elementwise activation/mixing, selection/control and logical scan visits.
        // MAC loop internals, object allocations, external head/hash/IO are excluded.
        val scalar = refAdd(refMul(64,vectors),refMul(1024,n+1),4096)
        meter.reserve(refAdd(s4Mac(0),minMac),scalar,numeric,refMul(2,r))
    }
    fun forward(
        event: UnoRefEvent, mask: BooleanArray, steps: Int,
        alpha: Double = 0.5, rho: Double = 0.5,
        memoryTemperature: Double = 1.0
    ): UnoRefOutput {
        val activeMask = mask.copyOf()
        require(activeMask.size == weights.blocks && activeMask.any { it }) { "B2_MASK_INVALID" }
        require(steps in 1..8) { "B2_OPTIONS_INVALID" }
        val (z, h) = prepare(event, alpha, rho, memoryTemperature)
        return recur(z, h, activeMask, alpha) { k, _ -> k == steps }
    }

    /** Actual state-dependent S6 on the host reference. Select after S4, pay each
     * matrix step before execution, then evaluate hazard on resulting state.
     * Caller supplies untrained head functions: this is NOT an admitted weight ABI.
     * Only S5/S6 matrix budget is enforced here. Exceptions publish no output. */
    fun forwardAdaptive(
        event: UnoRefEvent, budget: UnoS6Budget, turnSerial: Long,
        seed: Long, counter: Long,
        logits: (DoubleArray, DoubleArray) -> DoubleArray,
        hazard: (DoubleArray) -> Double,
        epsilon: Double = 0.05, temperature: Double = 1.0,
        alpha: Double = 0.5, rho: Double = 0.5, memoryTemperature: Double = 1.0
    ): UnoS6Execution = forwardAdaptiveMetered(event, budget, turnSerial, seed, counter, logits, hazard,
        epsilon, temperature, alpha, rho, memoryTemperature, null)

    internal fun forwardAdaptiveMetered(
        event: UnoRefEvent, budget: UnoS6Budget, turnSerial: Long,
        seed: Long, counter: Long,
        logits: (DoubleArray, DoubleArray) -> DoubleArray,
        hazard: (DoubleArray) -> Double,
        epsilon: Double = 0.05, temperature: Double = 1.0,
        alpha: Double = 0.5, rho: Double = 0.5, memoryTemperature: Double = 1.0, meter: RefCycleMeter?
    ): UnoS6Execution {
        require(turnSerial >= 0)
        val sampler = UnoS6Sampler(weights.blocks, weights.branchCount, weights.blockWidth,
            weights.expansion * weights.blockWidth, epsilon, temperature)
        val rng = UnoS6Prng(seed, counter)
        if (!sampler.admits(1, 1, budget)) return UnoS6Execution(
            UnoS6Selection(0, BooleanArray(weights.blocks), 0, seed, counter, true), null)
        meter?.ensureMac(refAdd(s4Mac(event.memory.size), sampler.estimatedCost(1, 1).first))
        val (z, h) = prepare(event, alpha, rho, memoryTemperature, meter)
        val effectiveBudget = if (meter == null) budget else UnoS6Budget(
            minOf(budget.maxMac, meter.remainingMac), budget.maxBytes, budget.maxInnerSteps)
        meter?.head()
        val rawLogits = logits(h.copyOf(), z.copyOf())
        meter?.checkpoint()
        val q = sampler.choosePrefix(rawLogits, turnSerial, effectiveBudget, rng)
        check(q > 0 && sampler.admits(q, 1, effectiveBudget)) { "S6_ADMISSION_INVARIANT" }
        val mask = unoCyclicPrefixMask(weights.blocks, q, turnSerial)
        var reason: UnoS6StopReason? = null
        val output = recur(z, h, mask, alpha, meter) { k, state ->
            meter?.checkpoint()
            reason = sampler.stopAfterStep(q, k, effectiveBudget, rng) {
                meter?.head()
                hazard(state.copyOf()).also { meter?.checkpoint() }
            }
            reason != null
        }
        return UnoS6Execution(UnoS6Selection(q, mask, output.trace.innerSteps, seed,
            rng.counter, startCounter = counter, stopReason = checkNotNull(reason)), output)
    }

    private fun prepare(event: UnoRefEvent, alpha: Double, rho: Double,
                        memoryTemperature: Double, meter: RefCycleMeter? = null): Pair<DoubleArray, DoubleArray> {
        val d = weights.d
        val m = weights.m
        require(event.features.size == weights.inputWidth && event.metadata.size == 32 &&
            event.state.size == d && event.goal.size == d &&
            (event.features + event.metadata + event.state + event.goal).all(Double::isFinite)) {
            "B2_INPUT_INVALID"
        }
        require(event.state.all { it in -1.0..1.0 } && event.goal.all { it in -1.0..1.0 }) { "B2_STATE_OUTSIDE_CUBE" }
        require(alpha.isFinite() && alpha in 0.0..1.0 &&
            rho.isFinite() && rho in 0.0..1.0 &&
            memoryTemperature.isFinite() && memoryTemperature > 0.0) { "B2_OPTIONS_INVALID" }
        for (entry in event.memory) {
            require(entry.key.size == m && entry.value.size == m &&
                entry.key.all { it in -1.0..1.0 } && entry.value.all { it in -1.0..1.0 }) {
                "B2_SEMANTIC_VECTOR_INVALID"
            }
        }

        // S4: CURRENT input must reach the query before semantic retrieval.
        val input = weights.projection.multiply(event.features, meter, "S4_projection")
        val sIn = weights.us.multiply(event.state, meter, "S4_us")
        val gIn = weights.ug.multiply(event.goal, meter, "S4_ug")
        val mIn = weights.meta.multiply(event.metadata, meter, "S4_meta")
        val z0 = DoubleArray(d) { i ->
            tanh(input[i] + sIn[i] + gIn[i] + mIn[i] + weights.eAt(i) + weights.biasAt(i))
        }
        val q = weights.wq.multiply(z0, meter, "S4_wq").map(::tanh).toDoubleArray()
        val read = DoubleArray(m)
        if (event.memory.isNotEmpty()) {
            meter?.enter("S4_scores", event.memory.size.toLong() * m)
            val scores = event.memory.map { entry ->
                var dot = 0.0
                for (i in 0 until m) dot += q[i] * entry.key[i]
                (dot / sqrt(m.toDouble())) / memoryTemperature
            }
            require(scores.all(Double::isFinite)) { "B2_SCORE_INVALID" }
            val largest = scores.maxOrNull()!!
            val exponentials = scores.map { exp(it - largest) }
            val total = exponentials.sum()
            require(total.isFinite() && total > 0.0) { "B2_SOFTMAX_INVALID" }
            meter?.enter("S4_read", event.memory.size.toLong() * m)
            for (idx in event.memory.indices) {
                val weight = exponentials[idx] / total
                for (i in 0 until m) read[i] += weight * event.memory[idx].value[i]
            }
        }
        val projectedRead = weights.wr.multiply(read, meter, "S4_wr")
        val z = DoubleArray(d) { i -> tanh(z0[i] + projectedRead[i]) }
        val h = DoubleArray(d) { i -> rho * event.state[i] + (1.0 - rho) * z[i] }
        require(h.all(Double::isFinite)) { "B2_STATE_INVALID" }
        return z to h
    }

    private fun recur(z: DoubleArray, initial: DoubleArray, mask: BooleanArray,
                      alpha: Double, meter: RefCycleMeter? = null, stop: (Int, DoubleArray) -> Boolean): UnoRefOutput {
        var h = initial
        var aCalls = 0
        var cCalls = 0
        var bCalls = 0
        var steps = 0
        // Precompute C_j z only for admitted blocks. No C/A/B calls for masked blocks.
        val cz = Array(weights.branchCount) { branch ->
            Array(weights.blocks) { block ->
                if (mask[block]) {
                    cCalls = Math.incrementExact(cCalls)
                    weights.branches[branch][block].c.multiply(z, meter, "S5_C")
                } else DoubleArray(0)
            }
        }
        for (step in 1..8) {
            val next = h.copyOf() // Synchronous update from same h^k for ALL blocks.
            for (block in mask.indices) {
                if (!mask[block]) continue
                val average = DoubleArray(weights.blockWidth)
                for (branch in 0 until weights.branchCount) {
                    val kernel = weights.branches[branch][block]
                    aCalls = Math.incrementExact(aCalls)
                    val ah = kernel.a.multiply(h, meter, "S5_A")
                    val activated = DoubleArray(kernel.a.rows) { i ->
                        tanh(ah[i] + cz[branch][block][i] + kernel.aBiasAt(i))
                    }
                    bCalls = Math.incrementExact(bCalls)
                    val raw = kernel.b.multiply(activated, meter, "S5_B")
                    for (j in 0 until weights.blockWidth) {
                        average[j] += tanh(raw[j] + kernel.bBiasAt(j)) / weights.branchCount
                    }
                }
                for (j in 0 until weights.blockWidth) {
                    val i = block * weights.blockWidth + j
                    next[i] = (1.0 - alpha) * h[i] + alpha * average[j]
                }
            }
            require(next.all(Double::isFinite)) { "B2_RECURRENT_RESULT_INVALID" }
            h = next
            steps = step
            if (stop(step, h)) break
        }
        val active = mask.count { it }
        val skipped = weights.blocks - active
        return UnoRefOutput(h, UnoRefKernelTrace(
            aCalls = aCalls,
            cCalls = cCalls,
            bCalls = bCalls,
            skippedBlocks = skipped, innerSteps = steps, activeBlocks = active
        ))
    }
}

/**
 * Host numerical port only. Synthetic weights are not a trained organism.
 * The result never contains an Android proposal. Any other byte layout is
 * rejected the same way as a missing model.
 */
class UnoFReferencePort(
    private val reference: UnoFReference,
    private val weights: UnoRefWeights,
    private val mask: BooleanArray,
    private val steps: Int,
    private val memoryPorts: UnoMemoryPorts? = null,
    private val s4Access: (() -> S4Access)? = null
) : NeuralPort {
    var lastTrace: UnoRefKernelTrace? = null
        private set

    override fun perceive(event: Percept): NeuralOutput {
        lastTrace = null
        val width = weights.inputWidth
        if (event.data.size != width * 8) {
            throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
        }
        val features = DoubleArray(width)
        for (index in 0 until width) {
            var bits = 0L
            for (byte in 0 until 8) {
                bits = bits or ((event.data[index * 8 + byte].toLong() and 0xff) shl (8 * byte))
            }
            val value = Double.fromBits(bits)
            if (!value.isFinite()) throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
            features[index] = value
        }
        var pendingTrace: UnoRefKernelTrace? = null
        fun run(bank: List<UnoRefMemoryVector>): NeuralOutput {
            val output = reference.forward(
                UnoRefEvent(features, DoubleArray(32), DoubleArray(weights.d),
                    DoubleArray(weights.d), bank),
                mask, steps
            )
            pendingTrace = output.trace
            val packed = ByteArray(output.state.size * 8)
            output.state.forEachIndexed { index, value ->
                var bits = value.toRawBits()
                for (byte in 0 until 8) {
                    packed[index * 8 + byte] = (bits and 0xff).toByte()
                    bits = bits ushr 8
                }
            }
            val digest = java.security.MessageDigest.getInstance("SHA-256").digest(packed)
                .joinToString("") { "%02x".format(it) }
            return NeuralOutput(digest, null)
        }
        val ports = memoryPorts
        val access = s4Access
        val result = if (ports == null && access == null) run(emptyList()) else {
            check(ports != null && access != null) { "S4_AUTHORITY_REQUIRED" }
            ports.withS4Bank(access(), weights.m) { bank ->
            check(bank.status == S4Status.COMPLETE || bank.status == S4Status.EMPTY) { "S4_${bank.status}" }
            // Existing synthetic reference representation only; not learned Wk/Wv ABI.
                run(bank.hits.map { UnoRefMemoryVector(it.vector, it.vector.copyOf()) })
            }
        }
        lastTrace = pendingTrace
        return result
    }
}
