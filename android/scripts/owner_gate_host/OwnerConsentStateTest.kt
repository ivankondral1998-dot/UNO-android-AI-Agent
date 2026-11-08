package org.unovyra.uno

import java.util.concurrent.atomic.AtomicBoolean

/** The platform is a hostile/fault-injected fixture: tests prove state transitions, not OS auth. */
object OwnerConsentStateTest {
    private var passed = 0
    private fun test(name: String, action: () -> Unit) {
        action(); passed++; println("PASS OWNER_STATE $name")
    }
    private class Fake : OwnerConsentState.CredentialPlatform {
        var now = 100L
        var secure = true
        var foreground = true
        var permission = true
        var launch = true
        var launched = 0
        var lastCode = -1
        override fun nowNanos() = now
        override fun secureAndUnlocked() = secure
        override fun foreground() = foreground
        override fun permissionsGranted(permissions: Set<String>) = permission
        override fun launchCredentialPrompt(requestCode: Int, exactDescription: String): Boolean {
            launched++;lastCode = requestCode;return launch
        }
    }
    private val dig = "a".repeat(64)
    private val scope = OwnerConsentState.Scope(0, dig, emptySet())
    private fun make() = Fake().let { it to OwnerConsentState(it) }
    fun run() {
        test("one OS result permits one local consumption, never two") {
            val (f,g)=make(); val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));check(g.consume(scope));check(!g.consume(scope));check(f.launched==1)
        }
        test("without device secure state challenge never starts") {
            val (f,g)=make();f.secure=false
            check(g.begin(scope,"Diagnostic NOOP")==null);check(f.launched==0)
        }
        test("without owner foreground no prompt") {
            val (f,g)=make();f.foreground=false
            check(g.begin(scope,"Diagnostic NOOP")==null);check(f.launched==0)
        }
        test("missing permission blocks admission before prompt") {
            val (f,g)=make();f.permission=false
            check(g.begin(scope,"Diagnostic NOOP")==null);check(f.launched==0)
        }
        test("failed OS prompt launch leaves no ticket") {
            val (f,g)=make();f.launch=false
            check(g.begin(scope,"Diagnostic NOOP")==null);check(!g.credentialResult(f.lastCode,true))
        }
        test("cancelled credential result cannot be consumed") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(!g.credentialResult(code,false));check(!g.consume(scope))
        }
        test("stale result requestCode cannot approve a new challenge") {
            val (_,g)=make();val first=g.begin(scope,"Diagnostic NOOP")!!
            check(!g.credentialResult(first,false))
            val second=g.begin(scope,"Diagnostic NOOP")!!
            check(first!=second);check(!g.credentialResult(first,true));check(!g.consume(scope))
            check(g.credentialResult(second,true));check(g.consume(scope))
        }
        test("OS result can arrive before keyguard unlock state refresh") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            f.secure=false // temporary KeyguardManager locked state in result callback
            check(g.credentialResult(code,true))
            f.secure=true
            check(g.consume(scope))
        }
        test("duplicate result callback never creates new permission") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));check(!g.credentialResult(code,true));check(g.consume(scope))
        }
        test("STOP before result permanently refuses current and future request") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            g.stop();check(!g.credentialResult(code,true));check(g.begin(scope,"Diagnostic NOOP")==null)
        }
        test("STOP after result before consumption revokes it") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));g.stop();check(!g.consume(scope))
        }
        test("changed proposal digest burns grant") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));check(!g.consume(scope.copy(proposalDigest="b".repeat(64))))
            check(!g.consume(scope))
        }
        test("changed permission set burns grant") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));check(!g.consume(scope.copy(permissions=setOf("android.permission.CAMERA"))))
            check(!g.consume(scope))
        }
        test("owner locks after OS confirmation then consumption refuses") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));f.secure=false;check(!g.consume(scope))
        }
        test("foreground loss after result refuses consumption") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));f.foreground=false;check(!g.consume(scope))
        }
        test("permission revoked after confirmation refuses consumption") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));f.permission=false;check(!g.consume(scope))
        }
        test("timeout refuses result and consumption") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            f.now=100+OwnerConsentState.TTL_NANOS
            check(!g.credentialResult(code,true));check(!g.consume(scope))
        }
        test("timeout after success refuses consumption") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));f.now=100+OwnerConsentState.TTL_NANOS
            check(!g.consume(scope))
        }
        test("monotonic clock regression refuses result") {
            val (f,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            f.now=99;check(!g.credentialResult(code,true))
        }
        test("second request while pending and ready is denied") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.begin(scope,"Diagnostic NOOP")==null)
            check(g.credentialResult(code,true));check(g.begin(scope,"Diagnostic NOOP")==null)
            check(g.consume(scope))
        }
        test("revoke ready on background refuses old approval") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(g.credentialResult(code,true));g.revokeReadyForBackground();check(!g.consume(scope))
        }
        test("bad digest and reserved action IDs never start prompt") {
            val (f,g)=make()
            check(g.begin(scope.copy(verb=24),"Diagnostic NOOP")==null)
            check(g.begin(scope.copy(proposalDigest="not-sha"),"Diagnostic NOOP")==null)
            check(f.launched==0)
        }
        test("an incorrect requestCode leaves actual pending challenge intact") {
            val (_,g)=make();val code=g.begin(scope,"Diagnostic NOOP")!!
            check(!g.credentialResult(code+1,true));check(g.credentialResult(code,true));check(g.consume(scope))
        }
        test("empty or excessive UI description is rejected") {
            val (f,g)=make()
            check(g.begin(scope," ")==null);check(g.begin(scope,"x".repeat(241))==null);check(f.launched==0)
        }
        println("UNO_OWNER_CONSENT_HOST_PASS=$passed")
    }
}
fun main(){OwnerConsentStateTest.run()}
