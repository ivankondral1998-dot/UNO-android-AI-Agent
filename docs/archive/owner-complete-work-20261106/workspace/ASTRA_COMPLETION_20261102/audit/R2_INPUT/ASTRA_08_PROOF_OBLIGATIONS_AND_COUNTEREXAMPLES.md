# ASTRA 08 — доказательства, контрпримеры и найденные исправимые дефекты

Это авторский математический проход. Независимые blind/crosscheck/final reports находятся в audit/ и ASTRA_10. Доказательство в идеальной модели не является выполненной проверкой Android или обученной модели.

## Т 1. Измеримость, тотальность и завершение

Допущения: конечные записи/очереди, фиксированный manifest, измеримое race-ядро до ближайшего таймера, trusted API с типизированным результатом или timeout. Каждый parser возвращает допустимый sum-type либо INVALID; каждой внутренней фазе соответствует producer. Allocation следует после проверки квот. Матрицы согласованы; для пустой памяти/каталога задан результат, знаменатели положительны. Конечная композиция измеримых операций задаёт тотальную δ; pushforward probability kernel сохраняет массу 1.

При обслуживании контроллера каждый work имеет конечные лимиты попыток, токенов, шагов и deadline. Ранг 01 исключает бесконечную внутреннюю работу. Это не доказывает завершение физического OS-действия или работу процесса, навсегда остановленного ОС.

Контрпример старому календарю: deadline наτ+1, но K_ext возвращаетΔ10 и completion с timestampτ+2. Сортировка после скачка не возвращает возможность своевременно остановить действие. S2 ограничивает время ближайшим событием; S3 использует известный outbox предыдущего перехода, без зависимости от будущего решения.

## Т 2. Ограниченность и контракция фиксированного F

База: s/g лежат в кубе, строки P — в шаре. tanh возвращает куб; h0 и active leaky update являются выпуклыми комбинациями; inactive координата сохраняется. Индукция по k/t сохраняет bounded h/s/g; sigmoid ограничиваетβ, projection ограничивает P. Для машинной арифметики нужны дополнительные finite checks и clipping округлений.

При fixed z ветвь имеет Lip≤||B||∞||A||∞≤.9. Усреднение и максимум по блокам сохраняют эту границу. Full step имеет c=1−α(1−γ)=.95; complete cube даёт unique fixed point и E_k≤c^kE0. При частичной общей маске ошибка не растёт. Если каждый блок обновлён за F_cov шагов, после обновления его error≤cE_start и граница сохраняется до конца покрытия. Поэтому весь sweep сжимает error. B2 sampling за K8 не гарантирует покрытия.

Контрпримеры: F=0,mask(1,0),h0=(1,1) навсегда оставляет вторую координату 1. Residual T(h)=h+tanh(−10h) имеет цикл±a, где 2a=tanh10a: положительный корень есть на(0,.5), поскольку производная разности в 0 положительна, а значение в.5 отрицательно. Clip не активен. Следовательно boundedness не означает convergence. Изменяющиеся z/Θ/маски исключают применение fixed-input теоремы. W4 допускает event Lip>1.

## Т 3. Квантование

Nearest rounding с шагом s даёт scalar error≤s/2, row-L1 error≤ns/2. Triangle inequality даёт decoded norm≤original norm+row error. Output error≤||ΔW||∞||x||∞. Через 1-Lipschitz tanh и fixed contractive map: E_next≤cE+ε, поэтому E_K≤c^KE0+ε(1−c^K)/(1−c). Sparse sweep допускает cE+F_covε.

Argmax сохраняется при top gap>2ε_l. Разные большие logits могут дать одинаковый machine sigmoid1.0; поэтому сравнивать надо logits. Decoded norm certificate не доказывает semantic quality.

## Т 4. Градиенты и локальное обучение

L4 — chain rule, tanh derivatives и outer products. B[b,χb]×A[χb,d] даёт Jacobian[b,d]. TiedE складывает lookup/output gradients, потому что параметр один.

L5 следует из ∂ΣπL=Σπ∂L+ΣπL∂logπ. Для baseline, независимого от текущего решения при фиксированной истории, Σb∂π=b∂1=0. Score term необходим для всехΘ, влияющих на z/h. Контрпример: z_θ=θ, B~Bernoulli(σθ), L=B. Pathwise derivative0, но ∂E[L]=σθ(1−σθ)>0. Offline objective использует P=0 как независимую константу. Если p(θ)=θ и L=(θ+p)², полная derivative8θ, а detached-p derivative4θ: текущий replay с detach был бы semi-gradient. TBPTT/STE в03 также не объявлены точной derivative полной истории/rounding.

P2: Hessian PSD, norm≤.25+λ. Оптимальность projection даёт ∇f·(p′−p)≤−||p′−p||²/η; smoothness завершает descent proof. Nonexpansive projection+Cauchy дают interference bound04; суммирование squared-distance recursion даёт realized-loss regretP3. Две задачи с одним h и противоположными y доказывают forgetting несмотря на local descent.

## Т 5. Ресурсный инвариант

Для аддитивного work/fuel перед primitive требуется c_i+reserve≤remaining; после него debitc_i. Индукция даётΣc_i+reserve≤B. Нужны корректные верхние цены и полный перечень операций. Для RAM/disk отдельно проверяется live+new+reserve≤cap до allocation; peak=sup_t live(t), освобождение учитывается после refcount0. Суммирование последовательных пиков не является равенством памяти. Finite headers не ограничивают память без квот на referenced payloads; B2 учитывает оба уровня.

