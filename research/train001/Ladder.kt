package org.unovyra.uno.research

import org.unovyra.uno.core.*
import java.util.Random
import kotlin.math.*

/** 005B-compatible distribution, not torch-PRNG-identical. Every model receives the same raw x.
 * No external slot lookup/key bank, no gold at read time, no f_e answer bypass. */
object Ladder {
    val rungs=listOf("r1_single","r2_two","r3_three","r4_overwrite","r5_order")
    val lengths=listOf(12,24,48,96)
    fun example(rung:String,length:Int,seed:Long,id:String,erase:Boolean=false):TrainingExample {
        require(rung in rungs && length in 10..96)
        val rng=Random(seed)
        fun uniform()=rng.nextDouble()*2-1
        val x=MutableList(length) {doubleArrayOf(uniform(),uniform(),0.0)}
        val n=when(rung) {"r1_single"->1;"r2_two","r5_order"->2;else->3}
        val codes=when(n) {1->listOf(0.0);2->listOf(-1.0,1.0);else->listOf(-1.0,0.0,1.0)}
        val count=n+if(rung=="r4_overwrite") 1 else 0
        val window=min(length-2,max(5,(length+1)/2))
        val stamps=(0 until window).shuffled(rng).take(count).sorted()
        val slots=(0 until n).shuffled(rng).toMutableList()
        if(count>n) slots.add(rng.nextInt(n))
        val query=rng.nextInt(n)
        for(j in stamps.indices) x[stamps[j]]=doubleArrayOf(uniform(),codes[slots[j]],1.0)
        val selected=if(rung=="r5_order") stamps.last() else stamps[slots.indexOfLast {it==query}]
        val answer=if(rung=="r5_order") x[selected][1] else x[selected][0]
        // Erasure changes inputs only; labels/source target remain fixed. No target-sourced memory filter.
        if(erase) for(j in stamps.indices) {
            if(rung=="r5_order") x[stamps[j]][1]=0.0
            else if(slots[j]==query) x[stamps[j]][0]=0.0
        }
        x[length-1]=if(rung=="r5_order") doubleArrayOf(0.0,0.0,-2.0) else doubleArrayOf(0.0,codes[query],-1.0)
        val events=x.mapIndexed {i,f ->MemoryReplay.Event(i+1L,i.toLong(),f,DoubleArray(128),f[2]==1.0)}
        val state=DoubleArray(64).apply {this[0]=if(answer>0) .8 else -.8}
        val value=DoubleArray(128).apply {this[0]=answer}
        return TrainingExample(id,events,DoubleArray(64),state,BooleanArray(64) {it==0},selected+1L,value,BooleanArray(128) {it==0})
    }
    fun data(split:String,n:Int,seed:Long,erase:Boolean=false):TrainingDataset {
        require(split in listOf("train","validation","test") && n in 1..10000)
        val offset=when(split) {"train"->0L;"validation"->1_000_000L;else->2_000_000L}
        return TrainingDataset((0 until n).map {i ->
            val length=if(split=="train") listOf(12,24,32)[(i/5)%3] else lengths[(i/5)%4]
            example(rungs[i%5],length,seed+offset+i,"$split-$i",erase)
        })
    }
    fun testData(seed:Long,erase:Boolean=false)=TrainingDataset(rungs.flatMap {rung -> lengths.flatMap {length ->
        (0 until 16).map {i -> example(rung,length,seed+2_000_000+length*100+i,"test-$rung-$length-$i",erase)}
    }})
    /** Astra Xavier -> Euclidean row-L1 projection, d64 is a diagnostic geometry only. */
    fun model(seed:Long):TrainModel {
        val rng=Random(seed);val d=64
        fun mat(r:Int,c:Int,cap:Double):UnoRefMatrix {
            val scale=sqrt(6.0/(r+c))
            val values=DoubleArray(r*c) {(rng.nextDouble()*2-1)*scale}
            for(row in 0 until r) projectRow(values.copyOfRange(row*c,(row+1)*c),cap).copyInto(values,row*c)
            return UnoRefMatrix(r,c,values)
        }
        val w=UnoRefWeights("LADDER_DIAGNOSTIC_D64",mat(d,3,8.0),mat(d,d,1.0),mat(d,d,1.0),mat(d,32,8.0),
            DoubleArray(d) {(rng.nextDouble()*2-1)*.01},DoubleArray(d),mat(128,d,2.0),mat(d,128,2.0),
            (0..1).map { listOf(UnoRefBranch(mat(256,d,1.0),mat(256,d,2.0),mat(64,256,.9),DoubleArray(256),DoubleArray(64))) })
        return TrainModel.from(w,mat(128,d,2.0),mat(128,d,2.0))
    }
}

