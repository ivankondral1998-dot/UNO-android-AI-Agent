package org.unovyra.uno.core

import java.util.concurrent.atomic.AtomicBoolean

enum class PcmStatus { ACCEPTED_FRAME, EMPTY, TOO_LARGE, STOPPED, PERMISSION_DENIED }

/**
 * Bounds a PCM frame. This is not a microphone, not ASR, and not storage.
 * An accepted frame is not a transcript.
 */
class PcmFrameGate(private val maxBytes: Int) {
    init { require(maxBytes in 2..1_048_576) }
    private val stopped = AtomicBoolean(false)
    fun stop() { stopped.set(true) }
    fun isStopped() = stopped.get()

    fun accept(pcm: ByteArray, permissionGranted: Boolean): PcmStatus {
        if (stopped.get()) return PcmStatus.STOPPED
        if (!permissionGranted) return PcmStatus.PERMISSION_DENIED
        if (pcm.isEmpty()) return PcmStatus.EMPTY
        if (pcm.size > maxBytes) return PcmStatus.TOO_LARGE
        return PcmStatus.ACCEPTED_FRAME
    }
}

enum class SensorFreshness { PRESENT, ABSENT, STALE, DENIED }

/** Missing is not the number zero. A denied channel returns no value. */
fun sensorFreshness(
    value: Double?, observedAt: Long, now: Long, maxAgeNanos: Long, permission: Boolean
): SensorFreshness {
    if (!permission) return SensorFreshness.DENIED
    if (value == null || !value.isFinite()) return SensorFreshness.ABSENT
    if (maxAgeNanos < 0 || observedAt < 0 || now < observedAt || now - observedAt > maxAgeNanos) {
        return SensorFreshness.STALE
    }
    return SensorFreshness.PRESENT
}
