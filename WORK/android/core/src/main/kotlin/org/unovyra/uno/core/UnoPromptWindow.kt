package org.unovyra.uno.core

/** Experimental text-only prompt window; user text is data, never Android authority. */
data class UnoChatTurn(val role: String, val content: String) {
    init {
        require(role == "user" || role == "assistant")
        require(content.isNotBlank() && content.length <= 1200)
    }
}

object UnoPromptWindow {
    private const val MAX_PRIOR_TURNS = 8
    private const val MAX_SAVED_TURNS = 40
    const val MAX_GENERATION_TOKENS = 128

    /** The system message is not derived from mutable memory, model output or a user field. */
    const val SYSTEM_TEXT =
        "Ты UNO — экспериментальный полностью локальный помощник на Android. " +
        "Отвечай по-русски, прямо и по существу. Не выдумывай факты. " +
        "У тебя нет прав выполнять действия ОС: ты можешь только отвечать текстом."

    fun sanitizeHistory(turns: List<UnoChatTurn>): List<UnoChatTurn> {
        require(turns.size <= MAX_SAVED_TURNS) { "CHAT_HISTORY_TOO_LARGE" }
        return turns.toList()
    }

    /** A fixed bounded context is intentionally distinct from durable exact/semantic memory. */
    fun forInference(history: List<UnoChatTurn>, user: String): List<Pair<String, String>> {
        require(user.isNotBlank() && user.length <= 1200) { "CHAT_MESSAGE_OUT_OF_RANGE" }
        val prior = sanitizeHistory(history).takeLast(MAX_PRIOR_TURNS)
        return listOf("system" to SYSTEM_TEXT) +
            prior.map { it.role to it.content } +
            listOf("user" to user)
    }

    fun committed(history: List<UnoChatTurn>, user: String, answer: String): List<UnoChatTurn> {
        require(answer.isNotBlank() && answer.length <= 1200) { "CHAT_ANSWER_OUT_OF_RANGE" }
        sanitizeHistory(history)
        return (history + UnoChatTurn("user", user) + UnoChatTurn("assistant", answer))
            .takeLast(MAX_SAVED_TURNS)
    }
}
