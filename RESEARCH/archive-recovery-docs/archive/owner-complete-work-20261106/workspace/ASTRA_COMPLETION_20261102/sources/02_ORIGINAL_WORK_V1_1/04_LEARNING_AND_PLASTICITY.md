# 04. Обучение новых весов и память

## 1. Что обучается и откуда берётся сигнал

Все Θ инициализируются заново; исторические JNO-веса не используются по умолчанию. Training corpus D должен иметь provenance, права использования, язык/дикторов/устройства/задачи, и раздельные train/dev/calibration/locked-test. Разделение по пользователям, диалогам, приложениям, шаблонам и времени важнее случайного деления кадров одной записи. Нельзя смешать будущие последствия в прошлые признаки.

| Часть Θ | Наблюдаемый target | Ограничение вывода |
|---|---|---|
| E_text, F, tied text-head | Следующие токены, диалог, инструкция→аргументы | Предсказание текста не даёт физической успешности |
| W_audio, F, CTC | PCM↔независимая транскрипция | Требуются русская речь, шумы, дикторы |
| W_image, F | Image-text, чтение UI, разрешённые UI-задачи | Отдельный перенос на реальные экраны |
| W_sensor,W_meta,U_s,U_g,F | Последовательности наблюдений/задач | Частичная наблюдаемость не исчезает |
| W_q,W_k,W_v,W_r | Размеченный retrieval и replay будущих запросов | Без таких данных семантика памяти не идентифицируется |
| W_a,W_p,value,risk,belief | Demonstrations, проверенные receipts, human labels | Для denied/UNKNOWN нет ложных success/failure |
| W_speech,F | Парные текст↔waveform/STFT | Качество голоса неизвестно до обучения |
| W_M,w_halt,w_wake | Затраты и проверенное качество решения | Риск выучить пропуск сложных задач |

Существование производной не гарантирует полезный градиент каждого веса на каждом batch. Если modality никогда не представлена в данных, её веса не обучаются содержательно.

## 2. Полная функция обучения

Для конечной размеченной траектории с масками достоверности m_j:

\[
L_{total}(\Theta;\tau)=
\lambda_{\rm txt}L_{\rm AR}+
\lambda_{\rm asr}L_{\rm CTC}+
\lambda_{\rm vis}L_{\rm grounding}+
\lambda_{\rm act}L_{\rm imitation}+
\lambda_{\rm out}L_{\rm verified}+
\lambda_{\rm belief}L_{\rm factors}+
\lambda_{\rm mem}L_{\rm retrieval}+
\lambda_{\rm speech}L_{\rm spec}+
\lambda_{\rm res}C(\tau)+
\lambda_{\rm ret}L_{\rm retention}+L_{\rm aux}.
\tag{L1}
\]

Целевой expected objective: $\mathcal J(\Theta)=\mathbb E_{D,\pi_\Theta}[L_{total}(\Theta;\tau)]$. Стоимость C(τ) — реализованная стоимость конкретной sampling trajectory; expectation берётся один раз снаружи. Все λ≥0, normalizers соответствуют числу валидных targets данного типа. Если targets нет, слагаемое **пропускается**, а не делится на ноль. Нельзя уравнивать миллионы текстовых токенов и единичные safety labels без task-balanced sampling.

AR/imit — CE по token/schema verb с teacher forcing; аргументы обучаются вместе со структурой. Verified — binary CE для выбранного verb по receipt.taskEvidence при fresh ticket. У belief B факторов — masked binary CE/Brier по отдельно размеченным наблюдаемым факторам, не по фантазии модели.

CTC:

\[
L_{\rm CTC}=-\log\sum_{\pi:\mathcal B(\pi)=y}
\prod_f p_\Theta(\pi_f|audio_{1:f}),
\]

где B удаляет blanks и сливает повторы. Для невозможных alignments сумму нельзя заменить положительным ε и назвать корректным target.

Spectral loss:

\[
L_{\rm spec}=\sum_f\|\hat a_f-\log(\epsilon+\min(M_{cap},|STFT(y)_f|))\|_1
+\lambda_{\rm stop}CE(\hat stop_f,stop_f).
\]

Это surrogate для речи, не теорема о разборчивости waveform после фазового восстановления.

Retrieval contrastive loss для подтверждённого нужного ключа i*:

\[
L_{\rm retrieval}=-\log
\frac{\exp(q^\top key_{i^*}/T)}
{\sum_{i\in I}\exp(q^\top key_i/T)}.
\]

