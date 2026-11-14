package org.unovyra.uno.core

enum class ModelProposalForm { NONE, TYPED, MISSING, AMBIGUOUS, MALFORMED }

data class ModelProposalParse(val form: ModelProposalForm, val proposal: Proposal?)

/**
 * Reads one untrusted text line. A parsed proposal is not consent and not an Android call.
 * Facts that are not in the supplied map are reported absent and are not filled in.
 */
object UnoModelProposal {
    private val typed = Regex("verb=([0-9]{1,3}) effect=([a-z0-9._-]{1,32}) args=([A-Za-z0-9._-]{1,64})")

    fun factLines(known: Map<String, String>, keys: List<String>): List<String> =
        keys.map { key ->
            val value = known[key]
            if (value == null) "FACT $key ABSENT" else "FACT $key = $value"
        }

    fun parse(text: String): ModelProposalParse {
        val lines = text.replace("\r\n", "\n").lines().map { it.trim() }.filter { it.startsWith("PROPOSAL:") }
        if (lines.isEmpty()) return ModelProposalParse(ModelProposalForm.MISSING, null)
        if (lines.size != 1) return ModelProposalParse(ModelProposalForm.AMBIGUOUS, null)
        val body = lines[0].removePrefix("PROPOSAL:").trim()
        if (body == "NONE") return ModelProposalParse(ModelProposalForm.NONE, null)
        val match = typed.matchEntire(body) ?: return ModelProposalParse(ModelProposalForm.MALFORMED, null)
        val verb = match.groupValues[1].toInt()
        if (verb !in 3..23 || match.groupValues[2] != "none") {
            return ModelProposalParse(ModelProposalForm.MALFORMED, null)
        }
        val proposal = Proposal(
            verb,
            match.groupValues[3].toByteArray(Charsets.UTF_8),
            "UNVERIFIED_TEXT",
            0L,
            "TEXT_NOT_F"
        )
        return ModelProposalParse(ModelProposalForm.TYPED, proposal)
    }
}
