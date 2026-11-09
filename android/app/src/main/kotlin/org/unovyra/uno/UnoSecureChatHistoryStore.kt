package org.unovyra.uno

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import org.unovyra.uno.core.UnoChatCipher
import org.unovyra.uno.core.UnoChatTurn
import org.unovyra.uno.core.UnoPromptWindow
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileNotFoundException
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * App-private AES/GCM transcript, bound to local AndroidKeyStore.
 * Existing v1 plaintext file is READ ONLY (never deleted or silently migrated in place).
 * Failure to decrypt v2 is fatal: no fallback to older v1 after potential corruption.
 * This is not yet a semantic memory or cross-device backup contract.
 */
internal class UnoSecureChatHistoryStore(private val context: Context) {
    private val legacy = UnoChatHistoryStore(context)
    private val file = AtomicFile(File(context.filesDir, "uno_chat_experiment_v2.aes"))
    private val alias = "uno_local_chat_v2_aes_gcm"

    private fun secretKey(allowCreate: Boolean): SecretKey {
        val keystore = KeyStore.getInstance("AndroidKeyStore")
        keystore.load(null)
        val existing = keystore.getKey(alias, null)
        if (existing is SecretKey) return existing
        check(existing == null) { "KEYSTORE_KEY_TYPE_INVALID" }
        check(allowCreate) { "CHAT_DECRYPTION_KEY_MISSING" }
        val spec = KeyGenParameterSpec.Builder(alias,
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

    private fun boundedRead(): ByteArray {
        val max = UnoChatCipher.MAX_CIPHERTEXT
        return file.openRead().use { input ->
            val out = ByteArrayOutputStream()
            val buffer = ByteArray(4096)
            while (true) {
                val n = input.read(buffer)
                if (n < 0) break
                check(out.size() + n <= max) { "CHAT_CIPHERTEXT_TOO_LARGE" }
                out.write(buffer, 0, n)
            }
            out.toByteArray()
        }
    }

    fun load(): List<UnoChatTurn> {
        val bytes = try { boundedRead() } catch (_: FileNotFoundException) {
            return legacy.load()
        }
        // An empty, bad, or tampered v2 record cannot fall back to stale v1 history.
        val clear = UnoChatCipher.open(bytes, secretKey(false))
        val obj = JSONObject(String(clear, Charsets.UTF_8))
        check(obj.getString("schema") == "UNO_CHAT_EXPERIMENT/2") { "CHAT_SCHEMA_INVALID" }
        val array = obj.getJSONArray("turns")
        check(array.length() <= 40) { "CHAT_TOO_MANY_TURNS" }
        return UnoPromptWindow.sanitizeHistory((0 until array.length()).map { i ->
            val item = array.getJSONObject(i)
            UnoChatTurn(item.getString("role"), item.getString("content"))
        })
    }

    fun save(turns: List<UnoChatTurn>) {
        val checked = UnoPromptWindow.sanitizeHistory(turns)
        val array = JSONArray()
        checked.forEach { array.put(JSONObject().put("role", it.role).put("content", it.content)) }
        val clear = JSONObject().put("schema", "UNO_CHAT_EXPERIMENT/2").put("turns", array)
            .toString().toByteArray(Charsets.UTF_8)
        val encrypted = UnoChatCipher.seal(clear, secretKey(true))
        val stream = file.startWrite()
        try {
            stream.write(encrypted)
            file.finishWrite(stream)
        } catch (e: Exception) {
            file.failWrite(stream)
            throw e
        }
    }
}
