# UNO-N0-02 / FROZEN RESEARCH CARD / 2026-11-05

Question: can a network of Boolean event neurons without numeric synaptic weights adapt through **local event-pair structural plasticity**, with no global program enumeration or replay fitting, retaining earlier behaviour and recombining learned factors under new circumstances?

STATUS BEFORE RUN: SPECIFIED_UNTESTED. Research-only; does not change R5.3. Per-owner limits: each run <=600 s wall clock, <=2 GiB address space, at most three trials of this candidate before review. No production training, no Android build, no GitHub Actions.

## Explicit inductive bias / fixed mechanism
- Each sensory input is one categorical token per feature; there are fixed sensory and motor event-neuron types. Network lacks trainable numeric coefficients. Synapses are labels: REQUIRE, EXCITE, FLIP. A parity event-neuron flips its Boolean output state once per simultaneously active FLIP source; not a multiply-by-weight operation.
- Only the last verified action/observation event is eligible to pair with the current verified one. If **the same action** and **exactly one categorical feature changed**, and the observed relation of action to outcome changed, locally add a FLIP-modulator for the nonreference value. If the outcome relation stayed the same, mark that local value NOT_FLIP. No global search, no minibatch gradient, no retroactive rebuilding over all receipts.
- The first verified context defines a reference value for each feature and establishes the default action-outcome relation. This is a **strong compositional XOR assumption**, given by the designer rather than discovered. It could generalize incorrectly when features interact nonlinearly, when observations are confounded, or when hidden state exists.
- Receipt verification is a simulated flag; no real security, consent or independent Android readback. Matching exact-key verified contradictions MUST return UNKNOWN for the key without deleting prior evidence. Unverified input MUST NOT update the graph. No autonomous exploration: an experimenter supplies paired interventions.

## Environment and data protocol
Sensory features: SURFACE={DRY,ICE}, MAGNET={OFF,ON}, FIELD={LOW,HIGH}, COLOR={RED,BLUE}, MATERIAL={WOOD,STEEL,GLASS}. Actions={PUSH_LEFT,PUSH_RIGHT}. Consequences={LEFT,RIGHT}. Hidden simulation law: observed direction is inverted relative to action iff an ODD number of {ICE, MAGNET=ON, FIELD=HIGH} holds; COLOR and MATERIAL are distractors. The learner sees only event tokens, action and verified consequence; hidden-law function is not used during inference or learning. All values categorical; numerical counters exist for test metrics only.

Frozen schedule of online experience (13 events, one pass, no replay-fit), in order:
1 RIGHT baseline DRY/OFF/LOW/RED/WOOD;
2 RIGHT ICE/OFF/LOW/RED/WOOD; 3 RIGHT baseline;
4 RIGHT DRY/ON/LOW/RED/WOOD; 5 RIGHT baseline;
6 RIGHT DRY/OFF/LOW/BLUE/WOOD; 7 RIGHT baseline;
8 RIGHT DRY/OFF/LOW/RED/STEEL; 9 RIGHT baseline;
10 LEFT baseline; 11 LEFT DRY/OFF/HIGH/RED/WOOD; 12 LEFT baseline; 13 RIGHT baseline.
Each event triggers update online; only adjacent verified event pairs allowed for local credit. Predictions before and after each receipt recorded.

## Evaluation frozen before the run
- Final retention: the training contexts with both action directions evaluated by direct network inference; accuracy >=0.9.
- Full finite-world test: all 2x2x2x2x3x2 = 96 context/action pairs (including training ones), >=0.95.
- Strict unseen exact combinations: filter out all recorded context/action keys, accuracy >=0.9. Mark as **PUBLIC, AUTHOR-KNOWN**, not sealed.
- Novel multi-cause compositions: ICE+MAGNET ON, MAGNET ON+FIELD HIGH, ICE+FIELD HIGH and all three with color/material variation and both actions; >=0.9.
- Negatives: unverified readback cannot change synapses; contradictory verified same context/action causes UNKNOWN only for that exact key; lack of a required sensor causes UNKNOWN; model inference must operate with simulator oracle disabled.
- Expressivity counterexample: change simulator law to invert **only when ICE AND MAGNET ON**, hold learning schedule fixed. Single-feature contrasts cannot identify conjunction; require at least one failure on unseen interaction. This negative control must be shown, not concealed.
- Controls: fixed-copy predictor, exact-key event memory (no generalization), hand-provided XOR-factor oracle baseline (stronger knowledge than the learner). Report accuracy and model stored topology. No claim of global novelty if a comparator is equal or better.

## Failure scope
This candidate is a symbolic Boolean event graph implementing a prescribed local plasticity rule; it is NOT proof that neurons spontaneously invent those rules, that it matches physical cortical neurons, that all numeric computations are gone, that complex tasks are learnable, or that memory/energy is better than quantized native models. No acoustic/sensor perception, reward-driven planning, independent user authorization, adaptive resource mask or Android testing. No training against sealed holdout. If thresholds fail, preserve failed result. No re-tuning after seeing test outcomes; next changed candidate must get new card/version.

Reproducibility: Python 3 stdlib only; deterministic, no RNG or seed required (seed: NONE). Run `python3 train_local_event_net.py > stdout.json 2> stderr.txt` in project directory under timeout/memory caps. Separate audit `python3 independent_audit.py > audit.json 2> audit_stderr.txt` also counts as a run. Frozen card SHA256 recorded into script before first run. Logs, exact source hash and environment preserved in manifest. Document code/static checks separately from model runs.
