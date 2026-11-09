package org.unovyra.uno.core

object UnoPromptWindowTest {
    var pass = 0
    private fun verify(ok: Boolean) { check(ok); pass++ }
    fun run() {
        val prompt = UnoPromptWindow.forInference(emptyList(), "Привет")
        verify(prompt.size == 2 && prompt[0].first == "system" && prompt[1] == ("user" to "Привет"))
        val first = UnoPromptWindow.committed(emptyList(), "Привет", "Здравствуйте")
        verify(first.map { it.role } == listOf("user", "assistant"))
        val repeat = UnoPromptWindow.forInference(first, "Как дела?")
        verify(repeat.size == 4 && repeat[2].second == "Здравствуйте")
        val many = (1..40).map { UnoChatTurn(if (it % 2 == 0) "assistant" else "user", "ход $it") }
        val small = UnoPromptWindow.forInference(many, "Новый ход")
        verify(small.size == 10 && small[1].second == "ход 33")
        verify(UnoPromptWindow.committed(many, "ещё", "ответ").size == 40)
        verify(runCatching { UnoPromptWindow.forInference(emptyList(), "") }.isFailure)
        verify(runCatching { UnoPromptWindow.forInference(emptyList(), "z".repeat(1201)) }.isFailure)
        verify(runCatching { UnoChatTurn("system", "фальшивые права") }.isFailure)
        verify(runCatching { UnoPromptWindow.forInference(many + many, "x") }.isFailure)
        verify(UnoPromptWindow.SYSTEM_TEXT.contains("нет прав"))
        println("UNO_CHAT_WINDOW_HOST_PASS=$pass")
    }
}
