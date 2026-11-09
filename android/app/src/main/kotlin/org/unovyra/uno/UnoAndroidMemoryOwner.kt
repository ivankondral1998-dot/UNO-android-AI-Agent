package org.unovyra.uno

import android.content.Context
import org.unovyra.uno.core.UnoExactMemoryPort
import java.io.File
import java.io.RandomAccessFile
import java.nio.channels.FileLock
import java.nio.channels.OverlappingFileLockException

/**
 * Single owner of encrypted exact memory for this Android app process.
 * A second process (including an isolated worker) is denied by an OS file lock.
 * The lock is held for the lifetime of the process, never a model-granted capability.
 */
internal object UnoAndroidMemoryOwner {
    private data class Session(
        val store: UnoExactMemoryPort,
        val file: RandomAccessFile,
        val lock: FileLock
    )
    private var session: Session? = null

    @Synchronized fun exact(context: Context): UnoExactMemoryPort {
        val existing = session
        if (existing != null) {
            check(existing.lock.isValid) { "EXACT_OWNER_LOCK_LOST" }
            return existing.store
        }
        val root = context.applicationContext
        val parent = root.filesDir
        check(parent.isDirectory) { "EXACT_OWNER_DIRECTORY_MISSING" }
        val file = RandomAccessFile(File(parent, "uno_exact_memory_writer_v1.lock"), "rw")
        val lock = try {
            file.channel.tryLock()
        } catch (_: OverlappingFileLockException) { null }
        catch (e: Exception) { file.close(); throw e }
        if (lock == null) {
            file.close()
            throw IllegalStateException("EXACT_MEMORY_ALREADY_OWNED")
        }
        try {
            val vault = UnoAndroidExactMemory(root)
            session = Session(vault, file, lock)
            return vault
        } catch (e: Throwable) {
            lock.release()
            file.close()
            throw e
        }
    }
}
