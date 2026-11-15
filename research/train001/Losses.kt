package org.unovyra.uno.research

import kotlin.math.*

/** Scalar branches on the existing tape; targets never become F inputs. */
object TrainLoss {
    fun mse(t: ReverseF, x: ReverseF.V, target: DoubleArray, valid: BooleanArray): ReverseF.V {
        require(x.x.size==target.size && valid.size==target.size && valid.any {it}) { "MSE_TARGET_MASK" }
        require(target.indices.all { !valid[it] || target[it].isFinite() })
        val n=valid.count {it}.toDouble()
        return t.node(doubleArrayOf(target.indices.sumOf { if(valid[it]) (x.x[it]-target[it]).pow(2)/n else 0.0 })) { y ->
            for(i in target.indices) if(valid[i]) x.g[i]+=y.g[0]*2*(x.x[i]-target[i])/n
        }
    }
    fun retrieval(t: ReverseF, query: ReverseF.V, keys: List<ReverseF.V>, target: Int): ReverseF.V {
        require(keys.isNotEmpty() && target in keys.indices && keys.all { it.x.size==query.x.size }) { "RETRIEVAL_TARGET_CATALOG" }
        val scale=1/sqrt(query.x.size.toDouble())
        val logits=keys.map { k -> query.x.indices.sumOf { query.x[it]*k.x[it] }*scale }
        require(logits.all(Double::isFinite))
        val largest=logits.max();val ex=logits.map {exp(it-largest)};val z=ex.sum()
        val value=ln(z)+(largest-logits[target]) // stable even when probability underflows
        return t.node(doubleArrayOf(value)) { y ->
            for(j in keys.indices) {
                val delta=(ex[j]/z-if(j==target) 1.0 else 0.0)*scale*y.g[0]
                for(i in query.x.indices) {
                    query.g[i]+=delta*keys[j].x[i]
                    keys[j].g[i]+=delta*query.x[i]
                }
            }
        }
    }
    fun joint(t: ReverseF, losses: List<ReverseF.V>, coefficients: List<Double>): ReverseF.V {
        require(losses.size==coefficients.size && losses.isNotEmpty() && losses.all {it.x.size==1})
        require(coefficients.all {it.isFinite() && it>=0} && coefficients.any {it>0})
        return t.add(*losses.indices.map {t.scale(losses[it],coefficients[it])}.toTypedArray())
    }
}
