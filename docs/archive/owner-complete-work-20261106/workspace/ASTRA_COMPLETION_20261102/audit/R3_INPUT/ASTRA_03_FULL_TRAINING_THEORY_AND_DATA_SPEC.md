# ASTRA 03 — обучение всего Θ и данные

Θ означает только свободные координаты по02; frozen-zero rows не обучаются. Статус: SPECIFIED, данные/обученные веса/скорость оборудования отсутствуют. Производственное обучение не выполнялось. Приведённые объёмы и learning rates — расчётные сценарии, не утверждение о достаточности.

## 1. Полная задача и измеримый target

Траектория τ содержит только причинно доступные observations, canonical proposal, teacher targets, вычислительные решения и cost. Все losses нормируются на число **валидных targets данного типа**; если их 0, term отсутствует. Mixture sampling выбирает task group равновероятно из имеющих данные; фиксированные task weights λ_j=1 после этой нормировки. Resource weight λ_c подбирается в {0,.001,.01,.1} на dev Pareto, не на test; risk constraints не покупаются уменьшением cost.

\[
J_{base}(\Theta)=E_{D,\pi_\Theta}\left[\sum_j\lambda_j L_j(\Theta;\tau)+\lambda_c C(\tau)/C_{ref}\right].\tag{L3}
\]

Cref=полная dense K8 цена для тех же admitted lengths; при пустой траектории cost term0. Это базовая часть одного ожидания; полная нормативная цель — L3a с terminal loss и coverage constraints. Masked supervised labels не являются обучаемыми masks. Нижеследующие loss coverage обязаны быть в training manifest, иначе соответствующая способность REQUIRES_DATA.

| Loss | Exact target/function | Тензоры с сигналом |
|---|---|---|
| L_AR | teacher next token CE, включая EOS, dialogue role/clarification | E,b_text,F,input,U_s,U_g,memory read |
| L_ground | CE canonical UI-element id +4 bbox-bin tokens (0…255) +text transcription; teacher grammar | W_image,W_meta,E,F и общий encoder |
| L_intent | CE goal-DSL serialization и parent refinement labels через grammar | U_g,E,F,W_meta |
| L_action | CE verb +args tokens по независимой demonstration, не собственному output | W_a,E,F,context |
| L_obs | BCE(R,σ(W_R[a]h_a+b_R[a])) для uncensored eligible attempts | W_R,F,proposal path |
| L_out | R·BCE(Y,σ((W_p[a]+P[a])h_a+b_p[a])) | W_p,F,proposal path |
| L_belief | mean masked BCE по 128 independently labelled factors | W_b,F,modalities |
| L_retrieve | CE на нужный memory record по q·k/(√mT_M) | W_q,W_k,encoder; indirect W_v,W_r через downstream labels |
| L_memory_use | AR ответа на будущий вопрос с реальным key/value write внутри unroll | W_v,W_r,W_k,W_q,F |
| L_CTC | exact negative logsum over alignments | W_audio,W_ctc,F |
| L_speech | mean L1(raw a_f, log(ε+min(Mcap,abs(STFT(y))))) +BCE(stop_f) | W_speech,W_audio feedback,F,U_g |
| L_value | (tanh(l_V)−G_norm)² по independently scored bounded episode return | w_V,F |
| L_risk | BCE(undesired outcome/incorrect proposal,h_a risk logit) | w_risk,F |
| L_conf | BCE(correct final answer/proposal,h_a or answer-end logit) | w_conf,F |
| L_wake | BCE(optional event relevant,metadata-only logit) | w_wake,W_meta не участвует в wake |
| L_halt | BCE(oracle says deeper allowed computation gives≤δ_h quality gain, halt logit) | w_halt,F |
| L_ret | replay losses +KL previous frozen output over licensed old tasks | все активные Θ |

