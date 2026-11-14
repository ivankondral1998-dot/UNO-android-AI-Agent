package org.unovyra.uno.core

import java.security.MessageDigest

enum class WeightAdmission {
    /** Byte length and SHA match a caller-supplied manifest; NOT accepted model weights. */
    PAYLOAD_CHECKSUM_ONLY,
    /** Legacy status, never returned by the unchecked manifest path. */
    ADMITTED_UNVERIFIED_QUALITY,
    REJECTED
}

/**
 * A caller-provided digest/length can check transfer integrity only.
 * Without independent trusted tensor shapes, ABI/2 descriptors, frozen rows,
 * norm certificates and provenance, the payload is NOT an admitted model.
 */
data class WeightManifest(
    val version: String,
    val inputWidth: Int,
    val stateWidth: Int,
    val memoryWidth: Int,
    val byteLength: Long,
    val digestSha256: String
)

fun admitWeights(manifest: WeightManifest, bytes: ByteArray, acceptedVersion: String): WeightAdmission {
    if (acceptedVersion.isBlank() || manifest.version != acceptedVersion) return WeightAdmission.REJECTED
    if (manifest.version.length > 128) return WeightAdmission.REJECTED
    if (manifest.inputWidth !in 1..4096 || manifest.stateWidth !in 1..4096 ||
        manifest.memoryWidth !in 1..4096) return WeightAdmission.REJECTED
    if (manifest.byteLength != bytes.size.toLong() || bytes.isEmpty()) return WeightAdmission.REJECTED
    if (manifest.digestSha256.length != 64 ||
        manifest.digestSha256.any { it !in '0'..'9' && it !in 'a'..'f' }) {
        return WeightAdmission.REJECTED
    }
    val actual = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }
    return if (actual == manifest.digestSha256) WeightAdmission.PAYLOAD_CHECKSUM_ONLY
    else WeightAdmission.REJECTED
}

/** Remembers an admission. The bytes are not a neural port and not a permission. */
class WeightSlot {
    private var admission = WeightAdmission.REJECTED
    fun offer(manifest: WeightManifest, bytes: ByteArray, acceptedVersion: String): WeightAdmission {
        val decision = admitWeights(manifest, bytes, acceptedVersion)
        admission = decision
        return decision
    }
    /** No full ABI loader exists yet. The checksum-only path must never enable inference. */
    fun admitted() = false
    fun checksumVerifiedOnly() = admission == WeightAdmission.PAYLOAD_CHECKSUM_ONLY
}

/** A checked file is still not a neural port. These bytes cannot propose an action. */
class WeightCheckedNeural(private val slot: WeightSlot) : NeuralPort {
    override fun perceive(event: Percept): NeuralOutput {
        if (!slot.admitted()) throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
        throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
    }
}
