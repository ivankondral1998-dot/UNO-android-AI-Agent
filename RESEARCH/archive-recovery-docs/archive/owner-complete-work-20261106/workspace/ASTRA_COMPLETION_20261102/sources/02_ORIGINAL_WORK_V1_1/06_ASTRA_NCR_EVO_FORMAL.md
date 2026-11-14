# 06. NCR-EVO: отдельный лабораторный цикл

Оригинал NCR_EVO_ASTRA_RESEARCH_BRIEF_2026-11-01.md прочитан целиком и сохранён в originals. Он объявляет гипотезу, а не готовую технологию. «Астра» здесь — адресат исходной экспертизы; NCR-EVO не тождественен inner-loop h и не вводит второй постоянно работающий мозг на Android.

## 1. Минимальная обоснованная комбинация

| Метод | Полезная роль | Ограничение / решение |
|---|---|---|
| Genetic programming | Изменение структуры AST | Ограниченная типизированная грамматика |
| Grammar-guided synthesis | Валидность конструкций, конечные loops | Не доказывает смысловую корректность |
| MAP-Elites/QD | Несколько поведенческих ниш | Использовать небольшой ограниченный архив |
| Novelty search | Сохранение ступеней | Только квота внутри QD, не самостоятельная цель |
| Surrogate-assisted evolution | Сокращение дорогих оценок | Сначала доказать выгоду относительно QD без surrogate |
| Active learning / uncertainty | Информативная выборка | Не только p≈0.5, обязательная exploration |
| Multi-fidelity | Cheap/static→host→device | Низкая fidelity не заменяет высокий уровень |
| Bayesian optimization | Формальный acquisition при модельных допущениях | Не требуется отдельный сложный optimizer |
| Большой LLM code generator | Может дать богатые мутации | Не обязателен; стоимость обучения/вызова должна окупиться |

Выбор: ограниченная AST-грамматика + QD + лёгкий surrogate + randomized sampling + независимый evaluator. Польза обучения генератора Θ_M не предполагается заранее. Первый генератор допустимо эвристический; это не отменяет требование реальных структурных изменений алгоритмов.

## 2. Типы и границы

G_const — immutable grammar typing rules, capabilities, resource caps, reference oracle и promotion policy. g^evo — набор допустимых mutable combinators/описаний модулей, versioned отдельно.

c=(AST,hash,parentHashes,grammarVersion,features,resourceCertificate). AST — чистая программа с явно ограниченными массивами/циклами. Никакой сети, файловой системы, Android permissions, eval/native escape, записи trusted state. Не прошедший H(c)=1 не исполняется; H=1 само по себе не равно CORRECT.

Φ_S — веса surrogate признаков f(c)∈R^p, p=32; он выдаёт correctness probability, quality delta, log-cost и модельную uncertainty. Например regularized linear regression для непрерывных labels и logistic для correctness. Confidence из модели не является свидетельством.

E_eval(c,fidelity,seed,tasks) возвращает **типизированный** вектор y=(correctness,robustness,quality,time,energy,RAM,descriptor,failures,censorFlags). При timeout цена известна до cap, завершённое качество не известно; нельзя подменять отсутствующую energy нулём.

Архив A имеет K_cell конечных descriptor-ячеек и квоты r элит, s ступеней, f воспроизводимых провалов на ячейку:
|A|≤K_cell(r+s+f). Расчётный вариант K_cell=64,r=2,s=1,f=1 →≤256 активных записей. Длинный лог имеет отдельную disk-quota и дедупликацию; «полный лог навсегда» при конечном диске не обещается.

Descriptor задаётся до эксперимента: например algorithm family × memory class × robustness class. Изменение descriptors при просмотре test-результатов — новый исследовательский этап, иначе создаёт подгонку.

## 3. Порождение, выбор и защита от selection bias

\[
c_i\sim M_{\Theta_M}(parent,g_n^{evo},\xi_i),\quad
parent\sim ParentSelect(A_n),\quad
\mathcal P=\{c_i:H(c_i)=1\}.
\]

Hash-duplicates устраняются до дорогой оценки. Статически неверные варианты получают reason, а не empirical-failure label поведения.

Нормировать признаки приобретения в [0,1] на dev-статистике:

\[
u_i^{acq}=
w_q\max(\widehat{\Delta q}_i-\delta_q,0)
+w_u\hat u_i+w_d\,nov_i+w_b\,coverage_i
-w_c\,\widehat{cost}_i.
\]

Если novelty ещё не измерена, это **предсказанная** novelty по структуре, не факт нового поведения. Для batch B_size=b_deep выбор iid с возвращением:

