# R1 — независимый adversarial re-audit frozen UNO B2

Дата 2026-11-02. Объект: `audit/R1_INPUT/` — все 12 авторских Markdown-файлов 00–09,11,12, `tensor_manifest_d1024.json`, `arithmetic_v2.json`, `recompute.py` (только чтение). Author documents не редактировались. Предыдущие BLIND_AUDIT/CROSSCHECK_PRIOR_AUDIT сохранены. Этот отчёт фиксирует первый re-audit; он **не** финальный verdict последних файлов.

Полные 12 документов прочитаны; усечённые объединённой выдачей конец09/начало11 отдельно дочитаны. Независимый Python использован только для целочисленного суммирования форм, packing/ресурсов и арифметики вероятностей; авторский recompute.py, модель, тренировка, Android и NCR поиск не запускались. Для найденных defects точечным чтением проверены текущие rootdocs; некоторые прежние уточнения уже внесены, но перечисленные ниже существенные пункты в момент сообщения автору оставались.

## Вердикт R1

**FAIL полноты/согласованности draft B2:** обнаружены исправимые ошибки stochastic admission, training estimand/coverage, статуса allocated/free parameters и статистического порога. Проверенные локальные proofs/counts ниже сохраняются в своей области. Этот FAIL не является утверждением, что вся архитектура невозможна.

## R1-01 — обязательная вероятность abstain на каждом frame/token разрушает длинный stream

**FAIL, высокий приоритет.** `01 §4 S6`: admissible prefix catalogue включает q=0, uniform exploration ε=.05 распределяется по всем feasible masks, q=0 сразу ABSTAIN. Этот selector применяется на каждом нейронном событии; audio/TTS имеют до1000 events, ответ до4096tokens.

Даже если logits идеально предпочитают вычисление, `Pr(q=0|history)≥ε/(nb+1)` (если часть masks infeasible, нижняя граница только возрастает). При semantics «ABSTAIN прерывает текущую задачу/turn» вероятность завершить L обязательных событий без такого отказа не превышает

`Pr(complete L)≤∏t(1−Pr(qt=0|survived history))≤(1−.05/(nb+1))^L`.

Независимость draws для этого upper bound не нужна: достаточно указанной conditional lower bound на каждой истории.

| d / nb | ε/(nb+1) | Верхняя вероятность без abstain, L1000 | L4096 |
|---|---:|---:|---:|
|512 /8|.00555556|.00380650|1.2298·10^-10|
|1024 /16|.00294118|.05257523|5.7586·10^-6|
|1536 /24|.002|.13506452|.00027460|
|2048 /32|.00151515|.21952251|.00200770|

Следовательно данный закон несовместим с высокой completion/coverage длинных обязательных streams даже при идеально обученных logits. Если q0 означает не abort, а пропуск отдельного frame, спецификация не определяет, какие CTC/TTS logits/waveform вместо отсутствующего forward выдаются и как это влияет на protocol; это другой алгоритм, не закрытие дефекта молчанием.

Минимальное исправление: один turn-level admission с допустимым ABSTAIN; после admission mask support `{1,…,qmax}` для каждого обязательного frame/token, тот же закон train/runtime. STOP/quota/NaN всё ещё могут прерывать с explicit incomplete status. Если хочется обязательной stochastic exploration отказа, исследовать её только на whole-turn уровне и заранее учесть ceiling coverage. Не «исправлять» epsilon→0 только при runtime: это снова незаявленный policy shift.

## R1-02 — objective не определяет потерю за terminal отказ/неполный output

**FAIL определения complete objective.** `03 L3` содержит нормированные supervised losses по наличию valid targets и cost; при q0 никаких output heads не вычисляется, а отдельного terminal failure/coverage loss не определено. Наличие target в датасете и наличие вычисленного model output — разные masks. Отказ модели не должен делать target «отсутствующим».

Контрпример допустимой буквальной реализации: один размеченный task, compute даёт CE L>0 и cost c>0; q0 возвращает ABSTAIN, число полученных output targets ошибочно считается0, поэтому loss0 и cost0. Expected objective `p_compute(L+λc)` строго улучшается при уменьшении p_compute. Heldout coverage gate предотвращает release такого агента, но не превращает J в задуманную обучающую задачу.

Закрытие: задать bounded terminal task score/loss для каждого issued task, включая missing required output, timeout и unauthorized action; q0/aborted sequence получает этот loss в score-function cost-to-go. Missing-data masks вычисляются из corpus/evidence, **до** compute sampling, и не отменяются модельным refusal. Можно использовать task-specific bounded score и hard training constraint/dual update, но его units/coefficient/range должны быть явно заданы. Не маркировать UNKNOWN как false physical Y ради штрафа: operational completion loss и outcome BCE — разные targets.

## R1-03 — A128 allocation не равно 128 обучаемым строкам в closed24verb schema

