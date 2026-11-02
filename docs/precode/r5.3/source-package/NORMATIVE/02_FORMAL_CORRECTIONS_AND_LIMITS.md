# R5.3 composite — математические исправления и строгие пределы claims

Здесь оформлены поимённые отмены. Полный исходный расчёт остаётся в прилагаемых Astra/R5.2 файлах. Статус *обоснованного локального утверждения* не означает `GLOBAL_MATH_PASS`.

## W4 — корректная оценка только для общей маски

Пусть `T_M(h,z)_j=(1−alpha M_j)h_j+alpha M_j F_j(h,z)`, `M_j in {0,1}`, `0≤alpha≤1` и `Lip∞F(·,z)≤gamma<1` при фиксированном z. Для двух состояний применяется **та же заранее фиксированная маска** M. Тогда

`||T_M(h,z)−T_M(h',z)||∞ ≤ c_M ||h−h'||∞`, где `c_M=max_j[1−alpha M_j(1−gamma)]`.

Треугольное неравенство по координате: `|(1−aM_j)Δh_j+aM_jΔF_j|≤(1−aM_j+aM_j gamma)||Δh||∞`.

При `alpha=.5, gamma=.9` full mask имеет `c_M=.95`, любая sparse маска с нулём в координате — `c_M=1`. Следовательно, старое безусловное `0.95^K` для sparse/adaptive **ОТМЕНЕНО**.

**Разные z, одинаковая заранее фиксированная последовательность масок:** при `Lip_z F≤L_Fz`, `e_{k+1}≤c_{M_k}e_k+alpha L_Fz||z−z'||∞`. После K шагов `e_K≤(product c)e_0+alpha L_Fz||Δz||∞ sum_i(product_{j>i}c_{M_j})`. Для constant sparse `c=1` сумма ровно K. Для z, зависящего от памяти/внешних событий, W4 не даёт полного сертификата.

**Контрпример адаптивного hard selector:** `F=0, alpha=.5, d=2`, `Mask(h)=(1,0)` при `h1>0`, иначе `(0,1)`; `h=(epsilon,1)`, `h'=(-epsilon,1)` ⇒ `||Δh||∞=2epsilon`, `||ΔT||∞=.5`, отношение `1/(4epsilon)→∞`. Это отвергает универсальную оценку для произвольных *пороговых* селекторов, **но не означает**, что каждый возможный адаптивный селектор обязательно разрывный.

**Fair-sweep** допускает оценку .95 *за полный sweep* только при общих масках, постоянном z и обновлении каждого блока относительно общей fixed point; случайные K≤8 сами sweep не гарантируют.

**Осторожность с текущей Astra_02 W4:** историческое обозначение `b_0` без самостоятельного сертификата нельзя подставлять в общий `L_event` как доказанный коэффициент. Для transfer bound сначала явно вывести `L_Fz` и условия memory/input. `Lip F(z fixed)` ≠ `Lip всего организма`.

## Memory — смысловое чтение НЕ точное

`r=sum_i omega_i v_i`; две записи `v` и `-v` с одинаковым key и весом 1/2 дают ноль. Из r нельзя восстановить обе записи, их provenance и конфликт. Старое обещание lossless из semantic aggregate **ОТМЕНЕНО**.

Отдельный deterministic `RetrieveExact(query,scope,k,budget)` — операция ограниченного локального хранилища, не второй reasoning agent. `RetrieveSemantic(q)` возвращает `SUMMARY_ONLY` и не удостоверяет completeness. Приоритет статусов **только при их условиях**:

1. `DENIED` при запрещённом scope или отзыве доступа до выдачи/использования — ни одного защищённого payload;
2. `UNKNOWN` при недостоверном snapshot, индексной/файловой порче, неопределённой канонизации/версиях;
3. `TRUNCATED` при `matched_count>k` либо недостаточном бюджете, **даже если уже виден конфликт**; continuation + matched lower bound, нельзя claim complete;
4. `CONFLICT` только после полностью сертифицированного snapshot-scan со всеми релевантными conflicting entries в лимите;
5. `COMPLETE` только после проверенного exhaustive scan разрешённого индексированного snapshot в допустимом scope, при отсутствии конфликтов и превышения лимита.

`COMPLETE` ≠ истина фактов мира, полная история жизни или текущий OS state. ID обязательно включает `store_generation, slot_generation, digest, source, kind, schema, consent_epoch, boot/session, TTL, model compatibility, raw payload ref` (подробный контракт `R52/02`). Нельзя изменять permission/provenance по предложению модели. При ABA, late revoke, смене boot/version старые refs не валидны. Существование записи как *исторического факта* не доказывает `VERIFIED_CURRENT`.

