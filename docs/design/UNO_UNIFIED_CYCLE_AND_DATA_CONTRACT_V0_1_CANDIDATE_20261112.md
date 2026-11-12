# UNO-UDC-001 — единый вычислительный цикл и данные для его обучения
**Редакция:** 0.1-CANDIDATE / 2026-11-12. **Авторы проекта:** GPT-6 (первый технический вариант), Grok (требуется независимая критика через issue #6).
**Статус:** `SPECIFIED_UNTESTED`. Это *инженерное предложение* для общего F, не утверждённая R5.3 baseline, не разрешение на обучение весов, изменение production Android, внешние действия или выпуск.
**Источник Android:** `feat/uno-permanent-full-foundation-20261111` @ `178ac32f53d1e84d44ca27475279d35113c19719`.
**Источник математики:** `docs/uno-r53-agent-handoff-20261102` @ `fb2b3f4c8ad299434fe555b6ccce728c58299e97`: `SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` S4–S7, `ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` L3a–L5 и §5; `NORMATIVE/02`, `NORMATIVE/03`, `NORMATIVE/05`, `NORMATIVE/06`. Полные Astra имеют приоритет над упрощённым `docs/UNO_SYSTEM_FORMULA.md`.

## 1. Доказанное исходное ограничение

| Точка | Есть сейчас | Нет/не доказано |
|---|---|---|
| `UnoChatActivity → UnoTextCycle → UnoNativeEngine/llama.cpp` | отдельный текстовый CPU inference и transcript | общий F, unified state, native Android action, independent outcome |
| `UnoActivity → UnoFoundationReferenceCycle` | типизированный Percept → exact observation → NeuralPort → bounded proposal → внешняя gate-схема | trained F; Android effect; confirmed independent device readback |
| `Contracts.kt` | `NeuralPort.perceive(Percept): NeuralOutput(stateDigest, action?)`, trust/contracts | полноценный session/context/goal ABI F, проверенные веса |
| `UnoBoundedPlanner.kt` | принимает **только совпадающие** с родительским proposal verb/args; шаг расходуется один раз | настоящая декомпозиция различных действий в план, самостоятельная постановка цели |
| `NoWeightsNeuralPort`, `DenyAllAndroidPort` | fail-closed | интеллект и разрешённое Android-действие |
| `LFM_HOST_TRIAL_20261112.md` | 700M/1.2B GGUF грузятся на host | качество Android/F, device verification; обе модели ошибались |

**Следствие:** нельзя соединить чат с выдачей Ticket простым парсингом текста LLM. Нужна одна причинная организация состояния/задач и отдельная доверенная граница.

## 2. Кандидат единого цикла U0 (не вводит второй «мозг»)

**Единственный источник интеллектуального решения** — общий оператор F с одной версионированной Θ, единой рабочей state/snapshot и входами всех модальностей. UI чата и будущие ASR/SENSOR являются *портами наблюдения*, а не отдельными независимыми reasoning-системами. Предложение и фраза для UI — два выхода одного committed logical turn. Готовый внешний GGUF, пока не доказана его интеграция в F, остаётся экспериментом, не ядром UNO.

```text
TEXT / future AUDIO / SENSOR / trusted OS events
 -> typed, bounded, provenance-tagged admission
 -> owner-goal snapshot + exact memory references (facts ≠ summaries)
 -> S4: z0 -> memory query -> r -> z -> h0
 -> S6: feasible compute / actual skipped inactive S5 blocks / bounded K
 -> unified F state hK, goal/proposal/clarification and optional UI text
 -> canonical proposal + re-encode proposal as in Astra S7
 -> planner (cannot enlarge capability envelope) -> external trust/consent/STOP
 -> durable ticket -> allowed Android native dispatch -> independent readback
 -> terminal status and evidence -> audited memory / future observation
```

**Не смешивать:** `model output` ≠ `owner goal` ≠ `Android consent` ≠ `native result` ≠ `verified current state`.

### U0-1. Вход
- Все источники через один `TurnEnvelope`: `event_id`, `boot/session`, `seq`, `event_time_monotonic`, `modality`, `source`, `scope`, `payload_digest`, availability masks, `origin_provenance`.
- Тег `authenticatedSource` и текст модели не являются полномочием. Identity/capability/permissions предоставляет отдельно *доверенный* Android gate. Нет права учить модель подменять этот gate.
- Детерминированная дедупликация событий и причинные проверки; восстановление после reboot не сравнивает голые монотонные timestamp разных boot epoch.
- `exact` содержит исходные факты только с согласованной областью доступа, `semantic` — неполное резюме и ссылку; семантическая агрегация не является lossless.

### U0-2. Единый F и предложение
- На каждом принятом событии S4/S5/S6 считаются *по тому же закону* при обучении и inference; неактивные блоки действительно не вызываются.
- `h,z,q,K` и selected mask — вычисленные и воспроизводимые traces, **не «истинные метки» от Android**. Точные счетчики seed/counter для stochastic policy должны фиксироваться; объявление argmax при обучении sampling policy без оценки mismatch запрещено.
- Возможные выходы: `ANSWER`, `CLARIFY`, `ABSTAIN`, `NOOP`, `PROPOSE_ACTION`. Текст не несёт capability. `NOOP` не означает `GOAL_ALREADY_SATISFIED`.
- Модель задаёт tentative `verb + canonicalArgs + goalId + traceDigest + modelDigest`; предложение сверяется с owner goal, schema, bounded plan, capability envelope. `Proposal` не выдаёт `Ticket` само.
- Многошаговый план **не реализован** существующим `UnoBoundedPlanner`; расширять набор verb, resource, effect или бюджеты автоматически нельзя. Механика корректной декомпозиции — отдельный `SPECIFIED_UNTESTED` дизайн-гейт, а не скрытое переименование текущего planner.

### U0-3. Доверенный итог
- Текущий Android `DenyAllAndroidPort` сохранять до отдельного допуска. В лаборатории использовать явный `NO_DISPATCH` либо контролируемый эмулятор; синтетический результат **не** объявлять независимым OS readback.
- `NativePort.dispatch` сообщает только о вызове/возврате, не об успехе. Осмысленный результат — типизированный `readback` с `ticket_id`, `endpoint predicate`, `observation_time`, `source generation`, `provenance`, `attribution`.
- Если readback нет, задержан, устарел, из чужой epoch или с частичным эффектом — `UNKNOWN`/ `MAY_HAVE_EXECUTED`, без слепого повторения. `STOP` блокирует **новые** действия и публикацию устаревшего результата, но не отменяет уже переданный OS-эффект.
- `TRUE endpoint` означает только истинность предиката в заданное время; само по себе не доказывает причинность изменения агентом и не делает все другие цели успешными.
- `VERIFIED_COMPLETION` запрещён без independent permitted readback, правильного target-time/phase/epoch и отдельной provenance. Неучтённые вмешательства третьих сторон — отдельный `attribution=UNKNOWN`.

## 3. Предлагаемый контракт данных `UNO_EPISODE/0.1-CANDIDATE`

**Единица обучения — полная причинная последовательность `Episode`, не отдельно `intent:text→label`.** Содержит `Turn[1..N]` для задач с памятью/планом/исходом; короткий single-turn — частный случай. При обучении допускается избирательное использование только корректно размеченных полей.

```text
Episode {
  episode_id, corpus_revision, generator_or_observer_version,
  source_uri_or_contract_id, source_sha256, rights: {
    license_id, permitted_train, permitted_derive,
    permitted_distribute, commercial_scope, consent_scope, pii_class
  },
  group_ids: {speaker, owner, session, device, app_family, template_family, paraphrase_family},
  acquisition: {captured_or_synthetic, environment, source_app, observer_identity},
  turns: [
    {
      turn_id, causal: {boot_epoch, event_serial, monotonic_time, prior_turn_id},
      observation: {type, bounded_payload_ref_or_digest, source, source_authenticity, missing_masks},
      owner_goal: {raw_intent_ref, target_predicate_dsl, allowed_effect_envelope, target_time_mode},
      memory: {exact_keys_and_kinds, summary_refs, retrieval_status, revocation_epoch},
      teacher: {independent_goal_label, proposal_verb, canonical_args,
                action_or_clarify_or_abstain, target_masks, annotator_provenance},
      computed_trace_optional: {model_digest, theta_manifest, s_digest, z_digest, h_digest,
                                sampled_mask_q, inner_K, rng_seed_counter, compute_cost},
      model_proposal_optional: {verb, canonical_args_digest, goal_id, trace_digest},
      trust: {authorization_status, permission_snapshot, consent_digest,
              ticket_id, phase, epoch, deadlines},
      attempt: {dispatched, native_return, may_have_executed},
      readback_optional: {source_generation, observed_at, typed_endpoint, time_semantics,
                          attribution, independent_observer, evidence_digest},
      terminal: {state, observable_endpoint_label, label_available,
                 task_complete_as_independently_defined, censor_reason, stop_status}
    }
  ],
  split: {group_key, partition, assignment_rule_version},
  transform_digest, export_manifest_digest
}
```

Список — **логическая типизация**, не окончательный JSON/ABI. Размеры, кодировки, обязательность полей по модальности, допустимые события `NONE` и алгоритм canonical digest ещё должны быть зафиксированы на совместном review; нельзя безоговорочно строить runtime по этому эскизу.

### 3.1 Четыре совершенно разные категории полей
1. **Наблюдения**: текст/PCM/UI/SENSOR/OS, время, происхождение; неизвестность и отсутствие показаний отдельными masks.
2. **Учитель и внешний oracle**: правильные goal/verb/args/ABSTAIN, независимые OS endpoint labels, нарушения, risk/confidence, owner decisions. `FALSE` нельзя ставить вместо `UNKNOWN`.
3. **Внутренние трассы**: S4/S5/S6 `h/z/q/K/Θ`; получаются исполнением модели и иногда train-only cost/quality oracle, но **не являются ground truth состояния Android**.
4. **Право и provenance**: лицензии, согласие, идентичность источника; это gate допустимости датасета, а не feature, по которому сеть сама выдаёт себе разрешение.

### 3.2 Обязательные семейства данных (кандидатная матрица, объём пока `REQUIRES_DATA`)
| Семейство | Что независимо размечать/проверять | Источник/статус |
|---|---|---|
| E01 Русский TEXT/goal | intent, однозначность, цель и valid action/CLARIFY; new paraphrases | licensed corpus + собственные оригинальные сценарии; `REQUIRES_DATA` |
| E02 OS/SENSOR/device state | типы, единицы, missing/stale, timestamps, provenance | typed device oracle; `REQUIRES_DATA` |
| E03 Audio/WAKE/ASR | PCM/keyword/negative wake, false alarms, speaker/session split | rights-cleared recordings; `REQUIRES_DATA` |
| E04 Screen/UI | UI tree, разрешённые bounding boxes, динамика UI и скрытые поля | controlled test-apps + consent, без секретов; `REQUIRES_DATA` |
| E05 Exact vs semantic memory | paired write→future query, conflict, revoke, TTL, summary insufficiency | synthetic contracts + controlled episodes; `REQUIRES_DATA` |
| E06 Goal/proposal/plan | teacher independent ordered verb/args, multi-turn dependencies, invalid envelope | instrumented safe task suite; `REQUIRES_DATA` |
| E07 Trust & consent (НЕ обучаем полномочия) | deny, expiration, auth, STOP, conflicting user intent | deterministic native/controller oracle; `REQUIRES_DATA` |
| E08 Verified outcome | before/after/timestamp/receipt/UNKNOWN/interference and missing labels | independent native readback on allowed test resources; `REQUIRES_DATA` |
| E09 Adaptive compute/halt | measured cost per active block, quality-vs-budget, train-only mask/stop oracle | bounded replay from trained/reference networks; `REQUIRES_DATA` |
| E10 Robustness/recovery | crashed PREPARED, MAY_HAVE_EXECUTED, stale time, repeat, injection, no blind retry | independent adversarial/fault harness; `REQUIRES_DATA` |
| E11 Multi-modal/relation | identical textual commands in different physical states, chained consequences | controlled grouped multi-event episodes; `REQUIRES_DATA` |

Наличие правильной формы не означает, что такие данные уже получены. Нельзя называть метку надежной только потому, что её написал Grok/GPT/LLM.

## 4. Математическая привязка — без выдуманной новой теоремы

- S4: `z0 → q(memory) → r → z → h0`, raw fact не равен `r`; S5: shared F и реальные sparse-skips; S6: q/K с сохранённой policy; S7: `q_R` (получение наблюдаемой метки) отдельно от `q_Y|R=1` (вероятность TRUE при наличии метки).
- `ASTRA_03` L3a является полным training objective для B2, включая терминальные отказ/таймаут и class coverage; L4 — градиенты повторений, L5 — дискретные решения при явно указанных предпосылках. **Ни один новый train_loss не объявлен здесь готовым к запуску**.
- Для supervised action использовать только независимые teacher `verb/args`, а не собственный ответ сети; для `outcome` только независимый endpoint с корректным availability/censor, не текст генерации; для `risk/confidence` — проверяемые targets с отдельными denominators.
- На этапе offline training по Astra `P=0`, фреймворк UNO 1.0 в runtime держит Θ неизменной. Самообучение/динамический Θ/P относится к отдельным будущим решениям. `STATIC/INTERNAL/EXTERNAL` fault-injection тесты не равны policy-learning на реальном устройстве.
- Размер сети, семейство B2/LR2/H2, параметры head, tokenizer, веса масок, пороги, optimizer и выбор хостинга **не утверждаем** до owner choice и воспроизводимых pilot/baselines.

## 5. Независимые критерии приёмки данных и будущего Android цикла

**Неподлежащие сокращению fail-cases:**
- нет прав `permitted_train` / consent или нет source digest → `QUARANTINE`, а не training PASS;
- по одному paraphrase/template/source-family есть элементы в train и sealed test → `LEAK`, не включать в final test;
- модель назвала «сделано», но ticket/readback нет → `FALSE_COMPLETION`;
- native return TRUE без независимого endpoint → `UNVERIFIED`;
- `STOP` после dispatch → `MAY_HAVE_EXECUTED`, не `CANCELLED_WITHOUT_EFFECT`;
- нет label при R=0 → `CENSORED/UNKNOWN`, не negative Y;
- `summary` выдаётся за exact raw или deleted fact resurrection → `FAIL`;
- запись из future epoch или чужой scope → `REJECT`;
- одинаковый `h` с противоположными метками → проверка неразличимости, а не фальшивое «новое умение»;
- fixed-mask contraction → не переносить на adaptive hard selection или весь агент;
- пустой корпус → `NO_TRAINING_DATA`, никогда «готово».

**Критерии полноты корпуса:** inventory E01–E11; source + rights ledger; формальная schema, версии и SHA; строгие train/dev/cal/sealed-locked/OOD splits с объединением source/template/speaker/session; coverage по классам; baseline tabular + fixed-Θ на тех же задачах; отдельные метрики полезной завершённой задачи, false action, abstain correctness, recovery, RAM/latency/energy. Пороги качества только заранее и по решению владельца.

**Первый безопасный end-to-end paper/device gate:** owner-сформулированная команда → верный canonical proposal либо CLARIFY → external gate `DENY_NO_EFFECT` → `NO_DISPATCH` → честная UI формулировка «не выполнено», точная память статуса. Этот gate **не доказывает** способность управлять телефоном; потом потребуется отдельно разрешённый native executor, independent OS readback и A52 trial.

## 6. Открытые инженерные решения на совместный review GPT-6 ↔ Grok

1. Как сохранить один `F`/единую state `s`, когда `UnoTextCycle` сейчас хранит только transcript, а `UnoFoundationReferenceCycle` принимает только `Percept` и output/action? Предложить **минимальный** способ доставки UI-текста в общий event loop без нового независимого reasoning-агента.
2. Как определить `TurnEnvelope/Goal/Effect/Outcome` с однозначной версионной сериализацией, не обходя существующие `UnoAbi` и `TrustController`? Где необходим ABI bump?
3. Как получить native readback для безопасного минимального Android effect (и можно ли получить действительно независимое наблюдение) без grant из текста модели?
4. Какие внутренние traces обязательно хранить/восстанавливать для обучения, а какие вычислять повторно? Не копировать личную память в публичные датасеты.
5. Какие две-три реальные controlled episodes дают максимум информации о недостатках F/data before training; как построить train-only oracle masks и не подогнать sealed holdout?
6. Дать конкретный counterexample к этой кандидатной схеме: подмена полномочий, ложная успешность, stale/ABA, неучтённая память, leakage или пропуск важной модальности.

## 7. Распределение исполнения после двух авторских review

- **GPT-6 + Grok:** разрабатывают и корректируют этот технический контракт, проверяют выводы друг друга, фиксируют точные открытые owner choices. Не утверждают свои гипотезы общим PASS.
- **Work:** независимая проверка полноты `E01–E11`, соответствия ASTRA_01/03/R5.3, реального происхождения/прав/объёма данных и слепых зон; документированное `PASS/FAIL/REQUIRES_DATA` с адресными контрпримерами, **не переписывать оригинал молча**.
- **Codex:** после фиксации версии — реализация предложенных валидаторов и проверки схемы, fault-injection, host tests; Android code только отдельным заданием, после разрешений и review. Никакого самостоятельного production training или GitHub Actions.
- **Владелец:** выбирает спорные модель/размер/ABI, разрешает веса и реальные эффекты. Создание этого документа не является этим решением.

**Публикация/статус:** только документальное проектирование, `NOT_IMPLEMENTED`, `NOT_HOST_TESTED`, `NOT_DEVICE_VERIFIED`, `NOT_OWNER_APPROVED`; никаких весов, тренировок, APK и изменений основного runtime.
