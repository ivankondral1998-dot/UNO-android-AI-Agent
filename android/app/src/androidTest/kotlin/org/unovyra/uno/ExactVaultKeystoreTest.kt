package org.unovyra.uno

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import androidx.test.ext.junit.runners.AndroidJUnit4
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import org.junit.Assert.assertEquals
import org.junit.Test
import org.junit.runner.RunWith
import org.unovyra.uno.core.EntryKind
import org.unovyra.uno.core.ExactStatus
import org.unovyra.uno.core.UnoEncryptedExactMemory

/** Device test. Uses a throwaway alias, never the owner's vault key. */
@RunWith(AndroidJUnit4::class)
class ExactVaultKeystoreTest {
    @Test
    fun createWriteReadReopen() {
        val alias = "uno_exact_keystore_it_v1"
        val keystore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        if (keystore.containsAlias(alias)) keystore.deleteEntry(alias)
        try {
            val spec = KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setKeySize(256)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .setUserAuthenticationRequired(false)
                .build()
            val key = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
                .apply { init(spec) }
                .generateKey() as SecretKey
            var stored: ByteArray? = null
            val now = 1_000L
            val created = UnoEncryptedExactMemory(
                key, "android-keystore-test",
                { stored?.copyOf() },
                { stored = it.copyOf() },
                initializeEmptyOnFirstOpen = true
            ) { now }
            val text = "УНА помнит число 84729."
            created.write(
                "owner-manual", "test123", text.toByteArray(Charsets.UTF_8),
                50_000L, 0L, EntryKind.USER_DECLARATION, "OWNER_MANUAL_FACT"
            )
            val reopened = UnoEncryptedExactMemory(
                key, "android-keystore-test",
                { stored?.copyOf() },
                { stored = it.copyOf() }
            ) { now }
            val read = reopened.read("owner-manual", "test123", 4, 64, now, 0L)
            assertEquals(ExactStatus.COMPLETE, read.status)
            assertEquals(text, read.entries.single().raw.toString(Charsets.UTF_8))
        } finally {
            if (keystore.containsAlias(alias)) keystore.deleteEntry(alias)
        }
    }
}
