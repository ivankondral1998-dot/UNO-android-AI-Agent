"""Bounded, CPU-only training and inspection for the existing UNO F."""
import argparse
import hashlib
import json
import math
import os
import platform
import time
from pathlib import Path
from zipfile import ZipFile

import torch
from torch.nn import functional as F

from corpus_check import CORPUS_SHA, TOKENIZER_SHA, window_bounds, inspect, baselines, encode_prompt
from guard import admit, resources, disk_admit
import guard
from model import LanguageF
from train001_backend import atomic, canonical, checkpoint, output_lock, restore
from boundary import save_boundary, load_boundary
from analytic_backward import loss_and_grad
from flat_backward import loss_and_grad as flat_loss_and_grad
from thermal import ThermalPacer

ROOT = Path(__file__).resolve().parent
WINDOW = 16
WIDTH = 512


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_pin():
    names = ("train.py", "model.py", "guard.py", "train001_backend.py", "corpus_check.py", "r54_measurement.py", "supervise.py", "boundary.py", "fast_projection.py", "analytic_backward.py", "flat_backward.py", "thermal.py")
    return {name: digest(ROOT / name) for name in names}


def inputs(path):
    # Training and generation load prose only. No holdout member is opened.
    if path.stat().st_size != 2595563 or digest(path) != CORPUS_SHA:
        raise ValueError("corpus ZIP mismatch")
    with ZipFile(path) as archive:
        raw = archive.read("uno_b2/tokenizer.json")
        if hashlib.sha256(raw).hexdigest() != TOKENIZER_SHA:
            raise ValueError("unexpected tokenizer")
        tokenizer = json.loads(raw)
        docs = json.loads(archive.read("uno_b2/language/data.json"))
    if set(docs) != {"train", "dev"}:
        raise ValueError("unexpected prose keys")
    ids = tokenizer["active_ids"]
    lookup = {token: i for i, token in enumerate(ids)}
    packed = {split: [torch.tensor([lookup[token] for token in doc]) for doc in rows]
              for split, rows in docs.items()}
    return packed, tokenizer, lookup


PEAK_RATES = (2e-4, 4e-4, 8e-4)

def lr(step, total, warmup=1000, peak=2e-4):
    if peak not in PEAK_RATES:
        raise ValueError("invalid peak learning rate")
    # Keep FIX03 arithmetic exactly when peak=2e-4. Higher rates are diagnostic candidates.
    scale = peak / 2e-4
    if step <= warmup:
        return (2e-4 * step / warmup) * scale
    if step <= 1000:
        return peak
    return (2e-5 + 9e-5 * (1 + math.cos(math.pi * (step - 1000) / (total - 1000)))) * scale


def pacing_config_matches(saved, current):
    if saved == current:
        return True
    if not isinstance(saved, dict) or not isinstance(current.get('source'), dict):
        return False
    old_pins = {'train.py': 'e52c01104d6cdb8864ac11e0d91eac67167f21004c2b1b7cf9817d842d0d2b9f', 'model.py': '22693a58414a04a7777c288c95dfe0f890e201b2740499ac4b52855222ea92d0', 'guard.py': 'a79b79ec6a4819ab3bf8a124b7c7619cd33f81f5f97edd54af357284a1e5c877', 'train001_backend.py': '6ca7867d2018a597def5bd4b2fec273c1d56f4f2e131b2a2d8dae36641a44dc3', 'corpus_check.py': '7d686d3ed49b92d3c0518f93854d06dff9444ca49f0cb0c021c8aa5b1e3b88c2', 'r54_measurement.py': 'd958ff9767f3d4c45bbfdadfc5846e38532d546782552b09f010b75705ea1764', 'supervise.py': 'db64c6c1f89b57628233ff425911083b4785020e689bca14dee5bcf94d3b967f', 'boundary.py': 'ecd5062dea61bccae8d0405b4af238e337a585c9a4cedf763ac663c92a3a294c', 'fast_projection.py': 'd586f8d5f079713717483b369954fc6111fbebdbb78d30f6faeaa8d62f38e593', 'analytic_backward.py': '20d04430c6cee7995801bd7cca3e640bc3fbe54d8ff8d46a149c88b3c790d945', 'flat_backward.py': '7860c8f65ee35e856c1dcbe9f3514f84db79dd8c4f5063f03f3eebf3cee58f4b', 'thermal.py': '09eb981125cbeac8d1c8d30685b3357428bd842777f25ba59b49282963a50a14'}
    if saved.get('source') != old_pins:
        return False
    if current.get('threads') != 12 or current.get('steps') != 2000:
        return False
    if set(current['source']) != set(old_pins) or any(current['source'][k] != v for k,v in old_pins.items() if k not in ('train.py','thermal.py')):
        return False
    if current['source']['thermal.py'] != 'fb4793b4be411507a299cbc08bc39fb772c95f2840fa8fd8c84b97f2ef9415f5':
        return False
    old = dict(current, source=old_pins)
    return saved == old