L_obs не исправляет MNAR и не идентифицирует Y при R=0: q_R q_Y относится к verified completion. Для hard-censored STOP/restart/consent revoke не присваивается R=0 как обычной завершённой попытке; эти причины хранятся отдельно. Для обычного protocol-timeout при известной активной попытке R=0 наблюдаемо, Y отсутствует. Outcome head не получает этот пример как Y=0. Risk/utility могут штрафовать operational failure по отдельной явной метрике, не подделывая физическую метку.

128 belief factors — versioned dictionary:0–31 whitelist package-visible predicates;32–63 UI template-presence;64–79 native binary OS predicates;80–95 truth of active goal clauses;96–111 independently verified retrieval facts of current task;112–127 externally logged operation-phase predicates. Package/template/fact definitions должны войти в dataset manifest с конкретным predicate hash до обучения; нельзя выдавать отсутствие этой разметки за готовую базу знаний. Unused clauses получают mask0; probabilities не являются authority bits.

G_norm=clip((verified goal rewards−cost/ Cref−incorrect-action penalty)/Gcap,−1,1), Gcap=4 как dev candidate; rewards success1,incorrect-action−4,unknown/abstain0 с отдельным coverage constraint. Это инженерная utility, не вывод об истинных предпочтениях владельца. Halt oracle перебирает K=1…8 и nb prefix masks на размеченном **train oracle pool**, выбирает cost-min среди quality-feasible; δ_h=.01 normalized task score. Его дополнительная цена≤8nb forward/пример учитывается отдельно. Не именовать этот используемый для supervision набор dev/test.

## 1a. Полная стоимость незавершённой задачи и coverage по каждому классу

Никакое sampled computation decision, отказ, ранний EOS, drop или timeout не удаляет выданную задачу из обучения. Z∈{1,…,m} — её заранее размеченный класс; π_j=Pr_D(Z=j)>0 — фиксированная известная вероятность mixture sampling (равна1/m при равномерной смеси). A(τ)∈{0,1} означает отсутствие требуемого завершения: необоснованный отказ, timeout, drop или resource abort. Корректное уточнение/обоснованный отказ имеет A=0 только если именно это требует независимая разметка данной ambiguous/unsupported задачи. Отсутствующий в корпусе класс сπ_j=0 не покрыт этой задачей и остаётся REQUIRES_DATA; деление на0 запрещено.

[
L_{task}=1-U_Z(	au),qquad 0le U_Zle1,
]
[
J(Theta;mu)=Eleft[sum_klambda_k L_k+L_{task}+lambda_c C/C_{ref}
+sum_{j=1}^{m}mu_j,rac{mathbf1{Z=j}}{pi_j},[A(	au)-(1-c_j)]
ight].	ag{L3a}
]

Здесь k индексирует виды supervised losses, j — классы задач. U_Z задаётся независимым train oracle: правильный полный результат1, необоснованный отказ/незавершённость0; корректное уточнение может иметь1 только для заранее размеченного соответствующего случая. Это utility обслуживания, не физическая метка Y. Missing outcome masks не присваивают UNKNOWN метку Y=0. При teacher forcing все предоставленные targets остаются в loss независимо от выбранного K; availability masks определяются корпусом до sampling.

Поскольку E[1{Z=j}f/π_j]=E[f|Z=j], каждое ограничение есть Pr(A=1|Z=j)≤1−c_j, а не совместная вероятность Pr(A=1,Z=j). Контрпример отвергнутой записи: при12 равновероятных классах полный отказ одного класса даёт joint rate1/12<.1, хотя conditional rate=1. Исправленная запись даёт violation .9 для c_j=.9.

c_j=.9 для каждого класса — явный кандидат coverage floor, если task manifest до обучения не задаёт более высокий floor; это не измеренная доступность. μ_j≥0 — dual variables, не веса Θ. На batch размера B использовать g_j=(1/B)Σ_b 1{Z_b=j}/π_j·[A_b−(1−c_j)] и μ_j←max(0,μ_j+η_μ g_j), candidate η_μ=.01. Этот estimator несмещён для derivative J по μ_j; при отсутствии j в batch g_j=0. Для каждого Θ-step μ и π заморожены, и L5 относится ко всей L3a. Это не гарантия сходимости stochastic primal-dual optimization.