Положительные примеры обязаны обозначать действительно нужную запись; «ближайшая по самой модели» не является независимой меткой.

## 2a. Недостающие auxiliary targets: явное закрытие всех голов

В первоначальном draft value/risk/conf/wake/halt были названы, но не полностью включены в L1. Это было ошибкой спецификации: например w_conf вообще не имел target и ∂L1/∂w_conf=0. Исправленная функция содержит

\[
L_{\rm aux}=\lambda_V m_V(\tanh(l_V)-G_{norm})^2
+\lambda_R m_R BCE(y_{risk},\sigma(l_R))
+\lambda_C m_C BCE(y_{correct},\sigma(l_C))
+\lambda_W m_W BCE(y_{wake},\sigma(l_W))
+\lambda_H\sum_k m_{Hk}BCE(y_{halt,k},\sigma(l_{Hk}))
.
\]

l_V=w_valueᵀh+b_value; l_R=w_riskᵀh+b_risk; l_C=w_confᵀh+b_conf; l_W=w_wakeᵀf_meta+b_wake; l_Hk=w_haltᵀh^k+b_halt. Здесь m — наличие именно независимой метки, а не другая обучаемая маска.

- G_norm=clip(G/G_cap,−1,1), G_cap>0 объявляется до сбора данных; для missing return m_V=0.
- y_risk∈{0,1} — размеченное независимым oracle нежелательное последствие/нарушение корректности конкретного предложения в текущей задаче; это прогноз, не замена gate. Без risk labels m_R=0 и нельзя заявлять обучение этой головы.
- y_correct∈{0,1} — независимая correctness текущего окончательного ответа/предложения. Это вспомогательная предсказанная confidence; held-out calibration выполняется отдельно. Прямого доступа к будущему label во входе нет.
- y_wake=1 для обязательной текущей owner-задачи/события, y_wake=0 только для independently labelled irrelevant optional ambient-event. STOP/REVOKE/DEADLINE/receipt обрабатываются вне learned wake и не могут быть им отключены.
- y_halt,k=1, если независимый dev-oracle уже считает решение на h^k достаточно правильным И ни одна разрешённая более глубокая depth на том же фиксированном примере не улучшает quality больше δ_halt при заданном cost-margin. Иначе0; если такого набора глубин/меток нет, m_Hk=0. Oracle считает bounded catalogue, его цена входит в training budget. Не использовать собственную confidence как target истинности.

Для logit-голов BCE derivative=(σ(l)−y)f, формы d либо32. Для value gradient wrt logit равен 2(tanh(l_V)−G_norm)(1−tanh²(l_V)); затем умножить на h. Таким образом все перечисленные веса имеют конкретный target и differentiable loss при наличии соответствующих данных. Отсутствующие метки не создаются формулой.

Для W_M фиксируется offline каталог C_mask={нулевая маска, все n_b одиночных блока, полная маска}; недопустимые по бюджету варианты исключаются до sampling. Никакого скрытого 2^{n_b}-перебора нет. Scores L(M)=Σ_j M_j ℓ^M_j; π_mask(M)=softmax_{C_mask,feasible}(L(M)/T_sched), T_sched>0. Если budget не позволяет работу — deterministic abstain, gradient0. Цену вычисления logits/normalization каталога включают в offline cost; runtime BudgetTop и train-catalog различаются, поэтому перевод требует dev-проверки.

ζ=(W_M,b_M,w_halt,b_halt,w_wake,b_wake). Stochastic training policy: Bernoulli wake для optional events; categorical mask; затем hazard p_k=σ(l_Hk) остановки после каждого k. Probability K равна p_K∏_{j<K}(1−p_j); на budget/Kmax p_K=1 принудительно. Mandatory events не проходят random wake. Все вероятности определены на конечных admissible траекториях, π_ζ — их произведение. L_sched-policy — название уже учтённой в L1 task-loss+стоимости на этой sampling trajectory, а не дополнительное слагаемое или новая матрица. Expectation берётся единожды в J(Θ).

Полный gradient при прямой зависимости loss от ζ:

\[
\nabla_\zeta\mathbb E_{\pi_\zeta}[L]
=\mathbb E[\nabla_\zeta L+(L-b(x))\nabla_\zeta\log\pi_\zeta].
\]

Упрощённая score-only формула §3 относится только к части loss без прямой зависимости при фиксированной sampling trajectory. Head auxiliary losses имеют direct-gradient и не должны его терять. Остальные Θ влияют на π через h,z,s; их pathwise derivative недостаточна. Для полного параметрического набора, включая ζ⊂Θ:

