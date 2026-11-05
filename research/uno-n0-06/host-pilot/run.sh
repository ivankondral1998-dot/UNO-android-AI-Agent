#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
N005="${N005_SOURCE_ROOT:-$ROOT/baseline_n005}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
javac -encoding UTF-8 -d "$TMP" \
  "$N005/host-test/org/json/JSONArray.java" \
  "$N005/host-test/org/json/JSONObject.java" \
  "$N005/host-test/org/json/JSONException.java" \
  "$N005/android/src/org/unovyra/n005audit/NeuralGraph.java" \
  "$ROOT/src/org/unovyra/n005audit/N006HostPilot.java"
java -cp "$TMP" org.unovyra.n005audit.N006HostPilot
