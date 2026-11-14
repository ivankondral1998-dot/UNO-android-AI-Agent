# Независимый слепой аудит UNO v1.1 — 2026-11-02

## Статус и пределы

Это самостоятельная реконструкция, зафиксированная **до чтения** `07_CRITICAL_REVIEW_AND_COUNTEREXAMPLES.md`, `08_MATH_ACCEPTANCE_MATRIX.md`, `OPEN_QUESTIONS_AND_DECISIONS.md`, `INDEPENDENT_REVIEW.md`. Численный пересчёт выполнен встроенной арифметикой Python; production-код, чужие исходники, обучение, Android и репозитории не запускались/не изменялись. Это не машинная сертификация и не доказательство отсутствия ошибок.

Полностью прочитаны mandate, masterplan, v1.1 `00–06`, `09`, все три Markdown-originals, включая полный исходный NCR-EVO brief (170 строк). Первая совмещённая выдача masterplan была усечена инструментом; затем весь документ прочитан частями 1–100 и 101–180. Исторические live Git refs не проверялись: граница задания — представленный документальный корпус.

Вывод: внутренние формулы весов, локального projected-gradient и условной контракции согласуются в проверенных областях; полнота математической/инженерной спецификации **не установлена**. До исправлений ниже нельзя выводить unconditional FORMAL_PASS или готовность к производственной реализации.

## 1. Самостоятельная реконструкция

Внешний мир `w` не принадлежит изменяемому нейронному состоянию. Для события с trusted clock `τ` сначала выбирается событие минимального времени и приоритета, затем производится конечный переход `δ`, затем среда эволюционирует до следующего допустимого момента. Тексты и сенсорные наблюдения не дают полномочий. Capability/STOP/generation/receipt-ledger лежат в `T`, модель в `S`.

Для одного принятого наблюдения, при замороженных `s,g,M,Θ`:

`q=tanh(Wq(s+g)); r=Σsoftmax(q·key/(√m TM))value; z=tanh(Eτ fτ+Us s+Ug g+Wr r+Wmeta fmeta+eτ+bz)`.

`h0=ρs+(1−ρ)z`; до inner-loop выбирается конечная маска. В активном блоке `h'= (1−α)h+α F(h,z)`, в неактивном блоке identity. Каждая ветвь `F_lj=tanh(B_lj tanh(A_lj h+C_lj z+a_lj)+b_lj)`; ветви усредняются. После K шагов `s'=hK`. Глагол/аргументы являются предложением, проверяемым trusted gate. Только проверенная бинарная метка на свежем ticket может менять P.

Online row update действительно равен projected gradient функции

`f(p)=BCE(y,σ(l0+p·h))/(ε+||h||²)+(λ/2)||p||²`.

`∇f=(σ(l0+p·h)−y)h/(ε+||h||²)+λp`; Hessian spectral norm ≤`1/4+λ`. Для feasible p, `0<η≤1/(1/4+λ)` и одного неизменного примера проекция даёт

`f(p')≤f(p)−(1/η−L/2)||p'−p||²`.

Здесь h — замороженный issue-trace, **q пересчитывается на текущей P**. Это закрывает stale-gradient нескольких задержанных receipts, но не selection bias, forgetting или общую полезность политики.

## 2. Независимая арифметика

Сумма input projections =`Vd+951d+2d²+4md`. Для F: `J[2χd²+χbd+(χ+1)d]`. Головы=`H(d+1)+V`, `H=774`; selector+wake=`(d/b)(2d+5)+33`.

| d | Input | F parameters | Heads | Selector+wake | PΘ | FP16 MiB | F MAC/full step | INT8 scheme MiB |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|512|18,050,560|4,461,568|429,830|8,265|22,950,223|43.774076|4,456,448|22.186211|
|1024|37,149,696|17,311,744|826,118|32,881|55,320,439|105.515364|17,301,504|53.130638|
|1536|57,297,408|38,550,528|1,222,406|73,881|97,144,223|185.287901|38,535,168|93.090691|
|2048|78,493,696|68,177,920|1,618,694|131,265|148,421,575|283.091688|68,157,440|142.066368|

INT8 здесь **только** схема источника: матрицы INT8 + FP32 scale на строку + FP32 vectors; не packed-runtime RAM. P требует ещё Ad чисел. Tied Etext посчитан один раз. MAC F исключает biases/активации. Реестр не содержит скрытого neural vocoder.

