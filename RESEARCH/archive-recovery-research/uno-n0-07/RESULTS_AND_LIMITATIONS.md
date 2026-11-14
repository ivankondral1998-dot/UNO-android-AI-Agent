# N0-07 evidence — fixed host pilot, 2026-11-05

- Owner requested an isolated small network modeled on N0-04/N0-05 Android research but implementing selected UNO mathematical principles from Grok's corrected paper.
- Pre-run frozen source record committed to research branch at `research/uno-n0-07/FROZEN_RESEARCH_CARD_20261105.md`, commit `051b2134f1f0901f8e38663497b546428956ec8d`.
- Host compilation JDK 21 source/target 8: **PASS** (`run_host.sh`). Exact original N0-05 comparator source preserved under `core/ref_n005/NeuralGraph.java`; JSON-only compile stubs under `core/test/org/json`, NOT Android app.
- Deterministic host unit/assertion count **8,434 PASS**, including physically skipping half the block kernels, zero leakage of future observations before predictions, owner source versus sensor source, P-style mock success gated on valid receipt, STOP/epoch/expiry/duplicate receipt rejection, checkpoint SHA256 corruption rejection, and bounded exact FIFO memory.
- Synthetic five-stage outcomes in `results/host_run_final_1.txt`; `results/host_run_final_2.txt` **byte-identical**. Frozen scores Tiny-F `99/240`, N0-05 graph `144/240`, persistence `143/240`, Markov `150/240`. Sensory network worse than baselines. No claims about physical A52 performance or retention.
- Synthetic saved-and-restored checkpoint hash appears in result stdout. This does NOT demonstrate Android Activity lifecycle, app-private native storage durability or independent OS effect confirmation.
- Android MainActivity Java source: **compiled only with locally crafted disposable Android stubs** (static API/syntax check). These stubs are not packaged and cannot prove Android build or runtime compatibility. AndroidManifest.xml parsed; no permissions.
- `build_android_with_sdk.sh` was attempted only to detect local SDK availability; it terminated `ANDROID_HOME` unset. No D8/aapt2, signed APK or real-phone trial. GitHub Actions **NOT launched**. Unverified code is deliberately not reported as `ANDROID_BUILT`.
- No training using user's real 400-row N0-05 sensor trace (its exact bytes still not archived as a replay fixture). No owner data or secrets exported.
- Verdict `IMPLEMENTED / HOST_TESTED_SYNTHETIC_ONLY / ANDROID_SOURCE_STUB_COMPILED`, `ANDROID_BUILT=FALSE`, `DEVICE_VERIFIED=FALSE`, `PRODUCT_GATES_UNCHANGED`.
