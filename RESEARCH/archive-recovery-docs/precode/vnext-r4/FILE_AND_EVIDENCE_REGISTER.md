# Реестр источников, наличия и проверки (на 2026-11-06)

| Объект | Где искать в ЭТОЙ ветке | Что реально известно | Статус |
|---|---|---|---|
| R5.3 NORMATIVE/01–06, Astra текущие, R51/R52 | `docs/precode/r5.3/source-package/` | Ранее зеркалирован на SHA fcddf0f и унаследован из research SHA efdb1767; оригиналы не перезаписаны | PRESENT / SOURCE DOCUMENTED |
| Astra полный final и первичные red-team audits | `docs/precode/vnext-r4/package/sources/source-package/SOURCES/ASTRA_CURRENT/`, `docs/audit/astra-20261102/` | Раздельные original source и повторная история red-team | PRESENT / PRESERVED |
| R4.1 интегрированная формула | `docs/precode/vnext-r4/package/R4_1_INHERITED_BASE.md` | Полные разделы; не замещены summary | PRESENT / DOCUMENTED |
| R4.1 инженерный аудит и host evidence | `docs/audit/r41-engineering-20261104/` | Отдельные результаты, артефакты и исходники, не Android product | PRESENT / LOCALLY REPRODUCED SELECTED |
| vNEXT-R3 | `docs/precode/vnext-r3/package/` | Все 13 исходных файлов, включая ERRATA и проверки | PRESENT / PRESERVED |
| vNEXT-R4 | `docs/precode/vnext-r4/package/` | Все 120 члена ZIP, встроенные источники, frozen card, counterexamples | PRESENT / LOCALLY REPRODUCED SELECTED |
| V01–V20 rev2 | `docs/precode/vnext-r4/package/evidence/v_sources/` | 20 первичных Python-стендов, SHA через R4 evidence; три адресных counterexamples V14/V19/V20 | PRESENT / BYTES VERIFIED / NOT FULL DEVICE REPLAY |
| R4 индивидуальные gates | `docs/precode/vnext-r4/package/R53_ORIGINAL_INDIVIDUAL_GATES.md`, `package/UNO_EVIDENCE_TRACEABILITY_AND_TEST_GATES.md` | 80 индивидуальных gates сохранены; PASS не приписывается всей системе | PRESENT / CANDIDATE |
| Research N0-01…N0-07 и Owner Teaching | `research/`, `UNO_LAB_REPORTS.txt`, `research/uno-lab-001/BENCH.txt` | Исследования частично HOST_TESTED/OWNER-REPORTED DEVICE, отрицательные результаты не исключаются | PRESENT / RESEARCH |
| N0-07 all 400 actual raw device export | Исходный ZIP/ research содержит stage5 reconstruction + owner's 400 review | **Байтово заверенный оригинальный полный raw экспорт не установлен** | MISSING SPECIFIC EVIDENCE (не все тесты) |
| Обученная production Θ, locked licensed dataset, production E2E Android | Отсутствует подтверждённый production checkpoint | Требуют отдельного G5 допущения и будущих испытаний; не задолженность Astra/R4 | NOT IMPLEMENTED / FUTURE GATE |
| Личные диалоги, PMB history и собранные экспериментальные APK | Только исходный приватный `UNO_ALL_WORK_AND_SOURCES_2026-11-06.zip` у владельца | Не копировать без классификации конфиденциальности и разрешений; в этом Git дереве этих байтов нет | EXIST OUTSIDE GIT / NOT MIRRORED |

Запрещён вывод «источников/математики/испытаний A52 не было»: аудиты и owner-reported опыты сохранены. Запрещено и обратное: «физический полноценный UNO доказан». Для каждого заявления указать слой и provenance.

ZIP оригинал R4 SHA-256 `85f203bbe6cd4f584ef70e9fd4cd77f4b2e11a6a0076c6607d946c5d82637ba6`. ZIP оригинал полной рабочей копии SHA-256 `8c87ebec317f9acd8398a1ff239edfccb193c0e182e0f91ef447bcb3b26ac02b`.
