#!/usr/bin/env python3
"""UNO-N0-01 — research-only event-driven neurons with NO scalar synaptic weights.

One shared neural event graph is rebuilt from verified experiences. It is a
symbolic/structural learning fixture, not a neural representation learned by
backpropagation or an autonomous Android agent.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import platform
import resource
import signal
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import monotonic

IDENTIFIER = "UNO-N0-01"
CARD_SHA256 = "ff7771226e50f50527bc6eecfaf41483cf692d1b2743873a14f050ab1404c34a"
BUDGET_SECONDS = 600
BUDGET_RAM_BYTES = 2 * 1024**3

FEATURES = ("SURFACE", "TREAD", "MAGNET", "MATERIAL", "DECOR")
VOCAB = {
    "SURFACE": ("DRY", "ICE"),
    "TREAD": ("PLAIN", "SPIKED"),
    "MAGNET": ("OFF", "ON"),
    "MATERIAL": ("WOOD", "STEEL", "GLASS", "CERAMIC"),
    "DECOR": ("RED", "BLUE"),
}
ACTIONS = ("PUSH_LEFT", "PUSH_RIGHT")
DIRECTIONS = ("LEFT", "RIGHT")
COPY = "COPY"
INVERT = "INVERT"


def inverse(value: str) -> str:
    if value not in DIRECTIONS:
        raise ValueError(f"Not a direction: {value}")
    return "RIGHT" if value == "LEFT" else "LEFT"


def transform(action: str, effect: str) -> str:
    direction = action.replace("PUSH_", "")
    if direction not in DIRECTIONS:
        raise ValueError(f"Invalid action: {action}")
    return direction if effect == COPY else inverse(direction)


def environment_readback(context: dict[str, str], action: str) -> str:
    """Truth only in *external simulator*, never called from graph inference/induction."""
    flip = ((context["SURFACE"] == "ICE" and context["TREAD"] == "PLAIN")
            or context["MAGNET"] == "ON")
    return transform(action, INVERT if flip else COPY)


def context(surface: str, tread: str, magnet: str, material: str, decor: str) -> dict[str, str]:
    ans = dict(SURFACE=surface, TREAD=tread, MAGNET=magnet,
               MATERIAL=material, DECOR=decor)
    if any(ans[key] not in VOCAB[key] for key in FEATURES):
        raise ValueError("Bad sensor token")
    return ans


def key_for(ctx: dict[str, str], action: str) -> tuple[str, ...]:
    return tuple(ctx[k] for k in FEATURES) + (action,)


@dataclass(frozen=True)
class Receipt:
    context: dict[str, str]
    action: str
    observed: str
    evidence_id: str
    verified: bool

    @property
    def effect(self) -> str:
        return COPY if transform(self.action, COPY) == self.observed else INVERT


# A neuron is an addressable stateful *event gate*. No floating or integer
# trainable parameter exists on a neuron or a synapse.
@dataclass(frozen=True)
class Neuron:
    name: str
    kind: str


@dataclass(frozen=True)
class Synapse:
    source: str
    target: str
    relation: str  # REQUIRES | EXCITES | INHIBITS, NOT a scalar weight.


Literal = tuple[str, str]
Guard = tuple[Literal, ...]


@dataclass(frozen=True)
class Program:
    default: str
    exceptions: tuple[Guard, ...]

    def effect(self, ctx: dict[str, str]) -> str:
        surprise = any(all(ctx[feature] == value for feature, value in guard)
                       for guard in self.exceptions)
        if surprise:
            return COPY if self.default == INVERT else INVERT
        return self.default

    def describe(self) -> str:
        if not self.exceptions:
            return f"DEFAULT {self.default}"
        clauses = [" AND ".join(f"{name}={value}" for name, value in guard)
                   for guard in self.exceptions]
        return f"DEFAULT {self.default}; FLIP DEFAULT WHEN " + " OR ".join(f"({c})" for c in clauses)


def all_guards() -> tuple[Guard, ...]:
    literals = tuple((f, value) for f in FEATURES for value in VOCAB[f])
    guards: list[Guard] = []
    for item in literals:
        guards.append((item,))
    for left, right in itertools.combinations(literals, 2):
        if left[0] != right[0]:
            guards.append(tuple(sorted((left, right))))
    return tuple(sorted(set(guards), key=lambda g: (len(g), g)))


GUARDS = all_guards()


def candidate_programs():
    """Global symbolic minimum-description fit; no gradient or learned scalars."""
    yield Program(COPY, ())
    yield Program(INVERT, ())
    for k in (1, 2):
        for total_literals in (k, k + 1, k + 2):
            groups = itertools.combinations(GUARDS, k)
            for gs in groups:
                if sum(map(len, gs)) != total_literals:
                    continue
                for default in (COPY, INVERT):
                    yield Program(default, gs)


def find_program(receipts: list[Receipt]) -> Program | None:
    # Induction knows no hidden physical law, only receipt.effect observed.
    if not receipts:
        return None
    evidence = tuple((r.context, r.effect) for r in receipts)
    for candidate in candidate_programs():
        if all(candidate.effect(c) == expected for c, expected in evidence):
            return candidate
    return None


class EventGraph:
    """Shared event graph with explicit neurons/synapses and nonnumeric activation.

    The graph is recompilable; mutations are changes of neurons and topology.
    """

    def __init__(self, program: Program):
        self.program = program
        neurons: dict[str, Neuron] = {}
        synapses: set[Synapse] = set()

        def put(name: str, kind: str):
            if name not in neurons:
                neurons[name] = Neuron(name, kind)

        for feature in FEATURES:
            for value in VOCAB[feature]:
                put(f"SENSE:{feature}={value}", "SENSORY")
        for action in ACTIONS:
            put(f"ACTION:{action}", "ACTION")
        for direction in DIRECTIONS:
            put(f"MOTOR:{direction}", "MOTOR")
        for trans in (COPY, INVERT):
            put(f"EFFECT:{trans}", "CONSEQUENCE")
        put("RULE:DEFAULT", "DEFAULT_GATE")
        synapses.add(Synapse("RULE:DEFAULT", f"EFFECT:{program.default}", "EXCITES"))

        self.condition_names: tuple[str, ...] = ()
        names = []
        for guard in program.exceptions:
            label = "RULE:" + "&".join(f"{f}={v}" for f, v in guard)
            put(label, "CONJUNCTION_GATE")
            names.append(label)
            for feature, value in guard:
                synapses.add(Synapse(f"SENSE:{feature}={value}", label, "REQUIRES"))
            opposite = INVERT if program.default == COPY else COPY
            synapses.add(Synapse(label, f"EFFECT:{opposite}", "EXCITES"))
            synapses.add(Synapse(label, "RULE:DEFAULT", "INHIBITS"))
        self.condition_names = tuple(names)

        # Motor circuit: two actions x two consequences, all Boolean/conjunctive.
        for act in ACTIONS:
            for consequence in (COPY, INVERT):
                label = f"MOTOR_GATE:{act}:{consequence}"
                put(label, "CONJUNCTION_GATE")
                synapses.add(Synapse(f"ACTION:{act}", label, "REQUIRES"))
                synapses.add(Synapse(f"EFFECT:{consequence}", label, "REQUIRES"))
                synapses.add(Synapse(label, f"MOTOR:{transform(act, consequence)}", "EXCITES"))
        self.neurons = tuple(neurons.values())
        self.synapses = tuple(sorted(synapses, key=lambda x: (x.source, x.target, x.relation)))
        self.requires: dict[str, set[str]] = {}
        self.excites: dict[str, set[str]] = {}
        self.inhibits: dict[str, set[str]] = {}
        for edge in self.synapses:
            source = {"REQUIRES": self.requires, "EXCITES": self.excites,
                      "INHIBITS": self.inhibits}[edge.relation]
            source.setdefault(edge.target if edge.relation == "REQUIRES" else edge.source,
                              set()).add(edge.source if edge.relation == "REQUIRES" else edge.target)

    def infer(self, ctx: dict[str, str], action: str) -> str | None:
        # No weighted sums, activation thresholds, neural attention, or scalars.
        active = {f"SENSE:{f}={ctx[f]}" for f in FEATURES}
        active.add(f"ACTION:{action}")
        firing_rules = {label for label in self.condition_names
                        if self.requires.get(label, set()) <= active}
        active |= firing_rules
        if "RULE:DEFAULT" not in {blocked for label in firing_rules
                                   for blocked in self.inhibits.get(label, set())}:
            active.add("RULE:DEFAULT")
        for label in tuple(firing_rules) + ("RULE:DEFAULT",):
            if label in active:
                active |= self.excites.get(label, set())
        for label, neuron in ((n.name, n) for n in self.neurons
                              if n.kind == "CONJUNCTION_GATE" and n.name.startswith("MOTOR_GATE:")):
            if self.requires.get(label, set()) <= active:
                active.add(label)
                active |= self.excites.get(label, set())
        outputs = {name for name in active if name.startswith("MOTOR:")}
        if len(outputs) != 1:
            return None
        return next(iter(outputs)).replace("MOTOR:", "")

    def validate_no_scalar_synapses(self) -> bool:
        return all(type(x) is str for neuron in self.neurons
                   for x in (neuron.name, neuron.kind)) and all(
                       type(x) is str for edge in self.synapses
                       for x in (edge.source, edge.target, edge.relation))


class StructuralNeurons:
    def __init__(self):
        self.receipts: list[Receipt] = []
        self.conflicts: set[tuple[str, ...]] = set()
        self.program: Program | None = None
        self.graph: EventGraph | None = None
        self.history: list[str] = []
        self.state = "UNTRAINED"

    def observe(self, receipt: Receipt):
        if not receipt.verified:
            raise ValueError("Unverified feedback is not learning evidence")
        if receipt.action not in ACTIONS or receipt.observed not in DIRECTIONS:
            raise ValueError("Malformed receipt")
        if set(receipt.context) != set(FEATURES):
            raise ValueError("Malformed context")
        self.receipts.append(receipt)
        by_key: dict[tuple[str, ...], set[str]] = {}
        for item in self.receipts:
            by_key.setdefault(key_for(item.context, item.action), set()).add(item.observed)
        self.conflicts = {key for key, vals in by_key.items() if len(vals) > 1}
        usable = [r for r in self.receipts if key_for(r.context, r.action) not in self.conflicts]
        self.program = find_program(usable)
        self.graph = EventGraph(self.program) if self.program else None
        self.state = ("CONFLICT" if self.conflicts else
                      "STRUCTURALLY_LEARNED" if self.graph else "NO_CONSISTENT_GRAPH")
        if self.graph and not self.graph.validate_no_scalar_synapses():
            raise AssertionError("Numeric synapse encountered")

    def predict(self, ctx: dict[str, str], action: str) -> str | None:
        if key_for(ctx, action) in self.conflicts or self.graph is None:
            return None
        return self.graph.infer(ctx, action)

    def choose(self, ctx: dict[str, str], target: str) -> str | None:
        for action in ACTIONS:
            if self.predict(ctx, action) == target:
                return action
        return None


class FixedCopy:
    def observe(self, _: Receipt):
        pass

    def choose(self, _: dict[str, str], target: str) -> str:
        return f"PUSH_{target}"


class LatestOnly:
    def __init__(self):
        self.transform: str | None = None

    def observe(self, r: Receipt):
        self.transform = r.effect

    def choose(self, _: dict[str, str], target: str) -> str | None:
        if self.transform is None:
            return None
        return f"PUSH_{target if self.transform == COPY else inverse(target)}"


class Lookup:
    def __init__(self, factored: bool):
        self.columns = ("SURFACE", "TREAD", "MAGNET") if factored else FEATURES
        self.table: dict[tuple[str, ...], str] = {}

    def observe(self, r: Receipt):
        self.table[tuple(r.context[f] for f in self.columns) + (r.action,)] = r.observed

    def choose(self, ctx: dict[str, str], target: str) -> str | None:
        for act in ACTIONS:
            if self.table.get(tuple(ctx[f] for f in self.columns) + (act,)) == target:
                return act
        return None


class OneExceptionNeurons(StructuralNeurons):
    """Same neural representation; deliberately restricted to 1 exception gate."""
    def observe(self, receipt: Receipt):
        super().observe(receipt)
        if self.program and len(self.program.exceptions) > 1:
            self.program = None
            self.graph = None
            self.state = "NEEDS_TWO_EXCEPTIONS"


def observed_phase(phase: str) -> list[Receipt]:
    patterns = {
        "A": [("DRY", tread, "OFF") for tread in ("PLAIN", "SPIKED")],
        "B": [("ICE", "PLAIN", "OFF")],
        "C": [("ICE", "SPIKED", "OFF")],
        "D": [("DRY", tread, "ON") for tread in ("PLAIN", "SPIKED")],
    }[phase]
    records = []
    for surf, tread, mag in patterns:
        for mat, action in itertools.product(("WOOD", "STEEL"), ACTIONS):
            ctx = context(surf, tread, mag, mat, "RED")
            records.append(Receipt(ctx, action, environment_readback(ctx, action),
                                   f"{phase}-{len(records):02d}", True))
    return records


def query_group(name: str) -> list[dict[str, str]]:
    configurations = {
        "A": [("DRY", tread, "OFF") for tread in ("PLAIN", "SPIKED")],
        "B": [("ICE", "PLAIN", "OFF")],
        "C": [("ICE", "SPIKED", "OFF")],
        "D": [("DRY", tread, "ON") for tread in ("PLAIN", "SPIKED")],
    }
    if name == "UNSEEN_MATERIAL":
        return [context(surf, tread, mag, mat, "BLUE")
                for config in configurations.values() for surf, tread, mag in config
                for mat in ("GLASS", "CERAMIC")]
    if name == "UNSEEN_COMBINATION":
        return [context("ICE", tread, "ON", mat, "BLUE")
                for tread, mat in itertools.product(("PLAIN", "SPIKED"),
                                                     ("GLASS", "CERAMIC"))]
    return [context(surf, tread, mag, mat, "RED")
            for surf, tread, mag in configurations[name]
            for mat in ("WOOD", "STEEL")]


def evaluate(agent, queries: list[dict[str, str]]) -> dict:
    correct = 0
    unknown = 0
    details = []
    for ctx, target in itertools.product(queries, DIRECTIONS):
        chosen = agent.choose(ctx, target)
        if chosen is None:
            unknown += 1
        else:
            verified = environment_readback(ctx, chosen)
            if verified == target:
                correct += 1
            else:
                details.append({"context": ctx, "target": target,
                                "chosen": chosen, "actual": verified})
    total = len(queries) * len(DIRECTIONS)
    return {"correct": correct, "total": total, "unknown": unknown,
            "accuracy": correct / total, "errors": details}


def limit_process():
    try:
        resource.setrlimit(resource.RLIMIT_AS, (BUDGET_RAM_BYTES, BUDGET_RAM_BYTES))
    except (ValueError, OSError):
        pass

    def expired(signum, frame):
        raise TimeoutError("Research time budget reached")

    signal.signal(signal.SIGALRM, expired)
    signal.alarm(BUDGET_SECONDS)


def main():
    start = monotonic()
    card = Path(__file__).with_name("EXPERIMENT_CARD_PRE_REGISTERED.md")
    actual = hashlib.sha256(card.read_bytes()).hexdigest()
    if actual != CARD_SHA256:
        raise RuntimeError(f"Pre-registered card changed: {actual}")
    limit_process()
    agents = {
        "UNO_N0_event_neurons": StructuralNeurons(),
        "fixed_copy": FixedCopy(),
        "latest_only": LatestOnly(),
        "exact_lookup": Lookup(False),
        "factored_oracle_lookup": Lookup(True),
        "one_exception_event_neurons": OneExceptionNeurons(),
    }
    stages = {}
    learned = agents["UNO_N0_event_neurons"]
    for stage in ("A", "B", "C", "D"):
        # All feedback comes from *independent simulator* after a scheduled action.
        for receipt in observed_phase(stage):
            for agent in agents.values():
                agent.observe(receipt)
        stages[stage] = {
            "learned_graph": learned.program.describe() if learned.program else "UNKNOWN",
            "graph_neurons": len(learned.graph.neurons) if learned.graph else 0,
            "graph_synapses": len(learned.graph.synapses) if learned.graph else 0,
            "scores": {name: {phase: evaluate(agent, query_group(phase))
                               for phase in ("A", "B", "C", "D")[:"ABCD".index(stage) + 1]}
                       for name, agent in agents.items()},
        }
    final = {name: {group: evaluate(agent, query_group(group))
                    for group in ("A", "B", "C", "D", "UNSEEN_MATERIAL", "UNSEEN_COMBINATION")}
             for name, agent in agents.items()}
    gates = {
        "OLD": final["UNO_N0_event_neurons"]["A"]["accuracy"] >= .9,
        "NEW_BCD": (sum(final["UNO_N0_event_neurons"][s]["correct"] for s in "BCD") / 16) >= .9,
        "UNSEEN_MATERIAL": final["UNO_N0_event_neurons"]["UNSEEN_MATERIAL"]["accuracy"] >= .9,
        "UNSEEN_COMBINATION": final["UNO_N0_event_neurons"]["UNSEEN_COMBINATION"]["accuracy"] >= .9,
    }
    # Negative controls: reject forged/unverified receipts and detect conflicts.
    bad_receipt = Receipt(context("DRY", "PLAIN", "OFF", "WOOD", "RED"),
                          "PUSH_LEFT", "RIGHT", "FORGED", False)
    forged_rejected = False
    try:
        learned.observe(bad_receipt)
    except ValueError:
        forged_rejected = True
    contradictory = Receipt(context("DRY", "PLAIN", "OFF", "WOOD", "RED"),
                            "PUSH_LEFT", "RIGHT", "CONTRADICTORY", True)
    learned.observe(contradictory)
    negative = {
        "unverified_receipt_rejected": forged_rejected,
        "conflict_detected": bool(learned.conflicts),
        "conflicted_key_abstains": learned.predict(contradictory.context, contradictory.action) is None,
        "nonconflicting_old_key_available": learned.predict(
            context("DRY", "SPIKED", "OFF", "STEEL", "RED"), "PUSH_LEFT") is not None,
    }
    out = {
        "candidate": IDENTIFIER,
        "experiment_card_sha256": actual,
        "status": "HOST_TESTED_SYNTHETIC_ONLY",
        "environment": {"python": platform.python_version(), "os": platform.platform(),
                        "limit_seconds": BUDGET_SECONDS, "limit_bytes": BUDGET_RAM_BYTES},
        "training_receipts": {stage: len(observed_phase(stage)) for stage in "ABCD"},
        "stages": stages,
        "final": final,
        "gates": gates,
        "negative_controls": negative,
        "runtime_seconds": monotonic() - start,
        "limitations": ["author-visible holdout", "designer-provided symbolic sensor vocabulary",
                        "designer-provided candidate grammar", "scheduled exploration, not autonomous RL",
                        "no numerical learned synaptic strengths, but digital computation is numerical",
                        "one-step deterministic synthetic world", "not production UNO or validated Android"],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
    if not all(gates.values()) or not all(negative.values()):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
