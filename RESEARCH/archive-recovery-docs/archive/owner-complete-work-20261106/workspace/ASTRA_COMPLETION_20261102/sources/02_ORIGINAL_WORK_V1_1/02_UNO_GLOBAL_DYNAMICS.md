# 02. Полная динамика организма

Все формулы — спецификация, не уже написанный runtime. События обрабатываются последовательно в доверенной точке фиксации; нейронная работа может прерываться. При конечном наборе событий равного времени приоритет: STOP/REVOKE/RESTART → DEADLINE → RECEIPT → OWNER_INPUT → прочие наблюдения. Совпадение receipt с deadline даёт TIMEOUT. Бесконечный Zeno-поток запрещён предпосылкой конечности событий на ограниченном интервале; переполнение очереди даёт BACKPRESSURE.

## 1. Частичная наблюдаемость

\[
w_{t+1},\Delta_t\sim K_{\rm env}(\cdot|w_t,a_t),\quad
o_{t+1}\sim O_{\rm obs}(\cdot|w_{t+1}).
\]

Для известных ядер идеальный belief обновлялся бы:

\[
b^-(dw')=\int K^W_{\rm env}(dw'|w,a)b_t(dw),\qquad
b_{t+1}(dw')=
\frac{O_{\rm obs}(o_{t+1}|w')b^-(dw')}
{\int O_{\rm obs}(o_{t+1}|u)b^-(du)}.
\]

Здесь K^W_env(A|w,a)=K_env(A×R_+|w,a): Δ маргинализирована. Если прошедшее время информативно, posterior надо условить на наблюдённой Δ, используя совместное K_env(dw',dΔ|w,a) и нормировку по w'. Это запись для случая существующих плотностей. При нулевом знаменателе событие OUT_OF_MODEL, posterior не определяется этой дробью. В общем случае используются условные меры на стандартных борелевских пространствах. Реальная UNO вместо неизвестного b хранит β=σ(W_b h+b_b) и provenance наблюдений. Никакая теорема точного Bayesian inference для β не заявляется.

Поскольку мир неизвестен, задать его численное ядро из handoff нельзя. **Глобальный transition kernel — семейство**, параметризованное K_env,O_obs, trusted OS-контрактами и Θ. Для заданных членов семейства переход ниже тотален; качество в неизвестном мире из тотальности не следует.

## 2. Наблюдение → вычисление

Валидатор V_obs либо возвращает ограниченное x, либо INVALID. Дешёвый admission использует тип события, метаданные, owner-задачу и остаточный бюджет; нулевой текстовый/сенсорный вектор не означает отсутствие задачи.

\[
q=\tanh(W_q(s+g)),\quad
\omega_i=\frac{\exp(q^\top key_i/(\sqrt m T_M))}
{\sum_{j\in \mathcal I}\exp(q^\top key_j/(\sqrt m T_M))},
\quad r=\sum_{i\in\mathcal I}\omega_i value_i.
\]

T_M>0 фиксирована. Пустой M даёт r=0. I выбирается только среди provenance-допустимых записей; stale записи могут быть контекстом с явным возрастом, но не свежим native readback. Поиск базово полный, до M_max; ANN не подразумевается. Для nonempty I знаменатель положителен; softmax считается с вычитанием максимума.

\[
z=\tanh(E_\tau f_\tau+U_s s+U_g g+W_r r+
W_{\rm meta} f_{\rm meta}+e_\tau+b_z),\quad
h^0=\rho s+(1-\rho)z.
\]

Для TEXT Eτ fτ — lookup строки общей embedding; для AUDIO/IMAGE/SENSOR — проекции из 03; для OS используется W_meta и fτ=0. Не дублировать метапроекцию OS дважды.

Выбор блоков до внутреннего цикла:

\[
\ell^M=W_M[z;s;c_{\rm norm}]+b_M,\quad
\mathcal B=\operatorname{BudgetTop}(\ell^M,C),
\quad c_{\rm norm}\in[0,1]^4.
\]

BudgetTop сортирует блоки по score с устойчивым tie; учитывает цену сортировки и резерв выходов. Вариант отказа — пустое множество, K=0 и ABSTAIN, а не случайное исполнение. Маска зафиксирована на время одного inner-loop. Динамическая маска от h — отдельная гипотеза без доказательства общей контракции.

## 3. Один нейронный оператор

Разбить координаты на n_b блоков по b. Для каждого блока j и ветви l=1…J:

\[
u_{lj}=\tanh(A_{lj}h+C_{lj}z+a_{lj})\in\mathbb R^{\chi b},
\quad f_{lj}=\tanh(B_{lj}u_{lj}+b_{lj})\in\mathbb R^b,
\quad F_j(h,z)=J^{-1}\sum_l f_{lj}.
\]

\[
h^{k+1}_j=
\begin{cases}
(1-\alpha)h^k_j+\alpha F_j(h^k,z),&j\in\mathcal B_k,\\
h^k_j,&j\notin\mathcal B_k .
\end{cases}
\tag{D1}
\]

Эквивалент исходного эскиза: R=α(F−h), h'=h+D_M R. Это **исправление** необусловленного residual h+R. Все ветви — совместные нелинейные части одного F; каждая не является отдельным агентом.

Базово B_k=B. K ограничивается K_max=8 и фактическим остатком бюджета; learned halt σ(w_halt^T h+b)>τ_h может остановить раньше. При K=0 s'=h^0. После K шагов s'=h^K; β' обновляется доступной головой. Это вычислительное состояние, не подтверждение физического мира.

Изолированная fixed-point теорема относится к неизменным z,Θ и общей справедливой последовательности масок; базовая разреженная B может не покрыть все координаты. Поэтому production-предложение после конечного K не объявляется fixed-point решением.

## 4. Целеполагание и выбор действия

Owner-ввод сохраняется в Q с raw-текстом и авторством. Нейронная декомпозиция создаёт подцели только внутри предиката и лимитов родителя. Подцель, расширяющая intent, требует нового owner-ввода; expiry аннулирует старый intent.

При завершении OWNER_GOAL_ENCODE g'=h^K; до завершения g прежний. Активная цель выбирается по (priority убыв.,deadline возр.,id возр.); при смене g загружается из записи цели или её текст заново подаётся тому же F. При terminal цели g=0 до выбора следующей. Самосозданная цель без ownerIntentRef остаётся HYPOTHESIS.

OwnerIntentRef ссылается на capability с ограниченным эффектом. Декомпозиция доказывает refinement только в конечном goal-DSL (≤16 conjunctive enum/range/typed-field ограничений). Для произвольной естественной речи полного семантического доказательства соответствия намерению нет: модель предлагает интерпретацию, и эффект за пределами ранее данного capability требует подтверждения точных параметров. Проверка permissions не доказывает, что модель правильно поняла человека.

Аргументы и текст генерируются авторегрессивно тем же F и tied text-head. Для каждой гипотезы a длина и тип проверяются schema. Оптимизационная интерпретация решения:

\[
\hat a\in\arg\max_{a\in\mathcal A_{\rm typed}(q)}
\{\widehat V(a|\beta,g,M)-\lambda_c\widehat C(a)
-\lambda_r\widehat{\rm risk}(a)\}.
\]

В конкретном графе распределение πΘ(verb|h)=softmax_schema(W_a h+b_a+κ[(W_p+P)h+b_p]), args — grammar-masked text-head. Value/risk обучаются как вспомогательные сигналы; формула argmax не означает точного решения POMDP. Ограниченный beam=1 по умолчанию; любой другой beam требует умножения стоимости. Отдельного поискового мозга нет. CLARIFY, ABSTAIN и NOOP — типизированные результаты; бессмысленный NOOP не засчитывается завершением новой задачи.

## 5. Доверенное исполнение и физическая проверка

Gate проверяет **в точке отправки действия**: свежесть ν,e; owner-intent; schema; реальные permissions; STOP; подтверждение, связанное с digest аргументов, сроком и целью; версию preconditions. Предварительный policy snapshot не заменяет эту проверку.

При разрешении выдаётся однократный ticket ι, фиксируются immutable (h_issue,P_version,expected,goal,deadline,prestate). Само разрешение не является receipt и не запускает learning.

Actuator может вернуть DISPATCHED, REJECTED, PARTIAL либо ERROR. Readback выполняется независимо от текста модели. Для функций без достаточного native-свидетельства результат UNKNOWN. Для частично выполненного многошагового плана выдаются отдельные receipts шагов; не объявляется общая атомарность внешнего мира.

\[
e=\operatorname{Verify}_{G_{\rm const}}
(\iota,prestate,dispatchReceipt,poststate,timestamps,interference).
\]

e несёт два независимых поля:

- taskEvidence∈{TRUE,FALSE,UNKNOWN}: выполнен ли утверждённый predicate;
- attribution∈{CONTROLLED,OBSERVATIONAL,UNKNOWN}: что можно сказать об эффекте именно действия.

TRUE не означает причинность: громкость мог изменить человек. FALSE требует полноценного валидного наблюдения после завершения; отсутствие readback не равно FALSE. Уже истинный до действия predicate даёт SATISFIED_NOOP и отдельно отражается в метриках.

P прогнозирует условную частоту проверенного исхода **после попытки**, а не причинный do-эффект. Обучение causal world-model допускается только при CONTROLLED либо отдельно обоснованной идентификации.

## 6. Тотальный событийный переход

Строки ниже — таблица исходов. Нормальная обработка использует явные микрофазы и события из §8. После malformed-проверки выбирается первая строка с совпавшими tag,phase,guards. Неизвестный tag или неподходящая фаза → INVALID/UNEXPECTED_EVENT. OBSERVATION не проходит несколько строк за один переход.

| Событие / условие | Переход | Изменение P / достоверной памяти |
|---|---|---|
| Неверная длина, тип, число, версия | INVALID, bounded log, без вычислений F | Нет |
| STOP/REVOKE | STOP=true; e++; отменить pending; запрет новых dispatch | Нет |
| RESTART/RESTORE/MODEL_SWITCH | Новое ν; STOP=true; pending=∅; валидировать снимок целиком | Только валидированное прежнее состояние, не новый опыт |
| Ошибка нового ν / trust-anchor | SAFE_MODE, DENY | Нет |
| OWNER_RESUME с действительным согласием | Снять STOP для новых разрешённых целей | Нет |
| DEADLINE для pending | TIMEOUT, consume ticket; записать uncertainty | Нет |
| RECEIPT неизвестного/использованного ticket | REPLAY_REJECTED | Нет |
| RECEIPT с неверными ν,e,model,goal,digest,precondition или после deadline | STALE, consume ticket | Нет |
| RECEIPT при STOP/отозванном intent | CANCELLED, consume ticket | Нет |
| RECEIPT с ошибкой/неполнотой наблюдения | UNKNOWN, consume ticket | Нет; диагностический U допустим |
| RECEIPT валидный taskEvidence FALSE | VERIFIED_FAILURE, consume и атомарно применить learn | Да, y=0; без причинного утверждения |
| RECEIPT валидный taskEvidence TRUE | VERIFIED_SUCCESS, consume и атомарно применить learn | Да, y=1; без причинного утверждения |
| Валидный обычный x при STOP | Допустима ограниченная диагностика/наблюдение, нет задач | Нет learn по успеху |
| x без цели/события пробуждения | IDLE; тяжёлые encoder/F/heads не исполняются | Нет |
| x с недостаточным резервом | BUDGET_ABSTAIN; quota event log | Нет |
| x с достаточным бюджетом | Encode→F→typed proposal; s,β могут измениться | Только недоверенное состояние |
| Неприемлемое/неуверенное proposal | CLARIFY/ABSTAIN/REJECT | Нет |
| Gate denied | DENIED, нет dispatch, consume proposal | Нет |
| Gate allowed, actuator не отправил | DISPATCH_FAILURE, без success-label | Только собственная диагностическая метка |
| NOOP при заранее подтверждённой цели | SATISFIED_NOOP, без fake action | Не учит эффективность действия |
| Любое неактуальное обычное событие | IGNORED/STALE_OBSERVATION | Нельзя повышать статус до актуального факта |

Обычное новое наблюдение не обязано отменять все tickets: отменяет их изменение соответствующей цели/precondition, STOP или epoch. Иначе непрерывное аудио делало бы любой долгий Android-вызов необучаемым.

## 7. Подтверждённый опыт

Если e валиден, транзакция проверяет unused(ι), current(ν,e,v), activeIntent и deadline, затем одной логической фиксацией добавляет receipt, markUsed и обновление P из 04. Сначала вычисляется новая P в staging; при неуспехе транзакции остаётся старая. L не принимает текст модели как доказательство.

M получает key=tanh(W_k h_issue), value=tanh(W_v h_issue+f_evidence(e)) с ссылкой на bounded canonical payload e. f_evidence — фиксированная manifest-функция в [−1,1]^m: status one-hot, нормированные поля native-poststate и missing-mask; обучаемых весов у неё нет. Непоместившиеся поля сохраняются в payload. Для точного воспоминания payload подаётся ограниченным наблюдением тому же F; это дополнительные события с собственным бюджетом. Eviction payload делает ссылку недоступной. При смене v embeddings мигрируют по 09. Хранение key/value не делает все связанные убеждения истинными. UNKNOWN может записываться отдельно для анализа неопределённости, но не учит task-success.

При позднем результате после отмены фактическое состояние мира всё равно могло измениться. Отдельное свежее OS-наблюдение может обновить OBSERVED-память; оно не реанимирует отменённый ticket и не выдаёт прежнему действию credit.

## 8. Микрофазы и полное ядро перехода

В полное состояние добавляется bounded reactor R_t: очередь событий, часы, таймеры, work-records и фаза каждого work-record. Фаза p∈{IDLE,COMPUTING,PROPOSED,AWAIT_CONFIRM,READY,DISPATCHED,WAIT_READBACK,COMMITTING,TERMINAL,SAFE_MODE}. Это детерминированный control flow единого агента, не второй интеллектуальный оркестратор. Pending действий ≤32; одновременно вычисляемый work-record один. Наблюдения во время ожидания receipt могут обслуживать организм, не стирая ticket.

| Фаза + входной tag | Операция и следующая фаза/событие |
|---|---|
| Свободный compute-slot + OBSERVATION | Admission; IDLE/ABSTAIN сразу terminal либо COMPUTING с ограниченным work-record |
| COMPUTING + COMPUTE_TICK | Один bounded neural/DSP primitive; при остатке работы COMPUTING, при завершении enqueue COMPUTE_DONE |
| COMPUTING + COMPUTE_DONE | Typed decode: PROPOSED либо terminal CLARIFY/ABSTAIN/INVALID_PROPOSAL; enqueue AUTHORIZE_REQUEST только для proposal |
| PROPOSED + AUTHORIZE_REQUEST | Текущая проверка schema/intent; DENIED terminal, AWAIT_CONFIRM либо READY |
| AWAIT_CONFIRM + OWNER_CONFIRM | Проверка digest/срока; READY либо DENIED; отсутствие ответа даёт DEADLINE |
| READY + DISPATCH_REQUEST | Повторная проверка live STOP/epoch/permissions; gate выдаёт ticket и ровно один async OS-dispatch, next=DISPATCHED, либо DENIED; OS boundary позже порождает DISPATCH_RETURN |
| DISPATCHED + DISPATCH_RETURN | REJECTED/ERROR → terminal без task-label; dispatched/partial → WAIT_READBACK, enqueue READBACK_REQUEST |
| WAIT_READBACK + READBACK_REQUEST | Async native query; ждать READBACK_RETURN или deadline |
| WAIT_READBACK + READBACK_RETURN | Verify; UNKNOWN terminal consume-ticket либо COMMITTING с подготовленной Evidence |
| COMMITTING + COMMIT_REQUEST | Атомарно recheck ν/e/intent/deadline/unused + receipt/P/markUsed; enqueue COMMIT_RETURN |
| COMMITTING + COMMIT_RETURN | COMMITTED/STALE/ERROR terminal; ERROR сохраняет прежнюю P и failclosed ticket-state |
| Любая фаза + STOP/REVOKE/RESTART/DEADLINE | Приоритетная отмена по таблице исходов; DEADLINE закрывает также AWAIT_CONFIRM/COMPUTING без ticket; поздние DONE/RETURN не возрождают работу |
| TERMINAL + RELEASE | Освободить refs/квоты; outcome остаётся в bounded log |

READY всегда enqueues DISPATCH_REQUEST; вход в COMPUTING enqueues первый COMPUTE_TICK, незавершённый tick enqueues следующий; вход в COMMITTING enqueues COMMIT_REQUEST. Терминальные исходы enqueues RELEASE. OWNER_CONFIRM и внешние returns порождает среда, а не модель. Если compute-slot занят, OBSERVATION ставится в bounded input-queue либо получает BACKPRESSURE; квоты из 01 не увеличиваются. Статус SATISFIED_NOOP может завершить задачу до dispatch только при независимом актуальном prestate.

RECEIPT в таблице исходов — внешнее подтверждение, принимаемое как READBACK_RETURN с проверяемым ticket/origin; произвольный текст не становится Evidence. Каждый внутренний tag имеет producer, bound и expected phase; повторный или несвоевременный tag получает UNEXPECTED_EVENT и не меняет работу. Ошибки native-query и crash до завершения дают UNKNOWN. Число auto-attempts, work ticks и generated tokens конечно. Эта микросемантика закрывает недостижимость gate-строк исходного draft.

Полное X=(w,S,T,R); для уже выбранного события e:

\[
(S^+,T^+,R^+,a)=\delta_{\Theta,G_{\rm const}}(S,T,R,e).
\]

Внешнее ядро K_ext(dw′,dΔ,dη|w,a,S+,T+,R+) включает физическую эволюцию и внешние события η (OS-returns, owner, сенсоры). Его согласованность с K_env/O_obs — предпосылка среды. Origin/tickets проверяются δ, а не считаются истинными из-за попадания в η. Внутренние вычислительные события создаются reactor-переходами, не O_obs.

\[
\mathcal K(A|X,e)=\int {\bf1}\!\left[
(w',S^+,T^+,\operatorname{AdvanceQueue}(R^+,\Delta,\eta))\in A
\right]K_{\rm ext}(dw',d\Delta,d\eta|w,a,S^+,T^+,R^+).
\]

AdvanceQueue увеличивает время, добавляет bounded η и due deadlines с приоритетами; overflow → bounded BACKPRESSURE/SAFE_MODE, idle queue получает IDLE-timer без тяжёлых вычислений. Следующее событие — детерминированный head очереди. Для deterministic environment Δ=0 на внутренних шагах допустимо только конечное их число до ожидания/terminal, чтобы исключить Zeno-loop. Стохастический ξ laboratory-policy включается в kernel отдельным распределением; runtime tie детерминирован.

Pushforward измеримого K_ext через total bounded δ и AdvanceQueue задаёт probability kernel. Это не неопределённое произведение зависимых Dirac/OS-мер. Численное K_ext без данных неизвестно. Теорема определённости не означает правильность интеллекта или безопасность некорректной ОС.

## 9. Детерминированные control defaults

BudgetTop: sort score убыв., index возр.; включать следующий блок только если есть резерв enc/head/control и хотя бы один полный inner-step. Если не помещается ни один блок — ABSTAIN. Kmax=8; halt-threshold .95 — расчётный default, требующий calibration. Mandatory owner-events и trusted control events bypass learned wake; optional wake threshold .5. Event queue≤1024 fixed headers по128 bytes плюс bounded refs; deadlines по (time,priority,serial). Pending≤32, Q≤64, payload-store из01. Переполнение control-queue не теряет STOP: отдельный atomic STOP-latch вне очереди; если control input нельзя безопасно принять — SAFE_MODE. Atomic latch и приоритет scheduler входят в A_cap/реализацию, не доказаны для Android. Confirmation для каждого typed proposal связана с digest, её отсутствие не наследует consent от соседнего предложения.
