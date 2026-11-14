# Воспроизведение расчётов

Из распакованного архива: `python EVIDENCE/recheck.py`.

Нужны Python 3 и NumPy. Никакого обращения к GitHub/интернету скрипт не делает; исходный repair ZIP и commit snapshot находятся в SOURCES. Скрипт вызывает прежний арифметический verifier, затем отдельное перечисление тензоров/смещений и математические fixtures. Он обновляет JSON/CSV/stdout только в локальном EVIDENCE; ни весов, ни production ядра не создаёт.

- original_check_stdout.txt: 64/63 записи манифестов, четыре B2 и compact counts.
- tensors_*.json: имя, форма, dtype category, allocated/frozen, row stride и offsets; без самих весов/scales.
- resources.csv/json: полные расчётные профили, raw/aligned INT8, FP16, MAC, known live и activation ledgers.
- checks.json/recheck_stdout.txt: 53 проверки; число не является метрикой покрытия архитектуры.
- source_inventory.json: 64 файла, байты и SHA; byte verification не full semantic reading.

Контрпримеры имеют результат PASS теста, потому что успешно опровергают неверный claim: hard selector Lipschitz, full-event contraction, lossless semantic aggregate, прежняя float PRNG граница, прежняя compact evidence shape. Статус самих claims — FAIL. Схема STOP — четыре причинных линейных порядка с атомарным commit, не exhaustive Android model checker. 500 P шагов не доказательство удержания навыков. Numerical gradient проверяет одну гладкую ветвь по 44 координатам, не весь multimodal BPTT.

Источники программ и результаты сохранены. Для воспроизведения точной среды версии Python/NumPy указаны в environment.json. Новая independent external review в этой редакции не проводилась; исторические отдельные reviewer отчёты остаются в исходных ZIP.
