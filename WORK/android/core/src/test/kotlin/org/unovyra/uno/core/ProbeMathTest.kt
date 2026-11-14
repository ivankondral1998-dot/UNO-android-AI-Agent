package org.unovyra.uno.core

object ProbeMathTest {
    var pass = 0
    private fun ok(name: String, body: () -> Unit) { body(); pass++; println("PASS $name") }
    fun run() {
        ok("percentiles nearest rank") {
            val values=(1L..100L).toList().reversed()
            check(ProbeMath.summarize(values) == ProbeMath.Latency(50,95,99,1,100,100))
        }
        ok("single sample") { check(ProbeMath.summarize(listOf(7)).p99Nanos == 7L) }
        ok("reject invalid percentile") {
            check(runCatching { ProbeMath.percentile(listOf(2), Double.NaN) }.isFailure)
            check(runCatching { ProbeMath.percentile(emptyList(), .5) }.isFailure)
            check(runCatching { ProbeMath.percentile(listOf(-1), .5) }.isFailure)
        }
        ok("inactive kernel truly skipped") {
            var called=0
            check(ProbeMath.conditionalKernel(false,{called++;-1},{42})==42)
            check(called==0)
        }
        ok("active kernel executes exactly once") {
            var called=0
            check(ProbeMath.conditionalKernel(true,{called++;9},{-1})==9)
            check(called==1)
        }
    }
}
