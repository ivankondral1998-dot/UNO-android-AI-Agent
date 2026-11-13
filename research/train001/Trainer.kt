package org.unovyra.uno.research

import kotlin.math.*

data class Experiment(
    val datasetHash:String, val seed:Long=11, val peakRate:Double=2e-4, val floorRate:Double=2e-5,
    val warmup:Int=1000, val totalSteps:Int=2000, val maxUpdates:Int=2,
    val beta1:Double=.9, val beta2:Double=.999, val epsilon:Double=1e-8, val clip:Double=1.0,
    val stateLoss:Double=1.0, val retrieveLoss:Double=.3, val valueLoss:Double=.2,
    val innerSteps:Int=3, val route:List<Boolean> = listOf(true,false)
) {
    init {
        require(datasetHash.matches(Regex("[0-9a-f]{64}")))
        require(peakRate.isFinite() && peakRate in 0.0..1.0 && peakRate>0 && floorRate.isFinite() && floorRate in 0.0..peakRate)
        require(warmup>=0 && totalSteps>0 && warmup<=totalSteps && maxUpdates in 1..totalSteps)
        require(beta1 in 0.0..<1.0 && beta2 in 0.0..<1.0 && epsilon.isFinite() && epsilon>0 && clip.isFinite() && clip>0)
        require(listOf(stateLoss,retrieveLoss,valueLoss).all {it.isFinite() && it>=0} && stateLoss+retrieveLoss+valueLoss>0)
        require(innerSteps in 1..8 && route.isNotEmpty() && route.any {it})
    }
    fun rate(step:Long):Double {
        require(step in 1..totalSteps.toLong())
        if(warmup>0 && step<=warmup) return peakRate*step/warmup
        val f=if(totalSteps==warmup) 1.0 else (step-warmup).toDouble()/(totalSteps-warmup)
        return floorRate+(peakRate-floorRate)*.5*(1+cos(Math.PI*f))
    }
}
class TrainingExample(val id:String, val events:List<MemoryReplay.Event>, val initial:DoubleArray,
                      val targetState:DoubleArray, val stateValid:BooleanArray,
                      val targetRecord:Long, val targetValue:DoubleArray, val valueValid:BooleanArray)

/** One immutable data snapshot bound to its manifest. No caller array becomes the training source. */
class TrainingDataset(examples:List<TrainingExample>) {
    private fun copy(e:TrainingExample)=TrainingExample(e.id,e.events.map {v ->
        MemoryReplay.Event(v.sequence,v.time,v.features,v.evidence,v.write,v.expiry,v.scope,v.version,v.revoked)
    },e.initial.copyOf(),e.targetState.copyOf(),e.stateValid.copyOf(),e.targetRecord,e.targetValue.copyOf(),e.valueValid.copyOf())
    private val data=examples.map(::copy)
    val hash=digest(data)
    val size get()=data.size
    init {require(data.isNotEmpty() && data.map {it.id}.distinct().size==data.size)}
    fun example(index:Int)=copy(data[index])
    companion object {
    /** Includes inputs, labels and all eligibility fields; changing any of them changes the manifest. */
    fun digest(examples:List<TrainingExample>):String=sha256(encode {o ->
        o.writeUTF("UNO-TRAIN-001/SYNTHETIC/V1");o.writeInt(examples.size)
        fun doubles(x:DoubleArray) {o.writeInt(x.size);x.forEach(o::writeDouble)}
        for(e in examples) {
            o.writeUTF(e.id);doubles(e.initial);o.writeInt(e.events.size)
            for(v in e.events) {
                o.writeLong(v.sequence);o.writeLong(v.time);doubles(v.features);doubles(v.evidence)
                o.writeBoolean(v.write);o.writeLong(v.expiry);o.writeUTF(v.scope);o.writeUTF(v.version)
                o.writeInt(v.revoked.size);v.revoked.sorted().forEach(o::writeLong)
            }
            doubles(e.targetState);o.writeInt(e.stateValid.size);e.stateValid.forEach(o::writeBoolean);o.writeLong(e.targetRecord)
            doubles(e.targetValue);o.writeInt(e.valueValid.size);e.valueValid.forEach(o::writeBoolean)
        }
    })
    }
}

data class Evaluation(val modelHash:String,val experimentHash:String,val loss:Double,val parts:List<Double>,val gradient:Map<String,DoubleArray>)
object JointGraph {
    fun evaluate(model:TrainModel,dataset:TrainingDataset,index:Int,c:Experiment):Evaluation {
        require(dataset.hash==c.datasetHash) {"DATASET_MANIFEST_MISMATCH"}
        val e=dataset.example(index)
        val graph=MemoryReplay(model.core(),model.memory("wk"),model.memory("wv"))
            .prefix(e.events,e.events.size,e.initial,c.route.toBooleanArray(),c.innerSteps)
        val read=graph.reads.last();val target=read.entries.indexOfFirst {it.stamp.sequence==e.targetRecord}
        require(target>=0) {"RETRIEVAL_MISS"}
        val t=graph.tape
        val losses=listOf(
            TrainLoss.mse(t,graph.states.last(),e.targetState,e.stateValid),
            TrainLoss.retrieval(t,read.query,read.entries.map {it.key},target),
            TrainLoss.mse(t,read.entries[target].value,e.targetValue,e.valueValid))
        val total=TrainLoss.joint(t,losses,listOf(c.stateLoss,c.retrieveLoss,c.valueLoss))
        t.backward(total,doubleArrayOf(1.0))
        return Evaluation(model.fingerprint(),sha256(configBytes(c)),total.x[0],losses.map {it.x[0]},
            model.rules.associate {it.name to t.leaves.getValue(it.name).g.copyOf()})
    }
}

