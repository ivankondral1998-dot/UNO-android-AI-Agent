# UNO 1.0 — ЕДИНАЯ ИНЖЕНЕРНАЯ КАРТА / HANDOFF ДЛЯ GROK И ЛЮБОГО НОВОГО АГЕНТА

## UPDATE 2026-11-08 — новейший WP-02 causal bridge (после Grok `bfb9acdad6b7bff30c9fae31ff9b3da043b2c665`)

**Действующий HEAD перепроверять непосредственно в GitHub.** После исправлений Grok дополнительно подключён `ActionIntentJournal` к **опциональному reference** `TrustController`, чтобы успешный журнал `PREPARED` предшествовал выдаче билета, а синхронизированный `MAY_HAVE_EXECUTED` предшествовал fake-native dispatch. Если долговечная запись не удалась, вызова native нет. Forged/невыданный `PREPARED` теперь означает pre-dispatch `FALSE`, а не видимость неопределённого OS-эффекта. Старый host-only конструктор без журнала сохранён для совместимости; **реальная Android Activity использует DenyAll Port, интеграции с Android-native по-прежнему нет**.

**Новые испытания:** 13/13 controller+outbox host integration и 12/12 standalone journal host — **25/25 PASS** с побайтово сверенными пятью файлами источников/тестов. Новые integration-тесты зарегистрированы в `AllHostTests.kt`; **полный suite после этих коммитов заново не выполнялся**, Android APK и A52 не проверены. [Математическая трассировка и границы испытаний](implementation/2026-11-08_WP02_CAUSAL_MATH_BRIDGE_R1.md).

**Критическая граница из Astra/R5.3:** `MAY_HAVE_EXECUTED` и полученное `TRUE` от fake port не доказывают независимый результат или causation. `A_cap/A_tx/A_fs`, STOP/OS linearization, атомарное `used+receipt+memory`, owner permissions, boot identity и физическое хранилище ещё не доказаны. Текущий `NativeEndpoint.FALSE` используется также для отказа до native — **до production-интеграции разделить статус допуска и независимый endpoint sample**, чтобы не обучать по отказам как по отрицательным исходам.

**Ядро F, веса и обучение не изменялись**; действующее решение владельца — разрабатывать Android-фундамент без вмешательства в параллельную работу над интеллектуальным ядром. Старые R5.3/Astra/Grok документы и исследования сохранены. `FOUNDATION_INCOMPLETE`.

---


## UPDATE 2026-11-08 — WP-02, текущая инженерная контрольная точка

**Сверяйте живой HEAD**, а не SHA вчерашнего снимка ниже. Изменения после исходной карты: новый `ActionIntentJournal.kt` + `ActionIntentJournalTest.kt`, зарегистрированный в `AllHostTests.kt`; документ `docs/implementation/2026-11-08_WP02_ACTION_INTENT_JOURNAL_HOST_R1.md`. Компонент отдельно HOST_TESTED (12/12), а ограниченный объединённый JVM набор 53/53 PASS, **не полный Gradle/preflight**. Journal фиксирует PREPARED и MAY_HAVE_EXECUTED с append + fd.sync и на восстановлении запрещает автоматический rearm. Он **НЕ подключён** к Android-порту и не предоставляет permissions, consent, native readback, trusted outcomes, Keystore, power-cut proof или работающий нейроинференс. `DenyAllAndroidPort` остаётся обязательным.

**Текущий фронт работ:** вручную собрать и запустить все host/Android checks без GitHub Actions; завершить WP-02 trust boundary и интеграцию journal через настоящий Android owner + permission + STOP + readback; отдельно WP-05 persistent memory. Интеллектуальное ядро/веса **не менять в этой ветке без отдельного решения владельца**. Не объявлять foundation завершённым по этим JVM проверкам.

[Подробный акт WP-02](implementation/2026-11-08_WP02_ACTION_INTENT_JOURNAL_HOST_R1.md).

---

**Снимок:** 2026-11-07, состояние исходников перед созданием этой карты: `f4bc0bd12f8f7b476682a4ff07da85ef419fd6fa`. **ЭТО НЕ ВЕЧНЫЙ HEAD.** Перед работой проверьте свежий SHA рабочей ветки. Этот файл — **маршрут и проверяемый снимок состояния, НЕ отдельный набор действующих правил**. Единственный нормативный источник полномочий — [корневой AGENTS.md](../AGENTS.md) (V3 или более позднее явное решение владельца).

