# UNO — граница передачи в реализацию и приёмка, V1, 12.11.2026

Документ адресован владельцу и следующему инженеру. Он не разрешает текущему аудитору изменять Android-код, обучать, запускать Actions или устройство. Предыдущее действующее разрешение владельца на разработку в feature branch не отменено историческими R5.3 gate, однако **это конкретное поручение ограничено аудитом и отдельной документацией**. Обучение production-весов, выбранная модель и изменение runtime-весов не разрешены. Никакой gate не утверждается здесь вместо владельца.

## 1. Что можно передать разработчику уже как точное задание

| Пакет работы | Контракт и первые проверки | Статус / граница |
|---|---|---|
| P1 Pure numerical F | Использовать S4–S5 из [кандидата](CORRECTED_ARCHITECTURE_CANDIDATE_V1_20261112.md), общие Θ, точные формы выбранного *исследовательского* manifest. Differential tests против independent FP64 oracle на малых детерминированных значениях; пустая память `z=tanh(z0)`; norm/finite/invalid shape. Считать вызовы активных и реально пропущенных kernels. | SPECIFIED_UNTESTED как единая интеграция; текущий [UnoFReference](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/178ac32f53d1e84d44ca27475279d35113c19719/android/core/src/main/kotlin/org/unovyra/uno/core/UnoFReference.kt) — численный host-участок, не обученный F в Android. На текущем задании код не писать. |
| P2 Единая session/GOAL | Один владелец `(s,g,goalVersion,session/STOP/memory epochs)`; GOAL same F с `s=g=0,I=∅`, сохранение одного рабочего s, атомарный check-and-publish, отмена устаревшего work cookie; raw goal в разрешённом exact store. | SPECIFIED_UNTESTED; выбрать механизм сериализации, но не продуктовый размер/ABI. |
| P3 Action protocol | Canonical args → тот же F в PROPOSAL → freeze `h_a` → S7 → независимый доверенный gate. Для внутренних verbs нет ticket; попытка/отказ/unknown различаются. Parent envelope/deadline/budget проверять доверенным кодом. | SPECIFIED_UNTESTED; identity-only planner не обещает многошаговую декомпозицию. Численные caps 64/16/3 — кандидаты, не пользовательское решение. |
| P4 Controller/reference исправления C1 | Trusted monotonic clock с boot ID при каждом admission/dispatch, сохранять expiry точного consent и повторно сверять его **после** prompt и **на** linearization; тестировать expiry между prepare и dispatch, STOP, отмену и уже отправленные эффекты. | FAIL как основание подключать privileged port к текущему host reference; действующий Android deny-all, физический эффект не показан. |
| P5 Memory authority | Единый durable scope epoch/tombstone для exact+semantic; проверить выдачу и использование ранее прочитанного после revoke, crash после каждого шага, recover, ABA, cross-boot, несовместимость модели, TTL, конфликт/неполноту. Сначала логический отказ, потом физическая уборка. | SPECIFIED_UNTESTED; отдельная будущая инженерная реализация. |
| P6 Weight validation | Проверка аутентифицированного manifest, integer overflow, exact shape/dtype/count, ranges, overlaps, endian, tokenizer/DSP/norm/version и после квантования; одно-байтовый пример обязан fail. Качество и лицензия — отдельные гейты. | FAIL если нынешний `admitWeights` считать полноценным loader; текущий `WeightCheckedNeural` намеренно не запускает модель. |
| P7 Dataset contract | Versioned roles A/B/C по UDC, `as_of` memory catalogue, независимые observer/teacher, complete denominator и censoring, split graph; T02/T05/T10 плюс leakage/negative cases. Создавать схему и synthetic fixtures разрешённой отдельной разработкой, не скачивая/обучая без прав. | SPECIFIED_UNTESTED; реальный лицензированный corpus REQUIRES_DATA. |
| P8 Validation | На одном хешированном candidate run T01–T17 и дополнительные тесты §3 с собственными oracle; версии, platform и точные команды фиксировать. Отдельные statics/compilation/host/device labels. | SPECIFIED_UNTESTED; эти тесты не проводились целиком в аудите. |

Не добавлять отдельную LLM, Android-планировщик с собственной принятой целью или девять самостоятельных «мозгов» под видом unified F. Технический backend/IO/permission boundary допустимы как обслуживающие механизмы. Не считать привязку чата и лаборатории к общей SQLite достаточной для общей нейросети: `s/g/Θ`, input/output paths и совместное обучение должны быть действительно одними.

