package org.unovyra.uno.research

import org.unovyra.uno.core.*
import kotlin.math.*
import java.nio.file.*
import java.io.*
private var tests=0
internal fun checkNear(name:String, actual:Double, expected:Double, tol:Double=1e-11) {
    println("CHECK $name expected=$expected actual=$actual tol=$tol error=${abs(actual-expected)}")
    check(actual.isFinite() && expected.isFinite() && abs(actual-expected)<=tol) {name};tests++
}
private fun rejected(name:String,action:()->Unit) {
    var threw=false
    try {action()} catch(e:Exception) {if(e is IllegalArgumentException || e is EOFException) {
        threw=true;println("REJECT $name ${e.message ?: e.javaClass.simpleName}")
    } else throw e}
    check(threw) {name};tests++
}
private fun equalMaps(name:String,a:Map<String,DoubleArray>,b:Map<String,DoubleArray>,tol:Double=0.0) {
    check(a.keys==b.keys)
    for(n in a.keys) checkNear("$name.$n",a.getValue(n).indices.maxOf {abs(a.getValue(n)[it]-b.getValue(n)[it])},0.0,tol)
}
/** Independent objective: plain Double math + original core forward, no tape losses/gradients. */
private fun plain(m:TrainModel,e:TrainingExample,c:Experiment):Double {
    val w=m.core();var state=e.initial.copyOf()
    val memory=mutableListOf<Pair<MemoryReplay.Event,UnoRefMemoryVector>>()
    var terminalKeys=emptyList<UnoRefMemoryVector>();var terminalRecords=emptyList<Long>();var lastQ=DoubleArray(128)
    for(event in e.events) {
        val eligible=memory.filter {(x,_)->x.sequence<event.sequence && x.time<=event.time && event.time<x.expiry && x.scope==event.scope && x.version==event.version && x.sequence !in event.revoked}
        val f=w.projection.multiply(event.features);val s=w.us.multiply(state)
        val z0=DoubleArray(128) {tanh(f[it]+s[it]+w.e[it]+w.bias[it])}
        lastQ=w.wq.multiply(z0).map {tanh(it)}.toDoubleArray()
        terminalKeys=eligible.map {it.second};terminalRecords=eligible.map {it.first.sequence}
        state=UnoFReference(w).forward(UnoRefEvent(event.features,DoubleArray(32),state,DoubleArray(128),terminalKeys),c.route.toBooleanArray(),c.innerSteps).state
        if(event.write) memory.add(event to UnoRefMemoryVector(m.memory("wk").multiply(state).map {tanh(it)}.toDoubleArray(),
            m.memory("wv").multiply(state).mapIndexed {i,v -> tanh(v+event.evidence[i])}.toDoubleArray()))
    }
    val target=terminalRecords.indexOf(e.targetRecord);require(target>=0 && terminalKeys.size>=2)
    fun mse(x:DoubleArray,y:DoubleArray,mask:BooleanArray)=x.indices.sumOf {if(mask[it]) (x[it]-y[it]).pow(2) else 0.0}/mask.count {it}
    val logits=terminalKeys.map {k ->lastQ.indices.sumOf {lastQ[it]*k.key[it]}/sqrt(128.0)}
    val max=logits.max();val ce=ln(logits.sumOf {exp(it-max)})+max-logits[target]
    return c.stateLoss*mse(state,e.targetState,e.stateValid)+c.retrieveLoss*ce+c.valueLoss*mse(terminalKeys[target].value,e.targetValue,e.valueValid)
}
private fun scalarModel(value:Double=0.0,frozen:Set<Int> = emptySet())=
    TrainModel(listOf(TensorRule("x",1,2,1.0,false,frozen)),mapOf("x" to doubleArrayOf(value,0.0)))
