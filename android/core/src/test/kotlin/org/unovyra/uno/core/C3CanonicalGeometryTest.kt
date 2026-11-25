package org.unovyra.uno.core

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest

object C3CanonicalGeometryTest {
    var pass = 0
    private fun verify(name: String, ok: Boolean) { check(ok) { name }; pass++; println("PASS C3 $name") }
    private fun sha(b: ByteArray) = MessageDigest.getInstance("SHA-256").digest(b).joinToString("") { "%02x".format(it) }
    fun run() {
        val fake = byteArrayOf(42)
        verify("one_byte_legacy_rejected_even_with_matching_digest", admitWeights(
            WeightManifest(UnoAbi.MODEL, 64, 64, 128, 1, sha(fake)), fake, UnoAbi.MODEL) == WeightAdmission.REJECTED)
        for ((d, count) in listOf(512 to 23015887L, 1024 to 55451639L, 1536 to 97340959L, 2048 to 148683847L)) {
            val specs = b2CanonicalInventory(d)
            // Source-generated digest covers every tensor name, dimensions, vector flag and frozen row.
            val sourceDigests = mapOf(512 to "dcf4e38a1d274e8b892b1d682a061df9000df0e8760a129bf4e55f7abbd6daf0",
                1024 to "6e95cb2572683a26def537eacf4fbb4e61d389df560a31c5a88ae3a07d79e9d1",
                1536 to "b266612d5cb96c24c09237da299ce17b62dc994032d8e87b483ede628d46784b",
                2048 to "ddb45426afb6f8efd293d121061580496919c2495aef9b7b5b1f0bf6c2f28352")
            val canonical = specs.joinToString("\n", postfix="\n") {
                "${it.name}|${it.shape.joinToString(",")}|${it.box}|${it.frozenRows.sorted().joinToString(",")}" }
            verify("source_tensor_inventory_$d", sha(canonical.toByteArray(Charsets.UTF_8)) == sourceDigests.getValue(d))
            verify("inventory_$d", specs.sumOf { it.elements } == count && specs.size == 38 + 10*d/64 &&
                specs.sumOf { it.frozenRows.size.toLong() * it.shape.getOrElse(1) { 1 } } == 318L * (d+1))
        }
        // Synthetic smallest paper candidate; not an architecture decision.
        val regions = mutableListOf<CanonicalFP32Region>()
        var pos = 0L
        for (spec in b2CanonicalInventory(512)) {
            regions += CanonicalFP32Region(spec.name, spec.shape, pos, spec.elements*4L)
            pos += spec.elements*4L
        }
        val data = ByteArray(pos.toInt())
        val little = ByteOrder.LITTLE_ENDIAN
        val b = ByteBuffer.wrap(data).order(little)
        val zeroSha = sha(data)
        fun checkData(rs: List<CanonicalFP32Region> = regions, digest: String = sha(data), d: Int = 512) =
            validateB2CanonicalFP32(data, d, digest, rs, little) == CanonicalGeometry.VALIDATED_CANDIDATE
        verify("complete_zero_candidate_geometry_not_runtime_admission", checkData())
        verify("wrong_digest", !checkData(digest="0".repeat(64)))
        verify("unapproved_width", !checkData(d=64))
        verify("missing_tensor", !checkData(regions.dropLast(1)))
        verify("duplicate_tensor", !checkData(regions.dropLast(1)+regions.first()))
        verify("same_count_wrong_shape", !checkData(regions.mapIndexed { i,r -> if(i==0) r.copy(shape=r.shape.reversed()) else r }))
        verify("overlap", !checkData(regions.mapIndexed { i,r -> if(i==1) r.copy(offset=r.offset-4) else r }))
        verify("hole", !checkData(regions.mapIndexed { i,r -> if(i==1) r.copy(offset=r.offset+4) else r }))
        verify("wrong_length", !checkData(regions.mapIndexed { i,r -> if(i==1) r.copy(byteLength=r.byteLength-4) else r }))
        verify("truncated_payload", validateB2CanonicalFP32(fake,512,sha(fake),regions,little)==CanonicalGeometry.REJECTED)
        fun at(name:String,row:Int=0,col:Int=0):Int {
            val r=regions.single { it.name==name };return (r.offset+4L*(row*r.shape.getOrElse(1){1}+col)).toInt()
        }
        fun put(name:String,v:Float,row:Int=0,col:Int=0) { b.putFloat(at(name,row,col),v) }
        put("E_text",Float.NaN);verify("nonfinite_nan",!checkData());put("E_text",0f)
        put("E_text",Float.POSITIVE_INFINITY);verify("nonfinite_inf",!checkData());put("E_text",0f)
        put("E_text",8f);put("E_text",Float.MIN_VALUE,col=1)
        verify("exact_row_cap_not_rounded_down",!checkData());put("E_text",0f);put("E_text",0f,col=1)
        put("U_s",0.75f);put("U_s",0.5f,col=1);verify("row_l1_not_individual_elements",!checkData());put("U_s",0f);put("U_s",0f,col=1)
        put("e_modality",1.0000001f);verify("modality_box_cap",!checkData());put("e_modality",0f)
        put("F.0.0.B",0.9f);put("F.0.0.B",Math.scalb(1.0f,-25),col=1)
        verify("B_row_real_point_nine_cap",!checkData());put("F.0.0.B",0f);put("F.0.0.B",0f,col=1)
        put("W_verb",Float.MIN_VALUE,row=24);verify("frozen_verb_row",!checkData());put("W_verb",0f,row=24)
        put("b_outcome",0.125f,row=2);verify("frozen_endpoint_bias",!checkData());put("b_outcome",0f,row=2)
        verify("fixture_restored",sha(data)==zeroSha)
        put("U_s",1f);put("F.0.0.B",0.9f);put("W_verb",0.25f,row=23);put("b_outcome",0.5f,row=3)
        verify("valid_boundary_nonzero_candidate",checkData())
        // Small isolated, untrained numeric fixtures; no new ABI or model admission.
        val mat=B2CanonicalTensor("synthetic",listOf(1,2),false,1.0)
        val fp16Ok=CanonicalGeometry.VALIDATED_CANDIDATE
        fun half(vararg x:Int)=x.map{it.toShort()}.toShortArray()
        fun h(spec:B2CanonicalTensor,vararg x:Int)=validateB2DecodedFP16Tensor(spec,half(*x))==fp16Ok
        verify("FP16_exact_cap",h(mat,0x3800,0xb800)) // +0.5 and -0.5
        verify("FP16_cap_plus_min_subnormal_rejected",!h(mat,0x3c00,0x0001))
        verify("FP16_nonfinite_inf_nan",!h(mat,0x7c00,0) && !h(mat,0,0xfe00))
        verify("FP16_frozen_zero_only",h(mat.copy(frozenRows=setOf(0)),0,0x8000) &&
            !h(mat.copy(frozenRows=setOf(0)),0,0x0001))
        verify("FP16_box_not_row_l1",h(mat.copy(box=true),0x3c00,0xbc00))
        verify("FP16_wrong_shape",!h(mat,0x3800))
        // Source Astra tests/boundaries.py: normalize [1, .51/127], round
        // to int8 [127,1] with max/127 scale. The decoded real norm exceeds 1.
        val witnessScale=(1.0/(1.0+0.51/127.0)/127.0).toFloat()
        fun q(spec:B2CanonicalTensor, values:ByteArray, scales:FloatArray)=
            validateB2DecodedINT8Matrix(spec,values,scales)==fp16Ok
        verify("INT8_Astra_rounding_counterexample_rejected",!q(mat,byteArrayOf(127,1),floatArrayOf(witnessScale)))
        verify("INT8_signed_abs_sum_exact_cap",q(mat,byteArrayOf(64,-64),floatArrayOf(1f/128)))
        verify("INT8_exact_scale_one_ulp_above_cap",!q(mat,byteArrayOf(64,-64),floatArrayOf(Math.nextUp(1f/128))))
        // Exact q*scale norm <=1, but independently rounded FP32 products exceed 1.
        val roundedScale=1f/116
        verify("INT8_individual_FP32_decode_rounding_checked",116.0*roundedScale.toDouble()<=1.0 &&
            (114f*roundedScale).toDouble()+(2f*roundedScale).toDouble()>1.0 &&
            !q(mat,byteArrayOf(114,2),floatArrayOf(roundedScale)))
        verify("INT8_negative_128_not_wrapped",!q(mat,byteArrayOf(-128,1),floatArrayOf(1f/128)))
        verify("INT8_invalid_scale",listOf(0f,-1f,Float.NaN,Float.POSITIVE_INFINITY).all{
            !q(mat,byteArrayOf(0,0),floatArrayOf(it))})
        verify("INT8_frozen_row",q(mat.copy(frozenRows=setOf(0)),byteArrayOf(0,0),floatArrayOf(1f)) &&
            !q(mat.copy(frozenRows=setOf(0)),byteArrayOf(0,1),floatArrayOf(Float.MIN_VALUE)))
        verify("INT8_layout_and_box_checks",!q(mat,byteArrayOf(1),floatArrayOf(1f)) &&
            !q(mat,byteArrayOf(0,0),floatArrayOf()) && !q(mat.copy(box=true),byteArrayOf(0,0),floatArrayOf(1f)))
        verify("INT8_09_decimal_cap",q(mat.copy(cap=0.9),byteArrayOf(1,0),floatArrayOf(0.9f)) &&
            !q(mat.copy(cap=0.9),byteArrayOf(1,0),floatArrayOf(Math.nextUp(0.9f))))
        println("UNO_C3_GEOMETRY_HOST_PASS=$pass")
    }
}
