# UNO — предкодовый инженерный мастер-план и реестр открытых решений

Дата: 2026-11-02. Статус: **PRE-CODE SYSTEM DESIGN / НЕ ДОПУЩЕН К PRODUCTION IMPLEMENTATION**.

Исходная проверенная база: `UNO_MATHEMATICAL_DESIGN_AUDITED_2026-11-01.zip`, версия v1.1 (файлы `00`–`09`, `OPEN_QUESTIONS_AND_DECISIONS.md`, `INDEPENDENT_REVIEW.md`, исходный NCR-EVO). Этот документ — инженерная дорожная карта на основе оригинальных файлов, а не замена/сертификат математики Work. До принятия решений владельцем расчётные конфигурации остаются кандидатами.

## 0. Цель, которую нельзя сокращать

UNO — новый самостоятельный коммерческий **полностью локальный Android AI-агент**; нейронная архитектура должна охватывать восприятие, единые обучаемые веса, общие вычисления, долгосрочное состояние, цели, решения, прогноз исходов, пластичную память, безопасное исполнение и достоверную обратную связь. Единый интеллект, а не ансамбль отдельных управляющих LLM/мостов. Android API / permissions / STOP / trusted authority / native readback являются необходимой внешней границей, но не дополнительным «мозгом». Первое устройство — Samsung Galaxy A52, Android 14; параметрическая архитектура должна переноситься на другое железо. NCR-EVO — строго изолированная исследовательская лаборатория, **не** самопрограммирование пользовательской APK. Старый JarvisLab — источник исторических примеров/локальных компонентов только после лицензирования и проверки; никаких изменений там без отдельного указания. CELL и PMB — отдельные проекты; их не включать.

Основной запрет: **не создавать новое production ядро, Android APK, производственные обученные веса, релиз, merge или GitHub Actions** до формальной приёмки этого предкодового плана. PR #3 — исторический host reference, не канонический UNO Core.

## 1. Что математически уже определено (не путать с экспериментально доказанным)

- Событийный переход `X_t -> X_(t+1)` с ограниченными фазами и явными outcomes (`02`); типы, пространства и квоты (`01`).
- Общий block-recurrent оператор `F`, shared weights `Theta`, bounded hidden state, mask пропускает реальные блоки (`02`, `03`). Условная контракция доказана **только** при фиксированных входе/весах и дополнительных условиях на маски (`05`).
- Один реестр весов, включая текстовый вход/выход, аудио, экран, сенсоры, мета, goal/state, memory I/O, оператор `F`, typed actions/expected outcomes, ASR/TTS heads, селектор/пробуждение (`03`).
- Обучающие objectives/градиенты и локальное обновление `P` по проверенному исходу (`04`). Не доказана способность полного обучения на доступном наборе данных и сохранение любых навыков.
- Stop/epoch/generation, receipt, verification, transactional memory, restore, отказ по умолчанию (`02`, `05`). Это **теоремы при предпосылках** о доверенном Android/backend, который ещё не реализован.
- Вычислительный бюджет и компонентная модель RAM/MAC/energy (`05`); неизвестны реальные коэффициенты Android.
- Отдельный NCR-EVO typed DSL/AST, mutation -> constraints -> surrogate -> evaluation -> QD archive -> recovery -> promotion с разрешением владельца (`06`). Его выигрыш по полезности не доказан.
- `09` содержит **14 математических oracle** будущей реализации. Нужны дополнительные oracle для обучения, сериализации, DSP и качества.

**Матрица Work v1.1:** M01–M44: 30 PASS (в том числе условные), 9 FAIL (в основном ложные универсальные утверждения + размер), 5 NOT_TESTABLE (обучение, качество/размер, Android, NCR-EVO). Нельзя заменять результат «44/44 PASS» путем удаления неудобных требований. Следующий пакет должен связывать КАЖДОЕ незакрытое требование с экспериментом и порогом.

## 2. Предварительная геометрия модели (ещё не утверждение параметров)

Семейство из `03`: `d in {512,1024,1536,2048}`, `b=64`, `chi=4`, `J=2`, `V=32768`, `A=128`, `m=128`, максимум `K=8`, `P in R^(A x d)`, `M_max=4096`; `d=1024` — **расчётная точка**, не доказанный оптимум.