## 0. Если вы только что вошли в проект — прочитайте это прежде, чем писать код

**Репозиторий:** `ivankondral1998-dot/UNO-android-AI-Agent` (**приватный**). **Актуальная ветка интеграции сегодняшних изменений:** `feat/uno-foundation-hardening-20261107`. Ветка-источник WP-01: `feat/uno-production-foundation-20261106` на `ebdfd3f8263592a4906a9829b3b93cadd2256a9c`. `main` при проверке указывала на `27402e7ca2162e5abb52e24c8efc90ee016080cd`; **она НЕ содержит сегодняшних hardening-коммитов**.

При подключении GitHub сначала **явно выберите** `feat/uno-foundation-hardening-20261107`; выдача `main` по умолчанию приведёт к ложному «сегодняшних изменений нет». Убедитесь, что сервис/агент имеет доступ к приватному репозиторию; одна лишь ссылка не выдаёт GitHub permissions.

Начните с `AGENTS.md` в выбранной ветке. Там действующие решения владельца, полномочия, границы и критерии. Затем прочитайте **этот** файл и фактические исходники. Старые [docs/AGENT_START_HERE.md](AGENT_START_HERE.md), [docs/CURRENT_TASK.md](CURRENT_TASK.md), [docs/STATUS.md](STATUS.md) содержат **архивный G4-срез от 02.11.2026** с историческим запретом production-кода; он **заменён** более новым явным решением владельца. Не трактовать исторические заголовки как актуальные.

Для локальной рабочей копии: `git fetch origin feat/uno-foundation-hardening-20261107`, `git switch feat/uno-foundation-hardening-20261107`, `git rev-parse HEAD`, `git status --short`. При работе через GitHub API сначала получите SHA ветки и текущие blob SHA файлов. **Не** трогайте `main`, чужие ветки, историю или оригинальные архивы.

## 1. Каким продуктом занимаемся — решение владельца 07.11.2026

**UNO 1.0:** законченный коммерческий **полностью локальный Android ИИ-агент** с **одной интеллектуальной организацией и общим состоянием**, диалогом/восприятием, локальной точной и семантической памятью, планированием, предложением действий, независимым Android authority, STOP, подтверждениями и отдельным native readback. Первое испытательное устройство — **Samsung Galaxy A52 / Android 14**; архитектура должна оставаться переносимой.

Самообучение весов, FR/TR, plasticity, NCR-EVO, «профессор/ученик», саморастущие связи **НЕ входят в runtime UNO 1.0**: исследования сохранены, но отложены. **Модель, веса, размер, формат, квантование, runtime и лицензия НЕ утверждены**. Production-код на изолированной feature-ветке разрешён. **Нет разрешения** обучать новые production-веса, запускать GitHub Actions, делать merge в `main`, удалять исходники/историю, делать force-push/reset/rebase, публиковать/подписывать APK и выпускать релиз без отдельного решения.

**Не подменять полный продукт:** простой Android UI + `NoWeightsNeuralPort` = диагностический каркас, не настоящий UNO. Не превращать систему в несколько независимых когнитивных моделей или переименованный Jarvis.

## 2. Реальный код — где находится и что означает

| Путь | Состояние на указанном source SHA | Что НЕ доказано |
| --- | --- | --- |
| [android/core/src/main/kotlin/org/unovyra/uno/core/](../android/core/src/main/kotlin/org/unovyra/uno/core/) | `Contracts.kt`, `Controller.kt`, `Memory.kt`, `Scheduler.kt`, `ComputeBudgetGate.kt`, `LabProtocol.kt`, `ProbeMath.kt`, `Measurement.kt`, `ThemePersonalization.kt`. Kotlin reference/host-проверки и отдельные исправления. | Production Android authority, persistent память, нейронный F, проверенная модель. |
| [android/app/src/main/kotlin/org/unovyra/uno/](../android/app/src/main/kotlin/org/unovyra/uno/) | `UnoActivity.kt`, `DeviceLab.kt`, `DeviceProbe.kt`, `LabSystemMetrics.kt`, `SensorLab.kt`; читающая диагностика, ограниченные ручные лабораторные сценарии и UI. | Полноценные разрешённые Android-действия, ASR/TTS, end-to-end интеллект. |
| `android/app/src/main/kotlin/org/unovyra/uno/NeuralWorkerService.kt` | Изолированный **placeholder** без Binder и inference. | Работающая нейросеть и веса. |
| `android/app/src/main/AndroidManifest.xml` | Ноль запрошенных permissions, `allowBackup=false`, `fullBackupContent=false`, `usesCleartextTraffic=false`; neural worker изолирован. | Полная офлайн-безопасность будущих SAF/провайдеров, лицензии, ОС-поведение на A52. |
| `android/core/src/test/kotlin/org/unovyra/uno/core/AllHostTests.kt` | Общий launcher Kotlin host-тестов; уже включает `FoundationHardeningTest` и `ComputeBudgetGateTest`. | **Полный совместный прогон на HEAD после всех сегодняшних изменений ещё не выполнен.** |
| [android/scripts/](../android/scripts/) | `run_all_preflight.sh`, `host_verify.sh`, `static_contract_check.py`, `test_lab_tools.py`, `adb_collect.py` и инструментальные тесты. | Android Gradle build, устройство и реальные privileged effects. |
| [organism/](../organism/) | Исторические исходники отдельной исследовательской линии; проверить модуль и интеграцию до использования. | Не считать работающим Android UNO по наличию этого каталога. |
| [docs/precode/r5.3/source-package/](precode/r5.3/source-package/) | Архивные математические источники и R5.3 candidate NORMATIVE/01–06, источники Astra/R5.2 и provenance. | Утверждение R5.3 владельцем, работающая модель или реальная device-проверка. |

