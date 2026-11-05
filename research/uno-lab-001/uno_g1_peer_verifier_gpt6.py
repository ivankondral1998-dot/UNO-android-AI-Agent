#!/usr/bin/env python3
"""GPT-6 independent UNO G1 verifier. Offline math claims are out of scope.
GITHUB_TOKEN=... python3 uno_g1_peer_verifier_gpt6.py --out ./g1-proof
python3 uno_g1_peer_verifier_gpt6.py --self-test
Requires Python stdlib + numpy for downloaded experiment.
"""
from __future__ import annotations
import argparse, ast, base64, hashlib, json, os, pathlib, subprocess, sys, tempfile
import urllib.parse, urllib.request

REPO = "ivankondral1998-dot/UNO-android-AI-Agent"
BRANCH = "docs/uno-lab-research-handoff-20261105"
SCRIPT = "research/uno-lab-001/grok_lab001_hfix.py"
GOLD = "research/uno-lab-001/grok_lab001_hfix_output.txt"
PIN_SCRIPT = "b70754f1c39faf564eb8a4fc0f671fbae961f75e56ab9ce9bf14d2757ee5225d"
PIN_GOLD = "cfd5b0bebee162a07907714d10aa14177b09074da02958dfdd5099619947f3a5"
TEXT = {".py", ".txt", ".md", ".json", ".jsonl", ".yaml", ".yml", ".sh", ".kt", ".kts", ".java", ".xml", ".gradle", ".properties", ".toml", ".ini", ".cfg", ".ps1"}

def sha(data):
    return hashlib.sha256(data).hexdigest()

def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def difference(a, b):
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y: return i
    return None if len(a) == len(b) else min(len(a), len(b))

class GitHub:
    def __init__(self, token):
        if not token: raise RuntimeError("GITHUB_TOKEN or GH_TOKEN required for private repo")
        self.token = token

    def read(self, endpoint):
        request = urllib.request.Request("https://api.github.com/repos/" + REPO + "/" + endpoint,
            headers={"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json",
                     "User-Agent": "uno-g1-peer-verifier"})
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)

    def head(self):
        sha1 = self.read("git/ref/heads/" + urllib.parse.quote(BRANCH, safe="/"))["object"]["sha"]
        if len(sha1) != 40 or any(c not in "0123456789abcdef" for c in sha1.lower()):
            raise RuntimeError("Invalid commit")
        return sha1

    def file(self, path, commit, tree_sha=None):
        result = self.read("contents/" + urllib.parse.quote(path, safe="/") + "?ref=" + commit)
        if result.get("type") != "file" or result.get("encoding") != "base64":
            raise RuntimeError("Not a file: " + path)
        raw = base64.b64decode(result["content"])
        if len(raw) != result["size"] or blob(raw) != result["sha"]:
            raise RuntimeError("Git file integrity failed: " + path)
        if tree_sha and blob(raw) != tree_sha:
            raise RuntimeError("Git tree mismatch: " + path)
        return raw

    def tree(self, commit):
        result = self.read("git/trees/" + commit + "?recursive=1")
        if result.get("truncated"): raise RuntimeError("Git tree truncated; cannot scan whole branch")
        return [e for e in result["tree"] if e["type"] == "blob"]

def inspect(path, raw):
    try: content = raw.decode("utf-8")
    except UnicodeDecodeError: return [{"path":path,"line":0,"kind":"non_utf8"}]
    problems = []
    for i, line in enumerate(content.splitlines(), 1):
        if "or" + " True" in line:
            problems.append({"path":path,"line":i,"kind":"literal_or_true","text":line.strip()[:140]})
    if path.endswith(".py"):
        try: tree = ast.parse(content, filename=path)
        except SyntaxError as e:
            problems.append({"path":path,"line":e.lineno,"kind":"syntax_error"})
        else:
            for n in ast.walk(tree):
                if isinstance(n, ast.Assert) and isinstance(n.test, ast.Constant) and n.test.value is True:
                    problems.append({"path":path,"line":n.lineno,"kind":"assert_true"})
                if isinstance(n, ast.BoolOp) and isinstance(n.op, ast.Or) and any(
                    isinstance(v, ast.Constant) and v.value is True for v in n.values):
                    problems.append({"path":path,"line":n.lineno,"kind":"or_true_ast"})
    return problems