| d | Медленные параметры Theta | Только FP16 веса, МиБ | F MAC / полный шаг | F MAC при K=8 |
|---:|---:|---:|---:|---:|
| 512 | 22 950 223 | 43.774 | 4 456 448 | 35 651 584 |
| 1024 | 55 320 439 | 105.515 | 17 301 504 | 138 412 032 |
| 1536 | 97 144 223 | 185.288 | 38 535 168 | 308 281 344 |
| 2048 | 148 421 575 | 283.092 | 68 157 440 | 545 259 520 |

При `d=1024` словарная голова = 33 554 432 MAC **на каждый выданный токен**; 100 log-mel кадров аудио в секунду и DSP нужно считать отдельно. Для `d=1024` базовые расчётные блоки RAM: FP16 Theta ~105.515 МиБ; FP32 P 0.5 МиБ; memory keys/values/metadata 2.25 МиБ; контекст 0.5 МиБ; pending metadata ~0.070 МиБ; 10-секундный PCM 0.305 МиБ; при полном резервировании общего payload-store 16 МиБ; по 1 МиБ trust-ledger/diagnostics. Сумма таких компонентов ~**127.14 МиБ**, **без** activation/workspaces, упаковки int8, модельных дубликатов, Android heap, UI, graph/runtime/DSP/image buffers, WAL/staging и драйверов. Это НЕ численная верхняя граница PSS.

FP32 offline-training baseline `16*P_Theta` (веса+градиенты+2 Adam moment) для d=1024 ~**844.12 МиБ**, без batch activations, mixed-precision master copies, optimizer overhead, датасета и GPU memory fragmentation. Выбор обучения нужно считать по фактической последовательности и batch size. INT8 в пакете ~53.131 МиБ — **только конкретная схема хранения матриц**, не итоговый Android RAM или гарантированная ускоренная арифметика.

## 3. До кода нужен «пакет конструирования»: обязательные проекты и расчёты

Каждый нижеуказанный документ должен содержать уравнения/размеры, порядок сборки, допустимые варианты, материальные бюджеты, наблюдаемые ошибки и критерии приёмки. Нельзя подменять незнание красивой цифрой.

### D01. Продуктовая спецификация задач и данных

**Что:** точный каталог обязательных сценариев с входами/выходами: русская речь/ASR, понимание произвольных пользовательских задач в разумно определённом диапазоне, текст, ответ и уточнения, цели и планы, визуальное состояние телефона, сенсоры, native Android actions, TTS, память, обучение по последствиям; отрицательные/опасные сценарии. Разделить minimum shippable tasks от исследовательских режимов, не выкидывая последние из архитектурного плана.

**Рассчитать:** распределения длины (токены, аудиокадры, изображения), долю UNKNOWN, задержку на задачу, допустимые false actions, покрытие (`coverage`), минимальный успех для каждого класса `q_j`, штраф на ошибочное исполнение, тестовые strata. Заранее указать baseline (табличный, фиксированная сеть, recurrent/attention) и held-out распределения.

**Состояние:** BLOCKED: Work не получал реального набора пользовательских задач, корпуса/действий и числовых порогов `q_j`. До этого оптимальный d не идентифицируем.

### D02. Канонический нейронный чертёж / ABI

**Что:** исчерпывающая таблица Θ и P с именными формами, dtype, единицами измерения, layout, alignment, norm constraints, initialization, update schedule, version/digest, tokenizer и DSP conventions. Отдельно versioned Graph, модельные и доверенные состояния. Строго показать совместимость forward/backward и связи между modalities/heads и **одним** F.

**Рассчитать:** `P_Theta(d,b,chi,J,V,A,m)` по (W1); peak workspace при разных schedules; MAC, memory bandwidth, cache, quant error bounds; инварианты после dequantization; осмысленный режим реальной block sparsity. Выделить, где full vocabulary / TTS / ASR разрушают бюджет.

**Состояние:** ЧАСТИЧНО ГОТОВО: формы/parameter counts есть; не выбраны ABI tensor layout, backend-specific packing, quantization fidelity, export parity.

### D03. Обучение НОВЫХ весов с нуля

**Что:** источники и права на русскоязычные текст/аудио, изображения/экраны, пары команда→исход, диалоги, TTS speech, состояния/цели; данные train/dev/immutable holdout/OOD; отсутствие утечек и PI; почему loss каждого head имеет валидный target; отсутствие обязательных old Jarvis weights. Обучение целиком Θ по стадиям, включая shared F, online `P` отдельно. Нельзя учить только readout и объявлять обученным организм.

