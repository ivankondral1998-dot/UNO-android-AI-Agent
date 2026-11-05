# UNO-N0-01 / FROZEN RESEARCH CARD / 2026-11-05

Candidate: ONE event-driven neuron graph without scalar trainable synaptic weights. All neuron→neuron edges have symbolic types only: REQUIRES, ACTIVATES, INHIBITS. Neurons are predicates (token), conjunctions (rule), and consequence/output neurons. Learning is structural graph rewriting from independently observed simulator receipts. There are no initialized numerical synaptic strengths, numerical gradients, backprop, or pretrained model weights. Integers still exist in the computer and in the research/evaluation program (addresses, enumeration, counts, search). We do NOT claim number-free physical computation, brain-scale intelligence, scientific priority, or production UNO.

## Authority
Standalone research fixture only, on free PC. <=600 seconds per process, <=2 GiB address space, <=3 runs of the same candidate before formal review. Zero production code, no GitHub Actions, Android device/build, release, source-package modification, or adoption of R5.3. G4 candidate, OWNER_APPROVED_PRECODE=FALSE, PRODUCTION_CODE_AUTHORIZED=FALSE.

## Hypothesis
An explicit neuron graph with non-numeric synapses can change its organization after a surprising outcome, keep verified earlier observations, and plan one-step actions under OLD→NEW→CORRECTION→SECOND NEW conditions. Graph induction should generalize across an unseen irrelevant material value and to one unseen combination of known causal features. It need not outperform a suitably chosen symbolic program baseline. We MUST distinguish graph realization from an original discovery.

## Environment (provided by researcher, not to learner)
Each step context contains SURFACE (DRY, ICE), TREAD (PLAIN, SPIKED), MAGNET (OFF, ON), MATERIAL (WOOD, STEEL, GLASS, CERAMIC), DECOR (RED, BLUE). Actions PUSH_LEFT/PUSH_RIGHT cause LEFT/RIGHT. Outcome reverses command when `(SURFACE=ICE and TREAD=PLAIN) or (MAGNET=ON)`. MATERIAL and DECOR are distractors. The simulator returns independently read actual outcome only after action. A target direction is external and not supplied as a training label for the world law.

## Four *sequential* experience phases
Train only on WOOD and STEEL, DECOR=RED, both PUSH actions per context:
A: DRY / PLAIN,SPIKED / MAGNET OFF. [8 action→effect receipts, COPY]
B: ICE / PLAIN / MAGNET OFF. [4 new receipts, INVERT]
C: ICE / SPIKED / MAGNET OFF. [4 new receipts, COPY]
D: DRY / PLAIN,SPIKED / MAGNET ON. [8 new receipts, INVERT]
No new or later-phase receipts allowed during earlier training. Actions during training are an exploration schedule with independently observed effects, NOT reinforcement-learning autonomy.

## Non-numeric graph construction / induction, declared before execution
Every rule is a condition neuron activated by a conjunction of feature=value neurons, with an EXCITE edge to a FLIP consequence and INHIBIT edge to the default COPY consequence. One shared graph predicts for either action; no task-specific evaluator-selected head. Graph can contain up to TWO exception neurons, each condition with at most TWO distinct feature literals. A rule requires all linked predicate neurons, not a weighted sum. To build/update the graph, search for the first lexicographically canonical minimal-description exact explanation of all non-conflicting receipts: enumerate defaults COPY before INVERT, then increase count of exceptions, then total condition literals. Exceptions in a program all emit the transform opposite to default; if multiple fire they jointly select that transform. Prefer models with fewer total conditions and literals; lexical deterministic tie-break. If no exact program exists, graph prediction is UNKNOWN; no fabricated success. Store all receipts (append-only); contradictory same complete context and action ⇒ CONFLICT and abstain for that key.

IMPORTANT: The learner receives the input feature NAMES, VALUES and the two-output action vocabulary. Its candidate grammar is designer-chosen and searches over features; it does not discover sensors, language, causal variables, or neurobiological principles. Graph synthesis is a symbolic program search and can use integer operation counts to choose a minimal structure. The *learned neuron's connection parameters* are not numerical. Compare with symbolic baselines.

## Predefined evaluation, no retraining on evaluations
After each phase test OLD A, B, C, D contextual settings where applicable; after D, assess:
* OLD A retention ≥0.90;
* NEW B, C and D jointly ≥0.90;
* unseen MATERIAL GLASS/CERAMIC (DECOR=BLUE) on seen surface/tread/magnet combinations ≥0.90;
* withheld COMBINATION ICE / MAGNET ON (all tread, GLASS/CERAMIC, DECOR=BLUE) ≥0.90;
* contradictory receipt should yield UNKNOWN on the exact conflicting key, not overwriting it.
Counts: A 8 target-direction decisions; B 4; C 4; D 8; new MATERIAL on known combinations 24 target decisions; unseen ICE+MAGNET ON 8 target decisions. Unseen combinations were never used in training. UNKNOWN counts as wrong. These are researcher-visible, not third-party-sealed tests. Thresholds are exploratory, not an owner-approved product standard.

## Baselines
- Fixed COPY behavior (no learning).
- Latest-only global COPY/INVERT state (forgets old).
- Exact lookup keyed by all context fields + action (fails unseen materials).
- Factor lookup keyed by surface+tread+magnet+action, manually supplied relevant features (strong baseline, expected to match material generalization but not unknown combinations).
- UNO-LR-01 is prior one-exception relational fixture; the new environment contains two independent reversal causes, so do not compare raw scores across different tasks. A direct same-dataset one-exception comparator may be included.

## Failure predeclarations
Potential failures: candidate grammar may not fit the streaming evidence or may use irrelevant features; graph can give confident wrong extrapolations, no dynamic confidence or calibrated probability; background feature distribution/causal structure hand-picked; two exceptions hard-coded capacity; minimum-description search may be expensive at scale; invented context labels not real perception; without exact receipts no factual learning; delayed/multi-step tasks not supported. Tests measure only small finite task success, not UNO intelligence, neuroscience, general scalability, on-device energy or true autonomy.

## Reproducibility
One script with Python 3 standard library and a standalone result JSON; log actual stderr/stdout and SHA-256 hashes. No random values necessary (deterministic enumeration). Freeze SHA-256 of this card into script and validate before run; do not modify card after trial. Any future modifications use a new candidate ID/card.