При d1024,K8 полная рекурренция=`138,412,032` MAC/event; 100 audio events/s дают `13,841,203,200` MAC/s **до** encoders, heads и DSP. Full vocabulary=`33,554,432` MAC/output token. Наличие малой FP16 модели не доказывает допустимую realtime мощность.

Hoeffding для фиксированной iid политики δ=.05, ε=.02 даёт ceil(log40/.0008)=4612. Для NCR paired range [−1,1], α_each=.025, Δ=.05, δ_effect=0 получены 8138 при β_each=.2 и 9457 при β_each=.1. Это совпадение арифметики не устанавливает независимость экспериментальных единиц.

## 3. Критические недоопределённости с контрпримерами

### B01 — причинный календарь событий и K_ext: требуется исправленная конструкция

`02 §8` определяет сначала δ, затем произвольное `K_ext(dΔ,dη|...)`, затем AdvanceQueue. Но явного ограничения `τ+Δ≤min(next queued timestamp,next deadline)` нет. Контрпример: сейчас τ=0, в очереди STOP на τ=1; внешнее K_ext выбирает Δ=10 и состояние мира на 10. Затем STOP обрабатывается при τ=10: событие на τ=1 уже не может запретить последствие на τ=2. Формальное pushforward остаётся probability kernel, но не является причинно согласованной системой с заявленной приоритетной семантикой.

Закрытие: календарь хранит time+priority+serial; физическая эволюция идёт до минимума ближайшего известного события, таймера и внешнего arrival; K_ext должен выдавать путь/первое arrival или согласованные competing clocks. Внутренние zero-time primitives обслуживаются перед положительным advance, причём число последовательных zero-time шагов конечное. Нельзя лечить это только сортировкой уже просроченных событий. Нужна filtration/adaptedness: δτ измерим относительно истории до τ, будущие returns не входят в наблюдения/targets.

### B02 — WHAT является нейронным событием/атомарным snapshot

Разрешены observations во время ожидания receipt, один compute-record и асинхронные work ticks. Но не полностью задано, какой `s,g,M,P` замораживается на входе COMPUTING, какой version проверяется перед publication `s'`, и допустимо ли commit P во время вычисления головы. При чтении P по строкам одновременно с транзакцией можно получить logits, не соответствующие ни одной версии P; блокировка только ledger не исключает этого.

Закрытие: immutable compute snapshot/epoch/version, single writer или versioned publication; explicit mapping вход→compute trace→proposal digest. Поздний COMPUTE_DONE после смены цели не может вернуть старое g. Все изменения shared mutable state должны иметь одну linearization/version semantics, не только trusted actions.

### B03 — прогноз до args против trace после args

Verb logit использует h, после чего args генерируются авторегрессивными событиями и меняют h/s. Gate фиксирует `h_issue`; не сказано, это h verb selection, окончательный h после args или новое encoding полного proposal. Если prediction logit вычислен на одном h, а local label применяется на другом, исходный prediction и обучение относятся к разным объектам. Кроме того, один verb «set volume» с разными targets/apps имеет разные исходы; h до генерации аргументов может их не различать.

Закрытие: сохранить `h_select` для policy log-prob, после bounded args encode полного typed proposal тем же F как отдельную фазу; прогноз `q_issue` и plastic update используют один `h_outcome` с digest конкретных args. Либо явно объявить старый q предсказанием усреднённого исхода по conditional args-policy и не приписывать ему конкретный effect-risk. Оба решения требуют учета дополнительных событий/стоимости.

### B04 — точный readback endpoint и informative censoring

«FALSE после завершения» требует определения окончания операции и окна readback. Readback сразу после async dispatch может увидеть старое значение, хотя операция завершится позже. Обратно, постусловие TRUE в один момент не доказывает его сохранение до следующей секунды. Требуются operation-specific terminal evidence, допустимая задержка, стабильность/длительность predicate и timestamp validity; без них UNKNOWN.

Второй контрпример: 50% попыток успешны быстро и дают receipt, остальные зависают/дают UNKNOWN. BCE на доступных receipts учит q→1; вероятность успеха среди всех попыток равна .5. Поэтому без MAR/positivity или дополнительного моделирования observation mechanism q оценивает `Pr(Y=1|h,a,R=1)`, где R=валидный receipt, а не безусловную вероятность успеха попытки. Это не исправляется пересчётом gradient на текущей P. Отказы/UNKNOWN обязаны входить в coverage/failure metrics; риск missingness не должен быть превращён в ложный y=0. Нужны отдельный target R, conservative utility или обоснованный censor correction.

