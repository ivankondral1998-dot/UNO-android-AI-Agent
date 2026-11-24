package org.unovyra.uno.core

/** Actual S6 runtime-law fixtures for independent CPU gradient tests. */
object Astra12PolicyParityTest {
    var pass=0
    private fun verify(name:String, ok:Boolean) { check(ok){name};pass++;println("PASS ASTRA12 $name") }
    fun run() {
        val logits=doubleArrayOf(.7,-.4,.2,-.9)
        var cases=0
        for (count in 1..4) for (turn in 0L..3L) for (eps in listOf(0.0,.05,1.0)) for (temp in listOf(.5,1.7)) {
            val s=UnoS6Sampler(4,2,32,128,eps,temp)
            val b=UnoS6Budget(s.estimatedCost(count,1).first,Long.MAX_VALUE,1)
            val cat=s.feasible(b)
            check(cat.contentEquals(IntArray(count){it+1}))
            val w=s.prefixWeights(logits,turn,cat)
            val p=w.map{eps/count+(1-eps)*it/w.sum()}
            check(kotlin.math.abs(p.sum()-1)<1e-14)
            println("ASTRA12_PREFIX\t$count\t$turn\t$eps\t$temp\t${logits.joinToString(",")}\t${p.joinToString(",")}")
            cases++
        }
        verify("runtime_prefix_fixtures_96",cases==96)
        val s=UnoS6Sampler(2,2,64,256)
        val r=UnoS6Prng(3,7)
        val b=UnoS6Budget(s.estimatedCost(1,1).first,Long.MAX_VALUE,2)
        verify("budget_forced_no_score_head",s.stopAfterStep(1,1,b,r){error("forced hazard")}==UnoS6StopReason.NEXT_STEP_BUDGET && r.counter==7L)
        verify("cap_forced_no_score_head",s.stopAfterStep(1,2,b,r){error("forced hazard")}==UnoS6StopReason.STEP_LIMIT && r.counter==7L)
        val ample=UnoS6Budget(Long.MAX_VALUE,Long.MAX_VALUE,3)
        verify("fixed_zero_hazard",s.stopAfterStep(1,1,ample,r){0.0}==null && r.counter==7L)
        verify("fixed_one_hazard",s.stopAfterStep(1,2,ample,r){1.0}==UnoS6StopReason.HAZARD && r.counter==7L)
        val expected=UnoS6Prng(3,7).nextDouble()<.37
        verify("interior_hazard_draw",(s.stopAfterStep(1,1,ample,r){.37}==UnoS6StopReason.HAZARD)==expected && r.counter==8L)
    }
}
