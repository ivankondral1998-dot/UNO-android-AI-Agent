package org.unovyra.uno.core

/**
 * One organism, two stores. A summary never replaces the exact record.
 * Revocation removes the summary first, then the fact.
 */
class UnoMemoryPorts(
    val exact: UnoExactMemoryPort,
    val semantic: UnoSemanticMemory
) {
    // Process-local fail-closed barrier. Not a cross-store transaction or anti-rollback proof.
    private val blockedScopes = mutableSetOf<String>()

    private fun blocked(scope: String): Boolean =
        scope in blockedScopes || semantic.isScopeRevoked(scope)

    @Synchronized fun linkSummary(entry: ExactEntry, vector: DoubleArray) {
        require(!blocked(entry.scope)) { "UNO_SCOPE_REVOKING_OR_REVOKED" }
        semantic.link(entry, vector)
    }

    @Synchronized fun recallExact(scope: String, factKey: String, k: Int, scanBudget: Int,
                                   now: Long, consentEpoch: Long): ExactRead {
        if (blocked(scope)) return ExactRead(ExactStatus.DENIED, emptyList(), 0)
        return exact.read(scope, factKey, k, scanBudget, now, consentEpoch)
    }

    @Synchronized fun recallSummary(scope: String, query: DoubleArray, k: Int,
                                     scanBudget: Int): SemanticRead {
        if (blocked(scope)) return SemanticRead(SemanticStatus.DENIED, emptyList(), 0)
        return semantic.retrieve(scope, query, k, scanBudget)
    }

    /**
     * Revoke summary first and persist its tombstone before revoking exact bytes.
     * If exact persistence then fails, this gateway still denies BOTH reads in-process
     * and after reopening a valid persisted semantic snapshot. Caller must keep the
     * failure visible and retry only this idempotent revoke, never an Android action.
     *
     * A crash before the semantic tombstone is durable cannot prove a revoke.
     * Bypassing this gateway or rolling back storage also defeats this narrow barrier.
     */
    @Synchronized fun revoke(scope: String) {
        require(scope.isNotBlank())
        blockedScopes.add(scope)
        semantic.dropScope(scope)
        exact.revoke(scope)
    }
}
