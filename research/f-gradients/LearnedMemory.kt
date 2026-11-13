package org.unovyra.uno.research

import org.unovyra.uno.core.UnoRefMatrix

/** Smooth offline projection only; f_e is fixed external data, not a learned embedding. */
class LearnedMemory(private val tape: ReverseF, wk: UnoRefMatrix, wv: UnoRefMatrix) {
    private val d=wk.cols
    init {
        require(wk.rows==128 && wv.rows==128 && wv.cols==d)
        require(wk.rowL1Within(2.0) && wv.rowL1Within(2.0)) { "MEMORY_WEIGHT_NORM" }
        tape.leaf("wk", DoubleArray(128*d) { wk[it/d,it%d] })
        tape.leaf("wv", DoubleArray(128*d) { wv[it/d,it%d] })
    }
    data class Stamp(val sequence: Long, val created: Long, val expiry: Long,
                     val scope: String, val version: String) {
        init {
            require(sequence>=0 && created>=0 && expiry>created && scope.isNotBlank() && version.isNotBlank())
        }
    }
    class Entry internal constructor(val stamp: Stamp, val key: ReverseF.V, val value: ReverseF.V)
    private val records=mutableListOf<Entry>()
    private var lastSequence=-1L
    private var lastTime=-1L
    fun commit(stamp: Stamp, h: ReverseF.V, fixedEvidence: DoubleArray): Entry {
        require(stamp.sequence>lastSequence && stamp.created>=lastTime) { "MEMORY_WRITE_ORDER" }
        require(h.x.size==d && h.x.all { it.isFinite() && it in -1.0..1.0 }) { "MEMORY_STATE" }
        require(fixedEvidence.size==128 && fixedEvidence.all { it.isFinite() && it in -1.0..1.0 }) { "MEMORY_EVIDENCE" }
        // Differentiable copy: caller changes to h.x must not change the committed state.
        val source=tape.scale(h,1.0)
        val key=tape.tanh(tape.mv(tape.leaves.getValue("wk"),128,d,source))
        val value=tape.tanh(tape.add(tape.mv(tape.leaves.getValue("wv"),128,d,source),
            ReverseF.V(fixedEvidence.copyOf())))
        return Entry(stamp,key,value).also {
            records.add(it); lastSequence=stamp.sequence; lastTime=stamp.created
        }
    }
    fun read(sequence: Long, now: Long, scope: String, version: String, revoked: Set<Long> = emptySet()): List<Entry> {
        require(sequence>=0 && now>=0 && scope.isNotBlank() && version.isNotBlank())
        // Explicit prefix view; a preloaded future record is still unavailable.
        return records.filter { e -> e.stamp.sequence < sequence && e.stamp.created<=now &&
            now<e.stamp.expiry && e.stamp.scope==scope && e.stamp.version==version && e.stamp.sequence !in revoked }
    }
}

/** Replay is full-prefix reconstruction, including state and earlier reads, never isolated h replay. */
class MemoryReplay(private val w: org.unovyra.uno.core.UnoRefWeights,
                   private val wk: UnoRefMatrix, private val wv: UnoRefMatrix) {
    class Event(val sequence: Long, val time: Long, features: DoubleArray, evidence: DoubleArray,
                val write: Boolean, val expiry: Long=1000L, val scope: String="test", val version: String="v1", revoked: Set<Long> = emptySet()) {
        val revoked=revoked.toSet()
        val features=features.copyOf()
        val evidence=evidence.copyOf()
    }
    data class Result(val tape: ReverseF, val states: List<ReverseF.V>, val memory: LearnedMemory)
    fun prefix(events: List<Event>, count: Int, initial: DoubleArray, mask: BooleanArray, steps: Int): Result {
        require(count in 1..events.size && count<=32) { "REPLAY_PREFIX_BOUND" }
        val tape=ReverseF(); tape.weights(w)
        val memory=LearnedMemory(tape,wk,wv)
        var state=tape.leaf("initial",initial)
        val metadata=ReverseF.V(DoubleArray(32)); val goal=ReverseF.V(DoubleArray(w.d))
        var previousSequence=-1L; var previousTime=-1L
        val states=mutableListOf<ReverseF.V>()
        for(i in 0 until count) {
            val e=events[i]
            require(e.sequence>previousSequence && e.time>=previousTime) { "REPLAY_EVENT_ORDER" }
            val eligible=memory.read(e.sequence,e.time,e.scope,e.version,e.revoked)
            state=tape.forward(w,tape.leaf("event.$i",e.features),metadata,state,goal,
                eligible.map { it.key },eligible.map { it.value },mask,steps)
            states.add(state)
            if(e.write) memory.commit(LearnedMemory.Stamp(e.sequence,e.time,e.expiry,e.scope,e.version),state,e.evidence)
            previousSequence=e.sequence; previousTime=e.time
        }
        return Result(tape,states,memory)
    }
}
