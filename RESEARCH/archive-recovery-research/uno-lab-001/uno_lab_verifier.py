#!/usr/bin/env python3
"""UNO-LAB-001: GitHub-backed, fail-closed, byte-exact G1 replay verifier.

Usage: python3 uno_lab_verifier.py
Requires: GitHub read access via GITHUB_TOKEN, GH_TOKEN, or existing 'gh auth'.
          Python3 + numpy for the fetched research experiment.
No GitHub writes, no weight training, no phone interaction.
"""
from __future__ import annotations

import argparse
import ast
import base64
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

OWNER_REPO = "ivankondral1998-dot/UNO-android-AI-Agent"
BRANCH = "docs/uno-lab-research-handoff-20261105"
FOLDER = "research/uno-lab-001/"
SCRIPT = FOLDER + "grok_lab001_hfix.py"
# This is the *actual* path on GitHub. 'hfix_stdout.txt' is not in the branch.
GOLD = FOLDER + "grok_lab001_hfix_output.txt"
JOURNAL = "UNO_LAB_REPORTS.txt"
API = "https://api.github.com/repos/" + OWNER_REPO

# Specific verified source at the beginning of this independent review.
# The branch can advance; the commit resolved at execution is the snapshot.
EXPECTED_SCRIPT_SHA256 = "b70754f1c39faf564eb8a4fc0f671fbae961f75e56ab9ce9bf14d2757ee5225d"
EXPECTED_GOLD_SHA256 = "cfd5b0bebee162a07907714d10aa14177b09074da02958dfdd5099619947f3a5"


def checksum(buf: bytes) -> str:
    return hashlib.sha256(buf).hexdigest()


def git_blob_sha1(buf: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(buf)).encode("ascii") + b"\0" + buf).hexdigest()


def get_token() -> str:
    direct = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if direct:
        return direct.strip()
    if shutil.which("gh"):
        process = subprocess.run(["gh", "auth", "token"], capture_output=True, timeout=10)
        if process.returncode == 0 and process.stdout.strip():
            return process.stdout.decode("utf-8").strip()
    raise RuntimeError("GitHub auth unavailable: configure GITHUB_TOKEN / GH_TOKEN or 'gh auth login'")


class GitHubSnapshot:
    def __init__(self, token: str):
        self.token = token
        self.commit = ""

    def get_json(self, relative_url: str) -> dict:
        url = API + "/" + relative_url
        request = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + self.token,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "UNO-LAB-byte-verifier/1.0",
        })
        try:
            with urlopen(request, timeout=60) as response:
                return json.loads(response.read())
        except HTTPError as exc:
            raise RuntimeError(f"GitHub HTTP {exc.code} on {relative_url}") from None
        except URLError as exc:
            raise RuntimeError(f"GitHub transport error on {relative_url}: {exc.reason}") from None

    def resolve(self) -> str:
        data = self.get_json("git/ref/heads/" + quote(BRANCH, safe="/"))
        sha = data["object"]["sha"]
        if len(sha) != 40 or any(ch not in "0123456789abcdef" for ch in sha.lower()):
            raise RuntimeError("GitHub returned an invalid commit SHA")
        self.commit = sha
        return sha

    def fetch_file(self, path: str, expected_blob_sha: str | None = None) -> bytes:
        if not self.commit:
            raise RuntimeError("Commit must be resolved first")
        data = self.get_json("contents/" + quote(path, safe="/") + "?" + urlencode({"ref": self.commit}))
        if data.get("type") != "file" or data.get("encoding") != "base64":
            raise RuntimeError(f"Unsupported contents response: {path}")
        try:
            payload = base64.b64decode(data["content"], validate=False)
        except (ValueError, KeyError) as exc:
            raise RuntimeError(f"Invalid GitHub base64 payload for {path}: {exc}") from None
        blob_sha = git_blob_sha1(payload)
        if blob_sha != data.get("sha") or (expected_blob_sha is not None and blob_sha != expected_blob_sha):
            raise RuntimeError(f"Git blob mismatch: {path}")
        if len(payload) != data.get("size"):
            raise RuntimeError(f"Git file length mismatch: {path}")
        return payload

    def tree(self) -> list[dict]:
        data = self.get_json("git/trees/" + self.commit + "?recursive=1")
        if data.get("truncated"):
            raise RuntimeError("GitHub recursive tree was truncated; cannot assert full-branch scan")
        return [o for o in data["tree"] if o.get("type") == "blob"]


