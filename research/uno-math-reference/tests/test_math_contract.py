"""Independent numerical and safety reference tests for UNO math v0.1.

No Android runtime, API, network, old Jarvis weights or third-party imports.
"""
import itertools
import json
import math
import random
import unittest
from hashlib import sha256

from uno_core.reference import (
    Organism, Policy, TrustedBoundary, Weights,
    readout_loss_and_gradient, train_new_readout,
)


def sample_core(seed=73, n=3, d=4, a=3, **config):
    return Organism(Weights.initial(n, d, a, seed), **config)


def policy(core, **kw):
    return Policy(owner=True, permission=True, confirmed=True, unlocked=True,
                  stopped=False, epoch=core.epoch,
                  permitted_actions=tuple(range(core.weights.a)), **kw)


def fixed_logit(core, action, h):
    return math.fsum(x*y for x, y in zip(core.weights.w_out[action], h)) + \
        math.fsum(x*y for x, y in zip(core.p[action], h)) + core.weights.b_out[action]


def sigmoid(z):
    return 1 / (1 + math.exp(-z))


class Mathematics(unittest.TestCase):
    def test_parameter_shape_fail_closed(self):
        w = Weights.initial(2, 3, 2)
        d = dict(w.__dict__)
        d["w_enc"] = ((0.0, 0.0),)
        with self.assertRaisesRegex(ValueError, "matrix shape"):
            Weights(**d)

    def test_all_nonfinite_weights_rejected(self):
        w = Weights.initial(2, 2, 2)
        for bad in [float("nan"), float("inf"), -float("inf")]:
            d = dict(w.__dict__)
            d["b_enc"] = (bad, 0.0)
            with self.subTest(bad=str(bad)), self.assertRaises(ValueError):
                Weights(**d)

    def test_deterministic_weights_without_old_JNO(self):
        a, b, c = Weights.initial(3, 4, 3, 17), Weights.initial(3, 4, 3, 17), Weights.initial(3, 4, 3, 18)
        self.assertEqual(a.digest(), b.digest())
        self.assertNotEqual(a.digest(), c.digest())

    def test_zero_input_true_skip(self):
        c = sample_core()
        h, p = c.h[:], [row[:] for row in c.p]
        self.assertIsNone(c.step((0.0, 0.0, 0.0), budget_units=1000))
        self.assertEqual(c.last_units, 0)
        self.assertEqual((h, p), (c.h, c.p))

    def test_budget_below_base_true_skip(self):
        c = sample_core()
        self.assertIsNone(c.step((1.0, 0.2, -0.1), budget_units=c.minimum_units-1))
        self.assertEqual(c.serial, 0)
        self.assertEqual(c.last_units, 0)

    def test_budget_no_recurrence_when_exact_base(self):
        c = sample_core()
        p = c.step((1.0, 0.2, -0.1), budget_units=c.minimum_units)
        self.assertIsNotNone(p)
        self.assertEqual(p.iterations, 0)
        self.assertEqual(p.used_units, c.minimum_units)

    def test_sparse_mask_row_skipping_and_cost(self):
        w = Weights.initial(3, 3, 2).identity_encoder()
        c = Organism(w, rho=0.0, delta=0.3, tau=0.1, max_steps=6)
        p = c.step((0.9, 0.0, 0.0), budget_units=10_000)
        self.assertEqual(p.active_rows, (0,))
        self.assertEqual(p.iterations, 6)
        self.assertEqual(p.used_units, c.minimum_units + 6 * (2 * w.d))
        self.assertEqual(p.trace[1], 0.0)
        self.assertEqual(p.trace[2], 0.0)

    def test_manual_reference_recurrence_matches(self):
        w = Weights.initial(2, 3, 2, 31)
        c = Organism(w, rho=0.4, delta=0.17, tau=0.08, max_steps=3)
        x = (0.8, -0.3)
        z = [math.tanh(sum(w.w_enc[j][i]*x[i] for i in range(w.n)) + w.b_enc[j]) for j in range(w.d)]
        mask = [j for j in range(w.d) if abs(z[j]) > c.tau]
        h = [max(-1, min(1, (1-c.rho)*val)) for val in z]
        for _ in range(3):
            nxt = list(h)
            for j in mask:
                value = sum(w.w_h[j][i]*h[i] for i in range(w.d)) + sum(w.w_z[j][i]*z[i] for i in range(w.d)) + w.b_h[j]
                nxt[j] = max(-1, min(1, h[j] + c.delta*math.tanh(value)))
            h = nxt
        prop = c.step(x, budget_units=1000)
        self.assertEqual(prop.iterations, 3)
        for got, expected in zip(prop.trace, h):
            self.assertAlmostEqual(got, expected, places=13)
        for i, got in enumerate(prop.probabilities):
            self.assertAlmostEqual(got, sigmoid(sum(w.w_out[i][j]*h[j] for j in range(w.d)) + w.b_out[i]), places=13)

    def test_all_small_budgets_obey_cap(self):
        for budget in range(0, 200):
            c = sample_core(seed=5)
            p = c.step((0.7, 0.3, -0.5), budget_units=budget)
            self.assertLessEqual(c.last_units, budget)
            if p:
                self.assertEqual(p.used_units, c.last_units)
                self.assertLessEqual(p.iterations, c.max_steps)

    def test_all_state_and_plastic_values_bounded_under_many_steps(self):
        c = sample_core()
        rng = random.Random(102)
        for _ in range(500):
            p = c.step(tuple(rng.uniform(-1, 1) for _ in range(c.weights.n)), budget_units=1000)
            self.assertTrue(p is None or all(-1 <= x <= 1 for x in p.trace))
            self.assertTrue(all(-c.plastic_cap <= v <= c.plastic_cap for row in c.p for v in row))

    def test_max_steps_and_zero_steps(self):
        c = sample_core(max_steps=0)
        p = c.step((0.5, 0.3, -0.3), budget_units=1000)
        self.assertEqual(p.iterations, 0)

    def test_malformed_inputs_do_not_mutate(self):
        c = sample_core()
        original = c.snapshot()
        cases = [((math.nan, 0, 0), 100), ((math.inf, 0, 0), 100), ((1, 2), 100), ((1, 0, 0), -1), ((1, 0, 0), True)]
        for x, budget in cases:
            with self.subTest(x=x, budget=budget), self.assertRaises(ValueError):
                c.step(x, budget_units=budget)
            self.assertEqual(c.snapshot(), original)

    def test_spend_monotone_and_bounded(self):
        costs = []
        for b in range(200):
            c = sample_core()
            c.step((0.7, -0.2, 0.3), budget_units=b)
            costs.append(c.last_units)
        self.assertEqual(costs, sorted(costs))
        self.assertLessEqual(max(costs), 200)


