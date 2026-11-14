# ASTRA 02 — новые веса, альтернативы и точный учёт

## 1. Решение и границы выбора

Нормативный расчётный кандидат UNO-B2: один shared block-recurrent F, все веса новые; m128,V32768,A128,b64,χ4,J2,Kmax8. d∈{512,1024,1536,2048}. B2 отличается от B1 текущим query, proposal-conditioned trace, отдельной observability-head и согласованным selector. Это не наследование доказательства качества B1.

Предпочтительный порядок проверки на бумаге: B2-512 как самый малый **кандидат**, B2-1024 как опорный, B2-1536 как увеличенный fallback; B2-2048 — контроль масштабирования. Если долгий контекст проваливает quality gate, предварительно определён fallback H2-1024 с локальным attention. Если MAC/bandwidth проваливают budget, LR2-1024(rank64) сравнивается на том же полном наборе задач. Ни одна конфигурация не названа smallest viable до measurements.

## 2. Полный реестр и соглашения

Ниже n элементов означает число **медленных trainable scalars**, не MAC. Все строки/ветви/blocks обучаются совместно. Структура каждой матрицы row-major [out,in], batch B: y=X Wᵀ+b, X[B,in], y[B,out], backward dW=dYᵀX, dX=dY W. Для lookup E: вход token id, выход d; backward scatter-add. Для tied text output используется E h, и два вклада суммируются в один E. Recurrent gradients суммируются по l,j,k,t; нет K копий весов.

Общие коды: **I** = независимая uniform Xavier (U[-\sqrt{6/(fanIn+fanOut)},+\sqrt{6/(fanIn+fanOut)}]), затем row-L1 projection; **Z**=0. Все bias init Z. Ω фиксирована до обучения: A rows≤1; B≤.9; C≤2; U_s,U_g≤1; W_q,k,v,r≤2; остальные matrices≤8; embeddings E row-L1≤8; e_modality,b_z box[-1,1]; прочие biases box[-8,8]. Это консервативные **кандидатные** caps, не найденный optimum. Обучение 03 может сравнить заранее перечисленные caps; изменение cap меняет manifest и доказательство чувствительности. e_modality init uniform[-.01,.01], b_z=0. Все медленные тензоры обновляются projected Adam/SGD offline; runtime immutable.

| Имя | Форма | Элементы | Роль / target | Init / constraint |
|---|---|---:|---|---|
| E_text | V×d | Vd | input/AR output, args, goals | I /8 |
| W_audio | d×80 |80d| ASR и TTS feedback | I /8 |
| W_image | d×768 |768d| screen grounding | I /8 |
| W_sensor | d×64 |64d| masked sensor/context | I /8 |
| W_meta | d×32 |32d| positions/mode/OS | I /8 |
| e_modality,b_z |6×d;d|7d| modes, all losses | small /box1 |
| U_s,U_g |2×(d×d)|2d²| temporal state/goal conditioning | I /1 |
| W_q,W_k,W_v |3×(m×d)|3md| query/key/value, supervised retrieval and future losses | I /2 |
| W_r |d×m|md| memory read injection | I /2 |
| A_lj,C_lj |2×Jnb×(χb×d)|2Jχd²| shared recurrence | I /1,2 |
| B_lj |Jnb×(b×χb)|Jχbd| shared recurrence | I /.9 |
| a_lj,b_lj |Jnb×(χb;b)|J(χ+1)d| recurrent bias | Z /box8 |
| W_a,b_a |A×d;A|A(d+1)| verb imitation | I,Z /8 |
| W_p,b_p |A×d;A|A(d+1)| Y conditional R=1 | I,Z /8 |
| W_R,b_R |A×d;A|A(d+1)| observability R; new B2 tensor | I,Z /8 |
| W_ctc,b_ctc |128×d;128|128(d+1)| RU symbols+blank | I,Z /8 |
| W_b,b_b |128×d;128|128(d+1)| annotated marginal factors | I,Z /8 |
| W_speech,b_speech |258×d;258|258(d+1)|257 log spectra+stop | I,Z /8 |
| w_V,w_risk,w_halt,w_conf, biases |4×(1×d;1)|4(d+1)| value/risk/halt/answer correctness | I,Z /8 |
| b_text |V|V| AR/argument CE | Z /box8 |
| W_M,b_M |nb×(2d+4);nb|nb(2d+5)| sampled prefix masks | I,Z /8 |
| w_wake,b_wake |1×32;1|33| optional ambient wake | I,Z /8 |
| P (не Θ) |A×d|Ad| fast verified update |0 /row L2≤1 |

