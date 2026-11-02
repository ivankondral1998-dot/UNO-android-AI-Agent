# R5.3 composite — выполненные проверки и границы

## Выполнено в текущем сеансе

- Подлинный источник Astra Final проверен против **116 записей** в его `FINAL_PACKAGE_MANIFEST.json` по size и SHA-256. Верхняя папка архива содержит также сам manifest, который не хешируется собой.
- Текущие ASTRA_01–12 включены **из последнего финального архива**, а не из R1/R2 snapshot; оригинал сохраняется неизменённым.
- Составной пакет включает адресные R5.1/R5.2 документы, прежний R5.3, full M01–M44, индивидуальные D/X/B, предыдущие аудиты и проектный исходник Work V2.2. Все их байты отражены в финальном manifest.
- Проверочный скрипт `EVIDENCE/recheck_arithmetic.py` независимо воспроизводит 4 totals B2, frozen rows, 4 MAC counts F, три epsilon-контрпримера hard selector, counts масок и cancellation memory.
- `SHA256_MANIFEST.json` считает SHA-256 **только остальных файлов пакета**, сам себя не включает. После сборки архив проходит ZipFile.testzip + независимую побайтовую сверку всех payload с manifest; итоговый zip SHA указывается во внешнем `SHA256_EXTERNAL.txt`.

## Не проверено и не объявляется PASS

- Математическая soundness каждой строки из 116 исторических файлов; correctness всех формул F/L3a/L4/L5 в произвольной среде, всей численной стабильности и полной интеграции Android.
- Никакие модели/сети **не обучены**, dataset rights не приобретались, A52 measurements не получались, UI/voice/Android native code и верифицируемый runtime не тестировались.
- WAKE acoustic и SENSOR target разработаны **как бумажные кандидаты**. Не доказаны low-power wake/системная доступность, корректность сенсорных значений без native oracle.
- W4 даёт только fixed common mask proof. Не доказаны full-organism contractivity/качество/скорость/регенерация.
- Formal verification of ownership/capability assumptions A_cap/A_tx/A_fs, полноценный LR2/H2 ABI/export, statistical power/data for NCR.
- Будущее утверждение владельца, разрешение кода и коммерческая пригодность отсутствуют.

## Дельта относительно краткой R5.3 Grok

| Дефект предыдущего документа | Исправление в composite | Доказательная граница |
|---|---|---|
| Нет полного Theta manifest/ABI | полный ASTRA_02 + machine tensor manifest + W2 count checker | shape/count PASS; trained/export NO |
| L3a и gradients сократили до Jbase | полный ASTRA_03 L3a/L4/L5/QAT/CTC | conditional derivations, no trained data |
| Режимы памяти без snapshot/revoke | R52/02 полностью + explicit supersession | contract candidate, native tests absent |
| WAKE/SENSOR только dual-option | R52/03 полностью с acoustic baseline и typed sensor semantics | owner choice and eval open |
| D/X/B сгруппированы | D01..10/X01..12/B01..14 индивидуально | statuses not test results |
| M01–M44 потеряны | Astra_09 + reproduced rows in normative registry | historical rejected remain rejected |
| Неопределённые n_b,q_j,M | словарь в 01, explicit distinction q_j/c_j | threshold values owner choice |
| Нет source precedence | owner>explicit delta>final Astra>historical evidence | still candidate until owner approves |
| Старый манифест хешировал себя | новый без self-reference; исторический original preserved | integrity not semantic proof |

**Итог:** `COMPOSITE_PACKAGING_PASS` при прохождении manifest verification; `LOCAL_ARITHMETIC_PASS`; `GLOBAL_MATH_CERTIFIED = NO`; `PRE_CODE_OWNER_APPROVED = NO`.
