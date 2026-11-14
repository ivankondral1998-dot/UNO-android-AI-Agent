# UNO Android C2 — fail-closed recovery of ambiguous encrypted snapshots (R4)

Статус: **SOURCE_PATCHED / HOST_UNTESTED / ANDROID_UNBUILT / DEVICE_UNTESTED**. Документ дополняет R1–R3, не изменяет математические первоисточники Astra R5.3, UDC v0.3, Terra и train001. Нового APK/подписи/сборки нет.

## Изменение

`android/app/src/main/kotlin/org/unovyra/uno/UnoAndroidExactMemory.kt` — commit `d50a4aed8890ca871fead1bb6ed880efdf9d4f9d`.

Случай `base.aes + base.aes.new` ранее входил в путь `COMMITTED` и мог открыть старый base, хотя `.new` мог содержать более позднее запрещение доступа или revocation. Случай `.bak + .new` также неоднозначен.

Теперь этот конфликт вызывает `EXACT_CONFLICTING_PARTIAL_SNAPSHOT` **до** любого чтения/восстановления. Он не выбирает одну копию, не перезаписывает файл, не удаляет ни ciphertext, ни AndroidKeyStore alias. Если остался один `.new` без base/backup, прежний путь проверки authenticated partial сохранился.

Это соответствует границе R5.3 exact memory/revocation: отсутствие подтверждённого порядка записи не должно превращаться в уверенный `COMPLETE`. Fail-closed является **консервативной мерой**, а не проверенным протоколом power-loss или антиотката.

## Сохранившиеся блокеры

- В Android `AtomicFile` и `AndroidKeyStore` требуется device instrumentation на A52 для нормальной записи, прерванного `finishWrite`, переоткрытия, boot и process death.
- Полная C2 транзакция exact+semantic+P-state и антиоткат старого валидного ciphertext не реализованы.
- Существующая политика writable genesis при key-without-exact-ciphertext оставлена без изменений; её безопасность при пропавшем старом vault требует отдельного recovery-контракта владельца. Нельзя молча удалить ключ или старые данные.
- Никакой тест в рамках R4 не запускался; подмена исходника сама по себе не доказывает Android compatibility.

**Без изменений:** `org.unovyra.uno`, `main`, `DenyAllAndroidPort`, `NoWeightsNeuralPort`, подпись, веса, данные владельца и прежние исследовательские ветки.
