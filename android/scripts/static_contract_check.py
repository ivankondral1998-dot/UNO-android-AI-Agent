#!/usr/bin/env python3
"""Static fail-closed guard for the WP-01 offline diagnostic APK.
Not an Android build, runtime network monitor, authority proof, or model quality test.
"""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ANDROID = '{http://schemas.android.com/apk/res/android}'
REQUIRED_FALSE = ('allowBackup', 'fullBackupContent', 'usesCleartextTraffic')
FORBIDDEN_SOURCE = (
    (r'\bjava\.net\.', 'java.net'),
    (r'\bokhttp3\.', 'OkHttp'),
    (r'\bio\.ktor\.client\.', 'Ktor client'),
    (r'\bHttpURLConnection\b', 'HttpURLConnection'),
    (r'\bWebView\s*\(', 'WebView constructor'),
    (r'\bACTION_SEND(?:TO|_MULTIPLE)?\b', 'outbound intent'),
    (r'\bAccessibilityService\b', 'AccessibilityService'),
)


def scan(root: Path) -> list[str]:
    errors: list[str] = []
    manifest_path = root / 'app/src/main/AndroidManifest.xml'
    try:
        manifest = ET.parse(manifest_path).getroot()
    except (OSError, ET.ParseError) as exc:
        return [f'manifest_unreadable:{type(exc).__name__}']

    for node in manifest:
        if node.tag in ('uses-permission', 'uses-permission-sdk-23', 'permission'):
            errors.append(f'unexpected_permission:{node.get(ANDROID + "name", "?")}')

    app = manifest.find('application')
    if app is None:
        return errors + ['missing_application']
    for attr in REQUIRED_FALSE:
        if app.get(ANDROID + attr) != 'false':
            errors.append(f'app_{attr}_not_false')

    activities = app.findall('activity')
    services = app.findall('service')
    # The laboratory launcher remains the only exported Activity. WP-04 adds an
    # internal-only text chat screen; fail closed for any other Activity or filter.
    by_name = {node.get(ANDROID + 'name'): node for node in activities}
    if len(activities) != 2 or set(by_name) != {'.UnoActivity', '.UnoChatActivity'}:
        errors.append('unexpected_activity_catalog')
    else:
        lab = by_name['.UnoActivity']
        chat = by_name['.UnoChatActivity']
        if lab.get(ANDROID + 'exported') != 'true':
            errors.append('missing_launcher_export')
        if chat.get(ANDROID + 'exported') != 'false' or chat.find('intent-filter') is not None:
            errors.append('unsafe_chat_activity')
    if len(services) != 1 or services[0].get(ANDROID + 'name') != '.NeuralWorkerService':
        errors.append('unexpected_service_catalog')
    elif services[0].get(ANDROID + 'isolatedProcess') != 'true' or services[0].get(ANDROID + 'exported') != 'false':
        errors.append('unsafe_neural_worker')
    for component in app:
        if component.tag in ('receiver', 'provider', 'activity-alias'):
            errors.append(f'unreviewed_component:{component.tag}')

    code_dir = root / 'app/src/main/kotlin/org/unovyra/uno'
    sources = sorted(code_dir.rglob('*.kt'))
    if not sources:
        return errors + ['app_kotlin_source_missing']
    code = '\n'.join(source.read_text(encoding='utf-8') for source in sources)
    for pattern, label in FORBIDDEN_SOURCE:
        if re.search(pattern, code):
            errors.append(f'unexpected_api:{label}')
    # These positive checks are intentionally narrow: strings in comments are not sufficient.
    activity = next((s.read_text(encoding='utf-8') for s in sources if s.name == 'UnoActivity.kt'), '')
    if not re.search(r'TrustController\s*\(\s*DenyAllAndroidPort\s*\(\s*\)\s*,\s*DenyAllLedger\s*\(\s*\)', activity):
        errors.append('missing_fail_closed_controller_wiring')
    if not re.search(r'NoWeightsNeuralPort\s*\(\s*\)', activity):
        errors.append('neural_placeholder_not_fail_closed')
    if 'labStop.stop()' not in activity or 'controller.stop()' not in activity:
        errors.append('missing_activity_abort_integration')
    if 'LabProfile.STRESS' not in activity:
        errors.append('manual_lab_control_missing')
    # These checks prevent regression to the old UI with no manual JSON export.
    # Source markers alone do not establish Android runtime/clipboard behavior.
    if 'Проверить SQLite (без создания базы)' not in activity or 'Проверить владельца через экран Android' not in activity:
        errors.append('owner_and_sqlite_diagnostics_missing')
    if 'ClipData.newPlainText' not in activity or 'copyableReport' not in activity or 'copyFullReport()' not in activity:
        errors.append('full_report_clipboard_export_missing')
    if 'УСТАНОВЛЕННЫЙ ПАКЕТ: $packageName' not in activity:
        errors.append('package_identity_not_displayed')
    # The owner's credential/one-use outcome must be visible adjacent to buttons.
    # Merely updating the global status at the top creates an apparent no-op.
    if (('root.addView(ownerFeedback)' not in activity and 'advancedContainer.addView(ownerFeedback)' not in activity) or
            'showOwnerFeedback(if (consumed)' not in activity or
            'showOwnerFeedback(if (accepted)' not in activity):
        errors.append('owner_local_result_feedback_missing')
    if ('runAppPrivateEffectProbe()' not in activity or
            'AppPrivateReadbackProbe.run(filesDir)' not in activity or
            'AppPrivateReadbackProbe.inspect(filesDir, outcome.id)' not in activity or
            'inspectLastAppPrivateEffect()' not in activity or
            'AppPrivateReadbackProbe.inspect(filesDir, id)' not in activity):
        errors.append('app_private_effect_readback_ui_missing')
    # Existing passive device probes must not secretly populate durable memory.
    start = activity.find('private fun runSimple(')
    end = activity.find('private fun confirmExactObservation()', start)
    if start < 0 or end <= start:
        errors.append('passive_probe_or_consent_section_missing')
    else:
        passive = activity[start:end]
        if ('observeDeviceSnapshot(' in passive or
                'UnoAndroidMemoryOwner.exact(' in passive or
                'runExactObservationWithConsent(' in passive):
            errors.append('implicit_exact_memory_write_in_passive_probe')
    if ('button("ЗАПИСАТЬ СНИМОК В ПАМЯТЬ UNO · отдельное согласие") { confirmExactObservation() }' not in activity or
            'AlertDialog.Builder(this)' not in activity or
            '.setPositiveButton("Сохранить") { _, _ -> runExactObservationWithConsent() }' not in activity):
        errors.append('explicit_exact_observation_consent_missing')
    if ('button("ОТОЗВАТЬ ДАННЫЕ ПАМЯТИ СНИМКОВ · отдельное подтверждение") { confirmExactRevocation() }' not in activity or
            '.setPositiveButton("Отозвать раздел") { _, _ -> revokeExactObservations() }' not in activity):
        errors.append('exact_observation_revocation_control_missing')
    # The authenticated exact observation references an independently retained
    # diagnostic file. A digest of compact JSON does not match its pretty form.
    if 'snapshot.toString(2).toByteArray(Charsets.UTF_8)' not in activity:
        errors.append('exact_observation_digest_mismatch')
    if 'DeviceProbe.persistImmutable(applicationContext, json)' not in activity:
        errors.append('exact_observation_evidence_not_immutable')
    if ('button("ПРОВЕРИТЬ ЗАПИСЬ ПАМЯТИ ПОСЛЕ ПЕРЕЗАПУСКА") { inspectLastExactObservation() }' not in activity or
            'private fun inspectLastExactObservation()' not in activity or
            '"SAME_BOOT_EXACT_AND_SOURCE_MATCH"' not in activity or
            'read.status != ExactStatus.COMPLETE' not in activity or
            '"EXACT_" + read.status.name' not in activity or
            '"diagnostics/observation-${digest!!}.json"' not in activity or
            '.put("new_vault_write_performed", false)' not in activity or
            'UnoAndroidExactMemory(applicationContext, readOnly = true).read(' not in activity):

        errors.append('exact_restart_readback_missing_or_unbounded')
    if ('putString("last_event_key", eventKey)' not in activity or
            '.putString("last_diagnostic_sha256", originalDigest).commit()' not in activity):
        errors.append('durable_exact_restart_locator_missing')
    # One-tap diagnostic must stay explicit and cannot bypass owner consent.
    if ('button("ПРОВЕРИТЬ UNO · ОДИН ТЕСТ") { runUnifiedSelfTest() }' not in activity or
            'advancedContainer.visibility' not in activity or
            'private fun runUnifiedSelfTest()' not in activity or
            'DeviceLab.run(applicationContext, LabProfile.QUICK, stop)' not in activity or
            'buildExactObservationReadback()' not in activity):
        errors.append('unified_one_tap_diagnostic_missing')
    single_start = activity.find('private fun runUnifiedSelfTest()')
    single_end = activity.find('private fun runSensorInventory()', single_start)
    if single_start < 0 or single_end <= single_start:
        errors.append('unified_diagnostic_scope_missing')
    else:
        single = activity[single_start:single_end]
        if any(x in single for x in (
                'runExactObservationWithConsent(', 'observeDeviceSnapshot(',
                'AppPrivateReadbackProbe.run(', 'ownerGate.begin(',
                'revokeExactObservations(', 'UnoAndroidMemoryOwner.exact(')):
            errors.append('unified_diagnostic_implicit_privileged_write')

    # Aggregation must be host-testable and cannot silently promote an incomplete
    # lab (or an unrecognized sub-check status) to whole-agent success.
    if (single_start >= 0 and single_end > single_start and
            ('UnoDiagnosticEvaluator.summarize(verdicts, stoppedNow)' not in single or
             '.put("status", summary.status)' not in single or
             '.put("stop_requested", stoppedNow)' not in single)):
        errors.append('unified_diagnostic_verdict_gate_missing')

    # An attempted read returning NOT_FOUND can be expired; do not claim no test ran.
    if (single_start >= 0 and single_end > single_start and
            ('"EXACT_DENIED" -> "DENIED"' not in single or
             '"EXACT_NOT_FOUND", "EXACT_UNKNOWN", "EXACT_TRUNCATED", "EXACT_CONFLICT" -> "UNKNOWN"' not in single)):
        errors.append('unified_exact_memory_status_overclaimed')

    adapter = (code_dir / 'UnoAndroidExactMemory.kt').read_text(encoding='utf-8') if (code_dir / 'UnoAndroidExactMemory.kt').exists() else ''
    if ('readOnly: Boolean = false' not in adapter or
            'EXACT_READONLY_SNAPSHOT_UNAVAILABLE' not in adapter or
            'initializeEmptyOnFirstOpen = !hasSnapshot && !readOnly' not in adapter or
            'EXACT_READONLY_WRITE_DENIED' not in adapter or
            'EXACT_READONLY_REVOKE_DENIED' not in adapter or
            'EXACT_READONLY_PENDING_RECOVERY' not in adapter or
            'FileInputStream(base)' not in adapter):

        errors.append('exact_readonly_disk_reopen_contract_missing')
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = scan(root)
    if errors:
        print('STATIC_PREFLIGHT_FAIL')
        for error in errors:
            print('FAIL', error)
        return 1
    print('STATIC_PREFLIGHT_PASS=GUARDS_OK (static only; NOT an Android build or runtime proof)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