Finite queue не гарантирует обслуживания при arrival rate>service rate. Одинаковый MAC не определяет bytes, ожидания или энергию. Маска после dense вычисления не экономит его MAC. d1024/K8/100audioframes дают 14.21G MAC/s с encoder/read/CTC, а не 138M на всю задачу; vocabulary добавляет 33.55M MAC на каждый output token.

## Т 6. Полномочия, replay и crash

При A_cap worker не имеет privileged dispatch или записи trusted state. Единственная gate-ветвь проверяет current cap/consent/epoch/STOP. Индукция по переходам доказывает, что любыеΘ/P не расширяют capability. STOP до linearization запрещает запрос; после неё возникший эффект не обязан отмениться.

A_tx атомарно фиксирует used/P-version/receipt/M-ref. При свежем уникальномν/e и model/goal/digest checks старый ticket не достигает learning. В P128 уникальность условна на отсутствие collision, bound05; точная A_gen требует отдельного monotonic anchor. PREPARED сохраняет MAY_HAVE_EXECUTED после crash, но не доказывает exactly-once физического действия.

PR3 trace: snapshot(epoch0,serial0)→proposal/ticket→STOP(epoch1)→restore(old0)→тот же proposal→старый boundary_pending ticket способен учить P. Это вывод по исходнику, не новая executed reproduction. PlainSHA допускает replacement+новый hash; authenticated old snapshot допускает rollback. Integrity, authenticity, freshness и semantic correctness различны.

## Т 7. Endpoint, censoring и причинность

Из 100attempts10 дают видимые TRUE,90 не дают label. Обучение только по видимым outcomes оценивает Pr(Y=1|R=1)=1. Мир с 90failures и мир с 90 ненаблюдаемыми successes дают одинаковые training labels, но разный physical success. Этот rate не идентифицирован. Тождество

\[
\Pr(R=1,Y=1\mid H)=\Pr(R=1\mid H)\Pr(Y=1\mid R=1,H)
\]

не требует MAR; B2 применяет его только к observable verified endpoint. Оценка множителей требуетданных.

TRUE после volume change не доказывает do-effect: человек мог параллельно установить то же значение. Predicate в одном sample не доказывает выполнение на всём интервале. Missing readback не является FALSE.

## Т 8. Регенерация и конечная информация

Полное стирание отображает разные F0/F1 в одинаковые доступные данные. Один repair output не совпадёт точно с обеими; randomized алгоритм также не гарантирует probability1 обоим. Конечное b-bit состояние различает≤2^b историй; большее число попарно несовместимых требований вызывает collision. Это не вывод конкретного числа neural parameters.

c2 из 06 корректен по prefix-max induction. c3 корректен на damaged set благодаря c2, на дополнении — только при current-context certificate. Аутентичное старое value4 при текущем max7 — контрпример условию «достаточно аутентичности».

## Т 9. Статистика и стоимость NCR-EVO

Вероятность ни разу не выбрать i за bIIDdraws равна(1−π_i)^b. Поэтому p_i=1−(1−π_i)^b, а E[I_iℓ_i/p_i]=ℓ_i для fixedφ и observed labels. Fitted minimizer, clipped weights, censoring и cross-fidelity extrapolation этого свойства автоматически не наследуют.

Hoeffding для range length2: Pr(mean−μ≤−r)≤exp(−nr²/2). Суммаα/βрадиусов≤Δ−δ даёт E6. Для двух comparisons нужны отдельные allocation:8138 дают 80% каждому, не conjunction;9457 дают консервативные80% joint только против δ0 при trueΔ.05. Для practical δ.02 при trueΔ.05 требуются26268; делитель в E6 равен(.05−.02)². Adaptive revealed holdout нарушает валидность отдельных tests; alpha-spending этого не исправляет.

Для fixed pool cost saving требует(N−K)D>F+O. Это не гарантирует useful yield: surrogate может пропустить все полезные программы. QD с конечными квотами не гарантирует сохранения будущей полезной ступени.

## Новые дефекты B1 и закрывающие изменения B2

|ID|Дефект / контрпример|Исправление и предел|
|---|---|---|
|C01|arbitrary time advance skips alreadyduedeadline|race-kernel01; scheduler fairness remains an assumption|
|C02|prediction indexed by verb uses h before args; twoargs differinsuccess|canonical proposal re-encoding,freezeh_a;notinjectivityproof|
|C03|verified-only sample can have100%conditionalvs10%overall|q_Rnewhead,q_Yconditional;product predicts only verified TRUE|
|C04|trainingcatalogzero/single/full differsruntime TopK|onesampled prefixlawtrain/runtime;argmax requires new gate|
|C05|learned memory query ignored current input|queryz0 afterinput projection,noextraweights|
|C06|TTS257outputfeeding80inputundefined,framingambiguous|fixedmel feedback,causalSTFT,GL/crop05|
|C07|clearing pending loses unresolved physical dispatch record|durablePREPARED/reconciliation04/05|
|C08|hardware antirollback assumed without evidence|P128probabilisticprofile;exact COUNTER not claimed|
|C09|goal/payload/index/FP32trace/copy-on-write workspace omitted|explicit resource ledger;full PSS still requires backend|
|C10|contractionofinner Fmisreadaslong-horizon agent property|W4,event bound and capacity counterexample;H2/FNC2alternatives|
|C11|goalchildsemanticrefinementundefinedinNL|typed capability envelope versus final predicate;human semantic confirmation|
|C12|all weights objective without memory-write gradient|pairedwrite-queryunroll,detach boundaries and bias declared|

Ни одна строка не оправдывает удаление исходных M14/M16/M18/M25/M27/M32/M36/M43 FAIL. Они ложные универсальные/исторические утверждения. M08 остаётся FAIL идентификации минимального достаточного размера. Завершение исправимой спецификации не делает эти утверждения истинными.
