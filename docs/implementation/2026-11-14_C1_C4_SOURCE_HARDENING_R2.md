# UNO 1.0 — C1–C4 source hardening R2, Android revocation wiring (2026-11-14)

**SOURCE_PATCHED / HOST_TESTS_NOT_RUN / ANDROID_NOT_BUILT / DEVICE_UNTESTED / RELEASE_NOT_READY.**

Это дополнение к R1, не замена исходным Astra R5.3 / UDC v0.3 / Terra. Основа: `feat/uno-permanent-full-foundation-20261111@ec9764f03dcdca305b575b41514d0aa153d2aab7`. Новый код в `fix/uno-consent-freshness-20261114`. Канал приложения `org.unovyra.uno` не изменён.

## C2: реальные пути приложения

До R2 `UnoMemoryPorts` защищал лишь обращения через общий core gateway. Теперь в существующем Android-приложении добавлен ограниченный recovery/denial для двух путей:
1. `UnoAndroidSemanticMemory.kt` реализует `isScopeRevoked` (read-only, без создания нового ключа) и `dropScopeIfPresent` (не создаёт новый пустой vault). Нечитаемый или частичный ciphertext ⇒ исключение, не `false`.
2. `UnoFactsActivity.kt` при ручном чтении/записи проверяет сохранённый semantic tombstone. При semantic-revoke без exact-revoke обычные операции блокируются; повторно продолжить отзыв можно только после нового явного подтверждения кнопки «Забыть все ручные факты». После подтверждения сначала фиксируется semantic tombstone существующего index, потом выполняется exact revoke и запись нового scope locator. Старые локальные файлы намеренно не удаляются.
3. `UnoActivity.kt` для scope `device-observation` тоже проводит semantic tombstone перед exact revoke после существующего отдельного подтверждения владельца. Исходная точная readback-диагностика и новая запись запрещаются при сохранённом semantic tombstone. Если семантического индекса нет, не создаётся новый ключ/файл; exact-revoke идёт как прежде.

**Предел:** это упорядоченное fail-closed восстановление поверх существующих stores, НЕ общая атомарная транзакция двух файлов, НЕ anti-rollback, НЕ secure erasure, НЕ гарантия безопасности любых legacy вызовов напрямую к `UnoExactMemoryPort`. Восстановление после power cut, Keystore, reboot, конкурентных Activity и rollback требует A52 испытаний и отдельного дизайн-решения. `UnoFSession.invalidateDerivedState()` реализован, но автоматическая привязка к Android revoke пока отсутствует, так как реальный обученный F не подключён.

## Остальные направления

C1: `Controller` TTL и monotonic rechecks; реальная привилегированная Android-граница не реализована, `DenyAllAndroidPort` сохранён. `ConsentFreshnessTest` написан, не запускался.

C3: caller-supplied SHA теперь только `PAYLOAD_CHECKSUM_ONLY`; приём пользовательских весов выключен до полноценной самостоятельной проверяемой ABI/2 и принятого checkpoint. `WeightGateSafetyTest` написан, не запускался.

C4: `UnoFSession` является host-only атомарной сессией поверх того же `UnoFReference`, с version/revision cookie и GOAL-encoding под пустым `I`. `UnoFSessionTest` написан, не запускался. Android/runtime интеграция и семантически полный F ещё отсутствуют.

## Приёмка: ещё НЕ выполнена

Выполнение новых тестов и Gradle сборки специально отложено, чтобы завершить согласованные исходные исправления в одной ветке и **не плодить APK**. До утверждения любого изменения нужны как минимум локальная Kotlin compilation, host suite, статическая policy проверка, затем ровно одна локальная Android сборка/lint и установка на A52 по owner-gate. Ни один historical PASS не переносить на эти изменения.

**Нет** новой APK, подписи, публикации, GitHub Actions, слияния в main, стирания пользовательских данных, обучения весов. Старые ветки, исходные математические документы и действующие подписи оставлены без изменений.
