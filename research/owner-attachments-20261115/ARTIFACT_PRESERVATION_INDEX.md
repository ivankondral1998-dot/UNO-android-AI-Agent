**УТОЧНЕНИЕ ВЛАДЕЛЬЦА, 16.11.2026:** основная цель текущего поручения — доступность исходников, экспериментальных результатов и их проверяемой истории агентам; **252-МБ оригинал `uno_ladder_005b_gpu.zip` не загружать в Git только ради дублирования.** Его 48 программных файлов уже восстанавливаются из сохранённых малых ZIP. Теперь также сохранены побайтно исходные отчёты `results-005b/SUMMARY.txt` и 30 JSON, оригинальные README/код/тесты/CPU-метрики 007 в `study-007/`. Большой архив и не перенесённые бинарные веса/optimizer checkpoints не объявлять сохранёнными. Ниже прежний аудит исходных ZIP остаётся историческим и точным именно для *полной byte-for-byte архивации ZIP*, а не критерием обязательной загрузки большого файла.

# UNO — uploaded research artifact preservation audit (2026-11-15)

> **CURRENT CORRECTION, 16.11.2026, extended by duplicate-upload audit (read this before the dated audit below).** The original table headed "NOT verified as byte-for-byte files" is a **historical snapshot**, not current inventory. Subsequent commits stored nine exact original ZIP blobs in `original-zips/`. On 16.11 the 14 local ZIPs passed SHA-256 and full CRC; the nine Git tree blob SHA-1 and sizes matched the corresponding local originals. **9 VERIFIED STORED / 5 MISSING from the latest-name set; TWO MORE distinct earlier ZIP versions are also missing**; no new Windows/CUDA training was run. Current machine data: [ARTIFACTS.tsv](ARTIFACTS.tsv) and [EXTRA_VERSIONS.tsv](EXTRA_VERSIONS.tsv), runnable checker: [verify_archives.py](verify_archives.py), agent navigation: [START_HERE.md](START_HERE.md). One cannot declare archival completion until five pending bytes are durably stored and downloaded/checked.


Source: user-supplied files in the ChatGPT UNO conversation. This file is an **inventory**, not evidence that the listed binary archives are committed to GitHub.

## Authoritative destination / branch discipline

- Repository: `ivankondral1998-dot/UNO-android-AI-Agent`.
- **Existing research branch only:** `research/uno-train-001-s4-20261115`. Do not create a new branch for continuation, handoff, audits, TRAIN-002 or these evidence files without a new explicit owner decision.
- Agent authority and current rules come **only** from `main/AGENTS.md`. This inventory does not change that document.
- Baseline inspected before this inventory commit: `e3bbcdee7d00c2b1962ce30de7da8094064b8d8a`; TRAIN-001 checkpoint `b371b627ef743b876e13daadf3b57d6013f37652`; TRAIN-002 implementation `1427053ce92fc8479550520a4f90ab2f5366851b`.
- Never run GitHub Actions, merge to main, delete/rewrite originals, or claim untested CUDA/Android.
- Before a new commit, verify remote HEAD, use a fast-forward-only update, and report full SHA.

## Already in this branch, confirmed from Git tree

- `research/train001/`: trainer sources, CPU evidence and CUDA/Windows package builder and scripts.
- `research/train002/`: chronology study, independent CPU audit of TRAIN-001, controls, tests, artifacts, instructions.
- `research/train002/delivery/UNO_TRAIN002_RTX_20261115.zip` — 21,140,290 bytes, blob `c8260cc12010f4489d20a04a9ae7f649124b5b4d`.
- This commit also adds original text for CAUSE-006 and Codex's TRAIN-001 task under `research/owner-attachments-20261115/`.

## Binary ZIPs in conversation, **NOT verified as byte-for-byte files in this branch**

The filenames below are available in the conversation/container only. Some code/results are included **inside other packages**, which is not a byte-identical archival copy of each original ZIP.

| Original filename | Bytes | SHA-256 |
|---|---:|---|
| `UNO_F_PILOT_001.zip` | 1,223,406 | `3d1daee647530a920363358c595622ce3092afe41407339c31a4aa856aaabd96` |
| `UNO_GPU_SAFE_002.zip` | 20,656 | `b4f45047c3485b9cc7978567983348043caeedc9782db12cb5bf53c7742f6033` |
| `UNO_F_MEMORY_003.zip` | 22,241 | `b39471db11a47b4ea428b930213ade12cd23f2b21478e764d12dc185e3540fdf` |
| `UNO_F_WORKING_MEMORY_004.zip` | 26,786 | `d7a36551f23ce814ac5d7ccdd9acc96b7ca68b1123f4beda9b4ec1580a3aa47d` |
| `UNO_F_DIAG_FIX_005.zip` | 30,860 | `6dce0df4183aa1565c193fe16bc9dd69ab81fddb592ee8c29779c25c251ac81e` |
| `UNO_F_LADDER_005.zip` | 15,217 | `ae0b97075b54291d834424dc58d322c45e67caa04a1d66a2f8f64516542e8bd2` |
| `UNO_F_LADDER_005_SAFE.zip` | 20,882 | `5bf1f88f98b3c1a76f98028bee25e4b36959a52a0b8b7e96b1e4c99f883e7ac2` |
| `UNO_F_LADDER_005B.zip` | 22,590 | `39fd8a55f96a1a1f10c3cd3f2b8b2f5c8587310faac99df4c5bae5a3fb747dca` |
| `UNO_S4_WM_007.zip` | 4,022,100 | `d9ac20652576b788d60cf951e708ad22d7fae00fca35c9c7ae008149cc5bf2d8` |
| `UNO_CODEX_TRAIN001_HANDOFF_20261115.zip` | 5,379,990 | `69518b914c65035259abef803fd65a25bbc7dc4cbf17dfe084123840698c0313` |
| `UNO_005B_FINAL_WEIGHTS_AND_RESULTS_20261115.zip` | 21,119,051 | `38e6a42fe84c652245fdb76a656fbfc6e5a95f13844f8f4131e6f5914e74a7f5` |
| `uno_ladder_005b_gpu.zip` | 252,091,601 | `14648c2beb79313af8230c6b6643aa01319743095c6e128820cf19f9c9d1bf8d` |
| `UNO_CODEX_TRAIN001_HANDOFF_20261115(1).zip` | 37,766,879 | `43bcbf5206401f4d1755bccfd639d225409176ebb3da7673f6ce2c90ab30f5bc` |
| `UNO_TRAIN001_RESULTS_20261115.zip` | 2,089,975 | `6f39bf1b5a96cfb7a18d48c5c2deb13e3f78c6f5ee18c80502d934998318dcdc` |