class Trainer:
    def __init__(self, documents, vocab, config):
        self.documents = documents
        self.config = config
        torch.manual_seed(config["seed"])
        self.model = LanguageF(vocab, config["width"])
        self.opt = torch.optim.Adam(self.model.parameters(), lr=2e-4, foreach=False)
        self.step = self.document = self.offset = 0
        self.state = torch.zeros(self.model.width)
        self.targets = 0

    def update(self, rate=None):
        if self.document == len(self.documents) or self.step >= self.config["steps"]:
            return None
        doc = self.documents[self.document]
        start = self.offset
        stop = min(start + self.config["window"], len(doc) - 1)
        self.opt.zero_grad(set_to_none=True)
        backend = self.config.get("gradient_backend", "autograd")
        if backend == "flat":
            loss, state, _ = flat_loss_and_grad(self.model, doc[start:stop], doc[start + 1:stop + 1], self.state)
        elif backend == "analytic":
            loss, state, _ = loss_and_grad(self.model, doc[start:stop], doc[start + 1:stop + 1], self.state)
        elif backend == "autograd":
            logits, state = self.model(doc[start:stop], self.state)
            loss = F.cross_entropy(logits, doc[start + 1:stop + 1])
            if not torch.isfinite(loss) or not torch.isfinite(state).all():
                raise ValueError("nonfinite forward")
            loss.backward()
        else:
            raise ValueError("unknown gradient backend")
        norm = torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1., error_if_nonfinite=True)
        self.opt.param_groups[0]["lr"] = lr(self.step + 1, self.config["steps"], self.config.get("warmup", 1000), self.config.get("peak_lr", 2e-4)) if rate is None else rate
        self.opt.step()
        self.model.project_()
        self.validate_moments()
        self.step += 1
        self.targets += stop - start
        if stop == len(doc) - 1:
            self.document += 1
            self.offset = 0
            self.state = torch.zeros_like(state)
        else:
            self.offset = stop
            self.state = state.detach()
        return {"step": self.step, "targets": self.targets, "loss": float(loss.detach()),
                "grad_norm": float(norm), "document": self.document, "offset": self.offset}

    def validate_moments(self):
        for p, state in self.opt.state.items():
            for key in ("exp_avg", "exp_avg_sq"):
                moment = state[key]
                if (moment.shape != p.shape or moment.dtype != p.dtype
                        or not torch.isfinite(moment).all()
                        or (key == "exp_avg_sq" and (moment < 0).any())):
                    raise ValueError(f"invalid Adam state: {key}")

    def validate_payload(self, saved, step):
        expected_model = self.model.state_dict()
        raw = saved["model"]
        if not isinstance(raw, dict) or raw.keys() != expected_model.keys():
            raise ValueError("invalid model tensor inventory")
        for name, tensor in raw.items():
            expected = expected_model[name]
            if (not isinstance(tensor, torch.Tensor) or tensor.dtype != expected.dtype
                    or tensor.shape != expected.shape or tensor.layout != torch.strided
                    or tensor.device.type != "cpu" or not bool(torch.isfinite(tensor).all())):
                raise ValueError(f"invalid raw model tensor: {name}")
        optimizer = saved["optimizer"]
        expected_opt = self.opt.state_dict()
        if (not isinstance(optimizer, dict) or set(optimizer) != {"state", "param_groups"}
                or not isinstance(optimizer["param_groups"], list)
                or len(optimizer["param_groups"]) != 1):
            raise ValueError("invalid optimizer schema")
        group = optimizer["param_groups"][0]
        expected_group = expected_opt["param_groups"][0]
        if set(group) != set(expected_group) or any(
                group[k] != expected_group[k] for k in expected_group if k != "lr"):
            raise ValueError("invalid optimizer parameter group")
        rate = group["lr"]
        if type(rate) not in (int,float) or not math.isfinite(rate) or rate <= 0:
            raise ValueError("invalid optimizer learning rate")
        if "source" in self.config:
            expected_rate = 2e-4 if step == 0 else lr(step,self.config["steps"],self.config.get("warmup",1000),self.config.get("peak_lr",2e-4))
            if rate != expected_rate:
                raise ValueError("optimizer learning rate does not match schedule")
        states = optimizer["state"]
        ids = group["params"]
        if not isinstance(states,dict) or set(states) != (set(ids) if step else set()):
            raise ValueError("incomplete optimizer state")
        for idx, param in zip(ids,self.model.parameters()):
            if not step:
                continue
            record = states[idx]
            if not isinstance(record,dict) or set(record) != {"step","exp_avg","exp_avg_sq"}:
                raise ValueError("invalid Adam record")
            number = record["step"]
            if (not isinstance(number,torch.Tensor) or number.ndim != 0
                    or number.dtype != torch.float32 or number.device.type != "cpu"
                    or not bool(torch.isfinite(number)) or float(number) != step):
                raise ValueError("invalid Adam step")
            for key in ("exp_avg","exp_avg_sq"):
                moment = record[key]
                if (not isinstance(moment,torch.Tensor) or moment.shape != param.shape
                        or moment.dtype != param.dtype or moment.layout != torch.strided
                        or moment.device.type != "cpu" or not bool(torch.isfinite(moment).all())
                        or (key == "exp_avg_sq" and bool((moment < 0).any()))):
                    raise ValueError(f"invalid raw Adam moment: {key}")
        rng = saved["rng"]
        if (not isinstance(rng,torch.Tensor) or rng.dtype != torch.uint8
                or rng.device.type != "cpu" or rng.shape != torch.get_rng_state().shape):
            raise ValueError("invalid RNG state")

    def save(self, path):
        checkpoint(path, {"kind": "UNO-LANGUAGE-CPU-1", "config": self.config,
                          "model": self.model.state_dict(), "optimizer": self.opt.state_dict(),
                          "rng": torch.get_rng_state(), "step": self.step, "document": self.document,
                          "offset": self.offset, "state": self.state, "targets": self.targets})

    def load(self, path):
        s = restore(path)
        if (not isinstance(s,dict)
                or set(s) != {"kind","config","model","optimizer","rng","step","document","offset","state","targets"}
                or s.get("kind") != "UNO-LANGUAGE-CPU-1" or not pacing_config_matches(s["config"], self.config)):
            raise ValueError("checkpoint experiment mismatch")
        d, off, step = s["document"], s["offset"], s["step"]
        if (type(d) is not int or type(off) is not int or type(step) is not int
                or not 0 <= step <= self.config["steps"] or not 0 <= d <= len(self.documents)
                or (d == len(self.documents) and off != 0)
                or (d < len(self.documents) and not 0 <= off < len(self.documents[d]) - 1)
                or off % self.config["window"] != 0):
            raise ValueError("invalid checkpoint cursor")
        targets = sum(len(doc) - 1 for doc in self.documents[:d]) + off
        expected_step = sum(math.ceil((len(doc) - 1) / self.config["window"])
                            for doc in self.documents[:d]) + off // self.config["window"]
        state = s["state"]
        if (type(s["targets"]) is not int or targets != s["targets"] or expected_step != step
                or not isinstance(state,torch.Tensor) or state.shape != (self.model.width,)
                or state.device.type != "cpu" or state.layout != torch.strided or state.dtype != torch.float32 or not ((state >= -1) & (state <= 1)).all()
                or (off == 0 and torch.count_nonzero(state))):
            raise ValueError("invalid checkpoint state or cursor")
        self.validate_payload(s,step)
        self.model.load_state_dict(s["model"], strict=True)
        self.model.validate()
        self.opt.load_state_dict(s["optimizer"])
        self.validate_moments()
        if any(int(v["step"]) != step for v in self.opt.state.values()):
            raise ValueError("optimizer step mismatch")
        torch.set_rng_state(s["rng"])
        self.step, self.document, self.offset, self.state, self.targets = step, d, off, state, targets


