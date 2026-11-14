package uno.research
import kotlin.math.abs
import kotlin.system.measureNanoTime
/** Host microbenchmark only. Not a trained model or phone energy test. */
object WeightKernelBenchmark {
 fun dense(w:FloatArray,x:FloatArray,n:Int):FloatArray {
  val y=FloatArray(n)
  for(i in 0 until n){var s=0f;for(j in 0 until n)s+=w[i*n+j]*x[j];y[i]=s}
  return y
 }
 fun factor(a:FloatArray,b:FloatArray,x:FloatArray,n:Int,r:Int):FloatArray {
  val t=FloatArray(r)
  for(k in 0 until r){var s=0f;for(j in 0 until n)s+=b[k*n+j]*x[j];t[k]=s}
  val y=FloatArray(n)
  for(i in 0 until n){var s=0f;for(k in 0 until r)s+=a[i*r+k]*t[k];y[i]=s}
  return y
 }
 @JvmStatic fun main(args:Array<String>){
  val n=args.getOrNull(0)?.toIntOrNull()?:256
  val r=args.getOrNull(1)?.toIntOrNull()?:32
  require(n in 16..2048 && r in 1..n)
  val a=FloatArray(n*r){((it*13L%101).toFloat()-50f)/(100f*r)}
  val b=FloatArray(r*n){((it*17L%97).toFloat()-48f)/100f}
  val x=FloatArray(n){(it%31-15)/31f}
  val w=FloatArray(n*n)
  for(i in 0 until n)for(j in 0 until n){var s=0f;for(k in 0 until r)s+=a[i*r+k]*b[k*n+j];w[i*n+j]=s}
  val yd=dense(w,x,n);val yr=factor(a,b,x,n,r)
  val error=yd.indices.maxOf{abs(yd[it]-yr[it])}
  check(error<0.0001f)
  var sink=0.0
  repeat(500){sink+=dense(w,x,n)[it%n]+factor(a,b,x,n,r)[it%n]}
  val count=2000
  val td=measureNanoTime{repeat(count){sink+=dense(w,x,n)[it%n]}}/count
  val tr=measureNanoTime{repeat(count){sink+=factor(a,b,x,n,r)[it%n]}}/count
  println("HOST_ONLY n="+n+" rank="+r+" error="+error+" dense_params="+(n*n)+" factor_params="+(2*n*r))
  println("dense_ns="+td+" factor_ns="+tr+" ratio="+(td.toDouble()/tr)+" sink="+sink)
  println("NOT full UNO F, not trained, not A52 energy or quality")
 }
}