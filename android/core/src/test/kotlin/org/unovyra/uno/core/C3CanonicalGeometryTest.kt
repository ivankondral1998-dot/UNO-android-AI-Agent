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
        println("UNO_C3_GEOMETRY_HOST_PASS=$pass")
    }
}
