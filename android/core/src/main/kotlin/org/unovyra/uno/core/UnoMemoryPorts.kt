package org.unovyra.uno.core

/** Exact tombstone is the logical authority. Index cleanup is a separate outcome. */
enum class S4Revocation { REVOKED_CLEAN, REVOKED_CLEANUP_PENDING }

/** Host reference. All authoritative reads use the exact store before the index.
 * Lock order exact -> semantic; callbacks must be pure and must not mutate stores.
 * This does not authorize Android actions or prove later session-state publication atomic.
 */
class UnoMemoryPorts(
    val exact: UnoExactMemoryPort,
    private val semantic: UnoSemanticMemory?
) {
    fun linkSummary(entry: ExactEntry, vector: DoubleArray, access: S4Access) =
        exact.withS4Authority(access) { authority ->
            require(S4RecordRef(entry.id, entry.generation, entry.sha256, entry.scope) in authority.live) {
                "S4_LINK_NOT_LIVE"
            }
            checkNotNull(semantic) { "S4_INDEX_UNAVAILABLE" }.link(entry, vector)
        }

    fun recallExact(scope: String, factKey: String, k: Int, scanBudget: Int, now: Long, consentEpoch: Long) =
        exact.read(scope, factKey, k, scanBudget, now, consentEpoch)

    /** Budget in row visits, across BOTH catalogues. No teacher ID participates. */
    fun <T> withS4Bank(access: S4Access, width: Int, use: (S4Catalogue) -> T): T =
        withS4BankMetered(access, width, {}, use)

    /** Charge completed catalogue scans as soon as their view is available,
     * even if subsequent authority validation rejects the cycle. No refund.
     * A backend failing before it reports a view is covered by reservation,
     * not claimed as observed work. */
    internal fun <T> withS4BankMetered(access: S4Access, width: Int,
        onScan: (Int) -> Unit, use: (S4Catalogue) -> T): T =
        exact.withS4Authority(access) { authority ->
            onScan(authority.scannedRows)
            if (authority.status != S4Status.COMPLETE && authority.status != S4Status.EMPTY)
                use(S4Catalogue(authority.status, emptyList(), authority.scannedRows))
            else if (semantic == null) use(S4Catalogue(S4Status.UNKNOWN, emptyList(), authority.scannedRows,
                reason = S4Reason.INDEX_UNAVAILABLE))
            else synchronized(semantic) {
                val raw = semantic.eligibleForS4(access.scope, access.scanBudget - authority.scannedRows)
                onScan(raw.scannedRows)
                val scanned = authority.scannedRows + raw.scannedRows
                if (raw.status != S4Status.COMPLETE && raw.status != S4Status.EMPTY)
                    use(S4Catalogue(raw.status, emptyList(), scanned, reason = raw.reason))
                else {
                    val hits = raw.hits.filter { S4RecordRef(it.exactId, it.generation, it.sha256, it.scope) in authority.live }
                    // A non-live link cannot be treated as evidence. Reject the entire stale view.
                    val status = when {
                        hits.size != raw.hits.size -> S4Status.UNKNOWN
                        hits.any { it.vector.size != width || it.vector.any { v -> v !in -1.0..1.0 } } -> S4Status.INCOMPATIBLE
                        hits.isEmpty() -> S4Status.EMPTY
                        else -> S4Status.COMPLETE
                    }
                    val revision = semantic.generation
                    val output = use(S4Catalogue(status, if (status == S4Status.COMPLETE) hits else emptyList(), scanned,
                        authority.generation, revision, authority.validUntilNanos,
                        if (hits.size != raw.hits.size) S4Reason.STALE_LINK else when (status) {
                            S4Status.INCOMPATIBLE -> S4Reason.INCOMPATIBLE_VECTOR
                            else -> S4Reason.NONE
                        }))
                    check(semantic.generation == revision) { "S4_INDEX_STALE" }
                    output
                }
            }
        }

    /** Version-only snapshot: GOAL mode may inspect versions, never memory content.
     * Existing lock order is exact -> semantic. Callers must use a trusted store instance. */
    internal inline fun <T> withVersions(use: (Long, Long) -> T): T = synchronized(exact) {
        synchronized(checkNotNull(semantic)) { use(exact.generation, semantic.generation) }
    }

    fun recallSummary(access: S4Access, query: DoubleArray, k: Int): SemanticRead =
        withS4Bank(access, query.size) { bank ->
            val result = when (bank.status) {
                S4Status.DENIED -> SemanticRead(SemanticStatus.DENIED, emptyList(), 0)
                S4Status.COMPLETE -> summarizeS4Catalogue(bank.hits, query, k)
                else -> SemanticRead(SemanticStatus.UNKNOWN, emptyList(), 0)
            }
            result.copy(catalogueStatus = bank.status, catalogueReason = bank.reason)
        }

    fun revoke(scope: String): S4Revocation {
        exact.revoke(scope) // durable tombstone first; failure here must not claim revocation
        return try {
            checkNotNull(semantic) { "S4_INDEX_UNAVAILABLE" }.dropScope(scope)
            S4Revocation.REVOKED_CLEAN
        } catch (_: Exception) {
            S4Revocation.REVOKED_CLEANUP_PENDING
        }
    }
}