Внутри допущенной длинной последовательности нет q0 на каждом frame (S6). Для terminal+cost части правильная zero-task-loss траектория с C/Cref≤1 и λ_c≤.1 имеет стоимость≤.1, тогда как необоснованный abort имеет task loss1. Для полного J сравнение верно лишь при равных остальных supervised/dual terms; глобальное предпочтение полного objective автоматически не следует. Supervised targets сохраняются независимо от отказа. Hard coverage gate всё равно нужен. Невыполнимая задача не становится решённой от добавления штрафа.

## 2. Цепное правило shared recurrence

Для ветви u=tanh(Ah+Cz+a), f=tanh(Bu+b), upstream δ_j=∂L/∂h'_j:

\[
\delta_f=\alpha M_j\delta_j/J,\quad \delta_v=\delta_f\odot(1-f^2),\quad
\delta_u=(B^T\delta_v)\odot(1-u^2),
\]
\[
\nabla B=\delta_vu^T,\ \nabla b=\delta_v,\ \nabla A=\delta_uh^T,\ \nabla C=\delta_uz^T,\ \nabla a=\delta_u,
\]
\[
\bar h_k=(I-\alpha D_M)^T\bar h_{k+1}+\sum_{lj}A_{lj}^T\delta_{u,lj}+\partial L_k/\partial h_k.
\tag{L4}
\]

Shared tensor contributions суммируются по всем usages. ∂z получает ΣCᵀδ_u, далее tanh(z0+W_r r), read softmax, q, z0; через s и g идёт BPTT. Градиент по memory values $\partial L/\partial v_i=\omega_i\bar r$; по score_i $\omega_i\bar r^T(v_i-r)$; по query Σscore-gradient·k_i/(√mT_M). Нужный key/value должен быть внутри differentiable unroll или заново replayed из source. Detached old embeddings не обучают W_k/W_v; paired write→future-query minibatches обязательны.

Для CE logits l=Wh+b: ∂W=(p−y)hᵀ, ∂h=Wᵀ(p−y). Для tied E scatter lookup gradient плюс output gradient; не отдельный optimizer state. BCE derivative σ(l)−y. Value derivative2(tanh(l)−G)(1−tanh²(l)). CTC posterior alignment occupancy γ_fk даёт ∂L/∂logit_fk=p_fk−γ_fk. CTC collapse: **сначала merge adjacent repeats, затем remove blank**; `[a,blank,a]→aa`. Несовместимые length targets (T<|y|+adjacentRepeatCount) отбрасываются с reason, не скрываются ε.

## 3. Дискретные решения и exactness

На фиксированной discrete trajectory dπ — закон wake, prefix q, hazards K из 01; при on-policy sampled words/actions добавляются их logprob. Для offline teacher-forcing words/actions заданы D, не sampled, их score term не нужен. Grammar feasibility — проверяемые discrete masks, не дифференцируемая процедура.

\[
\nabla_\Theta E[L]=E\left[\nabla_\Theta L+(L-b)\nabla_\Theta\log\pi_\Theta(\tau)\right].\tag{L5}
\]

Все свободные Θ, влияющие на h,z, имеют также score-gradient. Для variance reduction применяется сумма по decisions с cost-to-go и baseline b(history), независимым от текущего sampled decision; baseline stop-gradient, отдельно regression loss если trainable (в B2 используется existing value head, новых weights нет). Interchanging derivative/expectation допустимо для конечного bounded support и finite smooth logits; boundary cases forced choices logprob0. Hard quantization/argmax/eviction/projection не выдаются за гладкую identity.

