package org.unovyra.uno.core

import java.util.concurrent.atomic.AtomicBoolean

enum class PlanStatus { HELD, REJECTED, STOPPED }

/** One step inside a plan. It is not permission to act. */
data class PlanStep(val verb: Int, val canonicalArgs: ByteArray, val effectName: String)

data class BoundedPlan(val status: PlanStatus, val steps: List<PlanStep>)

/**
 * Holds only steps that repeat the parent proposal.
 * A different verb, different bytes, or a longer list is rejected.
 * This planner does not invent a goal and does not call Android.
 */
class BoundedPlanner(private val maxSteps: Int = 4) {
    private val stopped = AtomicBoolean(false)
    fun stop() { stopped.set(true) }
    fun isStopped() = stopped.get()

    fun bound(proposal: Proposal): BoundedPlan {
        if (stopped.get()) return BoundedPlan(PlanStatus.STOPPED, emptyList())
        if (maxSteps < 1) return BoundedPlan(PlanStatus.REJECTED, emptyList())
        return BoundedPlan(PlanStatus.HELD, listOf(
            PlanStep(proposal.verb, proposal.canonicalArgs.copyOf(), "")
        ))
    }

    fun decompose(proposal: Proposal, steps: List<PlanStep>, effectName: String): BoundedPlan {
        if (stopped.get()) return BoundedPlan(PlanStatus.STOPPED, emptyList())
        if (effectName.isBlank() || steps.isEmpty() || steps.size > maxSteps) {
            return BoundedPlan(PlanStatus.REJECTED, emptyList())
        }
        val parent = proposal.canonicalArgs
        val same = steps.all { step ->
            step.verb == proposal.verb &&
                step.effectName == effectName &&
                step.canonicalArgs.contentEquals(parent)
        }
        if (!same) return BoundedPlan(PlanStatus.REJECTED, emptyList())
        return BoundedPlan(PlanStatus.HELD, steps.map {
            PlanStep(it.verb, it.canonicalArgs.copyOf(), it.effectName)
        })
    }
}
