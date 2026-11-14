# UNO WP-01: first GitHub Actions Android debug build

Owner instruction of 2026-11-07: **"Собирай на Android Action, даю добро"**. This explicitly authorizes this Android CI build; it is **not** permission to publish a release, change `main`, sign commercial APKs, use secrets, or to start self-learning.

Repo/branch: `ivankondral1998-dot/UNO-android-AI-Agent`, `feat/uno-production-foundation-20261106`. One-time `push` trigger matches **only changes to this workflow filename**; ordinary subsequent source pushes are not automatically built. `workflow_dispatch` is retained as a manual event for when GitHub allows dispatch of this workflow. GitHub-managed Ubuntu runner downloads SDK/Gradle dependencies; the **produced application itself** is still offline and declares no INTERNET permission.

Build pipeline: static policy checks, Python tests, actual Kotlin self-tests via Gradle JavaExec, Android `assembleDebug`, `lintDebug`, APK SHA-256/manifest badge verification, private artifact retention 14 days. Running the job does not imply all tests passed. Only an execution log, artifact hash and manifest inspection can justify `ANDROID_BUILT`.

A successful CI build means **ANDROID_BUILT**, not `DEVICE_VERIFIED`: Samsung A52 installation, offline/network isolation and physical power/thermal measurements remain required. This is the diagnostic lab, not a trained AI or release.