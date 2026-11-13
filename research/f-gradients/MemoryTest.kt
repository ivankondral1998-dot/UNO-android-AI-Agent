package org.unovyra.uno.research

import org.unovyra.uno.core.*
import kotlin.math.*

private fun matrix(r:Int,c:Int,vararg x:Triple<Int,Int,Double>):UnoRefMatrix {
    val a=DoubleArray(r*c); for((i,j,v) in x) a[i*c+j]=v
    return UnoRefMatrix(r,c,a)
}
private fun core(p:Map<String,DoubleArray>):UnoRefWeights {
    fun zero(r:Int,c:Int)=matrix(r,c)
    val proj=UnoRefMatrix(128,2,p.getValue("projection"))
    return UnoRefWeights("SYNTHETIC_MEMORY",proj,
        matrix(128,128,Triple(0,0,.3),Triple(1,1,.2)),zero(128,128),zero(128,32),
        DoubleArray(128),DoubleArray(128),
        matrix(128,128,Triple(0,0,.8),Triple(1,1,.7)),
        matrix(128,128,Triple(0,0,.8),Triple(1,1,.6),Triple(0,2,.25)),
        (0..1).map { l -> (0..1).map { j -> UnoRefBranch(
            matrix(256,128,Triple(0,0,.4),Triple(1,1,.3)),
            matrix(256,128,Triple(0,0,.6),Triple(1,1,.5)),
            matrix(64,256,Triple(0,0,.5),Triple(1,1,.4)),DoubleArray(256),DoubleArray(64)) } })
}
private fun inputs():LinkedHashMap<String,DoubleArray> {
    val p=linkedMapOf<String,DoubleArray>()
    p["projection"]=DoubleArray(256).apply { this[0]=.7;this[1]=-.2;this[2]=.1;this[3]=.6 }
    p["wk"]=DoubleArray(128*128).apply {this[0]=.6;this[1]=-.2;this[128]=.1;this[129]=.5;this[256]=-.3;this[257]=.4}
    p["wv"]=DoubleArray(128*128).apply {this[0]=-.4;this[1]=.2;this[128]=.3;this[129]=.6;this[256]=.3;this[257]=-.2}
    p["initial"]=DoubleArray(128).apply {this[0]=.2;this[1]=-.3}
    listOf(doubleArrayOf(.7,-.5),doubleArrayOf(-.4,.8),doubleArrayOf(.6,.3),doubleArrayOf(-.2,.5)).forEachIndexed { i,x -> p["event.$i"]=x }
    return p
}
private fun events(p:Map<String,DoubleArray>)=(0..3).map { i ->
    val fe=DoubleArray(128).apply {this[2]=1.0;this[6]=1.0;this[40]=1.0;this[8]=.1*(i-1);this[24]=1.0}
    MemoryReplay.Event(i.toLong()+1,10L+i,p.getValue("event.$i"),fe,i<3,revoked=if(i==3) setOf(2L) else emptySet())
}
private val mask=booleanArrayOf(true,false)
private fun replay(p:Map<String,DoubleArray>,count:Int=4):MemoryReplay.Result =
    MemoryReplay(core(p),UnoRefMatrix(128,128,p.getValue("wk")),UnoRefMatrix(128,128,p.getValue("wv")))
        .prefix(events(p),count,p.getValue("initial"),mask,3)

