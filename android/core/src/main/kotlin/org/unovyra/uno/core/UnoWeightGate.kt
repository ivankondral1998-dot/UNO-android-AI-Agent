package org.unovyra.uno.core

import java.security.MessageDigest
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.math.BigDecimal
import kotlin.math.abs

enum class WeightAdmission { ADMITTED_UNVERIFIED_QUALITY, REJECTED }

/** Legacy envelope: it does not describe tensor layout, dtype, or a trusted digest. */
data class WeightManifest(
    val version: String,
    val inputWidth: Int,
    val stateWidth: Int,
    val memoryWidth: Int,
    val byteLength: Long,
    val digestSha256: String
)

/** C3 / Astra erratum 10. Without an approved full ABI there is no runtime admission.
 * Preserve the old signature for callers, but a self-described digest and size are not authority. */
@Suppress("UNUSED_PARAMETER")
fun admitWeights(manifest: WeightManifest, bytes: ByteArray, acceptedVersion: String): WeightAdmission =
    WeightAdmission.REJECTED

/** Canonical FP32 candidate geometry, NOT a new on-disk ABI or a loader.
 * Shapes and caps come from ASTRA_02 §2 / ASTRA_SUPPORT/evidence/recompute.py.
 * Rank-1 vectors and e_modality have elementwise box constraints. Matrices have row-L1 caps.
 */
internal data class B2CanonicalTensor(val name: String, val shape: List<Int>, val box: Boolean,
                                      val cap: Double, val frozenRows: Set<Int> = emptySet()) {
    val elements: Long get() = shape.fold(1L) { n, dim -> Math.multiplyExact(n, dim.toLong()) }
}
internal fun b2CanonicalInventory(d: Int): List<B2CanonicalTensor> {
    require(d in setOf(512, 1024, 1536, 2048)) { "UNAPPROVED_CANDIDATE_GEOMETRY" }
    val result = mutableListOf<B2CanonicalTensor>()
    fun m(name: String, rows: Int, cols: Int, cap: Double = 8.0, frozen: Set<Int> = emptySet()) {
        result += B2CanonicalTensor(name, listOf(rows, cols), false, cap, frozen)
    }
    fun v(name: String, n: Int, cap: Double = 8.0, frozen: Set<Int> = emptySet()) {
        result += B2CanonicalTensor(name, listOf(n), true, cap, frozen)
    }
    m("E_text", 32768, d); m("W_audio", d, 80); m("W_image", d, 768)
    m("W_sensor", d, 64); m("W_meta", d, 32); m("U_s", d, d, 1.0); m("U_g", d, d, 1.0)
    for (name in listOf("W_q", "W_k", "W_v")) m(name, 128, d, 2.0)
    m("W_r", d, 128, 2.0)
    result += B2CanonicalTensor("e_modality", listOf(6, d), true, 1.0)
    v("b_z", d, 1.0)
    for (l in 0..1) for (j in 0 until d / 64) {
        val base = "F.$l.$j."
        m(base + "A", 256, d, 1.0); m(base + "C", 256, d, 2.0)
        m(base + "B", 64, 256, 0.9); v(base + "a", 256); v(base + "b", 64)
    }
    for ((name, n) in listOf("verb" to 128, "outcome" to 128, "observable" to 128,
        "ctc" to 128, "belief" to 128, "speech" to 258, "value" to 1, "risk" to 1,
        "halt" to 1, "conf" to 1)) {
        val frozen = when (name) {
            "verb" -> (24..127).toSet()
            "outcome", "observable" -> ((0..2) + (24..127)).toSet()
            else -> emptySet()
        }
        m("W_$name", n, d, frozen = frozen); v("b_$name", n, frozen = frozen)
    }
    v("b_text", 32768); m("W_mask", d / 64, 2 * d + 4); v("b_mask", d / 64)
    m("W_wake", 1, 32); v("b_wake", 1)
    return result.toList()
}

/** A region of already isolated canonical FP32 payload. Header/padding/FP16/INT8
 * deployment decoding remains outside this validator. Offsets and byte order must come
 * from an independently trusted candidate layout; never trust model-provided descriptors.
 */
