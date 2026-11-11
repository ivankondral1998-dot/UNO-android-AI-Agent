# UNO — independently testable host utilities (11 November 2026)

This directory contains **only two self-contained, host-tested utilities** copied byte-for-byte as Git blobs from `feat/uno-foundation-hardening-20261107` at `031b01f29966258a9291e0bc0595dfaf33d89ae0`:

- `ProbeMath.kt` — latency statistics and a true skipped computation branch.
- `UnoDiagnosticSummary.kt` — fail-closed summary of lab diagnostics; **never** certifies agent readiness.

Their original tests are included unchanged. To run locally with Kotlin compiler and Java:

```sh
kotlinc android/core/src/main/kotlin/org/unovyra/uno/core/{ProbeMath,UnoDiagnosticSummary}.kt \
  android/core/src/test/kotlin/org/unovyra/uno/core/{ProbeMathTest,UnoDiagnosticSummaryTest,MainPromotionHostTest}.kt \
  -include-runtime -d /tmp/uno-main-host-tests.jar
java -jar /tmp/uno-main-host-tests.jar
```

Expected marker: `UNO_MAIN_PROMOTION_HOST_PASS=13`. Host verification was performed in the assistant's local Linux environment on 2026-11-11. It does **not** mean Android build, device test, neural inference, product acceptance, or release. No GitHub Actions run was requested.

**Preservation:** original feature branch and all historical research remain unchanged. No neural weights, Android application, experimental GGUF integration, unfinished authority/memory or signing mechanism is promoted by this commit.