\[
\nabla_\Theta\mathbb E_{\pi_\Theta}[L_{total}]
=\mathbb E[\nabla_\Theta L_{total}
+(L_{total}-b(x))\nabla_\Theta\log\pi_\Theta].
\]

Производные здесь вычисляются при фиксированной sampled discrete trajectory, включая зависимость policy logits от h,z,s. L_total — вся правая часть исправленной L1, включая L_aux. Baseline не зависит от sampled decision при фиксированном history, и его градиент не применяется в score baseline. Stop-gradient от h/z к scheduler был бы surrogate/semi-gradient, а не точный gradient данного expected objective. Training cost учитывает все sampled computations.

## 3. Градиенты всех непрерывных частей

Для CE с logits l=W h+b:

\[
\frac{\partial L}{\partial W}=(p-y)h^\top,\quad
\frac{\partial L}{\partial h}=W^\top(p-y),\quad
\frac{\partial L}{\partial b}=p-y.
\]

При tied E_text градиенты входного lookup и выходной матрицы **суммируются в один тензор**, а параметры не удваиваются.

Для одной ветви F_j:

\[
J_{lj}=D_{\tanh}(B_{lj}u+b_{lj})B_{lj}
D_{\tanh}(A_{lj}h+C_{lj}z+a_{lj})A_{lj};
\quad
J_F[j,:]=J^{-1}\sum_l J_{lj}.
\]

Соседние матрицы умножаются последовательно: b×b, b×χb, χb×χb, χb×d; итог b×d. Для D_M блочно-диагональной маски:

\[
J_{k}=I-\alpha D_M+\alpha D_M J_F,\qquad
\bar h_k=J_k^\top\bar h_{k+1}+\partial L_k/\partial h_k.
\]

Параметрическая производная F добавляется на **каждом** повторении общих Φ_R, не только на последнем. Затем chain rule через z,U_s,U_g,Eτ и чтение M; backprop через несколько событий нужен для credit assignment. Градиенты памяти offline вычисляются через записи в ограниченном unroll; detached runtime store сам по себе не даёт gradient W_k/W_v от будущего чтения.

Frozen hard masks, grammar selection, TopK и argmax не дифференцируются «как будто гладкие». Точные производные выше условны на фиксированную дискретную траекторию. Для обучения selector используется одно из двух явно определённых средств:

1. Offline stochastic policy π_ζ(M,K|x,budget), только допустимые варианты, с
   ∇ζ E[L]=E[(L−b(x))∇ζ logπζ], baseline не зависит от выбранного M. Этот estimator несмещён для ожидаемого loss при конечных integrable траекториях и parameter-independent окружении. Он может иметь большую дисперсию.
2. Supervised labels «минимальная цена среди решений с quality≥threshold» на фиксированном dev-пуле. Если допустимых решений нет — отдельный abstain target.

Straight-through был бы приближённым estimator и здесь не объявляется точным. Runtime-masks выбираются детерминированно; разрыв train/runtime проверяют отдельно.

Projected SGD:

\[
\Theta_{r+1}=\Pi_\Omega[\Theta_r-\eta_r\widehat{\nabla L}].
\]

Ω задана в 03 и имеет вычислимую проекцию по строкам. Для nonconvex общей сети не доказаны глобальная сходимость, нахождение минимума или качество. Truncated BPTT отбрасывает дальние производные: его bias явно учитывается, а delayed receipts вне окна не делают градиент истинно end-to-end.

## 4. Долгие задачи и credit assignment

Trace каждого dispatch хранит h_issue, verb, goal, v, ν,e, expected и время, а не использует h в момент позднего receipt. Для multi-step цели:

\[
G_t=\sum_{u\ge t}\gamma_d^{\,\tau_u-\tau_t}r_u,\quad 0<\gamma_d\le1.
\]

Единица времени фиксирована в manifest; иначе размерность степени не определена. Reward r_u — независимое выполнение предиката/стоимость, не текст «успех». TD-loss (G_t−VΘ(h_t))² можно использовать только при обоснованной policy-оценке. Наблюдательные траектории не дают идентифицированный counterfactual reward для невыбранных действий.

При offline policy learning importance ratio нужен только при positivity: π_behavior(a|x)>0 для каждого оцениваемого a, и при отсутствии скрытого confounding либо подходящем дизайне. Без этого разрешена imitation/prediction, но не утверждение о причинной оптимальности.

