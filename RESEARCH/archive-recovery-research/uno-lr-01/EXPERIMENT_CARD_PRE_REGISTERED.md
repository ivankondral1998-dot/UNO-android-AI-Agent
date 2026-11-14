# UNO-LR-01 | FROZEN EXPERIMENT CARD | 2026-11-05

STATUS: research-only candidate, NOT approved R5.3 replacement; no production code/training; no Android. Freeze this card BEFORE the first execution. Seed = 20261105. Python 3 standard library. One run <=600 seconds and <=2 GiB memory, no more than 3 candidate runs before review. This experiment does not train neural Θ or claim a new physical law.

## Hypothesis
A structural, revisable *causal relation* used as a 'weight' (not a fixed scalar) can reinterpret earlier action→outcome experience after new context is discovered, while retaining performance on earlier observed conditions. It might generalize over an unused material feature. This is a claim about an exact small deterministic grammar, not broad continual learning.

## Virtual world (known to experiment designer; hidden from model's fitting procedure)
Feature values: SURFACE in {ROUGH,SLICK}; TREATMENT in {NONE,GRIP}; MATERIAL in {WOOD,METAL,GLASS,CERAMIC}. Action LEFT or RIGHT; displacement is same direction unless SURFACE=SLICK AND TREATMENT=NONE, in which case movement is reversed. One transition per action; oracle response = independent synthetic readback of displacement. Actions in the learning phase are externally scheduled; in evaluation, agent must choose the correct action for a target displacement.

## Sequential evidence
A: all four ROUGH x {NONE,GRIP} x {WOOD,METAL} contexts, one action each LEFT and RIGHT (8 verified events). All same effect.
B: SLICK x NONE x {WOOD,METAL}, actions LEFT/RIGHT (4 more events), all reversed.
C: SLICK x GRIP x {WOOD,METAL}, actions LEFT/RIGHT (4 more events), all same effect.
Training order A then B then C; fixed enumeration. No GLASS or CERAMIC in training.

## Candidate relation grammar and revision
A relation is a typed conditional rewrite program with a default in {COPY,INVERT} and at most one conjunctive exception guard of length 1 or 2. Guards inspect feature-value *equality* in a context; features chosen from SURFACE, TREATMENT, MATERIAL; a guard cannot use the same feature twice. A matched exception applies the opposite of default. When a new verified event arrives, search all programs in this fixed grammar, select the one with 0 training errors and minimum number of literals (then lexical tie-break), and *replace the complete rule program*, retaining the evidence records. An inconsistent same-input same-action outcome must be surfaced as CONFLICT, never overwritten. No programmed target rule is supplied to the fitter.

## Predefined evaluation
Stage A: correctness on the 8 already observed ROUGH conditions. Stage B: old retention on same 8 and new acquisition on 4 SLICK+NONE conditions. Stage C: all 16 known conditions and held-out GLASS/CERAMIC x 4 surface/treatment x 2 target directions = 16 unseen-material control decisions. Also evaluate after B on held-out SLICK+GRIP (not yet observed) to expose premature overgeneralization; expected to fail, NOT hidden. Stage C for all three core gates require >=0.90 old, >=0.90 new conditions, >=0.90 held-out material control accuracy. No feedback from test cases updates candidate. Count unknown as failure.

## Baselines
1. Fixed COPY behavior. 2. One mutable scalar-like global transform replaced by latest outcome. 3. Exact key-value table keyed by (surface,treatment,material,action); unknown on unseen keys. 4. Factored context table keyed by (surface,treatment,action), manually given relevant features (strong oracle-like baseline). We do NOT expect to beat the factored table; matching it is not proof of novel intelligence.

## Before-run failure cases
- If world is not expressible in selected grammar, no exact program exists; report FAIL/UNKNOWN.
- Same observed context+action can produce incompatible results due to unobserved variables or noise; report CONFLICT rather than guarantee retention.
- The chosen grammar, feature names, and verification oracle are provided by the researcher. Context discovery is NOT demonstrated.
- The held-out split is author-visible, not a sealed independent benchmark.

## Gate status
G4=PRECODE_CANDIDATE; OWNER_APPROVED_PRECODE=FALSE; PRODUCTION_CODE_AUTHORIZED=FALSE; no changes to R5.3 NORMATIVE, O01–O08 remain owner decisions.
