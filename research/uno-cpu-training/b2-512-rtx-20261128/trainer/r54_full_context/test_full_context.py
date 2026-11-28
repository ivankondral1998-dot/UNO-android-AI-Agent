import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from trainer import (Codec, CausalB2, current_checkpoint, remapping, setup,
                     telemetry, verify_tensor_layout)
from core import Dialogues, POSITION_SCALE, make_batch, objective, generate
from quality import paired_questions
from model_audit import B2
from train_cuda_fast03 import output_lock, save


def record(*turns):
    return {"source": "synthetic", "messages": [
        {"role": "user" if i % 2 == 0 else "assistant", "text": text}
        for i, text in enumerate(turns)]}


class FullContextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        setup("cpu")
        cls.codec = Codec()
        cls.ids, cls.remap = remapping(cls.codec, "cpu")

    def models(self):
        reference = B2(64)
        model = CausalB2(64)
        model.load_state_dict(reference.state_dict())
        model.compact(self.ids)
        return model, reference

    def test_multiturn_mask_and_exclusion(self):
        example = record("Что запомнить?", "Дом.", "Какое слово?", "Дом.")
        long = record("длинный вопрос " * 400, "Да.")
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "dialogs.jsonl"
            p.write_text("".join(json.dumps(item) + "\n" for item in (example, long)), encoding="utf8")
            ds = Dialogues(p, self.codec, 128)
        self.assertEqual(ds.coverage["synthetic"], {"total": 2, "kept": 1})
        tokens, mask = ds.rows[0]
        short = self.codec.record(record("Эй", "Да"), "dialogue")
        x, y, valid = make_batch([ds.rows[0], short], self.codec, self.remap, "cpu")
        self.assertEqual(x[0].tolist(), tokens[:-1])
        self.assertEqual(x[0, 0].item(), self.codec.bos)
        expected = (self.codec.encode("Дом.") + [self.codec.eos]) * 2
        self.assertEqual(self.ids[y[0][valid[0]]].tolist(), expected)
        self.assertFalse(valid[1, len(short[0])-1:].any())
        self.assertEqual(sum(mask), len(expected))

    def test_forward_and_all_gradients_against_event(self):
        old, ref = self.models()
        model, reference = old.double(), ref.double()
        tokens = self.ids[torch.arange(10).view(2, 5)]
        actual = model.language(tokens, self.ids)
        state = torch.zeros(2, 64, dtype=torch.float64)
        values = []
        for pos in range(tokens.size(1)):
            meta = torch.zeros(2, 32, dtype=torch.float64)
            meta[:, 1] = meta[:, 4] = 1.0
            meta[:, 14] = pos / POSITION_SCALE
            state, _ = reference.event(tokens[:, pos], state, torch.zeros_like(state), meta)
            values.append(state)
        expected = torch.nn.functional.linear(torch.stack(values, 1),
                       reference.p["E_text"][self.ids], reference.p["b_text"][self.ids])
        torch.testing.assert_close(actual, expected, atol=2e-15, rtol=1e-12)
        actual.square().mean().backward()
        expected.square().mean().backward()
        for name, param in model.p.items():
            grad = reference.p[name].grad
            if param.grad is None:
                self.assertTrue(grad is None or not grad.any(), name)
            else:
                if name in ("E_text", "b_text"):
                    grad = grad[self.ids]
                torch.testing.assert_close(param.grad, grad, atol=1e-15, rtol=1e-10)

    def test_prefix_independent_of_length_and_streaming(self):
        model, _ = self.models()
        x = self.ids[torch.arange(20).view(1, -1)]
        full, ending = model.scan(x)
        prefix, state = model.scan(x[:, :7])
        torch.testing.assert_close(full[:, :7], prefix, atol=1e-7, rtol=1e-6)
        suffix, last = model.scan(x[:, 7:], state, start=7)
        torch.testing.assert_close(full[:, 7:], suffix, atol=1e-7, rtol=1e-6)
        torch.testing.assert_close(ending, last, atol=1e-7, rtol=1e-6)
        wrong, _ = model.scan(x[:, 7:], state)
        self.assertGreater((wrong - suffix).abs().max().item(), 1e-5)

    def test_directional_derivative(self):
        model, _ = self.models()
        model.double()
        rows = [self.codec.record(record("Да?", "Да"), "dialogue")]
        batch = make_batch(rows, self.codec, self.remap, "cpu")
        objective(model, batch)[0].backward()
        weights = model.p["U_s"]
        direction = weights.grad / weights.grad.norm()
        original = weights.detach().clone()
        values = []
        with torch.no_grad():
            for sign in (-1, 1):
                weights.copy_(original + direction * sign * 0.004)
                values.append(objective(model, batch)[0].item())
            weights.copy_(original)
        actual = (values[1] - values[0]) / 0.008
        self.assertAlmostEqual(actual, weights.grad.norm().item(), delta=8e-5)

    def test_candidate_pair_alignment(self):
        rows = [self.codec.record(record(q, a), "dialogue")
                for q, a in (("AAAA", "X"), ("BBBB", "Y"), ("CCCC", "X"))]
        pair, = paired_questions(rows, 10)
        (p, a), (q, b) = pair
        self.assertEqual(len(p), len(q))
        self.assertNotEqual(p, q)
        self.assertNotEqual(a[0], b[0])
        model, _ = self.models()
        generated, _ = generate(model, self.codec, p, 3)
        self.assertLessEqual(len(generated), 3)
        self.assertTrue(all(i in self.codec.allowed for i in generated))

    def test_corrupt_checkpoint_and_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            latest = directory / "latest.uno"
            with output_lock(directory):
                with self.assertRaises(OSError):
                    with output_lock(directory):
                        pass
                save(latest, {"step": 1})
                save(latest, {"step": 2}, keep_previous=True)
            self.assertEqual(current_checkpoint(directory), ({"step": 2}, "latest.uno"))
            with latest.open("r+b") as f:
                f.seek(-1, 2)
                f.write(b"_")
            self.assertEqual(current_checkpoint(directory), ({"step": 1}, "previous.uno"))
            (directory / "previous.uno").write_bytes(b"invalid")
            with self.assertRaisesRegex(ValueError, "NO_VALID_CHECKPOINT"):
                current_checkpoint(directory)

    def test_tensor_layout_rejects_implicit_cast(self):
        with self.assertRaisesRegex(ValueError, "CHECKPOINT_TENSOR_LAYOUT"):
            verify_tensor_layout({"x": torch.zeros(4)}, {"x": torch.zeros(4).double()})

    def test_telemetry_fail_closed(self):
        now = dt.datetime.now()
        for age, temp, memory, error in [(0, 77, 6499, None), (8, 77, 6400, "STALE"),
                (0, 78, 6400, "LIMIT"), (0, 77, 6500, "LIMIT"), (0, "nan", 42, "LIMIT")]:
            timestamp = (now - dt.timedelta(seconds=age)).strftime("%Y/%m/%d %H:%M:%S.%f")
            with patch("trainer.subprocess.check_output", return_value=f"{timestamp},GPU-xyz,{temp},{memory}\n"):
                if error:
                    with self.assertRaisesRegex(ValueError, error):
                        telemetry()
                else:
                    self.assertEqual(telemetry()["memory_mib"], memory)


if __name__ == "__main__":
    unittest.main(verbosity=2)
