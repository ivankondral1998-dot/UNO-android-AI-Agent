package org.unovyra.uno

import android.content.Context
import android.database.sqlite.SQLiteDatabase
import android.database.sqlite.SQLiteException
import android.database.sqlite.SQLiteOpenHelper
import android.os.SystemClock
import org.unovyra.uno.core.NativeEndpoint
import org.unovyra.uno.core.NativeEvidence
import org.unovyra.uno.core.Phase
import org.unovyra.uno.core.Ticket
import java.io.Closeable
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Android SQLite transaction boundary for action *records*, not for actions themselves.
 *
 * No OS privileges, no model calls, no dispatch, no identity/consent authority and no autonomous
 * retry. It is intentionally NOT wired to TrustController or to an Android NativePort yet.
 * A source-tagged readback claim here is not a verified OS fact. An independent trusted
 * Android owner/permission/dispatch/readback adapter is still required.
 *
 * All DB access must be on a non-UI thread in a single trusted application process.
 * NeuralWorkerService is isolated and cannot obtain this store or acquire authority.
 */
internal class AndroidOutcomeStore(context: Context) : SQLiteOpenHelper(
    context.applicationContext, DATABASE_NAME, null, DATABASE_VERSION
), Closeable {
    companion object {
        private const val DATABASE_NAME = "uno_outcome_v1.db"
        private const val DATABASE_VERSION = 1
        private const val PREPARED = 1
        private const val MAY_HAVE_EXECUTED = 2
        private const val READBACK_CLAIM = 3
        private const val MAX_ACTIVE = 32
        private const val MAX_TOTAL = 4096

        // Stable, independently executable SQL for host schema/fault-injection tests.
        internal const val CREATE_OPERATIONS = """
CREATE TABLE operations (
    ticket_id TEXT PRIMARY KEY NOT NULL,
    proposal_sha256 TEXT NOT NULL CHECK(length(proposal_sha256)=64),
    session_nonce TEXT NOT NULL,
    owner_epoch INTEGER NOT NULL CHECK(owner_epoch>=0),
    deadline_ns INTEGER NOT NULL CHECK(deadline_ns>0),
    prepared_ns INTEGER NOT NULL CHECK(prepared_ns>=0),
    dispatch_ns INTEGER,
    phase INTEGER NOT NULL CHECK(phase IN (1,2,3)),
    used INTEGER NOT NULL DEFAULT 0 CHECK(used IN (0,1)),
    outcome INTEGER CHECK(outcome IN (0,1)),
    source_tag TEXT,
    generation INTEGER,
    observed_ns INTEGER,
    memory_ref TEXT REFERENCES memory_records(content_sha256) ON DELETE RESTRICT,
    CHECK ((phase=1 AND dispatch_ns IS NULL AND used=0 AND outcome IS NULL AND source_tag IS NULL AND generation IS NULL AND observed_ns IS NULL AND memory_ref IS NULL)
        OR (phase=2 AND dispatch_ns IS NOT NULL AND used=0 AND outcome IS NULL AND source_tag IS NULL AND generation IS NULL AND observed_ns IS NULL AND memory_ref IS NULL)
        OR (phase=3 AND dispatch_ns IS NOT NULL AND used=1 AND outcome IS NOT NULL AND source_tag IS NOT NULL AND generation>0 AND observed_ns>=dispatch_ns AND memory_ref IS NOT NULL))
)
"""
        internal const val CREATE_MEMORY = """
CREATE TABLE memory_records (
    content_sha256 TEXT PRIMARY KEY NOT NULL CHECK(length(content_sha256)=64),
    kind TEXT NOT NULL CHECK(kind='REFERENCE_READBACK_CLAIM'),
    payload BLOB NOT NULL CHECK(length(payload)>0 AND length(payload)<=4096)
)
"""
        internal const val CREATE_REFERENCE_INDEX = """
CREATE INDEX operations_session_phase ON operations(session_nonce,phase)
"""
        internal const val CREATE_TRUSTED_LINK = """
CREATE TRIGGER memory_ref_insert_guard BEFORE UPDATE OF memory_ref ON operations
WHEN NEW.memory_ref IS NOT NULL AND NOT EXISTS
 (SELECT 1 FROM memory_records WHERE content_sha256=NEW.memory_ref)
BEGIN SELECT RAISE(ABORT,'MISSING_MEMORY_REFERENCE'); END
"""
    }

    private val stopLatch = AtomicBoolean(false)
    private val sessionNonce = ByteArray(16).also { SecureRandom().nextBytes(it) }
        .joinToString("") { "%02x".format(it) }
    private val thisSessionTickets = HashSet<String>()
    private var failed = false

    init { setWriteAheadLoggingEnabled(true) }

    override fun onConfigure(db: SQLiteDatabase) {
        super.onConfigure(db)
        db.setForeignKeyConstraintsEnabled(true)
    }

    override fun onCreate(db: SQLiteDatabase) {
        db.execSQL(CREATE_OPERATIONS)
        db.execSQL(CREATE_MEMORY)
        db.execSQL(CREATE_REFERENCE_INDEX)
        db.execSQL(CREATE_TRUSTED_LINK)
    }

    /** Never destroy or silently migrate previous evidence on a version mismatch. */
    override fun onUpgrade(db: SQLiteDatabase, oldVersion: Int, newVersion: Int) {
        throw SQLiteException("UNO_OUTCOME_MIGRATION_NOT_AUTHORIZED_"+oldVersion+"_"+newVersion)
    }

    override fun onOpen(db: SQLiteDatabase) {
        super.onOpen(db)
        db.rawQuery("PRAGMA quick_check", null).use { cursor ->
            if (!cursor.moveToFirst() || cursor.getString(0) != "ok" || cursor.moveToNext()) {
                failed = true
                throw SQLiteException("UNO_OUTCOME_INTEGRITY_FAILURE")
            }
        }
        // Validate referenced bytes BEFORE permitting any new transaction after reopen.
        // A normal SQLite integrity_check does not detect altered application payload hashes.
        db.rawQuery("SELECT o.memory_ref,m.payload FROM operations o LEFT JOIN memory_records m ON m.content_sha256=o.memory_ref WHERE o.phase=3",null).use { c ->
            while(c.moveToNext()) {
                if(c.isNull(0) || c.isNull(1) || sha256(c.getBlob(1)) != c.getString(0)) {
                    failed = true
                    throw SQLiteException("UNO_OUTCOME_REFERENCE_HASH_INVALID")
                }
            }
        }
    }

    private fun validId(s: String): Boolean = s.length in 1..128 && s.all {
        it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' || it in "_-:."
    }
    private fun validSource(s: String): Boolean = s.length in 1..96 && s.all {
        it in 'a'..'z' || it in 'A'..'Z' || it in '0'..'9' || it in "_-:."
    }
    private fun validDigest(s: String): Boolean = s.length == 64 && s.all { it in '0'..'9' || it in 'a'..'f' }
    private fun sha256(s: ByteArray): String = MessageDigest.getInstance("SHA-256").digest(s)
        .joinToString("") { "%02x".format(it) }

    private fun count(db: SQLiteDatabase, where: String? = null): Long {
        val sql = if (where == null) "SELECT count(*) FROM operations"
                  else "SELECT count(*) FROM operations WHERE $where"
        db.rawQuery(sql, null).use { c ->
            if (!c.moveToFirst()) throw SQLiteException("UNO_OUTCOME_COUNT_FAILED")
            return c.getLong(0)
        }
    }

    /** All modifications, including the memory ref, use the same SQLite transaction. */
    private fun transaction(block: (SQLiteDatabase) -> Boolean): Boolean {
        if (failed || stopLatch.get()) return false
        var db: SQLiteDatabase? = null
        var began = false
        return try {
            db = writableDatabase
            db.beginTransactionNonExclusive()
            began = true
            val ok = block(db) && !stopLatch.get()
            if (ok) db.setTransactionSuccessful()
            // Never return true until endTransaction itself has succeeded.
            db.endTransaction()
            began = false
            ok
        } catch (_: Exception) {
            failed = true // disk full, schema error and corruption must fail closed
            false
        } finally {
            if (began) {
                try { db?.endTransaction() } catch (_: Exception) { failed = true }
            }
        }
    }

    /** Stage only a digest, never raw model-controlled action arguments or future permissions. */
    @Synchronized fun stage(ticket: Ticket): Boolean {
        val now = SystemClock.elapsedRealtimeNanos()
        if (ticket.phase != Phase.PREPARED || ticket.used || !validId(ticket.id) ||
            !validDigest(ticket.proposalDigest) || ticket.epoch < 0 ||
            now >= ticket.deadlineNanos || thisSessionTickets.contains(ticket.id)) return false
        val ok = transaction { db ->
            if (count(db) >= MAX_TOTAL || count(db, "phase!=3") >= MAX_ACTIVE) return@transaction false
            val insert = "INSERT INTO operations (ticket_id,proposal_sha256,session_nonce,owner_epoch,deadline_ns,prepared_ns,phase,used) VALUES (?,?,?,?,?,?,1,0)"
            db.execSQL(insert, arrayOf(ticket.id,ticket.proposalDigest,sessionNonce,
                ticket.epoch,ticket.deadlineNanos,now))
            true
        }
        if (ok) thisSessionTickets.add(ticket.id)
        return ok
    }

    /** Must commit MAY_HAVE_EXECUTED before a trusted native dispatcher may run. */
    @Synchronized fun arm(ticket: Ticket): Boolean {
        if (ticket.phase != Phase.PREPARED || ticket.used ||
            !thisSessionTickets.contains(ticket.id)) return false
        val now = SystemClock.elapsedRealtimeNanos()
        if (now >= ticket.deadlineNanos) return false
        return transaction { db ->
            val sql = "UPDATE operations SET phase=2,dispatch_ns=? WHERE ticket_id=? AND proposal_sha256=? AND session_nonce=? AND owner_epoch=? AND phase=1 AND used=0"
            db.execSQL(sql,arrayOf(now,ticket.id,ticket.proposalDigest,sessionNonce,ticket.epoch))
            changed(db) == 1L
        }
    }

    /** SQLite changes() is connection-local and queried while still in our transaction. */
    private fun changed(db: SQLiteDatabase): Long = db.rawQuery("SELECT changes()",null).use { c ->
        if (!c.moveToFirst()) throw SQLiteException("UNO_OUTCOME_CHANGES_FAILED")
        c.getLong(0)
    }

    /**
     * Stores an untrusted *claim* only; no owner, capability, or independent native validation.
     * The memory record and operation's used/outcome/source/timestamp/reference become visible
     * together, or not at all. UNKNOWN never enters this terminal path.
     */
    @Synchronized fun recordReadbackClaim(ticket: Ticket, evidence: NativeEvidence): Boolean {
        if (ticket.phase != Phase.WAIT_READBACK || ticket.used ||
            !thisSessionTickets.contains(ticket.id) ||
            ticket.proposalDigest.length != 64 || evidence.ticketId != ticket.id ||
            evidence.endpoint == NativeEndpoint.UNKNOWN || !validSource(evidence.source) ||
            evidence.nativeGeneration <= 0 || evidence.observedAtNanos < 0) return false
        val now = SystemClock.elapsedRealtimeNanos()
        if (now >= ticket.deadlineNanos || evidence.observedAtNanos > now) return false
        val state = if (evidence.endpoint == NativeEndpoint.TRUE) 1 else 0
        val bytes = ("REFERENCE_READBACK_CLAIM/1|"+ticket.id+"|"+ticket.proposalDigest+"|"+
            state+"|"+evidence.source+"|"+evidence.nativeGeneration+"|"+evidence.observedAtNanos)
            .toByteArray(Charsets.UTF_8)
        if (bytes.size > 4096) return false
        val digest = sha256(bytes)
        return transaction { db ->
            val observedDispatch = db.rawQuery(
                "SELECT dispatch_ns FROM operations WHERE ticket_id=? AND proposal_sha256=? AND session_nonce=? AND owner_epoch=? AND phase=2 AND used=0",
                arrayOf(ticket.id,ticket.proposalDigest,sessionNonce,ticket.epoch.toString())
            ).use { c -> if (c.moveToFirst() && !c.isNull(0)) c.getLong(0) else null }
                ?: return@transaction false
            if (evidence.observedAtNanos < observedDispatch) return@transaction false
            db.execSQL("INSERT OR IGNORE INTO memory_records(content_sha256,kind,payload) VALUES (?,'REFERENCE_READBACK_CLAIM',?)",
                arrayOf(digest,bytes))
            db.execSQL("UPDATE operations SET phase=3,used=1,outcome=?,source_tag=?,generation=?,observed_ns=?,memory_ref=? WHERE ticket_id=? AND proposal_sha256=? AND session_nonce=? AND owner_epoch=? AND phase=2 AND used=0",
                arrayOf(state,evidence.source,evidence.nativeGeneration,evidence.observedAtNanos,
                    digest,ticket.id,ticket.proposalDigest,sessionNonce,ticket.epoch))
            changed(db) == 1L
        }
    }

    /** Crash recovery is inspect-only. Never returns an executable Ticket. */
    @Synchronized fun inspectAfterRestart(): Inspection {
        if (failed || stopLatch.get()) return Inspection.Unavailable("STORE_CLOSED_OR_FAILED")
        return try {
            val db = readableDatabase
            val result = ArrayList<StoredOutcome>()
            db.rawQuery("SELECT ticket_id,phase,used,outcome,memory_ref FROM operations ORDER BY rowid",null).use { c ->
                while (c.moveToNext()) {
                    val id = c.getString(0)
                    val phase = c.getInt(1)
                    val used = c.getInt(2) == 1
                    val outcome = if (c.isNull(3)) null else c.getInt(3)
                    val memoryRef = if (c.isNull(4)) null else c.getString(4)
                    if (phase == READBACK_CLAIM && (!used || memoryRef == null))
                        throw SQLiteException("UNO_OUTCOME_INVALID_COMMIT")
                    if (phase == READBACK_CLAIM) {
                        val payload = db.rawQuery("SELECT payload FROM memory_records WHERE content_sha256=?",arrayOf(memoryRef!!)).use { mc ->
                            if (mc.moveToFirst()) mc.getBlob(0) else null
                        } ?: throw SQLiteException("UNO_OUTCOME_MEMORY_REF_MISSING")
                        if (sha256(payload) != memoryRef)
                            throw SQLiteException("UNO_OUTCOME_MEMORY_HASH_MISMATCH")
                    }
                    // PREPARED and MAY_HAVE_EXECUTED are always unresolved after process death.
                    result.add(StoredOutcome(id,phase,used,outcome,memoryRef,executable=false))
                }
            }
            Inspection.Rows(result)
        } catch (_: Exception) {
            failed = true
            Inspection.Unavailable("STORE_RECOVERY_FAILED")
        }
    }

    internal sealed class Inspection {
        data class Rows(val entries: List<StoredOutcome>): Inspection()
        data class Unavailable(val reason: String): Inspection()
    }

    @Synchronized fun isFailed(): Boolean = failed

    fun stop() { stopLatch.set(true) }
    @Synchronized override fun close() { stop(); super.close() }

    internal data class StoredOutcome(
        val ticketId: String, val phase: Int, val used: Boolean,
        val endpoint: Int?, val memoryRef: String?, val executable: Boolean
    )
}
