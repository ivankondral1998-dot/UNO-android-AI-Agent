package org.unovyra.uno.research

import java.nio.file.*

/** No epoch loop. Explicit diagnostic update, at most two across checkpoint resumes. */
fun main(args:Array<String>) {
    require(args.isNotEmpty() && args[0] in listOf("inspect","step","resume")) {"Usage: inspect | step FILE | resume FILE"}
    val dataset=TrainingDataset(Synthetic.examples());val model=Synthetic.model();val config=Experiment(dataset.hash)
    val t=if(args[0]=="resume") {
        require(args.size==2);TrainCheckpoint.load(Paths.get(args[1]),model,config)
    } else OfflineTrainer(model,config)
    if(args[0]!="inspect") require(args.size==2)
    if(args[0]=="step") require(!Files.exists(Paths.get(args[1]))) {"REFUSE_EXISTING_CHECKPOINT"}
    val index=(t.optimizer().cursor%dataset.size).toInt();val sample=dataset.example(index)
    val result=JointGraph.evaluate(t.model,dataset,index,config)
    println("DATASET=${config.datasetHash} sample=${sample.id} losses=${result.parts} total=${result.loss} step=${t.optimizer().step}")
    if(args[0]!="inspect") {
        t.accumulate(result);val norm=t.update();TrainCheckpoint.save(Paths.get(args[1]),t)
        println("SYNTHETIC_DIAGNOSTIC_STEP=${t.optimizer().step} gradientNorm=$norm model=${t.model.fingerprint()} checkpoint=${Paths.get(args[1]).fileName}")
    }
    println("NO_PRODUCTION_TRAINING NO_EPOCH_LOOP DOUBLE_FIXED_ROUTE")
}
