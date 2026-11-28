"""Causal dialogue batches for the existing B2-512 operator."""
import json
import re

import torch
from torch.nn import functional as F

from fast_model03 import FastB2
from train_cuda_fast03 import TOK_SHA, require, sha

POSITION_SCALE = 128
SPLITS = ("train", "validation", "test")


class CausalB2(FastB2):
    def scan(self, tokens, state=None, start=0, packed=None):
        """Preserve state and absolute position across calls."""
        batch, length = tokens.shape
        p = self.p
        if state is None:
            state = p["U_s"].new_zeros(batch, self.d)
        A, C, B, a, b = self.packed() if packed is None else packed
        meta = p["W_meta"].new_zeros(length, 32)
        meta[:, 1] = 1
        meta[:, 4] = 1
        meta[:, 14] = (torch.arange(start, start + length, device=tokens.device)
                       / POSITION_SCALE).clamp(max=1)
        metadata = F.linear(meta, p["W_meta"])
        embedded = p["E_text"][self.remap_text[tokens]]
        modality = p["e_modality"].view(6, self.d)[0]
        states = []
        for t in range(length):
            z0 = torch.tanh(embedded[:, t] + F.linear(state, p["U_s"])
                            + metadata[t] + modality + p["b_z"])
            z = torch.tanh(z0)
            h = .5 * state + .5 * z
            u = torch.tanh(F.linear(h, A) + F.linear(z, C, a))
            u = u.reshape(batch, self.n * 2, 256)
            branch = torch.tanh(torch.bmm(u.transpose(0, 1), B.transpose(1, 2))
                                .transpose(0, 1) + b)
            state = .5 * h + .5 * branch.reshape(batch, self.n, 2, 64).mean(2).reshape(batch, self.d)
            states.append(state)
        return torch.stack(states, dim=1), state

    def readout(self, states):
        return F.linear(states, self.p["E_text"], self.p["b_text"])

    def language(self, x, active_ids, K=1):
        require(K == 1, "FIXED_K1_ONLY")
        return self.readout(self.scan(x)[0])


def corpus_identity(data, check):
    root = data.resolve(strict=True)
    manifest = root / "SHA256SUMS.txt"
    require(manifest.is_file() and not root.name.endswith(".building"), "CORPUS_INCOMPLETE")
    seen = set()
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, relative = line.split(maxsplit=1)
        relative = relative.removeprefix("*")
        path = (root / relative).resolve(strict=True)
        require(re.fullmatch(r"[0-9a-f]{64}", digest) and path.is_relative_to(root)
                and path not in seen and path.is_file(), "CORPUS_MANIFEST_ENTRY")
        check()
        require(sha(path) == digest, f"CORPUS_HASH {relative}")
        seen.add(path)
    expected = ["tokenizer.json", "report.json"]
    expected += [f"{kind}/{split}.jsonl" for kind in ("language", "dialogue")
                 for split in SPLITS]
    for name in expected:
        require((root / name).resolve() in seen, f"CORPUS_MISSING {name}")
    require(sha(root / "tokenizer.json") == TOK_SHA, "CORPUS_TOKENIZER")
    report = json.loads((root / "report.json").read_text(encoding="utf-8"))
    require(report.get("schema") == "UNO-CORPUS-PREP/4"
            and report.get("status") == "RESEARCH_CORPUS_NOT_COMMERCIAL_APPROVAL"
            and report.get("missing") == [] and report.get("retained_cross_split_keys") == 0,
            "FIX04_REPORT_REQUIRED")
    return sha(manifest)


class Dialogues:
    """Index only complete records and report every exclusion by source."""
    def __init__(self, path, codec, limit, check=lambda: None):
        self.rows = []
        self.coverage = {}
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                check()
                record = json.loads(line)
                messages = record["messages"]
                require(isinstance(messages, list) and len(messages) >= 2
                        and len(messages) % 2 == 0
                        and all(isinstance(m["text"], str) and m["text"].strip()
                                for m in messages), "DIALOGUE_SCHEMA")
                ids, mask = codec.record(record, "dialogue")
                stats = self.coverage.setdefault(record["source"], {"total": 0, "kept": 0})
                stats["total"] += 1
                if len(ids) - 1 <= limit:
                    self.rows.append((ids, mask))
                    stats["kept"] += 1
        require(self.rows, "NO_COMPLETE_DIALOGUES_WITHIN_LIMIT")
        self.order = sorted(range(len(self.rows)), key=lambda i: len(self.rows[i][0]))
        self.position = {row: pos for pos, row in enumerate(self.order)}

    def sample(self, rng, size):
        anchor = rng.randrange(len(self.rows))
        pos = self.position[anchor]
        neighbors = self.order[max(0, pos - size * 2):pos + size * 2 + 1]
        rng.shuffle(neighbors)
        return [self.rows[i] for i in [anchor] + [i for i in neighbors if i != anchor][:size - 1]]


def make_batch(rows, codec, remap, device):
    length = max(len(tokens) - 1 for tokens, _ in rows)
    x, y, masks = [], [], []
    for tokens, mask in rows:
        require(len(tokens) == len(mask) and all(t in codec.allowed for t in tokens),
                "INVALID_BATCH_RECORD")
        padding = length + 1 - len(tokens)
        x.append(tokens[:-1] + [codec.bos] * padding)
        y.append(tokens[1:] + [codec.eos] * padding)
        masks.append(mask[1:] + [False] * padding)
    inputs = torch.tensor(x, device=device)
    targets = remap[torch.tensor(y, device=device)]
    mask = torch.tensor(masks, device=device, dtype=torch.bool)
    require(bool(mask.any()), "NO_TRAINING_TARGETS")
    return inputs, targets, mask


def language_rows(records, rng, codec, length, batch):
    # Each window belongs to one document and starts with an explicit reset.
    rows = []
    for _ in range(batch):
        tokens, mask, _ = records.encoded(rng.randrange(len(records.offsets)), codec)
        start = rng.randint(0, max(0, len(tokens) - 1 - length))
        rows.append((tokens[start:start + length + 1], mask[start:start + length + 1]))
    return rows


def objective(model, batch):
    x, y, mask = batch
    states, _ = model.scan(x)
    logits = model.readout(states[mask])
    return F.cross_entropy(logits.float(), y[mask]), int(mask.sum().item())


@torch.inference_mode()
def generate(model, codec, prefix, count):
    device = next(model.parameters()).device
    packed = model.packed()
    _, state = model.scan(torch.tensor([prefix], device=device), packed=packed)
    result = []
    for position in range(len(prefix), len(prefix) + count):
        token = codec.ids[int(model.readout(state).argmax().item())]
        if token in (codec.bos, codec.eos):
            return result, token == codec.eos
        result.append(token)
        _, state = model.scan(torch.tensor([[token]], device=device), state, position, packed)
    return result, False


def remapping(codec, device):
    ids = torch.tensor(codec.ids, device=device)
    remap = torch.full((32768,), -1, device=device, dtype=torch.long)
    remap[ids] = torch.arange(len(ids), device=device)
    return ids, remap
