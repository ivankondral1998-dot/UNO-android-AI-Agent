# UNO-N0-03 — Android build evidence (2026-11-05)

Status: IMPLEMENTED / ANDROID_BUILT, DEVICE_VERIFIED=FALSE, RELEASE_READY=FALSE. Isolated research APK, not UNO production. No G4/G5 approval.

APK: `UNO_N0_03_RESEARCH_ANDROID_DEBUG.apk`, package `org.unovyra.n0research`, versionCode 1, versionName 0.3.0-research, minSdk 26, targetSdk 35, compileSdk 35; 29099 bytes; SHA-256 `b3e88cb340f6e9b527fb283993271b52da47e6790d50841f025c7d037ea5da10`.

Built in isolated Vercel Sandbox project `uno-n0-03-android-research`, using OpenJDK 17, Android SDK Platform 35, Build-Tools 35.0.0: javac -source 8, d8 --min-api 26, aapt2 compile/link, zipalign -p 4, apksigner sign and verify. Signature check: v2 PASS, v3 PASS, 1 signer; test-only RSA-2048 certificate SHA256 `34d99dff171d7d13856bf7fef40e667044e6d633bbea6db428ccbce78b56ec84`. `aapt dump badging`: launcher MainActivity, correct label, sdk, version. `aapt dump permissions`: no Android runtime permissions; no INTERNET.

Build-source SHA256 from sandbox:
- src/org/unovyra/n0research/MainActivity.java `b93fe987c0478ff219c6f313b961f46d6228a6cb11a3661d9b94fc48da0327d5`
- AndroidManifest.xml `1bda6000822f173921b32259474331a0315666d2814794bfa3759ed2d676042a`
- res/values/strings.xml `9848833383e416b6423fa174405b864148b99cf5b804d04d3b443b12e5649a0f`

The Vercel text transport omitted one trailing LF relative to local originals; build sources committed here match Vercel text transfer. Private test signing key is not committed, so byte-for-byte identical re-sign is not asserted.

Not done: app launch, device install, phone training, profiling on A52, logcat, OS permission/readback safety, native energy measurement. Expected synthetic scores on card are **not results**. This APK only runs a virtual-world structural neuron experiment; no control of real Android functionality. No online service or telemetry.
