package org.unovyra.uno.research

import java.nio.file.Paths
import kotlin.math.*

/** Paired fixed examples, no optimizer or selection. Probes terminal-answer path separately from auxiliary CE. */
fun main(args:Array<String>) {
    require(args.size==1)
    val run=LadderRun(Paths.get(args[0]),100,4,60,47)
    for(step in listOf(0L,100L)) {
        val t=TrainCheckpoint.load(run.checkpoint(step),run.template,run.config)
        var loss=0.0
        for(i in 0 until run.train.size) loss+=JointGraph.evaluate(t.model,run.train,i,run.config).loss
        println("TRAIN_POOL step=$step mean_joint_loss=${loss/run.train.size} model=${t.model.fingerprint()}")
        for(length in listOf(12,24,48,96)) {
            val data=TrainingDataset(listOf(Ladder.example("r2_two",length,99,"probe")))
            val cfg=run.config.copy(datasetHash=data.hash,stateLoss=1.0,retrieveLoss=0.0,valueLoss=0.0)
            val e=JointGraph.evaluate(t.model,data,0,cfg)
            val raw=data.example(0)
            for(memory in listOf(true,false)) {
                val events=if(memory) raw.events else raw.events.map {v->MemoryReplay.Event(v.sequence,v.time,v.features,v.evidence,false)}
                val graph=MemoryReplay(t.model.core(),t.model.memory("wk"),t.model.memory("wv")).prefix(events,events.size,raw.initial,booleanArrayOf(true),2,96)
                val objective=TrainLoss.mse(graph.tape,graph.states.last(),raw.targetState,raw.stateValid)
                graph.tape.backward(objective,doubleArrayOf(1.0))
                println("SOURCE_PATH step=$step length=$length memory=$memory grad_source_value=${graph.tape.leaves.getValue("event.${raw.targetRecord-1}").g[0]}")
            }
            println("ANSWER_PATH step=$step length=$length loss=${e.loss} "+listOf("wk","wv","wq","wr","projection","us").joinToString(" ") {n->"$n=${e.gradient.getValue(n).maxOf {abs(it)}}"})
        }
    }
}
