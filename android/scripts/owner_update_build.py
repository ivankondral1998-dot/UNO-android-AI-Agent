#!/usr/bin/env python3
"""Build ONE local-only signed UNO lab update from a confirmed installed APK.

Never installs/uninstalls, publishes, uploads or creates signing keys.
The existing installed APK must be independently confirmed on the owner's device;
matching two APK files alone cannot establish actual device state.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from apk_update_gate import ApkIdentity, evaluate, inspect

ANDROID = Path(__file__).resolve().parents[1]
PACKAGE_PATTERN = re.compile(r"org\.unovyra\.uno\.scaffold(?:\.ci[0-9]{5,20})?\Z")
REQUIRED_ENV = (
    "UNO_OWNER_UPDATE_KEYSTORE", "UNO_OWNER_UPDATE_STORE_PASSWORD",
    "UNO_OWNER_UPDATE_KEY_ALIAS", "UNO_OWNER_UPDATE_KEY_PASSWORD",
)


def keytool_digest(output: str) -> str:
    """Read a single SHA256 fingerprint from keytool -list -v (not a private key)."""
    matches = re.findall(r"^\s*SHA256:\s*([0-9A-Fa-f:]+)\s*$", output, re.M)
    digests = [match.replace(":", "").lower() for match in matches]
    if len(digests) != 1 or not re.fullmatch(r"[0-9a-f]{64}", digests[0]):
        raise ValueError("KEYSTORE_SIGNER_FINGERPRINT_UNREADABLE")
    return digests[0]


def validate_plan(old: ApkIdentity, new_code: int, keystore_sha256: str) -> None:
    if not PACKAGE_PATTERN.fullmatch(old.package):
        raise ValueError("BASELINE_NOT_A_RECOGNIZED_UNO_LAB_PACKAGE")
    if new_code <= old.version_code or not 2 <= new_code <= 2_147_483_647:
        raise ValueError("VERSION_CODE_MUST_INCREASE_IN_ANDROID_INT_RANGE")
    if old.signer_sha256 != (keystore_sha256,):
        raise ValueError("LOCAL_KEY_DOES_NOT_MATCH_INSTALLED_BASELINE_APK_SIGNER")


def command(args: list[str], *, cwd: Path | None = None) -> str:
    # Never include secret values in command arguments; keytool reads password by env name.
    completed = subprocess.run(args, cwd=cwd, capture_output=True,
                               text=True, timeout=900, check=False)
    if completed.returncode != 0:
        raise ValueError("COMMAND_FAILED_" + Path(args[0]).name +
                         "_EXIT_" + str(completed.returncode))
    return completed.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirmed-installed-baseline-apk", type=Path, required=True,
                        help="exact prior APK verified as installed on owner's phone")
    parser.add_argument("--new-version-code", required=True, type=int)
    parser.add_argument("--aapt", default="aapt")
    parser.add_argument("--apksigner", default="apksigner")
    parser.add_argument("--keytool", default="keytool")
    parser.add_argument("--gradle", default="gradle")
    parser.add_argument("--preflight-only", action="store_true",
                        help="compare baseline and local key; do NOT build")
    parser.add_argument("--output-dir", type=Path,
                        default=ANDROID / "dist" / "owner-updates")
    args = parser.parse_args()

    try:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            raise ValueError("OWNER_SIGNING_IS_LOCAL_ONLY_NOT_CI")
        for name in REQUIRED_ENV:
            if not os.environ.get(name):
                raise ValueError("MISSING_LOCAL_SIGNING_ENV_" + name)
        keystore = Path(os.environ["UNO_OWNER_UPDATE_KEYSTORE"]).expanduser().resolve()
        if not keystore.is_file():
            raise ValueError("OWNER_KEYSTORE_FILE_UNAVAILABLE")

        old = inspect(args.confirmed_installed_baseline_apk, args.aapt, args.apksigner)
        keytool_output = command([
            args.keytool, "-J-Duser.language=en", "-list", "-v",
            "-keystore", str(keystore),
            "-alias", os.environ["UNO_OWNER_UPDATE_KEY_ALIAS"],
            "-storepass:env", "UNO_OWNER_UPDATE_STORE_PASSWORD",
        ])
        local_fingerprint = keytool_digest(keytool_output)
        validate_plan(old, args.new_version_code, local_fingerprint)
        print("OWNER_UPDATE_PREFLIGHT_PASS package=" + old.package +
              " old_version=" + str(old.version_code) +
              " new_version=" + str(args.new_version_code))
        print("SIGNER_SHA256=" + local_fingerprint)
        print("BASELINE_INSTALLED_ON_DEVICE_NOT_ATTESTED_BY_THIS_SCRIPT")
        if args.preflight_only:
            print("NO_BUILD_NO_INSTALL")
            return 0

        # No new package suffix: use EXACT existing baseline applicationId.
        # Local Gradle signs debug lab APK using an OWNER-HELD key only.
        command([
            args.gradle, "--no-daemon", "--max-workers=2",
            "-PunoOwnerUpdateApplicationId=" + old.package,
            "-PunoOwnerUpdateVersionCode=" + str(args.new_version_code),
            ":app:assembleDebug", ":app:lintDebug",
        ], cwd=ANDROID)

        candidate = ANDROID / "app/build/outputs/apk/debug/app-debug.apk"
        new = inspect(candidate, args.aapt, args.apksigner)
        accepted, reason = evaluate(old, new)
        if not accepted or new.version_code != args.new_version_code:
            raise ValueError("BUILT_APK_UPDATE_GATE_FAIL_" + reason)

        sha256 = hashlib.file_digest(candidate.open("rb"), "sha256").hexdigest()
        output = args.output_dir.expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        target = output / ("uno-update-" + old.package + "-v" +
                           str(new.version_code) + "-" + sha256[:12] + ".apk")
        record = target.with_suffix(".json")
        if target.exists() or record.exists():
            raise ValueError("OUTPUT_ALREADY_EXISTS_NO_OVERWRITE")
        # Never replace prior artifacts; 'xb' fails on existing file.
        with candidate.open("rb") as src, target.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        evidence = {
            "schema": "UNO_LOCAL_OWNER_UPDATE/1",
            "status": "APK_IDENTITY_MATCHES_BASELINE_FILES_ONLY",
            "package": new.package,
            "old_version_code": old.version_code,
            "new_version_code": new.version_code,
            "signer_sha256": list(new.signer_sha256),
            "new_apk_sha256": sha256,
            "device_install_tested": False,
            "actual_baseline_installed_on_device_attested": False,
            "owner_key_held_only_locally": True,
            "native_model_or_action_acceptance": False,
        }
        with record.open("x", encoding="utf-8") as stream:
            json.dump(evidence, stream, indent=2, sort_keys=True)
            stream.write("\n")
        print("SIGNED_OWNER_LAB_UPDATE_FILES_CREATED=" + str(target))
        print("EVIDENCE_FILE=" + str(record))
        print("APK_SHA256=" + sha256)
        print("NO_INSTALL_NO_UNINSTALL_NO_PUBLISH")
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        # Errors must never include key passwords or gradle environment dumps.
        print("OWNER_UPDATE_BLOCKED " + type(exc).__name__ + " " + str(exc),
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