internal data class CanonicalFP32Region(val name: String, val shape: List<Int>,
                                       val offset: Long, val byteLength: Long)
internal enum class CanonicalGeometry { VALIDATED_CANDIDATE, REJECTED }

/** Validate the entire canonical payload, without granting runtime admission. A copy is
 * used for this host-only check so that callers cannot mutate the inspected snapshot.
 * The actual deployed ABI and authority for selecting d/digest are not defined here.
 */
internal fun validateB2CanonicalFP32(bytes: ByteArray, trustedD: Int, trustedDigest: String,
    trustedRegions: List<CanonicalFP32Region>, trustedByteOrder: ByteOrder): CanonicalGeometry {
    val reject = CanonicalGeometry.REJECTED
    if (trustedDigest.length != 64 || trustedDigest.any { it !in '0'..'9' && it !in 'a'..'f' }) return reject
    val expected = try { b2CanonicalInventory(trustedD) } catch (_: IllegalArgumentException) { return reject }
    val specs = expected.associateBy { it.name }
    val regions = trustedRegions.map { it.copy(shape = it.shape.toList()) }.sortedBy { it.offset }
    if (regions.size != expected.size || regions.map { it.name }.toSet() != specs.keys) return reject
    // All FP32 elements exactly once, with no holes, overlaps or trailing payload.
    var end = 0L
    for (r in regions) {
        val spec = specs.getValue(r.name)
        if (r.shape != spec.shape || r.offset != end || r.byteLength != spec.elements * 4L ||
            r.byteLength > bytes.size.toLong() - end) return reject
        end += r.byteLength
    }
    if (end != bytes.size.toLong()) return reject
    val snapshot = bytes.copyOf()
    val actual = MessageDigest.getInstance("SHA-256").digest(snapshot).joinToString("") { "%02x".format(it) }
    if (actual != trustedDigest) return reject
    val b = ByteBuffer.wrap(snapshot).order(trustedByteOrder)
    for (r in regions) {
        val spec = specs.getValue(r.name)
        val rows = spec.shape[0]
        val cols = spec.shape.getOrElse(1) { 1 }
        b.position(r.offset.toInt())
        for (row in 0 until rows) {
            val begin = b.position()
            var lo = 0.0
            var hi = 0.0
            for (col in 0 until cols) {
                val x = b.float
                if (!x.isFinite() || (row in spec.frozenRows && x != 0.0f)) return reject
                val a = abs(x.toDouble())
                if (spec.box) {
                    if (a > spec.cap) return reject
                } else if (a != 0.0) {
                    lo = Math.nextDown(lo + a)
                    hi = Math.nextUp(hi + a)
                }
            }
            if (!spec.box) {
                // Directed interval, then exact binary-float sum if near a cap.
                // Avoid accepting a row just above its real cap due to rounding.
                if (lo > Math.nextUp(spec.cap)) return reject
                if (hi > Math.nextDown(spec.cap)) {
                    var exact = BigDecimal.ZERO
                    for (col in 0 until cols) exact = exact.add(BigDecimal(abs(b.getFloat(begin + 4 * col).toDouble())))
                    if (exact > BigDecimal.valueOf(spec.cap)) return reject
                }
            }
        }
    }
    return CanonicalGeometry.VALIDATED_CANDIDATE
}

/** Remembers an admission. The bytes are not a neural port and not a permission. */
class WeightSlot {
    private var admission = WeightAdmission.REJECTED
    fun offer(manifest: WeightManifest, bytes: ByteArray, acceptedVersion: String): WeightAdmission {
        val decision = admitWeights(manifest, bytes, acceptedVersion)
        admission = decision
        return decision
    }
    fun admitted() = admission == WeightAdmission.ADMITTED_UNVERIFIED_QUALITY
}

/** A checked file is still not a neural port. These bytes cannot propose an action. */
class WeightCheckedNeural(private val slot: WeightSlot) : NeuralPort {
    override fun perceive(event: Percept): NeuralOutput {
        if (!slot.admitted()) throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
        throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
    }
}
