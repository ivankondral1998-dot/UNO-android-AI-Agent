# UNO-TRAIN-001 — контролируемый offline trainer существующего F

**Результат: IMPLEMENTED / HOST_TESTED / CONDITIONAL.** Создан рабочий механизм ограниченных синтетических обновлений существующего F. Это не обученный UNO, не доказательство сходимости или достаточности архитектуры, не разрешение production-обучения.

База `618b0227eb9c9d717464d923fa0312a42b0c1843`, отдельная ветка `research/uno-train-001-20261113`. main/AGENTS получен заново: `1df9ee7cc592f606939c8f004e1b11edd916b56c`. Результаты S4/S5 и Wk/Wv использованы без повторного общего аудита и без запуска их полных прежних численных батарей.

## Что работает

- `JointGraph` использует прежние `MemoryReplay`, `LearnedMemory`, `ReverseF`. В research-only forward добавлен observer фактического S4 query/read и сохранён read-trace; исходные формулы/порядок вычислений не менялись. Production-файлы Android не изменены.
- Одна потеря `J = λs·MSE(h_final,y_state) + λr·CE(retrieval,target_record) + λv·MSE(v_target,y_value)`. Defaults λ=(1,.3,.2). MSE усредняется только по заранее заданным валидным координатам; пустая разметка отвергается. CE — stable logsumexp по минимум двум уже допустимым кандидатам. Gold используется только после построения графа для loss. Отсутствующий target отвергается как RETRIEVAL_MISS, не добавляется в каталог. В будущей оценке такие отказы должны учитываться в denominator, а не отбрасываться как успешные.
- Градиенты всех трёх ветвей проходят через одну Θ, исходные F состояния и реальные Wk/Wv. Градиенты initial/input leaves не передаются optimizer. Это не замена UNO классификатором: CE здесь только вспомогательная loss поиска памяти, состояние/значения проверяются непрерывными задачами.
- `TrainModel` хранит все существующие параметры F/Wk/Wv с именами, формами и caps. Общие тензоры имеют по одному листу, одно состояние Adam. `OfflineTrainer.accumulate` суммирует полные episode-gradients, затем `update` усредняет по числу эпизодов, обнуляет frozen координаты, применяет global-L2 clip1, Adam(.9,.999,epsilon1e-8,без weight decay), bias correction и Euclidean row-L1 projection / bias box clamp. Caps соответствуют ASTRA_02: A1/B.9/C2, Us/Ug1, Wq/Wr/Wk/Wv2, projection/meta8, e/bias1, branch biases8. Frozen weights и оба момента сохраняются0.
- LR по Astra: warmup1000 до2e-4, cosine до2e-5 на заданных totalSteps. Константный LR применяется только в явно названных scalar unit-tests. Конфиг default ограничивает число обновлений двумя; нет epoch-loop или неявного длительного запуска.
- Проверки формы/конечности/накопления/моментов выполняются до изменения публичного состояния; невалидное обновление не частично записывает веса. Градиент привязан к fingerprint весов и эксперименту; устаревшие либо полученные при другой loss/config градиенты отвергаются.
- `TrainingDataset` делает глубокий неизменяемый snapshot событий/целей/eligibility, вычисляет SHA256 всех входов и labels; evaluation проверяет реальный manifest. Копии схемы, frozen-set и route защищены от изменений внешних коллекций после накопления.
- Checkpoint содержит weights, m/v, step, sample cursor, полную config (loss weights, optimizer/LR/route/K/budget/seed/data hash), schema digest. Сохранение — только optimizer boundary, без live tape/частичных gradient buffers; после восстановления состояние F/память пересчитываются из raw episode под новой Θ. Версионированный binary Double формат с SHA256, проверкой length/shape/norm/config и лимитом64MiB, atomic same-directory replacement. Загрузка требует доверенные schema+experiment manifest, не принимает произвольную архитектуру из файла. Этот research формат не weight ABI Android и не security signature. Power-loss durability/rollback protection/fsync родительского каталога отдельно не проверены.

## Воспроизведение

Существующие Kotlin2.2.21, Java21.0.13. Новых зависимостей нет. Из корня:

```bash
bash research/train001/run.sh
bash research/train001/negative.sh
bash research/train001/cli-smoke.sh
PATH=/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH bash android/scripts/host_verify.sh
sha256sum -c research/train001/evidence/SHA256SUMS
```

Для просмотра задачи без обновления: `bash research/train001/diagnostic.sh inspect`.
CLI `step FILE` выполняет ровно один synthetic diagnostic update и сохраняет checkpoint (существующий FILE отвергается); `resume FILE` выполняет следующий, максимум два суммарно. Никакой цикл обучения не запускается. `cli-smoke.sh` проверяет эти команды в отдельных JVM и отказ третьего update. Это тесты механизма, не запуск содержательного исследования качества.

## Фактические проверки

Все итоговые команды завершились exit0:

| Команда / лог | Результат и предел |
|---|---|
| `run.sh`, `evidence/train.txt` | **446** проверок нового механизма. Общая loss и её градиенты vs независимый plain-Double objective + неизменённый Kotlin UnoFReference. Не Python-подмена. Проверяются аддитивность loss/VJP, выбранные координаты Wk/Wv и F, scalar Adam1/2, clipping, Euclidean projection, freeze, batch mean, NaN/overflow/ownership, checkpoint и restored NEXT step. |
| `negative.sh`, `evidence/negative.txt` | **4** намеренных ошибки действительно обнаружены assertion: пропуск value loss; перезапись batch sums; пропуск Adam bias correction; потеря сохранённого m. Ошибка компиляции/старта не засчитывается. Временные mutants не изменяют репозиторий. |
| `cli-smoke.sh`, `evidence/cli.txt` | inspect без обновлений; два single-step запуска в разных JVM с checkpoint resume; третий update отклонён, SHA256 checkpoint неизменён. |
| `host_verify.sh`, `evidence/host.txt` | **446** по отдельному счётчику существующего core host runner; Kotlin compile+run. Это другой набор, не тот же результат нового trainer suite. Android APK/device не проверялись. |

