package org.unovyra.uno.core

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** Every positive result below is REFERENCE-ONLY, never Android-device evidence. */
object UnoFoundationReferenceCycleTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private fun input(t: Long = 1L) = Percept(PerceptType.TEXT,
        "Привет".toByteArray(), "UNTRUSTED_UI", t)
    private fun proposal() = Proposal(15, "k|v".toByteArray(), "FIXTURE", 1, "trace")
    private class MockNeural(private val action: Proposal? = null): NeuralPort {
        var calls = 0
        override fun perceive(event: Percept): NeuralOutput {
            calls++
            return NeuralOutput("FAKE_STATE", action)
        }
    }
    private class Native(private val result: NativeEndpoint = NativeEndpoint.TRUE): NativePort {
        override val trustedSourceTag = "FAKE_JVM"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return result }
        override fun readback(ticket: Ticket, nowNanos: Long) = NativeEvidence(
            ticket.id, result, calls.toLong(), nowNanos, trustedSourceTag)
    }
    private val decline = object: AuthenticatedOwnerUi {
        override fun showExactProposalAndObtainConsent(proposal: Proposal): Consent? = null
    }
    fun run() {
        val m = ExactMemory(8)
        val noWeights = UnoFoundationReferenceCycle(NoWeightsNeuralPort(), m,
            TrustController(Native(), InMemoryLedger()), decline)
        val missing = noWeights.accept(input(), 1, 100, "session", 0)
        verify(missing.status == FoundationReferenceStatus.MODEL_UNAVAILABLE &&
            missing.revision == 1L && !missing.verifiedAndroidEffect)
        verify(m.read("session", "event:1", 1, 8, 2, 0).status == ExactStatus.COMPLETE)
        verify(m.read("session", "event:1", 1, 8, 2, 0).entries.single().kind ==
            EntryKind.OBSERVED)
        verify(noWeights.accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.INVALID_EVENT)

        val neutral = MockNeural()
        val noAction = UnoFoundationReferenceCycle(neutral, ExactMemory(),
            TrustController(Native(), InMemoryLedger()), decline)
        verify(noAction.accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.NO_PROPOSAL)
        verify(neutral.calls == 1)
        verify(noAction.accept(input(2), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.INVALID_EVENT)
        verify(noAction.accept(input(2), 2, 2, "session", 0).status ==
            FoundationReferenceStatus.INVALID_EVENT)

        val declinedPort = Native()
        val denied = UnoFoundationReferenceCycle(MockNeural(proposal()), ExactMemory(),
            TrustController(declinedPort, InMemoryLedger()), decline)
        verify(denied.accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.OWNER_DECLINED)
        verify(declinedPort.calls == 0)

        val withoutPermission = Native()
        val defaultClosed = TrustController(withoutPermission, InMemoryLedger())
        val manufacturedConsent = object: AuthenticatedOwnerUi {
            override fun showExactProposalAndObtainConsent(proposal: Proposal) =
                Consent(defaultClosed.proposalDigest(proposal), "FAKE_ONLY", 90,
                    defaultClosed.epoch, defaultClosed.nonce, true)
        }
        verify(UnoFoundationReferenceCycle(MockNeural(proposal()), ExactMemory(),
            defaultClosed, manufacturedConsent).accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.TRUST_REJECTED)
        verify(withoutPermission.calls == 0)

        val fakeNative = Native()
        val fakeTrust = TrustController(fakeNative, InMemoryLedger(), mapOf(15 to "FAKE_ONLY"))
        val fakeOwner = object: AuthenticatedOwnerUi {
            override fun showExactProposalAndObtainConsent(proposal: Proposal) =
                Consent(fakeTrust.proposalDigest(proposal), "FAKE_ONLY", 90,
                    fakeTrust.epoch, fakeTrust.nonce, true)
        }
        val fakeMemory = ExactMemory()
        val positive = UnoFoundationReferenceCycle(MockNeural(proposal()), fakeMemory,
            fakeTrust, fakeOwner).accept(input(), 1, 100, "session", 0)
        verify(positive.status == FoundationReferenceStatus.REFERENCE_READBACK_CLAIM &&
            positive.nativeCalledInReference && !positive.verifiedAndroidEffect)
        verify(fakeNative.calls == 1)
        verify(fakeMemory.read("session", "event:1", 1, 2, 2, 0).entries
            .none { it.kind == EntryKind.VERIFIED_COMPLETION })

        val uncertainNative = Native(NativeEndpoint.UNKNOWN)
        val uncertainTrust = TrustController(uncertainNative, InMemoryLedger(),
            mapOf(15 to "FAKE_ONLY"))
        val uncertainOwner = object: AuthenticatedOwnerUi {
            override fun showExactProposalAndObtainConsent(proposal: Proposal) =
                Consent(uncertainTrust.proposalDigest(proposal), "FAKE_ONLY", 90,
                    uncertainTrust.epoch, uncertainTrust.nonce, true)
        }
        verify(UnoFoundationReferenceCycle(MockNeural(proposal()), ExactMemory(),
            uncertainTrust, uncertainOwner).accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.MAY_HAVE_EXECUTED)
        verify(uncertainNative.calls == 1)

        val preStopModel = MockNeural()
        val preStopped = UnoFoundationReferenceCycle(preStopModel, ExactMemory(),
            TrustController(Native(), InMemoryLedger()), decline)
        preStopped.stop()
        verify(preStopped.accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.STOPPED && preStopModel.calls == 0)

        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val slowModel = object: NeuralPort {
            override fun perceive(event: Percept): NeuralOutput {
                entered.countDown()
                release.await(3, TimeUnit.SECONDS)
                return NeuralOutput("FAKE_STATE", proposal())
            }
        }
        val concurrent = UnoFoundationReferenceCycle(slowModel, ExactMemory(),
            TrustController(Native(), InMemoryLedger()), decline)
        var completed: FoundationReferenceStatus? = null
        val thread = Thread { completed = concurrent.accept(input(), 1, 100, "session", 0).status }
        thread.start()
        verify(entered.await(2, TimeUnit.SECONDS))
        verify(concurrent.accept(input(2), 2, 100, "session", 0).status ==
            FoundationReferenceStatus.BUSY)
        concurrent.stop()
        release.countDown()
        thread.join(3000)
        verify(!thread.isAlive && completed == FoundationReferenceStatus.STOPPED)

        val tiny = UnoFoundationReferenceCycle(MockNeural(), ExactMemory(1),
            TrustController(Native(), InMemoryLedger()), decline)
        verify(tiny.accept(input(), 1, 100, "session", 0).status ==
            FoundationReferenceStatus.NO_PROPOSAL)
        verify(tiny.accept(input(2), 2, 100, "session", 0).status ==
            FoundationReferenceStatus.MEMORY_UNAVAILABLE)
        val shared = ExactMemory()
        val first = UnoFoundationReferenceCycle(MockNeural(), shared,
            TrustController(Native(), InMemoryLedger()), decline)
        verify(first.accept(input(10), 10, 100, "session", 0).status ==
            FoundationReferenceStatus.NO_PROPOSAL)
        val reopened = UnoFoundationReferenceCycle(MockNeural(), shared,
            TrustController(Native(), InMemoryLedger()), decline)
        verify(reopened.accept(input(10), 10, 100, "session", 0).status ==
            FoundationReferenceStatus.INVALID_EVENT)
        verify(reopened.accept(input(11), 11, 100, "session", 0).status ==
            FoundationReferenceStatus.NO_PROPOSAL)
        val quiet = ExactMemory()
        val before = quiet.generation
        val noAudio = UnoFoundationReferenceCycle(NoWeightsNeuralPort(), quiet,
            TrustController(Native(), InMemoryLedger()), decline)
        verify(noAudio.accept(Percept(PerceptType.AUDIO, byteArrayOf(1, 2), "MIC", 20),
            20, 100, "session", 0).status == FoundationReferenceStatus.AUDIO_REJECTED)
        verify(quiet.generation == before)
        val gate = PcmFrameGate(4)
        val heard = UnoFoundationReferenceCycle(NoWeightsNeuralPort(), quiet,
            TrustController(Native(), InMemoryLedger()), decline, audio = gate)
        verify(heard.accept(Percept(PerceptType.AUDIO, byteArrayOf(1, 2), "MIC", 21),
            21, 100, "session", 0).status == FoundationReferenceStatus.MODEL_UNAVAILABLE)
        verify(quiet.generation > before)
        gate.stop()
        verify(heard.accept(Percept(PerceptType.AUDIO, byteArrayOf(1, 2), "MIC", 22),
            22, 100, "session", 0).status == FoundationReferenceStatus.AUDIO_REJECTED)
        println("UNO_FOUNDATION_REFERENCE_CYCLE_HOST_PASS=$pass")
    }
}
