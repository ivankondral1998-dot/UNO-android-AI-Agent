package org.unovyra.uno.research

import org.unovyra.uno.core.*
import kotlin.math.*

/** Research vector VJP tape. Gradients accumulate at shared leaf identities. No optimizer. */
class ReverseF {
    class V(val x: DoubleArray) { val g = DoubleArray(x.size) }
    val leaves = linkedMapOf<String,V>()
    private val pullbacks = mutableListOf<() -> Unit>()
    fun leaf(name: String, x: DoubleArray): V {
        require(name !in leaves && x.all(Double::isFinite))
        return V(x.copyOf()).also { leaves[name] = it }
    }
    private fun node(x: DoubleArray, back: (V) -> Unit): V {
        require(x.all(Double::isFinite)) { "NONFINITE_RESEARCH_FORWARD" }
        return V(x).also { y -> pullbacks.add { back(y) } }
    }
    fun add(vararg xs: V): V {
        require(xs.isNotEmpty() && xs.all { it.x.size == xs[0].x.size })
        return node(DoubleArray(xs[0].x.size) { i -> xs.sumOf { it.x[i] } }) { y ->
            xs.forEach { a -> a.g.indices.forEach { i -> a.g[i] += y.g[i] } }
        }
    }
    fun scale(a: V, s: Double) = node(DoubleArray(a.x.size) { a.x[it]*s }) { y ->
        a.g.indices.forEach { a.g[it] += s*y.g[it] }
    }
    fun tanh(a: V) = node(DoubleArray(a.x.size) { tanh(a.x[it]) }) { y ->
        a.g.indices.forEach { a.g[it] += (1-y.x[it]*y.x[it])*y.g[it] }
    }
    fun mv(a: V, rows: Int, cols: Int, b: V): V {
        require(a.x.size == rows*cols && b.x.size == cols)
        val out = DoubleArray(rows)
        for (r in 0 until rows) for (c in 0 until cols) out[r] += a.x[r*cols+c]*b.x[c]
        return node(out) { y ->
            for (r in 0 until rows) for (c in 0 until cols) {
                a.g[r*cols+c] += y.g[r]*b.x[c]
                b.g[c] += a.x[r*cols+c]*y.g[r]
            }
        }
    }
    fun slice(a: V, from: Int, n: Int) = node(a.x.copyOfRange(from,from+n)) { y ->
        for (i in 0 until n) a.g[from+i] += y.g[i]
    }
    fun concat(xs: List<V>): V {
        return node(xs.flatMap { it.x.toList() }.toDoubleArray()) { y ->
            var offset=0
            for (a in xs) { for (i in a.g.indices) a.g[i] += y.g[offset+i]; offset += a.x.size }
        }
    }
    private fun read(q: V, keys: List<V>, values: List<V>, temperature: Double): V {
        if (keys.isEmpty()) return V(DoubleArray(q.x.size))
        val divisor=sqrt(q.x.size.toDouble())*temperature
        val scores=keys.map { k -> q.x.indices.sumOf { q.x[it]*k.x[it] } / divisor }
        val largest=scores.max()
        val ex=scores.map { exp(it-largest) }; val total=ex.sum()
        require(total.isFinite() && total>0)
        val p=ex.map { it/total }
        val out=DoubleArray(q.x.size) { j -> keys.indices.sumOf { i -> p[i]*values[i].x[j] } }
        return node(out) { y ->
            for (i in keys.indices) {
                val ds=p[i]*y.g.indices.sumOf { j -> y.g[j]*(values[i].x[j]-out[j]) }
                for (j in q.x.indices) {
                    values[i].g[j] += p[i]*y.g[j]
                    keys[i].g[j] += ds*q.x[j]/divisor
                    q.g[j] += ds*keys[i].x[j]/divisor
                }
            }
        }
    }
    fun backward(output: V, seed: DoubleArray) {
        require(seed.size==output.x.size && seed.all(Double::isFinite))
        // Single-use tape: a second call must not silently accumulate intermediate adjoints.
        check(!used); used=true
        seed.copyInto(output.g)
        pullbacks.asReversed().forEach { it() }
        require(leaves.values.all { it.g.all(Double::isFinite) }) { "NONFINITE_GRADIENT" }
    }
    private var used=false
    fun weights(w: UnoRefWeights) {
        fun matrix(name: String, a: UnoRefMatrix) = leaf(name,DoubleArray(a.rows*a.cols) { a[it/a.cols,it%a.cols] })
        matrix("projection",w.projection); matrix("us",w.us); matrix("ug",w.ug); matrix("meta",w.meta)
        leaf("e",w.e); leaf("bias",w.bias); matrix("wq",w.wq); matrix("wr",w.wr)
        for (l in 0..1) for (j in 0 until w.blocks) {
            val b=w.branches[l][j]; val p="branch.$l.$j"
            matrix("$p.a",b.a); matrix("$p.c",b.c); matrix("$p.b",b.b)
            leaf("$p.ab",b.aBias); leaf("$p.bb",b.bBias)
        }
    }
    /** Caller validates against the existing oracle before building a tape. Fixed route only. */
    fun forward(w: UnoRefWeights, f: V, metadata: V, state: V, goal: V,
                keys: List<V>, values: List<V>, mask: BooleanArray, steps: Int,
                alpha: Double=.5, rho: Double=.5, temperature: Double=1.0): V {
        // Reuse actual contract, including bounds and memory shapes, without a parallel validator.
        UnoFReference(w).forward(UnoRefEvent(f.x,metadata.x,state.x,goal.x,
            keys.zip(values).map { UnoRefMemoryVector(it.first.x,it.second.x) }),mask,steps,alpha,rho,temperature)
        require(keys.size==values.size)
        fun mat(n: String,r: Int,c: Int,x: V)=mv(leaves.getValue(n),r,c,x)
        val d=w.d
        val z0=tanh(add(mat("projection",d,w.inputWidth,f),mat("us",d,d,state),
            mat("ug",d,d,goal),mat("meta",d,32,metadata),leaves.getValue("e"),leaves.getValue("bias")))
        val q=tanh(mat("wq",128,d,z0))
        val z=tanh(add(z0,mat("wr",d,128,read(q,keys,values,temperature))))
        var h=add(scale(state,rho),scale(z,1-rho))
        val cz=Array(2) { l -> Array<V?>(w.blocks) { j ->
            if(mask[j]) mat("branch.$l.$j.c",256,d,z) else null
        } }
        repeat(steps) {
            h=concat((0 until w.blocks).map { j ->
                val old=slice(h,j*64,64)
                if(!mask[j]) old else {
                    val branches=(0..1).map { l ->
                        val p="branch.$l.$j"
                        val u=tanh(add(mat("$p.a",256,d,h),cz[l][j]!!,leaves.getValue("$p.ab")))
                        tanh(add(mat("$p.b",64,256,u),leaves.getValue("$p.bb")))
                    }
                    add(scale(old,1-alpha),scale(add(*branches.toTypedArray()),alpha/2))
                }
            })
        }
        return h
    }
}
