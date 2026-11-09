package org.unovyra.uno.core

import javax.crypto.KeyGenerator

object UnoChatCipherTest {
    var pass = 0
    private fun verify(ok:Boolean) {check(ok);pass++}
    fun run() {
        val factory = KeyGenerator.getInstance("AES").apply { init(256) }
        val key = factory.generateKey()
        val other = factory.generateKey()
        val plain = "Привет, UNO! Точный текст / revision=7".toByteArray(Charsets.UTF_8)
        val sealedBytes = UnoChatCipher.seal(plain, key)
        verify(!sealedBytes.contentEquals(plain))
        verify(UnoChatCipher.open(sealedBytes, key).contentEquals(plain))
        verify(sealedBytes.size == plain.size + 5 + 12 + 16)
        verify(runCatching { UnoChatCipher.open(sealedBytes, other) }.isFailure)
        val corrupt = sealedBytes.copyOf().apply { this[lastIndex] = (this[lastIndex].toInt() xor 1).toByte() }
        verify(runCatching { UnoChatCipher.open(corrupt, key) }.isFailure)
        val invalidHeader = sealedBytes.copyOf().apply { this[0] = 0 }
        verify(runCatching { UnoChatCipher.open(invalidHeader, key) }.isFailure)
        verify(runCatching { UnoChatCipher.open(sealedBytes.copyOf(10), key) }.isFailure)
        verify(runCatching { UnoChatCipher.seal(ByteArray(0), key) }.isFailure)
        verify(runCatching { UnoChatCipher.seal(ByteArray(UnoChatCipher.MAX_PLAINTEXT + 1), key) }.isFailure)
        val same = UnoChatCipher.seal(plain, key)
        verify(!same.contentEquals(sealedBytes)) // random IV
        println("UNO_CHAT_ENCRYPTION_HOST_PASS=$pass")
    }
}