**Текущая Android-подключённая политика:** `TrustController(DenyAllAndroidPort(), DenyAllLedger())` и `NoWeightsNeuralPort()`. Значит опасные действия **не разрешены**, нейроинференс отсутствует. Код интерфейса не равен реальной реализации.

## 3. Чьё происхождение и где математика

- **Грок:** бумажная архитектура и корректировки минимального организма от 03.11, см. [атрибуцию и математический аудит](audits/2026-11-07/GROK_WORK_B2_PROVENANCE_AND_MATH_AUDIT_R1.md). Не утверждайте, что он лично писал все Kotlin/Android-файлы, если нет первичного автора/коммита.
- **ChatGPT Work:** сохранённый `UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip`, внутри `06_NON_NORMATIVE_OLD_SCAFFOLD/`: runnable Python B2 reference + Kotlin/Android-основа. В [документе происхождения WP-01](implementation/2026-11-07_WP01_SCAFFOLD_REUSE.md) зафиксировано 67 побайтово сверенных файлов и SHA архива. **Не путать исторический Work package с текущим product runtime**.
- **ChatGPT, изменения 07.11:** Android диагностическая инфраструктура, host-тесты и безопасность foundation, отдельный branch `feat/uno-foundation-hardening-20261107`; см. [аудит FND-01..10](implementation/2026-11-07_FOUNDATION_HARDENING_AUDIT_V1.md) и [новый вычислительный admission-gate](implementation/2026-11-07_COMPUTE_BUDGET_CONTRACT_R1.md).
- **Существенные математические границы:** fixed-mask contraction `CONDITIONAL`, adaptive-mask global contraction `FAIL`; semantic summary `!=` exact recall. Числа параметров/MAC = арифметика, не качество обученной модели и не расход энергии. [Скрипт проверяемой геометрии](audits/2026-11-07/verify_b2_geometry_v1.py).
- **Воспроизведённый дефект старого Python B2 (`MATH-C01`):** `ResourceBudget.charge()` учитывает только MAC: при нулевых лимитах bytes/tokens/ns reference engine всё равно исполнял TEXT tick. Kotlin `ComputeBudgetGate` — **новый неинтегрированный host-tested примитив**, **не патч исторического Python**, не runtime UNO, не физический resource monitor.

**Для Grok:** сравнивайте свои исходные формулы и допущения с реальными Kotlin/Android API **адресно**. Не подменяйте одно другим на основании совпадающих терминов; фиксируйте контрпримеры. При необходимости запросите оригинальный Grok R3: его отдельный исходный blob в текущей проверке не удостоверен.

## 4. Матрица готовности — snapshot, не переносить PASS между HEAD