/** Independent plain Double projections plus the unchanged forward oracle, no tape primitives. */
private fun oracle(p:Map<String,DoubleArray>,count:Int=4):List<DoubleArray> {
    val w=core(p); val model=UnoFReference(w)
    var state=p.getValue("initial");val states=mutableListOf<DoubleArray>()
    val records=mutableListOf<Pair<MemoryReplay.Event,UnoRefMemoryVector>>()
    for(e in events(p).take(count)) {
        state=model.forward(UnoRefEvent(e.features,DoubleArray(32),state,DoubleArray(128),
            records.filter { it.first.sequence<e.sequence && it.first.time<=e.time && e.time<it.first.expiry && it.first.scope==e.scope && it.first.version==e.version && it.first.sequence !in e.revoked }.map { it.second }),mask,3).state
        states.add(state)
        if(e.write) {
            fun project(name:String,bias:DoubleArray)=DoubleArray(128) { r ->
                var dot=0.0
                for(c in 0 until 128) dot+=p.getValue(name)[r*128+c]*state[c]
                tanh(dot+bias[r])
            }
            records.add(e to UnoRefMemoryVector(project("wk",DoubleArray(128)),project("wv",e.evidence)))
        }
    }
    return states
}
private var checks=0
private fun near(name:String,a:Double,b:Double,tol:Double=2e-10) {
    println("CHECK $name expected=$b actual=$a tolerance=$tol error=${abs(a-b)}")
    check(a.isFinite() && b.isFinite() && abs(a-b)<=tol) { name };checks++
}
private fun reject(name:String,body:()->Unit) {
    var caught=false
    try {body()} catch(e:IllegalArgumentException) {caught=true;println("REJECT $name ${e.message}")}
    check(caught) {name};checks++
}
fun memoryMain() {
    println("WkWv smooth Double; no training. All inputs: sparse inputs()/core()/events() in MemoryTest.kt; seed[0]=.7 seed[1]=-.4 others0; K3 mask[true,false]")
    val p=inputs(); val seed=DoubleArray(128).apply { this[0]=.7;this[1]=-.4 }
    fun objective(q:Map<String,DoubleArray>,n:Int=4):Double {
        val h=oracle(q,n).last();return h.indices.sumOf {h[it]*seed[it]}
    }
    for(n in listOf(1,2,4)) {
        val result=replay(p,n); val expected=oracle(p,n)
        for(i in 0 until n) near("prefix$n.state$i",result.states[i].x.indices.maxOf { abs(result.states[i].x[it]-expected[i][it]) },0.0,2e-14)
        result.tape.backward(result.states.last(),seed)
        for(name in listOf("wk","wv")+p.keys.filter {it!="wk" && it!="wv"}) {
            val x=p.getValue(name)
            val g=result.tape.leaves[name]?.g ?: DoubleArray(x.size)
            val ids=if(name in listOf("wk","wv")) listOf(0,1,128,129,256,257,16383) else if(name=="projection") listOf(0,1,2,3,255) else listOf(0,1,x.lastIndex).distinct()
            for(index in ids) for(eps in listOf(1e-4,3e-5)) {
                val original=x[index];x[index]=original+eps;val plus=objective(p,n)
                x[index]=original-eps;val minus=objective(p,n);x[index]=original
                val numeric=(plus-minus)/(2*eps)
                near("prefix$n.$name[$index] input=$original eps=$eps",g[index],numeric,2e-10+2e-5*abs(numeric))
            }
            if(n==4 && name in listOf("wk","wv")) {
                val maxSignal=g.maxOf {abs(it)}
                println("SIGNAL $name max=$maxSignal required>1e-7")
                check(maxSignal>1e-7);checks++
            }
        }
        // Each matrix receives its own dense direction; not a common key shift.
        for(name in listOf("wk","wv","projection")) {
            val x=p.getValue(name);val g=result.tape.leaves.getValue(name).g
            val dir=DoubleArray(x.size) {sin((it+1)*.37+name.sumOf {it.code})/sqrt(x.size.toDouble())}
            val exact=x.indices.sumOf {g[it]*dir[it]};val eps=1e-4
            val plus=p+(name to DoubleArray(x.size){x[it]+eps*dir[it]})
            val minus=p+(name to DoubleArray(x.size){x[it]-eps*dir[it]})
            near("prefix$n.$name.direction",exact,(objective(plus,n)-objective(minus,n))/(2*eps))
        }
        // Reconstruct the entire prefix with the SAME weights and inputs on a fresh tape.
        val again=replay(p,4);again.tape.backward(again.states[n-1],seed)
        for(name in result.tape.leaves.keys) near("replay.prefix$n.$name.gradient",result.tape.leaves.getValue(name).g.indices.maxOf {abs(result.tape.leaves.getValue(name).g[it]-again.tape.leaves.getValue(name).g[it])},0.0,0.0)
        if(n==2) near("singleton.Wk.gradient",result.tape.leaves.getValue("wk").g.maxOf {abs(it)},0.0,0.0)
    }
    // Alter a future event: earlier outputs and derivatives must be invariant.
    val future=inputs();future.getValue("event.3")[0]=999.0
    val a=replay(p,3);val b=replay(future,3)
    a.tape.backward(a.states.last(),seed);b.tape.backward(b.states.last(),seed)
    near("future.output",a.states.last().x.indices.maxOf {abs(a.states.last().x[it]-b.states.last().x[it])},0.0,0.0)
    for(name in a.tape.leaves.keys) near("future.gradient.$name",a.tape.leaves.getValue(name).g.indices.maxOf {abs(a.tape.leaves.getValue(name).g[it]-b.tape.leaves.getValue(name).g[it])},0.0,0.0)
    check("event.3" !in a.tape.leaves);checks++
    val t=ReverseF();val m=LearnedMemory(t,UnoRefMatrix(128,128,p.getValue("wk")),UnoRefMatrix(128,128,p.getValue("wv")))
    val h=t.leaf("h",p.getValue("initial"))
    val stamp=LearnedMemory.Stamp(3,30,50,"s","v")
    m.commit(stamp,h,DoubleArray(128))
    for((label,read) in listOf("futureSequence" to m.read(3,30,"s","v"),"futureTime" to m.read(4,29,"s","v"),
        "expired" to m.read(4,50,"s","v"),"scope" to m.read(4,35,"other","v"),"version" to m.read(4,35,"s","v2"),
        "revoked" to m.read(4,35,"s","v",setOf(3)))) near("eligible.$label",read.size.toDouble(),0.0,0.0)
    near("eligible.live",m.read(4,30,"s","v").size.toDouble(),1.0,0.0)
    reject("duplicateWrite") {m.commit(stamp,h,DoubleArray(128))}
    reject("badState") {m.commit(stamp.copy(sequence=4),ReverseF.V(DoubleArray(127)),DoubleArray(128))}
    reject("NaNState") {m.commit(stamp.copy(sequence=4),ReverseF.V(DoubleArray(128){Double.NaN}),DoubleArray(128))}
    reject("evidenceShape") {m.commit(stamp.copy(sequence=4),h,DoubleArray(127))}
    reject("evidenceBound") {m.commit(stamp.copy(sequence=4),h,DoubleArray(128){2.0})}
    reject("evidenceNaN") {m.commit(stamp.copy(sequence=4),h,DoubleArray(128){Double.NaN})}
    reject("expiry") {LearnedMemory.Stamp(5,30,30,"s","v")}
    reject("backdatedWrite") {m.commit(stamp.copy(sequence=4,created=29),h,DoubleArray(128))}
    reject("badWkShape") {LearnedMemory(ReverseF(),matrix(127,128),matrix(128,128))}
    reject("WvNorm") {LearnedMemory(ReverseF(),matrix(128,128),matrix(128,128,Triple(0,0,2.1)))}
    reject("nonfiniteWeight") {UnoRefMatrix(128,128,DoubleArray(128*128){Double.NaN})}
    reject("badPrefix") {replay(p,0)}
    reject("eventOrder") {
        MemoryReplay(core(p),UnoRefMatrix(128,128,p.getValue("wk")),UnoRefMatrix(128,128,p.getValue("wv")))
            .prefix(events(p).reversed(),4,p.getValue("initial"),mask,3)
    }
    // FP16 quantization counterexample: both perturbed values round to 1 (binary16).
    // For values adjacent to 1, binary16 lower spacing=2^-11 and upper spacing=2^-10.
    val eps=1e-5
    fun roundHalfNearOne(x:Double):Double {
        require(x in .75..1.25)
        val spacing=if(x<1) 2.0.pow(-11) else 2.0.pow(-10)
        return floor(x/spacing+.5)*spacing
    }
    val derivative=(roundHalfNearOne(1+eps)-roundHalfNearOne(1-eps))/(2*eps)
    near("FP16.roundedDerivative",derivative,0.0,0.0)
    check(abs(derivative-1.0)==1.0);checks++
    println("COUNTEREXAMPLE FP16: 1±1e-5 both round to1; centralDerivative=0 smoothDerivative=1; exact smooth/storage parity NOT_CLAIMED")
    println("MEMORY_CHECKS_PASS=$checks FIXED_ROUTE_DOUBLE_NO_TRAINING")
}

fun main() { memoryMain() }
