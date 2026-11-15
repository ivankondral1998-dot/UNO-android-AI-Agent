import kotlin.math.*

/**
 * Independent, source-shaped S4 algebra regression. It mirrors the documented
 * scoring operations of UnoSemanticMemory.retrieve and the S4 dot-product law.
 * Does NOT compile the repository's actual Kotlin classes or verify Android.
 */
fun main() {
    val m = 128
    fun v(x: Double, y: Double = 0.0) = DoubleArray(m).also { it[0] = x; it[1] = y }
    fun dot(x: DoubleArray, y: DoubleArray): Double = x.indices.sumOf { x[it] * y[it] }
    fun norm(x: DoubleArray) = sqrt(dot(x, x))
    fun cosine(x: DoubleArray, y: DoubleArray) = dot(x, y) / (norm(x) * norm(y))
    fun s4Read(q: DoubleArray, keys: List<DoubleArray>, values: List<DoubleArray>): DoubleArray {
        val scores = keys.map { dot(q, it) / sqrt(m.toDouble()) }
        val base = scores.maxOrNull()!!
        val exps = scores.map { exp(it - base) }
        val total = exps.sum()
        return DoubleArray(m) { j -> values.indices.sumOf { i -> exps[i] / total * values[i][j] } }
    }
    fun nextState(z0: DoubleArray, read: DoubleArray) = 0.25 * tanh(z0[0] + read[0])

    // C1: The host adapter ranks candidates by original f rather than S4 q.
    val f = v(1.0)
    val z0 = f.map(::tanh).toDoubleArray()
    val q = z0.map { tanh(-it) }.toDoubleArray() // Wq=-I, norm-admissible.
    val keys = listOf(v(1.0), v(.9,.1), v(.8,-.2), v(.1,1.0), v(-1.0))
    val rawRank = keys.indices.sortedByDescending { cosine(f, keys[it]) }.take(4)
    val s4Rank = keys.indices.sortedByDescending { dot(q, keys[it]) }
    check(4 !in rawRank && s4Rank.first() == 4)
    val allState = nextState(z0, s4Read(q, keys, keys))
    val subsetState = nextState(z0, s4Read(q, rawRank.map(keys::get),rawRank.map(keys::get)))
    check(abs(allState - subsetState) > 0.02)
    println("CASE1_RAW_F_BEFORE_S4_Q=COUNTEREXAMPLE, delta_h=${abs(allState-subsetState)}")

    // C2: Using cosine to limit candidates does not preserve S4 raw-dot order.
    val positiveQ = v(1.0)
    val smallerDot = v(.9,.1)
    val largerDot = v(1.0,1.0)
    check(cosine(positiveQ, smallerDot) > cosine(positiveQ, largerDot))
    check(dot(positiveQ, smallerDot) < dot(positiveQ, largerDot))
    println("CASE2_COSINE_VERSUS_DOT=COUNTEREXAMPLE, cosineA=${cosine(positiveQ,smallerDot)}, cosineB=${cosine(positiveQ,largerDot)}, dotA=${dot(positiveQ,smallerDot)}, dotB=${dot(positiveQ,largerDot)}")

    // C3: A hard top-4 cap silently changes a full-eligible-I S4 aggregation.
    val vals = listOf(v(0.0),v(0.0),v(0.0),v(0.0),v(1.0))
    val fullAggregate = s4Read(positiveQ, keys, vals)[0]
    val top4 = keys.indices.sortedByDescending { dot(positiveQ,keys[it]) }.take(4)
    val shortAggregate = s4Read(positiveQ,top4.map(keys::get),top4.map(vals::get))[0]
    check(4 !in top4 && fullAggregate > 0.0 && shortAggregate == 0.0)
    println("CASE3_TOP4_VERSUS_FULL_ELIGIBLE_SET=COUNTEREXAMPLE, fullR0=$fullAggregate, truncatedR0=$shortAggregate")

    // Source-backed static limit, not a proof of learned representations:
    println("SOURCE_LIMITATION=reference adapter uses the same hit.vector as key and value; Wk/Wv and scope/version compatibility are not integrated")
    println("RESULT=3_INDEPENDENT_NUMERIC_COUNTEREXAMPLES_PASS")
    println("STATUS=PROVEN_LOCAL_ALGEBRA; REPOSITORY_KOTLIN_NOT_COMPILED")
}
