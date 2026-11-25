package org.unovyra.uno.core

import java.io.File
import kotlin.math.tanh

/** Host-only bridge to the existing F. This TSV is a test fixture, NOT a weight ABI. */
private fun matrices(file: File): Map<String, UnoRefMatrix> {
    val result = linkedMapOf<String, UnoRefMatrix>()
    for (line in file.readLines()) {
        val fields = line.split('\t')
        require(fields.size == 4 && fields[0] !in result)
        val rows = fields[1].toInt(); val cols = fields[2].toInt()
        require(rows in 1..256 && cols in 1..256)
        result[fields[0]] = UnoRefMatrix(rows, cols, fields[3].split(',').map(String::toDouble).toDoubleArray())
    }
    require(result.size == 20)
    return result
}

private fun reference(w: Map<String, UnoRefMatrix>): UnoFReference {
    fun m(n: String) = w.getValue(n)
    fun v(n: String) = m(n).let { a -> require(a.cols == 1); DoubleArray(a.rows) { a[it, 0] } }
    val branches = (0..1).map { l ->
        val n = "branch.$l.0."
        listOf(UnoRefBranch(m(n+"a"), m(n+"c"), m(n+"b"), v(n+"ab"), v(n+"bb")))
    }
    return UnoFReference(UnoRefWeights("TRAIN001_HOST_FIXTURE", m("projection"), m("us"), m("ug"),
        m("meta"), v("e"), v("bias"), m("wq"), m("wr"), branches))
}

fun main(args: Array<String>) {
    require(args.size == 2 || args.size == 3)
    val w = matrices(File(args[1]))
    if (args[0] == "reject") {
        try { reference(w); error("INVALID_REAL_CHECKPOINT_ACCEPTED") }
        catch (e: IllegalArgumentException) {
            require(e.message in setOf("B2_RECURRENCE_NORM_INVALID", "B2_S4_NORM_INVALID"))
            println("CORE_REJECTED_DECODED_NORM\t${e.message}")
        }
        return
    }
    require(args[0] == "fixture" && args.size == 3)
    val f = reference(w)
    val events = File(args[2]).readLines().map { it.split(',').map(String::toDouble).toDoubleArray() }
    require(events.size in 1..96 && events.all { it.size == 3 && it.all(Double::isFinite) })
    require(events.last()[2] in setOf(-1.0, -2.0) && events.dropLast(1).all { it[2] in setOf(0.0, 1.0) })
    val wk = w.getValue("wk"); val wv = w.getValue("wv")
    require(wk.rows == 128 && wk.cols == 64 && wv.rows == 128 && wv.cols == 64)
    for (mode in listOf("full", "memory_off", "zero_values")) {
        var s = DoubleArray(64)
        val bank = mutableListOf<Pair<Int, UnoRefMemoryVector>>()
        for ((index, event) in events.withIndex()) {
            val read = when (mode) {
                "memory_off" -> emptyList()
                "zero_values" -> bank.map { UnoRefMemoryVector(it.second.key, DoubleArray(128)) }
                else -> bank.map { it.second }
            }
            val out = f.forward(UnoRefEvent(event, DoubleArray(32), s, DoubleArray(64), read),
                booleanArrayOf(true), steps = 2)
            check(out.trace.aCalls == 4 && out.trace.bCalls == 4 && out.trace.cCalls == 2)
            s = out.state
            if (event[2] == 1.0) bank += (index+1) to UnoRefMemoryVector(
                wk.multiply(s).map(::tanh).toDoubleArray(), wv.multiply(s).map(::tanh).toDoubleArray())
        }
        println("STATE\t$mode\t${s.joinToString(",")}")
        for ((seq, v) in bank) println("BANK\t$mode\t$seq\t${v.key.joinToString(",")}\t${v.value.joinToString(",")}")
    }
}
