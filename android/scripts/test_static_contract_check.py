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
<service android:name=".NeuralWorkerService" android:isolatedProcess="true" android:exported="false"/>
</application></manifest>'''
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
    def test_clean_fixture(self): self.assertEqual(guard.scan(self.root), [])
    def test_reject_internet_permission(self):
        self.manifest.write_text(MANIFEST.replace('<application', '<uses-permission android:name="android.permission.INTERNET"/><application'))
        self.assertTrue(any(x.startswith('unexpected_permission:') for x in guard.scan(self.root)))
    def test_reject_sdk23_permission(self):
        self.manifest.write_text(MANIFEST.replace('<application', '<uses-permission-sdk-23 android:name="android.permission.READ_CONTACTS"/><application'))
        self.assertTrue(any(x.startswith('unexpected_permission:') for x in guard.scan(self.root)))
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
    def test_reject_socket_api(self):
        self.code.write_text(CODE + '\nval socket = java.net.Socket("localhost",443)\n')
        self.assertIn('unexpected_api:java.net', guard.scan(self.root))

if __name__=='__main__': unittest.main(verbosity=2)