**Рассчитать:** смеси задач/веса losses, token/frame/image counts, effective batch, BPTT/truncated BPTT lengths, optimizer, precision/norm projection after update, checkpoint size, FLOPs training приблизительно от forward/backward/sequence и числа токенов, RAM/VRAM, время и стоимость под доступное устройство обучения. Требуется документированы ранжированные планы A/B/C по доступному compute. Продумать ablation памяти, K, sparse masks, text head, ASR/TTS heads, goal conditioning.

**Состояние:** BLOCKED для численного training budget: не известны датасеты, GPU/CPU и целевое качество.

### D04. Память и переносимость навыков

**Что:** строгий жизненный цикл S=(s,P,M,Q,...) и trusted L; обновление только по валидной квитанции, provenance, retention, forgetting, re-encoding при смене modelVersion. Следить за зависимостью keys от Θ и необходимостью migration/replay. Отдельные требования на калибровку outcome и непротиворечивость фактов.

**Рассчитать:** максимальное число записей и размера payload, latency scan при `M_max=4096`, cost памяти на событие, горизонты retention, transaction/WAL snapshot, eviction/pinning; bounded-regret и performance envelopes по классу задач, где возможно. `zero forgetting` на всех распределениях недоказуемо; задать статистические допуски регрессии на контрольном наборе.

**Состояние:** ФОРМАЛИЗОВАНО, требуется decision по retention и измерения forgetting.

### D05. Доверенная Android-граница и state machine

**Что:** для каждого Android verb: permission, schema, consent scope, expected predicate, pre/post readback, idempotency, timeout, CANCEL/STOP, partial execution, UNKNOWN, retry, transaction semantics, owner-intent, generation & epoch, replay, process death, lockscreen, foreground/background restrictions. Строго отделить физический факт от причинности, `success`-текст от receipt. Выбрать защищённое хранение counter/keys/manifest с учётом rollback threat model; нельзя обещать hardware антиrollback без проверки железа.

**Рассчитать:** event phases/latency, worst-case stopping latency до dispatch, operation-specific readback cost/availability, журнал+atomic commit time/storage, crash recovery/rollback, энергопотребление контроллера в покое. Модель не имеет прямого доступа к external OS APIs; единственный privilege boundary — trusted gate.

**Состояние:** FORMAL CONTRACT имеется; АРХИТЕКТУРА Android backend, privacy/keystore/db choice и эксплуатационные измерения — BLOCKED.

### D06. Мультимодальное исполнение и локальный голос

**Что:** полный протокол AUDIO(PCM→log-mel→F→CTC), TEXT(byte-fallback→embeddings→F→tied vocab), IMAGE(patches→projection→F), SENSOR/OS, TTS(STFT magnitude→DSP phase restoration), планирование и bounded speech/text generation. Не обещать, что один математический output head даёт intelligible real-time speech.

**Рассчитать:** events/s, MAC/s, FFT/s, buffers, end-to-end latency (wake→ASR→interpret→action; text→TTS), UI responsiveness, power idle/listening/speaking. Для вариантов STFT-TTS и альтернативных vocoder вычислить разницу weights/MAC/quality/training data; не выбирать голос по архитектурной эстетике.

**Состояние:** DESIGN описан; модельное качество и downstream DSP / real-time ASSUMPTIONS требуют сравнительного теста.

### D07. Ресурсы и аппаратная реализация

**Что:** целевая аппаратная матрица Samsung A52 Android14: поддерживаемые CPU/GPU/NNAPI backend, память приложения, температурные и батарейные ограничения, архитектура native threads, доступность quantized fused ops, режимы foreground/background. Сначала определить **план измерений** и допустимые пороги; затем выбрать backend на данных, не по предположению.

**Рассчитать:** `RAM_peak = Theta+P+M+ctx+pending+DSP+workspace+OS+staging+payload+trust`, `J_total = θ_mac MAC + θ_mem bytesMoved + θ_dsp DSP + θ_io IO + P_idle T_idle + J_control + J_OS`, latency по отдельно нормируемым paths. Метрики на task (включая отказы), 1h/24h standby, cold start, temperature, Android process kill.

**Состояние:** формулы есть; коэффициенты/benchmark железа отсутствуют. Нельзя честно назвать `A52 PASS` до измерений.

### D08. NCR-EVO (цикл Астры) как изолированная лаборатория

**Что:** типизированный DSL/AST и immutable contracts, генератор мутаций, дешёвый surrogate, uncertainty/diversity, независимый evaluator, QD archive, ancestry, regeneration из проверенной информации, provenance/rollback, ручная promotion. Отдельная оценка эффективности compared A/B/C/D при одинаковых total CPU/energy/time budgets, включая стоимость обучения surrogate и selection bias. Нет автоматических изменений deployed model/code или safety contracts.

