package org.unovyra.uno.core

/** Erratum 05: explicit host-reference limits, not physical RAM/WCET/energy.
 * Numeric payload = conservative reservation for resident coefficient arrays and
 * explicit primitive numeric buffers (including copies). Scalar units are
 * conservative stage charges, not measured CPU instructions. Arbitrary external
 * head callbacks, object overhead, hashing, IO and other sessions are EXCLUDED.
 */
internal data class RefCycleLimits(val mac: Long, val scalarUnits: Long,
    val numericBytes: Long, val catalogueRows: Long) {
    init { require(mac >= 0 && scalarUnits >= 0 && numericBytes >= 0 && catalogueRows >= 0) }
}
internal data class RefCycleUsage(val enteredMac: Long, val scalarReserved: Long,
    val numericReservedBytes: Long, val catalogueRowsReserved: Long,
    val catalogueRowsObserved: Long, val kernelEntries: Map<String, Long>,
    val externalHeadEntries: Long)
internal class RefCycleAbort(val status: RefSessionStatus): RuntimeException(status.name)

internal fun refAdd(vararg values: Long): Long = values.fold(0L, Math::addExact)
internal fun refMul(vararg values: Long): Long = values.fold(1L, Math::multiplyExact)

/** One attempt, one reservation. No MAC refund after entry (a failed kernel
 * may have executed partially). Reserve scalar, numeric buffers, both catalogue
 * scans and publication BEFORE any work; dynamic S6 spends only remaining MAC.
 * Time checkpoints are cooperative, NOT a bound on duration of an in-flight call.
 */
internal class RefCycleMeter(private val limits: RefCycleLimits,
    private val checkTime: () -> Unit) {
    private var reserved = false
    private var mac = 0L
    private var scalar = 0L
    private var numeric = 0L
    private var rows = 0L
    private var observed = 0L
    private var heads = 0L
    private val entries = linkedMapOf<String, Long>()
    val remainingMac get() = limits.mac - mac
    fun checkpoint() = checkTime()
    fun reserve(minMac: Long, scalarUnits: Long, numericBytes: Long, catalogueRows: Long) {
        check(!reserved) { "CYCLE_ALREADY_RESERVED" }
        require(minMac >= 0 && scalarUnits >= 0 && numericBytes >= 0 && catalogueRows >= 0)
        checkpoint()
        if (minMac > limits.mac || scalarUnits > limits.scalarUnits ||
            numericBytes > limits.numericBytes || catalogueRows > limits.catalogueRows)
            throw RefCycleAbort(RefSessionStatus.BUDGET_ABORT)
        scalar = scalarUnits; numeric = numericBytes; rows = catalogueRows; reserved = true
    }
    fun ensureMac(cost: Long) {
        check(reserved) { "CYCLE_NOT_RESERVED" }
        if (cost < 0 || cost > remainingMac) throw RefCycleAbort(RefSessionStatus.BUDGET_ABORT)
    }
    fun enter(name: String, cost: Long) {
        checkpoint(); ensureMac(cost)
        mac += cost
        entries[name] = Math.incrementExact(entries[name] ?: 0L)
    }
    fun observeCatalogue(count: Int) {
        check(reserved) { "CYCLE_NOT_RESERVED" }
        require(count >= 0 && count.toLong() <= rows - observed)
        observed += count
    }
    fun head() { check(reserved) { "CYCLE_NOT_RESERVED" }; checkpoint(); heads = Math.incrementExact(heads) }
    fun usage() = RefCycleUsage(mac, scalar, numeric, rows, observed, entries.toMap(), heads)
}
