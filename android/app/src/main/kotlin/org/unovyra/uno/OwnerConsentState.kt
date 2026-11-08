package org.unovyra.uno

import java.security.SecureRandom
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger

/**
 * One-shot process-local consent state. This is NOT OS authority or a dispatch capability.
 * Only an Android-owned CredentialPlatform must instantiate it in production.
 * Independent Android permission/STOP/native checks remain necessary at OS linearization.
 */
internal class OwnerConsentState(private val platform: CredentialPlatform) {
    internal interface CredentialPlatform {
        fun nowNanos(): Long
        fun secureAndUnlocked(): Boolean
        fun foreground(): Boolean
        fun permissionsGranted(permissions: Set<String>): Boolean
        fun launchCredentialPrompt(requestCode: Int, exactDescription: String): Boolean
    }

    internal data class Scope(val verb: Int, val proposalDigest: String, val permissions: Set<String>) {
        fun valid(): Boolean = verb in 0..23 && proposalDigest.length == 64 &&
            proposalDigest.all { it in '0'..'9' || it in 'a'..'f' } &&
            permissions.size <= 8 && permissions.all { it.startsWith("android.permission.") && it.length <= 96 }
    }
    private data class Pending(val code: Int, val session: String, val scope: Scope, val at: Long)
    private data class Ready(val session: String, val scope: Scope, val at: Long)
    private val stopped = AtomicBoolean(false)
    private val session = ByteArray(16).also { SecureRandom().nextBytes(it) }
        .joinToString("") { "%02x".format(it) }
    private var pending: Pending? = null
    private var ready: Ready? = null

    companion object {
        const val TTL_NANOS = 60_000_000_000L
        private const val CODE_MIN = 0x4100
        private const val CODE_MAX = 0x7fef
        private const val CODE_SPACE = CODE_MAX - CODE_MIN + 1
        // Android request codes carry no cryptographic challenge. Do not reuse a code
        // across recreated OwnerConsentState instances *within the same process*.
        // Across process death, codes are randomized but stale OS callback collision
        // is not proven impossible. OS/device tests remain mandatory.
        private val codeSeed = SecureRandom().nextInt(CODE_SPACE)
        private val issuedCodes = AtomicInteger(0)
        private fun issueCode(): Int? {
            val n = issuedCodes.getAndIncrement()
            if (n !in 0 until CODE_SPACE) return null
            return CODE_MIN + (codeSeed + n) % CODE_SPACE
        }
        private val diagnosticDigest = MessageDigest.getInstance("SHA-256")
            .digest("UNO_OWNER_CREDENTIAL_NOOP/1".toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it) }

        /** Only the R5.3 verb 2 NOOP is authorized to request this diagnostic proof. */
        fun diagnosticNoopScope() = Scope(2, diagnosticDigest, emptySet())
    }

    /** Only the owner's foreground UI may call this. A model-supplied description is forbidden. */
    @Synchronized fun begin(scope: Scope, exactDescription: String): Int? {
        // Exact closed diagnostic catalogue. In particular verb 15 local notes and
        // all other Android effects must never gain a grant from this NOOP UI.
        if (stopped.get() || pending != null || ready != null || !scope.valid() ||
            scope != diagnosticNoopScope() ||
            exactDescription.isBlank() || exactDescription.length > 240 ||
            !platform.secureAndUnlocked() || !platform.foreground() ||
            !platform.permissionsGranted(scope.permissions)) return null
        val now = platform.nowNanos()
        if (now < 0 || now > Long.MAX_VALUE - TTL_NANOS) return null
        val code = issueCode() ?: return null // no reuse across instances in this process
        val immutable = scope.copy(permissions = scope.permissions.toSet())
        pending = Pending(code, session, immutable, now)
        val launched = try { platform.launchCredentialPrompt(code, exactDescription) }
                       catch (_: Exception) { false }
        if (!launched || stopped.get()) {
            pending = null
            return null
        }
        return code
    }

    /** Activity delivers its own resultCode; caller-controlled strings cannot assert this result. */
    @Synchronized fun credentialResult(requestCode: Int, successFromAndroid: Boolean): Boolean {
        val p = pending ?: return false
        if (p.code != requestCode) return false
        pending = null // consumes successful, cancelled, and failed results
        // Android may deliver RESULT_OK before Activity resumes and KeyguardManager
        // reports the screen unlocked. Revalidate secure/unlocked + foreground at consume.
        if (!successFromAndroid || stopped.get() || p.session != session ||
            !withinTtl(p.at) || !platform.permissionsGranted(p.scope.permissions)) return false
        ready = Ready(session, p.scope, p.at)
        return true
    }

    /**
     * Consumes admission exactly once, even when the digest/permissions or owner state differ.
     * A TRUE return is NOT a native effect, OS receipt, or permission to skip dispatch checks.
     */
    @Synchronized fun consume(scope: Scope): Boolean {
        val r = ready ?: return false
        ready = null
        return !stopped.get() && r.session == session && r.scope == scope &&
            scope == diagnosticNoopScope() && scope.valid() &&
            withinTtl(r.at) && platform.secureAndUnlocked() && platform.foreground() &&
            platform.permissionsGranted(scope.permissions)
    }

    private fun withinTtl(start: Long): Boolean {
        val now = platform.nowNanos()
        return start >= 0 && now >= start && now - start < TTL_NANOS
    }

    /** Cancel future admission immediately; an already dispatched OS effect is not undone. */
    fun stop() {
        stopped.set(true)
        synchronized(this) { pending = null; ready = null }
    }

    /** Foreground loss after a credential result burns readiness; pending OS prompt is preserved. */
    @Synchronized fun revokeReadyForBackground() { ready = null }
}
