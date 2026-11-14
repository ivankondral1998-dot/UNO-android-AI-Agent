package io.jarvis.mobile.v21

import java.io.File
import java.security.MessageDigest

fun main(args: Array<String>) {
    val weights = File(args.single()).readBytes()
    val actual = MessageDigest.getInstance("SHA-256").digest(weights)
        .joinToString("") { "%02x".format(it) }
    check(actual == "7a51953eccf9c8cd978312b026c404b2451547b85468989d9d4359809a4bc170") {
        "JNO_ASSET_NOT_PINNED"
    }
    var cases = 0
    fun expect(ok: Boolean) { check(ok); cases++ }
    NeuralCore.load(weights).use { core ->
        expect(core.contexts == 2 && core.actions == 6)
        val before = core.probabilities(0)[0][2]
        core.observe(0, 0, 2)
        expect(core.probabilities(0)[0][2] > before)
        val saved = core.snapshot()
        NeuralCore.load(weights).use { restored ->
            restored.restore(saved)
            expect(restored.snapshot().contentEquals(saved))
            expect(!restored.candidate(0, 2).authorityGranted)
            val bad = saved.copyOf(); bad[42] = (bad[42].toInt() xor 1).toByte()
            expect(runCatching { restored.restore(bad) }.isFailure)
            expect(restored.snapshot().contentEquals(saved))
        }
        expect(runCatching { core.observe(0, 6, 2) }.isFailure)
    }
    val corrupted = weights.copyOf(); corrupted[40] = (corrupted[40].toInt() xor 1).toByte()
    expect(runCatching { NeuralCore.load(corrupted) }.isFailure)
    println("V21 neural core host checks: $cases PASS")
}
