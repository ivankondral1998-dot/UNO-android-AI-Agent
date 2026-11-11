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
    fun multiply(vector: DoubleArray): DoubleArray {
        require(vector.size == cols && vector.all(Double::isFinite)) { "BAD_VECTOR" }
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
    val branches: List<List<UnoRefBranch>> = branches.map { it.toList() }
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
    for (j in 0 until selected) mask[(j + shift) % blocks] = true
    return mask
}

class UnoFReference(private val weights: UnoRefWeights) {
    fun forward(
        event: UnoRefEvent, mask: BooleanArray, steps: Int,
        alpha: Double = 0.5, rho: Double = 0.5,
        memoryTemperature: Double = 1.0
    ): UnoRefOutput {
        val d = weights.d
        val m = weights.m
        require(event.features.size == weights.inputWidth && event.metadata.size == 32 &&
            event.state.size == d && event.goal.size == d &&
            (event.features + event.metadata + event.state + event.goal).all(Double::isFinite)) {
            "B2_INPUT_INVALID"
        }
        require(mask.size == weights.blocks && mask.any { it }) { "B2_MASK_INVALID" }
        require(steps in 1..8 && alpha.isFinite() && alpha in 0.0..1.0 &&
            rho.isFinite() && rho in 0.0..1.0 &&
            memoryTemperature.isFinite() && memoryTemperature > 0.0) { "B2_OPTIONS_INVALID" }
        for (entry in event.memory) {
            require(entry.key.size == m && entry.value.size == m &&
                entry.key.all(Double::isFinite) && entry.value.all(Double::isFinite)) {
                "B2_SEMANTIC_VECTOR_INVALID"
            }
        }

        // S4: CURRENT input must reach the query before semantic retrieval.
        val input = weights.projection.multiply(event.features)
        val sIn = weights.us.multiply(event.state)
        val gIn = weights.ug.multiply(event.goal)
        val mIn = weights.meta.multiply(event.metadata)
        val z0 = DoubleArray(d) { i ->
            tanh(input[i] + sIn[i] + gIn[i] + mIn[i] + weights.eAt(i) + weights.biasAt(i))
        }
        val q = weights.wq.multiply(z0).map(::tanh).toDoubleArray()
        val read = DoubleArray(m)
        if (event.memory.isNotEmpty()) {
            val scores = event.memory.map { entry ->
                var dot = 0.0
                for (i in 0 until m) dot += q[i] * entry.key[i]
                dot / (sqrt(m.toDouble()) * memoryTemperature)
            }
            val largest = scores.maxOrNull()!!
            val exponentials = scores.map { exp(it - largest) }
            val total = exponentials.sum()
            require(total.isFinite() && total > 0.0) { "B2_SOFTMAX_INVALID" }
            for (idx in event.memory.indices) {
                val weight = exponentials[idx] / total
                for (i in 0 until m) read[i] += weight * event.memory[idx].value[i]
            }
        }
        val projectedRead = weights.wr.multiply(read)
        val z = DoubleArray(d) { i -> tanh(z0[i] + projectedRead[i]) }
        var h = DoubleArray(d) { i -> rho * event.state[i] + (1.0 - rho) * z[i] }
        require(h.all(Double::isFinite)) { "B2_STATE_INVALID" }

        // Precompute C_j z only for admitted blocks. No C/A/B calls for masked blocks.
        val cz = Array(weights.branchCount) { branch ->
            Array(weights.blocks) { block ->
                if (mask[block]) weights.branches[branch][block].c.multiply(z)
                else DoubleArray(0)
            }
        }
        for (step in 0 until steps) {
            val next = h.copyOf() // Synchronous update from same h^k for ALL blocks.
            for (block in mask.indices) {
                if (!mask[block]) continue
                val average = DoubleArray(weights.blockWidth)
                for (branch in 0 until weights.branchCount) {
                    val kernel = weights.branches[branch][block]
                    val ah = kernel.a.multiply(h)
                    val activated = DoubleArray(kernel.a.rows) { i ->
                        tanh(ah[i] + cz[branch][block][i] + kernel.aBiasAt(i))
                    }
                    val raw = kernel.b.multiply(activated)
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
        }
        val active = mask.count { it }
        val skipped = weights.blocks - active
        return UnoRefOutput(h, UnoRefKernelTrace(
            aCalls = steps * active * weights.branchCount,
            cCalls = active * weights.branchCount,
            bCalls = steps * active * weights.branchCount,
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
    private val steps: Int
) : NeuralPort {
    var lastTrace: UnoRefKernelTrace? = null
        private set

    override fun perceive(event: Percept): NeuralOutput {
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
        val output = reference.forward(
            UnoRefEvent(features, DoubleArray(32), DoubleArray(weights.d), DoubleArray(weights.d)),
            mask, steps
        )
        lastTrace = output.trace
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
}
