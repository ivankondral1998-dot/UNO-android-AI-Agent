package org.unovyra.uno
import android.content.Context
import java.nio.file.Files
import java.io.Closeable

class AndroidOutcomeStore(val ctx: Context): Closeable {
    companion object {
        var constructed=0
        var shouldThrow=false
        var next: Inspection = Inspection.Rows(emptyList())
    }
    init { constructed++; if (shouldThrow) throw IllegalStateException("fixture: corrupt DB") }
    sealed class Inspection {
        data class Rows(val entries: List<StoredOutcome>) : Inspection()
        data class Unavailable(val reason: String) : Inspection()
    }
    data class StoredOutcome(val phase: Int, val used: Boolean, val memoryRef: String?, val executable:Boolean)
    fun inspectAfterRestart():Inspection = next
    override fun close() {}
}

fun main() {
    var passes=0
    fun checkCase(label:String, run:()->Unit) { run();passes++;println("PASS INSPECTION $label") }
    val dir=Files.createTempDirectory("uno-inspection-")
    val f=dir.resolve("uno_outcome_v1.db").toFile()
    val ctx=Context(f)
    fun reset() { AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(emptyList());AndroidOutcomeStore.shouldThrow=false; AndroidOutcomeStore.constructed=0 }
    reset()
    checkCase("absent database remains absent and never opens SQLite") {
        val s=AndroidOutcomeInspection.inspect(ctx,false)
        check(s.status==AndroidOutcomeInspection.Status.NOT_INITIALIZED && s.total==0)
        check(!f.exists() && AndroidOutcomeStore.constructed==0)
    }
    reset()
    checkCase("orphan WAL without main database is not mistaken for clean empty history") {
        val wal=dir.resolve("uno_outcome_v1.db-wal").toFile()
        wal.writeText("orphaned")
        val s=AndroidOutcomeInspection.inspect(ctx, false)
        check(s.status==AndroidOutcomeInspection.Status.UNAVAILABLE)
        check(!f.exists() && AndroidOutcomeStore.constructed==0)
        wal.delete()
    }
    reset()
    checkCase("explicit initialization is required for new database") {
        val s=AndroidOutcomeInspection.inspect(ctx,true)
        check(s.status==AndroidOutcomeInspection.Status.INSPECTED && s.total==0)
        check(AndroidOutcomeStore.constructed==1)
    }
    f.writeText("fixture")
    reset()
    checkCase("existing empty database is not NOT_INITIALIZED") {
        check(AndroidOutcomeInspection.inspect(ctx,false).status==AndroidOutcomeInspection.Status.INSPECTED)
        check(AndroidOutcomeStore.constructed==1)
    }
    reset()
    checkCase("count all phases without exposing ticket content") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(listOf(
            AndroidOutcomeStore.StoredOutcome(1,false,null,false),
            AndroidOutcomeStore.StoredOutcome(2,false,null,false),
            AndroidOutcomeStore.StoredOutcome(3,true,"sha256",false)
        ))
        val s=AndroidOutcomeInspection.inspect(ctx)
        check(s.status==AndroidOutcomeInspection.Status.INSPECTED)
        check(s.total==3 && s.prepared==1 && s.mayHaveExecuted==1 && s.storedReadbackClaims==1)
        check(s.toString().contains("sha256").not())
    }
    reset()
    checkCase("claimed completion without used bit fails closed") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(listOf(AndroidOutcomeStore.StoredOutcome(3,false,"sha",false)))
        check(AndroidOutcomeInspection.inspect(ctx).status==AndroidOutcomeInspection.Status.UNAVAILABLE)
    }
    reset()
    checkCase("recovered executable ticket fails closed") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(listOf(AndroidOutcomeStore.StoredOutcome(1,false,null,true)))
        check(AndroidOutcomeInspection.inspect(ctx).status==AndroidOutcomeInspection.Status.UNAVAILABLE)
    }
    reset()
    checkCase("unknown future phase fails closed") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(listOf(AndroidOutcomeStore.StoredOutcome(42,false,null,false)))
        check(AndroidOutcomeInspection.inspect(ctx).status==AndroidOutcomeInspection.Status.UNAVAILABLE)
    }
    reset()
    checkCase("storage-declared unavailable fails closed") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Unavailable("corrupt")
        check(AndroidOutcomeInspection.inspect(ctx).status==AndroidOutcomeInspection.Status.UNAVAILABLE)
    }
    reset()
    checkCase("SQLite constructor failure is not misreported as no actions") {
        AndroidOutcomeStore.shouldThrow=true
        check(AndroidOutcomeInspection.inspect(ctx).status==AndroidOutcomeInspection.Status.UNAVAILABLE)
    }
    reset()
    checkCase("arm without used flag cannot be counted as proven effect") {
        AndroidOutcomeStore.next=AndroidOutcomeStore.Inspection.Rows(listOf(AndroidOutcomeStore.StoredOutcome(2,false,null,false)))
        val s=AndroidOutcomeInspection.inspect(ctx)
        check(s.status==AndroidOutcomeInspection.Status.INSPECTED && s.storedReadbackClaims==0 && s.mayHaveExecuted==1)
    }
    println("UNO_OUTCOME_INSPECTOR_HOST_PASS=$passes")
}