## 2. Что должно быть определено до утверждения решения

| Вопрос | Что отсутствует | Статус |
|---|---|---|
| Собственные веса и из каких данных | Описанный licensed and consented корпус по всем обязательным модальностям, hardware budget, право на train и production-derivatives, конечный quality taskset. | REQUIRES_DATA / OWNER_DECISION для отдельного обучения |
| Способности и размер | Data/quality vs ресурс Pareto на нескольких достаточных кандидатах, A52 полный путь и риск OOD. d=512/1024 и 23/55M — расчётные примеры, не обязательные границы и не proof minimum. | REQUIRES_DATA / OWNER_DECISION |
| Формат/ABI и выбираемый backend | Исторический ABI/2 — детальный кандидат для B2, но текущий WeightManifest не реализует его; выбор параметров, способ хранения/подписи и Android backend ещё не утверждены. | SPECIFIED_UNTESTED / OWNER_DECISION |
| Распределение mask и градиенты | Фактический механизм selection, изменение support на границе и сравнение biased vs стохастических оценок; validation всех свободных весов с ненулевым допустимым gradient path. | CONDITIONAL / REQUIRES_DATA |
| Доверенная граница | Security threat model, enrollment/owner consent, binding expiry, OS/FS атомарность, допустимый IPC и действие только с effect/readback contract. Изолированный service сейчас stub. | SPECIFIED_UNTESTED / REQUIRES_DATA |
| Память и текущий контекст | Эквивалентность семантического индекса требованиям S4/epochs, точный revoke, migration, crash, общая транзакция публикации и retention. | FAIL для утверждения о готовой unified memory; исправление SPECIFIED_UNTESTED |
| Устойчивость и exact long memory | W4 распространяется только на фиксированный z и общую маску; постоянная точная память/адаптивный selector/global stability не следуют. | CONDITIONAL / REQUIRES_DATA |
| Планирование и наблюдаемость | Свежие data с независимыми метками effect/causality, end-to-end goals, UNKNOWN, simultaneous snapshot, owner envelope. | REQUIRES_DATA |
| Android A52 | Для полного пути — RAM/PSS, длительность, тепловой режим, батарея, ОС/permissions, STOP при in-flight и airplane mode/device matrix. | REQUIRES_DATA |
| NCR-EVO/саморазвитие | Equal-total-cost randomized controlled investigation, независимый oracle/holdout, отдельное разрешение; отсутствует показанный прирост, runtime 1.0 frozen. | REQUIRES_DATA / OWNER_DECISION |

Нет доказанного универсального математического запрета создать UNO, но существующая информация не определяет поведение на неизвестных задачах: два мира с одинаковой историей могут требовать разных действий. Нужны новые наблюдения/данные или уточнение задачи. Никакая «красота F» этот блокер не устраняет.

## 3. Строгая матрица приёмки будущего изменения

У каждого теста: immutable input hashes; версия кода/manifest; expected values и tolerances **до** исполнения; фактический stdout/stderr/exit; seed; реальный path; кто был oracle; модель угроз; использованный ресурсный бюджет; факт `HOST_TESTED` либо `DEVICE_VERIFIED`. Ожидание не равно результату. Отрицательные случаи и ошибки не скрывать.

