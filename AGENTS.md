> **FULL SOURCE DISCOVERY UPDATE (2026-11-06):** In this integration branch 275 new documentation/evidence blobs were SHA-verified after GitHub upload. Read [ALL AVAILABLE SOURCES + coverage policy](docs/agent/01_ALL_AVAILABLE_SOURCES_AND_KNOWN_GAPS_20261106.md), including the 396-member complete-archive register; **indexed-but-not-mirrored is NOT the same as non-existent**. This line supersedes any smaller archive count below.

> **MANDATORY CURRENT ROUTE (2026-11-06, vNEXT-R4 integration branch):** Read [the current agent entry](docs/agent/00_START_HERE_CURRENT.md) before judging available evidence or editing anything. R5.3 remains a candidate; owner G4 approval and production code remain FALSE. R4 originals and prior Astra/R4.1/R3 source versions are preserved and indexed there. Historical statements below describing *no experimental A52 tests* or *missing V01–V20* must not be generalized beyond their historical date. Neither current docs nor A52 research imply production readiness.

---

> **MANDATORY OWNER-INTENT GUARD / 2026-11-05:** UNO must learn from three **distinctly sourced** streams: sensory observations, explicit owner explanation/correction, and independently verified Android native postconditions. Owner meaning is not physical truth; learning/memory is not permission; dispatch is not success. N0-04/N0-05 did NOT test owner teaching or verified OS-action learning. EVERY research agent must read [the owner teaching and Android evidence contract](docs/research/OWNER_TEACHING_AND_ANDROID_EVIDENCE_20261105.md) and [N0-06 candidate research card](research/uno-n0-06/RESEARCH_CARD_CANDIDATE_20261105.md), alongside R5.3 sources. This addendum does not authorize production code, Android Actions or approval of G4/G5.

> **2026-11-05 live UNO-LAB research amendment:** **OWNER RESEARCH PERMISSION — ACTIVE 2026-11-05 (research branch only).** The owner explicitly authorized isolated, versioned research candidates for Θ, graph, P, M and learning rules, synthetic tasks, and training SMALL EXPERIMENTAL weights on a free PC environment. For EACH run: maximum 600 seconds, maximum 2 GiB RAM (use lower caps if the environment is weaker), terminate on limit; no more than 3 runs of the same candidate before reviewing the result. Register frozen task/card, inputs, seed, evaluation and thresholds before running; save reproducible evidence. This supersedes any earlier blanket ban on *research-only* small-weight training. It does NOT authorize production code, production UNO training/checkpoints, Android builds/APKs/device actions, GitHub Actions, publication, secrets, main edits/merge, deletions, destructive history changes, approval of R5.3/G4/G5, or autonomous adoption of E1. R5.3 S1 itself still freezes runtime Θ; any Θ-changing E1 remains an isolated candidate, not the adopted contract. Source: owner decision on 2026-11-05, captured in [issue #4 comment 6660428370](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/issues/4#issuecomment-6660428370) and continued in owner-provided handoff. **For the LIVE queue use [BENCH.txt](research/uno-lab-001/BENCH.txt) and append-only [UNO_LAB_REPORTS.txt](UNO_LAB_REPORTS.txt).**

# CURRENT UNO AGENT ROUTE — 2026-11-02

Read [docs/AGENT_START_HERE.md](docs/AGENT_START_HERE.md) first, then [docs/CURRENT_TASK.md](docs/CURRENT_TASK.md) and [docs/precode/r5.3/README.md](docs/precode/r5.3/README.md). R5.3 is NOT owner-approved; do not start production code. The original rules below are retained as historical and continuing constraints.

---

# UNO — правила разработки для людей и AI-агентов

Проект: **UNO (Unified Neural Organism)** — новый независимый коммерческий Android AI-агент.

## Фактический статус
На дату создания этого файла готов только частный Git-репозиторий и исходное описание цели. **Новой обученной модели, работающего Android-приложения и проверенного APK UNO пока нет.** Нельзя называть документ или эксперимент готовой функциональностью.

## Цель продукта
- Один полностью локальный нейроноподобный агент с собственными **новыми** весами, состоянием, памятью, пластичными связями и обучением на проверенных последствиях.
- Исходная формула UNO относится к **всей организации агента**: восприятие → вычисления → состояние/связи → решение → разрешённое действие → независимый результат → опыт; она не является только формулой инференса модели.
- Android — **основной коммерческий продукт**, а не временный полигон. Качество UX, безопасность, батарея, производительность, надёжность и лицензии важны наравне с модельной точностью.
- Нет обязательного облачного AI, OpenAI API, OAuth, сетевого fallback, удалённой памяти или требуемого интернет-соединения в рабочем продукте.

## Инженерная дисциплина
1. Начинать с README и актуальных исходников этого репозитория; исторические материалы считать свидетельствами, а не состоянием текущей сборки.
2. Не превращать UNO в форк JarvisLab или переписанный Jarvis. Заимствовать только минимально необходимые, проверенные, лицензируемые отдельные локальные компоненты; происхождение и права каждого заимствования документировать.
3. Не использовать старые веса Jarvis v0/v1/v2 или их правила запретов как новый runtime по умолчанию. Новые веса должны иметь воспроизводимое обучение, датасетный протокол и объективные тесты.
4. Обособленные модули Android API могут существовать технически, но **несколько отдельных reasoning-агентов, BrainPort/Bridge/Orchestrator и независимых параллельных мозгов** не должны заменять одну интеллектуальную организацию.
5. Математические предложения, нейропластичность, структурный рост, регенерация и NCR-EVO — **гипотезы**, пока не подтверждены независимыми экспериментами; сравнивать с табличным и фиксированным baseline, тестировать забывание и расход ресурсов.
6. Нейронная модель **не выдаёт себе полномочия**. Системные Android permissions, согласие владельца, STOP/отмена, подтверждение чувствительных действий и независимый native readback обязательны.
7. Держать отдельно статусы `PLANNED`, `IMPLEMENTED`, `HOST_TESTED`, `ANDROID_BUILT`, `DEVICE_VERIFIED` и `RELEASE_READY`. Ни одна успешная компиляция не означает тест на смартфоне.
8. Первое испытательное устройство: Samsung Galaxy A52 / Android 14, но портируемость системы должна сохраняться.
9. Коммерческий закрытый код: не публиковать секреты, ключи подписи, приватные данные и лицензируемые чужие материалы. Проверять лицензии инструментов, моделей и данных до использования.

## Git и сохранность
- Основной приватный GitHub: `ivankondral1998-dot/UNO-android-AI-Agent`.
- Планируемое приватное зеркало GitFlic: **ещё не подключено**.
- Хранить независимый локальный Git bundle; отдельно резервировать LFS, веса, APK/AAB, release assets и SHA-256.
- Работать в отдельных feature-ветках. **Без прямого разрешения владельца:** не создавать merge в `main`, не делать force-push/reset/rebase с потерей истории, не удалять исходники, не публиковать бинарники, не запускать GitHub Actions/CI.
- Не делать `git push --mirror` и не использовать `--prune` для резервного GitFlic без отдельного разрешения: это способно удалить удалённые ветки.
- При недоступности хостинга работа должна продолжаться из локального архива и второго Git remote.

## Что считается полезным прогрессом
Подтверждённые работоспособные исходники + обучение новых весов + host- и Android-проверки + честная диагностика ограничений + воспроизводимые артефакты. Не подменять код документами и не урезать продукт до искусственно простой демонстрации.
