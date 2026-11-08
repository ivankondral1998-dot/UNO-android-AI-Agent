package android.content
import java.io.File
class Context(val path:File) {
    fun getDatabasePath(name: String): File = path
}
