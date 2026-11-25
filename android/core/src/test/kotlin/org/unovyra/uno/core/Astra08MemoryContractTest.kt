package org.unovyra.uno.core

import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption
import java.nio.channels.FileChannel
import javax.crypto.KeyGenerator

/** Real file replacement plus controlled faults, not an Android power-cut test. */
object Astra08MemoryContractTest {
    var pass = 0
    private fun verify(label: String, ok: Boolean) { check(ok) { label }; pass++; println("PASS ASTRA08 $label") }
    private enum class Fault { NONE, BEFORE, AFTER, SILENT, TORN, READ_ERROR }
    private class Disk(private val path: java.nio.file.Path) {
        var fault = Fault.NONE
        var unreadable = false
        fun load(): ByteArray? {
            check(!unreadable) { "injected read failure" }
            return if (Files.exists(path)) Files.readAllBytes(path) else null
        }
        fun persist(bytes: ByteArray) {
            if (fault == Fault.BEFORE) error("before replacement")
            if (fault == Fault.SILENT) return
            val tmp = path.resolveSibling(path.fileName.toString() + ".new")
            Files.write(tmp, if (fault == Fault.TORN) bytes.copyOf(7) else bytes)
            FileChannel.open(tmp, StandardOpenOption.WRITE).use { it.force(true) }
            Files.move(tmp, path, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
            if (fault == Fault.READ_ERROR) unreadable = true
            if (fault == Fault.AFTER || fault == Fault.TORN) error("after replacement")
        }
    }
    fun run() {
        val dir = Files.createTempDirectory("uno08-")
        try {
            val key = KeyGenerator.getInstance("AES").apply { init(128) }.generateKey()
            val exact = Disk(dir.resolve("exact")); val index = Disk(dir.resolve("index"))
            var now = 10L
            fun vault() = UnoEncryptedExactMemory(key,"boot",exact::load,exact::persist){now}
            fun summaries() = UnoSemanticMemory(key,"boot",index::load,index::persist)
            val v = vault(); val s = summaries(); val ports = UnoMemoryPorts(v,s)
            val a = S4Access("owner",10,3,16)
            val q = DoubleArray(8){0.5}
            fun bank(p: UnoMemoryPorts = ports, access: S4Access = a) = p.withS4Bank(access,8){it}
            fun row(scope:String = "owner") = v.write(scope,"fact",byteArrayOf(7),100,3,EntryKind.USER_DECLARATION,"OWNER_UI")
            verify("known_empty",bank().status == S4Status.EMPTY)
            verify("unavailable_index_not_empty",bank(UnoMemoryPorts(v,null)).let{it.status == S4Status.UNKNOWN && it.reason == S4Reason.INDEX_UNAVAILABLE})
            val r = row(); ports.linkSummary(r,q,a)
            verify("live_link",bank().hits.single().exactId == r.id)
            verify("callback_index_mutation_rejected",runCatching { ports.withS4Bank(a,8) {
                ports.linkSummary(r,q,a); it
            } }.isFailure)
            verify("reason_exact_budget",ports.recallSummary(a.copy(scanBudget=0),q,1).catalogueReason == S4Reason.SCAN_LIMIT)
            verify("reason_combined_budget",ports.recallSummary(a.copy(scanBudget=1),q,1).catalogueStatus == S4Status.BUDGET_EXCEEDED)
            verify("reason_wrong_epoch",ports.recallSummary(a.copy(consentEpoch=4),q,1).catalogueReason == S4Reason.STALE_LINK)
            verify("incompatible_width",ports.recallSummary(a,DoubleArray(2){0.5},1).catalogueStatus == S4Status.INCOMPATIBLE)
            now=100
            verify("expiry_equality",bank().reason == S4Reason.STALE_LINK && bank().hits.isEmpty())
            now=10
            val before = exact.load()!!
            exact.fault=Fault.BEFORE
            verify("precommit_failure_throws",runCatching{ports.revoke("owner")}.isFailure)
            verify("confirmed_old_snapshot_retained",exact.load()!!.contentEquals(before) && bank().status==S4Status.COMPLETE)
            exact.fault=Fault.SILENT
            verify("silent_noop_not_committed",runCatching{ports.revoke("owner")}.isFailure && bank().status==S4Status.COMPLETE)
            exact.fault=Fault.AFTER
            verify("ambiguous_commit_no_success",runCatching{ports.withS4Bank(a,8) {
                check(runCatching { ports.revoke("owner") }.isFailure); it
            }}.isFailure)
            verify("ambiguous_commit_quarantines_exact",v.read("owner","fact",1,16,10,3).status==ExactStatus.UNKNOWN && bank().status==S4Status.UNKNOWN)
            verify("ambiguous_commit_blocks_generation_and_write",runCatching{v.generation}.isFailure && runCatching{row("other")}.isFailure)
            exact.fault=Fault.NONE
            val reopened = vault(); val reopenedPorts = UnoMemoryPorts(reopened,summaries())
            verify("persisted_tombstone_denies_after_reopen",bank(reopenedPorts).status == S4Status.DENIED)
            verify("deny_even_missing_index",bank(UnoMemoryPorts(reopened,null)).status == S4Status.DENIED)
            verify("stale_index_cannot_link",runCatching{reopenedPorts.linkSummary(r,q,a)}.isFailure)
            index.fault=Fault.BEFORE
            verify("cleanup_failure_pending",reopenedPorts.revoke("owner")==S4Revocation.REVOKED_CLEANUP_PENDING)
            verify("cleanup_failure_does_not_regrant",bank(UnoMemoryPorts(vault(),summaries())).status==S4Status.DENIED)
            index.fault=Fault.NONE
            verify("cleanup_retry_idempotent",reopenedPorts.revoke("owner")==S4Revocation.REVOKED_CLEAN && reopenedPorts.revoke("owner")==S4Revocation.REVOKED_CLEAN)
            val other = reopened.write("other","fact",byteArrayOf(8),100,3,EntryKind.OBSERVED,"LOCAL_UI")
            val aa=a.copy(scope="other")
            reopenedPorts.linkSummary(other,q,aa)
            verify("unrelated_scope_live",bank(reopenedPorts,aa).status==S4Status.COMPLETE)
            index.fault=Fault.AFTER
            verify("index_ambiguous_update_throws",runCatching{reopenedPorts.linkSummary(other,DoubleArray(8){-0.5},aa)}.isFailure)
            verify("index_ambiguous_update_quarantined",bank(reopenedPorts,aa).reason==S4Reason.INDEX_UNAVAILABLE)
            index.fault=Fault.NONE
            verify("index_reopened_from_new_bytes",bank(UnoMemoryPorts(vault(),summaries()),aa).hits.single().vector[0]==-0.5)
            val fresh=vault()
            exact.fault=Fault.READ_ERROR
            verify("readback_unavailable_quarantines",runCatching{fresh.revoke("other")}.isFailure && fresh.read("other","fact",1,16,10,3).status==ExactStatus.UNKNOWN)
            exact.fault=Fault.NONE;exact.unreadable=false
            verify("second_tombstone_persisted",bank(UnoMemoryPorts(vault(),summaries()),aa).status==S4Status.DENIED)
            val torn=vault(); exact.fault=Fault.TORN
            verify("torn_snapshot_quarantined",runCatching{torn.write("third","fact",byteArrayOf(9),100,3,EntryKind.OBSERVED,"LOCAL_UI")}.isFailure && runCatching{torn.generation}.isFailure)
            exact.fault=Fault.NONE
            verify("torn_snapshot_not_reinitialized",runCatching{vault()}.isFailure && exact.load()!!.size==7)
            val exact2=ExactMemory();var index2Bytes:ByteArray?=null
            val index2=UnoSemanticMemory(key,"boot",{index2Bytes?.copyOf()},{index2Bytes=it.copyOf()},dimension=8)
            val ports2=UnoMemoryPorts(exact2,index2)
            val pos=exact2.write("owner","one",byteArrayOf(1),100,3,EntryKind.OBSERVED,"LOCAL_UI")
            val zero=exact2.write("owner","two",byteArrayOf(2),100,3,EntryKind.OBSERVED,"LOCAL_UI")
            ports2.linkSummary(pos,q,a);ports2.linkSummary(zero,DoubleArray(8),a)
            verify("S4_keeps_valid_zero_vector",bank(ports2).let{it.status==S4Status.COMPLETE && it.hits.size==2})
            val summary=ports2.recallSummary(a,q,2)
            verify("undefined_cosine_never_claims_partial_summary_complete",summary.status==SemanticStatus.UNKNOWN && summary.hits.isEmpty())
            verify("exact_tombstone_denies_both_paths",ports2.revoke("owner")==S4Revocation.REVOKED_CLEAN &&
                ports2.recallExact("owner","one",2,16,10,3).status==ExactStatus.DENIED && bank(ports2).status==S4Status.DENIED)
            println("UNO_ASTRA08_MEMORY_HOST_PASS=$pass")
        } finally { dir.toFile().deleteRecursively() }
    }
}
