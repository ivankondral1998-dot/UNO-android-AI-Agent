# UNO-N0-05 — Android research APK build evidence — 2026-11-05

Status IMPLEMENTED / HOST_GRAPH_REGRESSION_PASS / ANDROID_BUILT. DEVICE_RUN_NOT_YET; DEVICE_VERIFIED=FALSE; PRODUCTION_READY=FALSE.

Repository: private ivankondral1998-dot/UNO-android-AI-Agent, branch docs/uno-lab-research-handoff-20261105. Frozen source/card commit 029882048ae404bc6bc5eb63f903d37028c27a09. No edits to main, R5.3, N0-04 source or data.

GitHub Actions run: https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42094276662
Run status and all steps SUCCESS: checkout, source SHA256 verification, host tests, Android SDK35, standalone APK compilation, signing, APK ZIP validation, private artifact upload.

Private CI artifact ID 13445364692: UNO-N0-05-Android-Sensor-Neural-Audit. Artifact downloaded from GitHub and inspected separately in this conversation.

APK filename UNO_N0_05_NEURAL_AUDIT.apk; 45,483 bytes. SHA-256 (CI text and independently extracted APK agree):
052335fadd1c81d9ddf47488ac05ec4cb911d3ab527a265d6a8b637b364fe511
Package org.unovyra.n005audit, versionCode=1, versionName=0.5.0-research, minSdk 26, targetSdk 35, Android compileSdk35. App label UNO N0-05 Neural Audit. Signed v2=true, v3=true; APK ZIP integrity PASS, contains classes.dex. No INTERNET permission. Build signature research-only ephemeral key: not an official release key.

Host tests compare ORIGINAL untouched N0-04 NeuralGraph inference and learning with N0-05 graph on a fixed seed (2400 context predictions + 1200 on-the-fly graph updates), 16804 assertions PASS. Source reference in host-test/ref; org.json host stubs are deliberately compile-only; tests do NOT exercise actual device persistence, Android sensors, energy/PSS, phone UX or scientific superiority. Host report: neuronOrigins=54, noMatchOrigins=10, contestedOrigins=2336, nodes=24, contestedNodes=18, from artificially stochastic data. Do not generalize those counts to A52.

Reproducible source bundle research/uno-n0-05/source_bundle.tar.xz SHA256=5a62c788b6e3093a67e3000d9aef353a1c1f3e1640f745fff1c7238f465d1357, Git blob=533ac084bc6ea1c44f7a941f31ff1859dd56e477. CI checked embedded SOURCE_MANIFEST_SHA256.txt.
Frozen card: research/uno-n0-05/RESEARCH_CARD_FROZEN_BEFORE_DEVICE_RUN.md. Owner phone steps: research/uno-n0-05/PHONE_TEST_RU.md. No production changes. G4 PRECODE_CANDIDATE, OWNER_APPROVED_PRECODE=FALSE, PRODUCTION_CODE_AUTHORIZED=FALSE, G5/G6 closed.

Next evidence: fresh five-stage A→B→A device trial on Samsung A52 with full per-stage AUDIT origins, wins/losses and optional categorical per-window trace after app restart. Only then can we attribute ties to contested fallback or evaluate actual learned-neuron contribution.
