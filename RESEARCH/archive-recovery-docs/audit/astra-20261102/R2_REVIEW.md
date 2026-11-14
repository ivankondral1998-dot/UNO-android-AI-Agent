# R2 — независимое повторное чтение исправленного UNO B2

Дата: 2026-11-02. **Вердикт R2: FAIL для окончательной согласованности спецификации**, из-за четырёх оставшихся/новых конкретных замечаний ниже. R1-01,03,04,05,06 закрыты в своей математической области; R1-02 получил terminal loss, но новая per-stratum constraint записана неверно. Ни SPECIFIED, ни проверка арифметики не считаются empirical PASS.

## Точный scope

Полностью перечитаны все 15 Markdown-файлов frozen `R2_INPUT` (00–12, FINAL_README, REVISION_LOG), весь `recompute.py` только как текст арифметического скрипта, `arithmetic_v2.json`, все tensor/free-mask records JSON. Hash-bound scope: `audit/R2_INPUT/MANIFEST.json`, SHA-256 **f77357d5fa71b7b239205d763f685bf899068735bf27e619ce2028751c1a8c3c**. По нему независимо сверены bytes/SHA всех18 файлов, несовпадений0.

Автор заменил только arithmetic script/fast-P metadata перед их чтением и сообщил новый manifest; normative equations/docs не менялись. Именно последний manifest выше является входом данного заключения. Усечённый объединённой выдачей участок03 был перечитан отдельно (строки1–60). Author/root documents не редактировались. Независимые Python операции ограничены hashes, суммами размеров и scalar arithmetic; author script, модель, тренировка, Android и NCR не запускались. Внешние Android/API ссылки в этом model review заново не проверялись; их provenance принадлежит авторскому чтению.

## Проверка закрытия R1

|R1|Результат R2|Основание и предел|
|---|---|---|
|01 per-event q0|CLOSED, SPECIFIED|S6 support только q≥1; optional wake один раз наturn; mandatory owner bypass; hard resource/STOP abort остаётся явным failure|
|02 refusal objective|PARTIAL, новая ошибка R2-01|Terminal U/Ltask теперь существует, data masks не стираются отказом; per-stratum dual несогласован с mixture expectation|
|03 allocated/free|CLOSED, арифметика PASS|24verb rows,21endpoint rows, остальные0; Pactive21d; manifest masks/init/optimizer/restore/export согласованы|
|04 detached P exactness|CLOSED, CONDITIONAL|Offline P=0 фиксирована, не пересчитывается текущимиΘ; onlineP и runtime-adaptation evaluation отдельны; TBPTT/STE biased явно|
|05 practical power|CLOSED, CONDITIONAL|9457 дляδ0,26268 дляδ.02 при trueΔ.05, α_each.025/β_each.1; при spending используются фактические α, размер не переносится автоматически|
|06 peak sum|CLOSED|E5 additive CPU/J/IO; RAM/disk sup live, walltime makespan; release physical bounds всё ещё требуют измерений|

Turn-end β теперь нормативно указан в S5 и резервируется128d отдельно. GL crop/reanalysis использует физические t∈[0,160F), negative padding восстановлен на каждом анализе; это закрывает индексную неоднозначность, а не доказывает speech quality. CTC order merge-then-removeblank, alphabet count128 и versioned NFC/lowercase/UNK protocol согласованы. NCR fuel10^7/workspace16MiB,64 descriptor cells, отдельный calibration pool и bounded ancestry теперь заданы. Arithmetic script portable из deliverable/evidence к deliverable/sources; frozen copy в audit предназначена для чтения, не самостоятельного запуска из другой layout.

## R2-01 — coverage Lagrangian использует joint probability вместо условной доли в stratum

**FAIL математического соответствия L3a/dual целевой coverage.** 03 выбирает task group случайно из mixture. В L3a стоит `E[Σ_j μ_j(1_abort,j−(1−c_j))]`. Если `1_abort,j` — индикатор abort задачи из группы j, его ожидание равно `p_j P(abort|J=j)`, а не условной доле. В dual update ниже используется observed_abort_rate группы, то есть другой constraint.

Контрпример: 12 равновероятных групп, для одной c_j=.9 и всегда abort. Тогда E[1_abort,j]=1/12≈.0833≤.1, написанный constraint удовлетворён, хотя coverage данной группы0 вместо.9. Это не устраняется наличием terminal penalty: penalty и hard stratum constraint — разные части objective.

Варианты точного исправления:

1. `g_j(Θ)=E[1_{J=j}(abort−(1−c_j))]≤0`, p_j>0; dual increment — batch estimator именно этого joint centered quantity. Он эквивалентен conditional constraint по знаку, но масштаб зависит p_j.
2. При фиксированном известном p_j>0 использовать `E[(1_{J=j}/p_j)(abort−(1−c_j))]`, dual increment той же величины. Тогда g_j=conditional abort−budget.

Определить J как stratum, а j loss-index переименовать, чтобы не смешивать сумму supervised loss heads и task groups. Для отсутствующей группы p_j=0 требование нельзя назвать обученным/оценённым.

Дополнительно фраза «zero-task-loss trajectory с cost≤.1 лучше abort loss1» справедлива для **terminal+cost части** или при равных остальных losses, а не автоматически для полного J с дополнительной CE/aux loss. Не заявлять глобальное предпочтение полного objective без этого условия; hard coverage gate и отсутствие global convergence уже корректно оговорены.

