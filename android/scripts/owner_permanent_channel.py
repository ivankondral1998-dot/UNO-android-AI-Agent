#!/usr/bin/env python3
"""One locally held, repeatably updatable UNO Android lab installation.

init: create ONE private, non-replaceable signing identity on the owner's machine.
build: signed v1 or next strictly increasing version; never install or remove apps.
All secrets and resulting APKs stay outside the repository and outside GitHub.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

from apk_update_gate import ApkIdentity, evaluate, inspect
from owner_update_build import keytool_digest

ANDROID = Path(__file__).resolve().parents[1]
APP_ID = "org.unovyra.uno"
ALIAS = "uno_owner"
KEYFILE = "uno-owner-signing.p12"
PASSFILE = "uno-owner-signing.password"
CHANNEL = "channel.json"
RELEASE_PATTERN = re.compile(r"uno-v([1-9][0-9]*)-([0-9a-f]{12})\.(apk|json)\Z")


def fail_on_ci() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").lower() == "true":
        raise ValueError("OWNER_SIGNING_NOT_ALLOWED_IN_GITHUB_ACTIONS")


def owner_path(raw: Path) -> Path:
    if not raw.is_absolute():
        raise ValueError("OWNER_DIRECTORY_MUST_BE_ABSOLUTE")
    resolved = raw.resolve()
    if resolved == ANDROID or ANDROID in resolved.parents:
        raise ValueError("OWNER_DIRECTORY_MUST_BE_OUTSIDE_GIT_REPOSITORY")
    return resolved


def private_file(path: Path, payload: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(payload)
        out.flush()
        os.fsync(out.fileno())
    if os.name != "nt":
        os.chmod(path, 0o600)


def command(argv: list[str], *, env: dict[str, str] | None = None,
            cwd: Path | None = None) -> str:
    # argv never includes the password; keytool reads it by environment name.
    result = subprocess.run(argv, env=env, cwd=cwd, capture_output=True,
                            text=True, timeout=900, check=False)
    if result.returncode:
        raise ValueError("COMMAND_FAILED_" + Path(argv[0]).name +
                         "_EXIT_" + str(result.returncode))
    return result.stdout


def signing_env(folder: Path) -> dict[str, str]:
    password = (folder / PASSFILE).read_text(encoding="ascii").strip()
    if len(password) < 40:
        raise ValueError("SIGNING_PASSWORD_INVALID")
    return {
        **os.environ,
        "UNO_OWNER_UPDATE_KEYSTORE": str(folder / KEYFILE),
        "UNO_OWNER_UPDATE_STORE_PASSWORD": password,
        "UNO_OWNER_UPDATE_KEY_ALIAS": ALIAS,
        "UNO_OWNER_UPDATE_KEY_PASSWORD": password,
    }


def key_digest(folder: Path, env: dict[str, str], keytool: str) -> str:
    text = command([keytool, "-J-Duser.language=en", "-list", "-v",
                    "-keystore", str(folder / KEYFILE), "-alias", ALIAS,
                    "-storepass:env", "UNO_OWNER_UPDATE_STORE_PASSWORD"], env=env)
    return keytool_digest(text)


def init(folder: Path, keytool: str) -> None:
    fail_on_ci()
    if folder.exists():
        raise ValueError("OWNER_CHANNEL_DIRECTORY_ALREADY_EXISTS_NO_REKEY")
    folder.mkdir(mode=0o700)
    if os.name != "nt":
        os.chmod(folder, 0o700)
    password = secrets.token_urlsafe(48)
    private_file(folder / PASSFILE, (password + "\n").encode("ascii"))
    env = signing_env(folder)
    command([keytool, "-genkeypair", "-noprompt", "-alias", ALIAS,
             "-keystore", str(folder / KEYFILE), "-storetype", "PKCS12",
             "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000",
             "-dname", "CN=UNO Owner Local, OU=UNOVYRA, O=UNOVYRA",
             "-storepass:env", "UNO_OWNER_UPDATE_STORE_PASSWORD",
             "-keypass:env", "UNO_OWNER_UPDATE_KEY_PASSWORD"], env=env)
    if os.name != "nt":
        os.chmod(folder / KEYFILE, 0o600)
    digest = key_digest(folder, env, keytool)
    record = {"schema": "UNO_OWNER_CHANNEL/1", "application_id": APP_ID,
              "signer_sha256": digest, "alias": ALIAS,
              "key_is_only_local": True, "no_existing_installation_migrated": True}
    private_file(folder / CHANNEL, (json.dumps(record, sort_keys=True, indent=2) + "\n").encode())
    print("UNO_OWNER_CHANNEL_CREATED package=" + APP_ID)
    print("PUBLIC_SIGNER_SHA256=" + digest)
    print("NO_APK_BUILT_NO_INSTALL_NO_OLD_APP_REMOVED")
    print("BACKUP_REQUIRED: keep whole owner directory securely; its loss prevents future updates")


def load_channel(folder: Path, keytool: str) -> tuple[dict, dict]:
    if not folder.is_dir() or not (folder / KEYFILE).is_file():
        raise ValueError("OWNER_CHANNEL_UNAVAILABLE")
    data = json.loads((folder / CHANNEL).read_text(encoding="utf-8"))
    if (data.get("schema") != "UNO_OWNER_CHANNEL/1" or
            data.get("application_id") != APP_ID or
            not re.fullmatch(r"[0-9a-f]{64}", data.get("signer_sha256", ""))):
        raise ValueError("OWNER_CHANNEL_METADATA_INVALID")
    env = signing_env(folder)
    if key_digest(folder, env, keytool) != data["signer_sha256"]:
        raise ValueError("OWNER_SIGNING_KEY_DOES_NOT_MATCH_CHANNEL")
    return data, env


def last_release(folder: Path, signer: str, aapt: str, apksigner: str):
    releases = folder / "releases"
    if not releases.exists():
        return None
    if not releases.is_dir():
        raise ValueError("RELEASE_DIRECTORY_NOT_A_DIRECTORY")
    pairs: dict[tuple[int, str], set[str]] = {}
    for entry in releases.iterdir():
        match = RELEASE_PATTERN.fullmatch(entry.name)
        if not match or not entry.is_file():
            raise ValueError("UNKNOWN_OR_INCOMPLETE_RELEASE_ARTIFACT")
        version, short_hash, ext = int(match[1]), match[2], match[3]
        pairs.setdefault((version, short_hash), set()).add(ext)
    if any(ext != {"apk", "json"} for ext in pairs.values()):
        raise ValueError("RELEASE_APK_AND_EVIDENCE_MUST_BOTH_EXIST")
    versions = [v for v, _ in pairs]
    if len(versions) != len(set(versions)) or sorted(versions) != list(range(1, len(versions) + 1)):
        raise ValueError("RELEASE_VERSION_SEQUENCE_INVALID")
    if not pairs:
        return None
    version, short_hash = max(pairs)
    base = releases / f"uno-v{version}-{short_hash}"
    apk = base.with_suffix(".apk")
    evidence = json.loads(base.with_suffix(".json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    if (digest[:12] != short_hash or evidence.get("apk_sha256") != digest or
            evidence.get("version_code") != version):
        raise ValueError("PREVIOUS_RELEASE_INTEGRITY_INVALID")
    previous = inspect(apk, aapt, apksigner)
    if (previous != ApkIdentity(APP_ID, version, (signer,))):
        raise ValueError("PREVIOUS_RELEASE_SIGNER_OR_PACKAGE_INVALID")
    return previous


def build(folder: Path, keytool: str, gradle: str, aapt: str, apksigner: str) -> None:
    fail_on_ci()
    data, env = load_channel(folder, keytool)
    old = last_release(folder, data["signer_sha256"], aapt, apksigner)
    version = 1 if old is None else old.version_code + 1
    if version > 2_147_483_647:
        raise ValueError("ANDROID_VERSION_CODE_EXHAUSTED")
    command([gradle, "--no-daemon", "--max-workers=2",
             "-PunoOwnerUpdateApplicationId=" + APP_ID,
             "-PunoOwnerUpdateVersionCode=" + str(version),
             ":app:assembleDebug", ":app:lintDebug"], cwd=ANDROID, env=env)
    candidate = ANDROID / "app/build/outputs/apk/debug/app-debug.apk"
    actual = inspect(candidate, aapt, apksigner)
    if actual != ApkIdentity(APP_ID, version, (data["signer_sha256"],)):
        raise ValueError("CANDIDATE_SIGNING_IDENTITY_OR_VERSION_INVALID")
    if old is not None:
        allowed, reason = evaluate(old, actual)
        if not allowed:
            raise ValueError("NOT_A_SAFE_UPDATE_" + reason)
    digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
    releases = folder / "releases"
    releases.mkdir(mode=0o700, exist_ok=True)
    base = releases / f"uno-v{version}-{digest[:12]}"
    dest = base.with_suffix(".apk")
    record = base.with_suffix(".json")
    if dest.exists() or record.exists():
        raise ValueError("RELEASE_OUTPUT_EXISTS_NO_OVERWRITE")
    with candidate.open("rb") as src, dest.open("xb") as dst:
        shutil.copyfileobj(src, dst)
        dst.flush()
        os.fsync(dst.fileno())
    receipt = {"schema": "UNO_SIGNED_LOCAL_APK/1", "package": APP_ID,
               "version_code": version, "signer_sha256": data["signer_sha256"],
               "apk_sha256": digest, "previous_version_code": old.version_code if old else None,
               "device_install_verified": False, "existing_other_package_migrated": False}
    private_file(record, (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode())
    print("UNO_SINGLE_APP_SIGNED_APK=" + str(dest))
    print("VERSION_CODE=" + str(version))
    print("APK_SHA256=" + digest)
    print("NO_INSTALL_NO_UNINSTALL_NO_MIGRATION_NO_PUBLICATION")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["init", "build"])
    parser.add_argument("--owner-dir", required=True, type=Path,
                        help="new persistent PRIVATE folder outside this repository")
    parser.add_argument("--keytool", default="keytool")
    parser.add_argument("--gradle", default="gradle")
    parser.add_argument("--aapt", default="aapt")
    parser.add_argument("--apksigner", default="apksigner")
    args = parser.parse_args()
    try:
        target = owner_path(args.owner_dir)
        if args.operation == "init":
            init(target, args.keytool)
        else:
            build(target, args.keytool, args.gradle, args.aapt, args.apksigner)
        return 0
    except (ValueError, OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print("OWNER_CHANNEL_BLOCKED " + type(exc).__name__ + " " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