Names in machine inventory: W_verb=W_a, W_outcome=W_p, W_observable=W_R, W_belief=W_b, W_mask=W_M; все остальные отображения очевидны по role. `evidence/tensor_manifest_d1024.json` перечисляет **198 отдельных тензоров**, включая каждую ветвь/блок; это спецификация форм, не файл весов. Все остальные операции фиксированы, без trainable LayerNorm, positional table, adapter, vocoder или hidden bridge.

FP32 canonical/training master; deployment FP16 или заданный mixed INT8. В INT8 все matrix tensors (включая wake1×32) symmetric int8 с одной FP32 scale на output row, zero-point0; vectors/e_modality FP32. Row stride roundUp(in,16) bytes, начало tensor/scale array64-byte aligned. Header4096 bytes +128 bytes/tensor; он содержит id,shape,type,offset,length,scaleRef,digest/norm metadata refs. Padding0, SHA покрывает также padding. Ни Java object layout, ни backend packing не входят в эти размеры. FP16 raw=2P, deployed FP16 padding/header считать отдельно таким же descriptor rule. Dtypes для hidden/accumulator/P/trace FP32; memory key/value и FIFO FP16 с round-to-nearest; преобразования явные.

## 3. Аналитический и численный workbook

H=3A+128+128+258+4=902, в B1 было 774. Тогда

\[
P_{B2}=Vd+951d+2d^2+4md+J[2\chi d^2+\chi bd+(\chi+1)d]+H(d+1)+V+\frac db(2d+5)+33.
\tag{W2}
\]

951=80+768+64+32+6+1. Изменение относительно B1 **ровно 128(d+1)**. F-MAC полного прохода (J(2\chi d^2+\chi bd)). Bias увеличивает число параметров F на (J(\chi+1)d), но не MAC. Выдача токена Vd — отдельная операция.

|d|B1 P (сохранён)|B2 P|raw FP16 MiB|mixed INT8 ABI MiB|F MAC|FP32 Adam16P MiB|
|---:|---:|---:|---:|---:|---:|---:|
|512|22 950 223|23 015 887|43.899321|22.268860|4 456 448|351.194565|
|1024|55 320 439|55 451 639|105.765608|53.285583|17 301 504|846.124863|
|1536|97 144 223|97 340 959|185.663145|93.318054|38 535 168|1485.305161|
|2048|148 421 575|148 683 847|283.591932|142.366028|68 157 440|2268.735458|

Для d1024: unpadded INT8=55,843,608 bytes, ABI=55,873,984 bytes; fast P ещё131,072 FP32 values=524,288bytes. Не смешивать это с 55,711,512bytes B1. Подробные целочисленные расчёты воспроизводит только арифметический `evidence/recompute.py`; модель он не запускает.

Без padding (B_8=P+3P_{vec}+4R_{rows}), где (P_{vec}=7d+J(\chi+1)d+H+V+nb+1), (R_{rows}=V+7d+3m+J(2\chi+1)d+H+nb+1). Вектора хранятся 4bytes вместо 1; scale4bytes/row. Файл ABI суммирует каждое выравнивание, а не округляет только общую сумму.

## 4. Материально иные семейства

**LR2:** заменить каждую A,C независимыми L_A R_A,L_C R_C без biases факторов: L[χb,r],R[r,d], r64. Остальные tensors те же. Новое число

\[
P_{LR}=P_{B2}-2J\chi d^2+2Jnb\,r(d+\chi b),\quad
C_{F,LR}=Jnb[2r(d+\chi b)+\chi b^2].
\tag{W3}
\]

Нормы L_A,R_A≤1 дают A≤1; L_C≤1,R_C≤2 дают C≤2. Это достаточная факторная норма, не Euclidean projection всего произведения. Shape backward: ∂L/∂L_A=δ(R_Ah)ᵀ, ∂L/∂R_A=L_Aᵀδhᵀ. F один, rank ограничивает expressiveness; уменьшение MAC не доказывает сохранение quality.

**H2:** один causal attention read over последних Nctx≤256 состояний того же организма. Добавлены Q,K,V,O[d,d] без biases/LN, row-L1≤2, init I. На каждом событии новое state один раз проектируется в cache K,V; query=Qz0, a=softmax(qKᵀ/√d), context=OΣa_iV_i, z0 заменяется tanh(z0+context) **до** memory query и inner loop. Cache содержит только ранее завершённые события; новый state добавляется после event commit. Дополнительные 4d² parameters и ≤4d²+2Nctx d MAC/event, cache4Nctx d bytes FP16. В inner loop attention не пересчитывается. Существующий FIFO raw h остаётся нужен для versioned cache rebuild, нельзя вычесть его бесплатно. Этот вариант всё ещё один организм с совместным Θ.

