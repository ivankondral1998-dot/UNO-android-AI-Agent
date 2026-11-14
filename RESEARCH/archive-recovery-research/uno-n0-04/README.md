# UNO-N0-04 Android research (2026-11-05)

Research-only isolated prototype: physical Android accelerometer, qualitative neural conjunction graph with no learned numerical synaptic weights, sequential A->B->A prospective prediction experiment, persistence check and baselines. NOT commercial UNO, NOT an approved replacement of R5.3.

## Source and reproducibility
- `source_bundle.tar.xz`: complete exact research Java/Android sources under `android/`, plus experiment card and phone instructions. SHA-256 (locally recorded before upload): `f0d1a722baf63af3efc959e89c1d43410c0d11f0d54774cd75a6e5d908983b90`; Git blob `8a21b8cb7730e81950c221496e46f3301e517284`.
- `RESEARCH_CARD_FROZEN_BEFORE_DEVICE_RUN.md`: criteria fixed BEFORE GitHub Actions Android build/device trials.
- `PHONE_TEST_RU.md`: owner device steps.
- Build workflow: `.github/workflows/uno-n0-04-android-research.yml` on research branch, authorized by owner in chat on 2026-11-05. Workflow only compiles & signs APK; it **does not run phone training**.
- Separate package `org.unovyra.n004research`, no Internet/runtime permissions, no dependence on Jarvis or N0-03. Offline at runtime.
- APK signing key generated on ephemeral CI runner; NEVER committed. Each CI re-run may have different signing identity (updates might require uninstall—do not do that automatically).

## Status
Source IMPLEMENTED. CI / ANDROID_BUILT / DEVICE_RUN status: check live workflow/artifact and owner-supplied A52 report. No performance or learning PASS until five device stages and checkpoint restore. R5.3 G4/G5 untouched.
