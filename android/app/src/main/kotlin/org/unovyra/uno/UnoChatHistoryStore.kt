package org.unovyra.uno

import android.content.Context
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import org.unovyra.uno.core.UnoChatTurn
import org.unovyra.uno.core.UnoPromptWindow
import java.io.File
import java.io.ByteArrayOutputStream

/** App-private exact chat transcript. Unencrypted experiment, NOT semantic or trusted outcome memory. */
internal class UnoChatHistoryStore(context: Context) {
    private val file = AtomicFile(File(context.filesDir, "uno_chat_experiment_v1.json"))
    fun load(): List<UnoChatTurn> {
        if (!file.baseFile.exists()) return emptyList()
        val bytes = file.openRead().use { stream ->
            // Do not accept unbounded/corrupt transcripts.
            val cap = 100_000
            val output = ByteArrayOutputStream()
            val chunk = ByteArray(4096)
            while (true) {
                val count = stream.read(chunk)
                if (count < 0) break
                require(output.size() + count <= cap) { "CHAT_RECORD_TOO_LARGE" }
                output.write(chunk, 0, count)
            }
            output.toByteArray()
        }
        val obj = JSONObject(String(bytes, Charsets.UTF_8))
        require(obj.getString("schema") == "UNO_CHAT_EXPERIMENT/1") { "CHAT_SCHEMA_UNSUPPORTED" }
        val entries = obj.getJSONArray("turns")
        require(entries.length() <= 40) { "CHAT_RECORD_TOO_MANY_TURNS" }
        return UnoPromptWindow.sanitizeHistory((0 until entries.length()).map { i ->
            val item = entries.getJSONObject(i)
            UnoChatTurn(item.getString("role"), item.getString("content"))
        })
    }
    fun save(turns: List<UnoChatTurn>) {
        val valid = UnoPromptWindow.sanitizeHistory(turns)
        val array = JSONArray()
        valid.forEach { array.put(JSONObject().put("role", it.role).put("content", it.content)) }
        val bytes = JSONObject().put("schema", "UNO_CHAT_EXPERIMENT/1")
            .put("turns", array).toString().toByteArray(Charsets.UTF_8)
        require(bytes.size <= 100_000)
        val stream = file.startWrite()
        try {
            stream.write(bytes)
            file.finishWrite(stream)
        } catch (e: Exception) {
            file.failWrite(stream)
            throw e
        }
    }
}