В offline joint objective P **фиксирована равной0 на всём сегменте**. Она не пересчитывается текущейΘ с последующим detach. ПоэтомуL5 — обычный точный gradient явно выбранной supervised/offline задачи приfixedP, кроме отдельно названныхTBPTT/STE approximations. FastP обучается только правиломP1 поverifiedoutcomes и оценивается в отдельном complete runtime replay. Это не meta-gradient через историюonlineадаптации. Если будущая версия выберет replayP, его нужно заранее вычислить приfrozen referenceΘ и зафиксировать какdata, либо включитьполныйJacobian обновлений. ПересчётP текущейΘ сdetach былбы semi-gradient, а не точныйgradient заявленногоJ. РазличиеofflineP0/runtimeP являетсяобъявленным evaluation obligation.

## 4. Оптимизатор, truncation, precision

Frozen-zero coordinates и их optimizer moments равны0 после каждого шага; optimizer обновляет только Θ_free. Консервативный memory ledger16P/18P использует P_alloc и допускает плотное хранение нулевых slots. FP32 master Adam: m←.9m+.1g, v←.999v+.001g², bias correction, θ_temp=θ−η mhat/(√vhat+10^-8), θ←ΠΩ(θ_temp). Decoupled weight decay=0: не добавлять скрытый objective. Global gradient L2 clip1, η warmup1000steps до 2·10^-4, cosine к 2·10^-5 на заданном N_steps; dev alternatives {10^-4,2·10^-4,4·10^-4}, 3 seeds{11,73,2026}. Это bounded experimental grid, не теорема о лучшем optimizer. NaN/Inf→отклонить optimizer step, снизить loss scale, не записывать checkpoint; 3 последовательных rejects→stop с диагностикой. AMP BF16 activations, FP32 reductions/master/grad/moments; FP16 fallback с dynamic scale допускается только после finite-gradient gate.

ΠΩ для row x: если ||x||1≤cap, сохранить; иначе sign(x_i)max(|x_i|−t,0), единственное t с Σmax(|x_i|−t,0)=cap, находится сортировкой |x|. Bias clamp. Это Euclidean projection на row-L1 balls; Adam+projection не имеет доказанного global descent. Online P theorem отдельно 04. Quantization-aware phase последние 10% объявленных updates использует fake quantizer Q в forward и STE в backward: **biased surrogate gradient**, L5 не становится exact derivative integer rounding. После QAT реальный export проверяет decoded norms и numeric parity заново.

Unroll L=256 events, K≤8, microbatch B=4 для d1024; gradient accumulation8→effective32segments. Состояние переносится между соседними сегментами, gradient detached на границе; session shuffle только целыми episodes. Paired memory supervision окна длины≤256 либо teacher replay целой bounded write-query pair. Для speech≤1000frames использовать full utterance CTC loss с activation checkpointing, либо явно другой chunked CTC protocol с границами; простое independent CTC на кусках **не эквивалентно** full CTC. Формальный CTC training mode по умолчанию full utterance; L256 относится к dialogue/action training. Batch при full1000 нужно уменьшать по памяти.

TBPTT gradient biased для полной истории. Только если **все** event Jacobians включая memory имеют norm≤r<1 и cross-parameter/gradient products≤G, отброшенный tail≤G r^L/(1−r). Fixed F γ=.9 этого условия не даёт (02 W4), поэтому численного универсального truncation-error нет. Отдельная long-horizon battery с delay {32,256,1024,4096events} обязательна; mismatch→увеличение unroll/checkpointing/H2, не новый PASS по short tasks.

## 5. Данные: обязательный manifest и получение

Каждая запись: `sample_id, source_uri_or_contract_id, source_sha256, license_id, permitted_train/distribute/derive, language, speaker/person/app/device/session/template/time_group, consent_scope, pii_class, modality, raw_ref, target_ref, masks, timestamps, collection_version, split_group, transform_digest`. Отсутствие права использования или consent → quarantine. Не считать публичную доступность разрешением. Подписываемая таблица прав должна отдельно охватывать коммерческое обучение, производные веса и распространение голоса.