\[
\pi_i=\varepsilon/N+
(1-\varepsilon)\frac{\exp(u_i^{acq}/T)}
{\sum_j\exp(u_j^{acq}/T)},\quad
p_i=1-(1-\pi_i)^{b_{\rm deep}}.
\tag{E1}
\]

ε>0,T>0; N=|P|. Для пустого пула — no-evaluation. Оценить уникальные выбранные программы; повтор в batch не требует нового запуска. Резерв b_deep C_deep,max обеспечивает бюджет даже при разных реальных ценах. Это конкретный механизм с известными inclusion probabilities; произвольный top-k+ранняя остановка требует другого расчёта p_i.

Для фиксированной функции потерь ℓ_i(φ), условно на данном пуле:

\[
\widehat R(\phi)=N^{-1}\sum_{i:I_i=1}\ell_i(\phi)/p_i,\qquad
\mathbb E[\widehat R(\phi)|\mathcal P]=N^{-1}\sum_i\ell_i(\phi).
\]

Доказательство: E[I_i]=p_i, линейность ожидания; независимость I_i между собой не нужна. Это unbiased estimate finite-pool risk **для фиксированной φ**, не гарантия generalization обученного minimizer. Малые p дают большую дисперсию. Clipped weights уменьшают дисперсию с bias; их нельзя назвать несмещёнными. Отдельная случайная calibration-выборка и exploration нужны в любом случае.

Surrogate Fit использует только реально полученные labels и censor flags, rare generator-update — отдельный эксперимент. Никакие raw predictions не записываются как проверенная correctness.

Boundary-only counterexample: две области программ X и Y. В X предиктор correctness≈0.5, но все корректные программы бесполезны; в Y correctness≈0.99 и редкие качественные решения. Выбор только X может дать ноль полезных улучшений при лучшей калибровке. Поэтому entropy sampling и поиск полезных программ — разные цели.

## 4. QD и принятие

Сначала исключить нарушения hard contracts. В ячейке хранить ограниченный Pareto-набор по quality, robustness, cost; при переполнении — заранее определённая crowding/tie rule. Ступень с плохим quality может сохраняться только в s-квоте за новый descriptor/структурное свойство. Хранение не равно promotion. Failures полезны как регрессии и отрицательные labels, но их количество не должно вытеснять все элиты.

Одно поколение:

1. Проверить оставшийся ресурс и отсутствие новых trust нарушений.
2. Родители→bounded mutation/recombination→H.
3. Дедупликация→features→surrogate→E1.
4. Изолированный E_eval на dev/stress.
5. Append provenance/results→bounded QD update.
6. Fit Φ_S с учётом p_i; обновить dev-calibration.
7. При заранее заданном checkpoint только зафиксированный finalist идёт независимому оценщику.
8. Если budget исчерпан, нет admissible candidates или нарушен trust-контракт — STOP.

Для ограниченного AST допускается полная проверка на конечном входном домене, но его размер обычно экспоненциален. Для произвольных программ эквивалентность/termination не решаются общим алгоритмом. В данном DSL bounded loops гарантируют termination, но не правильный смысл.

## 5. Три поколения вручную: алгоритм восстановления

Это **ручная математическая иллюстрация**, не запущенный эксперимент, не dataset результата UNO и не замена всей архитектуры игрушкой.

Контракт задачи: m ключей; массив records r_i=(key,seq,value,valid), i=1…n. seq ограничен, valid предоставлен неизменяемым validator. Вернуть для каждого ключа value записи с лексикографически максимальной (seq,i) среди valid records этого ключа; если записей нет — UNKNOWN. Кандидат не может сам изменить valid.

Предок c0: для каждого key просканировать все records, отфильтровать valid и выбрать max(seq,i). Сложность O(mn+m), workspace O(m). Корректность очевидна из определения max конечного множества; пустой случай задан.

**G1, структурная мутация:** заменить outer-key-loop одним record-loop и индексированной записью в output[key]. c1 перезаписывает последней valid записью, не сравнивая seq. Это реальное изменение алгоритма и сложности, но неверно на переставленных records. Другой c1b сравнивает seq, но теряет valid-filter. Оба допускаются только в ступени, никогда в trusted runtime.

**G2, рекомбинация исправлений:** c2 — один record-loop; сначала valid и key-range, затем compare(seq,i) с best[key], заменить при большем tuple. Перед циклом initialize best=UNKNOWN. Сложность O(n+m), workspace O(m). Индукция по i: best[key] равно max среди первых i допустимых records; база UNKNOWN, шаг либо не меняет множество, либо добавляет один элемент и берёт max. На i=n выполнен контракт **для всех bounded входов**, не только для примеров.