| Часть | Что реально есть | Доказательство / статус |
| --- | --- | --- |
| WP-01 Android shell и read-only lab | Исходники + старый debug APK со старого коммита, ранее собранный единожды в разрешённом GitHub Actions run `42391092683`; APK SHA-256 `fb49afa67cbb4cc3591d72728da5ae8b649e5560e6d3c754b65ad58c610a728f`. | Старый APK — `ANDROID_BUILT` **только для своего SHA**. APK после hardening и новой математики **не собран**. Samsung A52 **не испытан**. |
| FND-01..10: tickets/STOP/memory/static policy/ADB | Исправлены конкретные ошибки в feature-ветке; fake/native JVM checks | Отдельно **24 Kotlin PASS** (10 базовых + 14 adversarial), **8 Python static fixture PASS + 4 ADB fixture PASS**. Не равняется full repo/Android integration PASS. |
| ComputeBudgetGate | Добавлен в Kotlin core и host launcher, MAC/tokens/peak scratch/deadline/concurrency/one-way STOP | **17/17 host PASS** в независимом прогоне, 10 повторов; full suite updated HEAD **ещё не выполнялся**. Не подключён к F. |
| WP-02 Android authority / actions | Reference controller + deny-all Android Port | **НЕ ГОТОВО:** owner identification, актуальные permissions, подтверждение, atomic STOP/dispatch boundary, durable outbox `PREPARED/UNKNOWN`, независимый Android readback. Важная гонка: `@Synchronized` может ждать выполняющийся native call; STOP не отменяет уже отправленный эффект. |
| WP-03/04 нейронный интеллект | `NoWeightsNeuralPort`, placeholder isolated service; бумажные B2/compact вычисления | **NOT_IMPLEMENTED:** trained/licensed model, frozen weights, measured quality, native inference, единый F, маски с реальным skip. Выбор модели — OWNER_DECISION; training отдельно не разрешён. |
| WP-05 память | `ExactMemory` in-memory, defensive copy и `NOT_FOUND`, запись `VERIFIED_COMPLETION` запрещена generic-пути | **NOT_IMPLEMENTED:** encrypted persistence, WAL, recovery, verified native writer, забывание, миграции и timestamp/boot identity. |
| Голос, сенсоры, память/планирование/цикл | Часть read-only датчиков для лаборатории, UI темы | **NOT_IMPLEMENTED как полный агент:** speech offline, планировщик, фактические действия и реальный end-to-end цикл. |
| Коммерческий релиз | Продуктовая цель утверждена | **NOT RELEASE_READY:** нет модельного и product-gate, device-результата, лицензий, подписи и разрешения на публикацию. |

**Не перепутать:** `HOST_TESTED` отдельной функции ≠ `ANDROID_BUILT` нового HEAD ≠ `DEVICE_VERIFIED`. Полный `android/scripts/run_all_preflight.sh` на текущей ветке и Android Gradle build/lint — **не проверены**. Старый CI run не запускать повторно без разрешения. Отдельные эксперименты на A52 по N0/LAB не доказывают работоспособность нового UNO 1.0.

## 5. Следующее практическое задание для нового агента (особенно Grok)

**Цель ближайшего этапа:** довести foundation до **целостного, проверяемого каркаса**, сохранив цель полного UNO 1.0. «Законченный каркас» НЕ означает ни обученную модель, ни готовый коммерческий агент.

1. **Первым действием:** проверьте текущие SHA и реальный diff к `feat/uno-production-foundation-20261106`; просмотрите `AGENTS.md` и этот handoff, исходники и их тесты. Ничего не удалять, не переписывать старые исследования.
2. **Установите чистый baseline обновлённой ветки:** локально `cd android && bash scripts/run_all_preflight.sh`; затем при **ручной** доступной SDK35/JDK17/Gradle-среде `gradle :core:unoHostTests :app:assembleDebug :app:lintDebug`. Сохраните stdout/stderr, APK SHA, exact HEAD. При ошибке **исправить причину и перепроверить**, не переносить старые PASS. Никаких Actions.
3. **Закройте критические инварианты WP-02:** независимый Android trust boundary; реальная авторизация/permissions/подтверждения; STOP/admission dispatch; идемпотентность и `UNKNOWN/MAY_HAVE_EXECUTED` без слепого повторения; durable transaction/outbox и независимый readback. До доказательства допуска — сохранять deny-all. STOP не отменяет уже выполненное действие ОС.
4. **Согласуйте границы компонентов:** одна организация, типизированные interfaces данных/состояния/решений, точная vs семантическая память, causal/boot identity, error recovery; убрать конфликт семантики `COMPLETE(empty)` в Python B2 vs `NOT_FOUND` в Kotlin **только в новой версии**, не править историю задним числом.
5. **Не терять математику:** любые новые F/маски/selector/ресурсный адмит проверять по исходным формам и контрпримерам; маски обязаны реально **пропускать** дорогую операцию. `ComputeBudgetGate` должен стоять перед encoder/selector/F-kernels лишь при реальной интеграции, с корректной оценкой ресурсов и STOP checkpoints. Пока нет модели — никаких заявлений об энергоэффективности и качестве.
6. **WP-05:** спроектировать и испытать локальное долговечное, защищённое хранение и восстановление сбоев без выдуманной proven-completion; нейросеть не может записать себе доказательство выполнения OS-действия.
7. **A52 gate:** установить **собранный из точного SHA собственный** APK на Samsung A52 / Android 14, записать raw логи, battery/PSS/CPU/thermal, lifecycle/STOP и проверить отсутствие сети, когда появятся соответствующие зависимости. До этого `DEVICE_VERIFIED=FALSE`.

