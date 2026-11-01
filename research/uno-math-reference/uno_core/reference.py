"""UNO mathematical reference v0.1: bounded unified recurrent state and evidence-gated plasticity.

This is a HOST REFERENCE, not an Android runtime, LLM or trusted OS security boundary.
Only standard Python library. A compute-unit count is an algorithmic proxy, NOT joules.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
import math
import random
import secrets
from typing import Callable, Optional, Sequence


MAX_DIM = 64
MAX_BUDGET = 1_000_000


def _finite(x: float) -> bool:
    return type(x) in (int, float) and math.isfinite(x)


def _sigmoid(x: float) -> float:
    if x >= 0.0:
        return 1.0 / (1.0 + math.exp(-x))
    v = math.exp(x)
    return v / (1.0 + v)


def _clip(x: float, limit: float = 1.0) -> float:
    return min(limit, max(-limit, x))


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return math.fsum(x * y for x, y in zip(a, b))


def _encode_json(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass(frozen=True)
class Weights:
    """Finite bounded trainable parameters. Rows W_enc[d,n], W_h[d,d], W_z[d,d], W_out[a,d]."""
    n: int
    d: int
    a: int
    w_enc: tuple[tuple[float, ...], ...]
    w_h: tuple[tuple[float, ...], ...]
    w_z: tuple[tuple[float, ...], ...]
    w_out: tuple[tuple[float, ...], ...]
    b_enc: tuple[float, ...]
    b_h: tuple[float, ...]
    b_out: tuple[float, ...]

    def __post_init__(self) -> None:
        if any(type(v) is not int or not 1 <= v <= MAX_DIM for v in (self.n, self.d, self.a)):
            raise ValueError("invalid dimensions")
        for matrix, rows, cols in (
            (self.w_enc, self.d, self.n),
            (self.w_h, self.d, self.d),
            (self.w_z, self.d, self.d),
            (self.w_out, self.a, self.d),
        ):
            if not isinstance(matrix, tuple) or len(matrix) != rows or any(not isinstance(row, tuple) or len(row) != cols for row in matrix):
                raise ValueError("matrix shape")
            if any(not _finite(x) or abs(x) > 10 for row in matrix for x in row):
                raise ValueError("invalid matrix weights")
        for vector, size in ((self.b_enc, self.d), (self.b_h, self.d), (self.b_out, self.a)):
            if not isinstance(vector, tuple) or len(vector) != size or any(not _finite(x) or abs(x) > 10 for x in vector):
                raise ValueError("invalid bias")

    @classmethod
    def initial(cls, n: int, d: int, a: int, seed: int = 73) -> "Weights":
        if any(type(x) is not int or not 1 <= x <= MAX_DIM for x in (n, d, a)):
            raise ValueError("invalid dimensions")
        r = random.Random(seed)
        mat = lambda rows, cols: tuple(tuple(r.uniform(-0.3, 0.3) for _ in range(cols)) for _ in range(rows))
        return cls(n, d, a, mat(d, n), mat(d, d), mat(d, d), mat(a, d),
                   (0.0,) * d, (0.0,) * d, (0.0,) * a)

    def identity_encoder(self) -> "Weights":
        if self.n != self.d:
            raise ValueError("identity encoder requires n == d")
        return replace(self, w_enc=tuple(tuple(float(i == j) for j in range(self.n)) for i in range(self.d)))

    def digest(self) -> str:
        return sha256(_encode_json(self.__dict__)).hexdigest()


@dataclass(frozen=True)
class Proposal:
    ident: int
    epoch: int
    action: int
    probabilities: tuple[float, ...]
    trace: tuple[float, ...]
    used_units: int
    iterations: int
    active_rows: tuple[int, ...]


@dataclass(frozen=True)
class Policy:
    """External authority snapshot. Default DENY; the neural model cannot grant privileges."""
    owner: bool = False
    permission: bool = False
    confirmed: bool = False
    unlocked: bool = False
    stopped: bool = True
    epoch: int = 0
    permitted_actions: tuple[int, ...] = ()


@dataclass(frozen=True)
class Ticket:
    """Transient ticket issued by trusted boundary, not by neural output."""
    nonce: str
    proposal_id: int
    epoch: int
    action: int


class Organism:
    """Stateful mathematical reference. No Android, network or device-authority methods."""

    def __init__(self, weights: Weights, *, rho: float = 0.5, delta: float = 0.2,
                 tau: float = 0.15, eta: float = 0.8, forgetting: float = 0.0,
                 plastic_cap: float = 4.0, max_steps: int = 4):
        vals = (rho, delta, tau, eta, forgetting, plastic_cap)
        if any(not _finite(x) for x in vals) or not 0 <= rho <= 1 or not 0 < delta <= 1 or not 0 <= tau < 1 or not 0 < eta <= 1 or not 0 <= forgetting < 1 or not 0 < plastic_cap <= 10:
            raise ValueError("invalid hyperparameters")
        if type(max_steps) is not int or not 0 <= max_steps <= 16:
            raise ValueError("invalid max_steps")
        self.weights = weights
        self.rho, self.delta, self.tau = rho, delta, tau
        self.eta, self.forgetting, self.plastic_cap = eta, forgetting, plastic_cap
        self.max_steps = max_steps
        self.h = [0.0] * weights.d
        self.p = [[0.0] * weights.d for _ in range(weights.a)]
        self.epoch = 0
        self.serial = 0
        self.learning_events = 0
        self.last_units = 0
        self._proposal: Optional[Proposal] = None

    def epoch_stop(self) -> None:
        self.epoch += 1
        self._proposal = None

    @property
    def minimum_units(self) -> int:
        # Matrix-vector multiply-accumulates only: encoder + base readout + plastic readout.
        # Not a measurement of CPU cycles, wall time, total FLOPs or joules.
        w = self.weights
        return w.d * w.n + 2 * w.a * w.d

    def step(self, stimulus: Sequence[float], *, budget_units: int) -> Optional[Proposal]:
        """Return a PROPOSAL only. No permission, actuator, readback or learning here."""
        w = self.weights
        if len(stimulus) != w.n or any(not _finite(x) or abs(x) > 1e6 for x in stimulus):
            raise ValueError("invalid stimulus")
        if type(budget_units) is not int or not 0 <= budget_units <= MAX_BUDGET:
            raise ValueError("invalid budget")
        self.last_units = 0
        self._proposal = None  # any newer observation, including IDLE, invalidates past pending action
        if budget_units < self.minimum_units or all(x == 0 for x in stimulus):
            return None  # truly skip encoder/readout/recurrent multiply
        z = []
        for j in range(w.d):
            z.append(math.tanh(_dot(w.w_enc[j], stimulus) + w.b_enc[j]))
        active = tuple(i for i, val in enumerate(z) if abs(val) > self.tau)
        # Projected leaky state. This and every recurrent step are bounded in [-1,1].
        h = [_clip(self.rho * prev + (1.0 - self.rho) * enc) for prev, enc in zip(self.h, z)]
        units = self.minimum_units
        per_iter = len(active) * (2 * w.d)
        k = min(self.max_steps, (budget_units - units) // per_iter) if per_iter else 0
        for _ in range(k):
            next_h = h.copy()
            for j in active:  # no matrix rows computed for masked-out channels
                r = math.tanh(_dot(w.w_h[j], h) + _dot(w.w_z[j], z) + w.b_h[j])
                next_h[j] = _clip(h[j] + self.delta * r)
            h = next_h
            units += per_iter
        logits = [_dot(w.w_out[i], h) + _dot(self.p[i], h) + w.b_out[i] for i in range(w.a)]
        if any(not _finite(x) for x in logits):
            raise ArithmeticError("nonfinite logits")
        probabilities = tuple(_sigmoid(val) for val in logits)
        action = max(range(w.a), key=lambda i: probabilities[i])
        if units > budget_units:
            raise ArithmeticError("compute budget exceeded")
        self.serial += 1
        self.h = h
        self.last_units = units
        proposal = Proposal(self.serial, self.epoch, action, probabilities,
                            tuple(h), units, k, active)
        self._proposal = proposal
        return proposal

    def _learn_from_authority(self, proposal: Proposal, outcome: int) -> bool:
        """Called only by the trusted boundary after a fresh readback; one-time update."""
        if outcome not in (0, 1) or type(outcome) is not int:
            raise ValueError("binary observed outcome required")
        if self._proposal != proposal or proposal.epoch != self.epoch:
            return False
        row = proposal.action
        h = proposal.trace
        denominator = math.fsum(x*x for x in h) + 1e-8
        old = self.p[row]
        prediction = proposal.probabilities[row]
        scale = self.eta * (float(outcome) - prediction) / denominator
        new = [_clip((1 - self.forgetting) * p + scale * v, self.plastic_cap) for p, v in zip(old, h)]
        if any(not _finite(x) for x in new):
            raise ArithmeticError("nonfinite plastic update")
        self.p[row] = new
        self.learning_events += 1
        self._proposal = None
        return True

    def config_digest(self) -> str:
        return sha256(_encode_json({"weights": self.weights.digest(),
            "rho": self.rho, "delta": self.delta, "tau": self.tau,
            "eta": self.eta, "forgetting": self.forgetting,
            "plastic_cap": self.plastic_cap, "max_steps": self.max_steps})).hexdigest()

    def snapshot(self) -> bytes:
        value = {"format": "UNO_SNAPSHOT_1", "weights": self.config_digest(),
                 "h": self.h, "p": self.p, "epoch": self.epoch,
                 "serial": self.serial, "learning_events": self.learning_events}
        raw = _encode_json(value)
        return _encode_json({"payload": value, "sha256": sha256(raw).hexdigest()})

    def restore(self, blob: bytes) -> None:
        """Validate entire snapshot before mutating any state (fail-closed)."""
        if not isinstance(blob, bytes) or len(blob) > 1_000_000:
            raise ValueError("invalid snapshot bytes")
        outer = json.loads(blob.decode("utf-8"))
        if not isinstance(outer, dict) or set(outer) != {"payload", "sha256"}:
            raise ValueError("invalid snapshot envelope")
        value = outer["payload"]
        if sha256(_encode_json(value)).hexdigest() != outer["sha256"]:
            raise ValueError("snapshot checksum")
        if not isinstance(value, dict) or set(value) != {"format", "weights", "h", "p", "epoch", "serial", "learning_events"}:
            raise ValueError("snapshot schema")
        if value["format"] != "UNO_SNAPSHOT_1" or value["weights"] != self.config_digest():
            raise ValueError("incompatible model")
        h, p = value["h"], value["p"]
        if not isinstance(h, list) or len(h) != self.weights.d or not isinstance(p, list) or len(p) != self.weights.a or any(not isinstance(row, list) or len(row) != self.weights.d for row in p):
            raise ValueError("snapshot shape")
        if any(not _finite(v) or abs(v) > 1 for v in h) or any(not _finite(v) or abs(v) > self.plastic_cap for row in p for v in row):
            raise ValueError("snapshot bounds")
        for key in ("epoch", "serial", "learning_events"):
            if type(value[key]) is not int or not 0 <= value[key] <= 2**63 - 1:
                raise ValueError("snapshot counters")
        # The only state mutations happen after full validation.
        self.h, self.p = h[:], [row[:] for row in p]
        self.epoch = value["epoch"]
        self.serial = value["serial"]
        self.learning_events = value["learning_events"]
        self._proposal = None  # never resurrect an in-flight device operation
        self.last_units = 0


class TrustedBoundary:
    """HOST SIMULATION of OS authority + native readback; NOT a device security boundary.

    In Android this must be implemented by OS-backed permissions/confirmation and
    a native independently sourced readback. Never accept model text as evidence.
    """

    def __init__(self, core: Organism):
        self.core = core
        self._pending: dict[str, Ticket] = {}

    def authorize(self, proposal: Proposal, policy: Policy) -> Optional[Ticket]:
        c = self.core
        valid = (policy.owner and policy.permission and policy.confirmed and policy.unlocked
                 and not policy.stopped and policy.epoch == c.epoch
                 and proposal.epoch == c.epoch and c._proposal == proposal
                 and proposal.action in policy.permitted_actions)
        if not valid:
            return None
        ticket = Ticket(secrets.token_hex(16), proposal.ident, proposal.epoch, proposal.action)
        self._pending[ticket.nonce] = ticket
        return ticket

    def finish(self, ticket: Ticket, *, expected: object,
               native_readback: Callable[[], object]) -> str:
        """Only a fresh one-time ticket can learn; unknown observations are never learned."""
        if self._pending.get(ticket.nonce) != ticket:
            return "REJECTED_TICKET"
        del self._pending[ticket.nonce]
        proposal = self.core._proposal
        if proposal is None or proposal.ident != ticket.proposal_id or proposal.epoch != ticket.epoch or self.core.epoch != ticket.epoch or proposal.action != ticket.action:
            return "STALE"
        try:
            actual = native_readback()
        except Exception:
            return "UNKNOWN"
        if actual is None or expected is None:
            return "UNKNOWN"
        # Reject 0/False ambiguity in Python for explicitly typed native states.
        if type(actual) is not type(expected):
            return "UNKNOWN"
        result = 1 if actual == expected else 0
        if not self.core._learn_from_authority(proposal, result):
            return "STALE"
        return "CONFIRMED" if result == 1 else "CONTRADICTED"


# Offline mini-experiment: learn newly initialized UNO readout weights using
# analytic softmax cross-entropy gradient. This is NOT general-language training.
def readout_loss_and_gradient(w_out: Sequence[Sequence[float]], features: Sequence[float], target: int):
    n_actions = len(w_out)
    if not n_actions or not 0 <= target < n_actions or any(len(row) != len(features) for row in w_out):
        raise ValueError("shape/target")
    logits = [_dot(row, features) for row in w_out]
    high = max(logits)
    ex = [math.exp(t - high) for t in logits]
    total = sum(ex)
    probs = [v / total for v in ex]
    loss = high + math.log(total) - logits[target]  # stable log-sum-exp even for tiny probabilities
    gradient = [[(probs[i] - float(i == target)) * f for f in features] for i in range(n_actions)]
    return loss, gradient


def train_new_readout(samples: Sequence[tuple[Sequence[float], int]], *, dim: int,
                      n_actions: int, epochs: int = 80, learning_rate: float = 0.2, seed: int = 11):
    """Fresh weights trained from random initialization; deterministic SGD."""
    if not samples or not 1 <= dim <= MAX_DIM or not 1 <= n_actions <= MAX_DIM or not 1 <= epochs <= 1000 or not 0 < learning_rate <= 1:
        raise ValueError("invalid training configuration")
    rand = random.Random(seed)
    w = [[rand.uniform(-0.05, 0.05) for _ in range(dim)] for _ in range(n_actions)]
    for _ in range(epochs):
        for features, target in samples:
            if len(features) != dim or any(not _finite(v) or abs(v) > 10 for v in features) or not 0 <= target < n_actions:
                raise ValueError("invalid training sample")
            _, grad = readout_loss_and_gradient(w, features, target)
            for i in range(n_actions):
                for j in range(dim):
                    w[i][j] -= learning_rate * grad[i][j]
    return tuple(tuple(row) for row in w)


def masked_recurrence_jacobian(weights: Weights, h: Sequence[float], z: Sequence[float],
                               active_rows: Sequence[int], delta: float):
    """Analytic d(h_next)/d(h) for one projected masked recurrence step.

    Valid only away from the nondifferentiable clipping boundary. Returns None
    if projection hits +/-1 on any active row. Not used to train UNO yet.
    """
    if len(h) != weights.d or len(z) != weights.d or not _finite(delta) or not 0 < delta <= 1:
        raise ValueError("jacobian shape or delta")
    if any(not _finite(x) or abs(x) > 1 for x in h) or any(not _finite(x) for x in z):
        raise ValueError("jacobian nonfinite")
    if len(set(active_rows)) != len(active_rows) or any(type(j) is not int or not 0 <= j < weights.d for j in active_rows):
        raise ValueError("invalid active rows")
    jmat = [[float(i == j) for j in range(weights.d)] for i in range(weights.d)]
    for i in active_rows:
        u = _dot(weights.w_h[i], h) + _dot(weights.w_z[i], z) + weights.b_h[i]
        r = math.tanh(u)
        if abs(h[i] + delta*r) >= 1.0:
            return None  # derivative of clip at boundary is not defined
        factor = delta * (1.0 - r*r)
        jmat[i] = [float(i == j) + factor*weights.w_h[i][j] for j in range(weights.d)]
    return tuple(tuple(row) for row in jmat)
