package org.unovyra.uno

import android.app.Activity
import android.app.KeyguardManager
import android.content.pm.PackageManager
import android.os.SystemClock

/**
 * OS-facing proof adapter. No privileged dispatch, no authentication via LLM/memory, no cloud.
 * Android createConfirmDeviceCredentialIntent is deprecated since API 29 but still available;
 * migrate to an audited platform BiometricPrompt flow after device evaluation.
 * RESULT_OK alone is not permission: OwnerConsentState binds it to a single pending request.
 */
internal class AndroidDeviceCredentialPlatform(private val activity: Activity) :
    OwnerConsentState.CredentialPlatform {

    override fun nowNanos(): Long = SystemClock.elapsedRealtimeNanos()

    override fun secureAndUnlocked(): Boolean {
        return try {
            val km = activity.getSystemService(KeyguardManager::class.java) ?: return false
            km.isDeviceSecure && !km.isDeviceLocked && !km.isKeyguardLocked
        } catch (_: Exception) { false }
    }

    override fun foreground(): Boolean = try {
        !activity.isFinishing && !activity.isDestroyed && activity.hasWindowFocus()
    } catch (_: Exception) { false }

    override fun permissionsGranted(permissions: Set<String>): Boolean = try {
        permissions.all { permission ->
            activity.checkSelfPermission(permission) == PackageManager.PERMISSION_GRANTED
        }
    } catch (_: Exception) { false }

    override fun launchCredentialPrompt(requestCode: Int, exactDescription: String): Boolean {
        if (!secureAndUnlocked() || !foreground()) return false
        return try {
            val km = activity.getSystemService(KeyguardManager::class.java) ?: return false
            val intent = km.createConfirmDeviceCredentialIntent(
                "UNO · проверка владельца", exactDescription
            ) ?: return false
            activity.startActivityForResult(intent, requestCode)
            true
        } catch (_: Exception) { false }
    }
}
