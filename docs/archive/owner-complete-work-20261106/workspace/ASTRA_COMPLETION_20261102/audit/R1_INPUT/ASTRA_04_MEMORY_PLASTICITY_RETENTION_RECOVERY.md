# ASTRA 04 — память, пластичность и восстановление

## 1. Что хранится и кому доверять

M — learned-addressable episodic context, L — trusted outcome journal, P — ограниченный predictor correction. Ни M, ни P не несут capabilities. В M fields: key[m]FP16,value[m]FP16,64-byte fixed header. Header offsets: recordId u64@0, payloadSlot u32@8,payloadGeneration u32@12, provenanceId u64@16, createdMonotonic u64@24, expiryMonotonic u64@32, modelTableIndex u32@40,kind u16@44,flags u16@46,lastAccessSerial u64@48,sourceSequence u64@56. Full model digest находится в immutable per-store table≤16×32bytes и проверяется до чтения. После reboot monotonic expiry недействителен: entries quarantine до policy revalidation; нельзя просто сравнивать часы разных boot.

Payload ≤4096 bytes/object,≤4096 slots shared с Q/D/L/U. Record references include slot generation, preventing reuse ABA; generation overflow slot retires. Full payload hash/authentication в store index64bytes/slot **дополнительно** к 16MiB contents; это новая поправка ресурса 05. Payload corruption → related M unavailable, не fallback к hallucinated value. Key/value checksum лишь находит битовую порчу; provenance требует protected L. Если даже raw record утерян, neuroembedding не считается lossless backup.

Вставка:

1. Verified receipt commit: (k=tanh(W_kh_{issue}),v=tanh(W_vh_{issue}+f_e(e))), kind VERIFIED_COMPLETION; CONTROLLED_EFFECT только при отдельном attribution certificate.
2. OBSERVED: native/user source validation, raw event canonicalization, F encoding h_obs, тот же W_k,W_v; e status=observed, kind/source distinct. Пользовательское утверждение USER_DECLARATION сохраняется как утверждение пользователя, не как факт мира.
3. HYPOTHESIS: inference output может войти только в U по умолчанию, M не пополняется им автоматически. Если эксперимент включает HYPOTHESIS in M, нужен отдельный flag и quota≤256, не новое authority.
4. UNKNOWN: diagnostic U с source refs; не verified label и не P update.

f_e∈[-1,1]^128 фиксирован: indices0–3 one-hot status(FALSE,TRUE,OBSERVED,UNKNOWN);4–6 one-hot attribution;7 signed no-op flag;8–23 sixteen bounded schema fields;24–39 masks этих полей;40–45 one-hot modality;46 normalized elapsed;47 valid-time mask;48–127 zero. W_vh всё равно может содержать подробности; payload имеет полный canonical record. Normalization каждого schema field из manifest, не ad hoc число. f_e и kind не аутентифицируют ничего сами.

Expiry candidate: observed OS entries5minutes, owner declarations30days, completed episodes30days; pinned active goals/operations не evict до разрешения. Историческое observed остаётся историческим, его TTL не доказывает текущую истинность. Удаление по privacy consent имеет приоритет и очищает references; активную операцию сначала закрыть UNKNOWN/STOP. Полный store scan deterministically удаляет expired/unpinned, затем LRU по(lastAccessSerial,id); если все pinned — новая вставка/dispatch DENIED_STORAGE. Старую квитанцию нельзя evict до завершения связанной транзакции; generation uniqueness и active-only ticket acceptance защищают replay после eviction старого used-header. Квоты конечны, обещания помнить всё навсегда нет.

## 2. Exact online update и область улучшения

Только при fresh verified binary endpoint из 01. Frozen FP32 h=h_a после args, current p=P[a], (l_0=W_p[a]h+b_p[a]), (q=σ(l_0+p^Th)). Defaults ε=1,λ=.001,η=.01,pmax=1.

\[
d_h=\epsilon+\|h\|_2^2,\quad
p'=\Pi_{\|p\|_2\le1}\{p-\eta[(q-y)h/d_h+\lambda p]\}.\tag{P1}
\]

Другие строки P неизменны. q_issue нужен для честной prequential calibration, не для delayed gradient. Used id/P-version commit не зависит от numerical comparison q. Euclidean projection (x\mapsto x/max(1,\|x\|_2)). Receipt duplicates дают **тождественно** старую P, а не «почти нулевой шаг».

P1 — PGD для (f(p)=BCE(y,σ(l_0+p^Th))/d_h+\lambda\|p\|²/2). Hessian (q(1-q)hh^T/d_h+\lambda I\), следовательно L≤.25+λ=.251; η=.01<1/L. Проекционное неравенство и smoothness дают

