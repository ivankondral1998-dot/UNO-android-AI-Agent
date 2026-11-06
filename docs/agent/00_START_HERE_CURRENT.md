> **ПОСЛЕДНЯЯ СВЕРКА 2026-11-06:** 396 исходных членов; 262 точных зеркала, 96 дополнительных исторических, 22 только в индексе, 16 research/private только в архиве. Из исходных 41 исключений 3 закрыты: paper по совпадающему SHA, `00_START_HERE.md` и `VERIFY_OUTPUT.txt` побайтово загружены. **Остаток 38**, не 41. [Машинный реестр](../archive/OWNER_COMPLETE_WORK_ARCHIVE_INDEX_20261106.json) и [историческая ведомость 41](../precode/vnext-r4/UNMIRRORED_41_EXACT_LEDGER_20261106.md). Не считать старые числа ниже актуальными.

> **АКТУАЛЬНОЕ УТОЧНЕНИЕ РЕЕСТРА:** из первоначальных 41 незеркалированного элемента один paper найден и сверён в Git. Текущий остаток 40 (24 + 16). [Полная адресная ведомость](../precode/vnext-r4/UNMIRRORED_41_EXACT_LEDGER_20261106.md). Для N0-01–N0-07 не путать наличие отчётов с наличием оригинальных ZIP/APK.\n\n# UNO — ЕДИНАЯ ТОЧКА ВХОДА ДЛЯ АГЕНТОВ (vNEXT-R4, 2026-11-06)

**Это документ новой ветки `docs/uno-vnext-r4-source-recovery-20261106`, основанной на `docs/uno-lab-research-handoff-20261105` (`efdb1767ef75cbdb04ff813323c107c3bd22c4b6`). Он не отражает состояние `main`.**

## Первый проход (ОБЯЗАТЕЛЬНО)

1. Начни здесь, затем [R4 README](../precode/vnext-r4/README.md), [R4 original start](../precode/vnext-r4/package/00_START_HERE.md), [R4 Errata](../precode/vnext-r4/package/ERRATA_R4.md), [полная R4 спецификация](../precode/vnext-r4/package/UNO_INTEGRATED_NEURAL_ORGANISM_PRECODE_CANDIDATE_vNEXT.md).
2. Для не переопределённых формул используй [R4.1 inherited full paper](../precode/vnext-r4/package/R4_1_INHERITED_BASE.md); не заменяй полный текст одним summary. Для раннего источника R3 — [R3 original start](../precode/vnext-r3/package/00_READ_ME.md), [R3 Errata R2](../precode/vnext-r3/package/ERRATA_R2.md) и [R3 Errata R3](../precode/vnext-r3/package/ERRATA_R3.md).
3. Обязательно прочти первоисточник R5.3: [R5.3 source-package](../precode/r5.3/source-package/00_START_HERE.md), NORMATIVE/01–06 и полный Astra/R52. Они сохранены в исходном виде, новые исправления только версионированными документами.
4. Аудит: [R4 SOURCE_AUDIT](../precode/vnext-r4/package/SOURCE_AUDIT.md), [R4 evidence gates](../precode/vnext-r4/package/UNO_EVIDENCE_TRACEABILITY_AND_TEST_GATES.md), [R4.1 history](../audit/r41-engineering-20261104/00_START_HERE.md), [Astra audit](../audit/astra-20261102/R3_FINAL_REVIEW.md). Исторические FAIL не превращать в PASS.
5. Исследовательские результаты и фактический журнал — [BENCH.txt](../../research/uno-lab-001/BENCH.txt), [UNO_LAB_REPORTS.txt](../../UNO_LAB_REPORTS.txt) и [owner teaching + native outcomes](../research/OWNER_TEACHING_AND_ANDROID_EVIDENCE_20261105.md). Оригинальная N0-07 Stage5 реконструкция есть, **сырого полного потока с телефона здесь нет**.
6. Перед любым изменением сверить [Сводку сохранности и известности](../precode/vnext-r4/FILE_AND_EVIDENCE_REGISTER.md), [сводку ошибок агентов](../precode/vnext-r4/CLAIM_CORRECTIONS.md), [файл SHA](../precode/vnext-r4/MIRROR_SHA256.json), current branch SHA и последние решения владельца. «Не увидел файла» ≠ «файл не существует».

## Полномочия и фаза

`G4 PRECODE_CANDIDATE`; `OWNER_APPROVED_PRECODE=FALSE`; `PRODUCTION_CODE_AUTHORIZED=FALSE`; G5/G6 не разрешены. Исследовательское разрешение от 2026-11-05 отдельно ограничено: малая модель, изолированные эксперименты, замороженный протокол, <=600 sec, <=2GiB, до 3 повторов кандидата. Не разрешает production-код, Actions, публикацию или main merge. Владелец принимает O01–O08, а не агент.

**Факты:** R5.3 и Astra документированы, R4.1 и vNEXT-R3 восстановлены, vNEXT-R4 добавляет адресные исправления V14/V19/V20; испытания на A52 ранее были (N0-03–N0-07), но устройство не подтверждало полнофункциональный UNO. Нет подтверждённых production weights или G4 approval. На этом состоянии нельзя утверждать, что этих документов / экспериментов «нет».

## Целостность источников

- Приложенный ZIP R4 `UNO_WORK_RETURN_PACKAGE_R4.zip`: SHA-256 `85f203bbe6cd4f584ef70e9fd4cd77f4b2e11a6a0076c6607d946c5d82637ba6`; локально извлечён и повторно проверен.
- Полный пакет предшествующей работы `UNO_ALL_WORK_AND_SOURCES_2026-11-06.zip`: SHA-256 `8c87ebec317f9acd8398a1ff239edfccb193c0e182e0f91ef447bcb3b26ac02b`; содержит также приватные PMB/диалоги/исследовательские APK и не должен механически публично копироваться в дерево Git. Материалы проекта, необходимые агенту, зеркалированы в документах выше.
- Не утверждать, что личный архив/полный сырой owner telemetry доступны в GitHub, если их нет. См. точный scope registry.
