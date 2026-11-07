package org.unovyra.uno.core

import java.io.File
import java.io.IOException
import java.nio.file.Files

/** Pure JVM journal contracts: no Android OS effects and no power-loss durability claim. */
object ActionIntentJournalTest {
    var pass = 0
    private val digest = "a".repeat(64)
    private fun test(label: String, f: () -> Unit) { f(); pass++; println("PASS OUTBOX $label") }
    private fun temp(): File = Files.createTempDirectory("uno-outbox-test-").resolve("journal.bin").toFile()
    private fun refusedOpen(file: File): Boolean = try {
        ActionIntentJournal(file).close()
        false
    } catch (_: IOException) { true }
    fun run() {
        test("new file empty and prepared") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                check(j.snapshot().isEmpty())
                check(j.prepare("t1",digest))
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.PREPARED)
                check(!j.prepare("t1",digest))
            }
        }
        test("disk replay retains prepared but forbids rearm") {
            val f=temp(); ActionIntentJournal(f).use { check(it.prepare("t1",digest)) }
            ActionIntentJournal(f).use { j ->
                check(j.snapshot().single().recovered)
                check(!j.arm("t1",digest))
            }
        }
        test("disk replay of armed is uncertain and never redispatched") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                check(j.prepare("t2",digest));check(j.arm("t2",digest))
            }
            ActionIntentJournal(f).use { j ->
                val row=j.snapshot().single()
                check(row.phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED && row.recovered)
                check(!j.arm("t2",digest))
            }
        }
        test("unknown ticket and wrong digest cannot arm") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                check(j.prepare("t3",digest))
                check(!j.arm("unknown",digest))
                check(!j.arm("t3","b".repeat(64)))
                check(j.snapshot().single().phase==ActionIntentJournal.Phase.PREPARED)
            }
        }
        test("STOP makes admission permanently fail closed") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                check(j.prepare("t4",digest)); j.stop()
                check(!j.arm("t4",digest));check(!j.prepare("t5",digest));check(j.isStopped())
            }
        }
        test("a second writer cannot open a locked journal") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                var rejected=false
                try { ActionIntentJournal(f).close() }
                catch (e: IllegalStateException) { rejected=e.message=="OUTBOX_ALREADY_OPEN" }
                check(rejected)
            }
            ActionIntentJournal(f).close()
        }
        test("tampered tail fails closed without destructive repair") {
            val f=temp(); ActionIntentJournal(f).use { check(it.prepare("t6",digest)) }
            val len=f.length();java.io.RandomAccessFile(f,"rw").use { r ->
                r.seek(len-1);r.writeByte(0)
            }
            check(refusedOpen(f) && f.length()==len)
        }
        test("truncated tail fails closed without truncation repair") {
            val f=temp(); ActionIntentJournal(f).use { check(it.prepare("t7",digest)) }
            java.io.RandomAccessFile(f,"rw").use { it.seek(it.length());it.writeByte(1) }
            val len=f.length()
            check(refusedOpen(f) && f.length()==len)
        }
        test("invalid identifiers and digests cannot persist") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                check(!j.prepare("../../escape",digest))
                check(!j.prepare("ok","AB".repeat(32)))
                check(!j.prepare("",digest))
                check(j.snapshot().isEmpty() && f.length()==0L)
            }
        }
        test("file cannot be rearmed after close") {
            val f=temp(); val j=ActionIntentJournal(f)
            check(j.prepare("t9",digest));j.close()
            check(!j.arm("t9",digest));check(!j.prepare("t10",digest))
        }
        test("intent file does not contain user action arguments") {
            val f=temp(); ActionIntentJournal(f).use { check(it.prepare("opaque-ticket",digest)) }
            val bytes=f.readBytes().decodeToString()
            check(!bytes.contains("personal user content"))
            check(bytes.contains("opaque-ticket"))
        }
        test("sequence and chain over multiple entries survive replay") {
            val f=temp(); ActionIntentJournal(f).use { j ->
                repeat(32) { idx ->
                    check(j.prepare("ticket_$idx",digest))
                    if(idx%2==0) check(j.arm("ticket_$idx",digest))
                }
            }
            ActionIntentJournal(f).use { j ->
                check(j.snapshot().size==32)
                check(j.snapshot().count { it.phase==ActionIntentJournal.Phase.MAY_HAVE_EXECUTED }==16)
                check(j.snapshot().all { it.recovered })
            }
        }
        println("ACTION_OUTBOX_HOST_PASS=$pass")
    }
}
fun main() { ActionIntentJournalTest.run() }
