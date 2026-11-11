package org.unovyra.uno.core

/**
 * One organism, two stores. A summary never replaces the exact record.
 * Revocation removes the summary first, then the fact.
 */
class UnoMemoryPorts(
    val exact: UnoExactMemoryPort,
    val semantic: UnoSemanticMemory
) {
    fun linkSummary(entry: ExactEntry, vector: DoubleArray) = semantic.link(entry, vector)

    fun recallExact(scope: String, factKey: String, k: Int, scanBudget: Int, now: Long, consentEpoch: Long) =
        exact.read(scope, factKey, k, scanBudget, now, consentEpoch)

    fun recallSummary(scope: String, query: DoubleArray, k: Int, scanBudget: Int) =
        semantic.retrieve(scope, query, k, scanBudget)

    fun revoke(scope: String) {
        semantic.dropScope(scope)
        exact.revoke(scope)
    }
}
