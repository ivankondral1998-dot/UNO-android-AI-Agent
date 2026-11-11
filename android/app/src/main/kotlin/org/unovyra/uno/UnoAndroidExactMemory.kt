package org.unovyra.uno

import android.content.Context
import android.os.SystemClock
import android.provider.Settings
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.AtomicFile
import org.unovyra.uno.core.ExactEntry
import org.unovyra.uno.core.ExactRead
import org.unovyra.uno.core.EntryKind
import org.unovyra.uno.core.UnoEncryptedExactMemory
import org.unovyra.uno.core.UnoExactMemoryPort
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileNotFoundException
import java.io.FileInputStream
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * Android-bound exact observations. This is not neural authority or OS readback.
 * Encryption key never leaves AndroidKeyStore. A missing key, corrupt ciphertext,
 * unknown boot identity or missing snapshot fails closed; no automatic data deletion.
 * A separate device integration test is needed for AndroidKeystore and boot identity.
 */
internal class UnoAndroidExactMemory(context: Context, private val readOnly: Boolean = false) : UnoExactMemoryPort {
    private val file = AtomicFile(File(context.filesDir, "uno_exact_memory_v1.aes"))
    private val keyAlias = "uno_exact_memory_aes_v1"
    private val backend: UnoEncryptedExactMemory

    init {
        val boot = bootIdentifier(context)
        val keystore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = keystore.getKey(keyAlias, null)
        val base = file.baseFile
        val backup = File(base.path + ".bak")
        val partial = File(base.path + ".new")
        check(existing == null || existing is SecretKey) { "EXACT_KEY_TYPE_UNSUPPORTED" }
        var residue = when {
            base.isFile || backup.isFile -> ExactVaultResidue.COMMITTED
            partial.isFile -> ExactVaultResidue.PARTIAL
            else -> ExactVaultResidue.NONE
        }
        val partialAuthentic = if (residue == ExactVaultResidue.PARTIAL && existing is SecretKey) {
            runCatching { exactPartialAuthentic(readCapped(partial), existing) }.getOrDefault(false)
        } else false
        when (exactFirstOpen(residue, existing is SecretKey, readOnly, partialAuthentic)) {
            ExactFirstOpen.PROMOTE_PARTIAL -> {
                // Interrupted finishWrite: publish the already authenticated bytes.
                // Never replace them with an empty genesis.
                check(!base.exists() && partial.renameTo(base)) { "EXACT_PARTIAL_PROMOTE_FAILED" }
                residue = ExactVaultResidue.COMMITTED
            }
            ExactFirstOpen.REJECT_PARTIAL ->
                throw IllegalStateException("EXACT_PARTIAL_SNAPSHOT_UNREADABLE")
            ExactFirstOpen.REJECT_READONLY_EMPTY ->
                throw IllegalStateException("EXACT_READONLY_SNAPSHOT_UNAVAILABLE")
            ExactFirstOpen.REOPEN_COMMITTED, ExactFirstOpen.WRITE_GENESIS -> Unit
        }
        val hasSnapshot = residue == ExactVaultResidue.COMMITTED
        check(!hasSnapshot || existing is SecretKey) { "EXACT_KEY_MISSING" }
        // A key with no ciphertext is not evidence of a vault. Writable open
        // completes genesis with that same key. Read-only never creates a file.
        val createdKey = existing !is SecretKey
        val key = (existing as? SecretKey) ?: generateKey()
        try {
            backend = UnoEncryptedExactMemory(
                key, boot,
                load = {
                    try {
                        // AtomicFile.openRead() may repair a legacy backup by renaming
                        // files. Read-only inspection must not mutate the vault.
                        val input = if (readOnly) {
                            check(!backup.exists()) {
                                "EXACT_READONLY_PENDING_RECOVERY"
                            }
                            FileInputStream(base)
                        } else file.openRead()
                        input.use { stream ->
                            val out = ByteArrayOutputStream()
                            val buffer = ByteArray(8192)
                            while (true) {
                                val n = stream.read(buffer)
                                if (n < 0) break
                                check(n <= 0 || out.size() + n <= 1_500_033) {
                                    "EXACT_SNAPSHOT_TOO_LARGE"
                                }
                                if (n > 0) out.write(buffer, 0, n)
                            }
                            out.toByteArray()
                        }
                    } catch (notFound: FileNotFoundException) {
                        if (hasSnapshot) throw IllegalStateException(
                            "EXACT_EXISTING_SNAPSHOT_UNREADABLE", notFound)
                        null
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
                },
                // Fresh or key-only state gets a durable genesis snapshot.
                // An existing ciphertext file is never replaced by this path.
                initializeEmptyOnFirstOpen = !hasSnapshot && !readOnly,
                clockElapsedNanos = SystemClock::elapsedRealtimeNanos
            )
        } catch (error: Throwable) {
            // Drop a key created in this call only when no ciphertext remains.
            if (createdKey && !base.isFile && !backup.isFile && !partial.isFile) {
                runCatching { keystore.deleteEntry(keyAlias) }
            }
            throw error
        }
    }

    private fun readCapped(source: File): ByteArray {
        FileInputStream(source).use { stream ->
            val out = ByteArrayOutputStream()
            val buffer = ByteArray(8192)
            while (true) {
                val n = stream.read(buffer)
                if (n < 0) break
                check(out.size() + n <= 1_500_033) { "EXACT_SNAPSHOT_TOO_LARGE" }
                if (n > 0) out.write(buffer, 0, n)
            }
            return out.toByteArray()
        }
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

    /** Kernel boot UUID, fallback to Android boot_count; otherwise stop, not fabricate time. */
    private fun bootIdentifier(context: Context): String {
        val kernelId = runCatching {
            File("/proc/sys/kernel/random/boot_id").readText(Charsets.US_ASCII).trim()
        }.getOrNull()
        if (kernelId != null &&
            Regex("[a-fA-F0-9]{8}(-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}").matches(kernelId))
            return "kernel:$kernelId"
        val count = Settings.Global.getInt(context.contentResolver, "boot_count", -1)
        check(count >= 0) { "EXACT_BOOT_ID_UNAVAILABLE" }
        return "android_boot_count:$count"
    }

    override val generation: Long get() = backend.generation
    override fun write(scope: String, factKey: String, raw: ByteArray, expiry: Long,
                       consentEpoch: Long, kind: EntryKind, source: String): ExactEntry {
        check(!readOnly) { "EXACT_READONLY_WRITE_DENIED" }
        return backend.write(scope, factKey, raw, expiry, consentEpoch, kind, source)
    }
    override fun read(scope: String, factKey: String, k: Int, scanBudget: Int,
                      now: Long, consentEpoch: Long): ExactRead =
        backend.read(scope, factKey, k, scanBudget, now, consentEpoch)
    override fun revoke(scope: String) {
        check(!readOnly) { "EXACT_READONLY_REVOKE_DENIED" }
        backend.revoke(scope)
    }
}
