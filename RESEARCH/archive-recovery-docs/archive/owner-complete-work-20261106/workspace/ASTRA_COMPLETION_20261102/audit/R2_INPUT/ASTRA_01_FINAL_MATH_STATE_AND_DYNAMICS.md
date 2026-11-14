# ASTRA 01 — UNO-B2: состояние, время и единый вычислительный цикл

Версия B2, 2026-11-02. SPECIFIED — выбранный здесь предкодовый кандидат, не утверждённая production-модель. Формальные доказательства — ASTRA_08. Полный реестр весов — ASTRA_02. Историческая B1 не является нормативной при расхождении.

## 1. Пространства и причинный порядок

Внешний мир $w\in\mathcal W$ — стандартное борелевское пространство. Наблюдение — конечная типизированная запись, а не свидетельство полномочий. Состояние

\[
X=(w,\tau,S,T,R),\quad S=(v,\Theta,s,g,\beta,P,M,Q,H_{ctx},U),
\quad T=(\nu,e,stop,owner,cap,L,D),
\tag{S1}
\]

где $s,g\in[-1,1]^d,\beta\in[0,1]^{128},P\in\mathbb R^{128\times d}$; каждая строка P лежит в L2-шаре радиуса 1. Θ и граф неизменны в runtime. R содержит конечные очереди, один активный neural work-record, таймеры, остатки ресурсов и промежуточное h. D — доверенные pending records с неизменяемым h_issue; нейросеть их не редактирует. Q≤64, M≤4096, D≤32, Hctx≤256; U,L≤8192 headers; общая очередь≤1024 headers. Данные переменной длины используют отдельный store≤4096×4096 bytes. Полное описание размеров — 05/07.

Время τ — монотонные наносекунды внутри session; wall-clock не авторизует действие. Удалённые или записанные в snapshot часы не восстанавливают deadline. Номер события t, внутренний шаг k и поколение лаборатории n различны. После reboot незавершённые планы не имеют действительного deadline/consent.

**Исправление causal clock.** Нельзя после обработки события безусловно выбрать произвольную Δ и перескочить уже поставленный таймер. Пусть $d_R\ge0$ — расстояние до ближайшего внутреннего ready/deadline/housekeeping события (∞ при отсутствии). Внешняя среда задаёт измеримое race-ядро

