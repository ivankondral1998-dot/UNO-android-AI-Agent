package android.app
import android.content.Intent
import android.content.pm.PackageManager
open class Activity {
    var isFinishing = false
    var isDestroyed = false
    var focused = true
    var permissions = true
    var throwOnLaunch = false
    var launchedCode = -1
    var keyguard: KeyguardManager? = KeyguardManager()
    @Suppress("UNCHECKED_CAST")
    fun <T> getSystemService(cls: Class<T>): T? = if(cls==KeyguardManager::class.java) keyguard as T? else null
    fun hasWindowFocus() = focused
    fun checkSelfPermission(permission:String):Int = if(permissions) PackageManager.PERMISSION_GRANTED else -1
    fun startActivityForResult(intent: Intent, code: Int) {
        if(throwOnLaunch) throw IllegalStateException("OS refused")
        launchedCode=code
    }
}
class KeyguardManager {
    var isDeviceSecure = true
    var isDeviceLocked = false
    var isKeyguardLocked = false
    var returnNullIntent = false
    fun createConfirmDeviceCredentialIntent(title:CharSequence,description:CharSequence):android.content.Intent? =
        if(returnNullIntent)null else android.content.Intent()
}
