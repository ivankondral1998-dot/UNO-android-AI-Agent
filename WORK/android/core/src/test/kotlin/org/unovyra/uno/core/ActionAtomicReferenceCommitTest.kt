package org.unovyra.uno.core

import java.io.RandomAccessFile
import java.nio.file.Files
import java.security.MessageDigest
import java.util.concurrent.atomic.AtomicInteger

/** JVM reference journal transaction tests; NOT Android authority or actual A_tx proof. */
object ActionAtomicReferenceCommitTest {
    var pass = 0
    private val effect = mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY")
    private fun case(label: String, body: () -> Unit) {
        body();pass++;println("PASS REF_TXN $label")
    }
    private fun journalFile() = Files.createTempDirectory("uno-ref-txn-").resolve("journal.bin").toFile()
    private fun proposal() = Proposal(15, "private|record".toByteArray(), "fixture-model", 11, "trace")
    private fun prepare(c: TrustController): Ticket {
        val p = proposal()
        val consent = Consent(c.proposalDigest(p), effect.getValue(15), 100, c.epoch,c.nonce,true)
        return c.prepare(p, consent, 0, 100) ?: error("ticket not issued")
    }
    private class FakeNative(val result: NativeEndpoint=NativeEndpoint.TRUE) : NativePort {
        val calls=AtomicInteger()
        var evidence: (Ticket,Long)->NativeEvidence = { t,now ->
            NativeEvidence(t.id, NativeEndpoint.TRUE,1,now,trustedSourceTag)
        }
        override val trustedSourceTag = "REF_TXN_FAKE"
        override fun dispatch(ticket:Ticket):NativeEndpoint {calls.incrementAndGet();return result}
        override fun readback(ticket:Ticket,nowNanos:Long)=evidence(ticket,nowNanos)
    }
    private fun recordSpans(file: java.io.File): List<Pair<Int,Int>> {
        val data=file.readBytes();val spans=ArrayList<Pair<Int,Int>>();var index=0
        while(index<data.size){
            check(data.size-index>=4)
            val len=((data[index].toInt() and 255) shl 24) or
                ((data[index+1].toInt() and 255) shl 16) or
                ((data[index+2].toInt() and 255) shl 8) or
                (data[index+3].toInt() and 255)
            check(len in 13..512)
            val end=index+4+len+32;check(end<=data.size)
            spans+=index to end;index=end
        }
        return spans
    }
    /** Mutate the last v2 record and recompute unkeyed SHA; parser still must reject semantics. */
    private fun corruptLastPayloadWithValidHash(file:java.io.File, mutate:(ByteArray,Int,Int)->Unit) {
        val data=file.readBytes();val spans=recordSpans(file);check(spans.size>=3)
        val (start,end)=spans.last();val payloadStart=start+4;val payloadLength=end-start-36
        mutate(data,payloadStart,payloadLength)
        val previousHash=if(spans.size==1) ByteArray(32) else data.copyOfRange(spans[spans.size-2].second-32,spans[spans.size-2].second)
        val next=MessageDigest.getInstance("SHA-256").digest(previousHash+data.copyOfRange(payloadStart,payloadStart+payloadLength))
        next.copyInto(data,end-32)
        file.writeBytes(data)
    }
    fun run() {
        case("single v2 record binds used and source-tagged receipt after native") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val native=FakeNative();val c=TrustController(native,InMemoryLedger(),effect,j)
                val t=prepare(c);check(c.dispatchOutcome(t,5)==DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                val countBefore=recordSpans(f).size;check(countBefore==2)
                check(c.readbackAndCommit(t,6) && native.calls.get()==1 && t.used)
                check(recordSpans(f).size==countBefore+1)
                val row=j.snapshot().single();check(row.phase==ActionIntentJournal.Phase.REFERENCE_USED_RECEIPT)
                check(row.used && row.receipt?.observedAtNanos==6L)
            }
            ActionIntentJournal(f).use {j->
                val row=j.snapshot().single();check(row.used && row.recovered)
                check(row.receipt?.endpoint==NativeEndpoint.TRUE)
                check(row.phase==ActionIntentJournal.Phase.REFERENCE_USED_RECEIPT)
                check(!j.arm(row.id,row.proposalSha256))
            }
        }
        case("legacy v1 receipt replays but does NOT imply durable used") {
            val f=journalFile();val digest="a".repeat(64)
            ActionIntentJournal(f).use {j->
                check(j.prepare("legacy",digest))
                check(j.arm("legacy",digest))
                check(j.recordReadbackClaim("legacy",digest,
                    NativeEvidence("legacy",NativeEndpoint.TRUE,1,5,"LEGACY_FAKE")))
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.RECEIPT_RECORDED)
                check(!j.snapshot().single().used)
            }
            ActionIntentJournal(f).use {j->
                val row=j.snapshot().single()
                check(row.recovered && !row.used)
                check(row.phase==ActionIntentJournal.Phase.RECEIPT_RECORDED)
                check(!j.recordReferenceUsedReceipt("legacy",digest,
                    NativeEvidence("legacy",NativeEndpoint.TRUE,1,5,"LEGACY_FAKE")))
            }
        }
        case("a second reference commit is rejected without extra bytes") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j)
                val t=prepare(c);c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
                val bytes=f.length();val count=recordSpans(f).size
                check(!j.recordReferenceUsedReceipt(t.id,t.proposalDigest,
                    NativeEvidence(t.id,NativeEndpoint.TRUE,2,7,"REF_TXN_FAKE")))
                check(!c.readbackAndCommit(t,7));check(f.length()==bytes && recordSpans(f).size==count)
            }
        }
        case("unknown native result never writes a durable used flag") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val n=FakeNative(NativeEndpoint.UNKNOWN)
                val c=TrustController(n,InMemoryLedger(),effect,j);val t=prepare(c)
                check(c.dispatchOutcome(t,5)==DispatchAttempt.Invoked(NativeEndpoint.UNKNOWN))
                check(!c.readbackAndCommit(t,6) && !t.used)
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
                check(j.snapshot().single().used==false)
            }
        }
        case("not a fake in-memory ledger: reference commit is denied") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val ledger=object:DurableLedger {
                    override fun prepare(ticket:Ticket)=true
                    override fun commit(ticket:Ticket,evidence:NativeEvidence)=error("should never call independent persistent ledger")
                    override fun unresolved():List<Ticket> = emptyList()
                }
                val c=TrustController(FakeNative(),ledger,effect,j);val t=prepare(c)
                check(c.dispatchOutcome(t,5)==DispatchAttempt.Invoked(NativeEndpoint.TRUE))
                check(!c.readbackAndCommit(t,6) && !t.used && t.phase==Phase.MAY_HAVE_EXECUTED)
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        case("pre-dispatch STOP yields only PREPARED, no used receipt") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val n=FakeNative();val c=TrustController(n,InMemoryLedger(),effect,j);val t=prepare(c)
                c.stop();check(c.dispatchOutcome(t,5) is DispatchAttempt.Rejected)
                check(n.calls.get()==0 && !j.snapshot().single().used)
                check(recordSpans(f).size==1)
            }
        }
        case("STOP after invocation blocks used even with positive fake readback") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j);val t=prepare(c)
                c.dispatchOutcome(t,5);j.stop()
                check(!c.readbackAndCommit(t,6))
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        case("checksum-correct malformed used marker cannot replay as committed") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j);val t=prepare(c)
                c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            corruptLastPayloadWithValidHash(f){data,start,len->data[start+len-1]=2}
            val len=f.length()
            var refused=false
            try{ActionIntentJournal(f).close()}catch(_:java.io.IOException){refused=true}
            check(refused && f.length()==len)
        }
        case("v2 commit with v1 record header and valid SHA cannot replay") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j);val t=prepare(c)
                c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            corruptLastPayloadWithValidHash(f){data,start,_->data[start]=1}
            var refused=false
            try{ActionIntentJournal(f).close()}catch(_:java.io.IOException){refused=true}
            check(refused)
        }
        case("torn v2 record fails closed, no automatic truncation") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j);val t=prepare(c)
                c.dispatchOutcome(t,5);check(c.readbackAndCommit(t,6))
            }
            RandomAccessFile(f,"rw").use {it.setLength(it.length()-1)}
            val len=f.length();var refused=false
            try{ActionIntentJournal(f).close()}catch(_:java.io.IOException){refused=true}
            check(refused && f.length()==len)
        }
        case("readback mismatched source never creates used receipt") {
            val f=journalFile()
            ActionIntentJournal(f).use {j->
                val n=FakeNative();n.evidence={t,now->NativeEvidence(t.id,NativeEndpoint.TRUE,1,now,"OTHER_SOURCE")}
                val c=TrustController(n,InMemoryLedger(),effect,j);val t=prepare(c)
                c.dispatchOutcome(t,5)
                check(!c.readbackAndCommit(t,6) && !t.used)
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED)
            }
        }
        case("recovered used receipt cannot invoke native again with old ticket") {
            val f=journalFile();lateinit var old:Ticket
            ActionIntentJournal(f).use {j->
                val c=TrustController(FakeNative(),InMemoryLedger(),effect,j);old=prepare(c)
                c.dispatchOutcome(old,5);check(c.readbackAndCommit(old,6))
            }
            ActionIntentJournal(f).use {j->
                val native=FakeNative();val c=TrustController(native,InMemoryLedger(),effect,j)
                check(c.dispatchOutcome(old,7)===DispatchAttempt.Unresolved)
                check(native.calls.get()==0)
                check(j.snapshot().single().used)
            }
        }
        println("ACTION_ATOMIC_REFERENCE_COMMIT_PASS=$pass")
    }
}
fun main(){ActionAtomicReferenceCommitTest.run()}
