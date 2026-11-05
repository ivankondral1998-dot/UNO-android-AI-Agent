# UNO-N0-04 Android sensor research build — 2026-11-05

STATUS: SOURCE_IMPLEMENTED; ANDROID_BUILT verified via GitHub Actions logs + artifact; DEVICE_RUN=NOT_YET, DEVICE_VERIFIED=FALSE, RELEASE_READY=FALSE.

Owner authorized Android experimental work earlier on 2026-11-05 and explicitly authorized GitHub Actions in this conversation. Workflow is isolated to `docs/uno-lab-research-handoff-20261105`, manual/push scoped to research/uno-n0-04. No changes to main, R5.3 source package, Jarvis or PMB. No production code authorization, G4/G5 not approved.

Build: GitHub Actions workflow `.github/workflows/uno-n0-04-android-research.yml`.
- Initial run #1 ID 42088816693 SUCCESS, but omitted explicit Android package version. Its APK is superseded and MUST NOT be presented for phone test.
- **Final run #2 ID 42089039650 SUCCESS**, source tree commit `f6ca6be23f75c038a0d6c7a242a60bf4b4f133b0`. Tested build steps: checkout, JDK 17, Android SDK API35 tools 35.0.0, javac/d8/aapt2/zipalign, apksigner verify v2=true/v3=true, aapt metadata, ZIP integrity, artifact upload.
- Final artifact: private GitHub Actions artifact ID `13444187349`, name `UNO-N0-04-Android-Research-APK`, archive 21835 bytes; contains exact APK, source SHA256, APK SHA256 and status note. Artifact retention configured 30 days, not a permanent release.
- Final APK: `UNO_N0_04_ANDROID_RESEARCH.apk`, 41387 bytes, SHA256 `791b171351c600eb6f493767ecdfe16efbc4b608e21a07fe22dffd9c4fb905c9`, verified independently after extraction from connector-downloaded GitHub Actions artifact.
- `aapt` confirms package `org.unovyra.n004research`, versionCode=1, versionName=`0.4.0-research`, minSdk=26, targetSdk=35, label `UNO N0-04 Sensor Research`. `aapt dump permissions` displayed only package name (no uses-permission); no INTERNET in source manifest.
- Source in GitHub `research/uno-n0-04/source_bundle.tar.xz` includes full .java, manifest, strings, card and phone protocol; bundle Git blob `8a21b8cb7730e81950c221496e46f3301e517284`, SHA256 `f0d1a722baf63af3efc959e89c1d43410c0d11f0d54774cd75a6e5d908983b90`.
- Final GHA SOURCE_SHA256.txt matched original source bytes: MainActivity.java `c3d3add0091d0f4e5afd61fd52450e96ac71aa28e33e80c723243e68f13d4e8d`; NeuralGraph.java `82eb0ac1da2d4639b952172c960f65af186e80b71cd31e17adb5e01ed49f1e99`.
- Research only: real TYPE_LINEAR_ACCELERATION (or accelerometer fallback) physical input, 250ms categorical windows, event-neuron graph with no learned numeric synaptic weights, built-in numeric threshold processing, numeric Markov and persistence baselines. 5-stage TRAIN A / TEST A / TRAIN B / TEST B / RESTORED TEST A; 80 prospective decisions per stage; frozen train/test split and explicit restart gate. No production Android operations.

PROTOCOL NOT YET RUN: N0-04 has **no phone learning numbers**, no actual sensor evidence from A52 yet, no proof of retention or baseline superiority, no energy/PSS, and no general intelligence claim. Freeze criteria from research/uno-n0-04/RESEARCH_CARD_FROZEN_BEFORE_DEVICE_RUN.md remain unchanged. First phone trial required; preserve exact copied report, including failures.