**Рассчитать:** expected valid/novel candidates per CPU-hour; archive growth/quota; confidence intervals, paired holdout, мощность/эффект, exploitation/exploration; влияние surrogate и альтернатива без него. На миллион полных Android-сборок не рассчитывать. Явно доказать, что процесс не модифицирует trusted OS boundary.

**Состояние:** математический протокол есть; реальные superiority claims — NOT_TESTABLE, отдельный исследовательский проект, не блокирующий базовый offline Android runtime если бизнес-цели требуют отделения.

### D09. Полный build/training/deployment граф до первого коммита

**Что:** спецификация репозитория/модулей, воспроизводимые tools + версии и локальная модельная ABI. Порядок артефактов должен быть строго определён (не код):

1. `model_architecture.yaml` + `tensor_manifest.json`: все слои, формы, квоты, norms, tokenizer/DSP/version.
2. `dataset_manifest.json` + licenses + immutable splits; фиксированные evaluation scripts/protocol.
3. `training_spec.yaml`: optimizer, seed, loss heads, curricula, quantization-aware procedure, checkpoint, pass criteria.
4. `weights.fp32/weights.f16/weights.int8` с SHA, model signature, tensor parity/quant error.
5. `core_math_api.md`: primitive contracts для reference/host; no production coding до gate.
6. `android_boundary.md`: per-verb native APIs/permission/consent/STOP/readback contracts.
7. `runtime_schedule.md`: одно состояние, event loop, memory/checkpoint IO, CPU/GPU lanes, cancellation/failclosed.
8. `build_release.md`: SDK/JDK/Gradle/NDK candidates, toolchain lock, signed build, SBOM, licenses, offline app manifest, installation, crash/rollback, QA.
9. `acceptance_plan.md`: formal oracle O1–O14 + обучение/accuracy/generalization/safety/device/NCR-EVO; evidence per gate.

**Рассчитать:** зависимости артефактов, memory footprint каждого, backend numeric parity, test-comparison tolerances, legal/licensing status, build time and storage for target CI-free local builds. Build commands определять после выбора backend и реального окружения; не предлагать GitHub Actions.

**Состояние:** `09` — только математический контракт будущего кодека; полного implementation manifest, data/compute plan и Android backend design нет.

### D10. Регистр рисков, испытаний и эксплуатация продукта

**Что:** угрозы владельцу/данным, работа в авиарежиме без cloud dependencies, privacy/storage encryption и consent, недостоверный readback, ошибки ASR/ложная активация, неустойчивое обучение, заражение корпуса, несовместимость квантования, ресурсное истощение, невозможность возобновления после crash, устройство недоступно/перегрев. Для каждой угрозы prevention/detection/mitigation/owner decision.

**Рассчитать:** целевой coverage/false-action thresholds, confidence bounds, release stop conditions, worst-case budget, rollout/rollback protocol и оценку стоимости поддержки коммерческого продукта. Не заявлять 100% безопасности или надежности в произвольной среде.

**Состояние:** Частично в 05/07/09. Не готов полный threat-model/release spec.

## 4. Что НЕ может быть рассчитано «на бумаге» до данных и железа

- Достаточны ли именно 55.32 млн параметров для нужного русского языка/диалога/планирования/видео. Геометрия весов определяет возможности выразить функции, не способность **обучиться** этим функциям на реальных данных.
- Достигнет ли заданный модельный граф `q_j` и сохранит ли навыки при online P/consolidation. Требует обученных весов, данных и независимого holdout.
- Какими будут реальные джоули, PSS, latency и температурное дросселирование на Samsung A52. Нужен эксперимент, причем до production model возможно раннее замерить примитивы backend, **не реализуя интеллектуальный UNO Core**.
- Даст ли NCR-EVO устойчивое преимущество над random/MAP-Elites baselines. Нужен изолированный лабораторный эксперимент и статистика.
- Может ли невосстановимая утраченная информация быть регенерирована. Не может в общем случае: требуется trust baseline, redundancy или новый независимый обучающий сигнал.

Эти вопросы нельзя честно маркировать PASS из желания получить «100% бумажной готовности». Можно добиться **100% specification completeness**: либо доказательство, либо вычислимый метод измерений и порог, либо честно установленный риск/невозможность.

## 5. Гейты (никаких процентов готовности из числа тестов)

