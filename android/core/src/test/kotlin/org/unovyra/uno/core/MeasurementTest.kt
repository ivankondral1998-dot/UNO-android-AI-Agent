package org.unovyra.uno.core

object MeasurementTest {
    var pass = 0
    private fun test(name: String, body: () -> Unit) { body();pass++;println("PASS $name") }
    fun run() {
        test("measurement nearest-rank and distribution") {
            val a=Measurement.summarize((1L..100L).toList().reversed())
            check(a.count == 100 && a.min == 1L && a.p50 == 50L && a.p90 == 90L)
            check(a.p95 == 95L && a.p99 == 99L && a.max == 100L)
            check(a.mean == 50.5 && a.sampleStdDev > 0.0)
        }
        test("measurement supports one sample") {
            val a=Measurement.summarize(listOf(7L));check(a.p99==7L && a.sampleStdDev==0.0)
        }
        test("invalid and empty measurement rejected") {
            check(runCatching { Measurement.summarize(emptyList()) }.isFailure)
            check(runCatching { Measurement.summarize(listOf(-1L)) }.isFailure)
            check(runCatching { Measurement.summarize(List(100_001) { 1L }) }.isFailure)
        }
        test("large numbers do not overflow") {
            val a=Measurement.summarize(listOf(Long.MAX_VALUE, Long.MAX_VALUE))
            check(a.max==Long.MAX_VALUE && a.sum>0.0)
        }
        test("paired benchmark insufficient is not pass") {
            val c=Measurement.compareLatency(List(3){100L}, List(3){60L},true,true)
            check(c.result=="INSUFFICIENT" && c.ratioCandidateToBaseline==null)
        }
        test("paired benchmark rejects incompatible conditions") {
            check(Measurement.compareLatency(List(20){100},List(20){1},true,false).result=="INCOMPARABLE")
        }
        test("paired benchmark records descriptive ratio") {
            val c=Measurement.compareLatency(List(20){100},List(20){50},true,true)
            check(c.result=="DESCRIPTIVE_ONLY" && c.ratioCandidateToBaseline==0.5)
        }
        test("zero baseline prevents speedup claim") {
            check(Measurement.compareLatency(List(20){0},List(20){0},true,true).result=="INDETERMINATE")
        }
        test("missing native oracle cannot pass") {
            check(ScenarioEvidence("s", "OK", "OK", false, true).verdict()==EvidenceVerdict.INCONCLUSIVE)
            check(ScenarioEvidence("s", "OK", null, true, true).verdict()==EvidenceVerdict.INCONCLUSIVE)
        }
        test("scenario pass fail not-run distinct") {
            check(ScenarioEvidence("s", "OK", "OK", true, true).verdict()==EvidenceVerdict.PASS)
            check(ScenarioEvidence("s", "OK", "NO", true, true).verdict()==EvidenceVerdict.FAIL)
            check(ScenarioEvidence("s", "OK", "OK", true, false).verdict()==EvidenceVerdict.NOT_RUN)
        }
    }
}
