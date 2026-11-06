# R5.2 — что закрыто, что проверяем дальше и когда допускается код

## Формально подтверждённые локальные результаты

| Обязательство | Статус | Основание |
|---|---|---|
| W4 одинаковые маски | `PROVEN_CONDITIONAL` | Неравенство и отдельная формула для изменяющегося z в `01` |
| Global bound для произвольного hard selector | `FAIL / FALSE` | Контрпример ε→0 в `01` |
| Semantic aggregation lossless | `FAIL / FALSE` | Противоположные значения v,-v в `02` |
| Exact retrieval behavior | `SPECIFIED_CANDIDATE` | Контракт и 7 тестовых оракулов в `02`; Android tests open |
| WAKE acoustic | `SPECIFIED_CANDIDATE / DATA_OPEN` | Цепочка audio→shared F→CTC→wake phrase в `03`; metadata-only wake не акустический |
| SENSOR | `SPECIFIED_CANDIDATE / DATA_OPEN` | Данные 32+32 mask→shared F; `L_sensor` как *новое* требование |
| 16-block prefix vs arbitrary | `ARITHMETIC_PASS` | 16·15+1=241; 2^16−1=65535, для q=3:16 vs C(16,3)=560 |
| Offline SAF | `BOUNDARY_SPECIFIED / DEVICE_OPEN` | default local-only, UNKNOWN provider rejected |
| Android STOP/authority | `CONDITIONAL_CONTRACT / DEVICE_OPEN` | No after-dispatch rollback guarantee; no old Jarvis component required |
| Quantized B2 counts | `LOCAL_ARITHMETIC` | Astra manifest; trained tensor/dequant parity absent |
| NCR-EVO | `DESIGN/EXPERIMENT_REQUIRED` | Termination ≠ superiority/self-regeneration |

## Неизменённые gates, которые нельзя превратить в PASS текстом

D01: owner scope/thresholds/14-class battery; D02: trained/export parity; D03: licensed data/training; D04: implementation memory fault tests; D05: Android trusted boundary tests; D06: RU/audio/screen/task quality; D07: A52 resources; D08: NCR-EVO experiment; D09: full ABI/build/local-source audit; D10: risk/legal/release thresholds.

X01–X12: ранее доказанные локальные identities остаются conditional where specified, X12 full trained Θ remains OPEN. B01–B14: user acceptance, corpora, weights, Android tests, commercial readiness remain OPEN where empirical; B12 evidence exists, B14 NOT_AUTHORIZED. См. оригинал `R5_1_.../05_D_X_B_GATE_MATRIX.md` и Astra D01–D10; численные PASS не переносить по краткой сводке.

## Стадии согласования

- **Сейчас:** R5.2 paper-only `CANDIDATE`; подготовлены поправки, исходники/история не перезаписаны.
- **Перед pre-code подписью:** владелец выбирает product-scope/architecture tradeoffs и предварительные quality gates; независимо проверяются разницы R5.1→R5.2; полная нормативная спецификация собирается и индексируется без противоречивых «APPROVED».
- **После отдельного решения владельца:** производственный код, обучение модели, Android tests, оценка качества и ресурсов.
- **Коммерческий release:** только по экспериментальным/правовым gates и подтверждённой работоспособности; не следует из pre-code подписи.

## Журнал статусов

`OWNER_APPROVED_PRECODE = FALSE`; `CODE_AUTHORIZED = FALSE`; `TRAINING_PERFORMED = FALSE`; `A52_DEVICE_VERIFIED = FALSE`; `COMMERCIAL_READY = FALSE`. Ранее напечатанное Grok APPROVED в старом пакете — ошибочное свидетельство, не решение владельца.

**Все материалы в текущем ZIP — новые кандидатные поправки. Они не меняют исходные Astra/Grok архивы и не утверждают baseline.**
