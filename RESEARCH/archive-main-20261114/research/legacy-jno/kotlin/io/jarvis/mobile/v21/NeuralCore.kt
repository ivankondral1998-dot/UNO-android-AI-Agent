package io.jarvis.mobile.v21

import java.io.ByteArrayInputStream
import java.io.DataInputStream
import java.io.ByteArrayOutputStream
import java.io.DataOutputStream
import java.security.MessageDigest
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.sqrt

/**
 * V21 portable neural fast-memory core. Based on trained JNO Generation 2 and
 * the bounded/integrity-checked native inference discipline of Jarvis Lab V21.
 *
 * Deliberately has no Android authority, command vocabulary, veto(), network,
 * second agent or Android dependency. Outcomes MUST come from a separately
 * verified real-world observation if attached to physical actions.
 */
class NeuralCore private constructor(
    val contexts: Int,
    val actions: Int,
    val dimension: Int,
    private val eta: Double,
    private val temperature: Double,
    private val modelHash: ByteArray,
    private val keys: Array<DoubleArray>
) : AutoCloseable {
    private val state = DoubleArray(dimension * actions)
    private val visits = IntArray(contexts * actions)
    private var closed = false

    data class Candidate(val action: Int, val goalProbability: Double, val exploratory: Boolean) {
        /** This is a neural proposal, never an Android authorization. */
        val authorityGranted: Boolean get() = false
        val deviceEffectVerified: Boolean get() = false
    }

    private fun requireOpen() { check(!closed) { "CORE_CLOSED" } }
    private fun checkIndex(context: Int, value: Int) {
        require(context in 0 until contexts && value in 0 until actions) { "EVENT_BOUNDS" }
    }
    private fun readout(key: DoubleArray, memory: DoubleArray = state): DoubleArray = DoubleArray(actions) { o ->
        var sum = 0.0
        for (d in 0 until dimension) sum += key[d] * memory[d * actions + o]
        sum
    }
    private fun softmax(values: DoubleArray): DoubleArray {
        val mx = values.maxOrNull()!!
        val exps = DoubleArray(values.size) { exp(values[it] - mx) }
        val total = exps.sum()
        return DoubleArray(values.size) { exps[it] / total }
    }
    private fun probs(key: DoubleArray, memory: DoubleArray = state): DoubleArray {
        val read = readout(key, memory)
        return softmax(DoubleArray(actions) { read[it] * temperature })
    }

    /** Predicted outcome probabilities for each potential action. No dispatch. */
    @Synchronized fun probabilities(context: Int): Array<DoubleArray> {
        requireOpen(); checkIndex(context, 0)
        return Array(actions) { a -> probs(keys[context * actions + a]) }
    }

    /** Suggest an action for an externally supplied symbolic goal; no device authority. */
    @Synchronized fun candidate(context: Int, goal: Int, threshold: Double = 0.7): Candidate {
        requireOpen(); checkIndex(context, goal)
        require(threshold.isFinite() && threshold in 0.0..1.0)
        val p = Array(actions) { a -> probs(keys[context * actions + a])[goal] }
        var best = -1; var score = -1.0
        for (a in 0 until actions) if (visits[context * actions + a] > 0 && p[a] > score) {
            best = a; score = p[a]
        }
        if (score < threshold) {
            val unseen = (0 until actions).firstOrNull { visits[context * actions + it] == 0 }
            if (unseen != null) return Candidate(unseen, p[unseen], true)
            best = (0 until actions).maxBy { p[it] }
        }
        return Candidate(best, p[best], false)
    }

    /**
     * One neural plasticity update for an observed event (not a command result string).
     * `cycles` repeats the delta rule, NOT higher-level reasoning.
     */
    @Synchronized fun observe(context: Int, action: Int, observedOutcome: Int,
                              cycles: Int = 1, adaptive: Boolean = false): Int {
        requireOpen(); checkIndex(context, action); checkIndex(context, observedOutcome)
        require(cycles in 1..8) { "CYCLE_BOUNDS" }
        require(state.all { it.isFinite() }) { "STATE_NONFINITE" }
        val k = keys[context * actions + action]
        var used = 0
        repeat(cycles) {
            val before = readout(k)
            for (d in 0 until dimension) for (o in 0 until actions) {
                state[d * actions + o] += eta * k[d] * ((if (o == observedOutcome) 1.0 else 0.0) - before[o])
            }
            used++
            if (adaptive && probs(k)[observedOutcome] >= 0.95) {
                visits[context * actions + action]++
                return used
            }
        }
        visits[context * actions + action]++
        return used
    }

    @Synchronized fun reset() { requireOpen(); state.fill(0.0); visits.fill(0) }

    /** Strict, model-bound, tamper-detecting snapshot. The host chooses storage. */
    @Synchronized fun snapshot(): ByteArray {
        requireOpen()
        val b = ByteArrayOutputStream()
        DataOutputStream(b).use { out ->
            out.write(modelHash); out.writeInt(dimension); out.writeInt(actions)
            state.forEach { out.writeDouble(it) }
            visits.forEach { out.writeInt(it) }
        }
        val raw = b.toByteArray()
        return raw + digest(raw)
    }
    @Synchronized fun restore(snapshot: ByteArray) {
        requireOpen()
        val expectedSize = 40 + 8 * dimension * actions + 4 * contexts * actions + 32
        require(snapshot.size == expectedSize) { "STATE_SIZE" }
        val raw = snapshot.copyOfRange(0, snapshot.size - 32)
        require(digest(raw).contentEquals(snapshot.copyOfRange(raw.size, snapshot.size))) { "STATE_HASH" }
        val input = DataInputStream(ByteArrayInputStream(raw))
        val hash = ByteArray(32); input.readFully(hash)
        require(hash.contentEquals(modelHash)) { "STATE_MODEL_MISMATCH" }
        require(input.readInt() == dimension && input.readInt() == actions) { "STATE_SHAPE" }
        val nextState = DoubleArray(state.size) { input.readDouble() }
        val nextVisits = IntArray(visits.size) { input.readInt() }
        require(input.available() == 0 && nextState.all { it.isFinite() && kotlin.math.abs(it) <= 1e6 } &&
            nextVisits.all { it >= 0 }) { "STATE_BOUNDS" }
        // All-or-nothing replacement, including if the snapshot is corrupted.
        nextState.copyInto(state); nextVisits.copyInto(visits)
    }

    /**
     * Opt-in state migration for a wider model with compatible earlier keys.
     * Supports adding symbolic contexts; never silently transfers state to
     * unrelated weights. Key drift AND all old predicted outcomes are bounded.
     * Neural training on the enlarged contexts is still a separate task.
     */
    @Synchronized fun migrateFrom(previous: NeuralCore, keyTolerance: Double = 0.02,
                                  probabilityTolerance: Double = 0.01) {
        requireOpen()
        require(keyTolerance.isFinite() && keyTolerance in 0.0..0.02 &&
            probabilityTolerance.isFinite() && probabilityTolerance in 0.0..0.02)
        synchronized(previous) {
            previous.requireOpen()
            require(contexts >= previous.contexts && actions == previous.actions &&
                dimension == previous.dimension) { "MIGRATION_SHAPE" }
            for (i in previous.keys.indices) {
                for (d in 0 until dimension)
                    require(kotlin.math.abs(keys[i][d] - previous.keys[i][d]) <= keyTolerance) { "MIGRATION_KEYS" }
                val oldP = previous.probs(previous.keys[i])
                val newP = probs(keys[i], previous.state)
                for (o in 0 until actions)
                    require(kotlin.math.abs(oldP[o] - newP[o]) <= probabilityTolerance) { "MIGRATION_BEHAVIOUR" }
            }
            previous.state.copyInto(state)
            visits.fill(0)
            previous.visits.copyInto(visits)
        }
    }

    @Synchronized override fun close() {
        state.fill(0.0); visits.fill(0)
        keys.forEach { it.fill(0.0) }
        modelHash.fill(0)
        closed = true
    }

    companion object {
        private const val MAX_MODEL_BYTES = 8_000_000
        private fun digest(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)

        /** Direct JNP2 load, verified before decoding; no JLB2 weights or semantic veto. */
        fun load(blob: ByteArray): NeuralCore {
            require(blob.size in 80..MAX_MODEL_BYTES) { "MODEL_SIZE" }
            val raw = blob.copyOfRange(0, blob.size - 32)
            require(digest(raw).contentEquals(blob.copyOfRange(raw.size, blob.size))) { "MODEL_HASH" }
            val input = DataInputStream(ByteArrayInputStream(raw))
            val magic = ByteArray(4); input.readFully(magic)
            require(String(magic, Charsets.US_ASCII) == "JNP2") { "MODEL_MAGIC" }
            val C = input.readInt(); val A = input.readInt(); val D = input.readInt(); val W = input.readInt()
            val eta = input.readDouble(); val temperature = input.readDouble()
            require(C in 1..64 && A in 2..64 && D in 4..512 && W in 4..4096 &&
                eta.isFinite() && eta > 0 && eta < 1 && temperature.isFinite() && temperature in 1.0..30.0) { "MODEL_CONFIG" }
            val shapes = intArrayOf(W * (C + A), W, W * W, W, D * W, D)
            val weights = ArrayList<DoubleArray>(6)
            for (n in shapes) {
                require(input.readInt() == n) { "MODEL_SHAPE" }
                val scale = input.readDouble()
                require(scale.isFinite() && scale > 0 && scale < 100 && input.available() >= n) { "MODEL_SCALE" }
                weights.add(DoubleArray(n) {
                    val q = input.readByte().toInt()
                    require(q != -128) { "MODEL_INT8" }
                    q * scale
                })
            }
            require(input.available() == 0) { "MODEL_TRAILING" }
            val keys = Array(C * A) { index ->
                var x = DoubleArray(C + A)
                x[index / A] = 1.0; x[C + index % A] = 1.0
                for (layer in 0..2) {
                    val size = if (layer == 2) D else W
                    val w = weights[2 * layer]; val b = weights[2 * layer + 1]
                    x = DoubleArray(size) { j ->
                        var sum = b[j]
                        for (i in x.indices) sum += w[j * x.size + i] * x[i]
                        if (layer < 2) max(sum, 0.0) else sum
                    }
                }
                val norm = max(sqrt(x.sumOf { it * it }), 1e-6)
                DoubleArray(D) { x[it] / norm }
            }
            // Slow weights need not stay in RAM: only bounded neural keys and fast state.
            weights.forEach { it.fill(0.0) }
            return NeuralCore(C, A, D, eta, temperature, digest(blob), keys)
        }
    }
}
