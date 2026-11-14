# Независимый критический проход R5.1

## 1. Проверка заявления Grok «full report»
Grok действительно прислал отдельный Stage2 файл 10 445 bytes, с 11 R1/R2 и 8 IR. Но большая часть D/X/B дана компактными строками, worst-case traces перечислены без machine-state logs и independent tensor manifests; подтверждается **наличие сравнительного отчёта**, не полнота всех выкладок или внешней сертификации. Не требуется повторный Stage1.

## 2. Проверка W4
Подробный вывод и explicit discontinuity counterexample см. `02`. Обе локальные оценки и combinatorial counts перепроверяются независимым stdlib audit-only тестом `evidence/verify.py`. Numerical tests не являются доказательством всеобщности; доказательство приведено символически.

## 3. Инварианты памяти
S4 attention aggregate может быть неинъективным независимо от softmax calibration. `CONFLICT/TRUNCATED/UNKNOWN` контракт предотвращает **заявление** о полноте когда raw индекс не даёт полноты; сам по себе не обучает сеть правильно отвечать. Top-k без `TRUNCATED` создаёт ложный exact recall; conflict_key без корректного time/source scope может объединить разные факты. `COMPLETE` распространяется только на eligible indexed records in a frozen snapshot. No exact recall of deleted raw payload.

## 4. Android и STOP
В S3 α-ordering нельзя понимать как физическую отмену: после durable PREPARED, но до подтверждения OS эффекта, crash даёт `MAY_HAVE_EXECUTED`, а не «не было действия». STOP после линейной точки отправки запрещает будущую авторизацию/обучение stale receipt, но не гарантирует физический rollback. Late native sample может быть записан как historical observation, но никогда не превращается в verified credit для stale ticket/P. `CONFIRM` из модели или произнесённый голос не равен доверенному owner consent.

## 5. Learning и causality
`Pr(R=1,Y=1|H)=Pr(R=1|H)Pr(Y=1|R=1,H)` — тождество наблюдаемого совместного события при определённых условных вероятностях, не proof causal effect. Если Y missing when R=0, физическая вероятность успеха не идентифицируется без MAR/контролируемой рандомизации. Projected one-sample descent P2 не доказывает no-forgetting или рост общей task quality. Условные гарантии по покрытию требуют π_j>0 и честной выборки issued tasks.

## 6. NCR-EVO
Finite bounded DSL делает termination проверяемым в заданных bounds, но не доказывает correctness программы, полезное развитие или восстановление утраченных фактов. HT unbiased только для фиксированного pool и точно известных ненулевых inclusion probabilities; adaptive holdout leakage/label censoring остаются возможными. При дешёвом oracle surrogate может быть дороже честного baseline. NCR не выдаёт себе authority и не должен иметь repo credentials.

## 7. Модель полноты
B2 allocated 55,451,639 при d=1024 подтверждён в Astra и R4; LR2 43,917,303 после добавления W_R, H2 59,645,943; это расчётные family candidates, не сравнительный результат trained models. No equivalence B2/LR2, no resource pass on A52. Отказ от modality ради меньшего числа параметров недопустим.

## 8. Новые технические замечания R5.1
- **R51-01 / PROVEN COUNTEREXAMPLE:** hard state-dependent mask может сделать event map discontinuous. Grok правильно предупредил, но не привёл конкретную пару траекторий; здесь она дана (`02`).
- **R51-02 / SPECIFICATION OPEN:** `RetrieveExact` с ограничением k не гарантирует полноту при >k matches; нужен явный TRUNCATED и provenance. Конкретный контракт предложен (`03`).
- **R51-03 / OWNER/TRUST OPEN:** device credential не тождественен идентичности владельца UNO на разделяемом устройстве; enrolment должен связывать identity и owner-controlled account/profile.
- **R51-04 / SCOPE OPEN:** strict offline должна определить границу гарантий; UNO без INTERNET не доказывает offline behavior сторонних SAF providers.
- **R51-05 / REVIEW LIMIT:** полный Stage2 не предоставляет самостоятельный подробный лог/сертификат всех D/X/B. Не ставить независимый общий PASS.

## 9. Граница проверяемости
В этом пакете выполнены read-only inspection, арифметика/численные sanity tests и символические контрпримеры. **Не выполнены**: model training, corpus validation, A52 API probes, Android fault injection, GPU/CPU real energy testing, formal proof assistant certification, external expert signature. Эти пункты остаются B-blockers.