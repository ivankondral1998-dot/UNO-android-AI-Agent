"""Short technical acceptance only. Never opens the corpus test or runs corpus training."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

import psutil
import torch
from torch.nn import functional as F

from corpus_check import windows
from guard import admit
from model import LanguageF
from train import Trainer, generate, inputs, nll, prepare_runtime, config
from train001_backend import checkpoint, output_lock, restore

DOCS = [torch.tensor([0, 1, 2, 3, 2, 3, 2, 3, 2, 3, 1]), torch.tensor([0, 2, 3, 1])]
CFG = {"width": 64, "steps": 3, "window": 4, "seed": 11}


def fixture():
    return Trainer(DOCS, 4, CFG)


def worker(mode, output):
    prepare_runtime(2)
    with output_lock(output):
        model = fixture()
        path = output / "latest.uno"
        if mode == "resume":
            model.load(path)
        else:
            output.mkdir()
        while model.update(rate=.002):
            model.save(path)
            if mode == "pause" and model.step == 1:
                (output / "step1-ready").touch()
                time.sleep(120)


def separate(mode, path, **kwargs):
    return subprocess.Popen([sys.executable, __file__, "--worker", mode, str(path)],
                            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)


def equal(x, y):
    if isinstance(x, torch.Tensor):
        return torch.equal(x, y)
    if isinstance(x, dict):
        return x.keys() == y.keys() and all(equal(x[k], y[k]) for k in x)
    if isinstance(x, (list, tuple)):
        return len(x) == len(y) and all(equal(a, b) for a, b in zip(x, y))
    return x == y


def scalar_reference(model, x, h):
    # Independent loop over A,B,C branches and blocks, no batched matmul or model.event.
    w = {k: v.detach() for k, v in model.named_parameters()}
    z = torch.tanh(torch.tanh(w["E"][x] + w["Us"].mv(h) + w["e"] + w["bz"]))
    h0 = .5 * h + .5 * z
    blocks = []
    for j in range(model.width // 64):
        proposals = []
        for branch in range(2):
            u = torch.tanh(w["A"][branch, j].mv(h0) + w["C"][branch, j].mv(z) + w["a"][branch, j])
            proposals.append(torch.tanh(w["B"][branch, j].mv(u) + w["b"][branch, j]))
        blocks.append(.5 * h0[64*j:64*(j+1)] + .25 * (proposals[0] + proposals[1]))
    hidden = torch.cat(blocks)
    return w["E"].mv(hidden) + w["b_text"], hidden


class Tests(unittest.TestCase):
    def test_causal_forward_and_numeric_gradient(self):
        torch.manual_seed(11)
        m = LanguageF(5, 128).double()
        state = torch.linspace(-.1, .1, 128, dtype=torch.float64)
        tokens = torch.tensor([0, 1, 2])
        got, last = m(tokens, state)
        original = state
        want = []
        for x in tokens:
            logits, state = scalar_reference(m, x, state)
            want.append(logits)
        torch.testing.assert_close(got, torch.stack(want), atol=2e-15, rtol=1e-12)
        torch.testing.assert_close(last, state, atol=2e-15, rtol=1e-12)
        alt, _ = m(torch.tensor([0, 1, 4]), original)
        self.assertTrue(torch.equal(got[:2], alt[:2]))
        targets = torch.tensor([1, 2, 3])
        F.cross_entropy(got, targets).backward()
        for name in ("E", "Us", "A", "B", "C", "b_text"):
            p = getattr(m, name)
            g = p.grad.reshape(-1)
            i = int(g.abs().argmax())
            self.assertGreater(float(g[i].abs()), 1e-8)
            def objective(delta):
                with torch.no_grad():
                    p.view(-1)[i] += delta
                    h, values = original, []
                    for x in tokens:
                        l, h = scalar_reference(m, x, h)
                        values.append(l)
                    loss = float(F.cross_entropy(torch.stack(values), targets))
                    p.view(-1)[i] -= delta
                    return loss
            numeric = (objective(1e-5) - objective(-1e-5)) / 2e-5
            self.assertAlmostEqual(numeric, float(g[i]), delta=3e-9)

    def test_state_and_window_boundaries(self):
        t = fixture()
        with torch.no_grad():
            m = t.model
            x = DOCS[0][:-1]
            full, _ = m(x, t.state)
            part, state = m(x[:4], t.state)
            rest, _ = m(x[4:], state)
            torch.testing.assert_close(torch.cat((part, rest)), full, atol=1e-7, rtol=1e-6)
            self.assertFalse(torch.allclose(rest, m(x[4:], torch.zeros_like(state))[0]))
        t.update()
        torch.testing.assert_close(t.state, state)
        self.assertIsNone(t.state.grad_fn)
        t.update()
        t.update()
        self.assertEqual((t.document, t.offset), (1, 0))
        self.assertTrue(torch.equal(t.state, torch.zeros(64)))
        self.assertEqual([x[1] for x in windows([DOCS[0]], 4)], [True, False, False])

    def test_learns_fixture_caps_and_generation(self):
        seq = torch.tensor([0, 2, 3, 2, 3, 1])
        t = Trainer([seq] * 100, 4, dict(CFG, steps=100, window=5))
        before, m = nll(t.model, [seq], 5, False)[1], t.model
        initial = copy.deepcopy(m.state_dict())
        while t.update(rate=.02):
            pass
        after = nll(m, [seq], 5, False)[1]
        self.assertLess(after, min(.6, before * .5))
        self.assertTrue(all(not torch.equal(initial[k], v) for k, v in m.state_dict().items()))
        m.validate()
        tokenizer = {"active_ids": [256, 257, 65, 66], "bos": 256, "eos": 257, "merges": [],
                     "tokens_hex": {"65": "41", "66": "42"}}
        result = generate(m, "", tokenizer, {x:i for i,x in enumerate(tokenizer["active_ids"])}, 4)
        self.assertEqual(result["continuation"], "ABAB")
        print(json.dumps({"fixture_initial_nll": before, "fixture_final_nll": after,
                          "decoded": result}, ensure_ascii=False), flush=True)

    def test_guard_refuses_missing_temperature(self):
        from unittest.mock import patch
        sample = {"rss_mib": 512, "available_mib": 6000, "system_cpu_pct": 30}
        with patch("guard.resources", return_value=sample):
            with patch("guard.cpu_package_celsius", side_effect=RuntimeError("no CPU sensor")):
                with self.assertRaisesRegex(RuntimeError, "no CPU sensor"):
                    admit()
            with patch("guard.cpu_package_celsius", return_value=86.):
                with self.assertRaisesRegex(RuntimeError, "CPU resource stop"):
                    admit()

    def test_nonfinite_forward_preserves_previous_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "last.uno"
            t = fixture()
            t.save(path)
            before = path.read_bytes()
            with torch.no_grad():
                t.model.bz[0] = torch.nan
            with self.assertRaisesRegex(ValueError, "nonfinite forward"):
                t.update()
            self.assertEqual(t.step, 0)
            self.assertEqual(path.read_bytes(), before)

    def test_kill_resume_lock_and_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            alive = separate("pause", a)
            try:
                for _ in range(400):
                    if (a / "step1-ready").exists():
                        break
                    if alive.poll() is not None:
                        self.fail(alive.communicate()[1])
                    time.sleep(.05)
                else:
                    self.fail("worker did not reach the first saved boundary")
                second = separate("resume", a)
                _, err = second.communicate(timeout=30)
                self.assertNotEqual(second.returncode, 0)
                self.assertTrue("OUTPUT_BUSY" in err or "BlockingIOError" in err, err)
            finally:
                alive.kill()
                alive.communicate(timeout=10)
            self.assertNotEqual(alive.returncode, 0)
            for mode, path in (("resume", a), ("full", b)):
                proc = separate(mode, path)
                _, err = proc.communicate(timeout=45)
                self.assertEqual(proc.returncode, 0, err)
            x, y = (restore(path / "latest.uno") for path in (a, b))
            self.assertTrue(equal(x, y))
            broken = Path(tmp) / "broken.uno"
            raw = (a / "latest.uno").read_bytes()
            broken.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
            with self.assertRaisesRegex(ValueError, "CHECKPOINT_INTEGRITY"):
                fixture().load(broken)


def measure(corpus):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "profile.uno"
        train, tokenizer, _ = inputs(corpus)
        # One short step on the actual d512 geometry with synthetic token IDs from
        # the pinned vocabulary, no main corpus updates or production checkpoint.
        ids = len(tokenizer["active_ids"])
        row = torch.arange(17) % ids
        p = psutil.Process()
        start = time.perf_counter()
        f = Trainer([row], ids, config(1, torch.get_num_threads()))
        init = time.perf_counter() - start
        start = time.perf_counter()
        log = f.update()
        update = time.perf_counter() - start
        start = time.perf_counter()
        f.save(path)
        save = time.perf_counter() - start
        f.load(path)
        rss_peak = getattr(p.memory_info(), "peak_wset", None)
        if sys.platform.startswith("linux"):
            with open("/proc/self/status", encoding="utf-8") as status:
                rss_peak = next(int(line.split()[1]) * 1024 for line in status if line.startswith("VmHWM:"))
        print(json.dumps({"host": sys.platform, "torch": str(torch.__version__),
                          "threads": torch.get_num_threads(), "parameters": sum(x.numel() for x in f.model.parameters()),
                          "d512_synthetic_window": log, "init_seconds": init, "update_seconds": update,
                          "atomic_save_seconds": save, "targets_per_second_without_guards": log["targets"] / update,
                          "checkpoint_bytes": path.stat().st_size, "process_peak_rss_bytes": rss_peak,
                          "rss_bytes": p.memory_info().rss, "full_size_reload": "PASS"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2)
    parser.add_argument("--profile", type=Path)
    args = parser.parse_args()
    prepare_runtime(2)
    if args.worker:
        worker(args.worker[0], Path(args.worker[1]))
    elif args.profile:
        measure(args.profile)
    else:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
