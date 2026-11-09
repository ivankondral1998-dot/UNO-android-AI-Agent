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
    if ('root.addView(ownerFeedback)' not in activity or
            'showOwnerFeedback(if (consumed)' not in activity or
            'showOwnerFeedback(if (accepted)' not in activity):
        errors.append('owner_local_result_feedback_missing')
    if ('runAppPrivateEffectProbe()' not in activity or
            'AppPrivateReadbackProbe.run(filesDir)' not in activity or
            'AppPrivateReadbackProbe.inspect(filesDir, outcome.id)' not in activity or
            'inspectLastAppPrivateEffect()' not in activity or
            'AppPrivateReadbackProbe.inspect(filesDir, id)' not in activity):
        errors.append('app_private_effect_readback_ui_missing')
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