\[
f(p')≤f(p)-(\eta^{-1}-L/2)\|p'-p\|².\tag{P2}
\]

Доказательство: p допустимо, оптимальность projection даёт ∇f·(p′−p)≤−||p′−p||²/η; подстановка в Taylor upper bound. Это точный результат для **данного sample и frozen h/l0**, а не global task success. Проекция/λ могут изменить знак отдельного логита; гарантируется f, не каждое слагаемое. h=0,λ=0 → no learning.

Градиент bound (G≤1/(2\sqrtε)+λpmax=.501). Nonexpansive projection даёт ||p′−p||≤ηG=.00501. На любом frozen old feature x с ||x||≤√d: |Δlogit|≤√dηG, |Δprob|≤√dηG/4; при d1024 это≤.04008. Bound груб, но конечный. После nsteps bound≤min(2pmax,nηG)√d/4 и бесполезен для длинного future; это не zero-forgetting.

Для T updates одной строки на произвольной **реализованной** последовательности convex f_t с ||gradient||≤G, diameterD=2:

\[
\sum_t[f_t(p_t)-f_t(p^*)]≤D²/(2η)+ηG²T/2.
\tag{P3}
\]

Вывод: squared-distance recursion projection, суммировать telescoping. При η=D/(G√T) bound DG√T. Defaults постояннаяη дают записанный bound, не автоматически O(√T). Если changing Θ/features или выбор actions зависит от P, P3 сравнивает с comparator на **тех же observed losses**, не hypothetical alternative policy/world и не nonstationary dynamic regret.

## 3. Retention без ложных универсальных обещаний

Контрпример: два tasks имеют h=1 и противоположные y. Положительный update по y1 уменьшает его BCE и увеличивает BCE y0. Ни ограниченность P, ни достаточность local descent не исключают forgetting. Более сильный production retention gate требует protected finite replay R_old: proposed update принимается только если Δloss_i≤δ_i всех retained strata и old hard fixtures unchanged. Режим online по умолчанию **без** проверки всех old tasks, поэтому обещание ограничено P1/P2; shadow evaluation и rollback P допускаются только по independent controls, не авторитету модели.

Предкодовый эксперимент: paired identical issued tasks до/после P; стратумы old/new/conflicting/UNKNOWN/delayed/device-state. Primary Δ_success_new≥.02, Δ_success_old≥−.01 и Δfalse_action≤0 в статистических bounds — **неутверждённые candidate thresholds**; при n малом INCONCLUSIVE. Обязательные ablations P=0,κ-acceptance disabled, memory off, replay on/off. Замерять coverage и исполнимость, не лишь training BCE. После Θ consolidation новые v/ν, P=0 по умолчанию; переносить P без re-fitting нельзя из-за смены features.

Для fixed deterministic finite fixtures можно enforce per-item nonregression exact; тогда monotonicity доказывается определением gate. Для IID paired population outcomes D∈[-1,1] bound радиуса sqrt(2log(1/α)/n); fresh heldout после каждой адаптивной consolidation либо заранее bounded finite family+uniform correction. Набор, используемый для принятия online updates, больше не locked test.

## 4. Migration и transactional persistence

Model switch: stop latch → закрыть dispatch → allocate freshν → pending cancelled → authenticate new architecture/tensor/tokenizer/DSP manifests → validate norms/shapes → stage new state → atomic version pointer. Raw source/provenance records сохраняются в пределах quota; старые keys/values/FIFO/P quarantine. Для каждой preserved raw запись: validate allowed source, re-encode **новым** F, regenerate W_k/W_v,f_e, atomically publish newM; payload absent → drop/UNKNOWN. Re-encoding исходного текста не восстанавливает прежний hidden state, поэтому training transfer требует separate evaluation. Budget migration≤4096records×(≤4096tokens each) по абсолютной верхней длине, а не 4096 бесплатных MAC; resumable staging не activeM до completion. На телефоне выбирается lazy migration≤16records/task budget, остальных entries I-excluded; long migration cost честно ухудшает cold-start.

Transaction domain: controller durable database содержит L,D,P-version и content-addressed row P; mutable neural worker не пишет туда. Prepared M bytes могут быть immutable staging object; commit включает их reference. Atomic commit либо делает used+receipt+newP+newM refs видимыми вместе, либо ни одно. После crash committed rows и references validate; orphanstaging bounded garbage-collected; unresolved PREPARED/SENT operations остаются reconciliation entries и не превращаются в «ничего не происходило».

Disk design: two authenticated snapshots neural state, bounded WAL≤8MiB, payload16MiB+index. При WALfull checkpoint под STOP; если durable checkpoint невозможен, failclosed. Crash at PREPARED-before-dispatch и after-dispatch-before-return неразличимы по одному локальному log; статус MAY_HAVE_EXECUTED. Readback сверяет текущий predicate, но не гарантирует exact-once historical effect. Retry только idempotent absolute set с новым intent/precondition или explicit informed owner after uncertainty; для send/delete нет silent retry.

SQLite/WAL либо альтернативный storage здесь **контракт backend**, не доказанная A52 atomicity. Конкретный local transaction serializer описан 07; implementation обязан fault-inject при каждой durable boundary. fsync/rename atomicity зависят от OS/filesystem; в теореме A_fs, а не универсальный факт.

## 5. Три разных восстановления

**Bytes:** authenticate known-good slot; checksum-only не защищает от replacement. **State:** replay complete authenticated event records с exact model version/RNG/DSP; если часть causal inputs отсутствует, восстановить точное s невозможно — reset s,g,P=0, raw evidence quarantine, STOP. **Function:** NCR-EVO ищет другую структуру, удовлетворяющую независимому контракту; это не восстановление утраченных private facts.

Теорема невозможности: два исходных states/functions u≠v дают одинаковый повреждённый record r и одинаковый доступный reference. Любая детерминированная R(r) одна и та же и ошибается хотя бы на одном; randomized R не даёт probability1 обоим. Для восстановления N equiprobable lost bits без side information вероятность угадать≤2^-N. Конкретно M capacity4096×payload4096bytes ограничена; embeddings не могут обещать восстановление произвольных бесконечных историй. Достаточный repair-reference — полный canonical raw log+model manifest+RNG, либо immutable verified baseline, либо contract, однозначно определяющий нужный output на входе. Если ни одного нет, единственный честный результат UNKNOWN/reset, а не «организм регенерировал знание».
