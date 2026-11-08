# UNO 1.0 — ЕДИНАЯ ИНЖЕНЕРНАЯ КАРТА / HANDOFF ДЛЯ GROK И ЛЮБОГО НОВОГО АГЕНТА

## UPDATE 2026-11-08 — SIDE-BY-SIDE APK, INSTALL CONFLICT

Владелец сообщил Android install отказ: конфликт с другим установленным пакетом. **Подпись как причина — гипотеза, на A52 `INSTALL_FAILED_UPDATE_INCOMPATIBLE`/cert пока не собраны.** Старое приложение и данные **НЕ удалять**. Исправление на feature branch: только CI debug получает уникальный суффикс `-PunoIsolatedDebugSuffix=ci${GITHUB_RUN_ID}`; обычные debug/release applicationId неизменны. ADB-подсказка в UI использует фактический `packageName`. Никаких изменений Jarvis/Neural Language/Astra/Grok.

**Реальный новый APK собран:** GitHub Actions [run #42493602248](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42493602248), **SUCCESS**, exact built source SHA `0afa6cb9850faee68abea0e93be98794db41b930`; `aapt dump badging` проверил **`org.unovyra.uno.scaffold.ci42493602248`** (не прежний `org.unovyra.uno.scaffold`). Размер **922678**, SHA-256 **`63b46afedb03641c189e7f9c71ede28b8e16b426878ab924952d16f69bc776c1`**, ZIP/APK checks integrity PASS. Отдельный приватный APK на Google Drive: https://drive.google.com/file/d/1M_Pzo19E9eVDSwFo8OmHYMOrXJWIbjgP/view?usp=drivesdk ; Drive подтвердил точный size и MIME. Подробный [акт исправления установки](implementation/2026-11-08_WP02_APK_INSTALL_CONFLICT_SIDE_BY_SIDE_R1.md).

**Это тестовая side-by-side сборка, не upgrade старого пакета**. Система создаёт новый sandbox, не импортирует существующие данные. Для обновлений в будущем понадобится фиксированный production/debug signer, не очередное изменение package ID. `DEVICE_VERIFIED=FALSE` до установки и реального test на A52, `FOUNDATION_INCOMPLETE` — нет ядра, весов и native readback. GitHub Actions и Google Drive приватная доставка авторизованы на выполнение задачи; публикации релиза нет.

---


## UPDATE 2026-11-08 — ANDROID SDK35 BUILT — RUN 42488780925 (CURRENT)

**ФАКТ `ANDROID_BUILT`** (но `DEVICE_VERIFIED=FALSE`): первое успешно собранное APK с **реальным Android SDK35** для текущего feature-кода UNO, exact built SHA `de7d3e9c3e9634daa6ec20e7741d24546d088569`; private GitHub Actions [run #42488780925](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42488780925) **SUCCESS**. Debug APK `org.unovyra.uno.scaffold`, `0.1.0-skeleton`, min26/target35, **922662 bytes**, SHA256 `2c5285ea277acc11a8925900a66013a0ad4585946e84c13ef8cb09e72365ed37`. GitHub private artifact ID `13620288108` (ZIP SHA `5d0cb1cd1d5d35ef1fba89fb197a84a531d662f3a2e70eeedc7c741b06251424`; expires 11 Nov). Artifact privately downloaded, ZIP/APK checked, SHA rechecked.

**EXECUTED TESTS:** полный `bash android/scripts/run_all_preflight.sh` с реальным standalone kotlinc (НЕ skip): core aggregate `193` checks, SQLite schema `14/14`, Kotlin inspector `11/11`, owner state `31/31`, credential adapter stubs `11/11`, static/diagnostic Python PASS; независимый `gradle :core:unoHostTests` SUCCESS, `gradle :app:assembleDebug` SUCCESS, `gradle :app:lintDebug` SUCCESS **с 7 предупреждениями** (4 локализация, target SDK, data-extraction rules, иконка). `aapt dump permissions`: permission-запросов нет, включая INTERNET/RECORD_AUDIO/CAMERA. Полная [проверяемая ведомость и SHA](implementation/2026-11-08_WP02_ANDROID_SDK35_CI_BUILD_R1.md).

**НОВЫЕ ПОЛНОМОЧИЯ**: владелец 08.11.2026 разрешил **GitHub Actions при объективной необходимости, без повторных согласований**. Новое правило зафиксировано **в единственном действующем корневом `/AGENTS.md`**. Для данного случая локального SDK не было, так что запущен один адресный `uno-feature-android-verify.yml` в feature-ветке, workflow path-filtered; **ни `main`, ни releases, ни секреты, ни Jarvis/Neural Language не изменены**.

**НЕ ОБЪЯВЛЯТЬ ГОТОВНОСТЬ UNO:** APK представляет диагностический каркас, `DenyAllAndroidPort` и `NoWeightsNeuralPort` не заменены; A52-устройство не тестировалось, реальные права/owner identity/native dispatch/readback отсутствуют. `FOUNDATION_INCOMPLETE`. Следующий физический gate — установка именно этого APK на A52, проверка Android device-credential, STOP, SQLite read-only и lifecycle; затем адресная реализация app-private verified effect. Из R5.3/Astra и Grok остаются `A_cap/A_tx/A_fs` условными, Grok MATH-C01/MATH-C05 открыты, Jarvis — изученный источник контрактов, не скопированный OwnerGate.

---


## UPDATE 2026-11-08 — AUDIT R2: OWNER CONSENT BUGFIX (MOST RECENT)

**READ ROOT `/AGENTS.md`, CHECK GITHUB HEAD BEFORE CHANGES.** Самостоятельный аудит обнаружил и воспроизвёл **три ошибки текущего `OwnerConsentState`** (не Android device exploit): (SEC-01) диагностический экран принимал scope verb15 и произвольный SHA; (SEC-02) requestCode `0x4100` повторялся при пересоздании gate, из-за чего старый тестовый RESULT_OK мог быть принят новым pending challenge; (SEC-03) произвольное описание системного подтверждения принималось с семантикой NOOP. Все три исправлены: **строгий единственный `diagnosticNoopScope()` (verb2, fixed digest, empty permissions)**, единый фиксированный `DIAGNOSTIC_DESCRIPTION` из того же класса, process-wide `AtomicInteger` + random start modulo 16 112 request codes (без reuse в одном процессе до исчерпания диапазона). `UnoActivity` использует только централизованные значения. **Старые исходники/математика сохранены; правки только на feature-ветке.**

**Проверено на реально выполненных host тестах:** `31/31` owner state и `11/11` Android platform-stub (**42/42**, 5 отдельных повторных JVM запусков); дополнительно `58/58` prior core reference host, `14/14` настоящая host SQLite SQL, `11/11` inspector stub. **125 сценариев разного уровня, НЕ 125 Android device tests.** Исправлены имена прежних fake-permission тестов: NOOP не требует Android permissions, поэтому они *не* были доказательством реального permission revocation. [Полное версионированное erratum R2 и точные Git blobs](implementation/2026-11-08_WP02_OWNER_CONSENT_SECURITY_ERRATUM_R2.md). Прежний R1 не переписывался.

**Jarvis актуально сверен, только read:** `kolakbro5995-cpu/JarvisLab` `feature/v21-local-offline-runtime-20261101` @ `9c60f81d81d11a0977be1d36d928a3b5d273bbef`, `AndroidOperationAuthority`, `ConfirmationTicketGate`, негативные host-тесты. Сохраняем one-use, STOP, permissions/context/native preflight; не переносим Cloud OwnerGate, special lab bypass, старые веса. Аудит Grok `MATH-C01` и `MATH-C05` остаются открыты; Astra `A_cap/A_tx/A_fs` — CONDITIONAL, не «PASS».

**Границы:** requestCode уникален **только внутри процесса**; после смерти процесса случайная коллизия и OS callback routing ещё не исключены испытаниями на A52. Deprecation `KeyguardManager.createConfirmDeviceCredentialIntent` API29 подтверждена Android reference; возможный `BiometricPrompt` требует отдельной SDK/device проверки. Android SDK/Gradle и Galaxy A52 здесь не проверялись; полный `run_all_preflight.sh` текущей ветки не выполнялся; `DenyAllAndroidPort` и `NoWeightsNeuralPort` не заменены. **`FOUNDATION_INCOMPLETE`.**

---


## UPDATE — OWNER CREDENTIAL NOOP / WP-02 (2026-11-08)

**При первом входе сверить текущий HEAD GitHub и `/AGENTS.md`.** Android-лаборатория получила **реальное обращение к системному экрану проверки учётных данных устройства**, пока только для диагностического `NOOP` (verb=**2** по Astra, **не ABSTAIN=0**). Добавлены `OwnerConsentState.kt` (process-only one-use/TTL/session nonce/STOP/permission/foreground binding) и `AndroidDeviceCredentialPlatform.kt` (Android KeyguardManager, actual OS device-credential intent). В `UnoActivity` — два owner-tapped шага запрос→Android RESULT_OK→одноразовое подтверждение без native-effect. Операции не выполняются, `DenyAllAndroidPort` и `NoWeightsNeuralPort` сохранены. Старый OwnerGate Jarvis, его cloud auth, веса, архитектура не переносились.

**HOST_TESTED:** 24/24 Kotlin process-state + 11/11 Android-platform mock tests = **35/35 PASS**, фактические исходники совпадают с GitHub blob SHA. Тест зарегистрирован в `android/scripts/run_all_preflight.sh`. **Это не тест Android OS UI**: настоящий SDK/Gradle, A52, credential callback/lifecycle, STOP/OS linearization не проверены. Старый `KeyguardManager.createConfirmDeviceCredentialIntent` доступен, но deprecated с API29; заменить/подтвердить на целевом Android отдельным решением. [Полный отчёт, R5.3 и provenance Jarvis](implementation/2026-11-08_WP02_DEVICE_CREDENTIAL_NOOP_R1.md).

**Блокеры:** проверка учётных данных Android-профиля ≠ доказательство индивидуального владельца UNO; одноразовый NOOP ≠ trusted dispatch, не соединён с SQLite outcome/verified readback. `A_cap/A_tx/A_fs` **условны**, `FOUNDATION_INCOMPLETE`. Следующий шаг — проверка сборки/устройства, затем ровно один локальный проверяемый effect contract под owner auth + independent readback. `main`, Jarvis, Neural Language, модель и веса не менять без нового допуска.

---


## UPDATE — SQLITE INSPECTION UI / WP-02 (2026-11-08) — CURRENT

**Ветка, SHA и правила:** перед правкой заново прочитать `/AGENTS.md` и HEAD; прошлые SHA ниже — исторические снимки. В `UnoActivity` добавлены две явные диагностические кнопки: чтение существующей SQLite без её создания и создание пустой SQLite для последующей проверки. Фактический `AndroidOutcomeInspection.kt` открывает `AndroidOutcomeStore.inspectAfterRestart()` на текущем background worker, возвращает только агрегированные счётчики, не выдаёт билеты/не делает native. `NOT_INITIALIZED` отличается от `UNAVAILABLE`; осиротевший WAL без основной БД и любой corrupt/executable/unknown row → **UNAVAILABLE**, не пустая история и не успех. UI записывает только app-private JSON с явными `verified_os_outcomes=false`, `native_actions_enabled=false` или FAIL-CLOSED.

**Код/проверка:** добавлены `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeInspection.kt`, Kotlin host fixtures `android/scripts/inspection_host/*`, запускаемый `android/scripts/test_outcome_inspection_host.sh`, добавлен запуск в `run_all_preflight.sh`; подробности в [WP-02 Android inspection UI R1](implementation/2026-11-08_WP02_ANDROID_INSPECTION_UI_R1.md). **11/11 новых Kotlin inspector host**, **14/14 прежних host SQLite** и **58/58 reference controller/journal JVM** PASS отдельно (разные уровни, не Android integration). Полный preflight на текущем HEAD, Android Gradle, UI/device тесты пока НЕ запускались.

**НЕ ЗАКРЫТО:** Ни один privileged native action не разрешён — `UnoActivity` всё ещё `DenyAllAndroidPort()+DenyAllLedger()`, веса отсутствуют. Конкретный action-authority, owner identification, one-use consent, Android permission revalidation, STOP/OS linearization, independent native readback и device transactional proof остаются `SPECIFIED_UNTESTED`. Jarvis V21 `AndroidOperationAuthority` и `ConfirmationTicketGate` проверены как источники требований (не код для слепого переноса). R5.3/Astra/Grok, N0/FR/TR, Jarvis, Neural Language и старые источники сохранены. `FOUNDATION_INCOMPLETE`.

---


## UPDATE — ANDROID SQLITE BACKEND / WP-02 (2026-11-08)

**Сверяй живой HEAD перед следующей правкой.** Добавлен `android/app/src/main/kotlin/org/unovyra/uno/AndroidOutcomeStore.kt`: настоящий Android `SQLiteOpenHelper` / WAL / `beginTransactionNonExclusive`; одна БД фиксирует `operations.used + source-tagged readback claim + bounded memory_ref/payload` в одном SQL COMMIT. После process restart `inspectAfterRestart()` возвращает **неисполнимую** историю либо явный `Inspection.Unavailable`, но **не выдаёт** старых tickets и никогда не делает retry. Есть SHA-256 validation raw bytes на открытии; schema upgrade fail closed, никаких удалений или автоматической конверсии старых journal-файлов. Никакие модельные/OS действия новый store самостоятельно не выполняет.

**Границы проверки:** `android/scripts/test_sqlite_outcome_schema.py` содержит **14/14 PASS** на настоящей host SQLite из *непосредственно извлечённых Kotlin SQL-констант*, 3 повтора; Kotlin класс компилировался только с Android test stubs (не SDK/API35); предыдущий core reference host JAR повторно **58/58 PASS**. Новый SQL тест включён в `android/scripts/run_all_preflight.sh`, но **полный preflight с текущей веткой ещё не запускался**. Android Gradle APK, A52, crash-power-cut, ОС readback НЕ проверены. [Исходный технический акт](implementation/2026-11-08_WP02_ANDROID_SQLITE_TRANSACTIONAL_STORE_R1.md).

**Главный незакрытый переход:** backend `IMPLEMENTED_UNWIRED`: `UnoActivity` всё ещё использует `DenyAllAndroidPort/DenyAllLedger`, neural worker изолирован, реальной Android owner auth, live permissions, consent, native linearization/readback ещё нет. SQLite `REFERENCE_READBACK_CLAIM` **не** `VERIFIED_COMPLETION`. До будущей доверенной Android интеграции этот класс не производит действия и не доказывает A_cap/A_tx всей UNO, A_fs или antirollback. RAM/energy/thermal — `REQUIRES_DATA`. **FOUNDATION_INCOMPLETE**.

**Обязательно помнить Jarvis и весь прошлый UNO:** по исходникам `kolakbro5995-cpu/JarvisLab` V21 сверены `AndroidOperationAuthority`, `ConfirmationTicketGate`, STOP/revalidation; переносить только доказанные контрактные требования, не cloud OwnerGate, lab bypass, старые веса, Jarvis BrainPort. Astra R5.3, Grok/Work, LAB/FR/TR, N0 и старые reference журналы сохранены. Neural Language — отдельный проект; ядро/веса UNO не тронуты. `main` и Jarvis не менять.

---


## UPDATE 2026-11-08 — WP-02 atomic reference used+receipt / Jarvis review (current)

**HEAD проверять заново**, snapshot этой записи не фиксирует будущие изменения. Текущий `ActionIntentJournal` получил append-only **v2 phase4 `REFERENCE_USED_RECEIPT`**: reference `used=true` и положительная source-tagged readback-запись лежат в **одном** sync-record; после reopen это восстанавливается без retry. Старый v1 `RECEIPT_RECORDED` всё ещё читается, но `used=false` (не исправлять историю задним числом). `TrustController` в reference+intentJournal режиме отвергает `DurableLedger`, отличный от тестового `InMemoryLedger`, чтобы не прятать вторую независимую дисковую транзакцию.

**HOST_TESTED (точные Git blobs):** 12 прежних journal + 23 typed controller integration + 11 receipt recovery + **12 новых atomic reference regressions** = **58/58 JVM PASS**, повторено три раза. Прогон ограничен 7 исходными Kotlin файлами; full Gradle/preflight после коммитов **НЕ** проводился. Все изменённые Git blob SHA и негативные тесты описаны в [WP-02 атомарная reference запись + проверенный Jarvis источник](implementation/2026-11-08_WP02_ATOMIC_REFERENCE_RECEIPT_JARVIS_REVIEW_R1.md).

**Jarvis учтён строго по исходникам:** только чтение `kolakbro5995-cpu/JarvisLab` `feature/v21-local-offline-runtime-20261101`; просмотрены `AndroidOperationAuthority.kt`, `ConfirmationTicketGate.kt`, `ActionEngine.kt`, `AndroidOperationAuthorityHostTest.kt`. Переносить автоматически их OwnerGate, облачную авторизацию, special lab security, старые веса и многомозговую архитектуру запрещено. В будущий Android trust port учесть one-use ticket/epoch/permission/owner/context revision, STOP и native preflight+readback **после отдельного ревью лицензий и совместимости**. Jarvis НЕ модифицирован.

**Блокеры:** одна reference journal запись **не** даёт полного `A_tx/A_fs` (нет `L,D,P-version,M-ref` transaction), нет реальной trust boundary Android / независимого native OS sample / безопасного local persistent memory / A52 device validation / trained weights. `DenyAllAndroidPort` остаётся. **FOUNDATION_INCOMPLETE**. Neural-Language, UNO F и веса не затронуты.

---


## UPDATE 2026-11-08 — readback receipt R1 (latest)

**Всегда сверить свежий SHA ветки.** Reference `TrustController` теперь отклоняет stale TRUE, если `observedAtNanos` предшествует `nativeAdmittedAtNanos`. В `ActionIntentJournal` добавлена новая append-only фаза `RECEIPT_RECORDED`: после положительного reference readback записываются ID билета, digest предложения, источник, nativeGeneration и время наблюдения; после crash такие байты можно восстановить, а ticket никогда не пересылается автоматически. Сбой sync receipt переводит текущий reference ticket в `MAY_HAVE_EXECUTED`, не в успех. Формат старых двухфазных журналов остаётся читаемым.

**HOST_TESTED:** ровно проверенные Git blobs двух core-файлов и нового теста; `11/11` новых recovery/receipt тестов + `23/23` предыдущих controller integration + `12/12` journal = **46/46 PASS**, ещё 3 повторных прогона тоже PASS. Тест добавлен в общий runner, однако **полный preflight текущей ветки и Android assembly не выполнены**. [Подробности, математика, исходники и доказательные границы](implementation/2026-11-08_WP02_READBACK_RECEIPT_REPLAY_R1.md).

**НЕ считать доверенным OS-результатом:** `RECEIPT_RECORDED` — только записанное source-tagged утверждение fake-native. Нет реального Android owner/permission/readback, `A_tx/A_fs` и единых атомарных `used + receipt + memory`; journal и ledger пока разные хранилища. STOP/OS linearization, boot identity, authentication/anti-rollback и device-gate остаются открыты. `FOUNDATION_INCOMPLETE`.

**Neural Language — самостоятельный проект, его код/веса/ABI не менялись и не переносились в UNO.** Действующее руководство этого репозитория — только `/AGENTS.md`; исторические Astra/R5.3 сохраняются и применяются как математические ограничения, не как утверждённый trained model.

---


## UPDATE 2026-11-08 — typed DispatchAttempt / causal outcome (после WP02 causal bridge)

**Проверять текущий HEAD GitHub; не использовать snapshot SHA из старых разделов.** Новый тип `DispatchAttempt` в `Contracts.kt` и метод `TrustController.dispatchOutcome()` **разделили отказ до native**, однократный **вызов native** (с результатом TRUE/FALSE/UNKNOWN без readback) и **неразрешённое состояние после прошлой попытки**. Прежний `dispatch(): NativeEndpoint` сохранён только как deprecated legacy adapter и всё ещё теряет семантику: его `FALSE` не является достоверным отрицательным OS sample. Новые пути `Verify/L/M` должны использовать типизированную причинную семантику; никакого обучения по отказам до native.

**Изменения:** `Contracts.kt`, `Controller.kt`, 10 новых сценариев в `ActionJournalControllerIntegrationTest.kt`. **Проверка:** совпавшие Git blobs пяти реально компилировавшихся Kotlin-файлов; `kotlinc` + JVM **23/23 integration и 12/12 journal PASS (35/35), 5 повторов**, полный Gradle/Android не проверен. [Подробные формулы, источник Astra/R5.3, тесты и блокеры](implementation/2026-11-08_WP02_TYPED_DISPATCH_OUTCOME_R1.md).

**Важное ограничение:** это **reference-only**, `A_cap/A_tx/A_fs` и реальный Android linearization/owner/permissions/native readback не подтверждены. В приложении по-прежнему `DenyAllAndroidPort`. `FOUNDATION_INCOMPLETE`. Ядро F/веса не менялись.

---


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
