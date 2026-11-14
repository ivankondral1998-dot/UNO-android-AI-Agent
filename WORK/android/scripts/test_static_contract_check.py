import importlib.util
from pathlib import Path
import tempfile
import unittest

GUARD = Path(__file__).with_name('static_contract_check.py')
spec = importlib.util.spec_from_file_location('guard', GUARD)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

MANIFEST = '''<manifest xmlns:android="http://schemas.android.com/apk/res/android">
<application android:allowBackup="false" android:fullBackupContent="false" android:usesCleartextTraffic="false">
<activity android:name=".UnoActivity" android:exported="true"/>
<activity android:name=".UnoChatActivity" android:exported="false"/>
<activity android:name=".UnoFactsActivity" android:exported="false"/>
<service android:name=".NeuralWorkerService" android:isolatedProcess="true" android:exported="false"/>
</application></manifest>'''
FACTS = '''package org.unovyra.uno
val inspect = UnoAndroidExactMemory(applicationContext, readOnly = true)
val result = UnoManualFacts.recall(memory, scope, k, SystemClock.elapsedRealtimeNanos())
fun factsSave() {
    check(!UnoProcessStop.isStopped())
    AlertDialog.Builder(this).setPositiveButton("Сохранить") { _, _ ->
        UnoManualFacts.remember(memory, scope, k, v)
    }
}
fun factsForget() {
    check(!UnoProcessStop.isStopped())
    AlertDialog.Builder(this).setPositiveButton("Забыть") { _, _ ->
        UnoManualFacts.forgetAll(memory, scope)
    }
}
'''
ADAPTER = '''package org.unovyra.uno
private val readOnly: Boolean = false
val policy = "EXACT_READONLY_SNAPSHOT_UNAVAILABLE"
val create = "initializeEmptyOnFirstOpen = !hasSnapshot && !readOnly"
val rejectWrite = "EXACT_READONLY_WRITE_DENIED"
val rejectRevoke = "EXACT_READONLY_REVOKE_DENIED"
val rejectBackup = "EXACT_READONLY_PENDING_RECOVERY"
val reader = FileInputStream(base)
'''