class TrustAndPlasticity(unittest.TestCase):
    def test_default_policy_denies(self):
        c = sample_core(); b = TrustedBoundary(c)
        prop = c.step((1.0, 0.2, 0.1), budget_units=1000)
        self.assertIsNone(b.authorize(prop, Policy()))
        self.assertEqual(c.learning_events, 0)

    def test_each_authority_gate_essential(self):
        c = sample_core(); b = TrustedBoundary(c)
        prop = c.step((1.0, 0.2, 0.1), budget_units=1000)
        good = policy(c)
        from dataclasses import replace
        for item, value in [("owner", False), ("permission", False), ("confirmed", False), ("unlocked", False), ("stopped", True), ("epoch", 2), ("permitted_actions", ())]:
            with self.subTest(field=item):
                self.assertIsNone(b.authorize(prop, replace(good, **{item: value})))
        self.assertIsNotNone(b.authorize(prop, good))

    def test_confirmed_success_updates_only_selected_plastic_row(self):
        c = sample_core(); b = TrustedBoundary(c)
        prop = c.step((1.0, 0.2, 0.1), budget_units=1000)
        before = sigmoid(fixed_logit(c, prop.action, prop.trace))
        old = [row[:] for row in c.p]
        ticket = b.authorize(prop, policy(c))
        self.assertEqual(b.finish(ticket, expected=17, native_readback=lambda: 17), "CONFIRMED")
        after = sigmoid(fixed_logit(c, prop.action, prop.trace))
        self.assertGreater(after, before)
        for i in range(c.weights.a):
            if i != prop.action:
                self.assertEqual(c.p[i], old[i])
        self.assertEqual(c.learning_events, 1)

    def test_contradiction_reduces_selected_outcome_prediction(self):
        c = sample_core(); b = TrustedBoundary(c)
        prop = c.step((0.5, 0.2, 0.3), budget_units=1000)
        before = sigmoid(fixed_logit(c, prop.action, prop.trace))
        ticket = b.authorize(prop, policy(c))
        self.assertEqual(b.finish(ticket, expected="ON", native_readback=lambda: "OFF"), "CONTRADICTED")
        self.assertLess(sigmoid(fixed_logit(c, prop.action, prop.trace)), before)

    def test_unknown_observation_never_teaches(self):
        for observed in (None, 17.0):
            c = sample_core(); b = TrustedBoundary(c)
            prop = c.step((1, 0, 0), budget_units=1000)
            ticket = b.authorize(prop, policy(c))
            old = c.snapshot()
            self.assertEqual(b.finish(ticket, expected=17, native_readback=lambda: observed), "UNKNOWN")
            self.assertEqual(c.snapshot(), old)

    def test_native_readback_exception_never_teaches(self):
        c = sample_core(); b = TrustedBoundary(c)
        prop = c.step((1, 0, 0), budget_units=1000)
        ticket = b.authorize(prop, policy(c)); old = c.snapshot()
        def bad(): raise RuntimeError("device read failed")
        self.assertEqual(b.finish(ticket, expected="ON", native_readback=bad), "UNKNOWN")
        self.assertEqual(c.snapshot(), old)

    def test_replay_ticket_rejected(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1, 0, 0), budget_units=1000); ticket = b.authorize(p, policy(c))
        self.assertEqual(b.finish(ticket, expected=True, native_readback=lambda: True), "CONFIRMED")
        after = c.snapshot()
        self.assertEqual(b.finish(ticket, expected=True, native_readback=lambda: True), "REJECTED_TICKET")
        self.assertEqual(c.snapshot(), after)

    def test_stop_epoch_stales_old_ticket(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1, 0, 0), budget_units=1000); ticket = b.authorize(p, policy(c))
        c.epoch_stop()
        after = c.snapshot()
        self.assertEqual(b.finish(ticket, expected=True, native_readback=lambda: True), "STALE")
        self.assertEqual(c.snapshot(), after)

    def test_new_proposal_stales_old_ticket(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1, 0, 0), budget_units=1000); ticket = b.authorize(p, policy(c))
        c.step((0, 1, 0), budget_units=1000)
        after = c.snapshot()
        self.assertEqual(b.finish(ticket, expected=True, native_readback=lambda: True), "STALE")
        self.assertEqual(c.snapshot(), after)

    def test_no_training_on_denial(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1, 0, 0), budget_units=1000)
        before = c.snapshot()
        self.assertIsNone(b.authorize(p, Policy()))
        self.assertEqual(c.snapshot(), before)

    def test_plasticity_math_independent_delta_oracle(self):
        c = sample_core(eta=0.5, forgetting=0.05)
        b = TrustedBoundary(c)
        p = c.step((0.8, 0.4, -0.2), budget_units=1000)
        baseline = c.p[p.action][:]
        expected = [max(-c.plastic_cap, min(c.plastic_cap, (1-c.forgetting)*a + c.eta*(1-p.probabilities[p.action])*h/(sum(v*v for v in p.trace)+1e-8))) for a,h in zip(baseline,p.trace)]
        ticket = b.authorize(p, policy(c))
        b.finish(ticket, expected="ON", native_readback=lambda: "ON")
        for actual, calc in zip(c.p[p.action], expected):
            self.assertAlmostEqual(actual, calc, places=14)

    def test_plastic_projection_bound_after_repeated_adaptations(self):
        c = sample_core(plastic_cap=0.1, eta=1)
        b = TrustedBoundary(c)
        for _ in range(250):
            p = c.step((1, 0.5, -0.1), budget_units=1000)
            ticket = b.authorize(p, policy(c))
            b.finish(ticket, expected=True, native_readback=lambda: True)
            self.assertTrue(all(-0.1 <= val <= 0.1 for row in c.p for val in row))


