# R5.4: decoded parameter caps and TRAIN001 host core parity

Scope: research TRAIN001, errata 06/10, following the measurement transfer at
`4b13f6ae1a9d969807bf2d844088cf7cc568c069`. Not a new architecture, model ABI,
Android weight admission or production training authorization.

## Reproduced defect

The pinned original checkpoint (`d85b14a2ab0e6e2c254d1ac45e64c56b28be9b2248a165869632919ef2847404`,
saved step 1000, selected step 950) was inspected read-only. The original
`initial.tsv` is bound by the checkpoint config SHA. Decode uses weights_only
and a caller-supplied trusted digest. For each finite decoded binary value,
`Fraction` computes the exact represented rational, and row L1/box comparisons
use the normative decimal cap, including 0.9. Of 2624 tensor rows (including
box rows), 722 in 12 of 20 tensors exceed their caps. The largest absolute
excess is about 5.0044e-8. The existing Kotlin `UnoRefWeights` constructor
independently rejects the unchanged selected weights: B2_RECURRENCE_NORM_INVALID.
This is a geometry/rounding problem, not evidence that the trained task quality
is zero. Historical checkpoint metrics remain diagnostic and unchanged.

## Correction

The recovered RTX trainer keeps the gap-coordinate L1 projection. A positive
binary64 reduction of n finite nonnegative terms has at most n-1 additions;
under IEEE round-to-nearest its relative normal-range rounding error is bounded
by gamma_(n-1) = (n-1)u/(1-(n-1)u), u=2^-53. The inward guard uses a conservative
margin 8*n*2^-52 and nextafter toward zero (also accounting for the decimal cap
representation). The fixed caps are 0.9, 1, 2, 8; subnormal contributions cannot
consume the guard margin. If the decoded cast is too close to the cap, rescale
toward a second inward guard and round each coordinate toward zero. Verify the
final decoded reduction against the first guard before copying back. Interior
rows remain bitwise unchanged; boundary rows may shrink slightly. This is not
a claim of exact Euclidean projection on the representable float lattice.
Nonfinite parameters are rejected before clipping. New runs certify the initial
boundary, projected updates, resume and selected evaluation. Source hash and
projection identity bind new manifests; no silent resumption of historical
training under the changed projection. Legacy validate() remains for diagnostic
replay only. The original 950 checkpoint has not been repaired or rewritten.
CUDA reduction and nextafter behavior still require the actual device check.

## Reproduce on host

From this directory, using the original handoff archive, original selected
checkpoint and original initial.tsv, with Python/PyTorch, Java and kotlinc:

```
python r54_checkpoint_audit_test.py
python r54_checkpoint_audit.py CHECKPOINT INITIAL --sha256 TRUSTED_SHA
python r54_core_parity.py HANDOFF_ZIP CORE_KOTLIN_DIRECTORY CHECKPOINT INITIAL --sha256 TRUSTED_SHA
```

Expected audit exit 2 for the known original checkpoint. The parity probe uses
the existing UnoFReference directly, not a duplicate Kotlin F implementation.
Only synthetic fixtures are projected. For the original checkpoint, a temporary
host-only TSV transports unchanged values to the existing constructor for the
negative test; no persistent export or Android loader is created. Kotlin host
fixture checks 3 modes, causal write IDs, all terminal state/key/value coordinates
and actual branch entry counts for 3 original synthetic fixtures. 4416 compared
coordinates; max absolute difference 2.2551405187698492e-17. The original is
rejected, its digest unchanged. See evidence/r54_decoded_caps_checks.log and
r54_decoded_caps_checkpoint950.json. Old gradient and short synthetic update
parity also pass, as do measurement, causal and policy regressions. These are CPU
mechanism tests, not training quality, CUDA certification, or A52 evidence.

## Remaining integration boundary

TRAIN001 has d64, three synthetic features, fixed K2, zero goal/metadata, and
only its 20 research tensors. It is not an approved full B2 weight inventory.
Android's reference session currently derives both key and value from the same
semantic vector, whereas TRAIN001 writes distinct Wk/Wv projections. A valid
product ABI, actual full weight set and causal write/read contract, verified
admission, and the integrated device tests remain necessary. Do not bypass
UnoWeightGate, open Android effects, or claim DEVICE_VERIFIED on this evidence.