**Приёмка завершённости именно каркаса:** единая трасса `event → shared state → typed proposal → explicit trust decision → outcome/status → memory` с тестируемыми заглушками для ещё не реализованных органов, недопуск эффектов по умолчанию, безопасный STOP и recovery, воспроизводимые host/Android проверки с точными SHA, прозрачный список намеренно **НЕ реализованных** пользовательских функций. Это *архитектурная приёмка*, не доказательство интеллектуальности. Нельзя ставить `FOUNDATION_COMPLETE` до независимого ревью и фактических тестов этих требований.

**Решения владельца, которые не выбирать молча:** конкретная модель/веса/runtime/лицензия, масштаб возможных реальных Android действий и разрешения, обучение весов, релиз/публикация. Дополнительные уточнения — через варианты с последствиями, не самовольным расширением полномочий.

## 6. Дорожная карта и известная ошибка навигации

Используйте [дорожную карту](roadmap/README.md), [мастер-план](roadmap/UNO_1_0_MASTER_PLAN.md) и [структурированный JSON](roadmap/UNO_1_0_PLAN.json); это **план, не доказательство реализации**.

**Проверенный конфликт количеств на 07.11:** мастер-план Markdown содержит **54 task headings / 11 направлений**, JSON содержит **58 tasks / 12 stages**. Все 54 Markdown IDs есть в JSON; четыре дополнительных JSON-задачи — `UI-01-T01..T04` (темы, UI и доступность). Не затирать эти четыре задачи и не представлять источники как идентичные. Рекомендуется согласовать будущий версионированный план с явным diff, **не переписывая** историческую постановку.

## 7. Как завершать следующую сессию

Оставляйте в этом **стабильном** пути `docs/ENGINEERING_HANDOFF.md` обновлённый снимок с датой и первичными доказательствами. **Не писать здесь второй AGENTS.md** и не перепечатывать действующие правила. Для каждого завершённого блока фиксируйте: файлы/коммиты, отдельные `IMPLEMENTED / HOST_TESTED / ANDROID_BUILT / DEVICE_VERIFIED`, воспроизводимые команды, непрошедшие тесты, исходные SHA/логи, что ещё не решено и кто вправе разрешить следующий шаг. Старые отчёты и доказательства сохраняйте.

**Проверка цепочки перед отправкой результата владельцу:** ссылка открывает **именно текущую feature-ветку**, исходные файлы физически существуют, лог соотнесён с SHA, Android build не приписан новому HEAD, архивные G4-правила не перепутаны с действующими. `main` и GitHub Actions не трогать без явного разрешения.

## 8. Снимок 2026-11-07 — Grok, foundation hardening

Ветка: `feat/uno-foundation-hardening-20261107`. База до правок: `7ed1786fec5d829f8ddd2653013a047a7c06c854`.

Исправлено в коде, не в отчёте:
- STOP и отказ до вызова native возвращают FALSE и CANCELLED/DENIED. UNKNOWN только если вызов мог уйти в native.
- Повтор того же билета после UNKNOWN не вызывает native второй раз.
- `recoverAfterProcessDeath` не переотправляет нерешённое.
- Семантическая запись не читается как точный факт. Пустой exact — NOT_FOUND.
- Неактивная маска не запускает тело. Проверено тестом.

Проверки: `cd android && bash scripts/run_all_preflight.sh` → `UNO_LAB_PREFLIGHT_SUCCESS (HOST ONLY; NOT ANDROID_BUILT OR DEVICE_VERIFIED)`. Android SDK в этой среде нет. Сборка APK не выполнялась. На A52 не ставилось.

Статус: **FOUNDATION_INCOMPLETE**. Нет доверенного Android-порта, нет постоянного журнала на устройстве, нет модели и весов, нет native readback, нет проверки на телефоне. Каркас не выдавать за UNO 1.0.
