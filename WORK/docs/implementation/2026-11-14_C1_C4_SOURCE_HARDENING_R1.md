# UNO 1.0 — C1–C4 source hardening R1, 2026-11-14

**Status: SOURCE_PATCHED / STATIC_REVIEWED / HOST_UNTESTED / ANDROID_UNBUILT / DEVICE_UNTESTED.**
Не APK, не выпуск, не установленный на A52 код. Никаких утверждений, что C1–C4 окончательно закрыты.

## Основание

- `main/AGENTS.md` V4, main `1df9ee7cc592f606939c8f004e1b11edd916b56c`.
- Исходная Android-ветка `feat/uno-permanent-full-foundation-20261111` @ `ec9764f03dcdca305b575b41514d0aa153d2aab7`.
- Новый изолированный ремонт: `fix/uno-consent-freshness-20261114`, без изменения Android app package `org.unovyra.uno`.
- Математика: Astra `ASTRA_01` S1/S4–S7, `ASTRA_02` Θ/ABI, `ASTRA_04` exact-vs-summary/forgetting, `ASTRA_05` trust/STOP, `ASTRA_07` ABI/2; нормативный пакет R5.3, Grok/GPT `UNO_UNIFIED_CYCLE_AND_DATA_CONTRACT_V0_3_CANDIDATE_20261112.md` и независимая Terra review. Это источники-кандидаты, не равнозначны утверждённой модели.

## C1: fresh consent & trusted time

`Controller.kt`: билет ограничен `min(taskDeadline,consentExpiry)`; новые sampling points при подготовке, после durable journal arm, перед и после native readback. Регрессия часов/исключение ⇒ отказ. Android `UnoActivity.kt` передаёт `SystemClock.elapsedRealtimeNanos()` существующему deny-all reference контроллеру. `ConsentFreshnessTest` (8 сценариев) в общем launcher.

**Осталось:** Android OS-linearization/STOP racing, ревокация owner/permissions в момент OS admission, независимый native readback, durable transaction; host-fallback clock с внешним `now` не разрешён для привилегированных портов. Реальный Android native port намеренно отсутствует.

## C2: grouped exact+semantic revocation mitigation

`UnoSemanticMemory.kt`: безопасное чтение собственного сохранённого tombstone scope.
`UnoMemoryPorts.kt`: сериализованный fail-closed барьер для `linkSummary`, `recallExact`, `recallSummary`, `revoke`; tombstone семантической памяти сохраняется прежде exact revoke. Если вторая запись обрывается, reads через **этот общий gateway** остаются DENIED и при переоткрытии корректной семантической копии. `UnoSemanticMemoryTest.kt` добавляет fault injection между двумя persist и на первой записи.

**Осталось:** прямой `UnoManualFacts` / `UnoFactsActivity` путь обходит gateway, Android single-writer/lock, crash до первого успешного tombstone, rollback старых валидных GCM snapshots, reset производного session state, физическое стирание, реальная транзакция двух persistent файлов. **Нельзя объявлять C2 CLOSED** или автоматически чистить пользовательские файлы. Ручное удаление остаётся по подтверждению владельца, код выполнения удаления не менялся.

## C3: disallow self-hashed arbitrary model admission

`UnoWeightGate.kt`: длина, диапазоны и SHA из caller-supplied manifest теперь дают `PAYLOAD_CHECKSUM_ONLY`, но **не** `ADMITTED_UNVERIFIED_QUALITY`; `WeightSlot.admitted() = false` до появления независимо проверяемого ABI-loader. `WeightCheckedNeural` по-прежнему fail-closed. `WeightGateSafetyTest` (6 сценариев) добавлен в host runner.

**Осталось:** утверждённый реестр tensor ids/shapes/dtype/strides/offsets, frozen zero rows, norm certificates, canonical manifest hash, trusted provenance/export and Android ABI decode; нет готового обученного Θ или разрешённого модельного файла. Честная непригодность внешних весов предпочтительнее ложного `ADMITTED`.

## C4: one F/session candidate and atomic goal publication

Новый **reference-only** `UnoFSession.kt`, использующий *существующий* `UnoFReference` и одну Θ: сохраняет общее `s,g`; GOAL вычисляется тем же F с временными `s=0,g=0,I=∅`, рабочее `s` не перезаписывается. `goalVersion/revision/sessionEpoch` проверяются при атомарном publish; новый goal отменяет устаревший observation; STOP/invalidate reject stale writes. `UnoFSessionTest` (8 сценариев) в host runner.

**Осталось:** подключение к действующему `UnoFoundationReferenceCycle` и Android UI, доверенный source/selection owner-goal, реальный goal encoder, versioned session lifecycle, resource/S6 admission, memory-scope revocation signal, planning/S7; ещё не evidence о полноценной непрерывной сессии UNO.

## Исполнение и приёмка

Имеются изменения исходников и кандидатные тесты без выполнения. **Не создавались APK, подписанный релиз, новые production weights, GitHub Actions, merge, удаление/миграция пользовательских данных.**
- Выполнена программная сверка исходного branch/HEAD и чтение первоисточников; exact SHA после записи должен проверяться отдельным запросом.
- **Не выполнены** Kotlin compilation и host tests на новом SHA, Android Gradle assemble/lint, A52. Каждый тест пока `SPECIFIED_UNTESTED`, а не PASS.
- Нельзя ждать до выпуска APK, чтобы впервые компилировать и прогонять host safety tests: перед release-gate они обязательны. Это не требует промежуточных APK.
- Следующий кодовый этап: согласованный end-to-end trust gateway и приложение memory revoke/goal state wiring, после чего один аккуратный APK для полной устройственной проверки. Доступ к подписи не означает разрешение делать новый APK.

## Важный запрет на смену проекта

Не создавать второй Android app, новый независимый нейронный мозг, LLM-as-permissions, новый production architecture/ABI без данных и owner decision. Ни один из source patches не переписывает математические оригиналы, отключает deny-all OS authority или меняет исследовательский trainer `UNO-TRAIN-001`.
