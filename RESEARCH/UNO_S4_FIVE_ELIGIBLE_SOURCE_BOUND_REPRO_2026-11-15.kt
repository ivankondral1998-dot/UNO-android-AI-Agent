package org.unovyra.uno.core

import java.security.MessageDigest
import javax.crypto.KeyGenerator
import kotlin.math.abs

/**
 * Negative S4 integration fixture, intentionally kept outside core/src/test.
 * Compiles against actual WORK/android/core/src/main Kotlin sources.
 * Confirms the current reference port drops one of 5 eligible semantic entries.
 * No production code, model weights or Android permissions are changed.
 */
object UnoS4FiveEligibleSourceBoundRepro {
    private const val D = 128
    private fun zero(r: Int, c: Int) = UnoRefMatrix(r, c, DoubleArray(r * c))
    private fun one(r: Int, c: Int, i: Int, j: Int): UnoRefMatrix =
        UnoRefMatrix(r, c, DoubleArray(r * c).also { it[i * c + j] = 1.0 })
    private fun basis(i: Int) = DoubleArray(D).also { it[i] = 1.0 }
    private fun packed(state: DoubleArray): ByteArray = ByteArray(state.size * 8).also { bytes ->
        state.forEachIndexed { i, number ->
            var bits = number.toRawBits()
            repeat(8) { j -> bytes[i * 8 + j] = (bits and 255).toByte(); bits = bits ushr 8 }
        }
    }
    private fun sha(state: DoubleArray) =
        MessageDigest.getInstance("SHA-256").digest(packed(state))
            .joinToString("") { "%02x".format(it) }
    private fun weights(): UnoRefWeights = UnoRefWeights(
        "S4_DIAGNOSTIC/1", one(D,D,0,0), zero(D,D), zero(D,D), zero(D,32),
        DoubleArray(D), DoubleArray(D), one(D,D,1,0), one(D,D,0,1),
        (0 until 2).map { (0 until 2).map {
            UnoRefBranch(zero(256,D), zero(256,D), zero(64,256),
                DoubleArray(256), DoubleArray(64))
        } }
    )
    fun run() {
        val exact = ExactMemory()
        val key = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()
        var persisted: ByteArray? = null
        val semantic = UnoSemanticMemory(key, "s4-repro-boot",
            { persisted?.copyOf() }, { persisted = it.copyOf() }, D)
        val vectors = listOf(basis(0), basis(0), basis(0), basis(0), basis(1))
        val ids = vectors.mapIndexed { i, v ->
            val record = exact.write("s4-repro", "fact-$i", byteArrayOf(i.toByte()),
                10_000L, 0L, EntryKind.OBSERVED, "LOCAL_SYNTHETIC")
            semantic.link(record, v)
            record.id
        }
        val f = basis(0)
        val hits = semantic.retrieve("s4-repro", f, 4, 64)
        check(hits.status == SemanticStatus.TRUNCATED &&
              hits.hits.size == 4 && hits.matchedLowerBound == 5)
        check(hits.hits.none { it.exactId == ids.last() })
        val w = weights()
        val mask = booleanArrayOf(true, false)
        val network = UnoFReference(w)
        val port = UnoFReferencePort(network, w, mask, 1, semantic, "s4-repro")
        val result = port.perceive(Percept(PerceptType.SENSOR, packed(f), "SYNTHETIC", 1L))
        fun evaluate(mem: List<UnoRefMemoryVector>) = network.forward(
            UnoRefEvent(f, DoubleArray(32), DoubleArray(D), DoubleArray(D), mem),
            mask, 1
        ).state
        val full = evaluate(vectors.map { UnoRefMemoryVector(it,it) })
        val four = evaluate(hits.hits.map { UnoRefMemoryVector(it.vector,it.vector) })
        check(result.action == null && port.lastTrace?.skippedBlocks == 1)
        check(result.stateDigest == sha(four)) { "Preselection algorithm changed; re-audit" }
        check(result.stateDigest != sha(full)) { "S4 full-I regression no longer reproduces" }
        check(full[0] - four[0] > 1e-4 && abs(full[0] - four[0]) < 1.0)
        println("S4_SOURCE_BOUND_NEGATIVE_REPRO_PASS=1")
        println("S4_FULL_STATE0=" + full[0] + " S4_PORT_STATE0=" + four[0])
        println("S4_ELIGIBLE=5 S4_PORT_SELECTED=4")
        println("LIMIT=synthetic weights and JVM; not a production memory or Android certification")
    }
}
fun main() = UnoS4FiveEligibleSourceBoundRepro.run()
