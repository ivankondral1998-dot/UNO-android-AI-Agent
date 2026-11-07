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
    def test_reject_socket_api(self):
        self.code.write_text(CODE + '\nval socket = java.net.Socket("localhost",443)\n')
        self.assertIn('unexpected_api:java.net', guard.scan(self.root))

if __name__=='__main__': unittest.main(verbosity=2)
