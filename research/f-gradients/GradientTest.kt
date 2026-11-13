package org.unovyra.uno.research

import org.unovyra.uno.core.*
import kotlin.math.*

private const val D=128
private fun numbers(n: Int, salt: Int, scale: Double) = DoubleArray(n) { scale*sin((it+1.0)*(salt+1.0)*.37) }
private fun fixture(): LinkedHashMap<String,DoubleArray> {
    val p=linkedMapOf<String,DoubleArray>()
    fun a(n:String,r:Int,c:Int,s:Int,scale:Double=.12/c) { p[n]=numbers(r*c,s,scale) }
    a("projection",D,2,1,.14); a("us",D,D,2); a("ug",D,D,3); a("meta",D,32,4)
    p["e"]=numbers(D,5,.08); p["bias"]=numbers(D,6,.04)
    a("wq",128,D,7, .7/D); a("wr",D,128,8,.5/128)
    for(l in 0..1) for(j in 0..1) {
        val prefix="branch.$l.$j"
        a("$prefix.a",256,D,10+l*4+j,.5/D)
        a("$prefix.c",256,D,20+l*4+j,.6/D)
        a("$prefix.b",64,256,30+l*4+j,.4/256)
        p["$prefix.ab"]=numbers(256,40+l*4+j,.04)
        p["$prefix.bb"]=numbers(64,50+l*4+j,.03)
    }
    p["features"]=doubleArrayOf(.23,-.31); p["metadata"]=numbers(32,61,.2)
    p["state"]=numbers(D,62,.25); p["goal"]=numbers(D,63,.3)
    for(i in 0..2) { p["key.$i"]=numbers(128,70+i,.7); p["value.$i"]=numbers(128,80+i,.6) }
    p["writeFeatures"]=doubleArrayOf(-.19,.27)
    return p
}
private fun weights(p: Map<String,DoubleArray>): UnoRefWeights {
    fun mat(n:String,r:Int,c:Int)=UnoRefMatrix(r,c,p.getValue(n))
    return UnoRefWeights("SYNTHETIC_GRADIENT_ONLY",mat("projection",D,2),mat("us",D,D),mat("ug",D,D),
        mat("meta",D,32),p.getValue("e"),p.getValue("bias"),mat("wq",128,D),mat("wr",D,128),
        (0..1).map { l -> (0..1).map { j -> val n="branch.$l.$j"
            UnoRefBranch(mat("$n.a",256,D),mat("$n.c",256,D),mat("$n.b",64,256),p.getValue("$n.ab"),p.getValue("$n.bb")) } })
}
private data class Case(val name:String,val k:Int,val mask:BooleanArray,val memory:Int,val write:Boolean=false,
                        val alpha:Double=.43,val rho:Double=.37,val temperature:Double=.8)
