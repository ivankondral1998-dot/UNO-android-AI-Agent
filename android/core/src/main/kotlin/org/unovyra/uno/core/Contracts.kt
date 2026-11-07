package org.unovyra.uno.core

/** UNO core contracts. Neural proposals are untrusted data, NEVER permissions. */
object UnoAbi {
    const val MODEL = "UNO_MODEL_ABI/2"
    const val ACTION = "UNO_ACTION_SCHEMA/2"
    const val MEMORY = "UNO_MEMORY_SCHEMA/2-CANDIDATE"
    const val MAX_QUEUE = 1024
    const val MAX_PENDING = 32
    const val MAX_MEMORY = 4096
    const val MAX_GOALS = 64
    const val MAX_TOKENS = 4096
    const val MAX_ARGUMENT_BYTES = 4096
}

enum class PerceptType { TEXT, AUDIO, IMAGE, SENSOR, OS, INTERNAL }
data class Percept(
    val type: PerceptType,
    val data: ByteArray,
    val sourceTag: String,
    val monotonicNanos: Long,
    val authenticatedSource: Boolean = false
) {
    init { require(data.size <= 16_384 && monotonicNanos >= 0) { "invalid percept size/time" } }
}

enum class NativeEndpoint { TRUE, FALSE, UNKNOWN }
enum class Phase { PREPARED, MAY_HAVE_EXECUTED, WAIT_READBACK, COMMITTED, CANCELLED, DENIED, UNKNOWN }

data class Proposal(
    val verb: Int,
    val canonicalArgs: ByteArray,
    val modelDigest: String,
    val goalId: Long,
    val traceDigest: String
) {
    init {
        require(verb in 0..127 && canonicalArgs.size <= UnoAbi.MAX_ARGUMENT_BYTES)
        require(modelDigest.isNotEmpty() && traceDigest.isNotEmpty())
    }
}

data class Consent(
    val proposalDigest: String,
    val effectName: String,
    val expiresAtNanos: Long,
    val epoch: Long,
    val nonce: String,
    val ownerUnlocked: Boolean
)

data class NativeEvidence(
    val ticketId: String,
    val endpoint: NativeEndpoint,
    val nativeGeneration: Long,
    val observedAtNanos: Long,
    val source: String
)

data class Ticket(
    val id: String,
    val proposal: Proposal,
    val proposalDigest: String,
    val epoch: Long,
    val nonce: String,
    val deadlineNanos: Long,
    val effectName: String,
    var phase: Phase,
    var used: Boolean = false,
    var readback: NativeEvidence? = null
)

/** Mandatory actual Android neural processor to be plugged in after weights export. */
interface NeuralPort {
    fun perceive(event: Percept): NeuralOutput
}
data class NeuralOutput(val stateDigest: String, val action: Proposal?)

/** Model is intentionally unavailable: no fabricated intelligence or actions. */
class NoWeightsNeuralPort : NeuralPort {
    override fun perceive(event: Percept): NeuralOutput =
        throw IllegalStateException("MODEL_NOT_TRAINED_OR_LOADED")
}

interface NativePort {
    val trustedSourceTag: String
    fun dispatch(ticket: Ticket): NativeEndpoint
    fun readback(ticket: Ticket, nowNanos: Long): NativeEvidence
}

interface AuthenticatedOwnerUi {
    /** Production must use Android profile-bound auth; never text/LLM/memory. */
    fun showExactProposalAndObtainConsent(proposal: Proposal): Consent?
}

interface DurableLedger {
    /** Must atomically store used+receipt+P-version+memory references when implemented. */
    fun prepare(ticket: Ticket): Boolean
    fun commit(ticket: Ticket, evidence: NativeEvidence): Boolean
    fun unresolved(): List<Ticket>
}
