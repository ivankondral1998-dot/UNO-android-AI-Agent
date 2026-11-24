package org.unovyra.uno.core

import kotlin.math.abs
import kotlin.math.tanh
import kotlin.random.Random

object Astra06StabilityTest {
    var pass = 0
    private fun verify(name: String, ok: Boolean) { check(ok) { name }; pass++; println("PASS ASTRA06 $name") }
    private val full = booleanArrayOf(true,true)
    private val left = booleanArrayOf(true,false)
    private val right = booleanArrayOf(false,true)
    private fun mat(r: Int,c: Int,col: Int=0,v: Double=0.0) = UnoRefMatrix(r,c,DoubleArray(r*c).also { it[col]=v })
    private fun weights(a: Double=1.0,b: Double=0.9,c: Double=2.0): UnoRefWeights {
        val base = UnoFReferenceTest.weights()
        val branches = List(2) { List(2) { j -> UnoRefBranch(mat(256,128,64*(1-j),a),
            mat(256,128,0,c),mat(64,256,0,b),DoubleArray(256),DoubleArray(64)) } }
        return UnoRefWeights(base.version,base.projection,base.us,base.ug,base.meta,base.e,base.bias,base.wq,base.wr,branches)
    }
    private fun event(h: DoubleArray,f: Double=0.0) = UnoRefEvent(doubleArrayOf(f),DoubleArray(32),h,DoubleArray(128))
    private fun step(f: UnoFReference,h: DoubleArray,m: BooleanArray,x: Double=0.0,k:Int=1) = f.forward(event(h,x),m,k,rho=1.0).state
    private fun distance(a: DoubleArray,b: DoubleArray) = a.indices.maxOf { abs(a[it]-b[it]) }
    private fun near(a:Double,b:Double) = abs(a-b)<1e-12
    fun run() {
        val f=UnoFReference(weights()); val s=f.stabilityBounds()
        verify("actual_decoded_norms", s.gamma>=.9 && near(s.gamma,.9) && s.lz>=1.8 && near(s.lz,1.8))
        val sl=UnoFReference(weights(1.0+5e-11,.9+5e-11,2.0+5e-11)).stabilityBounds()
        verify("allowed_tolerance_not_nominal_gamma",sl.gamma>.9 && sl.coefficient(full,.5)>.95 && sl.lz>1.8)
        verify("actual_branch_average_not_cap", near(UnoFReference(UnoFReferenceTest.weights(rec=true)).stabilityBounds().gamma,.45))
        verify("partial_identity_not_point95",s.coefficient(left,.5)==1.0 && s.coefficient(right,.5)==1.0)
        verify("full_coefficient",s.coefficient(full,.5)>=.95 && near(s.coefficient(full,.5),.95))
        verify("alpha_zero_and_one",s.coefficient(full,0.0)==1.0 && s.coefficient(left,0.0)==1.0 && s.coefficient(full,1.0)==s.gamma)
        verify("fair_sweep_requires_coverage",s.fairSweepCoefficient(listOf(left,left),.5)==null && s.fairSweepCoefficient(listOf(left,right),0.0)==null)
        verify("fair_sweep_bound",near(s.fairSweepCoefficient(listOf(left,right),.5)!!,.95))
        val h=DoubleArray(128); h[64]=1.0
        verify("unselected_coordinate_exact_identity",step(f,h,left)[64]==1.0)
        val zero=DoubleArray(128)
        verify("fixed_point_zero",step(f,zero,full).contentEquals(zero))
        val rng=Random(603)
        var one=true;var z=true;var sequence=true;var sweep=true;var k8=true;var bounded=true
        for (trial in 0 until 24) {
            val a=DoubleArray(128){rng.nextDouble(-1.0,1.0)}; val b=DoubleArray(128){rng.nextDouble(-1.0,1.0)}
            val dx=distance(a,b); val x=rng.nextDouble(-1.0,1.0); val y=rng.nextDouble(-1.0,1.0)
            val dz=abs(tanh(tanh(x))-tanh(tanh(y)))
            for (mask in listOf(full,left,right)) {
                val u=step(f,a,mask,x);val v=step(f,b,mask,x)
                one=one && distance(u,v)<=s.propagate(mask,.5,dx,0.0)+1e-12
                z=z && distance(u,step(f,b,mask,y))<=s.propagate(mask,.5,dx,dz)+1e-12
                bounded=bounded && u.all{it in -1.0..1.0}
            }
            var u=a;var v=b;var bound=dx
            for (mask in listOf(left,full,right,left)) {
                u=step(f,u,mask,x);v=step(f,v,mask,y);bound=s.propagate(mask,.5,bound,dz)
                sequence=sequence && distance(u,v)<=bound+1e-12
            }
            u=a;v=zero
            for(mask in listOf(left,right)){u=step(f,u,mask);v=step(f,v,mask)}
            sweep=sweep && distance(u,v)<=s.fairSweepCoefficient(listOf(left,right),.5)!!*distance(a,zero)+1e-12
            bound=dx;repeat(8){bound=s.propagate(full,.5,bound,0.0)}
            k8=k8 && distance(step(f,a,full,x,k=8),step(f,b,full,x,k=8))<=bound+1e-12
        }
        verify("real_kernel_same_z_masks_72_pairs",one)
        verify("real_kernel_different_z_72_pairs",z)
        verify("common_sequence_product_sum_96_steps",sequence)
        verify("real_kernel_fair_sweep_24_pairs",sweep)
        verify("real_kernel_K8_24_pairs",k8)
        verify("cube_invariance_sample",bounded)
        val flat=UnoFReference(weights(0.0,0.0,0.0)); val eps=1e-8
        val a=DoubleArray(128).also{it[0]=eps;it[64]=1.0}; val b=a.copyOf().also{it[0]=-eps}
        fun adaptive(h:DoubleArray)=flat.forwardAdaptive(event(h),UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE,1),0,3,0,
            {state,_-> if(state[0]>0) doubleArrayOf(0.0,-1000.0) else doubleArrayOf(0.0,1000.0)}, {0.0},epsilon=0.0,rho=1.0)
        val u=adaptive(a);val v=adaptive(b);val jump=distance(u.output!!.state,v.output!!.state)
        verify("actual_S6_distinct_masks",u.selection.q==1 && v.selection.q==2)
        verify("actual_adaptive_counterexample",jump==.5 && near(jump/distance(a,b),25_000_000.0))
        println("ASTRA06 gamma_upper=${s.gamma} Lz_upper=${s.lz} c_full=${s.coefficient(full,.5)} c_partial=${s.coefficient(left,.5)} tolerance_gamma=${sl.gamma} adaptive_amplification=${jump/distance(a,b)}")
        val w=1.0/(1.0+.51/127);val scale=w/127;val decoded=UnoRefMatrix(1,2,doubleArrayOf(scale*127,scale))
        verify("int8_decoded_norm_counterexample",decoded.decodedRowL1Upper()>1.003 && decoded.decodedRowL1Upper()<1.004)
        verify("invalid_mask_and_alpha",runCatching{s.coefficient(booleanArrayOf(false,false),.5)}.isFailure && runCatching{s.coefficient(full,Double.NaN)}.isFailure)
        verify("invalid_error_and_context_delta",runCatching{s.propagate(full,.5,-1.0,0.0)}.isFailure && runCatching{s.propagate(full,.5,1.0,Double.POSITIVE_INFINITY)}.isFailure)
    }
}