| Gate | Что должно быть перед переходом | Текущий статус |
|---|---|---|
| G0 SCOPE | Конечный набор функций, внешние/внутренние границы, коммерческие требования | Цель есть, точные `q_j` отсутствуют |
| G1 FORMAL | Уравнения, полные размерности, доказательства в области допущений, негативные контрпримеры | Условный PASS Work v1.1 |
| G2 ENGINEERING | D01–D10 с полными ABI, dataset, training compute, runtime/release architecture, trust threat model, quantified budgets | **НЕ PASS** |
| G3 BENCHMARK PROTOCOL | Стратифицированный holdout, baselines, методы измерения A52, риск-пороги, критерии остановки | **НЕ PASS** |
| G4 PRECODE DESIGN REVIEW | Независимый контроль всех D01–D10: конфликтные требования разрешены, каждый параметр traceable, блокеры явны, owner утверждает | **НЕ PASS** |
| G5 IMPLEMENTATION | Только после G4: train reference, weights, host parity, Android SDK/runtime, gates безопасности, APK device tests | Не начинался |
| G6 RELEASE | Проверено on-device качество/ресурсы, privacy/security, reproducibility, подписанные артефакты | Не начинался |

**Порядок:** G0→G1→G2→G3→G4→G5→G6. Для неизвестных физических коэффициентов допускаются отдельные минимальные калибровочные измерения устройства без production UNO, но результаты должны войти в G2/G3 до фиксации архитектуры. Запрет на ядро не означает запрет на измерения аппаратуры.

## 6. Реестр решений, которые должен получить следующий математический/системный аудитор

| ID | Решение | Текущий default | Что подтверждает | Без чего не фиксировать |
|---|---|---|---|---|
| DEC-01 | Список задач и качество | Полный контур: RU voice/text/vision/action/memory | Task battery с q_j и risk thresholds | Нет метрики достаточности d |
| DEC-02 | d и семейство F | d1024 baseline, варианты d512/1536/2048 | Training/holdout и A52 benchmark | Нет выбранного production size |
| DEC-03 | Tokenizer V | byte fallback V32768 | RU OOV, token rate, memory | Нет finalize vocabulary |
| DEC-04 | Audio/ASR | 16kHz, STFT512 hop160, mel80, CTC128 | WER, OOD, noise, latency | Нет доказанного RU ASR |
| DEC-05 | Text/grammar | tied Etext, verb schema A128 | Language/action QA, calibration, false-action rate | Нет autonomous safe execution |
| DEC-06 | Vision | patches16×16, feature768, max256 | screen understanding benchmark | Нет verified vision ability |
| DEC-07 | TTS | 257 mag + fixed DSP I_GL≤16 | intelligibility/MOS, speed, power | Не считать speech ready |
| DEC-08 | P retention | m128, M4096, P=A×d | online learning + forgetting tests | Нет качественного forgetting guarantee |
| DEC-09 | Norms/quant | γ=.9, α=.5, INT8 candidate | after-dequant norm and accuracy | Нет stability certificate on backend |
| DEC-10 | Owner authority | OS trusted gate, ν/e, STOP | Android threat model + real API readback | Нет implementation safety PASS |
| DEC-11 | Data and compute | new training from scratch | licenses, GPU budget, loss mixture | Нет viable training schedule |
| DEC-12 | NCR-EVO | off-device, no autopromotion | matched A/B/C/D, security isolation | Нет заявленного улучшения |

## 7. Точное следующее поручение (продолжать исследование, не кодить)

Провести **PRE-CODE ENGINEERING DESIGN REVIEW UNO** по всему оригинальному пакету Work v1.1 и этому мастер-плану. Не переписывать математику целиком и не удалять доказанные ограничения. Выдать D01–D10, implementation BOM, tensor ABI, data/training pipeline с затратами и зависимостями, Android capability table и resource model с sensitivity, build graph, risk register, reproducible evaluation protocols, traceability matrix `requirement→equation→tensor→dataset→artifact→test`, а затем независимую red-team проверку. Везде указать статус `PROVEN`, `SPECIFIED`, `ESTIMATED`, `REQUIRES_DATA`, `DEVICE_BLOCKED`, `REJECTED`. Конечный документ должен показывать разработчику точный следующий шаг и критерий готовности, а не просить его выдумать архитектуру самому. Не создавать production-код, не запускать GitHub Actions, не менять JarvisLab и main.

Если выяснится, что выбранный F не справляется с продуктовой задачей или не помещается в реальные бюджеты, зафиксировать это **как инженерный blocker** и изменить архитектуру на бумаге после объяснения компромиссов. Никакого фиктивного 100% PASS.
