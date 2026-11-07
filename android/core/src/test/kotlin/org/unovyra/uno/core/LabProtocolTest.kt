package org.unovyra.uno.core

object LabProtocolTest {
    var pass=0
    private fun t(label:String, action:()->Unit){action();pass++;println("PASS $label")}
    fun run(){
        t("quick cpu workload has finite metrics") {
            val r=LabWorkloads.cpu(4,8,{false})
            check(r.status==LabStatus.PASS && r.details["mac_per_round"]=="512")
            check((r.details["p95_ns"]?.toLong()?:-1)>=0)
        }
        t("cpu stress cancel before first round") {
            check(LabWorkloads.cpu(4,8,{true}).status==LabStatus.ABORTED)
        }
        t("sustained CPU respects time and produces batches") {
            val r=LabWorkloads.sustainedCpu(15,8,{false})
            check(r.status==LabStatus.PASS && r.details["batches"]!!.toInt()>=1)
        }
        t("parallel CPU run joins and records thread completion") {
            val r=LabWorkloads.parallelCpu(2,8,{false})
            check(r.status==LabStatus.PASS && r.details["completed"]=="2")
        }
        t("sustained CPU responds to stop") {
            check(LabWorkloads.sustainedCpu(20,8,{true}).status==LabStatus.ABORTED)
        }
        t("memory is capped and checksummed") {
            val r=LabWorkloads.heap(1,{false});check(r.status in setOf(LabStatus.PASS,LabStatus.UNSUPPORTED))
            if(r.status==LabStatus.PASS) check(r.details["allocated_mib"]=="1")
        }
        t("memory stress cancel is safe") {
            check(LabWorkloads.heap(1,{true}).status in setOf(LabStatus.ABORTED,LabStatus.UNSUPPORTED))
        }
        t("original payload versus altered copy") {
            check(LabWorkloads.integrity(2048,{false}).status==LabStatus.PASS)
        }
        t("integrity test cancel before mutation") {
            check(LabWorkloads.integrity(2048,{true}).status==LabStatus.ABORTED)
        }
        t("scheduler stays bounded under concurrent flood") {
            repeat(4) {
                val r=LabWorkloads.scheduler(4,500,{false})
                check(r.status==LabStatus.PASS) { r }
                check(r.details["accepted"]!!.toInt()<=64)
            }
        }
        t("stopped scheduler refuses future owner events") {
            val q=BoundedScheduler(2)
            check(q.enqueue(Priority.OWNER, "a",1));check(q.enqueue(Priority.OWNER, "b",2))
            check(q.enqueue(Priority.STOP,"c",3));check(q.poll(0L)==null)
            check(!q.enqueue(Priority.OWNER,"d",4))
        }
        t("lab stop cannot undo a stop") {
            val l=LabStop();check(!l.isStopped());l.stop();check(l.isStopped());l.stop();check(l.isStopped())
        }
        t("profiles have bounded safety ceilings") {
            check(LabProfile.QUICK.maxHeapMiB <= 8 && LabProfile.STRESS.maxHeapMiB <=64)
            check(LabProfile.STRESS.maxDurationMs <=60_000)
        }
    }
}
