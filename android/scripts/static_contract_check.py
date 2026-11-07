#!/usr/bin/env python3
"""Minimal static security and architecture preflight (does not compile Android)."""
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

root=Path(__file__).resolve().parents[1]
manifest=ET.parse(root/'app/src/main/AndroidManifest.xml').getroot()
ns='{http://schemas.android.com/apk/res/android}'
permissions=[x.get(ns+'name') for x in manifest.findall('uses-permission')]
errors=[]
if permissions: errors.append(f"unexpected manifest privileges: {permissions}")
activity=manifest.find('application/activity')
service=manifest.find('application/service')
if service is None or service.get(ns+'isolatedProcess')!='true' or service.get(ns+'exported')!='false':
    errors.append('worker service isolation missing')
if activity is None or activity.get(ns+'exported')!='true':
    errors.append('launcher activity mismatch')
code='\n'.join(x.read_text() for x in (root/'app/src/main/kotlin/org/unovyra/uno').glob('*.kt'))
for text in ('java.net.URL(', 'HttpURLConnection', 'OkHttpClient', 'WebView(', 'ACTION_SEND', 'AccessibilityService('):
    if text in code:errors.append('unexpected potential outbound/effect API '+text)
if 'DenyAllAndroidPort' not in code:errors.append('deny-all port missing')
if 'LabProfile.STRESS' not in code:errors.append('manual stress UI missing')
if 'labStop.stop()' not in code:errors.append('abort integration missing')
if errors:
    print('STATIC_PREFLIGHT_FAIL')
    for e in errors:print('FAIL',e)
    sys.exit(1)
print('STATIC_PREFLIGHT_PASS=7 ; NOT android compile, APK, offline proof or device verification')