def first_diff(actual: bytes, expected: bytes) -> int | None:
    if actual == expected:
        return None
    for i, (a, b) in enumerate(zip(actual, expected)):
        if a != b:
            return i
    return min(len(actual), len(expected))


def replay(script: bytes, expected: bytes, timeout: int, output_dir: Path) -> dict:
    with tempfile.TemporaryDirectory(prefix="uno_lab_001_") as root:
        path = Path(root) / "grok_lab001_hfix.py"
        path.write_bytes(script)
        # Avoid inherited GitHub credentials in untrusted research subprocess.
        child_env = {k: v for k, v in os.environ.items() if not (
            k.endswith("_TOKEN") or k.endswith("_KEY") or k.startswith("GITHUB_")
            or k.startswith("GH_") or k.startswith("AWS_") or k.startswith("AZURE_")
        )}
        child_env.update({
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "PYTHONNOUSERSITE": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        })
        try:
            proc = subprocess.run(
                [sys.executable, "-I", str(path)], cwd=root, env=child_env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            (output_dir / "actual_stdout.bin").write_bytes(exc.stdout or b"")
            (output_dir / "actual_stderr.bin").write_bytes(exc.stderr or b"")
            raise RuntimeError(f"hfix timed out after {timeout}s; captured partial outputs") from None

        (output_dir / "actual_stdout.bin").write_bytes(proc.stdout)
        (output_dir / "actual_stderr.bin").write_bytes(proc.stderr)
        offset = first_diff(proc.stdout, expected)
        verdict = {
            "returncode": proc.returncode,
            "stdout_exact_match": offset is None,
            "first_mismatch_offset": offset,
            "expected_stdout_bytes": len(expected),
            "actual_stdout_bytes": len(proc.stdout),
            "expected_stdout_sha256": checksum(expected),
            "actual_stdout_sha256": checksum(proc.stdout),
            "stderr_bytes": len(proc.stderr),
        }
        if proc.returncode != 0:
            raise RuntimeError(f"hfix exited with code {proc.returncode}; stderr saved to actual_stderr.bin")
        if offset is not None:
            raise RuntimeError(
                f"stdout byte mismatch at offset {offset}; expected {len(expected)}B, got {len(proc.stdout)}B; "
                "actual_stdout.bin and actual_stderr.bin saved"
            )
        if proc.stderr:
            raise RuntimeError("Nonempty research script stderr (saved to actual_stderr.bin)")
        return verdict


# Source files are fetched from every Git tree entry, not from default-branch code search.
# Binary blobs are excluded from *text* inspection and counted as skipped.
TEXT_SUFFIXES = {
    ".py", ".txt", ".md", ".json", ".jsonl", ".yaml", ".yml",
    ".sh", ".kt", ".kts", ".java", ".xml", ".gradle", ".properties",
    ".toml", ".ini", ".cfg", ".ps1", ".gitignore",
}


def inspect_text(path: str, raw: bytes) -> list[dict]:
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise RuntimeError(f"Text-like file is not valid UTF-8: {path}") from None
    issues: list[dict] = []
    for number, line in enumerate(content.splitlines(), 1):
        # Raw text detection, including journal and code; split the needle here so
        # that the checker does not list its own search string as an occurrence.
        needle = "or" + " True"
        if needle in line:
            issues.append({"path": path, "line": number, "kind": "literal_or_true", "text": line.strip()[:180]})
    if path.endswith(".py"):
        try:
            parsed = ast.parse(content, filename=path)
        except SyntaxError as exc:
            issues.append({"path": path, "line": exc.lineno or 0, "kind": "syntax_error", "text": str(exc)})
        else:
            for node in ast.walk(parsed):
                if isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant) and node.test.value is True:
                    issues.append({"path": path, "line": node.lineno, "kind": "assert_true", "text": "unconditional assert"})
                elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                    if any(isinstance(v, ast.Constant) and v.value is True for v in node.values):
                        issues.append({"path": path, "line": node.lineno, "kind": "or_constant_true_ast", "text": "boolean OR with constant True"})
    return issues