### B05 — ticket выдаётся до неатомарного OS dispatch; crash ambiguity

Atomic markUsed+P+receipt не даёт exactly-once physical action. Возможен crash после OS effect и до durable local dispatch marker. Новый ν предотвращает старое learning, но не сообщает, было ли действие. `09 §5` правильно запрещает автоматический retry UNKNOWN, однако завершённый lifecycle требует durable PREPARED/DISPATCH_INTENT/OUTCOME journal **перед** effect, operation-specific idempotency/reconciliation и owner-visible unresolved record после restart. Очистка pending без сохранения unresolved intents теряет обязательство разбирательства. Все эти records требуют bounded quotas и pinning.

### B06 — TTS и CTC не полностью определены как последовательные трансдьюсеры

TTS SPEAK не имеет точного input-event protocol: какой internal token/frame index/previous frame поступает F, чем отличается teacher forcing от inference, как синхронизированы текст и 100 frames/s, что означает stop для chunk/utterance. В реестре нет projection 257→d; нельзя незаметно подавать предыдущую speech magnitude в аудиопроекцию d×80. Допустим fixed 257→80 DSP transform или специальный INTERNAL token и meta counter — это надо выбрать явно и посчитать.

CTC collapse должен **сначала слить соседние повторы, затем удалить blank**. Фраза `B удаляет blanks и сливает повторы` двусмысленна: a,blank,a обязано дать aa, а a,a обязано дать a. Точное определение/алфавит/normalization нужны. STFT padding/centering/window/hop/boundaries, magnitude/energy convention, Griffin–Lim phase initialization/iteration/chunk overlap также должны быть зафиксированы; иначе один и тот же tensor ABI не определяет waveform.

### B07 — memory/goal lifecycle всё ещё не алгоритм

Есть storage quotas, типы и запрет превращать hypothesis в факт. Но обычные owner-declarations/OBSERVED events не имеют полного insertion/update policy, ttl/eviction ordering, dedup, conflict representation, pin release, recovery of dangling refs. Нет полного алгоритма goal completion/deadline/decomposition/priority change, особенно при нескольких predicates и cancel. Нельзя доказать тотальность всех state transitions одной фразой «валидировать целиком», пока допустимые cross-field invariants и разрешение конфликтов не перечислены.

Конкретный цикл: все payload entries pinned незавершёнными trusted obligations, новая декларация требует сохранения; memory insert MUST определять bounded rejection и судьбу processing goal. Это допустимый failclosed, но не бесконечный eviction scan или скрытая потеря trusted obligations.

### B08 — admission stability и очередь

Finite queue и BACKPRESSURE доказывают bounded storage, не обслуживание полного аудио/событий. При λ arrivals/s≥μ service/s backlog растёт до overflow; даже λ<μ не гарантирует hard latency без burst envelope. Для гарантируемого потока нужны arrival curve α(t)=σ+λt и service lower bound β(t), либо явное dropping/coalescing с degraded-quality status. Если все 100 audio frames/s обязательны, 13.84 GMAC/s recurrence — минимальная цена выбранного K8/full-mask режима. STOP-latch должен иметь отдельный bounded polling/preemption latency. `walltime budget` не является доказательством фактического preemption primitive с неизвестным WCET.

### B09 — обучение всех Θ: targets названы, сам эксперимент не определён

Все головы имеют названный loss, что необходимо, но не достаточно: `L_grounding`, `L_retention`, data mixtures, λ, initialization, norm caps для C/Us/Ug/E, optimizer schedule, BPTT horizon и sparse schedule deployment gap не завершены численно или вычислимым protocol. Заявление «у каждого веса имеется loss» не доказывает ненулевой градиент: при detached memory future retrieval не обучает Wv/Wk, при никогда активируемом блоке его A/B/C получают ноль. Требуется connectivity+coverage ledger и warm-start dense/exploration curriculum.