**FAIL утверждения «все скаляры медленные trainable»; arithmetic allocation PASS.** `02 §2` называет все W2 scalar trainable и все строки jointly trained; `05` разрешает verbs0–23 и навсегда маскирует24–127 RESERVED_DENY. Для masked softmax запрещённая строка W_a,b_a не участвует в нормировке, её derivative идентично0. W_p,W_R строки24–127 не получают eligible attempts, а verbs0–2 ABSTAIN/CLARIFY/NOOP не имеют action-success labels по прямому правилу каталога. Это не исправляется придумыванием denied→Y0.

Минимальное честное закрытие:

- `Θ_alloc` — все сохранённые scalar slots с W2 count, worst-case bytes остаются.
- `Θ_free` — trainable coordinates; W_a/b_a rows0–23, W_p/b_p/W_R/b_R rows3–23 только если каждый из этих21 verbs действительно имеет определённый observable endpoint protocol. Остальные строки fixed zero и enforced before export; optimizer их не обновляет.
- P allocated128×d, active21×d, остальные fixed0; не назвать unused values обученными.
- Feature-specific heads без label dataset остаются data-blocked, а не получают фиктивные labels. Общий F/encoders реально обучаются совместно на активных задачах.

Если endpoint eligible set E={3,…,23}, фиксировано `104(d+1)+2·107(d+1)=318(d+1)` slow coordinates:

|d|Allocated W2|Free under E3–23|Active P scalars|
|---:|---:|---:|---:|
|512|23,015,887|22,852,753|10,752|
|1024|55,451,639|55,125,689|21,504|
|1536|97,340,959|96,852,193|32,256|
|2048|148,683,847|148,032,265|43,008|

Это **coordinate count**, не число идентифицируемых функциональных степеней свободы: softmax common shifts/hidden permutations сохраняют nonidentifiability. Если E меньше21, формула общего случая: `P_free=P_alloc−(A−|V_active|)(d+1)−2(A−|E|)(d+1)`. Форму manifest/память можно оставить прежней, но fields must distinguish allocated/trainable mask/fixed values. Проверка nonzero gradient для целого tensor слишком слабая, чтобы подтвердить каждый allocated element.

## R1-04 — detached P не делает derivative точной производной обычного J

**FAIL заявленной exactness при буквальном replay текущих Θ внутри сегмента.** `03 §3` одновременно говорит: replay P из0 с updates, derivative через updates не считается, L5 точна для frozen-state objective на сегменте. Если значения P при каждом evaluation пересчитываются из текущих Θ, это не frozen function argument. Stop-gradient — определение semi-gradient, а не доказательство ordinary derivative E[L].

Простейшая математическая аналогия: `p(θ)=θ`, `L(θ,p)=(θ+p)^2`. Реальная `dL(θ,p(θ))/dθ=8θ`; detached-p differentiation даёт4θ. Назвав p «замороженным» только в backward, нельзя изменить значения objective L(θ,p(θ)) в соседних θ. В actual P1 зависимость через l0/h обычно также ненулевая.

Закрытие A: в начале outer iteration зафиксировать reference `barΘ`; воспроизвести P traces **целиком по barΘ**, frozen data/trace store, затем определить `J(Θ;barP)` с barP независимой от дифференцируемой Θ и discrete decisions внутри рассматриваемого segment; L5 exact для этого surrogate, outer alternation не exact gradient полного runtime objective. Закрытие B: сохранить dynamic replay, честно именовать resulting update semi-gradient с bias, не PASS exactness. Само identity L5 верно для полного differentiable path; ошибка в заявлении, что detached replay удовлетворяет её premises.

Замечание относится также к stateful normalizers, adaptive oracle targets или памяти, если значения повторно пересчитываются на текущих Θ, а соответствующие derivatives отбрасываются. TBPTT/STE уже честно маркированы biased и не являются этой новой ошибкой.

## R1-05 — statistical power для δ0 не соответствует practical gate δ.02

**FAIL общего power claim для финального practical decision.** `06 E6` использует true Δ=.05, null δ=0, α_each=.025, β_each=.1 и даёт n9457. Ниже положительное заключение требует `LCB>.02` для обеих comparisons. Для этого threshold denominator должен быть `(Δ−.02)^2=.03²`:

`n≥ceil[2(√log40+√log10)^2/.03²]=26,268`.

n9457 действительно даёт ≥.8 joint power для **mere positive** effect>0; не даёт ту же guarantee для practical>.02. Можно оставить две строго разные preregistered claims со своими sizes; нельзя использовать cheaper positive-effect power как сертификат practical acceptance. Если α делится ещё между адаптивными finalists/checkpoints, подставить фактическое α_j/2; тогда 26,268 тоже не универсальное число для всех rounds. Если trueΔ≤δ practical, данная power формула неприменима как finite sufficient detection size.

## R1-06 — сложение peakRAM/disk не является общей стоимостью в E5

**FAIL resource equality as written.** E5 суммирует per-candidate costs и называет результат vector(CPU-seconds,joules,disk,peakRAM). CPU work/энергия/bytes written аддитивны; peak resident RAM и peak live storage — max/sup по времени сумм одновременно живых allocations. Две последовательные оценки с workspace1GiB каждая не дают actual peak2GiB; параллельные дают2GiB плюс shared buffers.