Условная корректность требует `A_tx/A_fs`, atomically consistent snapshot и проверенного носителя. Следующие тесты обязательны после реализации: k16/17matches, ±v, consent revoke, corruption, ABA, reboot, concurrent mutation, forged timestamps и conflicting time scopes.

## WAKE — не выдавать metadata-only за акустический wake

`w_wake` из B2 — `1x32` metadata-only. **Он не распознаёт звук**. Для исследовательского обязательного пути: local microphone → bounded VAD/PCM → existing `W_audio` → same shared `F` → `W_ctc` → explicit keyword grammar → wake proposal. Его включение по материалам `R52/03` является **кандидатом**, требующим owner choice, датасета и тестирования false wake/hour, false reject, latency и idle energy. Если из-за вычислительных/энергетических затрат нужен `acoustic head 1xd`, обновлять полный тензорный manifest/ABI/MAC/gradient и заново проверять схему. Нельзя просто заменить `w_wake 1x32` и сохранить старые parameter counts. Дискретная decision-to-reward связь требует отдельной корректной training semantics: для supervised wake labels можно использовать CTC/CE/BCE, а при policy-selected actions — score term по условиям Astra L5; stop-gradient surrogate не называть unbiased.

## SENSOR — измерение, отсутствие показаний, точность

32 значения + 32 availability mask → `W_sensor` → same F. Versioned typed dictionary обязателен: channel, SI unit, range, scale, monotonic timestamp/source/generation, freshness TTL, permission/provenance; `mask=0` никогда не означает физическое значение 0. `L_sensor` как **новый предложенный** teacher CE по канонической сериализации, не существующий проверенный training signal Astra. Для требуемой физической точности приоритет имеет native typed reading и его verifier, не сгенерированное нейросетью округлённое число. Критерии будущего испытания: value/unit/missing/stale/reboot, independent oracle.

## Learning и unbiased/conditional границы

Истинная полная цель training: `ASTRA_03` **L3a**, а не сокращённая `GROK_R53` Jbase L3. В том числе по каждому классу j:

`J(Theta;mu)=E[sum_k lambda_k L_k + L_task +lambda_c C/C_ref + sum_j mu_j (1{Z=j}/pi_j)(A(tau)−(1−c_j))]`.

Здесь `pi_j>0`, `c_j` — candidate class-specific coverage floor, `A` — bad unfinished/abstain indicator, `mu_j` — dual multiplier. Идентичность `E[1{Z=j}f/pi_j]=E[f|Z=j]` верна при соответствующем sampling law; без pi>0 делить нельзя. Примеры R1/R2 failure остаются в исходных audit docs. Обозначение `q_j` в Grok R5.3 gates означает *качество*, и не заменяет `c_j` для покрытия.

Важны полные Astra L4 (smooth BPTT), L5 (score estimator для discrete sampled policy), censored/terminal loss, supervised masks, frozen P=0 для offline path, CTC whole utterance и явные границы TBPTT/STE. **Не объявлять** их воспроизведёнными одним Jbase. Наличие формы не гарантирует сходимость обучения или качество новой сети.

## Trust / STOP / provenance и офлайн

System consent/permissions/STOP/native readback расположены за внешней trusted boundary. **Старый Jarvis OwnerGate не является обязательным компонентом UNO**. Условные свойства зависят от A_cap/A_tx/A_fs и реальных Android tests. STOP до linearization блокирует dispatch; после — не отменяет уже переданный эффект. Stale receipt/другая epoch → UNKNOWN; no blind retry. Receipt совпавшего состояния не доказывает, что изменение *вызвал* UNO.

Строгий offline: app-private или независимо проверенный локальный источник по умолчанию. SAF provider без подтверждённой локальности может сам загрузить документ по сети даже при отсутствии INTERNET у UNO; такое нельзя сертифицировать offline. Предложенная безопасная политика — `UNSUPPORTED_OFFLINE_SOURCE` или отдельный opt-in вне строгого offline-claim. Это решение области продукта на утверждение владельца.

## Masks / costs / NCR и остальные пределы

Для 16 блоков cyclic-prefix masks = `16*(16−1)+1 = 241`, arbitrary nonempty = `2**16−1 = 65535`. Параметры `B2`, `LR2`, `H2` имеют различные возможности, без trained quality нельзя выбрать доминирующее семейство. Файл INT8 + runtime buffers != peak PSS; MAC не являются Joules, latency или device PASS. NCR-EVO bounded loops доказывают termination алгоритма отбора, **не** semantic correctness/реальную регенерацию/выигрыш над baselines. Trial selection и adaptive holdout требуют отдельной статистической постановки и fresh locked test.