private fun eval(t:OfflineTrainer,x:DoubleArray)=Evaluation(t.model.fingerprint(),sha256(configBytes(t.config)),1.0,listOf(1.0),mapOf("x" to x))
private fun lossTests() {
    val t=ReverseF();val x=t.leaf("x",doubleArrayOf(.2,-.3))
    val l=TrainLoss.mse(t,x,doubleArrayOf(.6,.1),booleanArrayOf(true,true))
    checkNear("mse.value",l.x[0],.16)
    t.backward(l,doubleArrayOf(1.0));checkNear("mse.gradient",x.g[0],-.4)
    rejected("all missing mask") {TrainLoss.mse(ReverseF(),ReverseF.V(doubleArrayOf(0.0)),doubleArrayOf(0.0),booleanArrayOf(false))}
    rejected("nonfinite valid target") {TrainLoss.mse(ReverseF(),ReverseF.V(doubleArrayOf(0.0)),doubleArrayOf(Double.NaN),booleanArrayOf(true))}
    val masked=ReverseF();val a=masked.leaf("a",doubleArrayOf(.3,9.0))
    val loss=TrainLoss.mse(masked,a,doubleArrayOf(.1,Double.NaN),booleanArrayOf(true,false))
    masked.backward(loss,doubleArrayOf(1.0));checkNear("masked.gradient",a.g[1],0.0,0.0)
    val ce=ReverseF();val q=ce.leaf("q",doubleArrayOf(1.0))
    val k1=ce.leaf("k1",doubleArrayOf(1000.0));val k2=ce.leaf("k2",doubleArrayOf(-1000.0))
    val cross=TrainLoss.retrieval(ce,q,listOf(k1,k2),1);ce.backward(cross,doubleArrayOf(1.0))
    checkNear("extreme.CE",cross.x[0],2000.0);checkNear("extreme.CE.gradient",q.g[0],2000.0)
    rejected("singleton target") {TrainLoss.retrieval(ReverseF(),q,listOf(k1),0)}
}
private fun graphTests(model:TrainModel,examples:List<TrainingExample>,c:Experiment):Evaluation {
    val dataset=TrainingDataset(examples);val e=dataset.example(0);val full=JointGraph.evaluate(model,dataset,0,c)
    checkNear("joint.loss.independent",full.loss,plain(model,e,c),2e-14)
    val components=listOf(c.copy(stateLoss=1.0,retrieveLoss=0.0,valueLoss=0.0),c.copy(stateLoss=0.0,retrieveLoss=1.0,valueLoss=0.0),c.copy(stateLoss=0.0,retrieveLoss=0.0,valueLoss=1.0))
        .map {JointGraph.evaluate(model,dataset,0,it)}
    val coefficients=listOf(c.stateLoss,c.retrieveLoss,c.valueLoss)
    checkNear("joint.loss.additivity",full.loss,components.indices.sumOf {components[it].loss*coefficients[it]},2e-14)
    for(r in model.rules) {
        val g=full.gradient.getValue(r.name)
        checkNear("joint.gradient.additivity.${r.name}",g.indices.maxOf {i ->abs(g[i]-components.indices.sumOf {components[it].gradient.getValue(r.name)[i]*coefficients[it]})},0.0,3e-15)
    }
    // Actual memory and F/state paths must carry information, not only a loss scalar.
    for(n in listOf("wk","wv","projection","us","wq","wr","branch.0.0.a","branch.0.0.c","branch.0.0.b")) {
        val max=full.gradient.getValue(n).maxOf {abs(it)};println("SIGNAL $n=$max required>1e-8");check(max>1e-8);tests++
    }
    for(n in listOf("wk","wv","projection","us","wq","wr","e","bias","branch.0.0.a","branch.0.0.c","branch.0.0.b","branch.0.0.ab","branch.0.0.bb")) {
        val values=model.values();val x=values.getValue(n)
        val ids=listOf(0,1,minOf(x.lastIndex,128)).distinct()
        for(index in ids) for(eps in listOf(1e-4,3e-5)) {
            val original=x[index];x[index]=original+eps;val plus=plain(TrainModel(model.rules,values),e,c)
            x[index]=original-eps;val minus=plain(TrainModel(model.rules,values),e,c);x[index]=original
            val numeric=(plus-minus)/(2*eps)
            checkNear("joint.$n[$index] input=$original eps=$eps",full.gradient.getValue(n)[index],numeric,2e-10+2e-5*abs(numeric))
        }
    }
    val trainer=OfflineTrainer(model,c);trainer.accumulate(full)
    val other=JointGraph.evaluate(model,dataset,1,c);trainer.accumulate(other)
    val mean=full.gradient.mapValues {(n,x)->DoubleArray(x.size) {(x[it]+other.gradient.getValue(n)[it])/2}}
    val one=OfflineTrainer(model,c);one.accumulate(full.copy(gradient=mean));one.update();trainer.update()
    equalMaps("batch.meanUpdate",trainer.model.values(),one.model.values())
    equalMaps("batch.meanM",trainer.optimizer().m,one.optimizer().m)
    checkNear("batch.cursor",trainer.optimizer().cursor.toDouble(),2.0,0.0)
    rejected("stale joint gradient") {trainer.accumulate(full)}
    rejected("changed experiment gradient") {OfflineTrainer(model,c.copy(stateLoss=2.0)).accumulate(full)}
    val external=Synthetic.examples();val immutable=TrainingDataset(external)
    external[0].targetState[0]=999.0;external[0].events[0].features[0]=999.0
    immutable.example(0).targetState[0]=111.0
    checkNear("dataset.snapshot",JointGraph.evaluate(model,immutable,0,c).loss,full.loss,0.0)
    rejected("dataset manifest mismatch") {JointGraph.evaluate(model,immutable,0,c.copy(datasetHash="b".repeat(64)))}
    return full
}
private fun optimizerTests(c:Experiment) {
    val constant=c.copy(peakRate=.01,floorRate=.01,warmup=0,totalSteps=2,maxUpdates=2,clip=1.0)
    val t=OfflineTrainer(scalarModel(),constant)
    t.accumulate(eval(t,doubleArrayOf(.3,-.4)));val norm=t.update()
    checkNear("adam.norm",norm,.5)
    checkNear("adam.first.weight",t.model.values().getValue("x")[0],-.01*.3/(.3+1e-8))
    checkNear("adam.first.m",t.optimizer().m.getValue("x")[0],.03)
    checkNear("adam.first.v",t.optimizer().v.getValue("x")[0],.00009)
    t.accumulate(eval(t,doubleArrayOf(-.1,.2)));t.update()
    val m=.9*.03+.1*(-.1);val v=.999*.00009+.001*.01
    val expected=-.01*.3/(.3+1e-8)-.01*(m/(1-.9.pow(2)))/(sqrt(v/(1-.999.pow(2)))+1e-8)
    checkNear("adam.second.weight",t.model.values().getValue("x")[0],expected)
    checkNear("adam.second.m",t.optimizer().m.getValue("x")[0],m)
    checkNear("adam.second.v",t.optimizer().v.getValue("x")[0],v)
    rejected("budget") {t.accumulate(eval(t,doubleArrayOf(.1,.1)));t.update()}
    val clip=OfflineTrainer(scalarModel(),constant)
    clip.accumulate(eval(clip,doubleArrayOf(3.0,4.0)));checkNear("clip.rawNorm",clip.update(),5.0)
    checkNear("clip.m",clip.optimizer().m.getValue("x")[0],.06)
    val projected=projectRow(doubleArrayOf(2.0,1.0),1.0)
    checkNear("L1.euclidean.x",projected[0],1.0);checkNear("L1.euclidean.y",projected[1],0.0)
    checkNear("L1.largeMagnitude",projectRow(doubleArrayOf(1e15,0.0),1.0)[0],1.0,0.0)
    val huge=projectRow(doubleArrayOf(Double.MAX_VALUE,Double.MAX_VALUE),1.0)
    checkNear("L1.extreme.x",huge[0],.5,0.0);checkNear("L1.extreme.y",huge[1],.5,0.0)
    val bound=OfflineTrainer(scalarModel(.99),constant.copy(peakRate=.5,floorRate=.5))
    bound.accumulate(eval(bound,doubleArrayOf(-1.0,-1.0)));bound.update()
    checkNear("optimizer.projectedNorm",bound.model.values().getValue("x").sumOf {abs(it)},1.0)
    val frozen=OfflineTrainer(scalarModel(0.0,setOf(0)),constant)
    frozen.accumulate(eval(frozen,doubleArrayOf(1.0,1.0)));frozen.update()
    checkNear("frozen.weight",frozen.model.values().getValue("x")[0],0.0,0.0)
    checkNear("frozen.m",frozen.optimizer().m.getValue("x")[0],0.0,0.0);checkNear("frozen.v",frozen.optimizer().v.getValue("x")[0],0.0,0.0)
    val bad=OfflineTrainer(scalarModel(),constant)
    rejected("NaN gradient") {bad.accumulate(eval(bad,doubleArrayOf(Double.NaN,0.0)))}
    checkNear("NaN transaction.pending",bad.pending.toDouble(),0.0,0.0)
    bad.accumulate(eval(bad,doubleArrayOf(Double.MAX_VALUE,Double.MAX_VALUE)))
    rejected("accumulation overflow") {bad.accumulate(eval(bad,doubleArrayOf(Double.MAX_VALUE,Double.MAX_VALUE)))}
    checkNear("overflow.pending",bad.pending.toDouble(),1.0,0.0)
    val before=bad.model.fingerprint();rejected("nonfinite norm") {bad.update()}
    check(before==bad.model.fingerprint() && bad.optimizer().step==0L);tests++
    val callerRoute=mutableListOf(true,false)
    val callerFrozen=mutableSetOf(0)
    val callerRules=mutableListOf(TensorRule("x",1,2,1.0,false,callerFrozen))
    val owned=OfflineTrainer(TrainModel(callerRules,mapOf("x" to doubleArrayOf(0.0,0.0))),constant.copy(route=callerRoute))
    owned.accumulate(eval(owned,doubleArrayOf(1.0,1.0)))
    callerRoute[0]=false;callerRules[0]=callerRules[0].copy(cap=.01);callerFrozen.clear()
    checkNear("ownership.route",if(owned.config.route==listOf(true,false)) 1.0 else 0.0,1.0,0.0)
    checkNear("ownership.cap",owned.model.rules[0].cap,1.0,0.0)
    owned.update();checkNear("ownership.frozen",owned.model.values().getValue("x")[0],0.0,0.0)
    rejected("nonzero initial moments") {
        OfflineTrainer(scalarModel(),constant,OptimizerState(0,0,mapOf("x" to doubleArrayOf(.1,0.0)),mapOf("x" to doubleArrayOf(0.0,0.0))))
    }
    checkNear("rate.warmup",c.rate(1),c.peakRate/c.warmup)
    checkNear("rate.final",c.rate(c.totalSteps.toLong()),c.floorRate)
}
private fun checkpointTests(model:TrainModel,examples:List<TrainingExample>,c:Experiment,gradient:Evaluation) {
    val dataset=TrainingDataset(examples)
    val root=Files.createTempDirectory("uno-train-check-");val path=root.resolve("state.bin")
    try {
        val t=OfflineTrainer(model,c);t.accumulate(gradient)
        rejected("midaccumulation checkpoint") {TrainCheckpoint.save(path,t)}
        t.update()
        val after=JointGraph.evaluate(t.model,dataset,0,c).loss
        println("DIAGNOSTIC_LOSS before=${gradient.loss} after=$after expectedAfterLessThanBefore=true ONE_STEP_ONLY")
        check(after<gradient.loss);tests++
        TrainCheckpoint.save(path,t)
        println("CHECKPOINT bytes=${Files.size(path)} sha256=${sha256(Files.readAllBytes(path))}")
        val savedBytes=Files.readAllBytes(path)
        val loaded=TrainCheckpoint.load(path,model,c)
        checkNear("checkpoint.step",loaded.optimizer().step.toDouble(),1.0,0.0)
        checkNear("checkpoint.cursor",loaded.optimizer().cursor.toDouble(),1.0,0.0)
        equalMaps("checkpoint.weights",t.model.values(),loaded.model.values());equalMaps("checkpoint.m",t.optimizer().m,loaded.optimizer().m);equalMaps("checkpoint.v",t.optimizer().v,loaded.optimizer().v)
        val second=JointGraph.evaluate(t.model,dataset,1,c);val restored=JointGraph.evaluate(loaded.model,dataset,1,c)
        checkNear("resume.loss",restored.loss,second.loss,0.0)
        equalMaps("resume.gradient",second.gradient,restored.gradient)
        t.accumulate(second);loaded.accumulate(restored);t.update();loaded.update()
        equalMaps("resume.next.weights",t.model.values(),loaded.model.values());equalMaps("resume.next.m",t.optimizer().m,loaded.optimizer().m);equalMaps("resume.next.v",t.optimizer().v,loaded.optimizer().v)
        check(t.optimizer().step==loaded.optimizer().step && t.optimizer().cursor==loaded.optimizer().cursor);tests++
        val original=sha256(savedBytes)
        t.accumulate(JointGraph.evaluate(t.model,dataset,0,c))
        rejected("rejected save preserves checkpoint") {TrainCheckpoint.save(path,t)}
        checkNear("checkpoint.preserved",if(original==sha256(Files.readAllBytes(path))) 1.0 else 0.0,1.0,0.0)
        rejected("config drift") {TrainCheckpoint.load(path,model,c.copy(seed=73))}
        rejected("dataset drift") {TrainCheckpoint.load(path,model,c.copy(datasetHash="b".repeat(64)))}
        val changed=model.rules.mapIndexed {i,r->if(i==0) r.copy(cap=7.9) else r}
        rejected("schema drift") {TrainCheckpoint.load(path,TrainModel(changed,model.values()),c)}
        val corrupt=root.resolve("corrupt.bin");val bytes=savedBytes.copyOf();bytes[bytes.lastIndex]=(bytes.last().toInt() xor 1).toByte();Files.write(corrupt,bytes)
        rejected("bit corruption") {TrainCheckpoint.load(corrupt,model,c)}
        Files.write(corrupt,savedBytes.copyOf(savedBytes.size/2));rejected("truncated checkpoint") {TrainCheckpoint.load(corrupt,model,c)}
    } finally {Files.list(root).use {it.forEach(Files::delete)};Files.delete(root)}
}
fun main() {
    println("UNO-TRAIN-001 bounded synthetic diagnostics. No epochs or training loop. Full inputs Synthetic.kt; default seed11. All coordinates not listed are0.")
    lossTests()
    val model=Synthetic.model();val examples=Synthetic.examples();val hash=Synthetic.digest(examples);println("DATASET_SHA256=$hash")
    val c=Experiment(hash)
    val gradient=graphTests(model,examples,c)
    optimizerTests(c);checkpointTests(model,examples,c,gradient)
    println("TRAIN001_CHECKS_PASS=$tests DOUBLE_FIXED_ROUTE_SYNTHETIC_ONLY")
}