def config(steps, threads, seed=11, warmup=16, gradient_backend='flat', peak_lr=2e-4):
    if peak_lr not in PEAK_RATES or gradient_backend not in ('flat','analytic','autograd'):
        raise ValueError('invalid training candidate')
    return {"steps": steps, "threads": threads, "seed": seed, "warmup": warmup, "peak_lr": peak_lr, "gradient_backend": gradient_backend, "width": WIDTH, "window": WINDOW,
            "source": source_pin(), "corpus": CORPUS_SHA, "tokenizer": TOKENIZER_SHA,
            "torch": str(torch.__version__), "system": platform.system(), "machine": platform.machine(),
            "python": platform.python_version(), "cpu_capability": torch.backends.cpu.get_cpu_capability(),
            "route": "all 8 blocks, K1, fixed; empty S4; zero goal/metadata; P0"}


def prepare_runtime(threads):
    if str(torch.__version__) != "2.10.0+cpu":
        raise RuntimeError("install the pinned CPU build with INSTALL.cmd")
    if not 1 <= threads <= 12:
        raise ValueError("choose 1–12 CPU threads")
    torch.set_num_threads(threads)
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)


def run(args):
    if not getattr(guard, 'MANAGED', False):
        raise RuntimeError('SUPERVISOR_REQUIRED: use START/RESUME_TRAINING.cmd')
    prepare_runtime(args.threads)
    pacer = ThermalPacer(sample=admit)
    # Pace setup, optimizer steps and checkpoint I/O separately. The independent
    # supervisor still enforces the unchanged hard limit and outer deadline.
    print(json.dumps(admit()), flush=True)
    pacer.ready("load_corpus")
    started = time.monotonic()
    docs, tokenizer, _ = inputs(args.corpus)
    pacer.after_work(started)
    manifest = config(args.steps, args.threads, warmup=args.warmup, gradient_backend=args.backend, peak_lr=args.peak_lr)
    path = args.output / "latest.uno"
    with output_lock(args.output):
        if args.command != "resume" and args.output.exists():
            raise FileExistsError("output directory already exists; use resume or select a new one")
        pacer.ready("initialize_model")
        started = time.monotonic()
        trainer = Trainer(docs["train"], len(tokenizer["active_ids"]), manifest)
        pacer.after_work(started)
        if args.command == "resume":
            pacer.ready("restore_checkpoint")
            started = time.monotonic()
            load_boundary(trainer.load, path, quarantine=True)
            pacer.after_work(started)
        else:
            from tempfile import mkdtemp
            pacer.ready("initial_checkpoint")
            started = time.monotonic()
            stage = Path(mkdtemp(prefix=".uno-init-", dir=args.output.parent))
            disk_admit(stage)
            admit()
            trainer.save(stage / "latest.uno")
            os.rename(stage, args.output)
            pacer.after_work(started)
        start = last_time = time.monotonic()
        deadline = start + args.seconds
        last_step = trainer.step
        while trainer.step < manifest["steps"] and trainer.document < len(trainer.documents):
            if not pacer.ready("optimizer_step", deadline):
                break
            started = time.monotonic()
            result = trainer.update()
            pacer.after_work(started)
            if result is None:
                break
            # Hard admission even after the final update, before claiming progress.
            stats = admit()
            due = trainer.step - last_step >= 5 or time.monotonic() - last_time >= 60
            if due:
                pacer.ready("periodic_checkpoint")
                started = time.monotonic()
                result.update(admit())
                save_boundary(trainer.save, path)
                last_step, last_time = trainer.step, time.monotonic()
                pacer.after_work(started)
            result["saved_step"] = last_step
            result["cpu_package_c"] = stats["cpu_package_c"]
            print(json.dumps(result), flush=True)
        if trainer.step != last_step:
            pacer.ready("final_checkpoint")
            admit()
            save_boundary(trainer.save, path)
        print(f"Saved boundary: step={trainer.step}, targets={trainer.targets}", flush=True)


