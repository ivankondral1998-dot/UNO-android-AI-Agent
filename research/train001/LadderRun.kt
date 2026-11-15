package org.unovyra.uno.research

import java.nio.file.*
import java.util.jar.JarFile
import java.security.MessageDigest

/** All stochasticity is counter based: seed + immutable dataset manifest + cursor.
 * There is no mutable PRNG/dropout state between updates. Every update is committed alone. */
class LadderRun(val directory:Path,val steps:Int,val batch:Int,val samples:Int,val seed:Long) {
    val train=Ladder.data("train",samples,seed)
    val validation=Ladder.data("validation",20,seed)
    val template=Ladder.model(seed)
    val config=Experiment(train.hash,seed=seed,totalSteps=maxOf(2000,steps),maxUpdates=steps,warmup=1000,
        replayLimit=96,innerSteps=2,route=listOf(true))
    init {require(steps in 1..10000 && batch in 1..64)}
    private fun executionHash():String {
        val path=Paths.get(javaClass.protectionDomain.codeSource.location.toURI())
        require(Files.isRegularFile(path)) {"RUN_FROM_COMPILED_JAR"}
        val digest=MessageDigest.getInstance("SHA-256")
        val names=listOf("Ladder", "TrainModel", "OfflineTrainer", "TrainLoss", "TrainCheckpoint", "CheckpointKt", "ParametersKt", "Experiment", "TrainingDataset", "JointGraph", "ReverseF", "LearnedMemory", "MemoryReplay", "UnoRef", "UnoFReference", "LockedReportKt")
        JarFile(path.toFile()).use {jar ->
            for(entry in jar.entries().toList().filter {e->e.name.endsWith(".class") && e.name.startsWith("org/unovyra/") &&
                names.any {e.name.substringAfterLast('/').startsWith(it)}}.sortedBy {it.name}) {
                digest.update(entry.name.toByteArray(Charsets.UTF_8));jar.getInputStream(entry).use {digest.update(it.readBytes())}
            }
        }
        return digest.digest().joinToString("") {"%02x".format(it)}
    }
    private val manifest="LADDER-V2\nexecution=${executionHash()}\nsteps=$steps\nbatch=$batch\nsamples=$samples\nseed=$seed\ntrain=${train.hash}\nvalidation=${validation.hash}\nschema=${template.schemaHash()}\nconfig=${sha256(configBytes(config))}\n"
    fun checkpoint(step:Long)=directory.resolve("step-%05d.uno".format(step))
    fun open(resume:Boolean):OfflineTrainer {
        if(!resume) {
            require(!Files.exists(directory) || Files.list(directory).use {!it.findAny().isPresent}) {"OUTPUT_EXISTS"}
            Files.createDirectories(directory);Files.writeString(directory.resolve("manifest.txt"),manifest,StandardOpenOption.CREATE_NEW)
            val t=OfflineTrainer(template,config);TrainCheckpoint.save(checkpoint(0),t);return t
        }
        require(Files.readString(directory.resolve("manifest.txt"))==manifest) {"RUN_MANIFEST_MISMATCH"}
        val latest=Files.list(directory).use {stream ->stream.filter {it.fileName.toString().matches(Regex("step-[0-9]{5}\\.uno"))}.sorted().toList().lastOrNull()}
        require(latest!=null) {"MISSING_CHECKPOINT"}
        val t=TrainCheckpoint.load(latest,template,config)
        require(latest==checkpoint(t.optimizer().step) && t.optimizer().cursor==t.optimizer().step*batch) {"CURSOR_MISMATCH"}
        return t
    }
    fun advance(t:OfflineTrainer,until:Int,observe:(Long,Double,Double)->Unit={_,_,_->}) {
        require(t.config==config && until in t.optimizer().step.toInt()..steps)
        require(t.pending==0 && t.optimizer().cursor==t.optimizer().step*batch) {"BATCH_CURSOR_BOUNDARY"}
        while(t.optimizer().step<until) {
            var loss=0.0
            val cursor=t.optimizer().cursor
            repeat(batch) {j ->
                val e=JointGraph.evaluate(t.model,train,((cursor+j)%train.size).toInt(),config)
                loss+=e.loss;t.accumulate(e)
            }
            val norm=t.update()
            TrainCheckpoint.save(checkpoint(t.optimizer().step),t)
            observe(t.optimizer().step,loss/batch,norm)
        }
    }
    /** Validation selects only among durable checkpoints. Recomputable after a crash; no best-file race. */
    fun select():Long {
        var best=0L;var bestLoss=Double.POSITIVE_INFINITY
        for(step in (0..steps).filter {it==0 || it%10==0 || it==steps}) {
            if(!Files.exists(checkpoint(step.toLong()))) continue
            val t=TrainCheckpoint.load(checkpoint(step.toLong()),template,config)
            val m=LadderEval.score(t.model,validation)
            println("VALIDATION step=$step n=${m.n} mse=${m.mse} accuracy=${m.accuracy} misses=${m.misses}")
            if(m.mse<bestLoss) {bestLoss=m.mse;best=step.toLong()}
        }
        return best
    }
}
fun main(args:Array<String>) {
    require(args.size in 6..7) {"train|resume|test|export|prepare DIR TOTAL_STEPS BATCH TRAIN_SAMPLES SEED [UNTIL_STEP]"}
    val (mode,dir)=args
    require(mode in listOf("train","resume","test","export","prepare"))
    val run=LadderRun(Paths.get(dir).toAbsolutePath(),args[2].toInt(),args[3].toInt(),args[4].toInt(),args[5].toLong())
    if(mode=="train" || mode=="resume") {
        val t=run.open(mode=="resume")
        run.advance(t,args.getOrNull(6)?.toInt()?:run.steps) {step,loss,norm ->
            println("TRAIN step=$step loss=$loss gradNorm=$norm model=${t.model.fingerprint()}")
        }
        println("BOUNDARY step=${t.optimizer().step} cursor=${t.optimizer().cursor} DOUBLE_FIXED_ROUTE_NO_CUDA")
    } else if(mode=="test") {
        run.open(true) // enforce immutable manifest; missing/corrupt newest checkpoint fails closed
        require(Files.exists(run.checkpoint(run.steps.toLong()))) {"TRAIN_BUDGET_NOT_FINISHED"}
        val selected=run.select()
        val pin="validation-selected-step=$selected checkpoint-sha256=${sha256(Files.readAllBytes(run.checkpoint(selected)))} test=${Ladder.testData(run.seed).hash} erased=${Ladder.testData(run.seed,true).hash}\n"
        print(lockedReport(run.directory,pin) {
        val report=StringBuilder()
        val model=TrainCheckpoint.load(run.checkpoint(selected),run.template,run.config).model
        // Test labels never enter selection or training. Retry pins exactly this selection.
        for(rung in Ladder.rungs) for(length in Ladder.lengths) {
            val examples=(0 until 16).map {i ->Ladder.example(rung,length,run.seed+2_000_000+length*100+i,"test-$rung-$length-$i")}
            val erased=(0 until 16).map {i ->Ladder.example(rung,length,run.seed+2_000_000+length*100+i,"test-$rung-$length-$i",true)}
            for(ablation in listOf("full","memory_off","zero_values","erased")) {
                val data=TrainingDataset(if(ablation=="erased") erased else examples)
                val m=LadderEval.score(model,data,if(ablation=="erased") "full" else ablation)
                report.appendLine("TEST rung=$rung length=$length mode=$ablation hash=${data.hash} n=${m.n} correct=${m.correct} eligibilityMisses=${m.misses} keyCorrect=${m.keyCorrect} mse=${m.mse}")
            }
        }
        report.toString()
        })
    } else {
        // TSV is exact Double round-trip text. Same raw data for any baseline, including erasures.
        require(!Files.exists(run.directory)) {"OUTPUT_EXISTS"};Files.createDirectories(run.directory)
        for(split in listOf("train","validation","test","erased")) {
            val data=if(split=="test" || split=="erased") Ladder.testData(run.seed,split=="erased")
                else Ladder.data(split,if(split=="train") run.samples else 20,run.seed)
            Files.newBufferedWriter(run.directory.resolve("$split.tsv")).use {o ->
                for(i in 0 until data.size) {
                    val e=data.example(i)
                    o.appendLine(listOf(e.id,if(e.targetState[0]>0) "1" else "0",e.targetRecord.toString(),e.targetValue[0].toString(),e.events.joinToString(";") {v->v.features.joinToString(",")}).joinToString("\t"))
                }
            }
        }
        if(mode=="prepare") {
            val values=run.template.values()
            Files.newBufferedWriter(run.directory.resolve("initial.tsv")).use {o ->for(r in run.template.rules)
                o.appendLine(listOf(r.name,r.rows,r.cols,r.cap,r.box,values.getValue(r.name).joinToString(",")).joinToString("\t"))
            }
            println("PREPARED_ONLY no updates model=${run.template.fingerprint()} schema=${run.template.schemaHash()}")
        }
    }
}