| ID | Минимальный материал для объективного закрытия | Текущий статус |
|---|---|---|
| UDC T01–T17 | Все условия и ограничения в таблице [verdict §5](INDEPENDENT_VERDICT_V1_20261112.md); test dispatch trace, actual compute, causality, data roles, GOAL/proposal и planner bounds. | SPECIFIED_UNTESTED |
| G01 время/authority | t=100 prepare, consent expiry=120, deadline=200, dispatch t=150 → **никакого native call**, а также prompt истекает до prepare; compare свежие boot epochs; смоделировать долгий journal; clock failure -> deny. | SPECIFIED_UNTESTED |
| G02 STOP и память | STOP или revoke после F и сразу перед publish; устаревший version не проходит atomic CAS; уже dispatched -> unresolved + reconciliation, не автоматический повтор. | SPECIFIED_UNTESTED |
| G03 хранилище | exact/semantic на одном scope: crash до/после tombstone и каждой физической записи, restart, старый ref/ABA, TTL/cross-boot; ни один защищённый результат не опубликован после отзыва. | SPECIFIED_UNTESTED |
| G04 градиенты | Fixed mask/short unroll deterministic Θ: FP64 central differences отдельных entries и направлений против полного analytic gradient по *всем* использованиям общего Θ; separate tests discontinuities/STE с правильными labels; tied E со входом и выходом. | PROVEN_LOCAL только учебный скалярный пример; общий F SPECIFIED_UNTESTED |
| G05 retrieval | I=∅, singleton zero-gradient, два admissible distractors, отсутствие необходимого разрешённого target -> retrieval miss по полному denominator; revoked/denied -> корректный отказ по oracle, разные scope/epoch, gold-перестановка не меняет I и order, выбор зависим только от past. | PROVEN_LOCAL singleton; end-to-end SPECIFIED_UNTESTED |
| G06 сверка qR/qY | Для UNKNOWN не присвоить Y, отдельно логировать hard censor; при 10 TRUE/90 protocol-timeout R=0: observability=10/100, outcome=10/10 лишь условный; отчёт не называет общим success=10/10. | PROVEN_LOCAL математика; runtime SPECIFIED_UNTESTED |
| G07 ABI | `byteLength=1` + корректный собственный hash -> reject как model; truncated/overlap/overflow/bad dtype/unknown version/wrong tokenizer/NaN/bad norm/frozen rows; валидный roundtrip и pinned approved digest. | PROVEN_LOCAL контрпример нынешнего маленького gate; новый loader SPECIFIED_UNTESTED |
| G08 budgets | Уменьшение q запрещает вызовы inactive A/C/B, trace соответствует политике и replay PRNG; аддитивный work, live-peak RAM, все output/scan/cache/validation/abort costs; storagefull -> безопасный отказ. | SPECIFIED_UNTESTED |
| G09 единый цикл | Одно и то же model_digest/F/s/g проходит UI input→memory→goal→proposal→trusted readback→новое состояние; попытка смены цели/STOP/revoke инвалидирует все entry points; GGUF и synthetic reference не выдаются за один организм. | FAIL как описание текущей интеграции; новый SPECIFIED_UNTESTED |
| G10 результат/навык | Реальные заранее зафиксированные обученные checkpoint и licensed split; сравнение equal-data/equal-total-cost, одинаковые issued tasks, held-out/OOD, old/new/retention, неизвестные результаты в denominator, trusted independent labels. | REQUIRES_DATA; обучение в этом задании запрещено |
| G11 Android | В отдельном разрешённом device-процессе проверить build provenance, permissions, isolated execution, thermal/energy/latency/memory/offline, process death и реальные безопасные readbacks; запрет скрытых сетевых SAF провайдеров по выбранной политике. | REQUIRES_DATA; здесь не выполнялось |

## 4. Конкретная последовательность без лишних исследований

1. Сначала устранить противоречия контракта C1–C6 и создать независимые проверки на чистом host. Нельзя вызывать эти проверки подтверждением, пока не выполнены; их код/результаты должны оставаться вне original ASTRA/R5.3. По условиям этой работы дан только бумажный контракт.
2. Собрать фактический каталог будущих задач, источников, лицензий, отдельно training corpus и locked OOD. Если часть модальности отсутствует — сохранить явную строку `NO_DATA`, не подменять synthetic правилами и не обнулять класс в метриках. Подготовить всестороннюю проверку обучаемости с простыми контрмоделями и стоимостью; это самая ценная следующая работа.
3. После отдельного решения о собственном обучении и бюджете провести минимальный preregistered multi-task/transfer/retention эксперимент одного общего F и baselines; не именовать игрушечный демонстратор полноценным UNO. Если multi-task без крупного обучения ещё не может быть испытан, допустима малая ограниченная проверка механизма с названием и границами, но она не закрывает продуктовый вопрос.
4. Выбрать feasible model/runtime/формат по измерениям и решению владельца. Отдельно сравнить готового лицензируемого локального кандидата, если владелец его рассматривает: такой baseline не утверждает отказ от оригинального UNO или смены концепции.
5. Только при наличии проверенной модели и согласованных полномочий переходить к интеграции F в Android, а затем к отдельно разрешённым безопасным device испытаниям. Отчёт должен отделять `PLANNED`, `IMPLEMENTED`, `HOST_TESTED`, `ANDROID_BUILT`, `DEVICE_VERIFIED`, `RELEASE_READY`; успешное одно состояние не автоматически следующее.

Нормативные оригиналы, main, исходный Android и модельные файлы этим кандидатом не изменяются. Ветка аудита предназначена только для документов и не является merge/release/одобрением G4/G5.
