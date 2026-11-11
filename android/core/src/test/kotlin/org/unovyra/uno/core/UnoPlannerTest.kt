package org.unovyra.uno.core

import java.security.MessageDigest

object UnoPlannerTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private fun proposal(verb: Int = 15) = Proposal(verb, "k|v".toByteArray(), "FIXTURE", 1, "trace")
    private class CountingOwner : AuthenticatedOwnerUi {
        var calls = 0
        override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? {
            calls++
            return null
        }
    }
    private class Proposing : NeuralPort {
        override fun perceive(event: Percept) = NeuralOutput("FAKE_STATE", proposal())
    }
    private class Native : NativePort {
        override val trustedSourceTag = "FAKE_JVM"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return NativeEndpoint.TRUE }
        override fun readback(ticket: Ticket, nowNanos: Long) = NativeEvidence(
            ticket.id, NativeEndpoint.TRUE, 1L, nowNanos, trustedSourceTag)
    }

    fun run() {
        val planner = BoundedPlanner(2)
        val parent = proposal()
        val same = PlanStep(15, "k|v".toByteArray(), "none")
        verify(planner.decompose(parent, listOf(same, same), "none").status == PlanStatus.HELD)
        verify(planner.decompose(parent, listOf(same, same, same), "none").status == PlanStatus.REJECTED)
        verify(planner.decompose(parent, listOf(PlanStep(16, "k|v".toByteArray(), "none")), "none")
            .status == PlanStatus.REJECTED)
        verify(planner.decompose(parent, listOf(PlanStep(15, "other".toByteArray(), "none")), "none")
            .status == PlanStatus.REJECTED)
        verify(planner.decompose(parent, listOf(PlanStep(15, "k|v".toByteArray(), "other")), "none")
            .status == PlanStatus.REJECTED)
        planner.stop()
        verify(planner.bound(parent).status == PlanStatus.STOPPED)
        val budget = BoundedPlanner(2)
        val opened = budget.decompose(parent, listOf(same, same), "none")
        verify(opened.status == PlanStatus.HELD && budget.remaining() == 2)
        verify(budget.bound(parent).status == PlanStatus.REJECTED && budget.remaining() == 2)
        verify(budget.take().steps.single().verb == 15)
        verify(budget.take().status == PlanStatus.HELD)
        verify(budget.take().status == PlanStatus.EXHAUSTED && budget.remaining() == 0)
        val marked = PlanStep(15, "k|v".toByteArray(), "none", reversible = true)
        verify(BoundedPlanner(2).decompose(parent, listOf(marked), "none").status ==
            PlanStatus.REJECTED)
        verify(BoundedPlanner(2).decompose(parent, listOf(marked), "none", setOf("none"))
            .status == PlanStatus.HELD)
        val fresh = BoundedPlanner()
        fresh.bound(parent)
        verify(fresh.restore(wasStopped = false).status == PlanStatus.EXHAUSTED)
        verify(fresh.take().status == PlanStatus.EXHAUSTED)
        verify(fresh.restore(wasStopped = true).status == PlanStatus.STOPPED)
        verify(fresh.bound(parent).status == PlanStatus.STOPPED)

        val memory = ExactMemory()
        val before = memory.generation
        val owner = CountingOwner()
        val native = Native()
        val held = BoundedPlanner()
        val cycle = UnoFoundationReferenceCycle(Proposing(), memory,
            TrustController(native, InMemoryLedger()), owner, planner = held)
        verify(cycle.accept(Percept(PerceptType.IMAGE, byteArrayOf(1), "CAMERA", 1),
            1, 100, "session", 0).status == FoundationReferenceStatus.IMAGE_REJECTED)
        verify(memory.generation == before && owner.calls == 0 && native.calls == 0)
        val stoppedPlan = BoundedPlanner()
        stoppedPlan.stop()
        val stoppedCycle = UnoFoundationReferenceCycle(Proposing(), memory,
            TrustController(native, InMemoryLedger()), owner, planner = stoppedPlan)
        verify(stoppedCycle.accept(Percept(PerceptType.TEXT, "a".toByteArray(), "UI", 2),
            2, 100, "session", 0).status == FoundationReferenceStatus.STOPPED)
        verify(owner.calls == 0 && native.calls == 0 && memory.generation > before)

        val slot = WeightSlot()
        val bytes = byteArrayOf(9, 9)
        val digest = MessageDigest.getInstance("SHA-256").digest(bytes)
            .joinToString("") { "%02x".format(it) }
        val manifest = WeightManifest("SYNTHETIC/1", 1, 1, 1, bytes.size.toLong(), digest)
        val checked = WeightCheckedNeural(slot)
        verify(runCatching { checked.perceive(Percept(PerceptType.TEXT, byteArrayOf(1), "UI", 3)) }
            .isFailure)
        verify(slot.offer(manifest, byteArrayOf(1), "SYNTHETIC/1") == WeightAdmission.REJECTED)
        verify(!slot.admitted())
        verify(slot.offer(manifest, bytes, "SYNTHETIC/1") ==
            WeightAdmission.ADMITTED_UNVERIFIED_QUALITY)
        verify(runCatching { checked.perceive(Percept(PerceptType.TEXT, byteArrayOf(1), "UI", 4)) }
            .isFailure)
        val admittedCycle = UnoFoundationReferenceCycle(checked, ExactMemory(),
            TrustController(native, InMemoryLedger()), owner)
        verify(admittedCycle.accept(Percept(PerceptType.TEXT, "b".toByteArray(), "UI", 5),
            5, 100, "session", 0).status == FoundationReferenceStatus.MODEL_UNAVAILABLE)
        verify(native.calls == 0)
        println("UNO_PLANNER_HOST_PASS=$pass")
    }
}
