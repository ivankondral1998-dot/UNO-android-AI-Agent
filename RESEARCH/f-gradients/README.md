# Проверка производных существующего F — 13.11.2026

**Вердикт: CONDITIONAL / HOST_TESTED. Можно продолжать создание обучающего механизма именно существующего гладкого F с фиксированным маршрутом.** Это не разрешение запускать обучение и не доказательство обучаемости полезного UNO, сходимости, качества или достаточности ёмкости.

База: `ec9764f03dcdca305b575b41514d0aa153d2aab7`, ветка результата `research/uno-f-gradients-20261113`. Production-файлы не изменены. Использованы существующий handoff и его WP03/Terra выводы; общий аудит не повторялся.

## Что реализовано

`ReverseF.kt` — исследовательский vector reverse-mode VJP для **тех же** S4/S5. Все матрицы, bias/e, признаки, metadata, исходные s/g и k/v имеют именованные листья. Один лист каждого параметра используется на всех шагах/событиях; pullback применяет `+=`. Возвращается градиент скалярной проекции выхода `L=seedᵀhK`. Нет optimizer, updates, selector, нового runtime или Android-интеграции. Tape однократный; backward второй раз запрещён. alpha/rho/T — заданные гиперпараметры, их производные не реализованы.

Локальное цепное правило: для y=Ax имеем bar(A)+=bar(y)xᵀ, bar(x)+=Aᵀbar(y); для y=tanh(x), bar(x)+=(1-y²)bar(y). Для read: bar(v_i)+=p_i bar(r), bar(score_i)=p_i bar(r)ᵀ(v_i-r); bar(k_i)+=bar(score_i)q/(sqrt(m)T), bar(q)+=Σbar(score_i)k_i/(sqrt(m)T). Это аналитическое обоснование правил, не формально верифицированный proof программы. Reverse-order tape разворачивает K синхронных шагов; сохранение h для всех блоков шага и повторное использование узла C z сохраняют полную сумму вкладов L4.

Формы остаются существующими: d128, m128, b64, χ4, J2; d128 — synthetic fixture, не выбор production-архитектуры. Небольшой fixture относительно существующего ABI; не уменьшаем b/m с подменой проверяемого кода. Каждая из матриц содержит детерминированные ненулевые элементы.

## Воспроизведение и фактические результаты

Уже установленный Kotlin 2.2.21 и Java 21.0.13; дополнительных зависимостей нет. Из корня:

```bash
bash research/f-gradients/run.sh
PATH=/workspace/uno-environment/kotlin-2.2.21/kotlinc/bin:$PATH bash android/scripts/host_verify.sh
bash research/f-gradients/negative-controls.sh
```

`run.sh` использует сохранённый путь cloud toolchain, затем имеющийся PATH; на другом хосте нужен доступный `kotlinc`/`java`. Временные jars удаляются только из созданного скриптом временного каталога.

- `evidence/gradients.txt`: 1634 успешные проверки; шесть сценариев K1/K3/K8, обе частичные маски и полная маска, empty/singleton/3-item memory, alpha0/rho1, два последовательных события write→read с общими весами.
- Аналитический forward сравнивается с **неизменённым Kotlin UnoFReference.forward**, максимальная ошибка проверяется против 2e-14.
- Для каждого именованного тензора/входа сравниваются максимум аналитического градиента **и независимо заданные координаты** 0/последняя/119 (без повторов), центральные разности ε=1e-5 и 3e-6; абсолютный допуск 2e-11 + 2e-5·|finite difference|. Плюс две направленные пробы всех координат всех тензоров, разные направления у разных имён. Это конечное покрытие, не покоординатная проверка каждого элемента полного Jacobian.
- Лог содержит значения возмущаемых координат, expected=central difference, actual=analytic, epsilon и tolerance. Все исходные значения без случайного RNG полностью задаются `fixture()`/`numbers()` в `GradientTest.kt` (salts/scales/формы), seed там же. Воспроизведение не требует неизвестных weights/data.
- Проверяются нули градиента неактивных ветвей; singleton q/Wq действительно имеет нулевой градиент. Многоэлементный read даёт ненулевые k/q/v производные. Invalid shape, NaN, Inf, пустой маршрут, K9, T0, нарушение row-L1 и overflow конечных score отвергнуты. В штатном host-наборе также есть large-finite-score softmax и empty-double-tanh проверки.
- `evidence/host.txt`: компиляция всех core main/test Kotlin и действительный запуск `AllHostTestsKt`, `UNO_WP01_HOST_PASS=446`, включая 12 `UnoFReferenceTest`. Это агрегат существующего runner, не 446 Android-сценариев.
- `negative-controls.sh` воспроизводимо компилирует временные повреждённые копии: удалённый key pullback и замена `+=` на `=` у общего матричного параметра. Ожидается именно assertion численного сравнения; compilation/startup errors не засчитываются. Лог: `evidence/negative-controls.txt`.