|d|LR2 rank64 P|LR2 F MAC|H2 P|доп. H2 MAC/event|
|---:|---:|---:|---:|---:|
|512|20 394 447|1 835 008|24 064 463|1 310 720|
|1024|43 917 303|5 767 168|59 645 943|4 718 592|
|1536|70 602 271|11 796 480|106 778 143|10 223 616|
|2048|100 449 351|19 922 944|165 461 063|17 825 792|

**Hierarchical memory alternative:** G=64 buckets×64 entries; centroids average existing compatible keys, не trainable. Query scores64 centroids + scan top4 buckets=256entries, затем weightedvalues; ≤(64+256+256)m MAC вместо 8192m, плюс maintenance/rebuild. Это approximation: rare key может быть вне выбранных buckets. Контрпример: bucket centroid0 из ±keys, relevant +key скрыт; nearest centroid ranking не гарантирует recall. Поэтому baseline остаётся полный scan; hierarchy допускается только recall lower bound≥.99 на held-out retrieval и cost gain после maintenance.

**Conventional small LLM+external state** — non-goal comparison: transformer с L слоями, MLP ratio4, tied vocabulary, без biases/LN для счёта (P\approx Vd+12Ld^2), KV bytes=4LNctx d FP16, MAC/token≈12Ld²+2LNctx d+Vd. Например L8,d512,V32768:41,943,040 parameters, KV4MiB при Nctx256. Добавление ASR/TTS/vision было бы отдельным ledger; нельзя сравнивать text-only cost с полным UNO. Это baseline цены/качества, не выбранная многомодельная архитектура продукта.

## 5. Контракция, выразительность и quantization

При fixed z leaky full step имеет c=.95. Даже после 8 steps worst-case остаток (c^8=.6634204313) от initial error; для 1% нужно 90 steps. K8 не является fixed-point solver с точностью 1%. Увеличение α до 1 даёт c=.9 (44steps для 1%), но меняет динамику обучения. B2 использует finite computation, не обязан доходить до fixed point.

Весь event **не contractive** из нормы F. При фиксированных x,g,M обозначим L_s=||U_s||∞, L_q=||W_q||∞, L_r=||W_r||∞. Softmax bound ||Δω||1≤2||Δlogits||∞ даёт

\[
L_z\le L_s[1+2L_rL_q\sqrt m/T_M],\quad
L_{event}\le c^K[\rho+(1-\rho)L_z]+\alpha b_0\|C\|_\infty L_z\sum_{i=0}^{K-1}c^i.
\tag{W4}
\]

Даже эти конечные caps допускают L_event≫1; changing masks может иметь discontinuities. Нельзя переносить fixed-z contraction на global training, goals или agent-world stability. Сильная глобальная контракция при одинаковых будущих входах стирает прошлые различия≤c^n, что конфликтует с persistent-bit задачей при конечной точности; episodic discrete payload даёт отдельный канал хранения, но конечную ёмкость. H2 и finite-K relaxed A-cap являются заранее описанными альтернативами, не обещанным исправлением интеллекта. Relaxed A-cap=2 сохраняет boundedness, теряет γ<1; это отдельный manifest FNC2, counts те же.

INT8 row quantizer (s_i=max_j|W_{ij}|/127) (для zero row s=1), q=round(W/s), decode=sq. Без saturation |ΔW_ij|≤s_i/2, row error≤n s_i/2. Сигнал linear-output error≤||ΔW||∞||x||∞; accumulate rounding добавляется. Для A,B надо проверить **decoded actual** (\|\tilde A\|∞\|\tilde B\|∞<1). Достаточный margin: ((a_{train}+δ_A)(b_{train}+δ_B)≤γ_{deploy}); нельзя автоматически вычесть .01 независимо от width/scale. Экспорт сначала считает decoded row sums, при нарушении reproject→requantize с уменьшаемым cap до сертификации или отвергает artifact. Конечное число export attempts≤8, затем FAIL; termination не означает успешный export.

При one-step error ε_num и full mask ε_K≤ε_num(1−c^K)/(1−c), для изменённого z добавляется W4, а при изменённом argmax нет гарантии одинакового решения. Для logits error≤ε_l exact greedy parity только если top1−top2>2ε_l. В маленьком margin требуется отчёт disagreement, не замалчивание.

## 6. Правило окончательного выбора

Feasible family (\mathcal F=\{(arch,d,format):LCB(Q_j)≥q_j, UCB(risk_j)≤r_j, coverage_j≥c_j, R_{peak}≤R_{cap}, T_{p95}≤T_{cap},J≤J_{cap}\}). Нижние/верхние границы simultaneous по preregistered strata, а не training score. Выбирается минимальный measured joules/issued-task среди feasible; ties → меньший PSS, затем меньший P. «Минимальный достаточный d» корректен только внутри объявленного семейства и проверенного распределения. Если F пусто, архитектура не допущена: сохранить функции, менять family/data/hardware, а не удалять речь или память для красивого PASS.
