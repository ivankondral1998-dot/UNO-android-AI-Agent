package org.unovyra.uno

import java.io.File
import java.nio.file.Files

object AppPrivateReadbackProbeHostTest {
    @JvmStatic fun main(args: Array<String>) {
        val root = Files.createTempDirectory("uno-private-effect-test-").toFile()
        var passed = 0
        fun checkCase(label: String, block: () -> Unit) {
            block(); passed++; println("PASS $label")
        }
        try {
            checkCase("STOP before write creates nothing") {
                val r = AppPrivateReadbackProbe.run(root) { true }
                check(r.status == AppPrivateReadbackProbe.Status.DENIED)
                check(!File(root,"uno_local_effect_probe_v1").exists())
            }
            val first = AppPrivateReadbackProbe.run(root) { false }
            checkCase("create and readback actual bytes") {
                check(first.status == AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES)
                check(first.id != null && first.digest?.length == 64)
            }
            checkCase("independent reopened descriptor matches") {
                val r = AppPrivateReadbackProbe.inspect(root,first.id!!)
                check(r.status == AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES)
                check(r.digest == first.digest)
            }
            checkCase("invalid id traversal rejected") {
                check(AppPrivateReadbackProbe.inspect(root,"../../etc/passwd").status ==
                    AppPrivateReadbackProbe.Status.DENIED)
            }
            checkCase("tampered bytes never report verified") {
                File(File(root,"uno_local_effect_probe_v1"),first.id + ".txt").appendText("tamper")
                check(AppPrivateReadbackProbe.inspect(root,first.id!!).status ==
                    AppPrivateReadbackProbe.Status.UNKNOWN_MAY_HAVE_WRITTEN)
            }
            checkCase("unique new marker never overwrites prior") {
                val second = AppPrivateReadbackProbe.run(root) { false }
                check(second.status == AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES)
                check(second.id != first.id)
            }
            checkCase("limit prevents unbounded disk writes") {
                repeat(14) { check(AppPrivateReadbackProbe.run(root) { false }.status ==
                    AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES) }
                check(AppPrivateReadbackProbe.run(root) { false }.status ==
                    AppPrivateReadbackProbe.Status.DENIED)
                check(File(root,"uno_local_effect_probe_v1").listFiles()!!.size == 16)
            }
            checkCase("missing private root fails closed") {
                check(AppPrivateReadbackProbe.run(File(root,"missing")) { false }.status ==
                    AppPrivateReadbackProbe.Status.UNAVAILABLE)
            }
            checkCase("readback of missing id fails closed") {
                check(AppPrivateReadbackProbe.inspect(root,"probe_"+"0".repeat(32)).status ==
                    AppPrivateReadbackProbe.Status.UNAVAILABLE)
            }
            // Owner STOP is sticky for new writes but never prevents a read-only recovery.
            val stoppedRoot = File(root, "stop_scope").also { check(it.mkdir()) }
            val stored = AppPrivateReadbackProbe.run(stoppedRoot) { false }
            check(stored.status == AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES)
            val storedId = stored.id!!
            AppPrivateReadbackProbe.stop()
            checkCase("owner STOP blocks fresh writes even with an unstopped callback") {
                val prior = File(stoppedRoot, "uno_local_effect_probe_v1").listFiles()!!.size
                val denied = AppPrivateReadbackProbe.run(stoppedRoot) { false }
                check(denied.status == AppPrivateReadbackProbe.Status.DENIED)
                check(denied.detail == "STOP_BEFORE_CREATE")
                check(File(stoppedRoot, "uno_local_effect_probe_v1").listFiles()!!.size == prior)
            }
            checkCase("owner STOP stays latched across a subsequent call") {
                check(AppPrivateReadbackProbe.run(stoppedRoot) { false }.status ==
                    AppPrivateReadbackProbe.Status.DENIED)
            }
            checkCase("read-only reopen remains possible after owner STOP") {
                check(AppPrivateReadbackProbe.inspect(stoppedRoot, storedId).status ==
                    AppPrivateReadbackProbe.Status.VERIFIED_LOCAL_BYTES)
            }
            println("UNO_APP_PRIVATE_EFFECT_HOST_PASS=$passed")
        } finally {
            // Only temporary host-test fixtures; never Android owner data.
            root.deleteRecursively()
        }
    }
}