По умолчанию dangerous exploration на телефоне отсутствует; недостающие альтернативы получают из разрешённого стенда или размеченных демонстраций.

## 5. Online P: точная локальная задача

Во время обычного использования Θ и Γ фиксированы. Для свежего receipt выбранного a, y∈{0,1}, h=h_issue:

\[
q=\sigma((W_p[a,:]+P[a,:])h+b_p[a]),\quad
d_h=\epsilon+\|h\|_2^2,
\]
\[
P'_a=\Pi_{\|p\|_2\le p_{\max}}
\left[(1-\eta\lambda)P_a+
\eta\frac{(y-q)h}{d_h}\right],\qquad
P'_j=P_j\;(j\ne a).
\tag{L2}
\]

ε>0, pmax>0, λ≥0; q пересчитывается на **текущей P** с замороженным h_issue. Прогноз q_issue хранится отдельно для честной оценки калибровки. Поэтому несколько допустимых delayed receipts не применяют неконтролируемый stale gradient.

L2 — projected gradient для выпуклой по p локальной функции

\[
f_{h,y}(p)=\frac{BCE(y,\sigma(l_0+p^\top h))}{d_h}
+\frac{\lambda}{2}\|p\|_2^2.
\]

\[
\nabla f=(q-y)h/d_h+\lambda p,\quad
\nabla^2 f=q(1-q)hh^\top/d_h+\lambda I,\quad
L_f\le1/4+\lambda.
\]

При 0<η≤1/L_f и неизменном примере projected-gradient уменьшает f:

\[
f(P')\le f(P)-(\eta^{-1}-L_f/2)\|P'-P\|^2.
\]

Доказательство: оптимальность евклидовой проекции даёт
⟨∇f,P'−P⟩≤−||P'−P||²/η; подставить в descent lemma. Это локальная теорема, **не улучшение всех целей**.

Если λ=0 и проекция не активна,
Δl=η(y−q)||h||²/d_h. При h=0 изменяется ровно ничего. С λ>0 знак Δl уже не обязан следовать y. После проекции гарантируется cap и локальное f-descent при условиях выше; глобальная монотонность не следует.

UNKNOWN, stale, STOP, denied, replay и предикат без надлежащего наблюдения дают P'=P. M/HYPOTHESIS и diagnostic U могут изменяться без повышения истинности записей.

## 6. Консолидация, забывание и калибровка

Новые verified эпизоды хранятся с квотами; консолидация Θ выполняется отдельно с replay старых категорий. L_retention может сочетать replay-loss, distillation фиксированной предыдущей версии и Fisher-weight penalty. Ни EWC-подобный штраф, ни distillation не доказывают zero forgetting.

Для фиксированного конечного контрольного набора T_control можно требовать **покомпонентное** Q_i(new)≥Q_i(old) при детерминированном oracle. Тогда принятие версии математически делает именно этот вектор монотонным. Шумные оценки/неизвестное распределение такого вывода не дают; confidence bounds и независимый retest нужны отдельно. Контрольный набор, используемый для допуска, перестаёт быть нетронутым holdout.

Калибровка q: Brier, log-loss и reliability-bin error на отдельной calibration-части; temperature scaling только по ней. Высокая confidence не равна достоверности. Distribution shift может испортить любую прежнюю калибровку. Abstention оценивается risk–coverage кривой с минимальным покрытием обязательных задач.

## 7. Идентифицируемость и бюджеты обучения

Permutation скрытых координат с согласованной перестановкой весов даёт ту же функцию. Поэтому индивидуальные «значения нейронов» не идентифицируются даже при идеальных данных. Два мира с одинаковыми O_obs до действия и различными последствиями не различимы из одного прошлого наблюдения.

Параметры P для действия без verified receipts не идентифицируются. Число миллисекунд логов не равно числу независимых задач. Для fixed policy и iid бинарных задач Hoeffding:

\[
n\ge\frac{\log(2/\delta)}{2\varepsilon_q^2}
\]

даёт ошибку доли ≤εq с вероятностью ≥1−δ. При δ=.05, εq=.02 нужно n≥4612 независимых испытаний. Это sample bound для **оценки фиксированной политики**, не число training examples, достаточное для обучения всех Θ.

Обучение: T_train=epochs×tokens×C_forward×κ_back; κ_back зависит от unroll/backend и checkpointing. Training RAM ≥16PΘ + activations + batch buffers в FP32 Adam-режиме. Нельзя установить стоимость обучения полноценной модели без corpus size, unroll и оборудования. Сейчас обучение не запускалось.
