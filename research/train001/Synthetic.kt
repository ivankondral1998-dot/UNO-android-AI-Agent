package org.unovyra.uno.research

import org.unovyra.uno.core.*

/** Small deterministic test data, NOT a language/intelligence or quality benchmark. */
object Synthetic {
    private fun mat(r:Int,c:Int,vararg values:Triple<Int,Int,Double>):UnoRefMatrix {
        val x=DoubleArray(r*c);for((i,j,v) in values) x[i*c+j]=v;return UnoRefMatrix(r,c,x)
    }
    fun model():TrainModel {
        val d=128
        val w=UnoRefWeights("SYNTHETIC_TRAIN_DIAGNOSTIC",
            mat(d,2,Triple(0,0,.7),Triple(0,1,-.2),Triple(1,0,.1),Triple(1,1,.6)),
            mat(d,d,Triple(0,0,.3),Triple(1,1,.2)),mat(d,d),mat(d,32),DoubleArray(d),DoubleArray(d),
            mat(128,d,Triple(0,0,.8),Triple(1,1,.7)),mat(d,128,Triple(0,0,.8),Triple(1,1,.6),Triple(0,2,.25)),
            (0..1).map { (0..1).map {UnoRefBranch(
                mat(256,d,Triple(0,0,.4),Triple(1,1,.3)),mat(256,d,Triple(0,0,.6),Triple(1,1,.5)),
                mat(64,256,Triple(0,0,.5),Triple(1,1,.4)),DoubleArray(256),DoubleArray(64))} })
        return TrainModel.from(w,
            mat(128,d,Triple(0,0,.6),Triple(0,1,-.2),Triple(1,0,.1),Triple(1,1,.5),Triple(2,0,-.3),Triple(2,1,.4)),
            mat(128,d,Triple(0,0,-.4),Triple(0,1,.2),Triple(1,0,.3),Triple(1,1,.6),Triple(2,0,.3),Triple(2,1,-.2)))
    }
    fun examples(seed:Long=11):List<TrainingExample> = (0..1).map { task ->
        val shift=(seed%17)*.001
        val f=listOf(doubleArrayOf(.7+shift,-.5),doubleArrayOf(-.4,.8-shift),doubleArrayOf(.6,.3),doubleArrayOf(-.2,.5))
            .map {x -> DoubleArray(2) {if(task==0) x[it] else -x[it]}}
        val events=f.mapIndexed {i,x ->
            val fe=DoubleArray(128).apply {this[2]=1.0;this[6]=1.0;this[40]=1.0;this[8]=(i-1)*.1;this[24]=1.0}
            MemoryReplay.Event(i+1L,10L+i,x,fe,i<3,revoked=if(i==3) setOf(2L) else emptySet())
        }
        val selected=if(task==0) 0 else 2
        val value=DoubleArray(128).apply {this[0]=f[selected][0];this[1]=f[selected][1]}
        val state=DoubleArray(128).apply {this[0]=f[selected][0];this[1]=(f[0][1]+f[2][1])*.5}
        val mask=BooleanArray(128) {it<2}
        TrainingExample("delayed-state-memory-$task-seed$seed",events,DoubleArray(128),state,mask,
            selected+1L,value,mask.copyOf())
    }
    fun digest(examples:List<TrainingExample>)=TrainingDataset.digest(examples)
}
