package org.unovyra.uno.core

/** Compiles and runs with standalone kotlinc/jdk, no Android SDK or JUnit needed. */
object CoreSelfTest {
    var pass=0
    fun checkCase(name:String,block:()->Unit) { block(); pass++;println("PASS $name") }
    fun run() {
        checkCase("no weights is fail closed") {
            var denied=false
            try { NoWeightsNeuralPort().perceive(Percept(PerceptType.TEXT,byteArrayOf(0),"owner",1)) }
            catch(e: IllegalStateException) { denied=e.message=="MODEL_NOT_TRAINED_OR_LOADED" }
            check(denied)
        }
        checkCase("default closed effect catalogue") {
            val t=TrustController(FakeNotesPort(),InMemoryLedger())
            val p=Proposal(15,"n|text".toByteArray(),"fixture",1,"h")
            val c=Consent(t.proposalDigest(p),"TEST",100,t.epoch,t.nonce,true)
            check(t.prepare(p,c,0,100)==null)
        }
        checkCase("approved test effect with exact consent") {
            val ledger=InMemoryLedger();val n=FakeNotesPort()
            val t=TrustController(n,ledger,mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val p=Proposal(15,"n|text".toByteArray(),"fixture",1,"h")
            val c=Consent(t.proposalDigest(p),"LOCAL_NOTE_CREATE_TEST_ONLY",10,t.epoch,t.nonce,true)
            val req=t.prepare(p,c,0,100)!!
            check(t.dispatch(req,1)==NativeEndpoint.TRUE)
            check(t.readbackAndCommit(req,2))
            check(!t.readbackAndCommit(req,2));check(req.used)
        }
        checkCase("stale digest cannot authorize") {
            val t=TrustController(FakeNotesPort(),InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val p=Proposal(15,"a|b".toByteArray(),"fixture",1,"h")
            val c=Consent("wrong","LOCAL_NOTE_CREATE_TEST_ONLY",10,t.epoch,t.nonce,true)
            check(t.prepare(p,c,0,10)==null)
        }
        checkCase("STOP gates native dispatch") {
            val n=FakeNotesPort();val t=TrustController(n,InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val p=Proposal(15,"n|text".toByteArray(),"fixture",1,"h")
            val c=Consent(t.proposalDigest(p),"LOCAL_NOTE_CREATE_TEST_ONLY",10,t.epoch,t.nonce,true)
            val ticket=t.prepare(p,c,0,20)!!
            t.stop();check(t.dispatch(ticket,1)==NativeEndpoint.UNKNOWN);check(ticket.phase==Phase.CANCELLED)
        }
        checkCase("crash never autocommits") {
            val n=FakeNotesPort();val t=TrustController(n,InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val p=Proposal(15,"n|text".toByteArray(),"fixture",1,"h")
            val c=Consent(t.proposalDigest(p),"LOCAL_NOTE_CREATE_TEST_ONLY",10,t.epoch,t.nonce,true)
            val ticket=t.prepare(p,c,0,20)!!
            t.dispatch(ticket,1);t.recoverAfterProcessDeath()
            check(ticket.phase==Phase.MAY_HAVE_EXECUTED)
            check(!t.readbackAndCommit(ticket,3))
        }
        checkCase("exact memory conflict and truncate") {
            val m=ExactMemory();m.write("owner","f","A".toByteArray(),100,0,EntryKind.OBSERVED,"native")
            m.write("owner","f","B".toByteArray(),100,0,EntryKind.OBSERVED,"native")
            check(m.read("owner","f",2,2,1,0).status==ExactStatus.CONFLICT)
            check(m.read("owner","f",1,2,1,0).status==ExactStatus.TRUNCATED)
        }
        checkCase("revocation blocks exact retrieval") {
            val m=ExactMemory();m.write("owner","f","A".toByteArray(),100,0,EntryKind.OBSERVED,"native")
            m.revoke("owner");check(m.read("owner","f",2,2,1,0).status==ExactStatus.DENIED)
        }
        checkCase("queue priority and STOP latch") {
            val q=BoundedScheduler(1)
            check(q.enqueue(Priority.SENSOR,"sensor",100))
            check(!q.enqueue(Priority.INTERNAL,"overflow",100))
            check(q.enqueue(Priority.STOP,"STOP",0))
            check(q.stopLatch.get())
            check(q.poll()!!.priority==Priority.SENSOR)
        }
        checkCase("unknown OS verbs denied") {
            val t=TrustController(FakeNotesPort(),InMemoryLedger(),mapOf(15 to "LOCAL_NOTE_CREATE_TEST_ONLY"))
            val p=Proposal(24,byteArrayOf(1),"fixture",1,"h")
            check(t.prepare(p,Consent(t.proposalDigest(p),"LOCAL_NOTE_CREATE_TEST_ONLY",10,t.epoch,t.nonce,true),0,10)==null)
        }
    }
}
fun main(){ CoreSelfTest.run();println("KOTLIN_CORE_PASS=${CoreSelfTest.pass}") }
