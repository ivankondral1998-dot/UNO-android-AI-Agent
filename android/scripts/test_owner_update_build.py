#!/usr/bin/env python3
"""Offline host regression for the owner-only APK update pipeline; NO signing or Android."""
import contextlib
import hashlib
import importlib.util
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name("owner_update_build.py")
spec = importlib.util.spec_from_file_location("owner_update_build", SOURCE)
owner = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = owner
spec.loader.exec_module(owner)
Old = owner.ApkIdentity
A = "a" * 64
B = "b" * 64


class OwnerUpdateBuildTest(unittest.TestCase):
    def test_keytool_colon_sha256(self):
        encoded = ":".join(A[i:i+2].upper() for i in range(0, 64, 2))
        self.assertEqual(owner.keytool_digest("SHA1: 00\n SHA256: " + encoded + "\n"), A)

    def test_keytool_rejects_missing_duplicate_or_invalid(self):
        for output in ("NO CERT", "SHA256: broken", "SHA256: " + A + "\nSHA256: " + B):
            with self.subTest(output=output[:20]), self.assertRaises(ValueError):
                owner.keytool_digest(output)

    def test_matching_canonical_increase(self):
        owner.validate_plan(Old("org.unovyra.uno.scaffold", 1, (A,)), 2, A)

    def test_matching_prior_ci_package_cannot_change_identity(self):
        owner.validate_plan(Old("org.unovyra.uno.scaffold.ci42670625565", 7, (A,)), 8, A)

    def test_reject_different_projects_and_suffixes(self):
        for package in ("org.evil.app", "org.unovyra.uno", "org.unovyra.uno.scaffold.ciabc",
                        "org.unovyra.uno.scaffold.ci123", "org.unovyra.uno.scaffold.trap"):
            with self.subTest(package=package), self.assertRaises(ValueError):
                owner.validate_plan(Old(package, 1, (A,)), 2, A)

    def test_reject_signer_change_and_multiple_signers(self):
        for signers in ((B,), (A, B), ()):
            with self.subTest(signers=signers), self.assertRaises(ValueError):
                owner.validate_plan(Old("org.unovyra.uno.scaffold", 1, signers), 2, A)

    def test_reject_same_older_and_out_of_range_code(self):
        old = Old("org.unovyra.uno.scaffold", 3, (A,))
        for code in (1, 2, 3, 0, 2147483648):
            with self.subTest(code=code), self.assertRaises(ValueError):
                owner.validate_plan(old, code, A)

    def fake_run(self, baseline: Old, current_key: str, version: int,
                 *, preflight: bool = True, is_ci: bool = False, destination: Path | None = None):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            key = root / "owner-keystore.jks"
            key.write_bytes(b"test fixture, NOT real key")
            baseline_path = root / "installed.apk"
            baseline_path.write_bytes(b"test baseline bytes")
            candidate = root / "app/build/outputs/apk/debug/app-debug.apk"
            candidate.parent.mkdir(parents=True)
            candidate.write_bytes(b"mock signed APK fixture (not real)")
            output = destination if destination is not None else root / "dist"
            env = {
                "UNO_OWNER_UPDATE_KEYSTORE": str(key),
                "UNO_OWNER_UPDATE_STORE_PASSWORD": "dummy",
                "UNO_OWNER_UPDATE_KEY_ALIAS": "dummy",
                "UNO_OWNER_UPDATE_KEY_PASSWORD": "dummy",
                "GITHUB_ACTIONS": "true" if is_ci else "false",
            }
            arguments = ["owner_update_build.py",
                         "--confirmed-installed-baseline-apk", str(baseline_path),
                         "--new-version-code", str(version),
                         "--output-dir", str(output)]
            if preflight:
                arguments.append("--preflight-only")
            newer = Old(baseline.package, version, baseline.signer_sha256)
            with patch.object(owner, "ANDROID", root), \
                 patch.object(owner, "inspect", side_effect=[baseline, newer]), \
                 patch.object(owner, "command", return_value="SHA256: " + current_key) as cmd, \
                 patch.dict(os.environ, env), \
                 patch.object(sys, "argv", arguments), \
                 contextlib.redirect_stdout(io.StringIO()) as standard, \
                 contextlib.redirect_stderr(io.StringIO()) as errors:
                result = owner.main()
                text = standard.getvalue() + errors.getvalue()
                files = list(output.glob("*")) if output.exists() else []
                return result, text, files, cmd.call_args_list

    def test_local_preflight_does_not_build_or_install(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        code, out, files, calls = self.fake_run(old, A, 2)
        self.assertEqual(code, 0)
        self.assertIn("OWNER_UPDATE_PREFLIGHT_PASS", out)
        self.assertIn("NO_BUILD_NO_INSTALL", out)
        self.assertEqual(files, [])
        self.assertEqual(len(calls), 1)  # keytool only

    def test_wrong_signer_fails_before_gradle(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        code, out, files, calls = self.fake_run(old, B, 2, preflight=False)
        self.assertEqual(code, 1)
        self.assertIn("LOCAL_KEY_DOES_NOT_MATCH", out)
        self.assertEqual(files, [])
        self.assertEqual(len(calls), 1)

    def test_ci_cannot_build_owner_signed_update(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        code, out, files, calls = self.fake_run(old, A, 2, preflight=False, is_ci=True)
        self.assertEqual(code, 1)
        self.assertIn("OWNER_SIGNING_IS_LOCAL_ONLY_NOT_CI", out)
        self.assertEqual(len(calls), 0)

    def test_no_secret_is_sent_as_command_argument(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        code, out, files, calls = self.fake_run(old, A, 2, preflight=False)
        self.assertEqual(code, 0, out)
        self.assertEqual(len(files), 2)  # versioned signed APK and JSON evidence
        self.assertTrue(any(x.suffix == ".apk" for x in files))
        self.assertTrue(any(x.suffix == ".json" for x in files))
        combined = " ".join(str(arg) for call in calls for arg in call.args[0])
        self.assertNotIn("dummy", combined)
        self.assertIn("-storepass:env", combined)
        self.assertIn("-PunoOwnerUpdateApplicationId=org.unovyra.uno.scaffold", combined)
        self.assertNotIn("-PunoIsolatedDebugSuffix", combined)

    def test_signed_apk_mismatch_is_blocked(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        with patch.object(owner, "evaluate", return_value=(False, "CHANGED_CERTIFICATE")):
            code, out, files, calls = self.fake_run(old, A, 2, preflight=False)
        self.assertEqual(code, 1)
        self.assertIn("BUILT_APK_UPDATE_GATE_FAIL", out)
        self.assertEqual(files, [])


    def test_existing_artifact_is_preserved_and_update_blocked(self):
        old = Old("org.unovyra.uno.scaffold", 1, (A,))
        digest = hashlib.sha256(b"mock signed APK fixture (not real)").hexdigest()
        name = "uno-update-" + old.package + "-v2-" + digest[:12] + ".apk"
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / name
            target.write_bytes(b"preserve previous owner's signed file")
            code, out, files, calls = self.fake_run(
                old, A, 2, preflight=False, destination=Path(td))
            self.assertEqual(code, 1)
            self.assertIn("OUTPUT_ALREADY_EXISTS_NO_OVERWRITE", out)
            self.assertEqual(target.read_bytes(), b"preserve previous owner's signed file")
            self.assertEqual(len(files), 1)

    def test_source_blocks_ci_suffix_and_uses_local_signer(self):
        build = (SOURCE.parents[1] / "app/build.gradle.kts").read_text(encoding="utf-8")
        for required in (
            'require(!ownerUpdateRequested || isolatedSuffix == null)',
            'signingConfigs.create("unoOwnerUpdate")',
            'signingConfig = signingConfigs.getByName("unoOwnerUpdate")',
            'providers.environmentVariable("UNO_OWNER_UPDATE_KEYSTORE")',
            'providers.environmentVariable("GITHUB_ACTIONS")',
        ):
            with self.subTest(marker=required):
                self.assertIn(required, build)


if __name__ == "__main__":
    unittest.main(verbosity=2)
