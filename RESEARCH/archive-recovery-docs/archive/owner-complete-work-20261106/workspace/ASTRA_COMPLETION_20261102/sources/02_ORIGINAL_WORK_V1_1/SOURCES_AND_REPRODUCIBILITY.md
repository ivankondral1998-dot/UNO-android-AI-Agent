# Источники и воспроизводимость

## Первичные научные/методические источники

Просмотрены 01.11.2026. Ни один источник не утверждает полученные здесь новые теоремы о UNO.

| Источник | Что использовано | Что не переносится |
|---|---|---|
| [OpenAI Alignment: LASER, 06.10.2026](https://alignment.openai.com/laser/) | Дешёвая logistic selection, дорогая разметка, повторное обучение; исходная задача — safety-eval conversations | Численный выигрыш LASER не переносится на генерацию программ/UNO |
| [Pugh, Soros, Stanley: Quality Diversity, 2016](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2016.00040/full) | QD ищет разнообразные качественные поведения, архив по нишам | Это не доказательство пользы наших descriptors и surrogate |
| [Google DeepMind: AlphaEvolve, 14.05.2025](https://deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/) | Программные предложения, автоматические evaluators, эволюционный архив | Их ensemble/инфраструктура не входят в UNO и не доказывают эффективность дешёвого offline поиска |
| [Graves: Adaptive Computation Time](https://arxiv.org/abs/1603.08983) | Исследовательский прецедент обучаемого числа шагов | Наши hard budgets/маски/контракция выведены отдельно; ACT-качество не наследуется |
| [Graves et al.: CTC, оригинальный paper](https://www.cs.toronto.edu/~graves/icml_2006.pdf) | Сумма вероятностей допустимых alignments для unsegmented speech | Не гарантия современного русского ASR на A52 |

Дополнительный источник из исходного NCR brief: [QD survey 2026, DOI10.1016/j.swevo.2025.102240](https://www.sciencedirect.com/science/article/pii/S2210650225003979). Проверены библиографические сведения/abstract; полное содержание не использовалось как доказательство. Первоначальный DOI-resolver для статьи2016 не открылся; использована найденная страница издателя.

Остальные доказательства в пакете — собственные конечномерные выкладки (chain rule, convex projection/descent lemma, Banach contraction с приведённой оценкой, индукция, inclusion probabilities, Hoeffding). Их предпосылки и выводы приведены непосредственно, без ссылочного подменивания доказательств.

## Репозиторные источники

Основной [UNO GitHub](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent), main409f04bf95a0a3fec18934982d76be7285864f0a; [PR3](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/pull/3), head8b20af37ffb3d9970d14a4d9f5e86e2b882b1ced, state=open,merged=false на момент чтения.

Вложенный SHA-256 manifest исходников проверен по байтам всех трёх файлов, все совпали. Git SHA-1 blob и SHA-256 локального файла — разные идентификаторы, их не смешивать. В финальном PACKAGE_MANIFEST_SHA256.json перечислены все deliverable-файлы кроме самого manifest.

## Что воспроизводилось сейчас

- Чтение полных первичных документов, live main/PR и указанного reference.py.
- SHA-256/byte-count сверка исходного пакета.
- Арифметический пересчёт параметров, MAC, памяти, sample bounds; результат evidence/arithmetic.json.
- Авторский второй проход и независимое модельное ревью с повторным чтением исправлений.
- Структурная сверка финального комплекта: обязательные11 документов, 44 строки матрицы, замкнутые delimiters формул, ZIP integrity.

## Что сейчас не запускалось

Новая модель или training; NCR simulation/search; Python host-tests из PR3; Android build/install/device test; energy measurement; GitHub Actions/CI; merge/push; JarvisLab modifications. Ручные поколения и oracle-входы — логические конструкции, не журналы выполненного эксперимента.

Арифметика повторяется подстановкой d,V,H,b,χ,J,m в W1/R1 и формулы INT8. Проверка hash/ZIP подтверждает целостность поставки, **не математическую истинность**, тем более не качество будущего продукта.
