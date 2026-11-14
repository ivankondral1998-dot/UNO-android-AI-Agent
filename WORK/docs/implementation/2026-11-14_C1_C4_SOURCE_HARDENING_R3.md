# UNO 1.0 — C2/C4 targeted source corrections R3 (2026-11-14)

**STATUS: SOURCE_PATCHED / HOST_UNTESTED / ANDROID_UNBUILT / DEVICE_UNTESTED.** Дополнение к R1/R2 и живой `main/AGENTS.md`; исходные Astra R5.3, UDC v0.3, Terra, research/train001 и product `main` не изменены.

База: `feat/uno-permanent-full-foundation-20261111@ec9764f03dcdca305b575b41514d0aa153d2aab7`. Изолированная рабочая ветка: `fix/uno-consent-freshness-20261114`. Нового APK, подписи, обучения весов или GitHub Actions нет.

## C2: восстановление двух хранилищ без скрытой потери tombstone

1. `UnoSemanticMemory.dropScope`: ранее сериализатор мог сохранить 257-й scope tombstone, хотя собственный decoder отказывает на количестве более `MAX_LINKS=256`. Теперь до шифрования/записи проверяется существующий cap; при превышении сохраняется предыдущий читаемый snapshot. Commit `b7b132d06e0a4d2b9b924003833c6a0b1ea81902`.
2. `UnoSemanticMemoryTest`: кандидатный тест 256 успешных tombstones, отказа 257-го, неизменности файлового содержимого и повторного чтения прежней копии. Commit `59cbfce8e70330e585928a6c5aac244336eda50f`. **Тест не запускался.**
3. `UnoAndroidSemanticMemory`: presence `.new` или legacy `.bak` теперь блокирует чтение/запись index, включая случай, когда старый base snapshot ещё читается. Никакой автоматической починки/удаления. Commit `716aacd60dd35c3f1e2dd01cd918988cfaa469da`.
4. Все local semantic adapters в одном процессе используют общий монитор вместо отдельных @Synchronized locks; каждый вызов заново открывает committed snapshot и не использует stale cached tombstone. Это защита от same-process lost update, **не** гарантия cross-process lock/fsync/anti-rollback. Commit `1495629d8205c840362edd708237d4539890e27d`.
5. При наличии AndroidKeyStore alias, но отсутствии сохранённого ciphertext index теперь отказ `SEMANTIC_SNAPSHOT_MISSING` вместо предположения «index отсутствует». Это предотвращает чтение старого exact после потери потенциального semantic tombstone. Новая проверка выполняется на read-only scope check и на write-open. Ни ключи, ни существующие файлы автоматически не удаляются. Commit `7690d4cfc2f3641df1f830eb00ada5d74c4a2fa2`.

**Открытые риски:** внешний процесс/восстановление старого валидного AES-GCM snapshot, отсутствие защищённой версии revocation, power-cut, сохранение семантического tombstone и exact revoke в двух разных файлах, старые прямые обращения вне gateway. Нельзя считать C2 CLOSED. При .new/.bak и key-without-file требуется отдельная владелец-ориентированная процедура восстановления после фактических испытаний, без принудительной потери данных.

## C4: публикация только реально вычисленных результатов единого F

`UnoFSession` теперь связывает `GoalWork/ObservationWork` с конкретным завершённым `UnoFReference.forward` и копией результата. `publishGoal/publishObservation` отклоняет неполученную из F, подменённую, изменённую, вытесненную другим вычислением или устаревшую версию. При GOAL switch, discard, memory invalidate и STOP ожидаемые результаты сбрасываются. Commit `1e6a0ac5ab95de56303134a788990363352a7f1b`.

`UnoFSessionTest` дополнен отказом fake GOAL, fake observation, прежнего результата после нового вычисления и мутированного результата. Commit `db83051c63a6eda39e1af2d77c0952e3c9d19db9`. **Не запускался.**

**Открытые риски:** GOAL encoder, trusted source owner goal, интеграция в работающую Android session, resource mask/selector, independent outcome, retention. Это по-прежнему one-F host reference, не второй мозг и не обученная модель.

## Оставшиеся обязательства до единого APK

- C1: полноценная trusted Android permission/owner/STOP/dispatch linearization, отдельный native readback и fault recovery; сейчас Android effects deny-all.
- C2: полноценные durability/rollback доказательства exact + semantic + derived state; нельзя выполнять silent reset.
- C3: самостоятельный реестр весов ABI/2, строгий decoder, доверенный model provenance и fixed Θ; checksum-only не разрешает inference.
- C4: проверенная Android-сессия одного F с целями/памятью/планом, без выдуманной модели или ненастоящих исходов.
- Проверить исходники Kotlin host suite/Gradle/lint и затем один APK из точного SHA с предыдущим applicationId/signing key и сохранением данных; физическая приёмка на A52 отдельна.

**Текущий результат:** зафиксированы только исходники и будущие тесты. Не присваивать PASS ни одному тесту, пока он не выполнен, и не объявлять продукт готовым по наличию документов.
