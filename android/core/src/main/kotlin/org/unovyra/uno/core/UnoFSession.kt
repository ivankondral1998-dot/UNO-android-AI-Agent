package org.unovyra.uno.core

import java.util.concurrent.atomic.AtomicBoolean

/**
 * Reference-only single-F session for UDC v0.3 GOAL transition and stale-work rejection.
 * This holds one s/g pair for ONE UnoFReference and ONE immutable Θ. It is not a second brain,
 * encoder, S6 selector, production runner, owner authentication, or Android action permission.
 * No model-generated output may modify this session without its matching work cookie.
 */
class UnoFSession(
    weights: UnoRefWeights,
    mask: BooleanArray,
    private val innerSteps: Int
) {
    private val operator = UnoFReference(weights)
    private val d = weights.d
    private val inputWidth = weights.inputWidth
    private val route = mask.copyOf()
    private val stopped = AtomicBoolean(false)

    init {
        require(route.size == weights.blocks && route.any { it } && innerSteps in 1..8) {
            "UNO_F_SESSION_ROUTE"
        }
    }

    class GoalWork internal constructor(
        val goalVersion: Long,
        internal val epoch: Long,
        internal val revision: Long
    )
    class ObservationWork internal constructor(
        val goalVersion: Long,
        internal val epoch: Long,
        internal val revision: Long,
        startState: DoubleArray,
        activeGoal: DoubleArray
    ) {
        private val startStateSnapshot = startState.copyOf()
        private val activeGoalSnapshot = activeGoal.copyOf()
        fun startState(): DoubleArray = startStateSnapshot.copyOf()
        fun goal(): DoubleArray = activeGoalSnapshot.copyOf()
    }
    data class Snapshot(val goalVersion: Long, val revision: Long,
                        val state: DoubleArray, val goal: DoubleArray, val stopped: Boolean)

    private var sessionEpoch = 0L
    private var revision = 0L
    private var activeGoalVersion = -1L
    private var pendingGoal: GoalWork? = null
    private var inFlightObservation: ObservationWork? = null
    private var state = DoubleArray(d)
    private var goal = DoubleArray(d)

    @Synchronized fun snapshot(): Snapshot =
        Snapshot(activeGoalVersion, revision, state.copyOf(), goal.copyOf(), stopped.get())

    /**
     * The trusted owner goal selector supplies strictly increasing versions.
     * A pending goal cancels in-flight observation publication; s remains untouched.
     */
    @Synchronized fun beginGoalSwitch(newGoalVersion: Long): GoalWork? {
        val minVersion = pendingGoal?.goalVersion ?: activeGoalVersion
        if (stopped.get() || revision == Long.MAX_VALUE || newGoalVersion < 0 ||
            newGoalVersion <= minVersion) return null
        val work = GoalWork(newGoalVersion, sessionEpoch, revision)
        inFlightObservation = null
        pendingGoal = work
        return work
    }

    /**
     * GOAL mode: zero temporary s/g, empty I. Same F and the same route/weights
     * as a normal observation. Canonical owner intent and mode metadata must be
     * supplied by a future separately reviewed encoder, not fabricated here.
     */
    fun computeGoal(work: GoalWork, rawCanonicalFeatures: DoubleArray,
                    goalModeMetadata: DoubleArray): UnoRefOutput {
        require(rawCanonicalFeatures.size == inputWidth && goalModeMetadata.size == 32) {
            "UNO_F_GOAL_INPUT"
        }
        require(!stopped.get()) { "UNO_F_SESSION_STOPPED" }
        return operator.forward(UnoRefEvent(
            rawCanonicalFeatures, goalModeMetadata,
            DoubleArray(d), DoubleArray(d), emptyList()
        ), route.copyOf(), innerSteps)
    }

    /** Commit is atomic with respect to other goal switches, revocation and STOP. */
    @Synchronized fun publishGoal(work: GoalWork, result: UnoRefOutput): Boolean {
        if (stopped.get() || pendingGoal !== work || work.epoch != sessionEpoch ||
            work.revision != revision || result.state.size != d ||
            result.state.any { !it.isFinite() || it !in -1.0..1.0 }) return false
        goal = result.state.copyOf()
        activeGoalVersion = work.goalVersion
        revision++
        pendingGoal = null
        // The original working s has never been replaced by GOAL computation.
        return true
    }

    @Synchronized fun discardGoal(work: GoalWork) {
        if (pendingGoal === work) pendingGoal = null
    }

    @Synchronized fun beginObservation(): ObservationWork? {
        if (stopped.get() || pendingGoal != null || inFlightObservation != null ||
            activeGoalVersion < 0 || revision == Long.MAX_VALUE) return null
        return ObservationWork(activeGoalVersion, sessionEpoch, revision, state, goal)
            .also { inFlightObservation = it }
    }

    fun computeObservation(work: ObservationWork, features: DoubleArray,
                           metadata: DoubleArray, visibleMemory: List<UnoRefMemoryVector>): UnoRefOutput {
        require(features.size == inputWidth && metadata.size == 32) {
            "UNO_F_OBSERVATION_INPUT"
        }
        require(!stopped.get()) { "UNO_F_SESSION_STOPPED" }
        return operator.forward(UnoRefEvent(
            features, metadata, work.startState(), work.goal(), visibleMemory
        ), route.copyOf(), innerSteps)
    }

    @Synchronized fun publishObservation(work: ObservationWork, result: UnoRefOutput): Boolean {
        if (stopped.get() || inFlightObservation !== work || pendingGoal != null ||
            work.epoch != sessionEpoch || work.revision != revision ||
            work.goalVersion != activeGoalVersion || revision == Long.MAX_VALUE ||
            result.state.size != d || result.state.any { !it.isFinite() || it !in -1.0..1.0 }) return false
        state = result.state.copyOf()
        revision++
        inFlightObservation = null
        return true
    }

    @Synchronized fun discardObservation(work: ObservationWork) {
        if (inFlightObservation === work) inFlightObservation = null
    }

    /**
     * Required after a trusted exact/semantic memory-scope revocation or session reset.
     * This primitive cannot itself prove durable two-store revocation or prevent a caller
     * that bypasses the gate from using a stale computed vector.
     */
    @Synchronized fun invalidateDerivedState(): Boolean {
        if (stopped.get() || revision == Long.MAX_VALUE ||
            sessionEpoch == Long.MAX_VALUE) return false
        revision++
        sessionEpoch++
        activeGoalVersion = -1L
        pendingGoal = null
        inFlightObservation = null
        state = DoubleArray(d)
        goal = DoubleArray(d)
        return true
    }

    fun stop() {
        stopped.set(true)
        synchronized(this) {
            pendingGoal = null
            inFlightObservation = null
        }
    }
}