def replay(script, expected, out, timeout):
    with tempfile.TemporaryDirectory(prefix="uno-g1-peer-") as tmp:
        path = pathlib.Path(tmp) / "grok_lab001_hfix.py"
        path.write_bytes(script)
        env = {k:v for k,v in os.environ.items() if not (
            k.endswith("_TOKEN") or k.endswith("_KEY") or k.startswith(("GITHUB_","GH_","AWS_","AZURE_")))}
        env.update({"OPENBLAS_NUM_THREADS":"1","OMP_NUM_THREADS":"1","MKL_NUM_THREADS":"1",
                    "PYTHONDONTWRITEBYTECODE":"1"})
        try:
            proc = subprocess.run([sys.executable,"-I",str(path)], cwd=tmp, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            (out/"actual_stdout.bin").write_bytes(e.stdout or b"")
            (out/"actual_stderr.bin").write_bytes(e.stderr or b"")
            raise RuntimeError("Timeout; partial outputs saved") from e
        (out/"actual_stdout.bin").write_bytes(proc.stdout)
        (out/"actual_stderr.bin").write_bytes(proc.stderr)
        pos = difference(proc.stdout,expected)
        if proc.returncode: raise RuntimeError(f"Script exited {proc.returncode}; see actual_stderr.bin")
        if proc.stderr: raise RuntimeError("Script wrote nonempty stderr; see actual_stderr.bin")
        if pos is not None: raise RuntimeError(f"stdout byte mismatch at offset {pos}")
        return {"exit_code":proc.returncode,"byte_exact":True,"stdout_bytes":len(proc.stdout),
                "expected_bytes":len(expected),"stderr_bytes":len(proc.stderr)}

def run(client, out, timeout):
    commit=client.head()
    result={"status":"FAIL","commit":commit,"branch":BRANCH,"script":SCRIPT,"gold":GOLD}
    try:
        script=client.file(SCRIPT,commit)
        golden=client.file(GOLD,commit)
        result["script_sha256"]=sha(script)
        result["gold_sha256"]=sha(golden)
        if sha(script)!=PIN_SCRIPT or sha(golden)!=PIN_GOLD:
            raise RuntimeError("Pinned source or golden changed; independent review required")
        (out/"expected_stdout.bin").write_bytes(golden)
        result["replay"]=replay(script,golden,out,timeout)
        tree=client.tree(commit)
        text=[e for e in tree if pathlib.Path(e["path"]).suffix.lower() in TEXT or e["path"]==".gitignore"]
        issues=[]
        for e in text:
            issues.extend(inspect(e["path"],client.file(e["path"],commit,e["sha"])))
        issues.sort(key=lambda v:(v["path"],v["line"],v["kind"]))
        scan={"inspected":len(text),"skipped_nontext":len(tree)-len(text),"findings":issues}
        (out/"branch_scan.json").write_text(json.dumps(scan,ensure_ascii=False,indent=2)+"\n")
        result["scan"]=scan
        if issues: raise RuntimeError(f"{len(issues)} suspicious lines; see branch_scan.json")
        result["status"]="PASS_G1_BYTE_REPLAY_AND_TEXT_SCAN"
        return result
    except Exception as e:
        result["error"]=f"{type(e).__name__}: {e}"
        raise
    finally:
        (out/"verdict.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")

def self_test():
    assert difference(b"a\n",b"a\n") is None
    assert difference(b"a\r\n",b"a\n")==1
    assert difference(b"a",b"ab")==1
    assert any(x["kind"]=="or_true_ast" for x in inspect("bad.py",b"assert False or"+b" True\n"))
    with tempfile.TemporaryDirectory() as folder:
        out=pathlib.Path(folder)
        assert replay(b'print("ok")\n',b"ok\n",out,5)["byte_exact"]
        for source,golden,part in [
            (b'print("ok")\n',b"ok\r\n","byte mismatch"),
            (b'raise RuntimeError("boom")\n',b"","exited"),
            (b'import sys;sys.stderr.write("bad")\n',b"","stderr"),
        ]:
            try: replay(source,golden,out,5)
            except RuntimeError as e:
                if part not in str(e): raise
            else: raise AssertionError("Incorrectly accepted broken fixture")
    print("SELFTEST PASS")

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out",type=pathlib.Path,default=pathlib.Path("uno-g1-peer-results"))
    p.add_argument("--timeout",type=int,default=1200)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        self_test()
        return 0
    a.out.mkdir(parents=True,exist_ok=True)
    try:
        result=run(GitHub(os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN") or ""),a.out,a.timeout)
        print(result["status"],result["commit"])
        return 0
    except Exception as e:
        message=f"FAIL {type(e).__name__}: {e}"
        (a.out/"verifier_stderr.txt").write_text(message+"\n")
        print(message,file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
