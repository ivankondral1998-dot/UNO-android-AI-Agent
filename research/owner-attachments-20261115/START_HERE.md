# UNO F/S4 research: entry point for agents (16.11.2026)

> **ТЕКУЩИЙ СТАТУС 17.11.2026 (после бинарных коммитов):** Из минимум **16 подтверждённых уникальных оригинальных ZIP-потоков** **15 сохранены** в существующей research-ветке: **11** отдельными Git blobs, **4** побайтно восстанавливаются из Git parts. Две ранние версии 005/005_SAFE лежат в `original-zips/early-v1/`; компактный 005B с финальными весами, S4_WM_007, оригинальный CODEX_TRAIN001 и Windows-ready `UNO_CODEX_TRAIN001_HANDOFF_20261115(1).zip` находятся в `original-zips/<имя>.parts/` с `manifest.json`. Отсутствует только **252 091 601-байтный `uno_ladder_005b_gpu.zip`**, который владелец решил **не загружать лишь ради архива**: его 47 промежуточных optimizer checkpoints не восстановимы из малых ZIP. Второй большой upload отдельно не проверен. У каждого загруженного блока подтверждены размер и Git blob SHA-1 в удалённом дереве; для новых 005B (14 частей) и Windows handoff (25 частей) локально собраны ZIP, проверены полный SHA-256, CRC и побайтное совпадение с оригиналами. Обратное скачивание бинарных данных из GitHub текущий коннектор не поддержал; **remote re-download SHA256 не объявляется пройденным**. Производный 20.8-МБ ZIP только финальных весов не сохранён как самостоятельный объект, но исходный компактный ZIP с этими весами сохранён. Исторические таблицы и статусы ниже относятся к **16.11 до этих коммитов**.

**Сводная карта работы и результатов для новых агентов:** [AGENT_RESEARCH_HANDOFF_20261116.md](AGENT_RESEARCH_HANDOFF_20261116.md). Машинный JSON-аудит ZIP: [audit_research_artifacts.py](audit_research_artifacts.py). Это дополнения к существующим первоисточникам, не отдельные правила.

**Scope:** read-only navigation, evidence and backup status, NOT new agent authority. The only current agent rules are **main/AGENTS.md**. Work in the pre-existing `research/uno-train-001-s4-20261115` branch for the F/S4/TRAIN line; inspect live HEAD first. Do not create branches, delete or overwrite original evidence, merge into main, or start Actions without applicable owner approval.


## Обновление объёма резервирования по указанию владельца, 16.11.2026

**НЕ загружать большой `uno_ladder_005b_gpu.zip` (252 МБ) только ради коллекции материалов.** Для ознакомления агентам доступны все 48 его программных файлов через восемь уже сохранённых малых ZIP (подробное совпадение: `005B_SPLIT_RESULT_20261116.md`). Не следует требовать этот большой архив как условие начала дальнейшего исследования. Но 47 старых промежуточных optimizer checkpoints из него удалённо не восстановимы: честно сохранить статус `NOT_IN_GIT`.

**Сначала изучить результаты:** [EXPERIMENT_RESULTS_MATRIX.md](EXPERIMENT_RESULTS_MATRIX.md) с точными сравнительными таблицами 005B / 007 / TRAIN-001 / TRAIN-002. Теперь в Git побайтно проверены **[005B SUMМARY + 30 исходных JSON](results-005b/)** и **[007 README, исходник, тесты, CPU-метрики, управляющие тексты](study-007/)**; исходные ZIP с бинарными промежуточными состояниями остаются отдельно учтёнными. Для восстановления читаемых файлов и тестов из девяти существующих Git ZIP использовать [extract_research_sources.py](extract_research_sources.py), без дублирующего хранения сотен мегабайт. Это восстановление исходников, не новые испытания.

Оригиналы `UNO_S4_WM_007.zip` и `UNO_CODEX_TRAIN001_HANDOFF_20261115.zip` теперь **побайтно восстанавливаются из Git** через `original-zips/<имя>.parts/` и `restore_split_zip.py`: SHA-256 каждой части, Git blob SHA-1 и итоговые SHA-256 сверены с пользовательскими оригиналами. Эти два ZIP **не лежат отдельными Git-файлами**, но их исходные байты сохранены. Компактные финальные веса 005B и отдельный Windows-ready handoff (37,8 МБ) остаются не подтверждены в Git. Полнота архивирования ZIP и доступность материалов исследований — разные показатели.