def scan_branch(client: GitHubSnapshot, output_dir: Path) -> dict:
    tree = client.tree()
    text_items = [o for o in tree if Path(o["path"]).suffix.lower() in TEXT_SUFFIXES or o["path"] == ".gitignore"]
    excluded = [o["path"] for o in tree if o not in text_items]
    issues: list[dict] = []
    def scan_entry(entry: dict) -> list[dict]:
        path = entry["path"]
        data = client.fetch_file(path, entry["sha"])
        return inspect_text(path, data)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(scan_entry, entry): entry["path"] for entry in text_items}
        for future in concurrent.futures.as_completed(futures):
            # Any access/read failure raises and fails the whole verification.
            issues.extend(future.result())
    issues.sort(key=lambda i: (i["path"], i["line"], i["kind"]))
    (output_dir / "branch_scan.json").write_text(json.dumps({
        "commit": client.commit, "inspected_text_files": len(text_items),
        "skipped_nontext_files": len(excluded), "skipped_paths": excluded,
        "findings": issues,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"inspected_text_files": len(text_items), "skipped_nontext_files": len(excluded), "findings": issues}


def self_test() -> None:
    assert first_diff(b"a\n", b"a\n") is None
    assert first_diff(b"a\r\n", b"a\n") == 1
    assert first_diff(b"abc", b"abcd") == 3
    assert inspect_text("script.py", b"x = True\nassert 1 == 1\n") == []
    bad = inspect_text("script.py", b"assert (1 == 2) or" + b" True\n")
    assert any(x["kind"] == "or_constant_true_ast" for x in bad)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            good = replay(b"print('ok')\n", b"ok\n", 5, Path(tmp))
            assert good["stdout_exact_match"]
            try:
                replay(b"print('bad')\n", b"good\n", 5, Path(tmp))
            except RuntimeError as exc:
                assert "byte mismatch" in str(exc)
            else:
                raise RuntimeError("MISMATCH SELFTEST FAILED: no rejection")
    except Exception as exc:
        raise RuntimeError(f"SELFTEST FAILED: {exc}") from exc
    print("SELFTEST PASS: strict byte compare, tampering rejection, and Python AST bypass detection")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("uno_lab001_verification"))
    parser.add_argument("--timeout", type=int, default=1200)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    output_dir = args.out_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict = {
        "status": "FAIL", "repository": OWNER_REPO, "branch": BRANCH,
        "script_path": SCRIPT, "gold_path": GOLD,
        "remark": "Exact stdout bytes check on frozen random fixture; NOT a math proof or trained UNO",
    }
    try:
        client = GitHubSnapshot(get_token())
        result["commit"] = client.resolve()
        script = client.fetch_file(SCRIPT)
        expected = client.fetch_file(GOLD)
        result["script_sha256"] = checksum(script)
        result["gold_sha256"] = checksum(expected)
        # Detect any replacement of the reviewed fixture, even if both files were changed together.
        if result["script_sha256"] != EXPECTED_SCRIPT_SHA256 or result["gold_sha256"] != EXPECTED_GOLD_SHA256:
            raise RuntimeError("Reviewed source/gold SHA-256 changed: explicit new review required")
        result["replay"] = replay(script, expected, args.timeout, output_dir)
        result["branch_scan"] = scan_branch(client, output_dir)
        dangerous = [i for i in result["branch_scan"]["findings"] if i["kind"] in (
            "literal_or_true", "or_constant_true_ast", "assert_true", "syntax_error"
        )]
        if dangerous:
            result["issues"] = dangerous
            raise RuntimeError(f"Found {len(dangerous)} suspicious occurrences in repository text; see branch_scan.json")
        result["status"] = "PASS_BYTE_REPLAY_AND_TEXT_SCAN"
        return 0
    except Exception as exc:
        message = f"FAIL: {type(exc).__name__}: {exc}"
        (output_dir / "verifier_stderr.txt").write_text(message + "\n", encoding="utf-8")
        print(message, file=sys.stderr)
        result["error"] = message
        return 1
    finally:
        (output_dir / "verdict.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{result['status']}  {output_dir / 'verdict.json'}")


if __name__ == "__main__":
    sys.exit(main())
