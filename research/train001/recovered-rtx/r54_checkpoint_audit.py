"""Read-only TRAIN001 selected-checkpoint audit; not a production weight admission."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import pathlib
import tempfile
from fractions import Fraction

import torch
from torch_backend import TorchF


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def exact_tensor_report(name, tensor, rows, cols, cap, box, dtype):
    need(isinstance(tensor, torch.Tensor) and tensor.layout == torch.strided
         and tensor.dtype == dtype and tuple(tensor.shape) == (rows, cols),
         'TENSOR_GEOMETRY ' + name)
    need(bool(torch.isfinite(tensor).all()), 'NONFINITE_TENSOR ' + name)
    limit = Fraction(str(cap))  # decimal contract, not rounded binary64 cap
    max_norm = Fraction(0)
    violations = 0
    for row in tensor.detach().cpu().tolist():
        terms = [Fraction(abs(v)) for v in row]
        norm = max(terms) if box else sum(terms, Fraction(0))
        max_norm = max(max_norm, norm)
        violations += int(norm > limit)
    return dict(name=name, shape=[rows, cols], box=box, cap=str(cap),
                max_decoded_norm=float(max_norm),
                max_excess=float(max(Fraction(0), max_norm-limit)),
                violating_rows=violations)


def audit_selected(checkpoint, initial, trusted_sha):
    need(len(trusted_sha) == 64 and all(c in '0123456789abcdef' for c in trusted_sha),
         'TRUSTED_SHA_REQUIRED')
    need(1 <= checkpoint.stat().st_size <= 64*1024*1024+128, 'CHECKPOINT_SIZE')
    blob = checkpoint.read_bytes()
    need(digest(blob) == trusted_sha, 'CHECKPOINT_TRUSTED_SHA_MISMATCH')
    head, body_sha, body = blob.split(b'\n', 2)
    need(head == b'UNO-TORCH-S4/V1' and body_sha == digest(body).encode(), 'CHECKPOINT_INTEGRITY')
    state = torch.load(io.BytesIO(body), map_location='cpu', weights_only=True)
    cfg = state['config']
    need(cfg['precision'] in ('float32', 'double'), 'CHECKPOINT_PRECISION')
    dtype = {'float32': torch.float32, 'double': torch.float64}[cfg['precision']]
    need(type(state['selected']) is int and type(state['step']) is int
         and 0 <= state['selected'] <= state['step'], 'CHECKPOINT_SELECTED_STEP')
    need(1 <= initial.stat().st_size <= 16*1024*1024, 'INITIAL_SIZE')
    layout = initial.read_bytes()
    need(digest(layout) == cfg['input']['initial.tsv'], 'INITIAL_SHA_MISMATCH')
    # Use the existing validated inventory, from a private snapshot of the pinned input.
    # Never load the selected weights into a runtime slot, write a checkpoint, or train.
    with tempfile.TemporaryDirectory() as tmp:
        p = pathlib.Path(tmp)/'initial.tsv'
        p.write_bytes(layout)
        model = TorchF(p, dtype, 'cpu')
    selected = state['best']
    need(set(selected) == set(model.state_dict()), 'CHECKPOINT_SLOT_SET')
    report = [exact_tensor_report(name, selected[f'slots.{i}'], rows, cols, cap, box, dtype)
              for i, (name, rows, cols, cap, box) in enumerate(model.rules)]
    bad = sum(r['violating_rows'] for r in report)
    need(digest(checkpoint.read_bytes()) == trusted_sha, 'CHECKPOINT_CHANGED')
    return dict(status='REJECTED_DECODED_CAP' if bad else 'TRAIN001_CAPS_PASS_NOT_ADMISSION',
                checkpoint_sha256=trusted_sha, selected_step=state['selected'],
                saved_step=state['step'], precision=cfg['precision'],
                initial_sha256=digest(layout), tensors=len(report),
                rows=sum(r['shape'][0] for r in report), violating_rows=bad,
                violating_tensors=sum(r['violating_rows'] > 0 for r in report),
                max_excess=max(r['max_excess'] for r in report),
                production_abi='NOT_PRESENT', runtime_admitted=False, tensor_reports=report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('checkpoint', type=pathlib.Path)
    parser.add_argument('initial', type=pathlib.Path)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    report = audit_selected(args.checkpoint, args.initial, args.sha256)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(2 if report['violating_rows'] else 0)
