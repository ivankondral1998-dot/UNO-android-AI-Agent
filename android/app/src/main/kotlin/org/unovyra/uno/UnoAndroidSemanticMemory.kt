package org.unovyra.uno

import android.content.Context
import android.util.AtomicFile
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import org.unovyra.uno.core.ExactEntry
import org.unovyra.uno.core.SemanticRead
import org.unovyra.uno.core.SemanticStatus
import org.unovyra.uno.core.UnoSemanticMemory
import java.io.File
import java.io.FileInputStream
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * Summary index beside the exact vault. A missing file is UNKNOWN, not an
 * empty fact. This store does not create vectors and does not open the vault.
 */
internal class UnoAndroidSemanticMemory(context: Context) {
    private val file = AtomicFile(File(context.applicationContext.filesDir, "uno_semantic_v1.aes"))
    private val keyAlias = "uno_semantic_aes_v1"
    private val boot = unoDeviceBootIdentifier(context.applicationContext)
    private var cached: UnoSemanticMemory? = null

    fun retrieve(scope: String, query: DoubleArray, k: Int, scanBudget: Int): SemanticRead {
        if (!file.baseFile.isFile) {
            check(!File(file.baseFile.path + ".new").isFile) { "SEMANTIC_PARTIAL_UNREADABLE" }
            return SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
        }
        return open(createKey = false).retrieve(scope, query, k, scanBudget)
    }

    fun link(entry: ExactEntry, vector: DoubleArray) {
        open(createKey = true).link(entry, vector)
    }

    fun dropScope(scope: String) {
        open(createKey = true).dropScope(scope)
    }

    private fun open(createKey: Boolean): UnoSemanticMemory {
        cached?.let { return it }
        val keystore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keystore.getKey(keyAlias, null)
        check(existing == null || existing is SecretKey) { "SEMANTIC_KEY_TYPE_UNSUPPORTED" }
        val base = file.baseFile
        if (!base.isFile && File(base.path + ".new").isFile) error("SEMANTIC_PARTIAL_UNREADABLE")
        if (base.isFile && existing !is SecretKey) error("SEMANTIC_KEY_MISSING")
        val key = (existing as? SecretKey) ?: if (createKey) generateKey()
        else error("SEMANTIC_KEY_MISSING")
        val opened = UnoSemanticMemory(
            key, boot,
            load = {
                if (!base.isFile) null
                else FileInputStream(base).use { input ->
                    val out = java.io.ByteArrayOutputStream()
                    val buffer = ByteArray(8192)
                    while (true) {
                        val n = input.read(buffer)
                        if (n < 0) break
                        check(out.size() + n <= 1_500_000) { "SEMANTIC_SNAPSHOT_TOO_LARGE" }
                        if (n > 0) out.write(buffer, 0, n)
                    }
                    out.toByteArray()
                }
            },
            persist = { bytes ->
                val stream = file.startWrite()
                try {
                    stream.write(bytes)
                    file.finishWrite(stream)
                } catch (error: Exception) {
                    file.failWrite(stream)
                    throw error
                }
            }
        )
        cached = opened
        return opened
    }

    private fun generateKey(): SecretKey {
        val spec = KeyGenParameterSpec.Builder(keyAlias,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setKeySize(256)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setRandomizedEncryptionRequired(true)
            .setUserAuthenticationRequired(false)
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
            .apply { init(spec) }.generateKey()
    }
}
