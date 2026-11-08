#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
kotlinc \
  "$ROOT/app/src/main/kotlin/org/unovyra/uno/OwnerConsentState.kt" \
  "$ROOT/app/src/main/kotlin/org/unovyra/uno/AndroidDeviceCredentialPlatform.kt" \
  "$ROOT"/scripts/owner_gate_host/stubs/*.kt \
  "$ROOT/scripts/owner_gate_host/OwnerConsentStateTest.kt" \
  "$ROOT/scripts/owner_gate_host/AndroidDeviceCredentialPlatformTest.kt" \
  -include-runtime -d "$TMP/owner-consent-host.jar"
java -cp "$TMP/owner-consent-host.jar" org.unovyra.uno.OwnerConsentStateTestKt
java -cp "$TMP/owner-consent-host.jar" org.unovyra.uno.AndroidDeviceCredentialPlatformTestKt