/** Plain Double inference uses the unchanged reference, independently of research VJP/loss code. */
object LadderEval {
    data class Prediction(val state:Double,val hit:Boolean,val key:Long?)
    fun predict(model:TrainModel,e:TrainingExample,ablation:String="full"):Prediction {
        require(ablation in listOf("full","memory_off","zero_values"))
        val w=model.core();val ref=UnoFReference(w)
        val bank=mutableListOf<Pair<LearnedMemory.Stamp,UnoRefMemoryVector>>()
        var state=e.initial.copyOf();var key:Long?=null;var hit=false
        val wk=model.memory("wk");val wv=model.memory("wv")
        for(v in e.events) {
            val eligible=bank.filter {(s,_) -> s.sequence<v.sequence && s.created<=v.time && v.time<s.expiry && s.scope==v.scope && s.version==v.version && s.sequence !in v.revoked}
            if(v===e.events.last()) {
                hit=eligible.any {it.first.sequence==e.targetRecord}
                if(eligible.isNotEmpty() && ablation!="memory_off") {
                    val input=w.projection.multiply(v.features);val prev=w.us.multiply(state);val emb=w.e;val bias=w.bias
                    val z0=DoubleArray(w.d) {i -> tanh(input[i]+prev[i]+emb[i]+bias[i])}
                    val q=w.wq.multiply(z0).map {tanh(it)}
                    key=eligible.maxBy {(_,entry)->q.indices.sumOf {q[it]*entry.key[it]}}.first.sequence
                }
            }
            val memory=if(ablation=="memory_off") emptyList() else eligible.map {(_,entry)->
                if(ablation=="zero_values") UnoRefMemoryVector(entry.key,DoubleArray(128)) else entry
            }
            state=ref.forward(UnoRefEvent(v.features,DoubleArray(32),state,DoubleArray(w.d),memory),booleanArrayOf(true),2).state
            if(v.write) bank.add(LearnedMemory.Stamp(v.sequence,v.time,v.expiry,v.scope,v.version) to
                UnoRefMemoryVector(wk.multiply(state).map {tanh(it)}.toDoubleArray(),
                    wv.multiply(state).mapIndexed {i,x->tanh(x+v.evidence[i])}.toDoubleArray()))
        }
        return Prediction(state[0],hit,key)
    }
    data class Metrics(val n:Int,val correct:Int,val misses:Int,val keyCorrect:Int,val mse:Double) {
        val accuracy get()=correct.toDouble()/n
    }
    fun score(model:TrainModel,data:TrainingDataset,ablation:String="full"):Metrics {
        var correct=0;var misses=0;var keys=0;var mse=0.0
        for(i in 0 until data.size) {
            val e=data.example(i);val p=predict(model,e,ablation)
            if(!p.hit) misses++
            if(p.hit && (p.state>=0)==(e.targetState[0]>0)) correct++
            if(p.key==e.targetRecord) keys++
            mse+=(p.state-e.targetState[0]).pow(2)
        }
        return Metrics(data.size,correct,misses,keys,mse/data.size)
    }
}
