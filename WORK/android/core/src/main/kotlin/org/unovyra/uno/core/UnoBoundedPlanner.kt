package org.unovyra.uno.core

import java.util.ArrayDeque
import java.util.concurrent.atomic.AtomicBoolean

enum class PlanStatus { HELD, REJECTED, STOPPED, EXHAUSTED }

/** One step inside a plan. It is not permission to act. */
data class PlanStep(
    val verb: Int,
    val canonicalArgs: ByteArray,
    val effectName: String,
    val reversible: Boolean = false
)

data class BoundedPlan(val status: PlanStatus, val steps: List<PlanStep>)

/**
 * Holds only steps that repeat the parent proposal.
 * A different verb, different bytes, or a longer list is rejected.
 * A taken step is spent. Restoring a plan never issues it again.
 * This planner does not invent a goal and does not call Android.
 */
class BoundedPlanner(private val maxSteps: Int = 4) {
    private val stopped = AtomicBoolean(false)
    private val queue = ArrayDeque<PlanStep>()
    fun stop() {
        stopped.set(true)
        queue.clear()
    }
    fun isStopped() = stopped.get()
    fun remaining() = queue.size

    fun bound(proposal: Proposal): BoundedPlan {
        if (stopped.get()) return BoundedPlan(PlanStatus.STOPPED, emptyList())
        if (queue.isNotEmpty() || maxSteps < 1) return BoundedPlan(PlanStatus.REJECTED, emptyList())
        val step = PlanStep(proposal.verb, proposal.canonicalArgs.copyOf(), "", false)
        queue.add(step)
        return BoundedPlan(PlanStatus.HELD, listOf(step))
    }

    fun decompose(
        proposal: Proposal,
        steps: List<PlanStep>,
        effectName: String,
        reversibleEffects: Set<String> = emptySet()
    ): BoundedPlan {
        if (stopped.get()) return BoundedPlan(PlanStatus.STOPPED, emptyList())
        if (queue.isNotEmpty() || effectName.isBlank() || steps.isEmpty() || steps.size > maxSteps) {
            return BoundedPlan(PlanStatus.REJECTED, emptyList())
        }
        val parent = proposal.canonicalArgs
        val same = steps.all { step ->
            step.verb == proposal.verb &&
                step.effectName == effectName &&
                step.canonicalArgs.contentEquals(parent) &&
                (!step.reversible || effectName in reversibleEffects)
        }
        if (!same) return BoundedPlan(PlanStatus.REJECTED, emptyList())
        val held = steps.map {
            PlanStep(it.verb, it.canonicalArgs.copyOf(), it.effectName, it.reversible)
        }
        queue.addAll(held)
        return BoundedPlan(PlanStatus.HELD, held)
    }

    /** One spent step. Empty or restored plans do not yield another. */
    fun take(): BoundedPlan {
        if (stopped.get()) {
            queue.clear()
            return BoundedPlan(PlanStatus.STOPPED, emptyList())
        }
        val step = queue.poll() ?: return BoundedPlan(PlanStatus.EXHAUSTED, emptyList())
        return BoundedPlan(PlanStatus.HELD, listOf(step))
    }

    /** Recovery keeps the stop bit and drops every unspent step. */
    fun restore(wasStopped: Boolean): BoundedPlan {
        queue.clear()
        if (wasStopped) {
            stopped.set(true)
            return BoundedPlan(PlanStatus.STOPPED, emptyList())
        }
        return BoundedPlan(PlanStatus.EXHAUSTED, emptyList())
    }
}