**Машинный каталог 70 исходных текстов из девяти сохранённых ZIP:** [EXTRACTED_TEXTS_MANIFEST.json](EXTRACTED_TEXTS_MANIFEST.json) (побайтные SHA-256, исходный ZIP и путь внутри). [extract_research_sources.py](extract_research_sources.py) опубликован в точности той же версией, которая локально восстановила 70 файлов из 9 архивов; Git blob SHA-1 исходного проверенного скрипта `4043c0c2bb730fe9bb831badfaf6d24d2ae3fcfe`. Сравнение сохранённых текстов/хешей не равно новому запуску моделей.

## Reading order and result provenance

| Stage | Where to read / original artifact | Verified scope, not an inferred outcome |
|---|---|---|
| 001 pilot F | `original-zips/UNO_F_PILOT_001.zip`, its README and CPU metrics | Earlier pilot and CPU artifact, not current UNO production weights |
| 002 GPU-safe | `original-zips/UNO_GPU_SAFE_002.zip` | Protective code/tests, not proof of productive GPU training |
| 003 memory | `original-zips/UNO_F_MEMORY_003.zip` | Early long-memory experiment |
| 004 working memory | `original-zips/UNO_F_WORKING_MEMORY_004.zip` | Early working-memory implementation |
| 005 diagnosis | `original-zips/UNO_F_DIAG_FIX_005.zip` | Diagnostic changes; compare README/tests |
| 005 Ladder | `original-zips/UNO_F_LADDER_005.zip`, `UNO_F_LADDER_005_SAFE.zip`, `UNO_F_LADDER_005B.zip` | Synthetic ladder/GRU comparisons; study limitations in the ZIPs |
| 005B GPU full | `uno_ladder_005b_gpu.zip` (**NOT GIT-PRESERVED**), `UNO_005B_FINAL_WEIGHTS_AND_RESULTS_20261115.zip` (**NOT GIT-PRESERVED**) | Full and compact GPU research archives are distinct; compact is NOT an exact substitute for all optimizer checkpoints |
| 006 cause | `UNO_F_CAUSE_006.py`, `UNO_F_CAUSE_006_REPORT.txt` in this directory | User supplied CPU diagnostic, not a learned S4 breakthrough |
| 007 S4 WM | `study-007/` и `original-zips/UNO_S4_WM_007.zip.parts/` (**EXACT RESTORABLE**) | Original code/tests/CPU result, exact source ZIP recoverable from Git parts; fixed-address prototype, not trained Wk/Wv |
| TRAIN-001 | `../train001/RESULT.md`, `../train001/CONTINUATION_RESULT.md`, `../train001/README_RTX.md`, `original-zips/UNO_TRAIN001_RESULTS_20261115.zip` | Original RTX result: full 253/320 vs inference memory_off 148/320; **NOT** fair retrained F-only baseline |
| TRAIN-002 | `../train002/RESULT.md`, `../train002/MATH.md`, `../train002/evidence/`, `../train002/delivery/UNO_TRAIN002_RTX_20261115.zip` | Reproduced TRAIN-001 on CPU; 30 incompatible auxiliary targets; order partly decodable. Chronology and 27-run matrix PREPARED; GPU/Windows/quality tests NOT DONE |

Historic `UNO_CODEX_TRAIN001_HANDOFF_20261115.zip` is **EXACT RESTORABLE from Git parts** in `original-zips/`; Windows-ready `UNO_CODEX_TRAIN001_HANDOFF_20261115(1).zip` is **NOT GIT-PRESERVED**. User-supplied original `CODEX_TRAIN001_TASK_20261115.txt` is preserved here, not test evidence.

## Backup truth and machine check

The only machine-readable inventory for these **14 latest-file-name ZIP entries** is [ARTIFACTS.tsv](ARTIFACTS.tsv). Each row records original bytes, SHA-256, Git blob SHA-1, ZIP entry count and exact Git path (or `-` if pending). **9/14 original ZIPs are single matching Git blobs, and 2 further ZIPs are exactly recoverable from tracked parts** when a checked-out branch is verified. **3/14 are not confirmed recoverable as original bytes** (including the intentionally excluded 252-MB archive). This is a raw-ZIP archival statistic, NOT a measure of research-source coverage. The source ZIPs passed complete CRC checks (14/14). The separate TRAIN-002 delivery ZIP exists in `../train002/delivery/` and is **not** one of these fourteen originals.

Run against locally available original ZIPs:

```sh
python3 research/owner-attachments-20261115/verify_archives.py --source /path/to/original-zips
# If the current research branch is checked out with original blobs:
python3 research/owner-attachments-20261115/verify_archives.py --source /path/to/original-zips --repo /path/to/UNO-checkout
# Optional whole-original-archive gate (not required for the owner's research-usability goal):
python3 research/owner-attachments-20261115/verify_archives.py --source /path/to/original-zips --require-all-git
```

