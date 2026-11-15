package org.unovyra.uno.research

import java.io.*
import java.nio.file.*
import java.nio.channels.FileChannel
import java.nio.ByteBuffer

internal fun configBytes(c:Experiment)=encode {o ->
    o.writeUTF(c.datasetHash);o.writeLong(c.seed)
    listOf(c.peakRate,c.floorRate,c.beta1,c.beta2,c.epsilon,c.clip,c.stateLoss,c.retrieveLoss,c.valueLoss).forEach(o::writeDouble)
    listOf(c.warmup,c.totalSteps,c.maxUpdates,c.innerSteps).forEach(o::writeInt)
    o.writeInt(c.route.size);c.route.forEach(o::writeBoolean);o.writeInt(c.replayLimit)
}
object TrainCheckpoint {
    private const val MAX_BYTES=64*1024*1024
    fun save(file:Path,t:OfflineTrainer) {
        require(t.pending==0) {"CHECKPOINT_OPTIMIZER_BOUNDARY_ONLY"}
        val model=t.model;val state=t.optimizer();OfflineTrainer.validateState(model,state,t.config)
        val body=encode {o ->
            o.writeInt(1);o.writeUTF(model.schemaHash())
            val cfg=configBytes(t.config);o.writeInt(cfg.size);o.write(cfg)
            o.writeLong(state.step);o.writeLong(state.cursor);o.writeInt(model.rules.size)
            val weights=model.values()
            for(r in model.rules) {
                o.writeUTF(r.name);o.writeInt(r.rows*r.cols)
                for(x in listOf(weights.getValue(r.name),state.m.getValue(r.name),state.v.getValue(r.name))) x.forEach(o::writeDouble)
            }
        }
        require(body.size<=MAX_BYTES)
        val bytes=encode {o ->o.writeUTF("UNO-TRAIN-001/DOUBLE/RESEARCH");o.writeUTF(sha256(body));o.writeInt(body.size);o.write(body)}
        val path=file.toAbsolutePath();val temp=Files.createTempFile(path.parent,"uno-train-", ".tmp")
        try {
            FileChannel.open(temp,StandardOpenOption.WRITE).use {ch ->
                val buffer=ByteBuffer.wrap(bytes);while(buffer.hasRemaining()) ch.write(buffer);ch.force(true)
            }
            Files.move(temp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING)
        } finally {Files.deleteIfExists(temp)}
    }
    /** A trusted schema and experiment manifest are mandatory; files cannot invent shapes/configuration. */
    fun load(file:Path,template:TrainModel,expected:Experiment):OfflineTrainer {
        require(Files.size(file) in 1..(MAX_BYTES+1024).toLong()) {"CHECKPOINT_SIZE"}
        val input=DataInputStream(ByteArrayInputStream(Files.readAllBytes(file)))
        require(input.readUTF()=="UNO-TRAIN-001/DOUBLE/RESEARCH") {"CHECKPOINT_FORMAT"}
        val checksum=input.readUTF();val size=input.readInt()
        require(size in 1..MAX_BYTES && size==input.available()) {"CHECKPOINT_LENGTH"}
        val bytes=ByteArray(size);input.readFully(bytes)
        require(sha256(bytes)==checksum) {"CHECKPOINT_INTEGRITY"}
        val i=DataInputStream(ByteArrayInputStream(bytes))
        require(i.readInt()==1 && i.readUTF()==template.schemaHash()) {"CHECKPOINT_SCHEMA"}
        val cfg=configBytes(expected);require(i.readInt()==cfg.size) {"CHECKPOINT_CONFIG_SIZE"}
        val stored=ByteArray(cfg.size);i.readFully(stored)
        require(stored.contentEquals(cfg)) {"CHECKPOINT_EXPERIMENT"}
        val step=i.readLong();val cursor=i.readLong();require(i.readInt()==template.rules.size)
        val values=linkedMapOf<String,DoubleArray>();val ms=linkedMapOf<String,DoubleArray>();val vs=linkedMapOf<String,DoubleArray>()
        for(r in template.rules) {
            require(i.readUTF()==r.name && i.readInt()==r.rows*r.cols) {"CHECKPOINT_TENSOR"}
            for(map in listOf(values,ms,vs)) map[r.name]=DoubleArray(r.rows*r.cols) {i.readDouble()}
        }
        require(i.available()==0) {"CHECKPOINT_TRAILING_BYTES"}
        return OfflineTrainer(TrainModel(template.rules,values),expected,OptimizerState(step,cursor,ms,vs))
    }
}
