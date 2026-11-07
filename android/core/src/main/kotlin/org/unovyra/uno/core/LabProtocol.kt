package org.unovyra.uno.core

import java.security.MessageDigest
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicLong
import kotlin.math.min

/** Test environment, not agent intelligence. All limits are hard-coded safety ceilings, not product thresholds. */
enum class LabProfile(val maxDurationMs: Long, val maxHeapMiB: Int, val parallelism: Int) {
    QUICK(12_000L, 8, 1),
    STRESS(60_000L, 64, 2)
}

enum class LabStatus { PASS, FAIL, ABORTED, UNSUPPORTED, INCONCLUSIVE }

data class LabResult(val name: String, val status: LabStatus, val durationNanos: Long,
                     val details: Map<String, String>)

/** A STOP is a one-way latch. A cancelled lab run cannot restart itself. */
class LabStop {
    private val cancelled = java.util.concurrent.atomic.AtomicBoolean(false)
    fun stop() { cancelled.set(true) }
    fun isStopped(): Boolean = cancelled.get()
}

object LabWorkloads {
    /** Deterministic CPU oracle. Values are deliberately tiny to avoid saturation and overflow. */
    fun cpu(rounds: Int, width: Int, cancelled: () -> Boolean, clock: () -> Long = System::nanoTime): LabResult {
        require(rounds in 1..64 && width in 8..128)
        val a = FloatArray(width * width) { ((it * 13) % 53 - 26) * 0.001f }
        val b = FloatArray(width * width) { ((it * 17) % 47 - 23) * 0.001f }
        val c = FloatArray(width * width)
        val times = ArrayList<Long>(rounds)
        var checksum = 0.0
        val begin = clock()
        for (r in 0 until rounds) {
            if (cancelled()) return LabResult("CPU_FP32", LabStatus.ABORTED, (clock()-begin).coerceAtLeast(0),
                mapOf("rounds_completed" to times.size.toString()))
            val start = clock()
            for (i in 0 until width) for (j in 0 until width) {
                var sum = 0.0f
                for (k in 0 until width) sum += a[i*width+k] * b[k*width+j]
                c[i*width+j] = sum
            }
            times.add((clock() - start).coerceAtLeast(0))
            checksum += c[(r*97) % c.size].toDouble()
        }
        val stats = Measurement.summarize(times)
        return LabResult("CPU_FP32", LabStatus.PASS, (clock()-begin).coerceAtLeast(0),
            mapOf("width" to width.toString(), "rounds" to rounds.toString(),
                "mac_per_round" to (width.toLong()*width*width).toString(),
                "p50_ns" to stats.p50.toString(), "p95_ns" to stats.p95.toString(),
                "p99_ns" to stats.p99.toString(), "mean_ns" to stats.mean.toString(),
                "checksum" to checksum.toString(),
                "limitations" to "naive FP32 CPU only; NOT neural accuracy, Joules, or NN throughput"))
    }

    /** Sustained CPU workload with explicit end time, bounded individual batches and cancellation. */
    fun sustainedCpu(durationMs: Long, width:Int, cancelled:()->Boolean,
                     clock:()->Long = System::nanoTime): LabResult {
        require(durationMs in 10L..40_000L && width in 8..128)
        val start=clock()
        val iterations=ArrayList<Long>()
        var batches=0
        var fingerprint=0.0
        val requested=durationMs*1_000_000L
        while ((clock()-start).coerceAtLeast(0)<requested && batches<10_000) {
            if(cancelled()) return LabResult("CPU_SUSTAINED",LabStatus.ABORTED,(clock()-start).coerceAtLeast(0),
                mapOf("batches" to batches.toString()))
            val r=cpu(2,width,cancelled,clock)
            if(r.status!=LabStatus.PASS) return LabResult("CPU_SUSTAINED",r.status,(clock()-start).coerceAtLeast(0),
                mapOf("batches" to batches.toString()))
            iterations.add(r.durationNanos)
            fingerprint+=(r.details["checksum"]?.toDoubleOrNull() ?: 0.0)
            batches++
        }
        val stats=Measurement.summarize(iterations)
        return LabResult("CPU_SUSTAINED",LabStatus.PASS,(clock()-start).coerceAtLeast(0),
            mapOf("batches" to batches.toString(),"matrix_width" to width.toString(),
                "p50_batch_ns" to stats.p50.toString(),"p95_batch_ns" to stats.p95.toString(),
                "p99_batch_ns" to stats.p99.toString(),"checksum" to fingerprint.toString(),
                "interpretation" to "sustained compute only; thermal and energy from separate OS snapshots"))
    }

    /** Observes concurrent kernel contention. Not a speedup claim without matched baseline. */
    fun parallelCpu(threads:Int, width:Int, cancelled:()->Boolean,
                    clock:()->Long=System::nanoTime): LabResult {
        require(threads in 1..3 && width in 8..96)
        val start=clock()
        val begins=CountDownLatch(1)
        val ends=CountDownLatch(threads)
        val counters=java.util.concurrent.atomic.AtomicIntegerArray(threads)
        val tasks=(0 until threads).map { i ->
            Thread {
                try {
                    begins.await(2,TimeUnit.SECONDS)
                    val r=cpu(8,width,cancelled,clock)
                    counters.set(i,if(r.status==LabStatus.PASS) 1 else -1)
                } catch (_:InterruptedException) { counters.set(i,-1) }
                finally { ends.countDown() }
            }.apply { isDaemon=true;start() }
        }
        begins.countDown()
        val finished=ends.await(6,TimeUnit.SECONDS)
        if(!finished)tasks.forEach(Thread::interrupt)
        val passed=(0 until threads).count{counters.get(it)==1}
        val status=when {
            cancelled()->LabStatus.ABORTED
            !finished->LabStatus.INCONCLUSIVE
            passed==threads->LabStatus.PASS
            else->LabStatus.FAIL
        }
        return LabResult("CPU_PARALLEL",status,(clock()-start).coerceAtLeast(0),
            mapOf("threads" to threads.toString(),"completed" to passed.toString(),
                "note" to "own threads only; not CPU affinity or global scheduler proof"))
    }