data class OptimizerState(val step:Long,val cursor:Long,val m:Map<String,DoubleArray>,val v:Map<String,DoubleArray>)
class OfflineTrainer(model:TrainModel, config:Experiment, state:OptimizerState?=null) {
    val config:Experiment=config.copy(route=java.util.Collections.unmodifiableList(config.route.toList()))
    var model:TrainModel=model
        private set
    private var saved=state?.let {copyState(it)} ?: OptimizerState(0,0,zeros(model),zeros(model))
    private var sums=zeros(model).toMutableMap()
    var pending:Int=0
        private set
    init { validateState(model,saved,config) }
    fun optimizer()=copyState(saved)
    fun accumulate(e:Evaluation) {
        require(e.modelHash==model.fingerprint() && e.experimentHash==sha256(configBytes(config))) {"STALE_GRADIENT"}
        require(e.loss.isFinite() && e.gradient.keys==sums.keys && pending<Int.MAX_VALUE)
        val next=sums.mapValues { (n,x) -> val g=e.gradient.getValue(n)
            require(g.size==x.size && g.all(Double::isFinite)) {"INVALID_GRADIENT"}
            DoubleArray(x.size) { x[it]+g[it] }.also {require(it.all(Double::isFinite)) {"ACCUMULATION_OVERFLOW"}}
        }
        sums=next.toMutableMap();pending++
    }
    /** A transaction: all candidate parameters/moments validated before committing anything. */
    fun update():Double {
        require(pending>0 && saved.step<config.maxUpdates) {"UPDATE_BOUNDARY_OR_BUDGET"}
        val nextStep=saved.step+1
        val g=sums.mapValues {(_,x)->DoubleArray(x.size) {x[it]/pending}}
        for(r in model.rules) r.frozen.forEach {g.getValue(r.name)[it]=0.0}
        var norm=0.0
        for(x in g.values) for(v in x) norm=hypot(norm,v)
        require(norm.isFinite()) {"NONFINITE_NORM"}
        val factor=if(norm>config.clip) config.clip/norm else 1.0
        val weights=model.values();val ms=zeros(model);val vs=zeros(model);val lr=config.rate(nextStep)
        for(r in model.rules) {
            val x=weights.getValue(r.name);val m=ms.getValue(r.name);val v=vs.getValue(r.name)
            for(i in x.indices) {
                if(i in r.frozen) {x[i]=0.0;continue}
                val grad=g.getValue(r.name)[i]*factor
                m[i]=config.beta1*saved.m.getValue(r.name)[i]+(1-config.beta1)*grad
                v[i]=config.beta2*saved.v.getValue(r.name)[i]+(1-config.beta2)*grad*grad
                val mh=m[i]/(1-config.beta1.pow(nextStep.toDouble()))
                val vh=v[i]/(1-config.beta2.pow(nextStep.toDouble()))
                x[i]-=lr*mh/(sqrt(vh)+config.epsilon)
                require(x[i].isFinite() && m[i].isFinite() && v[i].isFinite()) {"NONFINITE_ADAM"}
            }
            if(r.box) for(i in x.indices) x[i]=x[i].coerceIn(-r.cap,r.cap)
            else for(row in 0 until r.rows) projectRow(x.copyOfRange(row*r.cols,(row+1)*r.cols),r.cap).copyInto(x,row*r.cols)
        }
        val candidate=TrainModel(model.rules,weights)
        require(saved.cursor<=Long.MAX_VALUE-pending)
        val candidateState=OptimizerState(nextStep,saved.cursor+pending,ms,vs)
        validateState(candidate,candidateState,config)
        model=candidate;saved=candidateState;sums=zeros(model).toMutableMap();pending=0
        return norm
    }
    companion object {
        internal fun zeros(m:TrainModel)=m.rules.associate {it.name to DoubleArray(it.rows*it.cols)}
        internal fun copyState(s:OptimizerState)=OptimizerState(s.step,s.cursor,s.m.mapValues {it.value.copyOf()},s.v.mapValues {it.value.copyOf()})
        internal fun validateState(model:TrainModel,s:OptimizerState,c:Experiment) {
            require(s.step in 0..c.maxUpdates.toLong() && s.cursor>=s.step && s.m.keys==s.v.keys && s.m.keys==model.values().keys)
            for(r in model.rules) {
                val m=s.m.getValue(r.name);val v=s.v.getValue(r.name)
                require(m.size==r.rows*r.cols && v.size==m.size && m.all(Double::isFinite) && v.all {it.isFinite() && it>=0})
                if(s.step==0L) require(s.cursor==0L && m.all {it==0.0} && v.all {it==0.0}) {"INITIAL_OPTIMIZER_STATE"}
                require(r.frozen.all {m[it]==0.0 && v[it]==0.0}) {"FROZEN_MOMENTS"}
            }
        }
    }
}