Notably, `UNO_TRAIN001_RESULTS_20261115.zip` contains the actual trained `latest.uno` and its evaluation logs; **the full trained checkpoint is not currently stored as an independent GitHub artifact**. The original 005B ZIP is 252 MB and exceeds the ordinary GitHub 100 MB per-object limit; store via Git LFS or another owner-approved archive mechanism with verified hashes, rather than making an untracked empty placeholder. The compact 005B package omits intermediate Adam checkpoints and cannot substitute for complete training resume.

## Other input files / handling

- `UNO_F_CAUSE_006.py` and `UNO_F_CAUSE_006_REPORT.txt` are preserved as original source text in this commit; CPU-only, not a CUDA S4 result.
- `CODEX_TRAIN001_TASK_20261115.txt` is a user-supplied handoff task, not a test result.
- `README_RTX.md` and `CONTINUATION_RESULT.md` are already tracked under `research/train001/` (verify source/version rather than assuming filenames prove equality).
- Other local conversation materials: `SUMMARY.txt`, `SUMMARY(1).txt`, three `Вставленный текст(...).txt` pasted console logs, multiple earlier README attachments and screenshots. Preserve in the original conversation; do not blindly publish potentially sensitive UI captures. They are **not** counted as GitHub-preserved research files here.
- Python virtual environments, PyTorch wheels and Windows GPU drivers are reproducible tooling, not research model weights. Do not copy gigabytes of .venv to Git.

## Outstanding transfer / acceptance

1. Transfer **binary archives themselves** to this same branch (or Git LFS on this same branch), prioritizing trained TRAIN-001 results, full/compact 005B, early experiments 001–007 and Windows RTX reproducibility ZIP. Match exact SHA-256 shown above.
2. Confirm complete original byte size, SHA-256 and remote accessibility for each artifact. Commit an amended receipt/index only after verification. File hashes **alone are not backups**.
3. Do not call this archive complete until every required binary is independently retrievable from the repository or owner-approved durable storage.
4. Append required factual checkpoint to the existing canonical work log according to `main/AGENTS.md` when access and authorization allow, preserving historic entries.

Status: **PARTIAL ARCHIVE / MISSING BINARIES**. The fact that TRAIN-002 code and a 21 MB delivery ZIP are saved does not imply all earlier experiments/weights are saved.


## 16.11.2026 — повторная локальная проверка исходных вложений

Исполнитель: ChatGPT; источник: доступные в текущем чате оригинальные файлы `/mnt/data`, а не пересказ другого агента. Все **14 уникальных ZIP** из таблицы выше фактически открыты Python `zipfile`. Для каждого вычислен SHA-256 исходных байтов и сверен с таблицей: **14/14 совпадений**. Для каждого выполнен полный `ZipFile.testzip()` с чтением/проверкой CRC всех записей: **14/14 PASS**, включая `uno_ladder_005b_gpu.zip` размером 252091601 байт. Проверены пути участников архивов на абсолютные имена и `..`-компоненты: подозрительных путей не обнаружено. Это **интегритет ZIP**, не проверка безопасности исполняемого содержимого, качества модели либо воспроизводимости обучения.

Через GitHub API прочитан актуальный Git tree той же research-ветки. Вывод прежней инвентаризации о сохранности **не изменился**: исходные ZIP не найдены как самостоятельные byte-identical объекты Git этого HEAD; пакет `research/train002/delivery/UNO_TRAIN002_RTX_20261115.zip` есть, а исходный `UNO_TRAIN001_RESULTS_20261115.zip` и другие 13 оригинальных ZIP по-прежнему не восстановимы из данного Git tree как самостоятельные файлы. Локальный файл/ChatGPT-вложение не равно резервной копии на GitHub.

Действующее правило запрета новых веток опубликовано в каноническом `main/AGENTS.md` коммитом `847946595c66df31a6f155f2e33ca1ba6fabc069`. Попыток запуска Actions, CUDA, обучения, изменения исходников или удаления файлов не было. Фактический блокер закрытия полного GitHub-архива: подключённый GitHub-инструмент принимает текст либо `base64` содержимое, а не контейнерный путь к локальному бинарному вложению; контейнерный `git` не имеет сетевого доступа к GitHub. Переслать сотни мегабайт через текстовый аргумент, выдавая это за надёжную загрузку, нельзя. Нужен прямой бинарный транспорт с Git/LFS и обратной сверкой; **не отмечать COMPLETE до его выполнения**.
