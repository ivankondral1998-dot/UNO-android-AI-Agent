package org.unovyra.uno.core

/** R5.4 Candidate §3, erratum 06. Bounds on the real map of decoded weights,
 * not JVM rounding error, S4, or arbitrary adaptive policies. */
internal fun stabilityAdd(a: Double, b: Double): Double = when {
    a == 0.0 -> b
    b == 0.0 -> a
    else -> Math.nextUp(a + b)
}
internal fun stabilityMul(a: Double, b: Double): Double = when {
    a == 0.0 || b == 0.0 -> 0.0
    a == 1.0 -> b
    b == 1.0 -> a
    else -> Math.nextUp(a * b)
}
private fun stabilityMean(sum: Double, n: Int): Double =
    if (sum == 0.0 || n == 1) sum else Math.nextUp(sum / n)

internal class UnoRefStability private constructor(
    val gamma: Double, val lz: Double, private val blocks: Int
) {
    companion object {
        fun from(w: UnoRefWeights): UnoRefStability {
            var g = 0.0; var z = 0.0
            for (j in 0 until w.blocks) {
                var ga = 0.0; var gz = 0.0
                for (l in 0 until w.branchCount) {
                    val k = w.branches[l][j]
                    val b = k.b.decodedRowL1Upper()
                    ga = stabilityAdd(ga, stabilityMul(b, k.a.decodedRowL1Upper()))
                    gz = stabilityAdd(gz, stabilityMul(b, k.c.decodedRowL1Upper()))
                }
                g = maxOf(g, stabilityMean(ga, w.branchCount))
                z = maxOf(z, stabilityMean(gz, w.branchCount))
            }
            require(g.isFinite() && z.isFinite())
            return UnoRefStability(g,z,w.blocks)
        }
    }
    /** Same mask and alpha on both trajectories. Inactive rows are identity. */
    fun coefficient(mask: BooleanArray, alpha: Double): Double {
        require(mask.size == blocks && mask.any { it } && alpha in 0.0..1.0)
        if (alpha == 0.0) return 1.0
        val complement = if (alpha == 1.0) 0.0 else Math.nextUp(1.0 - alpha)
        val active = stabilityAdd(complement, stabilityMul(alpha, gamma))
        return if (mask.all { it }) active else maxOf(1.0, active)
    }
    /** e_next <= c_M e + alpha L_z^F delta_z. Repeat for a common sequence. */
    fun propagate(mask: BooleanArray, alpha: Double, error: Double, deltaZ: Double): Double {
        require(error.isFinite() && error >= 0 && deltaZ.isFinite() && deltaZ >= 0)
        return stabilityAdd(stabilityMul(coefficient(mask, alpha), error),
            stabilityMul(stabilityMul(alpha, lz), deltaZ))
    }
    /** Common fixed z and alpha, relative to shared fixed point; not a S6 schedule guarantee. */
    fun fairSweepCoefficient(masks: List<BooleanArray>, alpha: Double): Double? {
        require(alpha in 0.0..1.0 && masks.isNotEmpty())
        val covered = BooleanArray(blocks)
        for (mask in masks) {
            require(mask.size == blocks && mask.any { it })
            for (i in mask.indices) covered[i] = covered[i] || mask[i]
        }
        if (!covered.all { it } || gamma >= 1.0 || alpha == 0.0) return null
        return coefficient(covered, alpha).takeIf { it < 1.0 }
    }
}
