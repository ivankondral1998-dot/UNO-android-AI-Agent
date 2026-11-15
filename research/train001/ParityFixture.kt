package org.unovyra.uno.research

import java.nio.file.*

fun main(args:Array<String>) {
    require(args.size in 1..3)
    val p=Paths.get(args[0]);Files.createDirectories(p)
    val model=Ladder.model(47)
    val data=TrainingDataset(listOf(Ladder.example(args.getOrNull(1)?:"r2_two",args.getOrNull(2)?.toInt()?:12,99,"parity")))
    val c=Experiment(data.hash,replayLimit=96,innerSteps=2,route=listOf(true))
    val result=JointGraph.evaluate(model,data,0,c)
    Files.newBufferedWriter(p.resolve("weights.tsv")).use {o ->for(r in model.rules) {
        o.appendLine(listOf(r.name,r.rows,r.cols,model.values().getValue(r.name).joinToString(","),result.gradient.getValue(r.name).joinToString(",")).joinToString("\t"))
    }}
    val trainer=OfflineTrainer(model,c)
    for(step in 1..2) {
        val evaluated=JointGraph.evaluate(trainer.model,data,0,c)
        trainer.accumulate(evaluated);trainer.update()
        val optimizer=trainer.optimizer();val values=trainer.model.values()
        Files.newBufferedWriter(p.resolve("update$step.tsv")).use {o ->for(r in model.rules) {
            o.appendLine(listOf(r.name,r.cap,r.box,evaluated.gradient.getValue(r.name).joinToString(","),values.getValue(r.name).joinToString(","),optimizer.m.getValue(r.name).joinToString(","),optimizer.v.getValue(r.name).joinToString(",")).joinToString("\t"))
        }}
    }
    val e=data.example(0)
    Files.newBufferedWriter(p.resolve("events.tsv")).use {o ->for(v in e.events) o.appendLine(listOf(v.sequence,v.write,v.features.joinToString(",")).joinToString("\t"))}
    Files.writeString(p.resolve("target.tsv"),listOf(e.targetRecord,e.targetState[0],e.targetValue[0],result.loss).joinToString("\t"))
    Files.writeString(p.resolve("controls.tsv"),listOf("full","memory_off","zero_values").joinToString("\n") {mode -> "$mode\t${LadderEval.predict(model,e,mode).state}"})
    println("KOTLIN_FIXTURE loss=${result.loss} model=${model.fingerprint()} data=${data.hash}")
}
