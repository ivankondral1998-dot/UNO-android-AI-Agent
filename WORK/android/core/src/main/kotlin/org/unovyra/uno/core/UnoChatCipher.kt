package org.unovyra.uno.core

import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Minimal versioned AES-256-GCM envelope; not user-authentication or OS authority. */
object UnoChatCipher {
    private val header = byteArrayOf(85, 78, 79, 67, 2) // UNOC / v2
    private val associated = "UNO_CHAT_EXPERIMENT/2|local-device".toByteArray(Charsets.US_ASCII)
    const val MAX_PLAINTEXT = 100_000
    const val MAX_CIPHERTEXT = MAX_PLAINTEXT + 5 + 12 + 16
    private const val IV_LEN = 12

    fun seal(clear: ByteArray, key: SecretKey): ByteArray {
        require(clear.isNotEmpty() && clear.size <= MAX_PLAINTEXT) { "CHAT_SIZE_INVALID" }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        cipher.updateAAD(associated)
        val iv = cipher.iv
        require(iv != null && iv.size == IV_LEN) { "CHAT_IV_INVALID" }
        return header + iv + cipher.doFinal(clear)
    }

    /** Reject corrupted/tampered ciphertext. Never silently recreate a lost key. */
    fun open(envelope: ByteArray, key: SecretKey): ByteArray {
        require(envelope.size in (header.size + IV_LEN + 17)..MAX_CIPHERTEXT &&
            envelope.copyOfRange(0, header.size).contentEquals(header)) { "CHAT_ENVELOPE_INVALID" }
        val iv = envelope.copyOfRange(header.size, header.size + IV_LEN)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(128, iv))
        cipher.updateAAD(associated)
        return cipher.doFinal(envelope, header.size + IV_LEN,
            envelope.size - header.size - IV_LEN).also {
            require(it.isNotEmpty() && it.size <= MAX_PLAINTEXT)
        }
    }
}