Score-function identity корректна при parameter-independent environment, фиксированном support и конечной интегрируемой траектории. Если feasibility masks/teacher forcing/oracle labels обновляются из текущих Θ, нужно отделить data generation outer loop от gradient текущего fixed objective. Train каталог {zero,singletons,all} не содержит большинство runtime BudgetTop masks; качество по этим masks требуется отдельным validation/distillation. Для QAT gradients через quantizer — surrogate, а не точная производная deployed integer program.

### B10 — NCR-EVO ещё не полностью executable mathematics

E1 inclusion probabilities и fixed-pool IPW корректны для iid draws with replacement и фиксированного пула. Это не покрывает sequential multi-fidelity culling, optional stopping до фактического b, устройство/timeout censoring или training-risk на адаптивно сформированном distribution будущих поколений. Для нескольких fidelities надо логировать conditional inclusion probabilities и при нужной estimand использовать их произведение, либо не делать claim IPW correction на device labels.

DSL/type/resource checker и p=32 features пока описаны классами, без полного grammar/operators/error semantics и гарантии `H` → bounded eval. QD defaults для r=2 определены, для произвольного r формула вместимости есть, selection rule не полная. Descriptors thresholds и полезность distinct achievements требуют внешнего oracle, иначе «novelty» может стать reward hack. Ручной c0→c3 trace доказывает конкретную рекомпозицию, но не вероятность обнаружения c2 мутационным оператором.

## 4. Контракция: что действительно следует и чего не следует

При фиксированных z,Θ,масках, row-L1 constraints A≤a0,B≤b0,a0b0≤γ<1 действительно `Lip_h F≤γ`. Full leaky step имеет `c=1−α(1−γ)`. Для defaults c=.95 и c^8=.6634204313: после восьми шагов общий bound сохраняет около 66.3% начальной ошибки, а не доказывает почти точный fixed point. Residual certificate `||h−h*||≤||h−F(h)||/(1−γ)` относится к полному F.

Частичная фиксированная маска не сжимает неактивные координаты. Fair coverage proof применим только когда каждый блок обновлён за ограниченный sweep; базовый BudgetTop этого не гарантирует. Добавление численного возмущения ε на каждый из Fcov шагов даёт консервативный sweep-error `cE+Fcov ε`, stationary upper bound `Fcov ε/(1−c)`.

Нельзя переносить контракцию по h при фиксированном z на межсобытийный s. Для фиксированной памяти/цели, пусть `Lz=Lip_s z`, `β= max_j mean_l ||B_lj||∞||C_lj||∞`. Тогда полная маска, фиксированный K даёт

`Lip_s s' ≤ c^K[ρ+(1−ρ)Lz] + αβ(1−c^K)/(1−c) Lz`.

Уже Us не имеет условие, делающее этот bound <1. С чтением памяти консервативно `Lz≤||Us||∞+||Wr||∞ (√m/TM)||Wq||∞` при fixed keys/values∈[-1,1]; дополнительно меняющиеся память и goal вообще требуют новых terms. Межсобытийное bounded state сохраняется, но global convergence не доказана и не обязательна для агента.

Tradeoff: для фиксированного z contractive inner-loop имеет один attractor и не способен сохранять два точных различных fixed points; это ограничивает устойчивую bistable внутреннюю рабочую память **в этом режиме**. Это не опровержение всей архитектуры, поскольку z зависит от прошлого s, а M/Q имеют дискретное состояние. Альтернатива — finite-depth bounded noncontractive F, или contractive processing subspace + explicitly retained state, либо один shared recurrent/attention hybrid; все требуют нового tensor/resource ledger. Нельзя выбирать «достаточный» d исключительно из этих теорем.

## 5. Что сохранено и чего не заявлено

Условные доказательства bounded h/P, локального projected descent, power/IPW algebra, authority noninterference при A_cap, replay rejection при A_gen+A_tx и невозможности безынформационной регенерации не опровергнуты данным чтением. Их предпосылки существенны; отсутствие найденного контрпримера не превращается в PASS всего пакета.

Критический путь закрытия: causal event semantics → immutable snapshots/complete trace → native capability endpoints и unresolved effects → exact sequence/DSP protocol → complete training/data/calibration contract → измеримые device limits. Ресурсные/качественные числовые пороги и dataset/licenses неизвестны; нельзя заменить их выдуманными measured values.

**Frozen blind verdict: SPECIFICATION INCOMPLETE; conditional sub-results retained; production/design admission remains blocked pending corrected final-file audit.**
