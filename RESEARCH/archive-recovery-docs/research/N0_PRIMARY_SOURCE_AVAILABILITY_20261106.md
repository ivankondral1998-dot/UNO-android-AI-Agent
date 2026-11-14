# UNO N0-01…N0-07 — фактическая доступность первичных исследовательских пакетов (2026-11-06)

Источник: вложенные `workspace/upload/uno_handoff/original_assets/` в приватном полном ZIP владельца, сверка ZIP entry names локально. Это **не** утверждение, что исходники уже загружены в GitHub; отчёты/карточки исследования отдельно присутствуют в `research/`.

| Исходный ZIP | Читаемых source/docs entries | APK/JAR entries | Вывод |
|---|---:|---:|---|
| `UNO_N0_01_RESEARCH_TRAINED_2026-11-05.zip` | 9 | 0 | первичный Python, frozen card, результат |
| `UNO_N0_02_LOCAL_PLASTICITY_RESEARCH_2026-11-05.zip` | 15 | 0 | Python, audit и FAIL evidence |
| `UNO_N0_03_ANDROID_SOURCE_2026-11-05.zip` | 6 | 0 | Java, manifest, frozen card |
| `UNO_N0_04_ANDROID_SOURCE_FINAL_2026-11-05.zip` | 7 | 0 | Android source; один дополнительный нетекстовый entry |
| `UNO_N0_04_ANDROID_RESEARCH_ARTIFACT.zip` | 3 | 1 | APK плюс build checks |
| `UNO_N0_05_DIAGNOSTIC_20261105_SOURCE.zip` | 13 | 0 | Android Java/manifest |
| `UNO_N0_05_NEURAL_AUDIT_CI_ARTIFACT.zip` | 4 | 1 | APK плюс CI evidence |
| `UNO_N0_06_HOST_PILOT_20261105.zip` | 10 | 0 | host pilot; дополнительные vendored Java/class проверить отдельно |
| `UNO_N0_07_TINY_F_ORGANISM_20261105.zip` | 23 | 1 | исходники, тесты, результаты; вложенный JAR |
| `UNO_N0_07_TINY_F_CI_ARTIFACT.zip` | 5 | 1 | APK и CI evidence |
| `UNO_N0_07_APK_FOR_PHONE.zip` | 0 | 1 | APK без исходников |

Кроме того, отдельные `UNO_N0_04_ANDROID_RESEARCH.apk`, `UNO_N0_05_NEURAL_AUDIT.apk`, `UNO_N0_07_TINY_F_RESEARCH.apk` существуют в исходном архиве. Это **исследовательские бинарники**, не production UNO и не доказательство испытания на A52.

## Что агент вправе заключить

- N0-01…N0-07 **проводились/документированы**; не писать «не существовали».
- `research/` содержит отчёты и исследовательскую историю; для воспроизведения конкретной версии исходников требуется побайтовый первичный source ZIP либо извлечённые проверенные файлы.
- В полном ZIP владельца есть эти первичные пакеты, но они **пока не зеркалированы как bytes в GitHub**. Их нужно переносить отдельно после проверки лицензий, секретов и частных данных; APK и JAR не обязательно размещать вместе с исходниками.
- Исходные исследования N0-07 и 400-строчный оригинальный raw export — **разные** объекты. Наличие пакета N0-07 не доказывает наличие последнего.
- Статус G4 PRECODE_CANDIDATE; production-code и G5 не разрешены.

См. [полный индекс 396](../archive/OWNER_COMPLETE_WORK_ARCHIVE_INDEX_20261106.json) и [ведомость первоначальных 41 исключений](../precode/vnext-r4/UNMIRRORED_41_EXACT_LEDGER_20261106.md) для SHA-256 и точных исходных путей.