def nll(model, documents, limit, reset):
    if limit <= 0:
        raise ValueError("validation limit must be positive")
    loss = 0.
    count = 0
    with torch.inference_mode():
        for doc in documents:
            state = torch.zeros(model.width)
            for start, stop in window_bounds(len(doc), WINDOW):
                stop = min(stop, start + limit - count)
                if reset:
                    state.zero_()
                logits, state = model(doc[start:stop], state)
                loss += float(F.cross_entropy(logits, doc[start + 1:stop + 1], reduction="sum"))
                count += stop - start
                if count >= limit:
                    return count, loss / count
    if count == 0:
        raise ValueError("empty validation set")
    return count, loss / count


@torch.inference_mode()
def generate(model, prompt, tokenizer, lookup, count):
    seq = encode_prompt(prompt,tokenizer)
    state = torch.zeros(model.width)
    ids = tokenizer["active_ids"]
    for token in [tokenizer["bos"], *seq]:
        state = model.event(lookup[token], state)
    generated = []
    for _ in range(count):
        logits = model.E @ state + model.b_text
        logits[lookup[tokenizer["bos"]]] = -torch.inf
        nxt = int(logits.argmax())
        token = ids[nxt]
        if token == tokenizer["eos"]:
            break
        generated.append(token)
        state = model.event(nxt, state)
    dictionary = tokenizer["tokens_hex"]
    decoded = b"".join(bytes.fromhex(dictionary[str(token)]) for token in generated)
    text = decoded.decode("utf-8", errors="replace")
    return {"continuation": text, "tokens": len(generated),
            "adjacent_repeat_rate": sum(a == b for a, b in zip(generated, generated[1:])) / max(1, len(generated) - 1),
            "utf8_replacement_count": text.count("\ufffd")}


