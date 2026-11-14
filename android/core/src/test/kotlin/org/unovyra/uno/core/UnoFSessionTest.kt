package org.unovyra.uno.core

import kotlin.math.abs

/** C4: no partially encoded or stale owner goal can publish into the shared F state. */
object UnoFSessionTest {
    var pass = 0
        private set
    private fun verify(name: String, run: () -> Unit) {
        run()
        pass++
        println("PASS C4 $name")
    }
    private fun zero(r: Int, c: Int) = UnoRefMatrix(r, c, DoubleArray(r * c))
    private fun one(r: Int, c: Int) =
        UnoRefMatrix(r, c, DoubleArray(r * c) { if (it == 0) 1.0 else 0.0 })

    private fun weights(): UnoRefWeights {
        val d = 128
        return UnoRefWeights("C4_SYNTHETIC_DOUBLE/1",
            one(d, 1), zero(d, d), zero(d, d), zero(d, 32),
            DoubleArray(d), DoubleArray(d),
            one(128, d), one(d, 128),
            (0..1).map { (0..1).map {
                UnoRefBranch(zero(256, d), zero(256, d), zero(64, 256),
                    DoubleArray(256), DoubleArray(64))
            } }
        )
    }
    private fun near(a: DoubleArray, b: DoubleArray) =
        check(a.size == b.size && a.indices.all { abs(a[it] - b[it]) < 1e-12 })

    fun run() {
        val w = weights()
        val f = UnoFSession(w, booleanArrayOf(true, true), 1)
        val meta = DoubleArray(32)
        verify("a goal is required before an ordinary frame") {
            check(f.beginObservation() == null)
        }
        val first = f.beginGoalSwitch(1L) ?: error("first GOAL refused")
        verify("same-F GOAL uses s=0, g=0, and empty memory") {
            val direct = UnoFReference(w).forward(
                UnoRefEvent(doubleArrayOf(1.0), meta, DoubleArray(128),
                    DoubleArray(128), emptyList()), booleanArrayOf(true, true), 1)
            val computed = f.computeGoal(first, doubleArrayOf(1.0), meta)
            near(computed.state, direct.state)
            check(computed.state[0] > 0.0)
            check(f.publishGoal(first, computed))
            check(f.snapshot().goalVersion == 1L)
            check(!f.publishGoal(first, computed))
        }
        verify("normal observation can use memory without changing current goal") {
            val before = f.snapshot()
            val work = f.beginObservation() ?: error("ordinary frame refused")
            val key = DoubleArray(128); key[0] = 1.0
            val value = DoubleArray(128); value[0] = 1.0
            val withMemory = f.computeObservation(work, doubleArrayOf(0.2), meta,
                listOf(UnoRefMemoryVector(key, value)))
            val withoutMemory = f.computeObservation(work, doubleArrayOf(0.2), meta, emptyList())
            check(withMemory.state[0] > withoutMemory.state[0])
            check(f.publishObservation(work, withMemory))
            check(!f.publishObservation(work, withMemory))
            near(f.snapshot().goal, before.goal)
            check(f.snapshot().state[0] > 0)
        }
        verify("GOAL switch restores one working s and changes only g") {
            val before = f.snapshot()
            val work = f.beginGoalSwitch(2L) ?: error("goal2 refused")
            val computed = f.computeGoal(work, doubleArrayOf(-1.0), meta)
            check(f.publishGoal(work, computed))
            near(before.state, f.snapshot().state)
            near(computed.state, f.snapshot().goal)
            check(f.snapshot().goalVersion == 2L)
        }
        verify("newer owner goal invalidates an old computed goal") {
            val oldGoal = f.beginGoalSwitch(3L) ?: error("old goal refused")
            val oldOutput = f.computeGoal(oldGoal, doubleArrayOf(0.7), meta)
            val newest = f.beginGoalSwitch(4L) ?: error("new goal refused")
            check(!f.publishGoal(oldGoal, oldOutput))
            check(f.publishGoal(newest, f.computeGoal(newest, doubleArrayOf(-0.5), meta)))
            check(f.snapshot().goalVersion == 4L)
        }
        verify("in-flight observation cannot overwrite new active goal") {
            val work = f.beginObservation() ?: error("work refused")
            val computed = f.computeObservation(work, doubleArrayOf(0.3), meta, emptyList())
            val next = f.beginGoalSwitch(5L) ?: error("goal5 refused")
            check(!f.publishObservation(work, computed))
            check(f.publishGoal(next, f.computeGoal(next, doubleArrayOf(0.4), meta)))
            check(f.snapshot().goalVersion == 5L)
        }
        verify("memory revocation invalidation clears derived s/g and rejects stale frames") {
            val work = f.beginObservation() ?: error("work refused")
            val computed = f.computeObservation(work, doubleArrayOf(0.2), meta, emptyList())
            check(f.invalidateDerivedState())
            check(!f.publishObservation(work, computed))
            val state = f.snapshot()
            check(state.goalVersion == -1L && state.state.all { it == 0.0 } &&
                state.goal.all { it == 0.0 })
        }
        verify("STOP prevents new work and publishing old work") {
            val work = f.beginGoalSwitch(6L) ?: error("work refused")
            val computed = f.computeGoal(work, doubleArrayOf(0.7), meta)
            f.stop()
            check(!f.publishGoal(work, computed))
            check(f.beginGoalSwitch(7L) == null && f.beginObservation() == null)
            check(f.snapshot().stopped)
        }
    }
}
fun main() { UnoFSessionTest.run() }
