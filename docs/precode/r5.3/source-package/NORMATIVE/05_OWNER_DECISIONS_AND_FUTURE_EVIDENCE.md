# UNO R5.3 — решения владельца и проверки будущей реализации

**Не ставить пользователю бинарный вопрос «утвердить всю математику?» до того, как понятны отдельные компромиссы.** Авторские рекомендации ниже не равны решению пользователя. Ни один выбор не вносит новые обученные веса автоматически.

## A. Конечные продуктовые решения G4 (владелец; ещё не подписаны)

| ID | Выбор | Обоснованная предложенная опция | Риск или цена | Статус |
|---|---|---|---|---|
| O01 | WAKE+SENSOR обязательны или optional/frozen | Обязательные — сохранить полный замысел UNO | Дорогой audio baseline, датасет, background Android limits; нужен отдельный A52 gate | `OWNER_DECISION` |
| O02 | Политика вычислительных масок | Cyclic-prefix как исследовательский baseline с arbitrary comparator | 241 vs 65535, неизвестное quality gap, adaptive jumps | `OWNER_DECISION` |
| O03 | Семейство/ширина | B2 и сравнение размеров 512/1024/1536; 2048 как контроль; LR2/H2 — только по failure trigger | Нет доказательств достаточной ёмкости; варианты не эквивалентны | `OWNER_DECISION` об эксперименте, финальный размер по данным |
| O04 | Точная память | `RetrieveSemantic(SUMMARY_ONLY)` + `RetrieveExact` по R52/02 | конечное хранилище, TTL, согласие, conflict, ABA | `OWNER_DECISION` о принятии ABI; реализация тестируется позже |
| O05 | Строгий offline | App-private/проверенно локальные источники по умолчанию; непроверенный SAF — reject | сторонний provider может загружать по сети | `OWNER_DECISION` |
| O06 | Quality/coverage/security пороги | Заранее утверждённые per-class floors (quality q_j, coverage c_j, risk r_j) + независимые test oracles | числа нельзя вывести из формул, нельзя подогнать по тестам | `OWNER_DECISION` |
| O07 | Область авторизации Android | Внешний доверенный controller/API при отсутствии legacy OwnerGate как обязательной реализации | до реализации необходимо определить enrollment/auth/consent-expiry/threat model | `OWNER_DECISION/SECURITY_SPEC` |
| O08 | Политика эквивалентности/ресурсов | Выбирать семейство по quality-feasible и measured joules/task, не по параметрам | результаты только после обучения и A52 | `OWNER_DECISION` о правилах, не о будущих измерениях |

## B. Что реально можно поставить только после разрешённого кода (G5)

- Данные и правовое происхождение: лицензионная и consent-таблица; хранение датасетов и train/dev/cal/test split, разметка RU/audio/screen/action/WAKE/SENSOR; набор locked tests, независимые оракулы.
- Бинарный экспорт новых весов: официальные B2/LR2/H2 manifest, frozen row parity, decoded quant norms, tokenizer digest; результат фактического обучения, а не theoretical parameter count.
- На Samsung A52: p95/p99 latency, PSS peak, energy joules/task и idle, background mic, thermal throttling, offline network trace, long-run thermal, sensor freshness, native action race/STOP tests.
- Memory/capability fault injection: ABA, revoke midway, cross-boot TTL, crashed PREPARED/MAY_HAVE_EXECUTED, stale receipt, no blind retry, allowed provider policy, independent evidence.
- Качество и полезность: независимый locked holdout, subgroup bounds, RU ASR/TTS, full multi-task accuracy, wake false/hour and false rejects, target completion, forgetting; baseline compared on equal data and devices.
- NCR-EVO: bounded sandbox, equal-cost arm comparison + fresh independent holdout; no release claim self-regeneration by mere model selection.

## C. Утверждение предкодовой архитектуры ≠ релиз

`G4` подписывает **математические и инженерные кандидаты, условия их применимости, открытые эмпирические gates и разрешение/запрет начала разработки**. Он не требует заранее иметь полученные trained weights или A52 measured PASS. Но до G4 нужны выбранная область продукта, версия контрактов, security-scope и хотя бы процедура определения порогов качества до locked evaluation; не должно быть противоречивого исполняемого ABI.

`G5` — реальные веса/код/испытания; `G6` — подтверждённый коммерческий продукт, юридические и privacy/OS-store gates. **Владельцем ни G4, ни code authorization не выданы.**

## D. Формулировка будущего решения (НЕ ПОДПИСАНА)

«Рассмотрел составную UNO R5.3 от 2026-11-02, её явные предпосылки и ограничения. Принимаю варианты O01–O08 в отдельно подписанной таблице, признаю будущие G5/G6 испытания обязательными, утверждаю/не утверждаю математическую предкодовую основу и отдельно разрешаю/не разрешаю начало производственной реализации». Пока фактическое решение не предоставлено, эта строка — только шаблон.
