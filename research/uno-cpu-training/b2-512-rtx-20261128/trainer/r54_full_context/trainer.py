"""Bounded, resumable B2-512 CPU/CUDA research preflight."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
import pickle
from pathlib import Path
import random
import signal
import subprocess
import sys
import time

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch

from core import (CausalB2, Dialogues, corpus_identity, language_rows,
                  make_batch, objective, remapping)
from train_cuda_fast03 import Codec, Records, TOK_SHA, require, sha
from quality import validation
from train_cuda_fast03 import (PARENT_SHA, output_lock, restore, save,
                               validate_optimizer, validate_weights)

HERE = Path(__file__).resolve().parent
STAGE = "UNO-B2-R54-FULL-CONTEXT/1"
TEMPERATURE_LIMIT = 78
MEMORY_LIMIT = 6500
SEED = 20261128512


class StopRequested(Exception):
    pass


def telemetry():
    response = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=timestamp,uuid,temperature.gpu,memory.used",
         "--format=csv,noheader,nounits"], text=True, timeout=4)
    rows = response.strip().splitlines()
    require(len(rows) == 1, "EXPECTED_ONE_PHYSICAL_GPU")
    timestamp, uuid, temp, vram = (v.strip() for v in rows[0].split(","))
    moment = dt.datetime.strptime(timestamp, "%Y/%m/%d %H:%M:%S.%f")
    age = (dt.datetime.now() - moment).total_seconds()
    temp, vram = float(temp), float(vram)
    require(abs(age) <= 5 and uuid.startswith("GPU-"), "GPU_TELEMETRY_STALE")
    require(0 <= temp < TEMPERATURE_LIMIT and 0 <= vram < MEMORY_LIMIT,
            f"GPU_LIMIT temp={temp} memory={vram}")
    return {"uuid": uuid, "temperature_c": temp, "memory_mib": vram}


def setup(device):
    torch.set_num_threads(3)
    torch.manual_seed(SEED)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    if device == "cuda":
        require(torch.cuda.is_available() and torch.cuda.device_count() == 1,
                "SINGLE_CUDA_DEVICE_REQUIRED")


def model_from_parent(parent, ids, device):
    require(sha(parent) == PARENT_SHA, "B2_STEP50_CHECKPOINT_MISMATCH")
    state = torch.load(parent, map_location="cpu", weights_only=True)
    model = CausalB2(512)
    verify_tensor_layout(model.state_dict(), state["weights"])
    model.load_state_dict(state["weights"], strict=True)
    validate_weights(model)
    # Preserve canonical inactive rows in system RAM.
    model.compact(ids.cpu())
    return model.to(device)


def verify_tensor_layout(expected, actual):
    require(expected.keys() == actual.keys(), "CHECKPOINT_TENSOR_KEYS")
    for name, reference in expected.items():
        value = actual[name]
        require(isinstance(value, torch.Tensor) and value.layout == torch.strided
                and value.shape == reference.shape and value.dtype == reference.dtype,
                f"CHECKPOINT_TENSOR_LAYOUT {name}")


def code_id():
    paths = [HERE / n for n in ("trainer.py", "core.py", "quality.py")]
    paths += [HERE.parent / n for n in ("train_cuda_fast03.py", "fast_model03.py", "model_audit.py")]
    return hashlib.sha256("".join(sha(path) for path in paths).encode()).hexdigest()


def current_checkpoint(out):
    errors = []
    for name in ("latest.uno", "previous.uno"):
        path = out / name
        try:
            return restore(path), name
        except (OSError, ValueError, RuntimeError, EOFError, pickle.UnpicklingError) as error:
            errors.append(f"{name}: {error}")
    raise ValueError("NO_VALID_CHECKPOINT " + "; ".join(errors))


def configuration(args, digest, gpu):
    return {"stage": STAGE, "corpus": digest, "tokenizer": TOK_SHA, "parent": PARENT_SHA,
            "code": code_id(), "torch": str(torch.__version__), "device": args.device,
            "gpu": gpu, "precision": "fp32", "lang_context": args.language_context,
            "dialogue_limit": args.dialogue_limit, "batch": args.batch, "lr": args.lr,
            "schedule": ["dialogue", "dialogue", "language"], "clip": 1.0, "seed": SEED}


def write_report(path, result):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def run_worker(args):
    start = time.monotonic()
    last_heartbeat = 0
    interrupted = False
    def mark_stop(_signum, _frame):
        nonlocal interrupted
        interrupted = True
    signal.signal(signal.SIGINT, mark_stop)
    if hasattr(signal, "SIGBREAK"):
        signal.signal(signal.SIGBREAK, mark_stop)

    def check():
        nonlocal last_heartbeat
        now = time.monotonic()
        if now - last_heartbeat >= .5:
            args.heartbeat.touch()
            last_heartbeat = now
        if interrupted or args.stop_file.exists() or now - start >= args.seconds:
            raise StopRequested

    with output_lock(args.out):
        try:
            execute(args, check)
        except StopRequested:
            print("PREFLIGHT_STOPPED", flush=True)
            return 2
    return 0


def execute(args, check):
    check()
    setup(args.device)
    digest = corpus_identity(args.data, check)
    codec = Codec()
    ids, remap = remapping(codec, args.device)
    dialogues = {split: Dialogues(args.data / "dialogue" / f"{split}.jsonl", codec,
                                 args.dialogue_limit, check)
                 for split in ("train", "validation")}
    coverage = {split: dataset.coverage for split, dataset in dialogues.items()}
    print(json.dumps({"complete_dialogue_coverage": coverage}, ensure_ascii=False), flush=True)
    languages = {split: Records(args.data / "language" / f"{split}.jsonl", "language")
                 for split in ("train", "validation")}
    check()
    model = model_from_parent(args.parent, ids, args.device)
    opt = torch.optim.Adam([p for p in model.parameters() if p.requires_grad], lr=args.lr,
                           foreach=False)
    cfg = configuration(args, digest, args.gpu_uuid)
    rng = random.Random(SEED)
    step = 0
    replace_previous = False
    if args.resume:
        checkpoint, source = current_checkpoint(args.out)
        require(checkpoint["config"] == cfg, "EXACT_RESUME_CONFIG_MISMATCH")
        verify_tensor_layout(model.canonical_weights(), checkpoint["weights"])
        model.load_canonical(checkpoint["weights"])
        validate_weights(model)
        opt.load_state_dict(checkpoint["optimizer"])
        validate_optimizer(model, opt, ids)
        require(len(opt.param_groups) == 1 and opt.param_groups[0]["lr"] == args.lr
                and opt.param_groups[0]["betas"] == (.9, .999)
                and opt.param_groups[0]["eps"] == 1e-8
                and opt.param_groups[0]["weight_decay"] == 0, "CHECKPOINT_ADAM_SETTINGS")
        rng.setstate(checkpoint["rng"])
        torch.set_rng_state(checkpoint["torch_rng"])
        if args.device == "cuda":
            torch.cuda.set_rng_state_all(checkpoint["cuda_rng"])
        step = checkpoint["step"]
        require(type(step) is int and step >= 0, "CHECKPOINT_STEP_INVALID")
        replace_previous = source == "latest.uno"
        del checkpoint
        print(f"RESUMED step={step} from={source}", flush=True)

    def snapshot():
        nonlocal replace_previous
        validate_weights(model)
        validate_optimizer(model, opt, ids)
        save(args.out / "latest.uno", {"config": cfg, "step": step,
             "weights": model.canonical_weights(), "optimizer": opt.state_dict(),
             "rng": rng.getstate(), "torch_rng": torch.get_rng_state(),
             "cuda_rng": torch.cuda.get_rng_state_all() if args.device == "cuda" else []},
             keep_previous=replace_previous)
        replace_previous = True

    base = validation(model, languages["validation"], dialogues["validation"],
                      codec, remap, args.language_context, args.batch, check)
    print(json.dumps({"validation_before": base}), flush=True)
    targets, elapsed = 0, 0.0
    first_step = step
    for _ in range(args.steps):
        check()
        began = time.monotonic()
        kind = cfg["schedule"][step % len(cfg["schedule"])]
        rows = (dialogues["train"].sample(rng, args.batch) if kind == "dialogue"
                else language_rows(languages["train"], rng, codec, args.language_context, args.batch))
        batch = make_batch(rows, codec, remap, args.device)
        opt.zero_grad(set_to_none=True)
        loss, count = objective(model, batch)
        require(bool(torch.isfinite(loss)), "NONFINITE_LOSS")
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), cfg["clip"], error_if_nonfinite=True)
        opt.step()
        model.project_fast(opt)
        step += 1
        targets += count
        elapsed += time.monotonic() - began
        print(json.dumps({"step": step, "kind": kind, "loss": loss.item(),
                          "gradient_norm": norm.item(), "targets": count}), flush=True)
        # The probe is intentionally short. Each fully committed step is recoverable.
        snapshot()
    end = validation(model, languages["validation"], dialogues["validation"],
                     codec, remap, args.language_context, args.batch, check)
    check()
    report = {"status": "PREFLIGHT_MECHANICS_MEASURED_LONG_TRAINING_BLOCKED",
              "configuration": cfg, "first_step": first_step, "step": step,
              "dialogue_coverage": coverage, "validation_before": base, "validation_after": end,
              "targets": targets, "update_targets_s": targets / max(elapsed, 1e-9),
              "peak_cuda_reserved_mib": torch.cuda.max_memory_reserved() / 2**20
              if args.device == "cuda" else None}
    write_report(args.out / args.report, report)
    print(json.dumps(report, ensure_ascii=False), flush=True)


def supervise(args):
    require(not args.out.exists() if not args.resume else args.out.is_dir(),
            "USE_NEW_OUTPUT_OR_EXPLICIT_RESUME")
    if not args.resume:
        args.out.mkdir(parents=True, exist_ok=False)
    identifier = str(time.time_ns())
    heartbeat = args.out / f".heartbeat-{identifier}"
    stop = args.out / f".stop-{identifier}"
    first = telemetry() if args.device == "cuda" else None
    gpu = first["uuid"] if first else "cpu"
    command = [sys.executable, str(HERE / "trainer.py"), *sys.argv[1:], "--worker",
               "--heartbeat", str(heartbeat), "--stop-file", str(stop), "--gpu-uuid", gpu,
               "--report", f"preflight-{identifier}.json"]
    kwargs = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    started = time.monotonic()
    max_seen = dict(first) if first else None
    child = subprocess.Popen(command, **kwargs)
    result = None
    try:
        while child.poll() is None:
            now = time.monotonic()
            if now - started >= args.seconds + 1:
                raise StopRequested("PREFLIGHT_TIME_LIMIT")
            if heartbeat.exists():
                require(time.time() - heartbeat.stat().st_mtime <= 40, "PREFLIGHT_NO_PROGRESS")
            elif now - started > 35:
                raise ValueError("PREFLIGHT_NO_HEARTBEAT")
            if first:
                sample = telemetry()
                require(sample["uuid"] == gpu, "GPU_CHANGED")
                for key in ("temperature_c", "memory_mib"):
                    max_seen[key] = max(max_seen[key], sample[key])
            time.sleep(1)
        result = child.returncode
        if first:
            sample = telemetry()
            require(sample["uuid"] == gpu, "GPU_CHANGED")
            for key in ("temperature_c", "memory_mib"):
                max_seen[key] = max(max_seen[key], sample[key])
        if result == 0:
            require((args.out / f"preflight-{identifier}.json").is_file(), "REPORT_MISSING")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"PREFLIGHT_ABORTED {error}", file=sys.stderr, flush=True)
        result = 1
    except (KeyboardInterrupt, StopRequested):
        stop.touch()
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.kill()
        result = 2
    finally:
        if child.poll() is None:
            child.kill()
        child.wait()
        heartbeat.unlink(missing_ok=True)
        stop.unlink(missing_ok=True)
    telemetry_report = {"worker_exit": result, "telemetry_peaks": max_seen,
                        "elapsed_seconds": time.monotonic() - started,
                        "worker_report": f"preflight-{identifier}.json" if result == 0 else None}
    write_report(args.out / f"supervisor-{identifier}.json", telemetry_report)
    print(json.dumps(telemetry_report), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["probe", "train"])
    parser.add_argument("--data", type=Path, default=Path(r"D:\UNO\corpus_prepared_v4"))
    parser.add_argument("--parent", type=Path, default=Path(r"D:\UNO\B2_512\latest.uno"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cuda")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--seconds", type=int, default=150)
    parser.add_argument("--batch", type=int, default=2)
    parser.add_argument("--language-context", type=int, default=64)
    parser.add_argument("--dialogue-limit", type=int, default=512)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--heartbeat", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--stop-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--gpu-uuid", help=argparse.SUPPRESS)
    parser.add_argument("--report", help=argparse.SUPPRESS)
    args = parser.parse_args()
    require(args.command == "probe", "LONG_TRAINING_BLOCKED: context quality, Android admission and owner approval are pending")
    require(1 <= args.steps <= 12 and 30 <= args.seconds <= 240 and 1 <= args.batch <= 4
            and 8 <= args.language_context <= 128 and 64 <= args.dialogue_limit <= 1024
            and math.isfinite(args.lr) and 0 < args.lr <= .001, "PREFLIGHT_SETTINGS")
    for path in (args.data, args.out, args.parent, HERE, Path(sys.executable)):
        if os.name == "nt":
            require(path.resolve().drive.casefold() == "d:", "WINDOWS_USE_DRIVE_D")
    args.out = args.out.resolve()
    return run_worker(args) if args.worker else supervise(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        sys.exit(str(error))