    /** Allocations stay below both configured and currently available Java heap. No deliberate OOM. */
    fun heap(chunksMiB: Int, cancelled: () -> Boolean, clock: () -> Long = System::nanoTime): LabResult {
        require(chunksMiB in 1..64)
        val rt = Runtime.getRuntime()
        val unused = rt.maxMemory() - (rt.totalMemory() - rt.freeMemory())
        val maximum = min(chunksMiB.toLong(), ((unused - 32L*1024*1024).coerceAtLeast(0) / (1024*1024))).toInt()
        val start = clock()
        if (maximum < 1) return LabResult("HEAP_PRESSURE", LabStatus.UNSUPPORTED, 0,
            mapOf("reason" to "insufficient Java heap reserve"))
        val holding = ArrayList<ByteArray>(maximum)
        var checksum = 0L
        try {
            repeat(maximum) { idx ->
                if (cancelled()) return LabResult("HEAP_PRESSURE", LabStatus.ABORTED,
                    (clock()-start).coerceAtLeast(0), mapOf("chunks_allocated" to holding.size.toString()))
                val bytes = ByteArray(1024*1024)
                // Touch each page to measure real committed allocations, but only own app memory.
                for (offset in bytes.indices step 4096) bytes[offset] = (idx+offset).toByte()
                checksum += bytes.sumOf { it.toLong() }
                holding.add(bytes)
            }
            return LabResult("HEAP_PRESSURE", LabStatus.PASS, (clock()-start).coerceAtLeast(0),
                mapOf("allocated_mib" to holding.size.toString(), "checksum" to checksum.toString(),
                    "note" to "bounded own-process heap allocation; no global memory pressure attempt"))
        } finally { holding.clear() }
    }

    /** Checksum of deterministic buffer; its altered copy MUST be detected as corruption. */
    fun integrity(bytes: Int, cancelled: () -> Boolean, clock: () -> Long = System::nanoTime): LabResult {
        require(bytes in 16..2_097_152)
        val start = clock()
        if (cancelled()) return LabResult("INTEGRITY",LabStatus.ABORTED,0,emptyMap())
        val payload = ByteArray(bytes) { ((it*31+7) xor (it ushr 2)).toByte() }
        val digest = MessageDigest.getInstance("SHA-256")
        val original = digest.digest(payload)
        val changed = payload.copyOf()
        changed[bytes/2] = (changed[bytes/2].toInt() xor 1).toByte()
        val detects = !original.contentEquals(digest.digest(changed))
        return LabResult("INTEGRITY",if(detects) LabStatus.PASS else LabStatus.FAIL,
            (clock()-start).coerceAtLeast(0),mapOf("bytes" to bytes.toString(),
                "corruption_detected" to detects.toString(),
                "note" to "in-memory corruption test, not Android filesystem durability"))
    }

    /** Stress queue capacity, STOP priority, and threads without submitting OS operations. */
    fun scheduler(concurrent: Int, perThread: Int, cancelled: () -> Boolean,
                  clock: () -> Long = System::nanoTime): LabResult {
        require(concurrent in 1..4 && perThread in 1..10_000)
        val queue = BoundedScheduler(64)
        val accepted = AtomicInteger()
        val rejected = AtomicInteger()
        val completed = CountDownLatch(concurrent)
        val start = clock()
        val workers = (0 until concurrent).map {
            Thread {
                try {
                    repeat(perThread) {
                        if (cancelled()) return@Thread
                        if (queue.enqueue(Priority.OWNER,"local-synthetic", Long.MAX_VALUE)) accepted.incrementAndGet()
                        else rejected.incrementAndGet()
                    }
                } finally { completed.countDown() }
            }.apply { isDaemon=true; start() }
        }
        val joined = completed.await(4,TimeUnit.SECONDS)
        if (!joined) { queue.stop();workers.forEach(Thread::interrupt) }
        val acceptedCount = accepted.get()
        val bounded = acceptedCount <= 64 && queue.size() <= 64
        val stop = queue.enqueue(Priority.STOP, "STOP", 0)
        val noAfterStop = !queue.enqueue(Priority.OWNER,"after-stop", Long.MAX_VALUE) && queue.poll(0L)==null
        val status = when {
            cancelled() -> LabStatus.ABORTED
            !joined -> LabStatus.INCONCLUSIVE
            bounded && stop && noAfterStop -> LabStatus.PASS
            else -> LabStatus.FAIL
        }
        return LabResult("QUEUE_STOP", status, (clock()-start).coerceAtLeast(0),
            mapOf("threads" to concurrent.toString(), "attempts" to (concurrent*perThread).toString(),
                "accepted" to acceptedCount.toString(), "rejected" to rejected.get().toString(),
                "bounded" to bounded.toString(), "stop_preempts_queue" to noAfterStop.toString(),
                "note" to "host synthetic STOP and bounded queue; NOT Android dispatch race proof"))
    }
}