**G3, функциональное восстановление:** c3 добавляет режим Repair(D,authenticatedIntact,records). Вне damaged-mask D сохраняет только slots с независимым сертификатом равенства контракту F на ТОМ ЖЕ recordsDigest, validatorVersion и target-epoch; аутентичности байтов недостаточно. Для D применяет c2-фильтр, затем собирает полный output. Если current-context correctness certificate отсутствует — slot включается в D; если нет достаточных records — UNKNOWN. Корректность следует из контракта c2 на D и независимой правильности intact на дополнении в том же контексте records. Например authentic value4/seq1 при valid records seq2/value7 НЕ является intact-correct; этот slot обязан попасть в D. Сборка dense-output требует Ω(m); нельзя заявлять O(|D|) на весь результат.

| Ручной случай, m=2 | Ожидаемый output | c0 | c1 | c1b | c2 |
|---|---|---|---|---|---|
| (1,1,4,T),(1,2,7,T),(2,1,3,T) | (7,3) | PASS | PASS | PASS | PASS |
| (1,2,7,T),(1,1,4,T) | (7,UNKNOWN) | PASS | FAIL: 4 | PASS | PASS |
| (1,1,4,T),(1,9,99,F) | (4,UNKNOWN) | PASS | PASS | FAIL: 99 | PASS |
| (1,2,5,T),(1,2,6,T) | (6,UNKNOWN) | PASS | PASS | PASS | PASS |

Cheap features: nested-loop, has-maxseq, has-validfilter, dense-workspace, repair-mask. Никакие surrogate scores не выдаются за измерения. Накопленный опыт G1 — нарушения order-invariance и valid-filter; G2 использует оба исправления; G3 использует current-context certified correctness, а не только authenticated provenance. Архив хранит c0 и c2 в разных cost/structure-нишах, c1 в единственной ступени, его ошибки в failure-квоте. Если веса surrogate доступны, эти **ручные** метки могут быть учебным примером, но здесь Fit не запускался.

При n=1000,m=128 c0 выполняет 128000 проверок принадлежности key, c2 —1000 проверок/индексированных разборов и ≤1000 сравнений tuple плюс initialization 128. Это аналитические primitive-counts, не walltime и не ускорение «в 128 раз». c2 подтверждает возможность полезной алгоритмической мутации в этой задаче; не доказывает эффективность эволюционного поиска, который её нашёл бы.

Если повреждён весь archive и исходные records утрачены, контракты не определяют конкретные values: c3 обязан вернуть UNKNOWN/rollback. Regeneration не создаёт потерянную информацию.

## 6. Бюджет и предел выигрыша

\[
C_{\rm total}=\sum_{i=1}^N(C_{{mut},i}+C_{{static},i}+C_{{feat},i}+C_{{sur},i})
+\sum_{i\in U}C_{{deep},i}+\sum_{j=1}^{J_{\rm dev}}C_{{device},j}
+C_{\rm fit}+C_{\rm QD}+C_{\rm oracle}+C_{\rm isolation}+C_{\rm IO}.
\]

Цена — вектор (CPU-seconds,joules,RAM,disk), либо заранее объявленная скаляризация с единицами. J_dev≪|U|≪N — желаемый режим, не закон. NN surrogate может быть дороже сэкономленных deep calls.

Для фиксированного пула, вероятность полезности θ_i и E1:

\[
\mathbb E[N_{\rm useful-evaluated}|\mathcal P]
=\sum_i p_i\theta_i.
\]

Это число полезных уникальных кандидатов, не новых QD-ячеек: несколько кандидатов могут попасть в одну нишу. Улучшение поиска требует превысить baseline yield при одинаковом **полном** C_total, а не одинаковом числе кандидатов.

Иллюстрация цен: N=1000, cheap=1, deep=1000 условных CPU-units, b_deep=50, прочее=0. Full-eval стоит 1 001 000; selected-eval ≤51 000; отношение≈19.63. Это лишь отношение цен при фантастическом отсутствии прочих расходов и без гарантии обнаружения полезных решений. Если все полезные варианты не выбраны, полезное ускорение равно нулю. Универсального положительного lower-bound speedup нет.

## 7. Эксперимент опровержения и статистическая мощность

Группы: A random+single-best; B обычный QD; C QD+surrogate+E1; D1=C без обучения; D2=C без novelty. Один grammar, oracle, задачи и общий ресурсный cap; все генерации/отборы/обучение входят в cap. Сравнение по нескольким seeds и семействам задач; train/dev/stress не пересекаются с locked independent test.

Primary endpoint: независимо полезные различные алгоритмы на единицу полного бюджета либо заранее фиксированная bounded utility на семейство задач. Нельзя после просмотра результатов выбрать только выгодную метрику.