| Направление | Предпочтительный источник | Target/QC | Чего сейчас нет |
|---|---|---|---|
| RU dialogue/planning | заказанные/лицензированные тексты и реальные добровольные задачи; fully offline transcripts | two annotators intent/answer + adjudication; leakage/dedup по semantic templates | ни корпуса, ни лицензий |
| RU ASR | собственные consent recordings; дополнительный кандидат Google FLEURS ru_ru | speaker-disjoint, clean/noisy/farfield strata; independent transcript | downloaded audio и A52 noise отсутствуют |
| RU TTS | специально лицензированный дикторский корпус | exact waveform/text alignment, silence/clipping QC; права на коммерческий synthetic voice | голоса/consent нет |
| Screen/vision | собственный test-app suite, consent screenshots с local redaction | UI tree+bbox+native action traces; passwords запрещены | реального UI taskset нет |
| Action/readback | instrumented controlled device sessions, отдельные observers | before/after/endpoint/attribution/UNKNOWN и complete attempts denominator | labels отсутствуют |
| Memory/retention | законные тексты и controlled tasks с delayed queries | true source id, contradiction/expiry labels, privacy revocation cases | long-horizon battery нет |
| Safety/uncertainty | designed negative scenarios, ambiguous speech, replay/STOP | trusted oracle statuses; human semantic risk | частот реальных ошибок нет |

FLEURS — **кандидат**, его карточка Google указывает русский и CC-BY-4.0: https://huggingface.co/datasets/google/fleurs/blob/b4a42ed06e12025c42f3b4eff6338ace2fe2447a/README.md (проверено02.11.2026). Это не готовое разрешение на любые downstream rights и не proof noisy RU ASR. Attribution/license review обязательны. Никакой dataset здесь не скачивался. Для других языков нет данных; UTF-8 byte coverage не означает multilingual competence.

Split: hashes of **groups**, 80%train/10%dev/5%calibration/5%locked test; linked speaker/session/person/template/app-family groups объединяются до split. Locked OOD выделяется по новым приложениям/дикторам/дате отдельно и не выбирает hyperparameters. Training corpus grows only in versioned releases; dedup against known tests. Test labels не попадают в memory/replay. Размеры validation задаются confidence bounds, а не лишь процентом small dataset.

Tokenization artifact: deterministic BPE on licensed train-only UTF-8, vocabulary32768, byte fallback256, reserved role/schema markers, merge tie by byte lexical order; SHA tokenizer обязателен, unbuilt vocabulary — data-dependent artifact. Target ASR alphabet128: blank0,space1,33 lowercase Russian letters в порядке `абвгдеёжзийклмнопрстуфхцчшщъыьэюя`,26 lowercase Latin,10digits,32ASCII punctuation sorted by codepoint,24 chars `€£¥₽°№–—…«»„“”‘’±×÷µ²³¼½`, UNK127. Нормализация: Unicode15.1 NFC → default lowercase → NFC; resulting codepoints вне alphabet переходят в UNK, expansion обрабатывается как последовательность codepoints. Unicode tables/version и alphabet order включаются в manifest/hash; punctuation retained; raw text отдельно. Никакой tokenizer от test.

## 6. Curriculum и критерии остановки

Stage T0 validates data/schema/DSP; T1 joint language/audio/screen/speech supervised representation, all non-selector heads active; T2 goals/actions/outcomes+paired memory; T3 resource selector/halt with bounded oracle catalogue, full replay mixture; T4 QAT/export/calibration. T1/T2/T3 не замораживают F/encoders: joint fine-tuning сохраняет все виды batches. Для отсутствующего task dataset stage gate FAIL, случайные weights не называют обученными. Early stop: dev objective не улучшается≥1% relative за 3 evaluations через фиксированные 1000steps, либо compute cap exhausted; качество принимается только отдельным test. Trials cap=3rates×3seeds×{B2-512,B2-1024,B2-1536}, расширения LR/H2 только по объявленному failure trigger. Финальный training corpus size выбирается learning curve, а не числом параметров.

