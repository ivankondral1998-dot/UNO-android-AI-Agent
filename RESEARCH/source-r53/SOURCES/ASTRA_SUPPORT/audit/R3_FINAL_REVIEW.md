# R3 — итоговое независимое математическое перечитывание

Дата: 2026-11-02. **CONDITIONAL FORMAL/SPECIFICATION ACCEPTANCE** для точного набора файлов ниже: после содержательных исправлений R1/R2 и проверки поправки формулы L3a известных открытых критических противоречий из проведённого аудита не осталось. Это ограниченное заключение о согласованности рассмотренной параметризованной математической спецификации, а не universal proof, machine certification, empirical UNO PASS или разрешение реализации.

## Точный предмет и способ повторной проверки

База: `audit/R3_INPUT/MANIFEST.json`, SHA-256 **437a32fe9e14aa6dee3d5a1e01a7d4f31ede556ebfaeb68a261e8650261adcc5**. Все18 файлов независимо проверены по bytes/SHA. Девять файлов byte-identical полностью прочитанному и проверенному R2: 00,02,04,06,11,12, arithmetic_v2.json, tensor_manifest_d1024.json, recompute.py. Их прежнее чтение не заменено догадкой: идентичность подтверждена hashes.

Изменения 01,03,05,07,08,09,10,FINAL_README,REVISION_LOG прочитаны целиком как diff к уже полностью прочитанным R2-файлам, с контекстом соответствующих нормативных разделов. Это проверка именно новых определений, а не повторный пересказ предыдущего verdict.

В первоначальном R3 документе03 обнаружена потеря LaTeX backslashes и control characters в L3a. Дефект сохранён в immutable R3_INPUT. Отдельный `R3_PATCH_INPUT/ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` заменяет **только03** в области настоящего заключения: SHA-256 **52b1eab23c977d253625b98de20bee6e5802c652973cf96403037118b5fbe4be**,27425bytes. Patch полностью сравнен с R3, изменён только повреждённый блок формулы; правильная формула перечитана, control chars кроме newline отсутствуют.

Итоговые18 entries с review-source и hashes зафиксированы в `audit/R3_AUDITED_MANIFEST.json`. Ни R1/R2, ни author normative files reviewer не редактировал. Последующие status-only изменения09/10/FINAL_README/REVISION_LOG требуют короткого отдельного signoff; пока настоящий verdict относится к этому точному effective snapshot.

## Закрытие всех содержательных замечаний R2

|ID|Проверенное исправление|Статус и условия|
|---|---|---|
|R2-01 coverage mixture|L3a использует `1{Z=j}/π_j·[A−(1−c_j)]`, π_j>0 фиксированы; matching batch dual estimator; task classes отделены от loss indices|CLOSED. Ожидание равно условному violation; при12классах полный отказ одного даёт.9 приc=.9. Сходимость stochastic primal-dual и качество не доказаны|
|R2-02 log/internal rule|Для E3–23 `u=qR qY≥u_min` эквивалентно `log(max(ε,u))≥log(u_min)` при0<ε<u_min≤1;0–2 отдельный terminal branch|CLOSED. Internal verbs не читают frozen outcome rows, не создают tickets/OS effects/P updates. NOOP и verified NOOP_ALREADY_TRUE разделены|
|R2-03 generic UI effects|UI23 требует trusted effect-contract registry, проверенную local/instrumented surface, version/effect containment; unknown/third-party downstream effect DENY|CLOSED CONDITIONALLY на A_ui/A_cap. Registry пока пуст, поведение зарегистрированного кода должно быть проверено будущей реализацией; signer/hash сами не доказывают semantics|
|R2-04 temporal conjunction|CURRENT_ALL требует единый target time и joint snapshot/stability intervals; OBSERVED_ALL явно допускает разные observation times|CLOSED. Нельзя незаметно менять текущую цель на историческую. Нет evidence для переноса clauses на target time → UNKNOWN; native endpoints/стабильность остаются внешними контрактами|

Дополнительное замечание о предпочтении complete trajectory теперь ограничено terminal+cost частью либо равными прочими loss/dual terms; ложного глобального ordering полного J не заявлено. Canonical goal ABI07 и counterexamples08 согласованы с01/05. Матрица09 добавляет N81–N84, сохраняя историю FAIL и эмпирические blockers.

## Сохраняющееся закрытие R1

Непустой per-event selector устраняет искусственный геометрический collapse длинных streams; turn-level admission и hard interruptions остаются явными. Отказ имеет terminal score и правильные per-stratum constraints. Θ_alloc/Θ_free/frozen coordinates разделены; all-trainable claim больше не применяется к резервным строкам. Offline P=0 фиксирована, exact derivative не выдаётся за meta-gradient динамической адаптации. Practical power26268 отделена от positive-effect power9457. Additive costs и sup live RAM/disk не смешиваются. GL physical crop/reanalysis, turn-endβ и Unicode/CTC conventions исправлены и согласованы с формами.

Независимые ранее выполненные arithmetic checks сохраняются благодаря byte identity: d1024 allocated55,451,639,free55,125,689; activeP21,504; mixed INT8 ABI55,873,984bytes; full-K8 ASR14,210,672,000MAC/s безDSP/control; explicit FP16 subtotal153.475633621MiB до named extras. Это подсчёты, а не measurements или sufficient intelligence sizes.

## Что принято условно, а что не принято

Приняты в указанной области: типизированные state/shape contracts; conditional fixed-z contraction и boundedness; локальный P descent и realized-loss regret; causal race/outbox при заданном measurable environment/progress; authority/replay/persistence при A_cap/A_ui/A_tx/A_fs и generation assumptions; finite-pool propensity algebra; объявленные statistical bounds при независимых единицах; c2/c3 repair proof при достаточном current-context reference. Наличие accepted contracts не означает выполненной проверки Android implementation.

Остаются открытыми/не установлены: достаточный или минимальный d; реальные обученные веса; лицензированные данные для всех свободных heads; thresholds/utility approval; RU language/ASR/TTS/UI/planning quality; long-horizon learning/retention/calibration; empirical on-policy behavior с fastP; actual quantization norms/parity/quality; A52 API/storage/isolation/latency/PSS/joules/thermal; correctness effect registry; NCR superiority и доступная стоимость эксперимента. Эти пункты имеют методы проверки и gates, но не получают PASS от документального аудита.

Сохраняются исходные M08 и восемь опровергнутых universal/historical claims M14/M16/M18/M25/M27/M32/M36/M43. Их нельзя удалить или превратить в PASS при финальном оформлении. Conditional acceptance означает, что известные исправимые противоречия закрыты в scoped design; не означает истинность всех желаемых свойств, общую безопасность произвольной ОС или невозможность найти дополнительные ошибки.

Никакое новое направление исследований, выполнение production-code/training/Android/NCR, изменение репозиториев или разрешение на эти действия из настоящего заключения не следует. Следующий шаг остаётся data/device/requirements gate по11/12 и отдельное решение владельца. Для окончательного пакета требуется только проверка объявленных status-only edits и связывание последнего manifest с этим verdict.
