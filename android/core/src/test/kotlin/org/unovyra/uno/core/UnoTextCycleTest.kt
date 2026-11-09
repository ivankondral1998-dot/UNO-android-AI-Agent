package org.unovyra.uno.core

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

object UnoTextCycleTest {
    var pass = 0
    private fun expect(ok: Boolean) { check(ok); pass++ }
    fun run() {
        var writes = 0
        var stored = emptyList<UnoChatTurn>()
        val cycle = UnoTextCycle(emptyList()) { stored = it.toList(); writes++ }
        val event = UnoTextInput("Привет", 1L, "LOCAL_UI_TEXT")
        val result = cycle.run(event, { false }) { prompt, stopped ->
            expect(prompt.size == 2 && prompt.last() == ("user" to "Привет") && !stopped())
            "Здравствуйте"
        }
        expect(result.status == UnoTextStatus.COMMITTED && result.revision == 1L)
        expect(result.history == stored && writes == 1)
        expect(result.stateSha256.length == 64 && !result.nativeEffectDispatched)

        var modelCalls = 0
        val empty = cycle.run(UnoTextInput("", 2L, "LOCAL_UI_TEXT"), { false }) { _, _ ->
            modelCalls++; "NO"
        }
        expect(empty.status == UnoTextStatus.INVALID_INPUT && modelCalls == 0 && writes == 1)
        val failed = cycle.run(UnoTextInput("Вопрос", 3L, "LOCAL_UI_TEXT"), { false }) { _, _ ->
            modelCalls++; throw IllegalStateException("model not loaded")
        }
        expect(failed.status == UnoTextStatus.MODEL_FAILED && writes == 1)
        val cancelled = cycle.run(UnoTextInput("Вопрос", 4L, "LOCAL_UI_TEXT"), { true }) { _, _ ->
            modelCalls++; "SHOULD NOT RUN"
        }
        expect(cancelled.status == UnoTextStatus.CANCELLED && modelCalls == 1)
        val blank = cycle.run(UnoTextInput("Вопрос", 5L, "LOCAL_UI_TEXT"), { false }) { _, _ -> "" }
        expect(blank.status == UnoTextStatus.MODEL_FAILED && writes == 1)
        val backwards = cycle.run(UnoTextInput("Вопрос", 1L, "LOCAL_UI_TEXT"), { false }) { _, _ -> "NO" }
        expect(backwards.status == UnoTextStatus.INVALID_INPUT && writes == 1)

        val writeFailure = UnoTextCycle(emptyList()) { throw IllegalStateException("disk full") }
        val noCommit = writeFailure.run(event, { false }) { _, _ -> "response" }
        expect(noCommit.status == UnoTextStatus.STORAGE_FAILED &&
            noCommit.history.isEmpty() && noCommit.revision == 0L)
        expect(writeFailure.clear().status == UnoTextStatus.STORAGE_FAILED)

        val entered = CountDownLatch(1)
        val release = CountDownLatch(1)
        val concurrent = UnoTextCycle(emptyList()) { }
        var finish: UnoTextReceipt? = null
        val thread = Thread {
            finish = concurrent.run(event, { false }) { _, stop ->
                entered.countDown()
                release.await(2, TimeUnit.SECONDS)
                expect(stop())
                "never commit"
            }
        }
        thread.start()
        expect(entered.await(2, TimeUnit.SECONDS))
        expect(concurrent.run(event, { false }) { _, _ -> "unsafe" }.status == UnoTextStatus.BUSY)
        concurrent.stop()
        release.countDown(); thread.join(3000)
        expect(!thread.isAlive && finish?.status == UnoTextStatus.CANCELLED)
        expect(concurrent.clear().status == UnoTextStatus.STOPPED)
        expect(concurrent.run(event, { false }) { _, _ -> "no" }.status == UnoTextStatus.STOPPED)
        val goodClear = cycle.clear()
        expect(goodClear.status == UnoTextStatus.COMMITTED && goodClear.history.isEmpty() && writes == 2)
        expect(goodClear.revision == 2L)
        println("UNO_TEXT_CYCLE_HOST_PASS=$pass")
    }
}
