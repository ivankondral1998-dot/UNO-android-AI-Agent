# Permanent APK v1 — local signed build 2026-11-11

Source branch `feat/uno-permanent-full-foundation-20261111` @ `e90b5211aa072b597527992ba8f91321f7379a60`.

| Field | Value |
|---|---|
| package | `org.unovyra.uno` |
| versionCode | 1 |
| versionName | `0.1.0-lab.1` |
| label | UNOVYRA UNO |
| apk sha256 | `74f7ec1e3be4961dfb4e7d1530d8948bbebcecce7971b00d0dc9b8311f4c8941` |
| signer sha256 | `58c92aec4b4ffe2dda8e1cb481e0216b2f51f3aabe4470b919036e7abdb99f51` |
| native | arm64-v8a, `libuno_llama.so` + `libllama.so` + ggml |
| permissions | none of INTERNET, RECORD_AUDIO, CAMERA |
| device install | not done |
| prior `.ci*` packages migrated | no |

Gradle `:app:assembleDebug` and `:app:lintDebug` finished `BUILD SUCCESSFUL in 4m 30s` on the executor (SDK 35, NDK 27.2.12479018, Gradle 8.7). Host preflight on the same tree printed `UNO_WP01_HOST_PASS=336` and `UNO_LAB_PREFLIGHT_SUCCESS`.

The private key is not in this repository. A separate private repository `ivankondral1998-dot/UNO-owner-signing-backup` holds the PKCS12 and password. GitHub Actions secrets and secret gists were not writable by the current token (HTTP 403). This APK does not update `org.unovyra.uno.scaffold.ci42670625565`.

`DEVICE_VERIFIED=FALSE`. `NoWeightsNeuralPort` still fails closed. This is the permanent install channel, not a finished neural product.
