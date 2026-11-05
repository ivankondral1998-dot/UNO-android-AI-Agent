# UNO-N0-07 — signed Android research APK build evidence (2026-11-05)

Status: **IMPLEMENTED / HOST_TESTED / ANDROID_BUILT / DEVICE_VERIFIED=FALSE / RELEASE_READY=FALSE**. This is a standalone tiny shared-F experimental neural organism, NOT the G4-approved UNO product or a complete R5.3 runtime. Owner explicitly requested the Android APK after clarifying that Samsung Galaxy A52 is the target.

## Reproducible research build

- GitHub private repo `ivankondral1998-dot/UNO-android-AI-Agent`, branch `docs/uno-lab-research-handoff-20261105`.
- Unchanged frozen research source archive: `research/uno-n0-07/source_bundle.tar.xz`, SHA256 `0bf6758020b22e80ba07dfaef7c487d66f2d3cf613489feda090c49f9b2316fc`; CI verified the complete archived source manifest.
- Research CI workflow: `.github/workflows/uno-n0-07-android-research.yml`; a single explicit owner build request; first run [42104659735](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42104659735) compiled/signed but failed artifact upload due to trying to tee a log before creating its directory, not a Java compile issue. The directory creation order was fixed in the workflow, without modifying research neural source, and second run [42104813304](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42104813304) completed **SUCCESS** with all steps passed.
- Build source commit `5fc805d33f6e28d77c5ecaab88098ecc567d9a03`, JDK 17, Android SDK platform 35 and build tools 35.0.0, compiling Java source and producing a D8 dex. CI fixed host test output unchanged: `CHECKS_TOTAL=8434`, `FROZEN_AGGREGATE tinyF=99/240 oldN005=144/240 persistence=143/240 Markov=150/240`. Predictive superiority remains FAIL on synthetic tests.
- Private workflow artifact **13451865954**: `UNO-N0-07-Tiny-F-Android-Research-APK`. Its ZIP was downloaded into the conversation runtime, the APK extracted to `/mnt/data/UNO_N0_07_TINY_F_RESEARCH.apk`, ZIP container checked with `unzip -t`, and SHA256 independently recomputed from the APK bytes. SHA matches the CI checksum.

## Signed APK identity

```text
File: UNO_N0_07_TINY_F_RESEARCH.apk
Bytes: 53675
SHA256: 642d17365e3f5d40baf90450800da5b626735cec5e1ef92a51e5ffc0334ecf2e
Package: org.unovyra.n007
Version name: 0.7.0-research
Version code: 1
minSdkVersion: 26
targetSdkVersion: 35
Launchable Activity: org.unovyra.n007.MainActivity
Signing schemes: v2=true, v3=true (verified by Android SDK apksigner in CI)
APK zip integrity: PASS; includes AndroidManifest.xml, resources.arsc, classes.dex
INTERNET permission: absent (validated using aapt dump permissions in CI)
Release signing identity: NO; temporary research-only key created within CI and NOT exported
```

## Research use

Runs locally on Samsung A52 Android 14 *if Android installation and runtime succeed*; no device install, smoke test, native Android outcome readback, power/PSS/thermal result or user-side feedback learning result has been verified yet. Five stages: A TRAIN → A TEST → B TRAIN → B TEST → close and relaunch app → RETEST A. Per stage 80 valid windows, check movement diversity. During train stages, owner may press explicit intention feedback buttons; such labels are not physical sensor truth. App never dispatches privileged Android actions. The old N0-04/N0-05 apps and data are separate packages.

Scope restrictions: original precode/R5.3 source, main, N0-04/N0-05 and result thresholds not changed. No published GitHub release, no permanent signing key, no production training/model adoption. G4 PRECODE_CANDIDATE, OWNER_APPROVED_PRECODE=FALSE, PRODUCTION_CODE_AUTHORIZED=FALSE.