class AdditionalSafety(unittest.TestCase):
    def test_new_idle_stimulus_invalidates_old_ticket(self):
        c = sample_core(); boundary = TrustedBoundary(c)
        p = c.step((1.0, 0.0, 0.0), budget_units=1000)
        ticket = boundary.authorize(p, policy(c))
        c.step((0.0, 0.0, 0.0), budget_units=1000)
        self.assertEqual(boundary.finish(ticket, expected=True, native_readback=lambda: True), "STALE")
        self.assertEqual(c.learning_events, 0)

    def test_new_budget_exhausted_stimulus_invalidates_old_ticket(self):
        c = sample_core(); boundary = TrustedBoundary(c)
        p = c.step((1.0, 0.0, 0.0), budget_units=1000)
        ticket = boundary.authorize(p, policy(c))
        c.step((1.0, 0.0, 0.0), budget_units=0)
        self.assertEqual(boundary.finish(ticket, expected=True, native_readback=lambda: True), "STALE")

    def test_random_budget_model_seed_properties(self):
        rng = random.Random(8)
        for _ in range(500):
            n, d, a = (rng.randint(1, 6) for _ in range(3))
            budget = rng.randint(0, 500)
            c = Organism(Weights.initial(n, d, a, rng.randrange(100000)),
                         rho=rng.random(), delta=rng.random()*0.99 + 0.01,
                         tau=rng.random()*0.7, max_steps=rng.randint(0, 8))
            x = tuple(rng.uniform(-1, 1) for _ in range(n))
            p = c.step(x, budget_units=budget)
            self.assertLessEqual(c.last_units, budget)
            self.assertTrue(all(-1 <= v <= 1 for v in c.h))
            if p:
                self.assertTrue(0 <= p.iterations <= c.max_steps)
                self.assertTrue(all(-1 <= v <= 1 for v in p.trace))
                self.assertTrue(all(0 <= v <= 1 for v in p.probabilities))
                self.assertEqual(p.used_units, c.minimum_units +
                                 p.iterations * len(p.active_rows) * (2 * d))


