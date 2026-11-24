"""R5.4 candidate erratum 12: offline S6 score objective, not training.
Conditional smooth law for fixed feasible prefixes, rotation and causal histories.
No unbiasedness claim for finite PRNG, floating CDF, rejection or aborts.
"""
from dataclasses import dataclass
import math
import torch


def _require(ok, reason):
    if not bool(ok):
        raise ValueError(reason)


def _scalar(x):
    return isinstance(x, torch.Tensor) and x.dtype == torch.float64 and x.ndim == 0 and bool(torch.isfinite(x))


def prefix_log_probs(logits, feasible_count, turn_serial, epsilon=.05, temperature=1.):
    """Marginal epsilon-mixture, not the score of the latent explore branch.
    Feasible q=1..count as in UnoS6Sampler. Empty support is terminal.
    """
    _require(isinstance(logits, torch.Tensor) and logits.dtype == torch.float64
             and logits.ndim == 1 and torch.isfinite(logits).all(), 'LOGITS')
    n = logits.numel()
    _require(type(feasible_count) is int and 1 <= feasible_count <= n, 'FIXED_NONEMPTY_SUPPORT')
    _require(type(turn_serial) is int and 0 <= turn_serial <= 2**63-1, 'TURN')
    _require(math.isfinite(epsilon) and 0 <= epsilon <= 1 and math.isfinite(temperature) and temperature > 0, 'POLICY_DOMAIN')
    rotated = torch.roll(logits, -(turn_serial % n))
    total = logits.new_zeros(())
    scores = []
    for q in range(1, feasible_count+1):
        total = total + rotated[q-1]
        _require(torch.isfinite(total), 'PREFIX_OVERFLOW')
        scores.append(total / math.sqrt(q))
    a = torch.stack(scores)
    delta = a-a.max().detach()
    _require(torch.isfinite(delta).all(), 'SCORE_DIFFERENCE')
    if feasible_count == 1:
        return delta * 0.
    if epsilon == 1.:
        return delta*0. - math.log(feasible_count)
    scaled = delta / temperature
    _require(torch.isfinite(scaled).all(), 'SCALED_SCORE')
    _require((scaled.exp() > 0).all(), 'SOFTMAX_UNDERFLOW')
    s = torch.log_softmax(scaled, dim=0)
    if epsilon == 0.:
        return s
    return torch.logaddexp(s+math.log1p(-epsilon), s.new_tensor(math.log(epsilon)-math.log(feasible_count)))


def halt_log_prob(logit, stop):
    """Trainable hazard after actual S5 step. Fixed/forced choices omitted.
    Numerically saturated probabilities are outside smooth domain."""
    _require(_scalar(logit) and type(stop) is bool, 'HALT_DOMAIN')
    p = logit.detach().sigmoid()
    _require(0 < p < 1, 'HALT_SATURATION')
    return torch.nn.functional.logsigmoid(logit if stop else -logit)


@dataclass(frozen=True)
class Decision:
    log_prob: torch.Tensor
    cost_to_go: torch.Tensor
    baseline_before: torch.Tensor


def score_objective(path_loss, decisions):
    """Caller MUST form each baseline before its action, and exclude from G
    only costs already determined before it. Detach both coefficients;
    retain full pathwise graph. Forced decisions omitted. Value unchanged.
    Caller causality is not inferred from tensors."""
    _require(_scalar(path_loss), 'PATH_LOSS')
    result = path_loss
    for d in decisions:
        _require(isinstance(d, Decision) and all(_scalar(x) for x in (d.log_prob,d.cost_to_go,d.baseline_before)), 'DECISION_SCALAR')
        _require(d.log_prob <= 0, 'LOG_PROB')
        advantage = d.cost_to_go.detach()-d.baseline_before.detach()
        _require(torch.isfinite(advantage), 'ADVANTAGE_OVERFLOW')
        result = result + advantage*(d.log_prob-d.log_prob.detach())
    _require(torch.isfinite(result), 'SURROGATE_NONFINITE')
    return result
