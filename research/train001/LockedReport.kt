package org.unovyra.uno.research

import java.nio.file.*
import java.nio.channels.FileChannel
import java.nio.ByteBuffer

/** Crash retries keep the same pre-test selection. Completed results are replayed, never reselected. */
internal fun lockedReport(directory:Path,pin:String,produce:()->String):String {
    val marker=directory.resolve("locked-test-selected.txt")
    val report=directory.resolve("locked-test-results.txt")
    if(Files.exists(marker)) require(Files.readString(marker)==pin) {"LOCKED_TEST_SELECTION_CHANGED"}
    else Files.writeString(marker,pin,StandardOpenOption.CREATE_NEW)
    if(Files.exists(report)) return Files.readString(report)
    val value=produce()
    val temp=Files.createTempFile(directory,"test-results-",".tmp")
    try {
        FileChannel.open(temp,StandardOpenOption.WRITE).use {ch ->
            val buffer=ByteBuffer.wrap(value.toByteArray(Charsets.UTF_8));while(buffer.hasRemaining()) ch.write(buffer);ch.force(true)
        }
        Files.move(temp,report,StandardCopyOption.ATOMIC_MOVE)
    } finally {Files.deleteIfExists(temp)}
    return value
}