\[
K_{race}(dw',d\Delta,d\eta\mid w,S,T,R,u_R),\qquad 0\le\Delta\le d_R.
\tag{S2}
\]

Здесь u_R — уже сформированный предыдущим δ одноразовый outbox request, изначально NONE. Ядро потребляет его ровно один раз; δ ниже формирует следующий outbox. Поэтому в аргументе K нет неизвестного будущего a. Его η — конечный пакет внешних событий в τ+Δ; при Δ=d_R добавляются все due timers. При ready microstep (d_R=0) время не продвигается; среда может зарегистрировать новый native request и уже прибывшие marks, но не произвольно эволюционировать физический мир за положительное время. Outstanding native operations включены в w. Это совместное ядро течения мира и первого поступления, а не независимое произведение K_env×O_obs. Одновременные события сортируются STOP/REVOKE/PROCESS_DEATH → DEADLINE → READBACK → OWNER → SENSOR → INTERNAL, затем serial. Отдельный STOP-latch читается перед каждым primitive и dispatch; overflow не может его вытеснить.

После race шага полная атомарная функция

\[
(S^+,T^+,R^+,a)=\delta(S,T,\operatorname{Enqueue}(R,\eta,\Delta),head),
\quad \mathcal K(A\mid X)=\int1_A(w',\tau+\Delta,S^+,T^+,R^+)K_{race}(d\cdot).
\tag{S3}
\]

Если отправки нет, a=NONE; δ присваивает R⁺.outbox=a после потребления прежнего u_R. a — запрос, авторизованный в этой точке linearization, а не уже исполняющийся вызов. После linearization STOP не обещает отменить outbox, как и уже переданный OS request. Enqueue/δ — измеримые конечные алгоритмы с INVALID/default и bounded backpressure; при данных K_race это probability kernel. Неизвестность конкретного мира не мешает определению семейства, но исключает численный прогноз мира из одной формулы.

Идеальный belief $b'=\Pr(w'\in\cdot\mid history,\Delta,\eta)$ задаётся regular conditional probability. При плотностях $b'(dw')\propto \int K_{race}(dw',d\Delta,d\eta\mid w,\ldots)b(dw)$; нормировка по w′, нулевой likelihood → OUT_OF_MODEL. β — 128 обучаемых маргинальных факторов из data dictionary, не точный совместный belief и не доказанный фильтр Байеса.

## 2. Канонические входы и пакетизация

Все числовые поля валидируются до allocation. NaN/Inf, неизвестный enum, превышение длины → INVALID. Missing имеет отдельный бит, значение нормированного неизвестного поля равно 0 только при mask=0. Полномочия не входят в обучаемые признаки как действительный capability.

| Тип | Форма и предел | Правило |
|---|---|---|
| TEXT | UTF-8≤16384 bytes, ≤4096 tokens | V32768 с 256 byte symbols; deterministic trained tokenizer artifact; decode lossless для валидного UTF-8 |
| AUDIO | PCM16 LE mono16k Hz, ≤160000 samples/turn | 10 s; один turn≤1000 кадров по 160 samples с контекстом 512; excess → split только после явной границы/уточнение |
| IMAGE | canonical RGB uint8 256×256 | 256 патчей 16×16×3; resize с сохранением aspect и letterbox; координаты/паддинг в metadata |
| SENSOR | 32 values +32 masks | f∈[-1,1]^64; scale/unit/min/max для каждого канала в manifest |
| OS | 16 values +16 masks | f_meta, native source tag в envelope; не RECEIPT |
| INTERNAL | token / TTS frame / timer / replay tag | тот же F; provenance=internal; никогда owner автоматически |

f_meta∈[-1,1]^32: 0–3 fixed one-hot mode (perceive/generate/proposal/speak); 4–9 one-hot modality; 10–13 нормированные x,y,width,height патча (иначе 0); 14 position/(declared length or cap), 15 elapsed/turn cap; 16–23 восемь OS/context values; 24–31 их masks. OS с 16 полями подаётся двумя последовательными пакетами по 8; metadata не складывается с второй OS-проекцией. Source authentication/owner identity хранятся в envelope и gate, не выводятся из one-hot. Все позиции/clips фиксированы, нет скрытой positional embedding. Различать начало/конец/роль помогают зарезервированные TEXT токены; INTERNAL TTS использует AUDIO-проекцию с отдельным mode и e_INTERNAL.

Один neural session владеет s: в пределах ASR-turn кадры идут подряд; обычные text/image события ждут либо вызывают явную отмену turn. STOP/OS-control не ждут F. CTC-логиты разных turns не смешиваются. TTS и микрофон полудуплексны по умолчанию, barge-in сначала отменяет TTS, затем начинает новую ASR-сессию. Это одно состояние, а не набор скрытых независимых reasoning-моделей. Издержка — очередь/задержка; worst-case измеряется и включена в deadline.

## 3. Текущий вход → память → общий F

Чтобы запрос памяти учитывал текущий вход, B2 заменяет отложенный запрос B1 на

\[
z_0=\tanh(E_\tau f+U_s s+U_g g+W_{meta}f_{meta}+e_\tau+b_z),\quad q=\tanh(W_qz_0),
\]
\[
\omega_i=\operatorname{softmax}_{i\in I}\{q^Tk_i/(\sqrt m T_M)\},\quad r=\sum_{i\in I}\omega_iv_i,
\quad z=\tanh(z_0+W_rr),\quad h^0=\rho s+(1-\rho)z.
\tag{S4}
\]

T_M=1, ρ=.5 — расчётные defaults. Пустой I → r=0 (z=tanh(z0), намеренно не z0). I включает живые representation-compatible entries; HYPOTHESIS может быть контекстом только со своим kind, но не reference для Verify. Единая память не превращается в скрытую базу разрешений. Полный scan≤4096, никаких бесплатных ANN.

При b64,χ4,J2 и nb=d/b:

\[
u_{lj}=\tanh(A_{lj}h+C_{lj}z+a_{lj}),\quad
F_j(h,z)=J^{-1}\sum_{l=1}^J\tanh(B_{lj}u_{lj}+b_{lj}),
\]
\[
h^{k+1}_j=(1-\alpha M_j)h^k_j+\alpha M_j F_j(h^k,z),\quad s^+=h^K,
\quad\beta^+=\begin{cases}\sigma(W_bh^K+b_b),&\text{turn-end},\\\beta,&\text{otherwise}.\end{cases}
\tag{S5}
\]

α=.5, K≤8. Norms A row-L1≤1, B≤.9 дают γ=.9 только при фиксированном z; C≤2, прочие ограничения 02. Неактивные j **не вызывают** A,C,B kernels. C z можно кэшировать один раз на событие; цена/буфер отдельно 05. Belief-head вызывается ровно на turn-end (конец ASR/text/image session либо завершение canonical proposal); при budget shortage turn заканчивается ABSTAIN без нового β. Его 128d MAC резервируются отдельно; per-frame таблица 05 их не содержит.

## 4. Один закон conditional compute для обучения и runtime

Заранее фиксированная перестановка блоков σ_rot(j)=(j+turnSerial mod nb) mod nb зависит только отserial, не отΘ. После admission события допустимы **только непустые** prefix masks q∈{1,…,nb}. Логиты ℓ=W_M[z;s;c]+b_M, score a_q=Σ_{j<q}ℓ_{σ_rot(j)}/√q. Prefix sums стоятO(nb). Feasible catalogue содержит теq, для которых зарезервированы encoder, нужные heads, хотябыодинinnerstep, control иabort. Пустойfeasiblecatalogue означает BUDGET_ABORT, полноценный terminal failure/clarification с учётомcoverage, а не sampled q0.

\[
\pi(q)=\epsilon_s/|\mathcal F|+(1-\epsilon_s)softmax_{\mathcal F}(a_q/T_s),\quad
\epsilon_s=.05,\ T_s=1,\quad \mathcal F\subseteq\{1,\ldots,nb\}.\tag{S6}
\]

В runtime и training используется один и тот же закон sampling с записаннымPRNG seed/counter. K определяется Bernoulli hazard после каждого **выполненного** шага, 1≤K≤8; budget/Kmax принудительно останавливаютinnerloop ссохранениемhead output. Внутреннееhalt не обрывает оставшиесяaudio/textframes. Mandatory owner turns обходят learnedwake; optional ambient **turn admission** может быть отклонён Bernoulli wake наmetadata. Уже допущенная последовательность не проходитwake заново длякаждогокадра. Семантический ABSTAIN/CLARIFY остаётсяявным terminal action поитогузадачи. STOP/resourceerror могутпрерватьпоследовательность, ноэтоотражаетсявloss/coverage, ане пропадаетизdenominator.

Runtime argmax вместоsampling — другаяpolicy и требуетповторнойоценки. Этотзакон сохраняетреальныепропускинеактивныхkernels иidleрежим, но неслучайныйобрыв1000-кадровойречи. Дляfixed-zfair-sweepтеоремыK8samplingвсёещёнедостаточен.

Ресурсные c∈[0,1]^4 — normalised MAC cap, allocated workspace cap, remaining task tokens, remaining monotonic time; для gradient feasible set считается фиксированным внешним budget. Для hard deadline нельзя использовать ожидаемые latency вместо верхних bounds. Сортировка scores больше не нужна.

## 5. Цели, текст и полное предложение

Q хранит raw owner-intent, capability envelope допустимых эффектов и отдельно конечный target predicate DSL: conjunction≤16 clauses, field∈trusted schema, comparator∈{equal,in_set,closed_interval}, enum set≤128. Включение child effect envelope⊆parent capability проверяется диапазонами/множествами по каждому полю и совпадением resource. Противоречивое пересечение — infeasible. Это не требование, чтобы каждый промежуточный subgoal уже влек конечный target: конечная цель проверяется отдельно после всех шагов. Иначе необходимый промежуточный шаг мог бы оказаться ошибочно запрещён самой декомпозицией. Общая семантика русского не сводится к проверке envelope; владелец подтверждает точные чувствительные параметры.

Активная цель: max priority, min deadline, min id. При переключении g=0, её raw canonical intent заново кодируется F в режиме GOAL с s=0 и без memory-read (I=∅); затем g=h_final, рабочее s восстанавливается из единственного saved s. Кэшей g для 64 целей нет. Это ≤4096 дополнительных событий, оплаченных до допуска. Каждая decomposition node наследует оставшийся бюджет родителя; максимум 64 узла,16 steps активного плана,3 безопасных retries всего, parent deadline не продлевается. Terminals: SATISFIED (native predicate at defined time), NOOP_ALREADY_TRUE, FAILED_VERIFIED, UNKNOWN, CANCELLED, EXPIRED, CLARIFY. Все 16 clauses должны иметь evidence, иначе UNKNOWN; не требуется синхронность независимых мировых фактов без специального snapshot-contract.

На h_dec verb~softmax_schema(W_a h_dec+b_a); args/ответы идут autoregressive tied E_text с grammar mask. Максимум 128 токенов proposal,4096 текстового ответа,16 действий плана; EOS или limit, beam1. На каждом токене вызывается F. Все args затем **повторно** кодируются в canonical order тем же F с h_dec как стартовым s, отдельной ролью PROPOSAL и замороженным g. Получается h_a; до этого результата запрещено freeze trace и оценивать исход именно этого предложения. Generated proposal prefix и evaluator h_a не меняют trusted state. Возможность двух args дать одинаковое h_a остаётся capacity-risk, а не доказательство их различимости.

Дополнительная голова B2 отделяет наблюдаемость:

\[
q_R(a)=\sigma(W_R[a]h_a+b_R[a]),\qquad
q_Y(a)=\sigma((W_p[a]+P[a])h_a+b_p[a]).
\tag{S7}
\]

R=1 означает получение валидного endpoint label по протоколу; q_Y оценивает Pr(Y=1|R=1,eligible attempt features). q_R q_Y оценивает **совместное** событие «получен проверенный TRUE», не вероятность физического успеха при R=0. P влияет на решение через acceptance score log(max(ε,q_Rq_Y)) и abstention порог u_min, а не на выбор verb до знания args. Defaults: ε=10^-6,u_min=.5, risk≤.1, conf≥.5; это unapproved calibration candidates, gate от них не зависит. Допускается максимум 2 дополнительных предложения при отказе, каждый со своей полной ценой; ни один отказ не считается успехом. Ни по S7, ни по value нельзя заявлять оптимальную POMDP-policy.

## 6. Total protocol и endpoint evidence

| Фаза | Вход/операция | Следующее состояние |
|---|---|---|
| IDLE | valid owner/observation + admission | COMPUTING; иначе terminal idle/invalid/backpressure |
| COMPUTING | bounded primitive tick | следующий tick; либо DECODE_DONE→PROPOSED; quota/NaN→ABSTAIN |
| PROPOSED | canonical schema/intent/prestate | AWAIT_CONFIRM или READY; invalid→DENIED |
| AWAIT_CONFIRM | exact digest-bound owner consent | READY; timeout→EXPIRED |
| READY | durable PREPARED ticket; live gate повторно | DISPATCHED или DENIED; fs failure→SAFE_MODE |
| DISPATCHED | native return | WAIT_READBACK; rejected-before-effect→DISPATCH_FAILURE; uncertain→WAIT_READBACK |
| WAIT_READBACK | native endpoint sample | COMMITTING либо UNKNOWN; deadline→UNKNOWN |
| COMMITTING | guarded atomic receipt+P+used | TERMINAL; failure→old state+SAFE_MODE |
| TERMINAL | release bounded refs | IDLE; pinned unresolved operations остаются в reconciliation L |
| любая | STOP/revoke/process death | epoch invalidation; CANCELLED; already dispatched effect не отменён |
| любая | malformed/replay/wrong phase | INVALID без оживления work |

Каждый вход в COMPUTING создаёт TICK; tick создаёт следующий tick или DONE; READY создаёт DISPATCH_REQUEST; WAIT_READBACK создаёт QUERY; COMMITTING создаёт COMMIT_REQUEST; TERMINAL создаёт RELEASE. Returns создаёт OS, не нейросеть. DEADLINE есть для всех незавершённых work records, включая confirmation и computation. Внешний вызов всегда asynchronous с bounded request queue. Предыдущие work cookies отвергаются.

Ticket identity=(ν128,e64,serial64,v Digest,proposalDigest). Выбор ν и rollback-threat в 05; overflow счётчиков → SAFE_MODE. Перед dispatch journal PREPARED durable, затем live linearization gate. Crash между journal и OS означает MAY_HAVE_EXECUTED; никогда автоматический повтор неидемпотентного действия.

Endpoint schema фиксирует **что и когда** проверяется: например GET_VOLUME(stream) на первом native sample в [dispatch-return,deadline) с source generation и token, predicate=value target. FALSE означает ложность predicate в этом sample, не «никогда не достигалось». Callback сообщает только доступный контракт API. Unknown/partial/interference не подменяются ложным результатом. Deadline в тот же timestamp имеет приоритет; post-deadline sample не даёт прежний credit. Поле attribution отдельно OBSERVATIONAL/CONTROLLED/UNKNOWN; q_Y и M не объявляют причинного do-эффекта.

Commit допустим только при active unused ticket, current ν/e/model/goal/consent, valid endpoint timestamp, now<deadline, !STOP. h_issue=каноническое h_a, FP32 freeze, P пересчитывает q на текущей строке. Used flag, receipt, P-version и M-reference фиксируются одной транзакцией. UNKNOWN/STOP/denied/replay не меняют P. Offline observability-head может обучаться на полноценном протоколе attempts, но отменённые/неопределённо восстановленные попытки имеют censor flags и не становятся Y=0.

## 7. Завершение и его предел

При admission work фиксирует immutable snapshot (v,Θ,s,g,M-reference set,P-version,budget,ν/e,goal-version) и отдельный workCookie. Внутренние ticks используют только его и локальные промежуточные состояния. Receipt другого действия может атомарно изменить global P/M, но не прочитанные tensors текущего work: copy-on-write/pinned refs оплачены в 05. Перед публикацией s/β/proposal контроллер сверяет workCookie,ν/e,v и goal-version; obsolete work отбрасывается. Gate проверяет текущие OS/preconditions заново. Для P-update q вычисляется по текущей P с frozen h_issue, а не по snapshot P. Так исключена смесь версий посреди матричного вычисления.

При конечных cap, локально конечных внешних arrivals и справедливом обслуживании контроллера каждый work имеет конечное число primitives/token/attempts и deadline. Ранг=(remaining attempts,remaining tokens,remaining inner steps,remaining primitive instructions) убывает в лексикографическом порядке между внешними ожиданиями; ожидание прекращается deadline. Зависимость от fairness/реального обслуживания таймера существенна. В идеальном reactor результат terminal достигается; в Android walltime≤deadline+L_control лишь после измеренного/обеспеченного L_control. Без допущения scheduler progress процесс может быть остановлен ОС навсегда. Никакой теоремы завершения всех будущих внешних задач или отмены физических последствий нет.