## R2-02 — log-score threshold и internal verbs не имеют полного dispatch-free branch

**FAIL/недоопределённость точного acceptance rule**, `01 §5 S7`.

Score задан `u=log(max(ε,qR qY))`, threshold `u_min=.5`, но сравнение не записано. u≤0, поэтому буквальное `u≥.5` никогда не проходит. Если intended threshold относится к вероятности, необходимо явно `qR qY≥.5`, эквивалентно `u≥log(.5)` при ε<.5. Формулы должны определять одну policy, а не оставлять это разработчику.

Кроме того, `02` теперь фиксирует outcome rows0–2 равными0. Их sigmoid=.5, product=.25. Если общий acceptance rule применяется к ABSTAIN/CLARIFY/NOOP, все они отвергаются threshold.5 и инициируют бессмысленный retry, хотя не имеют outcome labels и не должны dispatch/учить P. Явно задать branch для internal0–2: terminal semantic output (NOOP только с проверенным pre-predicate), без qR/qY scoring, ticket/OS effect и online update. Outcome acceptance applies лишь E3–23; unsupported/reserved rows DENY.

Это не опровержение probabilistic factorization qR qY, которая остаётся верной для declared endpoint conditioning.

## R2-03 — generic UI_TYPED_ACTION обходит обещанный запрет классов effects

**FAIL категорического effect-exclusion claim в05**, а не опровержение capability induction при правильно ограниченном gate.

Текст утверждает, что purchases/messages/calls/accounts/financial actions отсутствуют в ABI и не могут быть сгенерированы. Однако verb23 разрешает generic `UI_TYPED_ACTION(nodeId,op,args)` для allowlisted package/node snapshot; явно исключены password fields, но не downstream effects. Контрпример в этой абстрактной модели: разрешённый node является кнопкой Send или Buy; op=click проходит описанные schema/gate checks и вызывает запрещённый эффект. Отсутствие отдельного verb BUY не устраняет возможность его композиции через generic click.

Для сохранения запрета ограничить verb23 effect-level allowlist: только known instrumented/local surfaces и операции с независимо проверенным contract конечного разрешённого effect; unknown/unclassified business effect → DENY. Package/node allowlist сам по себе не доказывает этот контракт. Либо честно ослабить product claim и требовать informed owner authorization на такие эффекты, но это изменение scope, а не доказательство их невозможности.

Gate должен проверять effect-class/refinement по trusted manifest, не по заявлению нейросети или строке label кнопки. Новые app versions/node semantics требуют revalidation, иначе stale effect mapping снова допускает counterexample.

## R2-04 — asynchronous clause evidence не доказывает current conjunction

**FAIL/недоопределённость временной семантики goal DSL**, `01 §5`: target — conjunction clauses, SATISFIED по native predicate в определённое время, но затем «не требуется синхронность ... без специального snapshot-contract».

Если intent означает `A(t*) AND B(t*)` в одном текущем endpoint, отдельные TRUE при разных временах недостаточны. Контрпример: A=true,B=false приt1; затем A=false,B=true приt2. Два authentic valid samples удовлетворяют каждый своей clause, но ни одного момента с A∧B нет. Independence источников/факторов не является persistence во времени.

Закрытие: сделать temporal operator частью trusted goal schema. Например OCCURRED_ALL означает «для каждого j существует свой t_j в interval», CURRENT_ALL требует общего snapshot/epoch либо explicit stability certificates, переносящих каждую clause на общийt*. HISTORICAL/OCCURRED не выдавать за текущую цель. При отсутствии joint evidence CURRENT_ALL→UNKNOWN, не SATISFIED. Owner confirmation/canonical goal text должны содержать это различие. Семантика step success и final conjunction остаётся раздельной.

## Независимая арифметика и сохранённые теоремы

Проверены JSON shapes/products/free-mask partition всех198tensors: allocated55,451,639; free55,125,689; fixed325,950. Fast active rows3…23:21,504 координаты при allocated131,072. Формулы четырёхd и LR/H2 remain согласованы; allocated не объявляется числом содержательно обученных координат. Nonidentifiability мягко не смешана с coordinate freedom.

Power practical самостоятельно пересчитана:26268. Дополнительные fixed-data allocations самостоятельно пересчитаны: tokenizer8,781,828bytes, DSP89,024bytes, output buffers8192bytes. Новый explicit subtotal d1024FP16=153.475633621MiB, до named capture/backend/controller/driver/snapshot extras. Это не measured PSS.

Сохраняются условные доказательства: bounded state и rowP; fixed-z contraction/fair sweeps; P1/P2 descent/P3 realized losses; finite-pool E4 IPW для fixedφ/observed labels; c2/c3 prefix-max/current certificate; authority induction при A_cap и **правильно заданном effect scope**; atomic no-replay при A_tx и freshν, P128 conditional no-collision. S2/S3 causal outbox/race типизирован и ограничен ближайшим таймером; real OS/progress остаётся предпосылкой. Эти sub-results не доказывают полноту продукта.

## Следующий reread

R2 frozen и этот отчёт не менять. Дать R3 manifest после исправления R2-01…04, включая согласованные 01/03/05/07/08/09/11 и окончательный status/report. Затем reviewer перечитает изменённые normative contracts и весь final narrative, сверит hashes и явно укажет, какой набор последних файлов покрыт заключением. Сейчас N72/final PENDING корректны; итоговый общий FORMAL_PASS не установлен.
