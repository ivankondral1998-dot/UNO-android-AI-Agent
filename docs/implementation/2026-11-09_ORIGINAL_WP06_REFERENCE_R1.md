# R1 — Original UNO roadmap repair and neutral integrated reference

The earlier ad hoc patch labels WP-05 (text cycle) and WP-06 (GGUF picker)
are EXPERIMENTAL PATCH LABELS, not original roadmap stages. The original plan
defines WP-03 operator F, WP-04 model weights, WP-05 exact/semantic memory,
WP-06 unified end-to-end agent. No original stage is closed by those patches.

This change supplies a real HOST-ONLY WP-06-T01 reference trajectory:
typed Percept -> bounded scheduler -> shared ExactMemory observation ->
one NeuralPort -> untrusted Proposal -> explicit owner-consent interface ->
TrustController -> typed native attempt -> reference readback status.

JVM fake receipts remain REFERENCE_READBACK_CLAIM with
verifiedAndroidEffect=false, never VERIFIED_COMPLETION memory. Native UNKNOWN
is MAY_HAVE_EXECUTED, no automatic retry. One-way STOP and concurrency gates
are exercised. Existing Android DenyAllAndroidPort and NoWeightsNeuralPort
remain; this does not create Android action authority, a new brain, F, or weights.
Process-wide STOP from the chat is now also considered in laboratory action
admission, NOOP owner confirmation and app-private marker creation. Read-only
post-STOP reopening is still allowed as previously documented.

Test/acceptance: standalone host suite, SDK build and lint required;
Android device verification and full foundation closure still NOT achieved.
Existing sources/archives and the current feature history remain unchanged.
No training, no new permissions, no release, no main merge.
