package org.unovyra.uno.core

import java.security.MessageDigest

enum class WeightAdmission { ADMITTED_UNVERIFIED_QUALITY, REJECTED }

/**
 * Shape and digest check only. Admission is not a quality score,
 * not a trained model, and not permission to act.
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
    return if (actual == manifest.digestSha256) WeightAdmission.ADMITTED_UNVERIFIED_QUALITY
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
    fun admitted() = admission == WeightAdmission.ADMITTED_UNVERIFIED_QUALITY
}

/** A checked file is still not a neural port. These bytes cannot propose an action. */
class WeightCheckedNeural(private val slot: WeightSlot) : NeuralPort {
    override fun perceive(event: Percept): NeuralOutput {
        if (!slot.admitted()) throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
        throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
    }
}