class Snapshots(unittest.TestCase):
    def test_snapshot_roundtrip_and_model_binding(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((0.7, -0.2, 1), budget_units=1000)
        ticket = b.authorize(p, policy(c))
        b.finish(ticket, expected=2, native_readback=lambda: 2)
        data = c.snapshot()
        fresh = Organism(c.weights)
        fresh.restore(data)
        self.assertEqual(fresh.snapshot(), data)
        self.assertEqual(fresh.learning_events, 1)
        other = sample_core(seed=92)
        with self.assertRaisesRegex(ValueError, "incompatible model"):
            other.restore(data)

    def test_snapshot_bound_to_hyperparameters(self):
        c = sample_core()
        data = c.snapshot()
        changed = Organism(c.weights, rho=0.1)
        with self.assertRaisesRegex(ValueError, "incompatible model"):
            changed.restore(data)

    def test_corruption_fails_atomically(self):
        c = sample_core(); c.step((1, 0, 0), budget_units=1000)
        good = c.snapshot()
        for pos in (0, 13, len(good)//2, len(good)-2):
            bad = bytearray(good)
            bad[pos] ^= 1
            with self.subTest(pos=pos), self.assertRaises((ValueError, TypeError, UnicodeError, json.JSONDecodeError)):
                c.restore(bytes(bad))
            self.assertEqual(c.snapshot(), good)

    def test_even_rehashed_invalid_bounds_and_shape_rejected(self):
        c = sample_core(); before = c.snapshot()
        for mutate in (lambda p: p.update({"h": [3.0] + p["h"][1:]}),
                       lambda p: p.update({"h": [0.0]}),
                       lambda p: p.update({"serial": -1}),
                       lambda p: p.update({"epoch": 0.1})):
            o = json.loads(before)
            mutate(o["payload"])
            o["sha256"] = sha256(json.dumps(o["payload"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
            with self.assertRaises(ValueError):
                c.restore(json.dumps(o).encode())
            self.assertEqual(c.snapshot(), before)

    def test_inflight_ticket_is_not_restored(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1, 0, 0), budget_units=1000)
        ticket = b.authorize(p, policy(c))
        data = c.snapshot()
        c.restore(data)
        self.assertEqual(b.finish(ticket, expected=True, native_readback=lambda: True), "STALE")
        self.assertEqual(c.learning_events, 0)


class GradientAndTraining(unittest.TestCase):
    def test_cross_entropy_analytic_vs_central_difference(self):
        w = [[0.25, -0.5], [0.43, 0.29], [-0.11, 0.71]]
        f = [0.7, -0.6]
        _, grad = readout_loss_and_gradient(w, f, 2)
        eps = 1e-6
        for a, d in itertools.product(range(3), range(2)):
            plus = [row[:] for row in w]; minus = [row[:] for row in w]
            plus[a][d] += eps; minus[a][d] -= eps
            approx = (readout_loss_and_gradient(plus, f, 2)[0] - readout_loss_and_gradient(minus, f, 2)[0]) / (2*eps)
            self.assertAlmostEqual(grad[a][d], approx, delta=1e-8)

    def test_new_readout_training_and_holdout(self):
        rng = random.Random(100)
        train = []
        test = []
        for idx in range(500):
            x = (rng.uniform(-1, 1), rng.uniform(-1, 1))
            if abs(x[0]-x[1]) < 0.1:
                continue
            feat = (math.tanh(x[0]), math.tanh(x[1]))
            target = int(x[0] < x[1])
            (train if idx < 330 else test).append((feat, target))
        weights = train_new_readout(train, dim=2, n_actions=2, epochs=35, learning_rate=0.1)
        acc = sum(max(range(2), key=lambda a: sum(weights[a][j]*f[j] for j in range(2))) == y for f,y in test)/len(test)
        self.assertGreaterEqual(acc, 0.96, f"Holdout accuracy: {acc}")

    def test_training_is_deterministic_new_weights(self):
        samples = [((1.0, -1.0), 0), ((-1.0, 1.0), 1)]
        self.assertEqual(train_new_readout(samples, dim=2, n_actions=2),
                         train_new_readout(samples, dim=2, n_actions=2))


if __name__ == "__main__":
    unittest.main()


class RecurrenceDerivatives(unittest.TestCase):
    def test_masked_jacobian_against_finite_difference(self):
        from uno_core.reference import masked_recurrence_jacobian
        rng = random.Random(224)
        eps = 1e-6
        for _ in range(120):
            w = Weights.initial(3, 3, 2, rng.randrange(10000))
            h = [rng.uniform(-0.6, 0.6) for i in range(3)]
            z = [rng.uniform(-0.4, 0.4) for i in range(3)]
            active = (0, 2)
            delta = 0.15
            analytic = masked_recurrence_jacobian(w, h, z, active, delta)
            self.assertIsNotNone(analytic)
            def evolve(hv):
                nxt = hv[:]
                for i in active:
                    u = sum(w.w_h[i][j] * hv[j] for j in range(3)) + sum(w.w_z[i][j]*z[j] for j in range(3)) + w.b_h[i]
                    nxt[i] = max(-1, min(1, hv[i]+delta*math.tanh(u)))
                return nxt
            for i, j in itertools.product(range(3), repeat=2):
                pos = h[:]; neg = h[:]
                pos[j] += eps; neg[j] -= eps
                approx = (evolve(pos)[i] - evolve(neg)[i])/(2*eps)
                self.assertAlmostEqual(analytic[i][j], approx, delta=2e-9)

    def test_masked_recurrence_has_finite_lipschitz_bound(self):
        rng = random.Random(90)
        for _ in range(250):
            w = Weights.initial(3, 4, 2, rng.randrange(50000))
            h1 = [rng.uniform(-0.8, 0.8) for _ in range(4)]
            h2 = [rng.uniform(-0.8, 0.8) for _ in range(4)]
            z = [rng.uniform(-0.7, 0.7) for _ in range(4)]
            active = (1, 3)
            delta = 0.2
            bound = 1+delta*max(sum(abs(v) for v in row) for row in w.w_h)
            def evolve(h):
                out = h[:]
                for i in active:
                    y = sum(w.w_h[i][j]*h[j] for j in range(4)) + sum(w.w_z[i][j]*z[j] for j in range(4)) + w.b_h[i]
                    out[i] = max(-1, min(1, h[i]+delta*math.tanh(y)))
                return out
            inp = max(abs(a-b) for a,b in zip(h1,h2))
            diff = max(abs(a-b) for a,b in zip(evolve(h1),evolve(h2)))
            self.assertLessEqual(diff, bound*inp+1e-12)

    def test_stop_during_native_readback_fails_closed(self):
        c = sample_core(); b = TrustedBoundary(c)
        p = c.step((1.0, 0.0, 0.0), budget_units=1000)
        ticket = b.authorize(p, policy(c))
        def device_callback():
            c.epoch_stop()  # STOP arrives during external readback
            return True
        self.assertEqual(b.finish(ticket, expected=True, native_readback=device_callback), "STALE")
        self.assertEqual(c.learning_events, 0)

class InvalidConfigurationAndBounds(unittest.TestCase):
    def test_bad_dimension_and_weight_values(self):
        from dataclasses import replace
        w = Weights.initial(2, 2, 2)
        with self.assertRaises(ValueError):
            replace(w, n=0)
        with self.assertRaises(ValueError):
            Weights.initial(65, 2, 2)
        with self.assertRaises(ValueError):
            replace(w, w_h=((float('nan'), 0.0), (0.0, 0.0)))
        with self.assertRaises(ValueError):
            w.identity_encoder() if w.n != w.d else Weights.initial(2, 3, 2).identity_encoder()

    def test_bad_hyperparameters_and_step_limit(self):
        w = Weights.initial(2,2,2)
        for config in ({'rho': float('nan')}, {'rho': -0.1}, {'eta': 0.0},
                       {'plastic_cap': 11.0}, {'delta': 1.01}, {'forgetting': 1.0}):
            with self.subTest(config=config), self.assertRaises(ValueError):
                Organism(w, **config)
        for limit in (-1, 17, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                Organism(w, max_steps=limit)

    def test_reject_invalid_outcome_and_training_samples(self):
        c = sample_core(); p = c.step((1,0,0), budget_units=1000)
        for value in (True, 2, -1, 0.1):
            with self.assertRaises(ValueError):
                c._learn_from_authority(p, value)
        with self.assertRaises(ValueError):
            readout_loss_and_gradient(((0.0, 0.0),), (0.0, 0.0), 2)
        for bad in ([], [((math.inf, 0), 1)], [((1,), 0)], [((1,0), 3)]):
            with self.assertRaises(ValueError):
                train_new_readout(bad, dim=2, n_actions=2)

    def test_invalid_snapshot_envelopes_and_schema(self):
        c = sample_core(); baseline = c.snapshot()
        for blob in ("not bytes", b"[]", b"{}", b"\"abc\"", b"0"*1_000_001):
            with self.subTest(blob=str(blob)[:30]), self.assertRaises((ValueError, TypeError)):
                c.restore(blob)
            self.assertEqual(c.snapshot(), baseline)
        obj = json.loads(baseline)
        del obj['payload']['serial']
        obj['sha256'] = sha256(json.dumps(obj['payload'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        with self.assertRaises(ValueError):
            c.restore(json.dumps(obj).encode())
        self.assertEqual(c.snapshot(), baseline)

    def test_derivative_rejects_bad_shapes_and_clip_nondifferentiability(self):
        from uno_core.reference import masked_recurrence_jacobian
        w = Weights.initial(2, 2, 2)
        for h, z, mask in [((0,), (0,0), (0,)), ((float('nan'), 0), (0,0), (0,)),
                           ((0,0), (0,0), (0,0)), ((0,0), (0,0), (3,))]:
            with self.subTest(h=h, mask=mask), self.assertRaises(ValueError):
                masked_recurrence_jacobian(w, h, z, mask, 0.2)
        self.assertIsNone(masked_recurrence_jacobian(w, (1.0, 0.0), (0.0, 0.0), (0,), 0.2))

    def test_snapshot_finite_invalid_internal_readout_does_not_commit(self):
        c = sample_core()
        c.p[0][0] = float('inf')  # deliberate internal corruption, bypassing normal storage validators
        h_before = c.h[:]
        with self.assertRaises(ArithmeticError):
            c.step((1,0,0), budget_units=1000)
        self.assertEqual(c.h, h_before)


class TrainedWeightsIntegration(unittest.TestCase):
    def test_newly_trained_readout_is_used_by_same_core(self):
        from dataclasses import replace
        train = []
        for v in [0.3, 0.5, 0.7, 0.9]:
            train.extend([((math.tanh(v), math.tanh(-v)), 0),
                          ((math.tanh(-v), math.tanh(v)), 1)])
        learned = train_new_readout(train, dim=2, n_actions=2, epochs=70, learning_rate=0.2)
        core_weights = replace(Weights.initial(2,2,2, seed=123).identity_encoder(), w_out=learned)
        core = Organism(core_weights, rho=0, max_steps=0)
        proposal = core.step((0.75, -0.65), budget_units=core.minimum_units)
        self.assertEqual(proposal.action, 0)
        reverse = Organism(core_weights, rho=0, max_steps=0)
        proposal2 = reverse.step((-0.65, 0.75), budget_units=reverse.minimum_units)
        self.assertEqual(proposal2.action, 1)
