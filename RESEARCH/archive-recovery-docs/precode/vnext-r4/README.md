# UNO vNEXT-R4 — документальная интеграция, не production

Дата источника: 2026-11-06. Последний полученный от владельца пакет `UNO_WORK_RETURN_PACKAGE_R4.zip` SHA-256 `85f203bbe6cd4f584ef70e9fd4cd77f4b2e11a6a0076c6607d946c5d82637ba6`.

**Начни с [единых инструкций](../../agent/00_START_HERE_CURRENT.md).** [Подлинный R4 start](package/00_START_HERE.md) → [R4 исправления](package/ERRATA_R4.md) → [кандидатная математическая спецификация](package/UNO_INTEGRATED_NEURAL_ORGANISM_PRECODE_CANDIDATE_vNEXT.md) → [R4.1 inherited base](package/R4_1_INHERITED_BASE.md) → [аудит](package/SOURCE_AUDIT.md) → [гейты](package/UNO_EVIDENCE_TRACEABILITY_AND_TEST_GATES.md) → [варианты решений владельца](package/UNO_OWNER_DECISION_OPTIONS_O01_O08.md).

`package/` = **побайтовая копия всех 120 членов R4 zip**, включая бинарные вложения, запечатанные источники Astra/Grok/R52 и оригинальные V01–V20. Не править, не сокращать, не перезаписывать. Коррекции только отдельными версионированными файлами.

База R5.3, статусы research и N0-07 не исчезают, см. Git-ветку и приведённые ссылки. Противоречия классифицировать как (1) точное содержание исходного файла, (2) позже подтверждённые факты/исправления, (3) ещё не проверено, (4) решение владельца. Не считать теоретическую арифметику измерениями A52 и успешные игрушечные тесты production.

Проверка: `python -B docs/precode/vnext-r4/verify_mirror.py` в корне этой ветки, отдельно `cd docs/precode/vnext-r4/package && python -B verify_package.py && python -B evidence/recheck.py`. Эта проверка **не** запускает исторические 20 end-to-end V-стендов и не использует Android.
