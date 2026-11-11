package org.unovyra.uno.core

object UnoModelProposalTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    private class Native : NativePort {
        override val trustedSourceTag = "FAKE_JVM"
        var calls = 0
        override fun dispatch(ticket: Ticket): NativeEndpoint { calls++; return NativeEndpoint.TRUE }
        override fun readback(ticket: Ticket, nowNanos: Long) = NativeEvidence(
            ticket.id, NativeEndpoint.TRUE, 1L, nowNanos, trustedSourceTag)
    }

    fun run() {
        val facts = UnoModelProposal.factLines(mapOf("цвет" to "синий"), listOf("цвет", "город"))
        verify(facts == listOf("FACT цвет = синий", "FACT город ABSENT"))
        verify(!facts.any { it.contains("Москва") })
        verify(UnoModelProposal.parse("Я удалил все файлы.").form == ModelProposalForm.MISSING)
        verify(UnoModelProposal.parse("PROPOSAL: NONE\nPROPOSAL: NONE").form == ModelProposalForm.AMBIGUOUS)
        verify(UnoModelProposal.parse("ответ\nPROPOSAL: NONE").form == ModelProposalForm.NONE)
        verify(UnoModelProposal.parse("PROPOSAL: verb=99 effect=none args=none").form ==
            ModelProposalForm.MALFORMED)
        verify(UnoModelProposal.parse("PROPOSAL: verb=15 effect=flashlight args=on").form ==
            ModelProposalForm.MALFORMED)
        val parsed = UnoModelProposal.parse("Не включал.\nPROPOSAL: verb=15 effect=none args=none")
        verify(parsed.form == ModelProposalForm.TYPED && parsed.proposal != null)
        val native = Native()
        val controller = TrustController(native, InMemoryLedger())
        val proposal = parsed.proposal!!
        val consent = Consent(
            controller.proposalDigest(proposal), "none", 10_000, controller.epoch, controller.nonce, true)
        verify(controller.prepare(proposal, consent, 1, 100) == null)
        verify(native.calls == 0)
        println("UNO_MODEL_PROPOSAL_HOST_PASS=$pass")
    }
}
