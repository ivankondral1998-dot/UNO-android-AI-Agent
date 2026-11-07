package org.unovyra.uno.core

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger

/** Negative safety regressions for core foundation; fake native only, NOT Android authority. */
object FoundationHardeningTest {
    var pass=0
    private fun case(name:String, block:()->Unit) { block();pass++;println("PASS HARDENING $name") }
    private fun proposal()=Proposal(15,"note|approved".toByteArray(),"fixture",1,"trace")
    private fun prepared(native:NativePort=FakeNotesPort()):Pair<TrustController,Ticket> {
        val c=TrustController(native,InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
        val p=proposal()
        val consent=Consent(c.proposalDigest(p),"LOCAL_NOTE_CREATE_TEST_ONLY",100L,c.epoch,c.nonce,true)
        return c to (c.prepare(p,consent,0L,100L) ?: error("prepare failed"))
    }
    fun run() {
        case("mutable original proposal cannot change approved effect") {
            val source=proposal();val c=TrustController(FakeNotesPort(),InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val consent=Consent(c.proposalDigest(source),"LOCAL_NOTE_CREATE_TEST_ONLY",100L,c.epoch,c.nonce,true)
            val ticket=c.prepare(source,consent,0L,100L)!!
            source.canonicalArgs.fill(0)
            check(ticket.proposal.canonicalArgs.decodeToString()=="note|approved")
            check(c.dispatch(ticket,1L)==NativeEndpoint.TRUE)
        }
        case("native sees immutable snapshot while caller mutates ticket") {
            val entered=CountDownLatch(1);val proceed=CountDownLatch(1)
            var observed=""
            val native=object:NativePort {
                override val trustedSourceTag="SNAPSHOT_TEST"
                override fun dispatch(ticket:Ticket):NativeEndpoint {
                    entered.countDown();check(proceed.await(2,TimeUnit.SECONDS))
                    observed=ticket.proposal.canonicalArgs.decodeToString()
                    return NativeEndpoint.TRUE
                }
                override fun readback(ticket:Ticket,nowNanos:Long)=NativeEvidence(ticket.id,NativeEndpoint.TRUE,1,nowNanos,trustedSourceTag)
            }
            val (c,t)=prepared(native)
            val worker=Thread { check(c.dispatch(t,1L)==NativeEndpoint.TRUE) }
            worker.start();check(entered.await(2,TimeUnit.SECONDS))
            t.proposal.canonicalArgs.fill(42)
            proceed.countDown();worker.join(2000)
            check(!worker.isAlive && observed=="note|approved")
        }
        case("mutated issued ticket rejected") {
            val (c,t)=prepared()
            t.proposal.canonicalArgs[0]=42
            check(c.dispatch(t,1L)==NativeEndpoint.UNKNOWN)
            check(t.phase==Phase.DENIED)
        }
        case("forged never-issued ticket rejected") {
            val (c,t)=prepared()
            val fake=t.copy()
            check(c.dispatch(fake,1L)==NativeEndpoint.UNKNOWN)
        }
        case("ticket cannot redispatch after mutable phase reset") {
            val (c,t)=prepared()
            check(c.dispatch(t,1L)==NativeEndpoint.TRUE)
            t.phase=Phase.PREPARED
            t.used=false
            check(c.dispatch(t,2L)==NativeEndpoint.UNKNOWN)
        }
        case("negative native readback never commits success") {
            val native=object:NativePort {
                override val trustedSourceTag="NEGATIVE_TEST"
                override fun dispatch(ticket:Ticket)=NativeEndpoint.FALSE
                override fun readback(ticket:Ticket,nowNanos:Long)=NativeEvidence(ticket.id,NativeEndpoint.FALSE,1,nowNanos,trustedSourceTag)
            }
            val (c,t)=prepared(native)
            check(c.dispatch(t,1L)==NativeEndpoint.FALSE)
            check(!c.readbackAndCommit(t,2L))
            check(t.phase==Phase.DENIED && !t.used)
        }
        case("unknown native result remains MAY_HAVE_EXECUTED") {
            val native=object:NativePort {
                override val trustedSourceTag="UNKNOWN_TEST"
                override fun dispatch(ticket:Ticket)=NativeEndpoint.UNKNOWN
                override fun readback(ticket:Ticket,nowNanos:Long)=NativeEvidence(ticket.id,NativeEndpoint.UNKNOWN,0,nowNanos,trustedSourceTag)
            }
            val (c,t)=prepared(native)
            check(c.dispatch(t,1L)==NativeEndpoint.UNKNOWN)
            check(t.phase==Phase.MAY_HAVE_EXECUTED)
            check(c.dispatch(t,2L)==NativeEndpoint.UNKNOWN)
        }
        case("STOP prevents any subsequent native dispatch") {
            val calls=AtomicInteger(0)
            val native=object:NativePort {
                override val trustedSourceTag="COUNTING_TEST"
                override fun dispatch(ticket:Ticket):NativeEndpoint {calls.incrementAndGet();return NativeEndpoint.TRUE}
                override fun readback(ticket:Ticket,nowNanos:Long)=NativeEvidence(ticket.id,NativeEndpoint.TRUE,1,nowNanos,trustedSourceTag)
            }
            val (c,t)=prepared(native)
            c.stop()
            check(c.stopped)
            check(c.dispatch(t,1L)==NativeEndpoint.UNKNOWN)
            check(calls.get()==0)
        }
        case("memory write return cannot mutate stored bytes") {
            val m=ExactMemory()
            val source="fixed".toByteArray();val written=m.write("owner","key",source,100L,0,EntryKind.OBSERVED,"test")
            source[0]=42;written.raw[1]=42
            val read=m.read("owner","key",5,10,1L,0)
            check(read.status==ExactStatus.COMPLETE)
            check(read.entries.single().raw.decodeToString()=="fixed")
        }
        case("memory read result cannot mutate stored bytes") {
            val m=ExactMemory()
            m.write("owner","key","fixed".toByteArray(),100L,0,EntryKind.OBSERVED,"test")
            val a=m.read("owner","key",5,10,1L,0).entries.single()
            a.raw[0]=42
            val b=m.read("owner","key",5,10,1L,0)
            check(b.status==ExactStatus.COMPLETE)
            check(b.entries.single().raw.decodeToString()=="fixed")
        }
        case("missing exact key explicitly NOT_FOUND") {
            val m=ExactMemory()
            check(m.read("owner","missing",1,1,1L,0).status==ExactStatus.NOT_FOUND)
        }
        case("expired queued events discarded") {
            val q=BoundedScheduler(2)
            check(q.enqueue(Priority.SENSOR,"old",10L))
            check(q.enqueue(Priority.OWNER,"fresh",40L))
            check(q.poll(20L)?.payload=="fresh")
            check(q.poll(20L)==null)
        }
        case("STOP clears queued events and is one-way") {
            val q=BoundedScheduler(3)
            check(q.enqueue(Priority.OWNER,"old",100L))
            check(q.enqueue(Priority.REVOKE,"revoke",0L))
            check(q.isStopped() && q.size()==0 && q.poll()==null)
            check(!q.enqueue(Priority.OWNER,"new",100L))
        }
        println("FOUNDATION_HARDENING_PASS=$pass")
    }
}