`evidence/red-loss.txt`: тест MSE сначала упал на исполняемой нулевой заглушке (expected.16, actual0), затем реализован правильный узел. `initial-loss.txt` — ранний узкий прогон двух loss-проверок, не итоговая батарея.

Все sparse synthetic входы/цели заданы в `Synthetic.kt`, не текущими предсказаниями модели: два варианта delayed-state/memory, четыре последовательных события, независимые цели состояния и значения выбранной исторической записи. Третий source-event сам читает более раннюю память; последний read исключает отозванную запись2. d128/m128/b64/J2/χ4, K3, route[true,false], seed11 — только diagnostic geometry существующего oracle, не production dimension decision. Dataset SHA256: `5bce259474a1863498fa5461cfb60cbfbe912bbc4493e5fa816630939485c869`.

Численные пробы: ε=1e-4 и3e-5, tol=2e-10+2e-5·|central difference|. Лог содержит имена/значения координат, expected=numeric, actual=analytic, epsilon/tolerance. Проверены выбранные координаты, не весь полный Jacobian. Информативные max|grad|: Wk≈3.67823e-4, Wv≈.0722994, projection≈.163532, Us≈.045843; сигнал проходит также через Wq/Wr/A/C/B. Metadata/goal в этих fixtures нулевые; полезное обучение Ug/meta здесь не доказано.

Один диагностический шаг: J `.5701859408485126 → .5701851167587603`. Это проверка правильного движения конкретного маленького примера, не learning curve, не validation quality и не теорема монотонного уменьшения для projected Adam. Проверка checkpoint: weights/m/v и следующий update после restore совпадают побитно с непрерывным запуском. Ephemeral checkpoint≈10.37MB, веса/checkpoints в Git не публиковались; сохранены код, manifests и логи.

## Найденные ошибки и исправления

1. Новая схема/конфиг первоначально удерживали caller-owned mutable collections. Между accumulate и update можно было сменить route/cap/frozen и неверно пометить опыт. Теперь защищённые глубокие копии; regression изменяет внешние коллекции после accumulate.
2. Первоначальная scaled L1 projection принимала `.9992007221626409` вместо1 для `[1e15,0]`, cap1. Кандидат исправления реализован: порог решается в координатах `gap=maxAbs-|x_i|` с устойчивым `delta+=(gap-delta)/activeCount`; выход `sign(x) max(delta-gap,0)`. Проверены `[2,1]→[1,0]`, `[1e15,0]→[1,0]`, `[MAX,MAX]→[.5,.5]`. Исходные Astra/R5.3 не изменены.
3. Хеш данных первоначально был только caller label при изменяемых targets. Заменён на bound immutable snapshot; несоответствие config manifest отвергается. Копии данных, возвращённые пользователю API, не изменяют источник обучения.

Независимое ревью проверило математику общего графа, обновления/restore, исправленные ownership/projection/dataset пути. Контрпример относится к новой реализации projection, не к ядру F. Нового ядра или общего повторного аудита не создавалось.

## Перед первым содержательным контролируемым обучением

1. **Точность:** всё здесь Double. Нужны FP32 master/gradient/optimizer parity, AMP nonfinite/reject/loss-scale протокол; FP16-storage против smooth offline objective и явно biased STE/QAT. Контрпример округления из MEMORY_CONTRACT остаётся открытым; точность не решена именем optimizer.
2. **Selector/halt:** fixed route/K/P0. S6/L5 estimator, support/feasibility boundaries и score terms общего Θ не реализованы и не доказаны этой батареей.
3. **Полный граф:** реализован общий механизм и три diagnostic losses, не все supervised heads/язык/ASR/TTS/actions/coverage/value/retention цели R5.3. Необходимы их masks, denominators, causal targets, независимые тесты, полные gradient paths. Нельзя назвать synthetic state regression полноценным интеллектом.
4. **Данные:** реальные лицензированные manifests, splits/locked holdouts, meaningful paired memory negatives и baseline/quality gates не подготовлены. Toy tasks проверяют механику, не способность понимать язык или решать задачи владельца.
5. **Experiment gate:** перед большим запуском — отдельное разрешение владельца, явные бюджет/число steps/stop criteria, выбранный loss manifest и precision contract. Ни длительного, ни production, ни real-data обучения здесь нет.
6. **Replay/runtime:** bounded≤32-event in-memory prefixes; raw-source snapshots, реальные f_e schema/normalization, транзакции/ревокация/TTL persistence, long-horizon retention/TBPTT bias и boot/model consistency остаются. Checkpoint64MiB и tensor≤2M elements — исследовательские ресурсные границы; полный большой production inventory может их превысить. Они проверяются отказом, а не скрытым обрезанием.
7. **Приёмка продукта:** C1–C4, Android integration/device/resource/offline checks не затронуты. main/production/workflows/оригиналы неизменны. HOST_TESTED не ANDROID_BUILT/DEVICE_VERIFIED/RELEASE_READY.

Источники: текущий main/AGENTS; ASTRA_02 формы/Ω и ASTRA_03 §2–4 shared gradients, Adam/projection, TBPTT/precision; Terra TRAINING_READINESS §1–2; предыдущие `research/f-gradients/README.md`, `MEMORY_CONTRACT.md`, `MEMORY_RESULT.md`. Их исторические контрольные суммы относятся к прежним commit; новый manifest включает изменённые research tape/read-trace файлы. Исходный handoff/аудит не переписывался.
