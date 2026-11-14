# UNO — исправленный контракт единого F, кандидат V1 от 12.11.2026

**Статус документа: SPECIFIED_UNTESTED.** Это адресная поправка к R5.3 S4–S7 и UNO-UDC-001 v0.3, а не замена нормативных оригиналов, утверждённый ABI или разрешение на новый runtime. Гипотеза: один параметризованный F способен выучить нужный набор функций; она остаётся REQUIRES_DATA. Чат, память, органы восприятия и UI не становятся независимыми интеллектуальными агентами. Доверенная Android-граница — средство полномочий, а не второй разум. Действующие UNO 1.0 Θ на устройстве неизменяемы; прежняя быстрая пластичность P1 — исследовательский архив и отключена, пока владелец отдельно не изменит решение.

## 1. Источники, формы и единый переход

База: [ASTRA_01 S4–S7](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/fb2b3f4c8ad299434fe555b6ccce728c58299e97/docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md#L57), [ASTRA_02](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/fb2b3f4c8ad299434fe555b6ccce728c58299e97/docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md#L15), [UDC v0.3](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/116820103c8b3e3c315fe0c92f658900819cf8d6/docs/design/UNO_UNIFIED_CYCLE_AND_DATA_CONTRACT_V0_3_CANDIDATE_20261112.md). Следующий математический контракт сохраняет исходную архитектуру; конкретные размеры/предельные числа являются параметрами кандидата и не считаются решением владельца.

Обозначения: `d` — размер общего состояния и цели; `m` — ширина памяти; `b | d`, `n=d/b` — блоки; `χ` — расширение; `J` — число ветвей на блок; `V` — размер словаря. Общее Θ содержит, при фиксированной версии manifest:

| Тензор | Форма | Использование |
|---|---|---|
| `E_text` | V×d | embedding и связанный текстовый выход, один общий тензор |
| `E_τ` | d×p_τ | audio, image, sensor и другие типы входов; конечный каталог p и preprocessing фиксируются версией |
| `U_s,U_g` | каждый d×d | рабочее состояние и цель |
| `W_meta,e_τ,b_z` | d×32, d, d | структура/позиция/режим, не полномочия |
| `W_q,W_k,W_v,W_r` | m×d, m×d, m×d, d×m | запрос, запись и извлечение памяти |
| `A_lj,C_lj,B_lj,a_lj,b_lj` | χb×d, χb×d, b×χb, χb, b | один и тот же recurrent F при всех допустимых режимах |
| головки `W_a,W_p,W_R,W_ctc,W_b,W_speech,W_M,...` | как в ASTRA_02 / versioned shape manifest | typed action, прогноз наблюдаемости/исхода, речь, маргинальные состояния, вычислительная политика; это головы общего F, не отдельные агенты |

Принимаются только конечные значения, корректные длины, dtype и независимые masks. Контракт S4–S5 при одном событии:

```
z0 = tanh(Eτ f + Us s + Ug g + Wmeta fmeta + eτ + bz)
q  = tanh(Wq z0)
I  = eligible(snapshot, scope, consent_epoch, TTL, model_version, causal_time, budget)
ωi = softmax_i(qᵀki / (sqrt(m) TM)),   r = Σi∈I ωi vi
если I пусто: r=0
z = tanh(z0 + Wr r),    h0 = ρ s + (1−ρ) z
u_lj = tanh(A_lj hk + C_lj z + a_lj)
Fj = (1/J) Σ_l tanh(B_lj u_lj + b_lj)
h^(k+1)_j = (1−α Mj) h^k_j + α Mj Fj
s_candidate = hK
```

`I=∅ ⇒ z=tanh(z0)`, а не `z=z0`. Точная память возвращает помеченные `COMPLETE / TRUNCATED / CONFLICT / UNKNOWN / DENIED` оригинальные записи по R52; семантический r — только `SUMMARY_ONLY`. `Wk/Wv` создают key/value из совместимого предыдущего F состояния, но их фактическая связь с конкретной записью, временем, owner scope и модельной версией должна быть сохранена доверенным store. При несовместимости source/model/epoch значение не используется; отсутствие не замещается fabricated zero-fact. Пересчёт старых embeddings без доступного raw source не считается восстановлением.

Выбор mask/halt: либо исторический S6 cyclic-prefix с его **заданным законом** ε-mixture и hazard, либо другой явно версионированный закон после сравнения; фиксация конкретной стратегии требует решения. `M` реально пропускает A/C/B вычисления неактивных блоков. Допустимое множество mask определяется доверенным ресурсным бюджетом до выборки; seed/counter и закон пишутся в trace. Пустое feasible set -> `BUDGET_ABORT`, а не фиктивный успешный шаг. Если runtime использует argmax, а training sampling, это иная политика и её качество/ресурсы проверяются отдельно. При `h,z` и общем фиксированном M W4 даёт локальный bound, но не глобальную устойчивость.

## 2. Согласованное единое состояние и публикация

Один сериализованный владелец логической сессии хранит

```
S = (model_digest, session_nonce, boot_id, event_seq,
     s, g, goal_id, goal_version, memory_snapshot, consent_epoch,
     stop_generation, budget_epoch, rng_counter, work_cookie,
     bounded_pending_and_reconciliation_refs)
```

Это логическая модель, **не зафиксированный бинарный ABI**. Raw goal и полные аргументы хранятся в разрешённом exact store по bounded/versioned ссылке, поскольку конечный g не гарантирует обратимость произвольного исходного текста. Рабочий snapshot включает проверенные inputs и одинаковые версии. Независимый наблюдатель публикует typed `OBSERVED`, `USER_DECLARED`, `HYPOTHESIS` и `VERIFIED_COMPLETION` различными типами; последняя метка принадлежит только доверенной границе.

**Алгоритм публикации результата (поправка C4).** При начале работы взять immutable версию `V=(session_nonce,event_seq,model_digest,goal_version,consent_epoch,stop_generation,memory_scope_epoch,budget_epoch,work_cookie)`. F пишет только в ограниченный приватный staging. Перед видимым обновлением `s`, `g`, созданием proposal и публикацией ответа доверенный владелец выполняет **атомарно** `if currentV==V and !STOP and authority_live: commit(candidate); else discard`. Реализация может использовать один controller event loop либо CAS в транзакционном store; выбор конкретного механизма предстоит проверить. Проверка непосредственно перед commit — часть одного события линейризации; раздельные `check(); publish()` недостаточны. Если в промежутке уже отправлен внешний запрос, discard вычисления не отменяет эффект: ticket остаётся `MAY_HAVE_EXECUTED`, требуется безопасный readback/reconciliation.

**Переключение цели.** Только при смене активной цели snapshot одного рабочего s; временно `s=0,g=0,I=∅`, кодировать полный raw canonical intent тем же F в режиме GOAL с ограниченным ресурсом. По завершении g←h_final и возврат рабочего s в одном commit по неизменным версиям. Отмена, STOP, revoke, новая цель или нехватка бюджета -> никаких частичных g/s/permissions. Компромисс: одно конечное g может сжать смысл, но не гарантирует точность произвольного длинного запроса; original intent остаётся bounded exact reference. Автоматически заменять точные поля значениями из смыслового резюме нельзя.

**Предложение.** Текст/числовые аргументы внешнего действия сгенерировать тем же F, нормализовать через closed typed schema, затем полностью и в canonical порядке повторно закодировать тем же F, `s_start=h_dec`, `g=frozen_goal`, роль PROPOSAL. Только после полного encode зафиксировать `h_a` и оценить S7. Вербы внутреннего ответа/отказа/уточнения, как определено schema, не получают action ticket/S7/native effect. Допустимый текст (ANSWER) и реальный системный endpoint имеют разные критерии качества и семантику readback.

Планировщик может предложить дерево целей, но не расширяет parent capability envelope; проверяются тип, допустимые диапазоны эффекта, конечное дерево, общий budget и parent deadline. Исходные ceiling 64 nodes/16 активных шагов/3 безопасных повтора — наследуемые примеры R5.3, не утверждённые владельцем обязательные числа. При UNKNOWN у неидемпотентного эффекта авто-повтор запрещён. `CURRENT_ALL` требует совместного актуального snapshot либо перекрывающихся сертификатов; два разновременных TRUE не доказывают одновременность.

## 3. Доверенные часы, согласие, отзыв и восстановление

**Fresh-time contract для C1.** Источник времени контроллера получает `(boot_id, elapsed_monotonic)` от доверенной OS, не из worker/model. Во время admission, после внешнего ожидания ввода владельца и непосредственно на границе dispatch читать **новое** время. В защищённой записи consent/ticket фиксировать точные canonical args digest, effect/scope, session_nonce, owner identity, `consent_epoch`, `consent_expiry`, `deadline`, boot ID и использованность; проверка при dispatch: все версии/current authority совпадают, `now < min(consent_expiry, deadline)`, нет STOP, proof of consent и effect допустимы. Срок согласия не должен исчезнуть между prepare и dispatch. Любое ожидание после этого check до фактической отправки требует новой проверки либо архитектуры атомарного допущения/линейризации; нельзя обещать физическое отменённое действие, если ОС уже приняла вызов. Readback может прийти позднее в пределах протокола evidence, но не заменяет consent на dispatch.

**Одна логическая граница revoke для C2.** Доверенный durable `scope_epoch/tombstone` является авторитетом для exact и semantic, независимо от места хранения bytes. Сначала транзакционно увеличивается epoch и публикуется отказ старой версии; любое чтение, использование cached semantic, GOAL/working state с производной от scope и публикация result повторно проверяют epoch. После успешной tombstone необходимо также инвалидировать уже закоммиченные `s/g` и кэши, которые могли вобрать данные отозванного scope: при отсутствии надёжного taint tracking очистить состояние сессии целиком либо восстановить его исключительно из ещё разрешённой истории. Одной проверки epoch при следующей публикации недостаточно, если старое состояние уже содержит отозванный факт. Физическая очистка может быть отложена, но чтение и применение данных запрещены сразу после успешного логического revoke; при сбое записи — состояние `UNKNOWN/DENIED` и восстановление через журнал. Эквивалентное очищение физически двух файлов одной транзакцией не предполагается. Речь не о математическом гарантированном удалении следов в параметрах, созданных из другого набора обучающих данных; scope provenance и политика производных данных нужны отдельно.

**Outbox.** Для side effect: `PREPARED` с immutable digest и sync -> разрешённый dispatch -> `SENT/MAY_HAVE_EXECUTED` -> независимый native readback -> `COMMITTED` с evidence либо `UNKNOWN`. После crash или process death не считать accepted intent доказанным outcome; восстановить pending на новой nonce, старые tickets недействительны. Фактическую атомарность и filesystem durability подтверждают fault tests A_tx/A_fs, а не сама схема. При неверном clock/boot/identity/consent — deny/unknown, не действие по памяти.

**Предел изоляции.** [ASTRA_05](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/blob/fb2b3f4c8ad299434fe555b6ccce728c58299e97/docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md#L3) доказывает отсутствие расширения полномочий только при A_cap: надёжная ОС, trusted controller и изоляция произвольного worker. Для threat model arbitrary worker отдельный isolated process без permissions является кандидатным способом, а не уже работающей реализацией. `NeuralWorkerService` сейчас stub; если выбрать тот же process/UID, необходимо доказать эквивалентную capability isolation либо честно ослабить threat model, а не переносить старую теорему автоматически. Это техническая граница, не второй мозг/облачный посредник.

## 4. Исправление проверок входных весов

Пока формат/размер не выбран владельцем, loader принимает **только явно approved versioned manifest**; не считать SHA от недоверенной пары file+manifest независимой аутентификацией. У manifest должны быть trusted origin/key и разрешённый model digest; проверка signature, schema, версия tokenizer/DSP/norm и ожидаемых shape; checked uint arithmetic для размеров, offsets/length/ranges и выравнивания, полная таблица имён/форм/dtypes/endian, отсутствие дублирования/пересечений и лишних bytes по выбранному ABI, нули reserved rows, finite decoded values и сертификаты фактических после квантования норм. Ограничить размер до allocation, отказ при любом mismatch. Закрытая оценка и качественный допуск модели отдельно: «корректный формат» не значит «научилась».

**Состояния ошибки:** отсутствующая модель -> MODEL_UNAVAILABLE; нехватка законных данных -> NO_TRAINING_DATA; отсутствие независимого readback -> UNKNOWN; memory migration неизвестна -> QUARANTINE/UNKNOWN; несуществующий режим -> UNSUPPORTED; перегрузка -> BUDGET_ABORT; отсутствие лицензии -> NOT_ELIGIBLE. Ни один из них не превращать в успешный ответ. Цифры RAM и MAC выдавать по реальным формам/allocations, физическую энергию/тепло и PSS — только по измеренному A52.

## 5. Математические пределы и регрессии

1. Finite memory: d=256 и b=32 бит в одном `g` дают не более 2^8192 состояний; множество 4096-символьных строк над 64 символами содержит 2^24576 строк. По принципу Дирихле точное обратное восстановление любого запроса только по g невозможно при этих условиях. Это пример конечного представления, а не предложение d=256 или доказательство неспособности решать практические задачи. Raw goal хранится отдельно при разрешении.
2. `R=0` не наблюдает outcome. Сохранение отдельных `R,Y` не решает missing-not-at-random; наблюдаемость, causal attribution и качество нужны в данных, а не в имени confidence.
3. Аддитивные MAC/IO/CPU-work учитываются суммой; peak RAM/disk = `max_t Σ live_i(t)`. Прогноз времени `max(MAC/r_MAC, bytes/r_BW)` — нижняя оценка при заданных пропускных способностях, не гарантия deadline. Из MAC без backend/температуры нельзя вывести J/°C.
4. После исправлений предусмотреть T01–T17 плюс clock-after-prompt, consent expiry-after-prepare, STOP/goal check-commit race, two-store crash/revoke, data leakage through I, dimension/version mismatch, weight-manifest one-byte и malformed ranges, полные исходы с denominator, finite-difference/gradient checks и реально пропущенные kernels. На момент документа они **не выполнены**.