private fun oracle(p:Map<String,DoubleArray>,c:Case):DoubleArray {
    val w=weights(p); val f=UnoFReference(w)
    var s=p.getValue("state")
    var mem=(0 until c.memory).map { UnoRefMemoryVector(p.getValue("key.$it"),p.getValue("value.$it")) }
    if(c.write) {
        val written=f.forward(UnoRefEvent(p.getValue("writeFeatures"),p.getValue("metadata"),s,p.getValue("goal")),
            c.mask,c.k,c.alpha,c.rho,c.temperature).state
        // Explicit test boundary: identity key/value write, no invented Wk/Wv.
        mem=listOf(UnoRefMemoryVector(written,written))+mem
        s=written
    }
    return f.forward(UnoRefEvent(p.getValue("features"),p.getValue("metadata"),s,p.getValue("goal"),mem),
        c.mask,c.k,c.alpha,c.rho,c.temperature).state
}
private fun analytic(p:Map<String,DoubleArray>,c:Case, detachWrite:Boolean=false):Pair<ReverseF,ReverseF.V> {
    val t=ReverseF(); val w=weights(p); t.weights(w)
    for((n,x) in p) if(n !in t.leaves) t.leaf(n,x)
    fun v(n:String)=t.leaves.getValue(n)
    var state=v("state")
    var keys=(0 until c.memory).map { v("key.$it") }; var vals=(0 until c.memory).map { v("value.$it") }
    if(c.write) {
        state=t.forward(w,v("writeFeatures"),v("metadata"),state,v("goal"),emptyList(),emptyList(),c.mask,c.k,c.alpha,c.rho,c.temperature)
        val stored=if(detachWrite) ReverseF.V(state.x.copyOf()) else state
        keys=listOf(stored)+keys; vals=listOf(stored)+vals
    }
    return t to t.forward(w,v("features"),v("metadata"),state,v("goal"),keys,vals,c.mask,c.k,c.alpha,c.rho,c.temperature)
}
private var count=0
private fun near(name:String,actual:Double,expected:Double,tol:Double) {
    println("CHECK $name expected=$expected actual=$actual absError=${abs(actual-expected)} tolerance=$tol")
    check(actual.isFinite() && expected.isFinite() && abs(actual-expected)<=tol) { name }; count++
}
private fun reject(name:String, body:()->Unit) {
    var rejected=false
    try {body()} catch(e:IllegalArgumentException) {rejected=true; println("REJECT $name ${e.message}")}
    check(rejected); count++
}
fun main() {
    val cases=listOf(Case("emptyK1",1,booleanArrayOf(true,false),0),
        Case("singletonK3",3,booleanArrayOf(false,true),1),
        Case("multipleK3",3,booleanArrayOf(true,false),3),
        Case("fullK8",8,booleanArrayOf(true,true),3),
        Case("writeReadK3",3,booleanArrayOf(true,false),2,true),
        Case("alpha0rho1",3,booleanArrayOf(true,false),3,alpha=0.0,rho=1.0))
    val seed=numbers(D,99,.2)
    println("INPUT generator=scale*sin((i+1)*(salt+1)*0.37); full salts/scales in fixture(); outputSeed salt99 scale0.2; epsilon=1e-5,3e-6")
    for(c in cases) {
        val p=fixture(); val expected=oracle(p,c); val(t,out)=analytic(p,c)
        println("CASE ${c.name} K=${c.k} mask=${c.mask.toList()} memories=${c.memory} write=${c.write} alpha=${c.alpha} rho=${c.rho} T=${c.temperature} features=${p.getValue("features").toList()}")
        near("${c.name}.forwardMax",out.x.indices.maxOf { abs(out.x[it]-expected[it]) },0.0,2e-14)
        t.backward(out,seed)
        for((n,x) in p) {
            val g=t.leaves.getValue(n).g
            for(idx in listOf(g.indices.maxBy { abs(g[it]) },0,x.lastIndex,minOf(119,x.lastIndex)).distinct()) {
            val original=x[idx]
            for(eps in listOf(1e-5,3e-6)) {
                x[idx]=original+eps; val plus=oracle(p,c).zip(seed).sumOf { it.first*it.second }
                x[idx]=original-eps; val minus=oracle(p,c).zip(seed).sumOf { it.first*it.second }
                x[idx]=original
                val numeric=(plus-minus)/(2*eps)
                near("${c.name}.$n[$idx] input=$original eps=$eps",g[idx],numeric,2e-11+2e-5*abs(numeric))
            }
            }
            if(n.startsWith("branch.")) {
                val block=n.split('.')[2].toInt()
                if(!c.mask[block]) near("${c.name}.$n maskedGradientMax",g.maxOf { abs(it) },0.0,0.0)
            }
        }
        // Whole-tensor directional derivative, including every coordinate rather than just maxima.
        for(salt in 1..2) {
            val directions=p.mapValues { (n,x) -> numbers(x.size,salt+n.fold(0) { h,ch -> (h*31+ch.code)%10007 },.1/sqrt(x.size.toDouble())) }
            val exact=p.keys.sumOf { n -> t.leaves.getValue(n).g.indices.sumOf { i -> t.leaves.getValue(n).g[i]*directions.getValue(n)[i] } }
            val eps=1e-5
            val plus=p.mapValues { (n,x) -> DoubleArray(x.size) { x[it]+eps*directions.getValue(n)[it] } }
            val minus=p.mapValues { (n,x) -> DoubleArray(x.size) { x[it]-eps*directions.getValue(n)[it] } }
            val numeric=(oracle(plus,c).zip(seed).sumOf {it.first*it.second}-oracle(minus,c).zip(seed).sumOf {it.first*it.second})/(2*eps)
            near("${c.name}.allCoordinatesDirection$salt",exact,numeric,2e-11+2e-5*abs(numeric))
        }
        if(c.write) {
            val (detached,detachedOut)=analytic(p,c,true)
            near("detach.forwardParity",detachedOut.x.indices.maxOf { abs(detachedOut.x[it]-out.x[it]) },0.0,0.0)
            detached.backward(detachedOut,seed)
            val full=t.leaves.getValue("writeFeatures").g
            val wrong=detached.leaves.getValue("writeFeatures").g
            val gap=full.indices.maxOf { abs(full[it]-wrong[it]) }
            println("COUNTEREXAMPLE detachWrite full=${full.toList()} detached=${wrong.toList()} gap=$gap requiredGap>1e-9")
            check(gap>1e-9); count++
        }
        if(c.memory==1) near("singleton.queryGradient",t.leaves.getValue("wq").g.maxOf { abs(it) },0.0,0.0)
    }
    // Prior Terra counterexample, retained as a regression for shared-use accumulation.
    val w=.4; val h=.7; val x=.2; val eps=1e-6
    fun recurrent(a:Double)=a*(a*h+x)+x
    val numeric=(recurrent(w+eps)-recurrent(w-eps))/(2*eps)
    near("sharedUse.correct",2*w*h+x,numeric,1e-9)
    check(abs((w*h+x)-numeric)>.2)
    println("COUNTEREXAMPLE sharedUse lastOnly=${w*h+x} full=${2*w*h+x} numeric=$numeric")
    val p=fixture(); val c=cases[2]
    reject("NaN feature") { val q=fixture();q.getValue("features")[0]=Double.NaN;oracle(q,c) }
    reject("invalid shape") { oracle(p+ ("state" to DoubleArray(127)),c) }
    reject("empty route") { oracle(p,c.copy(mask=booleanArrayOf(false,false))) }
    reject("K9") { oracle(p,c.copy(k=9)) }
    reject("temperature0") { oracle(p,c.copy(temperature=0.0)) }
    reject("row norm") { oracle(p+("us" to DoubleArray(D*D){2.0}),c) }
    reject("infinite memory") { val q=fixture();q.getValue("key.0")[0]=Double.POSITIVE_INFINITY;oracle(q,c) }
    reject("finite dot overflow") { val q=fixture();q["key.0"]=DoubleArray(128){Double.MAX_VALUE};oracle(q,c.copy(temperature=Double.MIN_VALUE)) }
    println("GRADIENT_CHECKS_PASS=$count NO_TRAINING FIXED_ROUTE_ONLY")
}
