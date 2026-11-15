package org.unovyra.uno.core

import java.security.MessageDigest

object UnoFrameContractTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private fun sha(bytes: ByteArray) = MessageDigest.getInstance("SHA-256").digest(bytes)
        .joinToString("") { "%02x".format(it) }

    fun run() {
        val bytes = byteArrayOf(1, 2, 3, 4)
        val manifest = WeightManifest("SYNTHETIC/1", 8, 128, 128, bytes.size.toLong(), sha(bytes))
        verify(admitWeights(manifest, bytes, "SYNTHETIC/1") ==
            WeightAdmission.PAYLOAD_CHECKSUM_ONLY)
        verify(admitWeights(manifest, byteArrayOf(1, 2, 3, 5), "SYNTHETIC/1") ==
            WeightAdmission.REJECTED)
        verify(admitWeights(manifest, bytes, "OTHER") == WeightAdmission.REJECTED)
        verify(admitWeights(manifest.copy(byteLength = 3), bytes, "SYNTHETIC/1") ==
            WeightAdmission.REJECTED)
        verify(admitWeights(manifest.copy(inputWidth = 0), bytes, "SYNTHETIC/1") ==
            WeightAdmission.REJECTED)
        verify(admitWeights(manifest, byteArrayOf(), "SYNTHETIC/1") == WeightAdmission.REJECTED)

        val audio = PcmFrameGate(4)
        verify(audio.accept(byteArrayOf(), true) == PcmStatus.EMPTY)
        verify(audio.accept(byteArrayOf(1, 2), false) == PcmStatus.PERMISSION_DENIED)
        verify(audio.accept(byteArrayOf(1, 2, 3, 4, 5), true) == PcmStatus.TOO_LARGE)
        verify(audio.accept(byteArrayOf(1, 2), true) == PcmStatus.ACCEPTED_FRAME)
        audio.stop()
        verify(audio.accept(byteArrayOf(1, 2), true) == PcmStatus.STOPPED)

        verify(sensorFreshness(0.0, 10, 12, 5, true) == SensorFreshness.PRESENT)
        verify(sensorFreshness(null, 10, 12, 5, true) == SensorFreshness.ABSENT)
        verify(sensorFreshness(1.0, 10, 20, 5, true) == SensorFreshness.STALE)
        verify(sensorFreshness(1.0, 10, 12, 5, false) == SensorFreshness.DENIED)
        verify(sensorFreshness(Double.NaN, 10, 12, 5, true) == SensorFreshness.ABSENT)
        println("UNO_FRAME_CONTRACT_HOST_PASS=$pass")
    }
}
