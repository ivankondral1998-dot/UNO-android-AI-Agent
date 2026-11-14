package org.unovyra.uno.research

import org.unovyra.uno.core.*
import java.security.MessageDigest
import java.io.*
import kotlin.math.*

internal fun sha256(bytes:ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") {"%02x".format(it)}
internal fun encode(body:(DataOutputStream)->Unit):ByteArray {
    val b=ByteArrayOutputStream();DataOutputStream(b).use(body);return b.toByteArray()
}
data class TensorRule(val name:String,val rows:Int,val cols:Int,val cap:Double,val box:Boolean=false,val frozen:Set<Int> = emptySet()) {
    init {require(rows>0 && cols>0 && rows.toLong()*cols<=2_000_000 && cap.isFinite() && cap>0 && frozen.all {it in 0 until rows*cols})}
}
class TrainModel(rules:List<TensorRule>, values:Map<String,DoubleArray>) {
    val rules:List<TensorRule> = java.util.Collections.unmodifiableList(rules.map {
        it.copy(frozen=java.util.Collections.unmodifiableSet(it.frozen.toSet()))
    })
    private val data=values.mapValues {it.value.copyOf()}
    init {
        require(rules.size in 1..256 && rules.map {it.name}.distinct().size==rules.size)
        require(data.keys==rules.map {it.name}.toSet())
        for(r in rules) {
            val x=data.getValue(r.name);require(x.size==r.rows*r.cols && x.all(Double::isFinite))
            require(r.frozen.all {x[it]==0.0}) {"FROZEN_PARAMETER"}
            if(r.box) require(x.all {abs(it)<=r.cap}) else require((0 until r.rows).all {row ->
                (0 until r.cols).sumOf {abs(x[row*r.cols+it])}<=r.cap+1e-10 }) {"PARAMETER_NORM"}
        }
    }
    fun values()=data.mapValues {it.value.copyOf()}
    fun schemaHash()=sha256(encode {o -> for(r in rules) {
        o.writeUTF(r.name);o.writeInt(r.rows);o.writeInt(r.cols);o.writeDouble(r.cap);o.writeBoolean(r.box)
        o.writeInt(r.frozen.size);r.frozen.sorted().forEach(o::writeInt)
    }})
    fun fingerprint()=sha256(encode {o -> o.writeUTF(schemaHash());for(r in rules) data.getValue(r.name).forEach(o::writeDouble)})
    fun core():UnoRefWeights {
        val map=rules.associateBy {it.name};fun mat(n:String):UnoRefMatrix {
            val r=map.getValue(n);return UnoRefMatrix(r.rows,r.cols,data.getValue(n))
        }
        val d=map.getValue("projection").rows
        return UnoRefWeights("UNO_TRAIN_001_SYNTHETIC",mat("projection"),mat("us"),mat("ug"),mat("meta"),
            data.getValue("e"),data.getValue("bias"),mat("wq"),mat("wr"),
            (0..1).map {l -> (0 until d/64).map {j -> val n="branch.$l.$j"
                UnoRefBranch(mat("$n.a"),mat("$n.c"),mat("$n.b"),data.getValue("$n.ab"),data.getValue("$n.bb")) } })
    }
    fun memory(name:String):UnoRefMatrix {
        val r=rules.single {it.name==name};return UnoRefMatrix(r.rows,r.cols,data.getValue(name))
    }
    companion object {
        fun from(w:UnoRefWeights,wk:UnoRefMatrix,wv:UnoRefMatrix):TrainModel {
            val t=ReverseF();t.weights(w);LearnedMemory(t,wk,wv)
            val rules=mutableListOf<TensorRule>()
            fun m(n:String,x:UnoRefMatrix,cap:Double) {rules.add(TensorRule(n,x.rows,x.cols,cap))}
            fun b(n:String,numbers:Int,cap:Double) {rules.add(TensorRule(n,numbers,1,cap,true))}
            m("projection",w.projection,8.0);m("us",w.us,1.0);m("ug",w.ug,1.0);m("meta",w.meta,8.0)
            b("e",w.d,1.0);b("bias",w.d,1.0);m("wq",w.wq,2.0);m("wr",w.wr,2.0)
            for(l in 0..1) for(j in 0 until w.blocks) {val n="branch.$l.$j";val k=w.branches[l][j]
                m("$n.a",k.a,1.0);m("$n.c",k.c,2.0);m("$n.b",k.b,.9);b("$n.ab",256,8.0);b("$n.bb",64,8.0)
            }
            m("wk",wk,2.0);m("wv",wv,2.0)
            return TrainModel(rules,t.leaves.mapValues {it.value.x})
        }
    }
}

/** Euclidean L1-ball projection, not radial rescaling. */
internal fun projectRow(x:DoubleArray,cap:Double):DoubleArray {
    require(x.all(Double::isFinite) && cap.isFinite() && cap>0)
    if(x.sumOf {abs(it)}<=cap) return x.copyOf()
    val largest=x.maxOf {abs(it)}
    // Solve for delta=maxAbs-threshold using gaps, avoiding maxAbs-cap cancellation.
    val gaps=x.map {largest-abs(it)}.sorted()
    var delta=cap
    for(i in 1 until gaps.size) {
        if(gaps[i]>=delta) break
        delta+=(gaps[i]-delta)/(i+1)
    }
    val out=DoubleArray(x.size) {sign(x[it])*max(0.0,delta-(largest-abs(x[it])))}
    require(out.all(Double::isFinite) && out.sumOf {abs(it)}<=cap+1e-10) {"PROJECTION_NUMERIC"}
    return out
}
