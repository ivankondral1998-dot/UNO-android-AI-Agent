# WORK status / контрольная точка 2026-11-14

**Текущая Git-ветка:** `integration/uno-work-research-20261114` (коммит HEAD нужно читать в Git при каждом новом действии).
**Код WORK/android:** точное Git tree `5a56b22e11252ddf54ee83b24515c99fe9a92bba` из `fix/uno-consent-freshness-20261114@d439a19320e74a3a2760fbe48a53d801812aeaff`.
**Происхождение train001:** `research/uno-train-001-20261113@44fdc357b1b6ddec5ed97188c7fd2dc3d03b7e2d`.
**Math/R5.3:** `docs/uno-r53-agent-handoff-20261102@7e94b717d73312f1bf3a926ea5f89586c9d23d7b`.
**Terra:** `audit/uno-terra-math-training-20261112@0af492ee7a8d15b371bf0de1c21d73ca1fd8b050`.
**UDC v0.3:** `design/uno-unified-cycle-data-20261112@3b06b024199d9bfcf1362a6b48156dfa0c74c9dc`.
**Основные правила:** `main@1df9ee7cc592f606939c8f004e1b11edd916b56c`, blob `AGENTS.md@1b53fc85543c285867defd08a0110d3e59e9dbe8`.

## Не выдавать за завершённое

- S4/S5 Double oracle: исходный код есть. Один F с полной устойчивой Android-сессией — **НЕ ДОКАЗАН**; `UnoFSession` остаётся reference only.
- S6 adaptive selector/halt с исчерпывающим бюджетом, независимая память и GOAL/PROPOSAL/S7 по R5.3 — **частично/не интегрировано**.
- C1 C2 C4 — локальные кодовые исправления, **проверки всей native/Android trust boundary нет**; C3 — placeholder и контроль checksum, не loader.
- `UnoActivity` использует `NoWeightsNeuralPort` и `DenyAllAndroidPort`. GGUF chat — диагностический отдельный путь.
- Память, планирование, действия, readback, crash/STOP, Android trust/OwnerGate нуждаются в сквозной реализации и испытании.
- **Компилятор Kotlin, Gradle, устройство A52, интегрированный SDK и этот смешанный checkout пока не проверены.**
- **Полезное обучение весов, законный корпус, held-out качество, ресурсы/энергия на A52 не подтверждены.** Веса не трогать до готовности каркаса и отдельного допуска.

## Правильная следующая техническая работа

Сначала выполним хостовую регрессию `WORK/android/scripts/host_verify.sh` с архивом stdout/exit code и сопоставим WORK со всеми применимыми Terra C1–C4. Затем докажем единый жизненный цикл F/GOAL/памяти на синтетическом фиксированном операторе и безопасность STOP/consent/recovery; только после этого интеграция Android и отдельные данные/обучение. Не открывать альтернативные «мозги». Не смешивать утверждения из прошлых веток с текущим выполненным тестом.

**Не удалены:** main, другие ветки, Git история, исходные математические документы и веса.

## Контрольная точка возобновления — 2026-11-15 (без изменения кода)

- **Рабочий источник:** `integration/uno-work-research-20261114@943e2492ae68b8d1d0e05b94c3b6b5ceacb9709c`; при каждом новом действии перечитывать живой HEAD. Исходный интеграционный организационный снимок `1f51d3d612d2ca850375b65e4b9c23b4f1d28d38` сохранён в Git history. Текущий `WORK/android` по точному Git tree `5a56b22e11252ddf54ee83b24515c99fe9a92bba` совпадает с `fix/uno-consent-freshness-20261114@d439a19320e74a3a2760fbe48a53d801812aeaff`. Не возвращаться к старому Android только ради старого SHA.
- **Приоритет первоисточников:** действующие полномочия только `main/AGENTS.md`; математическая основа `RESEARCH/source-r53/00_START_HERE.md` → `NORMATIVE/01–06` → полные `SOURCES/ASTRA_CURRENT` и адресные `R52`; исторический бумажный кандидат Grok — `RESEARCH/grok/`; последующие адресные поправки/границы Terra — `RESEARCH/terra/`; причинный цикл и тест-карточки — `RESEARCH/udc/`. Кандидаты не утверждены автоматически; противоречия фиксировать адресно, не менять молча формулы.
- **Сверка с реальным кодом, без утверждения полного соответствия:** `UnoFReference.kt` реализует ограниченный численный S4/S5 с пропуском masked kernels. `UnoFReferencePort.recalled()` предварительно отбирает semantic hits по исходным признакам, до S4-запроса `q` из общего F, и не является полноценным stateful S4 memory path. S6 policy sampling/halt не интегрированы. `UnoFSession.kt` даёт reference-only GOAL/stale-work механизм, но не Android full-cycle. C1/C2 частично укреплены, C3 checksum-only fail-closed, C4 host reference; `UnoActivity` по-прежнему `NoWeightsNeuralPort` + `DenyAllAndroidPort`.
- **Что действительно выполняли другие проверки:** `UNO-WL-399/400` заявляют ограниченные JVM slices (STOP, cipher, C4 с test-double, C3 checksum). Их evidence вне репозитория; не считать этим выполненными полный `host_verify.sh`, действительный численный F-integration, Android build или A52. Исследовательский TRAIN-001 из `RESEARCH/` не является production training или подключёнными весами.
- **Точное возобновление:** (1) получить полный checkout именно текущей интеграционной ветки; выполнить существующий `bash WORK/android/scripts/host_verify.sh` с stdout/stderr, exit code, JDK/Kotlin versions и SHA; (2) сопоставить по формулам S4–S7/Terra C1–C4 существующие реализации и тесты, отдельно зарегистрировать контрпример `recalled()` и отсутствие интегрированного S6; (3) лишь после воспроизводимого FAIL и анализа первоисточника выполнять минимальную адресную правку с независимым oracle; (4) Android и A52 только в разрешённом испытательном контуре. Дефекты в `RESEARCH/*-negative.sh` ниже не блокируют основной `WORK/android` host suite.
- **Известный долг после обратимого отката:** `RESEARCH/train001/negative.sh` содержит путь `research/train001`, а `RESEARCH/f-gradients/memory-negative.sh` — `research/f-gradients` при cwd `RESEARCH/`; сейчас пути неверны. Это только разбор исходника, не выполненные mutation tests. Не изменять их без отдельной конкретной задачи и проверки.
- **Ограничения:** никакого одобрения G4/G5, production training, выпуска, merge в main, Actions, удаления файлов, изменения модели или прогонов A52 этим checkpoint не совершено. `SPECIFIED_UNTESTED` и `REQUIRES_DATA` остаются открытыми.