CODE = '''package org.unovyra.uno
val controller = TrustController(DenyAllAndroidPort(), DenyAllLedger())
val neural = NoWeightsNeuralPort()
fun onPause() { labStop.stop(); controller.stop() }
val stress=LabProfile.STRESS
// Minimal static fixture for the current diagnostic UI markers.
val copyableReport: String? = "{}"
fun copyFullReport() = ClipData.newPlainText("UNO", copyableReport)
button("Проверить SQLite (без создания базы)") { }
button("Проверить владельца через экран Android") { }
val identity = "УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName"
// Fixture markers: both OS callback and one-shot button update nearby feedback.
root.addView(ownerFeedback)
fun runAppPrivateEffectProbe() {
    val outcome = AppPrivateReadbackProbe.run(filesDir)
    val inspect = AppPrivateReadbackProbe.inspect(filesDir, outcome.id)
}
button("СОЗДАТЬ ТЕСТОВЫЙ ЛОКАЛЬНЫЙ МАРКЕР") { runAppPrivateEffectProbe() }
fun inspectLastAppPrivateEffect() = AppPrivateReadbackProbe.inspect(filesDir, id)
button("ПОВТОРНО ПРОЧИТАТЬ ПОСЛЕДНИЙ ЛОКАЛЬНЫЙ МАРКЕР") { inspectLastAppPrivateEffect() }
showOwnerFeedback(if (consumed) "one-use" else "NOOP denied")
showOwnerFeedback(if (accepted) "OS OK" else "OS cancelled")
private fun runSimple(withCpu: Boolean) { DeviceProbe.persist(applicationContext, json) }
button("ЗАПИСАТЬ СНИМОК В ПАМЯТЬ UNO · отдельное согласие") { confirmExactObservation() }
private fun confirmExactObservation() {
    AlertDialog.Builder(this).setPositiveButton("Сохранить") { _, _ -> runExactObservationWithConsent() }
}
fun runExactObservationWithConsent() {
    val reportBytes = snapshot.toString(2).toByteArray(Charsets.UTF_8)
    DeviceProbe.persistImmutable(applicationContext, json)
    observeDeviceSnapshot(json)
}
button("ПРОВЕРИТЬ ЗАПИСЬ ПАМЯТИ ПОСЛЕ ПЕРЕЗАПУСКА") { inspectLastExactObservation() }
private fun inspectLastExactObservation() {
    val exactResult = UnoAndroidExactMemory(applicationContext, readOnly = true).read(1)
    if (read.status != ExactStatus.COMPLETE) "EXACT_" + read.status.name
    val sourceFile = "diagnostics/observation-${digest!!}.json"
    val success = "SAME_BOOT_EXACT_AND_SOURCE_MATCH"
    val json = JSONObject().put("new_vault_write_performed", false)
}
// Single-click read-only consolidated diagnostics, separate from explicit consent.
val advancedContainer = object { val visibility = 0 }
val advancedVisible = advancedContainer.visibility
button("ПРОВЕРИТЬ UNO · ОДИН ТЕСТ") { runUnifiedSelfTest() }
private fun runUnifiedSelfTest() {
    val lab = DeviceLab.run(applicationContext, LabProfile.QUICK, stop)
    val exact = buildExactObservationReadback()
    val verdicts = listOf("PASS")
    val stoppedNow = stop.isStopped()
    val summary = UnoDiagnosticEvaluator.summarize(verdicts, stoppedNow)
    val record = JSONObject().put("status", summary.status).put("stop_requested", stoppedNow)
    val classified = when (code) {
        "EXACT_DENIED" -> "DENIED"
        "EXACT_NOT_FOUND", "EXACT_UNKNOWN", "EXACT_TRUNCATED", "EXACT_CONFLICT" -> "UNKNOWN"
        else -> "NOT_RUN"
    }
}
private fun runSensorInventory() {}
fun saveLocator() {
    prefs.edit().putString("last_event_key", eventKey)
        .putString("last_diagnostic_sha256", originalDigest).commit()
}
button("ОТОЗВАТЬ ДАННЫЕ ПАМЯТИ СНИМКОВ · отдельное подтверждение") { confirmExactRevocation() }
fun confirmExactRevocation() {
    AlertDialog.Builder(this).setPositiveButton("Отозвать раздел") { _, _ -> revokeExactObservations() }
}
'''


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.manifest=self.root/'app/src/main/AndroidManifest.xml'
        self.code=self.root/'app/src/main/kotlin/org/unovyra/uno/UnoActivity.kt'
        self.manifest.parent.mkdir(parents=True)
        self.code.parent.mkdir(parents=True)
        self.manifest.write_text(MANIFEST)
        self.code.write_text(CODE)
        self.adapter = self.code.with_name("UnoAndroidExactMemory.kt")
        self.adapter.write_text(ADAPTER)
        self.facts = self.code.with_name("UnoFactsActivity.kt")
        self.facts.write_text(FACTS)
    def test_clean_fixture(self): self.assertEqual(guard.scan(self.root), [])
    def test_reject_internet_permission(self):
        self.manifest.write_text(MANIFEST.replace('<application', '<uses-permission android:name="android.permission.INTERNET"/><application'))
        self.assertTrue(any(x.startswith('unexpected_permission:') for x in guard.scan(self.root)))
    def test_reject_sdk23_permission(self):
        self.manifest.write_text(MANIFEST.replace('<application', '<uses-permission-sdk-23 android:name="android.permission.READ_CONTACTS"/><application'))
        self.assertTrue(any(x.startswith('unexpected_permission:') for x in guard.scan(self.root)))
    def test_reject_exported_chat(self):
        self.manifest.write_text(MANIFEST.replace(
            '<activity android:name=".UnoChatActivity" android:exported="false"/>',
            '<activity android:name=".UnoChatActivity" android:exported="true"/>'))
        self.assertIn('unsafe_chat_activity', guard.scan(self.root))
    def test_reject_chat_intent_filter(self):
        self.manifest.write_text(MANIFEST.replace(
            '<activity android:name=".UnoChatActivity" android:exported="false"/>',
            '<activity android:name=".UnoChatActivity" android:exported="false">'
            '<intent-filter><action android:name="android.intent.action.VIEW"/></intent-filter></activity>'))
        self.assertIn('unsafe_chat_activity', guard.scan(self.root))
    def test_reject_extra_activity(self):
        self.manifest.write_text(MANIFEST.replace(
            '</application>', '<activity android:name=".Unreviewed" android:exported="true"/></application>'))
        self.assertIn('unexpected_activity_catalog', guard.scan(self.root))
    def test_reject_missing_chat_activity(self):
        self.manifest.write_text(MANIFEST.replace(
            '<activity android:name=".UnoChatActivity" android:exported="false"/>', ''))
        self.assertIn('unexpected_activity_catalog', guard.scan(self.root))
    def test_reject_exported_facts(self):
        self.manifest.write_text(MANIFEST.replace(
            '<activity android:name=".UnoFactsActivity" android:exported="false"/>',
            '<activity android:name=".UnoFactsActivity" android:exported="true"/>'))
        self.assertIn('unsafe_facts_activity', guard.scan(self.root))
    def test_reject_facts_intent_filter(self):
        self.manifest.write_text(MANIFEST.replace(
            '<activity android:name=".UnoFactsActivity" android:exported="false"/>',
            '<activity android:name=".UnoFactsActivity" android:exported="false">'
            '<intent-filter><action android:name="android.intent.action.VIEW"/></intent-filter></activity>'))
        self.assertIn('unsafe_facts_activity', guard.scan(self.root))
    def test_reject_facts_without_consent(self):
        self.facts.write_text(FACTS.replace('.setPositiveButton("Забыть")',
                                           '.setPositiveButton("Без подтверждения")'))
        self.assertIn('manual_facts_consent_or_readonly_contract_missing', guard.scan(self.root))
    def test_reject_facts_without_readonly(self):
        self.facts.write_text(FACTS.replace(
            'UnoAndroidExactMemory(applicationContext, readOnly = true)',
            'UnoAndroidMemoryOwner.exact(applicationContext)'))
        self.assertIn('manual_facts_consent_or_readonly_contract_missing', guard.scan(self.root))
    def test_reject_exported_worker(self):
        self.manifest.write_text(MANIFEST.replace('android:exported="false"', 'android:exported="true"'))
        self.assertIn('unsafe_neural_worker', guard.scan(self.root))
    def test_reject_backup_enabled(self):
        self.manifest.write_text(MANIFEST.replace('android:allowBackup="false"', 'android:allowBackup="true"'))
        self.assertIn('app_allowBackup_not_false', guard.scan(self.root))
    def test_reject_unreviewed_provider(self):
        self.manifest.write_text(MANIFEST.replace('</application>', '<provider android:name=".Unsafe" android:exported="true"/></application>'))
        self.assertIn('unreviewed_component:provider', guard.scan(self.root))
    def test_reject_placeholder_not_wired(self):
        self.code.write_text(CODE.replace('TrustController(DenyAllAndroidPort(), DenyAllLedger())', 'TrustController(RealAndroidPort(), RealLedger())'))
        self.assertIn('missing_fail_closed_controller_wiring', guard.scan(self.root))
    def test_reject_missing_sqlite_button(self):
        self.code.write_text(CODE.replace("Проверить SQLite (без создания базы)", "Missing SQLite UI"))
        self.assertIn('owner_and_sqlite_diagnostics_missing', guard.scan(self.root))
    def test_reject_missing_clipboard(self):
        self.code.write_text(CODE.replace("ClipData.newPlainText", "MissingClipboardCode"))
        self.assertIn('full_report_clipboard_export_missing', guard.scan(self.root))
    def test_reject_missing_package_identity(self):
        self.code.write_text(CODE.replace("УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName", "No identity"))
        self.assertIn('package_identity_not_displayed', guard.scan(self.root))
    def test_reject_hidden_owner_result_feedback(self):
        self.code.write_text(CODE.replace("root.addView(ownerFeedback)", "globalStatusOnly"))
        self.assertIn('owner_local_result_feedback_missing', guard.scan(self.root))
    def test_reject_hidden_owner_os_callback(self):
        self.code.write_text(CODE.replace("showOwnerFeedback(if (accepted)", "status.text = if (accepted)"))
        self.assertIn('owner_local_result_feedback_missing', guard.scan(self.root))
    def test_reject_missing_app_private_effect(self):
        self.code.write_text(CODE.replace("AppPrivateReadbackProbe.run(filesDir)", "UNSAFE_STUB"))
        self.assertIn('app_private_effect_readback_ui_missing', guard.scan(self.root))
    def test_reject_missing_independent_reopen(self):
        self.code.write_text(CODE.replace("AppPrivateReadbackProbe.inspect(filesDir, outcome.id)", "NO_REOPEN"))
        self.assertIn('app_private_effect_readback_ui_missing', guard.scan(self.root))
    def test_reject_implicit_exact_memory_recording(self):
        self.code.write_text(CODE.replace(
            'DeviceProbe.persist(applicationContext, json)',
            'observeDeviceSnapshot(json); DeviceProbe.persist(applicationContext, json)'))
        self.assertIn('implicit_exact_memory_write_in_passive_probe', guard.scan(self.root))
    def test_reject_missing_exact_memory_consent(self):
        self.code.write_text(CODE.replace(
            'button("ЗАПИСАТЬ СНИМОК В ПАМЯТЬ UNO · отдельное согласие") { confirmExactObservation() }',
            'button("Bad implicit write") { runExactObservationWithConsent() }'))
        self.assertIn('explicit_exact_observation_consent_missing', guard.scan(self.root))
    def test_reject_missing_owner_revocation_control(self):
        self.code.write_text(CODE.replace(
            '.setPositiveButton("Отозвать раздел") { _, _ -> revokeExactObservations() }',
            '.setPositiveButton("Отозвать раздел") { _, _ -> Unit }'))
        self.assertIn('exact_observation_revocation_control_missing', guard.scan(self.root))
    def test_reject_mismatched_json_digest(self):
        self.code.write_text(CODE.replace(
            'snapshot.toString(2).toByteArray(Charsets.UTF_8)',
            'snapshot.toString().toByteArray(Charsets.UTF_8)'))
        self.assertIn('exact_observation_digest_mismatch', guard.scan(self.root))
    def test_reject_overwritable_provenance_file(self):
        self.code.write_text(CODE.replace(
            'DeviceProbe.persistImmutable(applicationContext, json)',
            'DeviceProbe.persist(applicationContext, json)'))
        self.assertIn('exact_observation_evidence_not_immutable', guard.scan(self.root))
    def test_reject_missing_exact_restart_readback_ui(self):
        self.code.write_text(CODE.replace(
            'button("ПРОВЕРИТЬ ЗАПИСЬ ПАМЯТИ ПОСЛЕ ПЕРЕЗАПУСКА") { inspectLastExactObservation() }',
            'button("NO_RESTART_READBACK") { Unit }'))
        self.assertIn('exact_restart_readback_missing_or_unbounded', guard.scan(self.root))
    def test_reject_unbound_restart_readback_status(self):
        self.code.write_text(CODE.replace(
            'read.status != ExactStatus.COMPLETE', 'read.status != ExactStatus.NOT_FOUND'))
        self.assertIn('exact_restart_readback_missing_or_unbounded', guard.scan(self.root))
    def test_reject_missing_exact_restart_locator(self):
        self.code.write_text(CODE.replace(
            '.putString("last_diagnostic_sha256", originalDigest).commit()',
            '.apply()'))
        self.assertIn('durable_exact_restart_locator_missing', guard.scan(self.root))
    def test_reject_restart_claiming_new_vault_write(self):
        self.code.write_text(CODE.replace(
            '.put("new_vault_write_performed", false)',
            '.put("new_vault_write_performed", true)'))
        self.assertIn('exact_restart_readback_missing_or_unbounded', guard.scan(self.root))
    def test_reject_restart_without_source_digest_path(self):
        self.code.write_text(CODE.replace(
            'diagnostics/observation-${digest!!}.json',
            'diagnostics/probe_latest.json'))
        self.assertIn('exact_restart_readback_missing_or_unbounded', guard.scan(self.root))
    def test_reject_cached_memory_not_disk_reopen(self):
        self.code.write_text(CODE.replace(
            'UnoAndroidExactMemory(applicationContext, readOnly = true).read(',
            'UnoAndroidMemoryOwner.exact(applicationContext).read('))
        self.assertIn('exact_restart_readback_missing_or_unbounded', guard.scan(self.root))
    def test_reject_readonly_adapter_missing(self):
        self.adapter.write_text(ADAPTER.replace(
            'initializeEmptyOnFirstOpen = !hasSnapshot && !readOnly',
            'initializeEmptyOnFirstOpen = !hasSnapshot'))
        self.assertIn('exact_readonly_disk_reopen_contract_missing', guard.scan(self.root))
    def test_reject_readonly_disk_repair_mutation(self):
        self.adapter.write_text(ADAPTER.replace('FileInputStream(base)', 'file.openRead()'))
        self.assertIn('exact_readonly_disk_reopen_contract_missing', guard.scan(self.root))
    def test_reject_missing_unified_one_tap_button(self):
        self.code.write_text(CODE.replace('ПРОВЕРИТЬ UNO · ОДИН ТЕСТ', 'NO TEST'))
        self.assertIn('unified_one_tap_diagnostic_missing', guard.scan(self.root))
    def test_reject_unified_implicit_exact_write(self):
        self.code.write_text(CODE.replace(
            'val exact = buildExactObservationReadback()',
            'runExactObservationWithConsent()\n    val exact = buildExactObservationReadback()'))
        self.assertIn('unified_diagnostic_implicit_privileged_write', guard.scan(self.root))
    def test_reject_unified_owner_auto_credential(self):
        self.code.write_text(CODE.replace(
            'val exact = buildExactObservationReadback()',
            'ownerGate.begin(scope, description)\n    val exact = buildExactObservationReadback()'))
        self.assertIn('unified_diagnostic_implicit_privileged_write', guard.scan(self.root))
    def test_reject_unified_bypassing_verdict_gate(self):
        self.code.write_text(CODE.replace(
            'UnoDiagnosticEvaluator.summarize(verdicts, stoppedNow)',
            'StaleUiStatusAggregator.summarize(verdicts, stoppedNow)'))
        self.assertIn('unified_diagnostic_verdict_gate_missing', guard.scan(self.root))
    def test_reject_unified_marker_autowrite(self):
        self.code.write_text(CODE.replace(
            'val exact = buildExactObservationReadback()',
            'AppPrivateReadbackProbe.run(filesDir)\n    val exact = buildExactObservationReadback()'))
        self.assertIn('unified_diagnostic_implicit_privileged_write', guard.scan(self.root))
    def test_reject_unified_missing_quick_profile(self):
        self.code.write_text(CODE.replace('DeviceLab.run(applicationContext, LabProfile.QUICK, stop)', 'DeviceLab.fake()'))
        self.assertIn('unified_one_tap_diagnostic_missing', guard.scan(self.root))
    def test_reject_expired_memory_as_not_run(self):
        self.code.write_text(CODE.replace(
            '"EXACT_NOT_FOUND", "EXACT_UNKNOWN", "EXACT_TRUNCATED", "EXACT_CONFLICT" -> "UNKNOWN"',
            '"EXACT_NOT_FOUND", "EXACT_UNKNOWN", "EXACT_TRUNCATED", "EXACT_CONFLICT" -> "NOT_RUN"'))
        self.assertIn('unified_exact_memory_status_overclaimed', guard.scan(self.root))
    def test_reject_revocation_denial_as_not_run(self):
        self.code.write_text(CODE.replace('"EXACT_DENIED" -> "DENIED"', '"EXACT_DENIED" -> "NOT_RUN"'))
        self.assertIn('unified_exact_memory_status_overclaimed', guard.scan(self.root))
    def test_reject_socket_api(self):
        self.code.write_text(CODE + '\nval socket = java.net.Socket("localhost",443)\n')
        self.assertIn('unexpected_api:java.net', guard.scan(self.root))

if __name__=='__main__': unittest.main(verbosity=2)
