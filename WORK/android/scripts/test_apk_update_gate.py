import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).with_name('apk_update_gate.py')
spec = importlib.util.spec_from_file_location('update_gate', MODULE)
gate = importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name] = gate
spec.loader.exec_module(gate)
C1 = 'a' * 64
C2 = 'b' * 64


class ApkUpdateGateTest(unittest.TestCase):
    def test_parse_badging(self):
        self.assertEqual(gate.parse_badging("package: name='org.unovyra.uno.scaffold' versionCode='7' versionName='r7'\n"), ('org.unovyra.uno.scaffold', 7))
    def test_reject_bad_badging(self):
        with self.assertRaises(ValueError): gate.parse_badging('no package')
    def test_certificates_from_verifier(self):
        self.assertEqual(gate.parse_certificates('Signer #1 certificate SHA-256 digest: ' + C1 + '\n'), (C1,))
    def test_reject_no_cert(self):
        with self.assertRaises(ValueError): gate.parse_certificates('Unsigned')
    def test_allowed_binary_identity(self):
        old = gate.ApkIdentity('org.unovyra.uno', 1, (C1,))
        new = gate.ApkIdentity('org.unovyra.uno', 2, (C1,))
        self.assertEqual(gate.evaluate(old, new), (True, 'BINARY_UPDATE_IDENTITY_MATCH_DEVICE_STILL_UNVERIFIED'))
    def test_distinct_ci_suffix_blocked(self):
        old = gate.ApkIdentity('org.unovyra.uno.scaffold.ci123', 1, (C1,))
        new = gate.ApkIdentity('org.unovyra.uno.scaffold.ci124', 2, (C1,))
        self.assertFalse(gate.evaluate(old, new)[0])
    def test_changed_signer_blocked(self):
        old = gate.ApkIdentity('org.unovyra.uno', 1, (C1,))
        new = gate.ApkIdentity('org.unovyra.uno', 2, (C2,))
        self.assertFalse(gate.evaluate(old, new)[0])
    def test_non_increasing_version_blocked(self):
        old = gate.ApkIdentity('org.unovyra.uno', 3, (C1,))
        new = gate.ApkIdentity('org.unovyra.uno', 3, (C1,))
        self.assertFalse(gate.evaluate(old, new)[0])


if __name__ == '__main__':
    unittest.main()