def test_model(args):
    if not getattr(guard, 'MANAGED', False):
        raise RuntimeError('SUPERVISOR_REQUIRED: use TEST_MODEL.cmd')
    saved = load_boundary(restore, args.output / "latest.uno")
    if (saved.get("kind") != "UNO-LANGUAGE-CPU-1" or saved["config"]["source"] != source_pin()
            or saved["config"]["width"] != WIDTH or saved["config"]["corpus"] != CORPUS_SHA
            or saved["config"]["tokenizer"] != TOKENIZER_SHA
            or type(saved["config"].get("seed")) is not int
            or not 0 <= saved["config"]["seed"] <= 2**32-1
            or type(saved["config"].get("threads")) is not int
            or not 1 <= saved["config"]["threads"] <= 12
            or saved["config"].get("window") != WINDOW
            or type(saved["config"].get("steps")) is not int
            or not 1 <= saved["config"]["steps"] <= 55225
            or saved["config"].get("warmup") not in (16,1000)
            or saved["config"].get("peak_lr") not in PEAK_RATES
            or saved["config"].get("gradient_backend") not in ("flat","analytic","autograd")):
        raise ValueError("wrong language checkpoint or source")
    prepare_runtime(args.threads)
    docs, tokenizer, lookup = inputs(args.corpus)
    saved_config,saved_step=saved["config"],saved["step"]
    del saved
    verifier = Trainer(docs["train"],len(lookup),saved_config)
    load_boundary(verifier.load,args.output / "latest.uno")
    model = verifier.model
    del verifier
    model.validate()
    print(json.dumps(generate(model, args.prompt, tokenizer, lookup, args.tokens), ensure_ascii=False))
    if args.validation_targets:
        baseline = baselines((d.tolist() for d in docs["train"]),
                             (d.tolist() for d in docs["dev"]), len(lookup),
                             limit=args.validation_targets)
        print(json.dumps(baseline))
        for reset in (False, True):
            count, loss = nll(model, docs["dev"], args.validation_targets, reset)
            print(json.dumps({"validation_targets": count, "state_reset_each_window": reset,
                              "nll": loss, "perplexity": math.exp(loss)}))
    if args.export:
        if args.export.exists():
            raise FileExistsError("export already exists")
        weights = {name: value.cpu() for name, value in model.state_dict().items()}
        disk_admit(args.export)
        admit()
        checkpoint(args.export, {"kind": "UNO-TEXT-F-FP32-1", "state_dict": weights,
                                 "active_ids": tokenizer["active_ids"], "tokenizer_sha256": TOKENIZER_SHA,
                                 "config": saved_config, "step": saved_step})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=("check", "train", "resume", "test"))
    p.add_argument("--corpus", type=Path, required=True)
    p.add_argument("--output", type=Path, default=Path("uno_cpu_run"))
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--warmup", type=int, choices=(16,1000), default=16)
    p.add_argument("--backend", choices=("flat","analytic","autograd"), default="flat")
    p.add_argument("--peak-lr", type=float, choices=PEAK_RATES, default=2e-4,
                   help="higher rates are experimental; not accepted for production training")
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--seconds", type=int, default=1800)
    p.add_argument("--prompt", default="В тихий вечер")
    p.add_argument("--tokens", type=int, default=64)
    p.add_argument("--validation-targets", type=int, default=512)
    p.add_argument("--export", type=Path)
    a = p.parse_args()
    if not (1 <= a.threads <= 12 and 1 <= a.steps <= 55225 and 1 <= a.seconds <= 1800
            and 1 <= a.tokens <= 128 and 0 <= a.validation_targets <= 112994
            and len(a.prompt.encode("utf-8")) <= 512):
        p.error("invalid resource or diagnostic budget")
    if a.command == "check":
        if not getattr(guard, 'MANAGED', False):
            raise RuntimeError('SUPERVISOR_REQUIRED: use CHECK.cmd')
        print(json.dumps(inspect(a.corpus), ensure_ascii=False))
        print(json.dumps(admit()))
    elif a.command == "test":
        test_model(a)
    else:
        run(a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted. Resume from the previously saved optimizer boundary.")
        raise SystemExit(130)