This tool is **read-only** and requires Python standard library only. It detects source corruption, CRC failures, dangerous member names, and mismatching checkout copies. The Git tree cross-check in this audit used source-derived Git SHA-1 and size to match remote Git object IDs; this verifies content-addressed identity without claiming that a ZIP was independently downloaded from GitHub. The ZIP verifier does not qualify model accuracy or Android execution.

## Tooling and transfer constraints

- ChatGPT conversation files are already mounted in the runtime as originals; use their real paths for local hashing instead of calling a failing rematerialization or guessing a filename path.
- The GitHub `fetch_file` call on this branch for `AGENTS.md` returns 404 **by design**: canonical instructions are `main/AGENTS.md`. Never "fix" by inventing a new branch-local AGENTS.
- The connected GitHub write endpoints take UTF-8 or base64 **string payloads**, not local container paths. A local ZIP cannot be made remotely present by committing a receipt. Use an actual binary transfer/Git LFS route where available; then download/compare SHA-256 and update the exact `git_path` value.
- The 252,091,601-byte original exceeds the usual GitHub single-object size ceiling. Preserve through Git LFS or another owner-approved durable storage with verified retrieval. Do not replace originals with summaries, extracted files, blank placeholders or fabricated LFS pointers.

## Next verifiable steps

1. Prioritize research usability: preserve distinct source code, experiment configurations, verified evaluation results, final weights and reproducibility instructions. Full original ZIP byte-for-byte preservation is a separate optional archival goal, not a gate for the owner's requested research handoff. Do not require the 252 MB original or 47 intermediate optimizer checkpoints for agent research use.
2. Fetch uploaded objects and verify bytes, update `ARTIFACTS.tsv`, run the checker with `--require-all-git`, then revise the archival status. Until then: **PARTIAL BACKUP**.
3. For experiments, follow TRAIN-002 README: Windows `Run.ps1 Check` on an RTX first; **27 GPU training runs have not been performed**. Do not quietly re-run or change the locked test.
4. Work-log entry must follow the location and permissions in `main/AGENTS.md` (separate existing branch). This guide is not an alternative canonical log.


## Version audit addendum: repeated uploads (16.11.2026)

The initial **14 ZIP rows represent 14 distinct filenames / latest accessible mounted copies**, **NOT all historic versions**. Rematerializing earlier chat uploads uncovered **two additional, distinct, CRC-valid ZIP contents**, both still absent from Git. They are pinned by original user upload ID, size and SHA-256 in [EXTRA_VERSIONS.tsv](EXTRA_VERSIONS.tsv):

- Early `UNO_F_DIAG_FIX_005.zip`: 28,103 bytes / 7 entries; later 30,860-byte version already stored in Git.
- Early `UNO_F_LADDER_005_SAFE.zip`: 20,404 bytes / 9 entries; later 20,882-byte version already stored in Git.
- A *second* 252,091,601-byte `uno_ladder_005b_gpu.zip` chat attachment could not be independently rematerialized (file tool 100-MiB cap). Its SHA-256 may or may not match the available copy; **do not count it as verified duplicate**.

**Confirmed minimum is therefore 16 distinct ZIP byte streams, 9 stored, 7 not stored in Git.** Additional unverified duplicate contents may change that count. These early ZIPs must be archived without overwriting their later names (e.g. version-qualified paths).

Five other **byte-exact** original text attachments are now stored in [text-versions/](text-versions/): three earlier README_RU variants and two historic 005B summary variants. Their Git object IDs were checked against raw original bytes. These files are documentation/evidence, not new tests and not substitutes for the original ZIPs. Three user-supplied Windows console logs are now also stored **byte-for-byte** under [text-versions/](text-versions/) as `CONSOLE_RTX_SETUP_02.txt`, `CONSOLE_RTX_SETUP_03.txt`, `CONSOLE_RTX_SETUP_04.txt`; original SHA-1 Git blob identities were checked against the uploaded ChatGPT text including CRLF. They are historical diagnostics, not proof of CUDA qualifications. UI screenshots remain in chat and are not backed up to Git.

## New split artifacts: 005B programs / final weights (16.11.2026)

See [005B_SPLIT_RESULT_20261116.md](005B_SPLIT_RESULT_20261116.md) for exact sizes, SHA-256, scope and limits. **48/48 program files from the 252 MB original are already byte-identical in eight earlier small ZIPs preserved on this branch.** Two local convenience ZIPs were created (144 KB programs only; 20.8 MB final weights+results). The **final weights-only package is not yet verified uploaded to GitHub**, and 47 historical optimizer checkpoints are excluded. Do not claim complete remote preservation.
