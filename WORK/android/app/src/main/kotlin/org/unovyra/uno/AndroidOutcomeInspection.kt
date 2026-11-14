package org.unovyra.uno

import android.content.Context

/**
 * App-private, read-only recovery summary for the owner-facing diagnostic UI.
 * This does not authenticate an owner, grant permissions, replay a Ticket, verify native
 * evidence, or authorize any action. Payloads, ticket IDs and memory are never surfaced.
 */
internal object AndroidOutcomeInspection {
    enum class Status { NOT_INITIALIZED, INSPECTED, UNAVAILABLE }
    data class Summary(
        val status: Status,
        val total: Int = 0,
        val prepared: Int = 0,
        val mayHaveExecuted: Int = 0,
        val storedReadbackClaims: Int = 0
    )

    /**
     * Unless explicitly requested, inspection MUST NOT create an empty database.
     * Even after a successful inspection the returned claims are not verified OS outcomes.
     */
    fun inspect(context: Context, initializeIfMissing: Boolean = false): Summary {
        val databaseFile = try {
            context.getDatabasePath("uno_outcome_v1.db")
        } catch (_: Exception) {
            return Summary(Status.UNAVAILABLE)
        }
        if (!initializeIfMissing && !databaseFile.isFile) {
            // A missing main DB beside WAL/journal files is NOT an empty clean history.
            val hasSidecars = listOf("-wal", "-shm", "-journal")
                .any { suffix -> java.io.File(databaseFile.path + suffix).exists() }
            return Summary(if (hasSidecars) Status.UNAVAILABLE else Status.NOT_INITIALIZED)
        }
        return try {
            AndroidOutcomeStore(context).use { store ->
                when (val state = store.inspectAfterRestart()) {
                    is AndroidOutcomeStore.Inspection.Unavailable -> Summary(Status.UNAVAILABLE)
                    is AndroidOutcomeStore.Inspection.Rows -> {
                        var prepared = 0
                        var uncertain = 0
                        var claims = 0
                        for (row in state.entries) {
                            // A future schema with executable recovered tickets must fail closed.
                            if (row.executable) return Summary(Status.UNAVAILABLE)
                            when (row.phase) {
                                1 -> if (!row.used) prepared++ else return Summary(Status.UNAVAILABLE)
                                2 -> if (!row.used) uncertain++ else return Summary(Status.UNAVAILABLE)
                                3 -> if (row.used && row.memoryRef != null) claims++
                                     else return Summary(Status.UNAVAILABLE)
                                else -> return Summary(Status.UNAVAILABLE)
                            }
                        }
                        Summary(Status.INSPECTED, state.entries.size, prepared, uncertain, claims)
                    }
                }
            }
        } catch (_: Exception) {
            // Failed/locked/corrupt storage is never reported as an empty or completed history.
            Summary(Status.UNAVAILABLE)
        }
    }
}
