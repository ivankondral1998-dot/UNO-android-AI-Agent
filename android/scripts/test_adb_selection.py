"""Deterministic ADB selection tests: no USB device is contacted."""
import unittest
from adb_collect import select_authorized_serial

class AdbSelectionTests(unittest.TestCase):
    def test_one_authorized_device_selected(self):
        raw=b"List of devices attached\nSERIAL_A\tdevice product:mock model:A52\n"
        self.assertEqual(select_authorized_serial(raw), "SERIAL_A")

    def test_multiple_phones_require_explicit_serial(self):
        raw=b"List of devices attached\nSERIAL_A\tdevice\nSERIAL_B\tdevice\n"
        with self.assertRaises(RuntimeError):
            select_authorized_serial(raw)
        self.assertEqual(select_authorized_serial(raw, "SERIAL_B"), "SERIAL_B")

    def test_unauthorized_device_cannot_be_selected(self):
        raw=b"List of devices attached\nSERIAL_A\tunauthorized\n"
        with self.assertRaises(RuntimeError):
            select_authorized_serial(raw)
        with self.assertRaises(RuntimeError):
            select_authorized_serial(raw, "SERIAL_A")

    def test_wrong_explicit_serial_is_rejected(self):
        raw=b"List of devices attached\nSERIAL_A\tdevice\n"
        with self.assertRaises(RuntimeError):
            select_authorized_serial(raw, "SERIAL_B")

if __name__ == "__main__": unittest.main(verbosity=2)
