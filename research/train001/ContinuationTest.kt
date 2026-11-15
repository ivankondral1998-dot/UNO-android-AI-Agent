package org.unovyra.uno.research

import java.nio.file.*
import kotlin.math.abs

private fun rejects(block:()->Unit) {var caught=false;try {block()} catch(e:IllegalArgumentException) {caught=true};check(caught)}
fun main() {
    val t=ReverseF();val q=t.leaf("q",doubleArrayOf(.3));val k=t.leaf("k",doubleArrayOf(.2))
    val ce=TrainLoss.retrieval(t,q,listOf(k),0)
    check(ce.x[0]==0.0);t.backward(ce,doubleArrayOf(1.0))
    check(q.g[0]==0.0 && k.g[0]==0.0)
    rejects {TrainLoss.retrieval(ReverseF(),q,emptyList(),0)}
    println("SINGLETON_CE_ZERO_GRADIENT_PASS")
    val initialized=Ladder.model(47)
    val m=TrainModel(initialized.rules,initialized.values().mapValues {(_,v)->v.map {it*.9}.toDoubleArray()})
    for(rung in Ladder.rungs) for(length in Ladder.lengths) {
        val e=Ladder.example(rung,length,99,"example")
        val erased=Ladder.example(rung,length,99,"example",true)
        check(e.targetState.contentEquals(erased.targetState));check(e.targetRecord==erased.targetRecord)
        check(e.events.all {it.evidence.all {v->v==0.0}})
        // Independent scan of raw observed x, not generator's target selection.
        val writes=e.events.filter {it.write};val query=e.events.last().features
        val source=if(rung=="r5_order") writes.last() else writes.last {it.features[1]==query[1]}
        val answer=source.features[if(rung=="r5_order") 1 else 0]
        check(source.sequence==e.targetRecord && (answer>0)==(e.targetState[0]>0))
        if(length==96 && rung=="r2_two") {
            val replay=MemoryReplay(m.core(),m.memory("wk"),m.memory("wv"))
            rejects {replay.prefix(e.events,96,e.initial,booleanArrayOf(true),2)}
            rejects {replay.prefix(e.events,96,e.initial,booleanArrayOf(true),2,97)}
            val graph=replay.prefix(e.events,96,e.initial,booleanArrayOf(true),2,96)
            check(graph.states.size==96)
            check(graph.reads.indices.all {i->graph.reads[i].entries.all {it.stamp.sequence<e.events[i].sequence}})
            val p=LadderEval.predict(m,e)
            check(abs(graph.states.last().x[0]-p.state)<1e-14)
            graph.tape.backward(graph.states.last(),DoubleArray(64) {if(it==0) 1.0 else 0.0})
            val source=(e.targetRecord-1).toInt();val epsilon=1e-5
            val plus=Ladder.example(rung,length,99,"plus");plus.events[source].features[0]+=epsilon
            val minus=Ladder.example(rung,length,99,"minus");minus.events[source].features[0]-=epsilon
            val numeric=(LadderEval.predict(m,plus).state-LadderEval.predict(m,minus).state)/(2*epsilon)
            val analytic=graph.tape.leaves.getValue("event.$source").g[0]
            check(abs(analytic)>1e-10 && abs(numeric-analytic)<1e-10+abs(numeric)*1e-5)
            check(LadderEval.predict(m,e,"memory_off").key==null)
            println("LONG96_PLAIN_REFERENCE_FORWARD_CAUSAL_PASS sourceGradient numeric=$numeric analytic=$analytic")
        }
    }
    val data=Ladder.data("train",5,47);val c=Experiment(data.hash,totalSteps=4,maxUpdates=4,warmup=1,replayLimit=96,innerSteps=2,route=listOf(true))
    check(JointGraph.evaluate(m,data,1,c).loss.isFinite())
    // Finite differences of independent plain reference state objective: no retrieval/value derivative reuse.
    val stateConfig=c.copy(stateLoss=1.0,retrieveLoss=0.0,valueLoss=0.0)
    val stateEval=JointGraph.evaluate(m,data,1,stateConfig)
    for(name in listOf("wk","wv","wq","wr","projection","us")) {
        val coordinate=stateEval.gradient.getValue(name).indices.maxBy {abs(stateEval.gradient.getValue(name)[it])}
        val eps=1e-5
        fun objective(delta:Double):Double {
            val values=m.values();values.getValue(name)[coordinate]+=delta
            val candidate=TrainModel(m.rules,values)
            val e=data.example(1);val diff=LadderEval.predict(candidate,e).state-e.targetState[0]
            return diff*diff
        }
        val numeric=(objective(eps)-objective(-eps))/(2*eps)
        val analytic=stateEval.gradient.getValue(name)[coordinate]
        check(abs(numeric-analytic)<2e-10+abs(numeric)*2e-4) {"FD $name numeric=$numeric analytic=$analytic"}
        check(abs(analytic)>1e-16) {"DEAD_PATH $name"}
        println("PLAIN_DOUBLE_FD $name[$coordinate] numeric=$numeric analytic=$analytic")
    }
    val tmp=Files.createTempDirectory("uno-ladder-test-")
    val a=LadderRun(tmp.resolve("a"),4,2,5,47);val b=LadderRun(tmp.resolve("b"),4,2,5,47)
    val uninterrupted=a.open(false);a.advance(uninterrupted,4)
    val interrupted=b.open(false);b.advance(interrupted,2)
    val resumed=b.open(true);b.advance(resumed,4)
    check(uninterrupted.model.fingerprint()==resumed.model.fingerprint())
    check(Files.readAllBytes(a.checkpoint(4)).contentEquals(Files.readAllBytes(b.checkpoint(4))))
    val mixed=a.open(true)
    mixed.accumulate(JointGraph.evaluate(mixed.model,a.train,0,a.config))
    rejects {a.advance(mixed,4)}
    val wrongCursor=OfflineTrainer(a.template,a.config,OptimizerState(1,1,OfflineTrainer.zeros(a.template),OfflineTrainer.zeros(a.template)))
    rejects {a.advance(wrongCursor,1)}
    rejects {a.open(false)}
    rejects {LadderRun(tmp.resolve("b"),4,1,5,47).open(true)}
    val bytes=Files.readAllBytes(b.checkpoint(4));bytes[bytes.size/2]=(bytes[bytes.size/2].toInt() xor 1).toByte()
    Files.write(b.checkpoint(4),bytes);rejects {b.open(true)}
    println("BATCH_CURSOR_MANIFEST_CORRUPTION_EXACT_RESUME_PASS")
    val reportDir=tmp.resolve("locked");Files.createDirectory(reportDir)
    var crashed=false
    try {lockedReport(reportDir,"selection-sha",{throw IllegalStateException("simulated crash")})} catch(e:IllegalStateException) {crashed=true}
    check(crashed)
    check(lockedReport(reportDir,"selection-sha",{"complete metrics"})=="complete metrics")
    check(lockedReport(reportDir,"selection-sha",{error("MUST_NOT_REOPEN_TEST")})=="complete metrics")
    rejects {lockedReport(reportDir,"different selection",{"retune"})}
    println("LOCKED_TEST_CRASH_RETRY_PIN_AND_CACHED_RESULT_PASS")
    println("CONTINUATION_TESTS_PASS")
}
