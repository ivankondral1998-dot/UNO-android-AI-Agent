package org.unovyra.uno
import android.app.Activity
import android.os.SystemClock

object AndroidDeviceCredentialPlatformTest {
    var pass=0
    private fun test(label:String,block:()->Unit){block();pass++;println("PASS DEVICE_CREDENTIAL_ADAPTER $label")}
    fun run(){
        test("secure Android keyguard launches one request"){
            val a=Activity();val p=AndroidDeviceCredentialPlatform(a)
            check(p.secureAndUnlocked() && p.foreground())
            check(p.launchCredentialPrompt(0x4100,"Diagnostic only"));check(a.launchedCode==0x4100)
        }
        test("missing credential setup refuses launch"){
            val a=Activity();a.keyguard!!.isDeviceSecure=false
            val p=AndroidDeviceCredentialPlatform(a)
            check(!p.secureAndUnlocked() && !p.launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("locked Android profile refuses launch"){
            val a=Activity();a.keyguard!!.isDeviceLocked=true
            val p=AndroidDeviceCredentialPlatform(a)
            check(!p.launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("keyguard showing refuses launch"){
            val a=Activity();a.keyguard!!.isKeyguardLocked=true
            val p=AndroidDeviceCredentialPlatform(a)
            check(!p.launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("lost foreground focus refuses launch"){
            val a=Activity();a.focused=false
            val p=AndroidDeviceCredentialPlatform(a)
            check(!p.foreground() && !p.launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("destroyed activity refuses foreground"){
            val a=Activity();a.isDestroyed=true
            check(!AndroidDeviceCredentialPlatform(a).foreground())
        }
        test("missing required Android permission refuses"){
            val a=Activity();a.permissions=false
            val p=AndroidDeviceCredentialPlatform(a)
            check(!p.permissionsGranted(setOf("android.permission.RECORD_AUDIO")))
        }
        test("secure lock but null OS prompt intent refuses"){
            val a=Activity();a.keyguard!!.returnNullIntent=true
            check(!AndroidDeviceCredentialPlatform(a).launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("OS throws while starting prompt: fail closed"){
            val a=Activity();a.throwOnLaunch=true
            check(!AndroidDeviceCredentialPlatform(a).launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("no KeyguardManager service refuses"){
            val a=Activity();a.keyguard=null
            check(!AndroidDeviceCredentialPlatform(a).secureAndUnlocked())
            check(!AndroidDeviceCredentialPlatform(a).launchCredentialPrompt(0x4100,"Diagnostic only"))
        }
        test("monotonic OS clock is used, not wall clock"){
            val a=Activity();SystemClock.now=500
            check(AndroidDeviceCredentialPlatform(a).nowNanos()==500L)
        }
        println("UNO_DEVICE_CREDENTIAL_PLATFORM_HOST_PASS=$pass")
    }
}
fun main(){ AndroidDeviceCredentialPlatformTest.run() }
