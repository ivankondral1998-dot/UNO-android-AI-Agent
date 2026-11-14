# UNO — независимая процедура приёма агентом (2026-11-06)

1. Открыть [вход](00_START_HERE_CURRENT.md), [полный индекс](01_ALL_AVAILABLE_SOURCES_AND_KNOWN_GAPS_20261106.md) и зафиксировать Git HEAD. Исходная ветка integration создана от research commit `efdb1767ef75cbdb04ff813323c107c3bd22c4b6`. `main` отдельно.
2. Локально в корне клона: `python -B docs/precode/vnext-r4/verify_mirror.py`. Это проверяет 178 файлов, перечисленных в первичном [MIRROR_SHA256](../precode/vnext-r4/MIRROR_SHA256.json); 2 файла (сам манифест и verifier) вне самопроверки. Результат при создании: `178 / 178 verified`.
3. Затем `cd docs/precode/vnext-r4/package`; `python -B verify_package.py` → `DELIVERY_INTEGRITY_OK files=119 source_git_blobs=64 source_sha256=63 V_blocks=20 gates=80`; `python -B evidence/recheck.py` → all listed host checks OK (18 case fixtures); исторические V01–V20 full end-to-end и Android не запускались.
4. Все 120 членов R4 лежат в `package/`. 13 файлов R3 лежат в `../vnext-r3/package/`. 20 V-скриптов в `package/evidence/v_sources/`; combined original rev2 в [owner archive mirror](../archive/owner-complete-work-20261106/workspace/uno_r4_audit_inputs/raw_v/UNOVYRA%20AI%20Agent%20Adaptive%20Neural%20Organism/UNO_R41_A52_V01_V20_ALL_TESTS_AND_RESULTS_REV2_2026-11-04.txt).
5. Реестр `OWNER_COMPLETE_WORK_ARCHIVE_INDEX_20261106.json` охватывает 396 членов старого ZIP. Не пытаться вывести существование файла вне репозитория из отсутствия его Git-path. Проверять `repo_path`, `status` и SHA-256.
6. Source bytes/Python scripts ≠ trained production Θ, good adaptive utility, Android OS effect or OWNER_APPROVED_PRECODE. G4/G5 остаются отдельными gate.

GitHub Actions не требуются. Никаких изменений source-package R5.3 или оригинального R4 `package/` при этой процедуре.
