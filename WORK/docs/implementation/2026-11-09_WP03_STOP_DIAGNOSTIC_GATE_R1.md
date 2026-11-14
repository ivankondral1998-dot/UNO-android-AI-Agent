# UNO WP-03 STOP regression — bounded diagnostic scope, 2026-11-09

Authority: root `/AGENTS.md` V3. Parent HEAD `1b808385ede6018fb225a38a36b892bfe296c15e`. This patch does NOT select/enable a neural model, external Android action, native NativePort, or weights training.

Finding: owner STOP previously stopped the current `LabStop` and controller, but a new owner tap called `runAppPrivateEffectProbe()` which made a fresh `LabStop`; the UI could schedule another app-private marker write. This was a code-level finding, NOT a device result or NativePort privilege bypass.

Change: `UnoActivity` latches explicit owner STOP and denies new `execute()` diagnostics, including a separately scheduled worker after STOP. `AppPrivateReadbackProbe` independently latches explicit STOP in process and checks before create and after write; a new call may not create a fresh marker after the stop latch. An already-created marker remains `UNKNOWN_MAY_HAVE_WRITTEN` if stopped during execution. Separate read-only `inspect()` is allowed to recover evidence after STOP; reporting the readback may itself write an app-private diagnostic JSON. Theme changes remain owner UI settings, not Android action dispatch.

Scope: owner STOP is **process-local**, not a durable cross-reboot Android authority. STOP races with an already-in-flight filesystem syscall are not proved linearizable; STOP cannot undo a completed file effect. Android trust boundary remains `DenyAllAndroidPort`. Do not promote this fixture to trusted verb 15.

New regression cases appended to the Kotlin host probe test: STOP blocks subsequent writes after a previous successful marker; sticky stop on repeat; read-only reopen after STOP. Old nine host tests retained.

Verification at commit creation: source patch patterns checked against exact GitHub blob/parent; existing workflow path filters inspected. **HOST_TESTED=NOT_RERUN; ANDROID_BUILT=NOT_RERUN; DEVICE_VERIFIED_WP03=FALSE.** Next required validation is `bash android/scripts/test_app_private_effect_host.sh`, full preflight and SDK35 build before a new APK. Existing owner A52 build `ci42512824888` predates this patch. No GitHub Actions were started.