From scratch — продуктовый default. Законно лицензированный pretrained small transformer допускается только offline benchmark/optional teacher при documented rights, additional compute и teacher-error audit; нет обязательной third-party runtime dependency. Сравнивать на одинаковых approved train/test и учитывать всю pretraining compute при заявлении resource superiority. Нельзя считать бесплатной недоступную историю обучения внешней модели.

## 7. Training compute/VRAM — выведенные сценарии

Пусть N_e — число событий каждого пути за все epochs, C_e его forward MAC, C_oracle — cost labels halt/selector. Dense backward примерно 2 forward матричных прохода, поэтому

\[
F_{train}\approx6\sum_e N_e C_e+F_{DSP}+F_{optimizer}+F_{oracle}+F_{recompute},\quad
t=F_{train}/r_{effective},\quad cost=t\,price_{hour}.
\tag{L6}
\]

6 — conversion MAC→FLOP2 × forward/backward3, оценка для matmul, не hardware theorem. r_effective измеряется для shapes/precision; peak FLOPS не подставлять. Adam/projection ~O(P) per update, L1 sorting O(P log fanin), dataload/FFT/validation/checkpoint отдельно. CTC DP O(T|y|), memory softmax BLM, vocabulary B L V считаются.

Для d1024 full-K8 text event C=175,448,160 MAC; homogeneous reference:

| План | Text events, только численная шкала | Матрицы FLOP | Время при **условных measured-equivalent**10TFLOP/s |
|---|---:|---:|---:|
|A ограниченный исследовательский бюджет|10^8|1.05268896·10^17|2.924h|
|B средний|10^9|1.05268896·10^18|29.241h|
|C расширенный|10^10|1.05268896·10^19|292.414h|

Это не время полного обучения и не качество: для мультимодального задания подставить N_audio=100×seconds, N_image=256×images, N_tts=100×seconds, proposal generation+canonical re-encoding+goals; добавить trials, oracle, tests, I/O. При effective1TF эти часы×10; при 100TF÷10. Если доступный budget меньше минимальной зарезервированной полной evaluation, новый trial не начинать. Ни один из A/B/C не называется sufficient до learning curves и holdout.

FP32 state16P (param4+grad4+moments8); BF16 forward с FP32 master/grad/moments18P. Для non-recomputed dense unroll верхняя **согласованная allocation-схема**, не минимум всех autodiff runtimes:

\[
B_{act}=4BL\{K[d+J\chi d+Jd]+5d+2m+M+V\},\tag{L7}
\]

хранит h,u,f,encoder intermediates, query/read,scores,logits; отсутствующие heads могут экономиться. B4,L256,K8,d1024 дают 542,113,792bytes≈517MiB; вместе с 18P≈951.890MiB →1468.89MiB до buffers/backend. Для L1000×(1000/256) и CTC DP2T(2|y|+1)×4bytes/utterance. Дополнительные activation-grad buffers, saved tensors optimizer kernels, full F preactivations если backend не восстанавливает производную из tanh output, packedweights, allocator fragmentation и data batch входят в B_backend. Device training feasibility: upper allocated+backend≤VRAMcap с резервом 20%; измерить actual peak, не выдать 1.435GiB за гарантированную карту GPU.

Checkpoint reproducibility: Θ_FP324P+moments8P+optional gradient accumulation4P+P state+RNG+optimizer step+split/tokenizer/normalizer hashes. При save только на optimizer boundary gradient не нужен, training resume payload12P; max two slots24P + bounded logs/data cache. Seeds не гарантируют bitwise equal across backends: math parity отдельно от deterministic backend requirement.
