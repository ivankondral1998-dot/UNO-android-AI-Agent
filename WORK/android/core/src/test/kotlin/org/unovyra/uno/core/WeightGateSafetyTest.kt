package org.unovyra.uno.core

import java.security.MessageDigest

/** C3: SHA from the same untrusted manifest is not model integrity or shape attestation. */
object WeightGateSafetyTest {
    var pass = 0
        private set

    private fun verify(label: String, body: () -> Unit) {
        body()
        pass++
        println("PASS C3 $label")
    }

    private fun sha(bytes: ByteArray) =
        MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }

    private fun manifest(bytes: ByteArray) = WeightManifest(
        UnoAbi.MODEL, 128, 128, 128, bytes.size.toLong(), sha(bytes)
    )

    fun run() {
        verify("one-byte self-hashed payload is not an admitted model") {
            val bytes = byteArrayOf(42)
            check(admitWeights(manifest(bytes), bytes, UnoAbi.MODEL) ==
                WeightAdmission.PAYLOAD_CHECKSUM_ONLY)
            val slot = WeightSlot()
            check(slot.offer(manifest(bytes), bytes, UnoAbi.MODEL) ==
                WeightAdmission.PAYLOAD_CHECKSUM_ONLY)
            check(slot.checksumVerifiedOnly() && !slot.admitted())
            check(runCatching {
                WeightCheckedNeural(slot).perceive(
                    Percept(PerceptType.TEXT, "test".toByteArray(), "TEST", 0L)
                )
            }.isFailure)
        }
        verify("4096 self-hashed random bytes are not a complete tensor inventory") {
            val bytes = ByteArray(4096) { it.toByte() }
            val slot = WeightSlot()
            slot.offer(manifest(bytes), bytes, UnoAbi.MODEL)
            check(!slot.admitted() && slot.checksumVerifiedOnly())
        }
        verify("digest mismatch rejects") {
            val a = byteArrayOf(1, 2, 3)
            val b = byteArrayOf(1, 2, 4)
            check(admitWeights(manifest(a), b, UnoAbi.MODEL) == WeightAdmission.REJECTED)
        }
        verify("length mismatch rejects") {
            val bytes = byteArrayOf(1)
            check(admitWeights(manifest(bytes).copy(byteLength = 2L), bytes, UnoAbi.MODEL) ==
                WeightAdmission.REJECTED)
        }
        verify("version mismatch rejects") {
            val bytes = byteArrayOf(1)
            check(admitWeights(manifest(bytes), bytes, "OTHER/1") == WeightAdmission.REJECTED)
        }
        verify("invalid stated dimension rejects even checksum-only status") {
            val bytes = byteArrayOf(1)
            check(admitWeights(manifest(bytes).copy(memoryWidth = 0), bytes, UnoAbi.MODEL) ==
                WeightAdmission.REJECTED)
        }
    }
}
fun main() { WeightGateSafetyTest.run() }
