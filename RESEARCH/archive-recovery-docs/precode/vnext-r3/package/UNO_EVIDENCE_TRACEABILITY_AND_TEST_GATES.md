> Редакция R2: применять с ERRATA_R2.md; исторические числа N0/LR не перепроверены по сырым трассам.

# Происхождение и приёмка vNEXT

R53_ORIGINAL_INDIVIDUAL_GATES.md содержит каждую строку D01–D10, X01–X12, B01–B14 и M01–M44. Сохраняются исходные статусы и условия. Подробное отображение R4.1 приведено в приложенной базе §§16, 16.1, 26. Изменения vNEXT затрагивают D02–D04, D07–D08, X01–X02/X05–X07/X09–X10 и соответствующие B/M по предмету контракта. До повторного расчёта и исполнения новые A/B не наследуют PASS исходного эксперимента. Индивидуальные результаты не повышены.

| Утверждение | Статус и основание | Ворота |
|---|---|---|
| При γ=0 либо пустом B графе восстановление базовой формулы | PROVEN_LOCAL, подстановка в §A/B при том же snapshot и маске | Проверить parity байтов и трассы на реализации |
| Локальная Lipschitz оценка B | CONDITIONAL, frozen coefficients, common mask, norm cap | Проверить decoded tensors, глобальный feedback открыт |
| Summary теряет идентичность | PROVEN_LOCAL, противоположные вклады | Exact retrieval, consent, conflict, generation и bounded completeness |
| P и record update с UNKNOWN | SPECIFIED_UNTESTED, расширение не наследует P1 proof | Квитанции, дедупликация, crash и отрицательные тесты |
| Learned semantics, retention и ресурсный выигрыш | REQUIRES_DATA | Лицензия, независимые splits, сравнение при равном бюджете |
| N0-07 полезность | FAIL в границах owner-reported контролей | A control F14/80, persistence65/80, Markov65/80. B control F24/80, persistence52/80, Markov35/80. After-restart F77/80 INVALID_LOW_MOTION_DIVERSITY |
| Фонарик и native authority | SPECIFIED_UNTESTED | Раздельно intent, action authorization, OS outcome, independent physical outcome, causal attribution |
| Переходы и профиль | OWNER_DECISION | O01–O08 и отдельный допуск |

Для будущего экзамена заранее закрепить класс, N, expected outcome, permitted observations, latency/energy budget и quality/coverage/risk thresholds. Счёт отдельно на каждую страту: successes/N, eligible completed/N, unauthorized effects/N, UNKNOWN/N, retries/N, old-before и old-after на одинаковых задачах. Разделить positive/negative consent, ambiguous, stale readback, lifecycle, conflict, sensor missing, idle и warm/thermal runs. Аппаратные результаты p95/p99, PSS, joules/task, idle и thermal здесь REQUIRES_DATA. Нулевое число ошибок на конечном N требует верхней доверительной границы, а не заявления нулевого риска.

## Контрольная точка и пределы доступа

06.11.2026 через GitHub прочитан ref исследовательской ветки efdb1767ef75cbdb04ff813323c107c3bd22c4b6 и main 409f04bf95a0a3fec18934982d76be7285864f0a. Совпадает с контрольной точкой нового recovery audit. Предыдущий handoff 06.11 был прочитан начиная с 05_WORK_MANDATE, в предыдущем ходе проверены CRC и 31 SHA. Новый recovery ZIP содержит валидаторы и отчёт об охвате. Синтетический FIXTURE_PASS в нём не подтверждает GitHub snapshot из 247 blobs.

Каноническая основа доступна локально как архив commit fcddf0f в UNO_ENGINEERING_RECHECK/SOURCES и как ORIGINAL_SOURCE_PACKAGE в UNO_TO_WORK_R3_FULL_SOURCE_REPAIR. Адресно использованы ASTRA_03 L3a/L4/L5, NORMATIVE/04 и /05, R4.1 и ledger 06.11. Полное сравнение каждого байта с текущей исследовательской веткой efdb1767 и полное перечитывание ASTRA_01–12 и R52 в этом ходе не выполнены. Android и host результаты LR/N0 взяты из ledger с его уровнями доверия. Полный оригинал UNO_R41_A52_V01_V20_ALL_TESTS_AND_RESULTS_REV2_2026-11-04.txt и сырой 400-row N0-07 trace здесь не получены. Архив сдачи содержит проект и исходную матрицу, его охват не включает зеркальную копию репозитория. Это ограничивает независимую приёмку исходников и полное закрытие мандата.

Recovery ZIP проверен по CRC и 8 записям VERIFIED_FILE_MANIFEST.json.