Закрытие: отделить additive `(CPU_time,total_joules,IO_bytes,currency)` от capacity constraints `R_peak=sup_t Σlive_i bytes_i(t)` и `D_peak=sup_t retained_bytes(t)`. Можно использовать сумму всех workspace bounds как **консервативный upper bound**, но не равенство C_total измеренному peak и не скалярный speedup на этом векторе. Условие break-even `(N−K)D>F+O` корректно для одной выбранной аддитивной единицы с consistent full-eval baseline.

## R1-07 — меньшие обязательные уточнения и уже изменённые rootdocs

1. Frozen `01 S5` обновляет β на каждом event, тогда как `05` считает β optional turn-end и таблица исключает128d. Current root уже уточнён автором; требуется final reread точной нормативной формулы, а не просто примечания.
2. Frozen GL говорит «crop exact160F samples» без индексов; из causal frame start−352 следует, что нужен crop `[0,160F)` координат восстановленного сигнала, а не первые160F samples массива, начинающегося в−352. Current root final crop должен фиксировать также STFT reanalysis support/left padding каждого GL шага. Это indexing closure, не заявление, что Griffin–Lim гарантирует intelligibility.
3. Frozen N65 «DSL завершён» сильнее некоторых отсутствующих численных fuel/workspace caps и robust descriptor thresholds. Author сообщил добавление fuel10^7/workspace16MiB и bins в current root; подтвердить final bytes. Полнота общей grammar implementation всё равно ограничена перечнем exact primitive semantics, checked arithmetic и входным finite contract.
4. Unicode ASR inventory **арифметически** даёт128 slots: blank+space+33RU+26Latin+10digits+32ASCIIpunct+24extras+UNK. Строка extra реально имеет24 chars. NFC/lowercase normalization должна быть versioned; редкие Unicode lower expansions/unsupported symbols дают declared UNK, а не silently different alphabet. Это не найденная count error.

## Проверенные PASS конкретных claims

Здесь PASS означает проверенное утверждение в названной области, не отсутствие любых ошибок.

|Claim|Вердикт и evidence|
|---|---|
|W2 allocated counts|PASS независимого суммирования; manifest198 tensors суммируется в55,451,639; все4d совпадают|
|Mixed INT8 d1024 bookkeeping|PASS для указанной схемы/align: unpadded55,843,608; packed55,873,984bytes, не runtimePSS|
|F MAC и path table|PASS для uncached full memory scan/head schedules, β отдельно: text175,448,160MAC/event; ASR14,210,672,000MAC/s приd1024|
|Resource partial subtotal|PASS арифметики: state22,880,768bytes,W6,471,296; rawFP16subtotal133.757917MiB; плюс.25+.25+2.75+8=145.007917MiB; named backend/capture/staging исключены явно|
|L7 stored activation expression|PASS подстановки4BL{…}:542,113,792bytes, не upper bound arbitrary autodiff implementation|
|P1/P2|CONDITIONAL PASS: current row q, frozen FP32 h, η≤1/(.25+λ), Euclidean feasible projection; доказательство в04 корректно|
|P3 realized-loss regret|CONDITIONAL PASS для bounded convex f_t и comparator на той же реализованной loss sequence; не policy regret|
|S4 tensor compatibility|PASS: текущий input входит z0→query, output memory read d; no hidden trainable projection|
|S2/S3 outbox typing/causal clock|CONDITIONAL PASS как abstract kernel: old outbox потребляется средой, новый formδ, supportΔ≤dR; external causal race/progress assumed, real OS не tested|
|Immutable compute snapshot|SPECIFIED coherent single-writer/COW contract; runtime evidence absent|
|qR/qY factorization|PROVEN conditional identity `P(R,Y1|H)=P(R|H)P(Y1|R,H)`; не физический success приR0 и не causal effect|
|Fixed z contraction|CONDITIONAL PASS γ.9,c.95; finite K8 residual factor .6634204313, global event contraction не заявлена|
|CTC order, TTS80 feedback|PASS математических размеров и collapse order; DSP coordinates требуют R1-07 final closure|
|NCR finite-pool IPW|CONDITIONAL PASS для declared fixed pool, b draws, observed labels, fixedφ; calibration pool distinct, no arbitrary multi-fidelity extrapolation|
|NCR E6 algebra at δ0|PASS9457 for declared independent paired units and two comparisons; practicalδ.02 needsR1-05|
|c2/c3 manual algorithm proof|CONDITIONAL PASS prefix maximum/current-context intact certificate; search discovery/superiority не следует|
|Nonce birthday bound|CONDITIONAL PASS P128, honest no-zero-probability claim; hardware antirollback не предположен|

## Требования к следующему reread

Автор должен сохранить R1_INPUT/R1_REVIEW без подмены; дать новый frozen snapshot/manifest. Проверить все R1-01–06 по уравнениям, metadata/free-count evidence, loss definitions и матрице M33/M34/N50/N54/N67, включая blueprint/oracles. Пересчитать новые free counts и practical power. Затем отдельно фиксировать SHA-256 последних audited author files. Никаких итоговых FORMAL_PASS сейчас: новые противоречия должны быть закрыты либо оставлены конкретными blockers.