## Контрпримеры, ошибки и исправления

1. Terra shared-use example сохранён как regression: h1=w·h0+x,h2=w·h1+x, w=.4,h0=.7,x=.2. Полная производная .76; central .759999999960792; только последний usage .48. Это контрпример неверному backward, **не обнаруженная ошибка существующего forward**.
2. Singleton softmax даёт p=1 и нулевой query gradient. Кандидат исправления уже задан Terra: допустимые независимые от gold distractors и честная метрика retrieval misses; численная проверка не заменяет candidate-generation contract.
3. Identity-write fixture: полная производная по writeFeatures `[-.0007108168112202611,-.0009864656332236035]`, при detach сохранённого k/v `[-.0006956115875236528,-.0009712007335783606]`; одинаковый forward, разница градиента до 1.52649e-5. Нужен differentiable write/replay при той же Θ. Fixture специально **не объявляется реализацией Wk/Wv**: они отсутствуют в UnoRefWeights. Производные по готовым k/v и композиция identity-write проверены; обучаемые генераторы памяти остаются блокером.
4. Независимое ревью обнаружило ошибку первоначального механизма проверки: направления одинаковой длины имён совпадали (общий сдвиг всех ключей softmax-инвариантен), координаты выбирались только по аналитическому максимуму, floor2e-9 маскировал малые key gradients. Исправлено независимыми координатами, hash имени и floor2e-11; negative-control должен теперь обнаруживать удалённый key pullback. Первоначальный успешный прогон не используется как итоговое доказательство покрытия ключей.
5. Противоречий S4/S5 forward с прочитанными формулами на исследованных путях не найдено; оригиналы Astra/R5.3 не изменены. Отдельный архитектурный кандидат не создавался, поскольку математического противоречия не обнаружено.

## Что остаётся перед обучением

- S6 discrete adaptive selector/halt, меняющийся support/route: pathwise fixed-mask gradient не равен score-gradient L5. Для него нужны отдельные estimator/variance/boundary tests; никаких выводов из этих 1634 проверок о его корректности.
- Wk/Wv и реальный causal write/replay/snapshot/eligible-candidate path, version/TTL/revoke, согласование semantic port с query. Здесь identity boundary и входные k/v, а не production memory trainer.
- Общий trainer со всеми targets/heads и shared Θ, loss masking, optimizer/projection, checkpoint/ABI, FP32/AMP/export parity отсутствуют либо не проверены этим этапом. Double oracle не доказывает FP32/INT8 устойчивость.
- Реальные данные/права, разделённые holdouts, невырожденные memory negatives, долгие BPTT/retention последовательности, gradient magnitude/conditioning на рабочем распределении. Ненулевой локальный gradient не гарантирует полезного обучения; универсальный TBPTT bound из fixed-z contraction не следует.
- C1–C4 из handoff не исправлялись. Android build/device/энергия/качество и весь unified-cycle не проверялись. Ни весов, ни training batches не обучали; finite-difference perturbations — только диагностические копии параметров.

## Источники (адресное продолжение)

Действующий main AGENTS `1df9ee7cc592f606939c8f004e1b11edd916b56c`; исходный handoff/control HEAD выше. R5.3 ASTRA_01 S4/S5, ASTRA_02 формы/row caps, ASTRA_03 L4/L5/§4, ASTRA_04 memory и NORMATIVE/03. UDC v0.3 по историческому `116820103c8b3e3c315fe0c92f658900819cf8d6`; Terra `304b416430810dc17350bcab826046f5ade2da1d`, TRAINING_READINESS и CORRECTED_ARCHITECTURE/INDEPENDENT_VERDICT. Полученные refs на дату проверки: r53 `7e94b717d73312f1bf3a926ea5f89586c9d23d7b`, udc `3b06b024199d9bfcf1362a6b48156dfa0c74c9dc`, terra `0af492ee7a8d15b371bf0de1c21d73ca1fd8b050`. Это прочитанные источники, не новое одобрение их архитектурных кандидатов.
