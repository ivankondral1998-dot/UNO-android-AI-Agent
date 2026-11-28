package org.unovyra.uno.core

import java.io.File

// Host fixture adapter for existing UnoFReference. No production import path.
fun main(args: Array<String>) {
    val weights = File(args.single()).readLines().associate {
        val (name, values) = it.split('\t')
        name to values.split(',').map(String::toDouble).toDoubleArray()
    }
    val d = weights.getValue("e").size
    val vocabulary = weights.getValue("E").size / d
    fun mat(r: Int, c: Int, x: DoubleArray = DoubleArray(r*c)) = UnoRefMatrix(r, c, x)
    fun branch(name: String, l: Int, j: Int, length: Int): DoubleArray {
        val offset = (l * (d / 64) + j) * length
        return weights.getValue(name).copyOfRange(offset, offset + length)
    }
    val rows = weights.getValue("E")
    val projection = DoubleArray(d*vocabulary) { n -> rows[(n % vocabulary)*d + (n / vocabulary)] }
    val w = UnoRefWeights("TEXT_HOST_FIXTURE", mat(d,vocabulary,projection), mat(d,d,weights.getValue("Us")),
        mat(d,d), mat(d,32), weights.getValue("e"), weights.getValue("bz"), mat(128,d), mat(d,128),
        List(2) { l -> List(d/64) { j ->
            UnoRefBranch(mat(256,d,branch("A",l,j,256*d)), mat(256,d,branch("C",l,j,256*d)),
                mat(64,256,branch("B",l,j,64*256)), branch("a",l,j,256), branch("b",l,j,64))
        }})
    val ref = UnoFReference(w)
    var state = DoubleArray(d)
    for (x in listOf(0, 1, 2, 3)) {
        val input = DoubleArray(vocabulary)
        input[x] = 1.0
        state = ref.forward(UnoRefEvent(input,DoubleArray(32),state,DoubleArray(d)),
            BooleanArray(d/64) { true },1).state
        println(state.joinToString(","))
    }
}
