"""Vectorized gap-coordinate L1 projection for UNO text FP32."""
import torch
from train001_backend import decoded_row_guard, project as reference_project

@torch.no_grad()
def project(row, cap):
    if row.ndim != 2 or row.shape[0] == 0 or row.dtype not in (torch.float32, torch.float64):
        raise ValueError("PROJECTION_SHAPE_OR_DTYPE")
    guard = decoded_row_guard(cap, row.shape[1])
    if not bool(torch.isfinite(row).all()):
        raise ValueError("NONFINITE_PARAMETER")
    x = row.detach().double()
    original_norm = x.abs().sum(-1)
    if bool((original_norm <= guard).all()):
        return row
    outside = original_norm > cap
    candidate = row.detach().clone()
    if bool(outside.any()):
        active = x[outside]
        largest = active.abs().amax(-1, keepdim=True)
        gaps = (largest - active.abs()).sort(-1).values
        k = torch.arange(1, row.shape[1]+1, dtype=torch.float64, device=row.device)
        delta = ((gaps.cumsum(-1) + cap) / k).amin(-1)
        q = active.sign() * (delta[:, None] - (largest-active.abs())).clamp_min(0)
        candidate[outside] = q.to(row.dtype)
    norm = candidate.double().abs().sum(-1)
    border = norm > guard
    if bool(border.any()):
        inner = decoded_row_guard(guard, row.shape[1])
        q = (candidate[border].double()*(inner/norm[border])[:,None]).to(row.dtype)
        candidate[border] = torch.nextafter(q, torch.zeros_like(q))
    if not bool(torch.isfinite(candidate).all()) or not bool((candidate.double().abs().sum(-1)<=guard).all()):
        return reference_project(row, cap)
    row.copy_(candidate)
    return row
