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
