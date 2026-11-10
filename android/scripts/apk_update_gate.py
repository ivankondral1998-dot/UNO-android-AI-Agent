#!/usr/bin/env python3
"""Conservative APK-to-APK update identity gate. NEVER installs or deletes anything.

The baseline APK must be independently verified as the package *actually installed*
on the owner's device. Matching two arbitrary files is not device verification.
"""
import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ApkIdentity:
    package: str
    version_code: int
    signer_sha256: tuple[str, ...]


def parse_badging(output: str) -> tuple[str, int]:
    match = re.search(r"^package: name='([^']+)' versionCode='([0-9]+)'", output, re.M)
    if not match or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.]*', match.group(1)):
        raise ValueError('UNREADABLE_PACKAGE_OR_VERSION')
    return match.group(1), int(match.group(2))


def parse_certificates(output: str) -> tuple[str, ...]:
    values = re.findall(r'^Signer #\d+ certificate SHA-256 digest:\s*([0-9A-Fa-f:]+)\s*$', output, re.M)
    cleaned = tuple(v.replace(':', '').lower() for v in values)
    if not cleaned or any(not re.fullmatch(r'[0-9a-f]{64}', v) for v in cleaned):
        raise ValueError('MISSING_OR_INVALID_APK_SIGNER_DIGEST')
    return tuple(sorted(cleaned))


def evaluate(old: ApkIdentity, new: ApkIdentity) -> tuple[bool, str]:
    if old.package != new.package:
        return False, 'DIFFERENT_APPLICATION_ID_WOULD_INSTALL_SIDE_BY_SIDE'
    if old.signer_sha256 != new.signer_sha256:
        return False, 'SIGNING_CERTIFICATE_MISMATCH_UPDATE_WILL_FAIL'
    if new.version_code <= old.version_code:
        return False, 'VERSION_CODE_MUST_INCREASE'
    return True, 'BINARY_UPDATE_IDENTITY_MATCH_DEVICE_STILL_UNVERIFIED'


def inspect(apk: Path, aapt: str, apksigner: str) -> ApkIdentity:
    if not apk.is_file():
        raise ValueError('APK_NOT_FOUND')
    def call(cmd: list[str]) -> str:
        return subprocess.run(cmd, check=True, capture_output=True,
                              text=True, timeout=30).stdout
    package, version = parse_badging(call([aapt, 'dump', 'badging', str(apk)]))
    certs = parse_certificates(call([apksigner, 'verify', '--print-certs', str(apk)]))
    return ApkIdentity(package, version, certs)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--installed-baseline-apk', required=True, type=Path)
    p.add_argument('--candidate-apk', required=True, type=Path)
    p.add_argument('--aapt', default='aapt')
    p.add_argument('--apksigner', default='apksigner')
    args = p.parse_args()
    try:
        old = inspect(args.installed_baseline_apk, args.aapt, args.apksigner)
        new = inspect(args.candidate_apk, args.aapt, args.apksigner)
        ok, reason = evaluate(old, new)
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print('APK_UPDATE_GATE_FAIL', type(exc).__name__, str(exc), file=sys.stderr)
        return 1
    print('APK_UPDATE_GATE_PASS' if ok else 'APK_UPDATE_GATE_FAIL', reason)
    print(f'old={old.package} versionCode={old.version_code} new={new.package} versionCode={new.version_code}')
    print('NO_INSTALL_PERFORMED; NO_DEVICE_STATE_ASSERTED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