Для primary bounded utility заранее фиксируются равные total-budget B_lab>0 и K_out≤256 допустимых итоговых кандидатов. Определить U=min(K_out,N_independently_useful_distinct)/K_out∈[0,1]; D_i=U_C,i−U_baseline,i. Одна клетка с несколькими эквивалентными решениями даёт одно distinct achievement по заранее заданному oracle. Тогда E2 применима именно к этой utility; Δ=.05 означает5 процентных пунктов нормированной utility, не произвольные алгоритмы/сек. Raw yield/CPU и энергия — отдельные endpoints с собственным bound/тестом, не подставляются бесплатно в E2.

Для paired независимых task-family/seed единиц D_i∈[−1,1], mean Δ, нижняя односторонняя Hoeffding-граница:

\[
LCB=\bar D-\sqrt{2\log(1/\alpha)/n}.
\]

Чтобы при истинном Δ>δ обнаружить Δ>δ с ошибкой I рода ≤α и мощностью ≥1−β, достаточно:

\[
n\ge
\frac{2(\sqrt{\log(1/\alpha)}+\sqrt{\log(1/\beta)})^2}
{(\Delta-\delta)^2}.
\tag{E2}
\]

Вывод: tail bound для sample mean диапазона длины 2; threshold radius плюс отклонение с вероятностью β должны быть меньше Δ−δ. Для двух primary comparisons C>A,C>B, Bonferroni α=.025, β=.2, δ=0, Δ=.05: n≥8138 независимых paired единиц на каждый comparison. Это гарантирует power≥.8 для каждого отдельно; для совместного успеха C>A И C>B union-bound даёт лишь≥.6. Для joint power≥.8 надо задать β_each=.1, либо построить совместный тест; при той же α_each=.025 получается n≥9457 paired единиц на comparison. Это консервативная distribution-free оценка, **не утверждение о достаточности 8138 мутаций**, и не обещание доступной стоимости. Более эффективный preregistered sequential/pilot variance design возможен.

Повторные проверки одного и того же holdout адаптируют поиск к нему. Допуск: freeze finalist до test и использовать fresh independent test-data для последующих адаптивных finalists. Alpha-spending контролирует сумму ошибок только при валидных условных p-values; оно НЕ исправляет reuse одного раскрытого holdout. Для fixed заранее объявленного конечного семейства гипотез допустим simultaneous uniform bound. Для адаптивного выбора на том же holdout нужен отдельно доказанный reusable-holdout/anytime-valid механизм, которого здесь нет. Clustering по task-family/seed обязателен; тысячи зависимых мутаций не дают тысячи независимых replicates.

Если LCB_C−B/А не выше δ при запланированной мощности — выигрыш **не подтверждён**. Это не доказывает равенство методов. Если upper-bound≤δ, можно отвергнуть практически значимое преимущество в заданном домене. Stop: trust violation, исчерпание бюджета, систематический oracle exploit, недопустимый crash/timeout, заранее заданный futility threshold.

## 8. Связь с UNO и неизменность доверенной границы

Mutable graph-кандидаты UNO допускаются только через проверяемый constructor family Γ_v и manifest norm/resource constraints. Архив лаборатории не доступен runtime как executable. В evaluator нет production capabilities. Promotion требует independent contracts/norm/resource review, новый device PASS и отдельное owner approval; результат — новая подписанная версия v и новая ν. Авторизация и verifier никогда не являются targets мутации.

Доказательство невмешательства: при A_cap единственный доступный effect кандидата — ограниченный output в лабораторный evaluator; нет пути capability к T. Поэтому по индукции поколений значения T и code G_const не меняются. Если evaluator исполняет arbitrary native code в том же привилегированном процессе, A_cap ложна и гарантия исчезает. H(c) и тесты не заменяют изоляцию.

Условия полезной интеграции: кандидат сохраняет весь interface; экономия/качество превосходят цену его поиска и переноса; сохраняются norms/safety obligations; есть независимая переносимость на Android. Эти условия сейчас REQUIRES_DATA. NCR-EVO остаётся лабораторной процедурой; постоянной энергии телефона он не потребляет до отдельно разрешённого эксперимента.

## 9. Безопасные детерминированные defaults архива

Внутри ячейки candidates сначала фильтруются по hard contracts, затем по Pareto dominance; одинаковые objective vectors разрешаются по hash лексикографически. Если nondominated>r, сохраняется минимум cost и максимум quality; если это один кандидат — следующий по quality затем cost затем hash. Это сознательная ограниченная аппроксимация frontier, не сохранение всего Pareto-set. Stepping-stone выбирается по structural novelty среди не-элит, затем hash; failure — самый ранний воспроизводимый новый failure-signature, затем hash. Descriptor thresholds фиксируются до test. ParentSelect: uniform по непустым ячейкам, затем uniform по elite/step квоте; failures не родители по умолчанию. Изменение этого правила — отдельная абляция.
