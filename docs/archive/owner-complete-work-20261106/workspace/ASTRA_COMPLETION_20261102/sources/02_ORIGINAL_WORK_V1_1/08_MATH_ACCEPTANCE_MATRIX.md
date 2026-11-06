# 08. Конечная матрица математической приёмки

Зафиксировано 44 обязанности. PASS относится только к написанному свойству в указанной области. FAIL не скрывается за условным словом «готово». NOT_TESTABLE — эмпирическая или внешняя обязанность, не проверенная данной работой. Полный Android/product PASS не вычисляется как процент этих строк.

| ID | Обязанность / проверяемое утверждение | Статус знания | Вердикт | Доказательство / blocker |
|---|---|---|---|---|
| M01 | Развести граф, геном, trusted contracts, Θ/Φ_R/Φ_S/Θ_M | PROVEN | PASS | 01, словарь и формы |
| M02 | Полностью прочитать NCR-EVO оригинал, сохранить provenance | PROVEN | PASS | 00, originals, manifest |
| M03 | Определить наблюдения, цели, missing/unknown | PROVEN | PASS | 01 sum-types, bounded lengths |
| M04 | Определить частично наблюдаемый мир и kernel | CONDITIONAL | PASS | 02 §1,8; заданные measurable K_env,O_obs |
| M05 | Все веса имеют формы, counts и роль | PROVEN | PASS | 03 W1 и tensor table |
| M06 | Параметры d=512/1024/1536/2048 посчитаны | PROVEN | PASS | 03 §6; арифметика evidence |
| M07 | Выбранный d=1024 достаточен для полноценных задач | REQUIRES_DATA | NOT_TESTABLE | Нет training corpus и quality results |
| M08 | Минимально жизнеспособный размер установлен | UNDETERMINED | FAIL | 03 §1: d* зависит от неизвестной feasible-set |
| M09 | Новые веса фактически обучены | REQUIRES_DATA | NOT_TESTABLE | Обучение запрещено текущим scope |
| M10 | Никакие старые веса не обязательны в Θ | PROVEN | PASS | 03 полный реестр |
| M11 | δ тотальна для success/failure/unknown/cancel/stale/STOP/denied/timeout/restart | CONDITIONAL | PASS | 02 table; 05 T1; finite input, total trusted API contracts |
| M12 | Типовая корректность всех матричных произведений | PROVEN | PASS | 01–04 размеры d,b,χ,m,A,H |
| M13 | h,s,β и P bounded | PROVEN | PASS | 05 T2 |
| M14 | Исходный residual с clip всегда сходится | REJECTED | FAIL | 07 §1, двухточечный цикл |
| M15 | Fixed F contractive при norm bounds | CONDITIONAL | PASS | 05 T3 |
| M16 | Sparse inner-loop сходится при любом выборе масок | REJECTED | FAIL | 07 §2 |
| M17 | Fair common schedule сходится при фиксированном z | CONDITIONAL | PASS | 05 T3, sweep-proof |
| M18 | Полный агент стабилен/сходится при любой среде | REJECTED | FAIL | Меняющееся z, goals, kernel; 05 T3 не применима |
| M19 | Стоимость selector, masks, heads, DSP отделена | PROVEN | PASS | 05 R1–R3, P-readout дополнительно |
| M20 | Алгоритмический work-budget соблюдается | CONDITIONAL | PASS | 05 T4; корректные upper costs/reserve |
| M21 | Реальные RAM/PSS, joules, latency A52 подтверждены | REQUIRES_DATA | NOT_TESTABLE | Неизвестны backend/коэффициенты; 05 R4 |
| M22 | Idle не означает нулевую энергию ОС | PROVEN | PASS | Модель 05 §3 различает control/work |
| M23 | Права не зависят от Θ,P | CONDITIONAL | PASS | 05 T5 при A_cap |
| M24 | STOP запрещает ещё не linearized dispatch | CONDITIONAL | PASS | 05 T5 |
| M25 | STOP отменяет уже возникший физический эффект | REJECTED | FAIL | 05 T5; уже отправленный OS call |
| M26 | Stale/replay не меняют P/verified knowledge | CONDITIONAL | PASS | 05 T6 при A_gen,A_tx,A_cap |
| M27 | PR #3 уже обеспечивает safe snapshot rollback | REJECTED | FAIL | 07 §3, конкретная последовательность |
| M28 | Crash-safe persistence определена | CONDITIONAL | PASS | 05 T7; A_fs,A_auth,A_gen,failclosed |
| M29 | Android storage/trust-boundary реализуют A_fs/A_cap | REQUIRES_DATA | NOT_TESTABLE | Контракт будущей реализации, не факт |
| M30 | Unknown/denied/timeout не превращаются в y=0/1 | PROVEN | PASS | 02 event table, 04 L2 guard |
| M31 | Текст success не является receipt | PROVEN | PASS | 02 §5–7 |
| M32 | Verified completion доказывает причинный effect | REJECTED | FAIL | 07 §6; confounding |
| M33 | Offline objectives покрывают все Θ | CONDITIONAL | PASS | 04 §2a,L1 и mapping/chain rule; нужны соответствующие targets |
| M34 | Градиенты smooth-path и discrete-selector разведены | PROVEN | PASS | 04 §2a–3, полный score+pathwise gradient |
| M35 | Online L2 — projected gradient с локальным descent | CONDITIONAL | PASS | 04 §5, η≤1/(1/4+λ), текущая q |
| M36 | Online learning улучшает все будущие задачи без forgetting | REJECTED | FAIL | 07 §8 и finite-state limit |
| M37 | Контрольная монотонность возможна на finite deterministic set | CONDITIONAL | PASS | 05 T8; не generalization |
| M38 | Energy/success определена при нуле успехов и без отказного exploit | PROVEN | PASS | 05 §3 extended metric + hard coverage |
| M39 | NCR-EVO меняет алгоритмы; 3 поколения вручную | PROVEN | PASS | 06 §5, c0–c3 и induction c2 |
| M40 | IPW unbiased finite-pool risk при E1 | CONDITIONAL | PASS | 06 §3; известные p_i>0, fixed φ |
| M41 | NCR-EVO статистически превосходит A/B | REQUIRES_DATA | NOT_TESTABLE | 06 §7, экспериментов нет |
| M42 | Генератор не может изменить trusted contracts | CONDITIONAL | PASS | 06 §8 при capability isolation |
| M43 | Regeneration восстановит любую стёртую функцию | REJECTED | FAIL | 07 §12 |
| M44 | Future implementation contracts и математические oracle заданы | PROVEN | PASS | 09, fixtures, версия/приёмка |

Итог: число конкретных PASS не является вероятностью правильности и не компенсирует FAIL. M08 — открытая задача идентификации размера; остальные FAIL в основном явно опровергают лишние универсальные обещания/наследуемую безопасность PR. Продуктовая достаточность, энергетика и эволюционный выигрыш остаются не установленными.

**Безусловный MATH DESIGN PASS не присвоен.** Допустим статус «полная расчётная спецификация с условными теоремами, готова к рассмотрению». Владелец может утвердить формальную область применимости и экспериментальные пороги; это не превратит UNKNOWN в доказанное свойство.

После независимого повторного чтения: проверенные локальные formal obligations получили CONDITIONAL PASS (INDEPENDENT_REVIEW.md, E2). Это относится к исправленным фазам/kernel, L_aux и полной derivative ожидаемого loss, current-context предпосылке G3. Исходные замечания ревью и FAIL первой версии сохранены.
