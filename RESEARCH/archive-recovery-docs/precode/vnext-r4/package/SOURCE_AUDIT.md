# Происхождение и повторная проверка

## Checkpoint и маршруты

| Источник | Точная версия | Применение |
|---|---|---|
| GitHub research | docs/uno-lab-research-handoff-20261105 @ efdb1767ef75cbdb04ff813323c107c3bd22c4b6 | AGENTS/README/start/task/status, BENCH, UNO_LAB_AGENTS и owner evidence/N0-06; актуальный research permit, G4/G5 |
| GitHub normative | docs/uno-r53-agent-handoff-20261102 @ fcddf0f626cc13a60ec13200b4a48b7dee180fb4 | docs/precode/r5.3/source-package. 64 import entries совпадают с исследовательским tree, 63 origin SHA verified в предыдущем ходе |
| GitHub main | 409f04bf95a0a3fec18934982d76be7285864f0a | Контрольная ссылка, отдельная ветка |
| Work | vNEXT-R3 + FINAL_RECHECK от 06.11 | Открытые пункты, history; точка замены перечислена в errata |
| Оригинальный brief | NCR_EVO_ASTRA_RESEARCH_BRIEF_2026-11-01.md | Прочитан полностью. Immutable contracts, отдельные mutator/selector/oracle, bounded search, цена и falsification. Исторический Jarvis как потребитель не переносится в UNO |
| V fixture source | UNO_R41_A52_V01_V20_ALL_TESTS_AND_RESULTS_REV2_2026-11-04.txt, rev2 479306 B, SHA e881d6029227bf6b7e2586409b51540d8ce0596c56609978d40b697f09ad16e7 | Восстановлены 20 original Python blocks, проверены SHA по индексу, AST/контракт. Отчёт A52 исторический |
| Stage 5 | research/uno-n0-07/results/OWNER_A52_STAGE5_CATEGORICAL_TRACE_RECONSTRUCTED_20261106.csv, Git blob 9c8ad6d9e90c9abc13e4f54ddb9ec3f7ae5f3cac | 80 строк проверены и пересчитаны. Сырой 400-row export и независимый device fingerprint отсутствуют |

Привязка основных выводов: causal time/STOP S1–S7 → ASTRA_01 §§1,4–7, ASTRA_05 §§1–2, V19/V20; weight shapes/decoded bounds → ASTRA_02 W2/W3/W4, R52/01, R4.1 §21; L3a/L4/L5/CTC/QAT → ASTRA_03 §§1–4, данных §5–7; memory/P/recovery → ASTRA_04 P1–P3, R52/02, V14–V18; full DSP/energy → ASTRA_05 §§3–6, R52/03–04; NCR → ASTRA_06 E3–E6 и оригинальный brief. D/X/B/M: ASTRA_07/08/09 и NORMATIVE/04; статус G4, unknowns и границы → ASTRA_10–12, NORMATIVE/05–06, R52/05. Ревизия не меняет исторические FAIL. Полный предыдущий архив UNO_ALL_WORK_AND_SOURCES_2026-11-06.zip сохраняет всю историю, включая ранние копии и исходные отчёты. Новая сдача содержит компактную базу, извлечённые фикстуры и добавленный анализ.

## V01–V20 — что фактически покрывается

Для всех строк подтверждены байты и синтаксический AST. Исторические числа перенесены из индекса rev2. Native binary и устройство в этом аудите не запускались. Выборочно вызваны только указанные функции V14/V19/V20, а не весь stage harness.

| ID | Содержимое и исторический результат | Что можно заключить и что остаётся |
|---|---|---|
| V01 | controller + SQLite writer, 168 попыток, 115 REQUEST→ACK окон | Наблюдения окна при CPU load. Не доказан STOP на общем IPC/permission gate |
| V02 | Directed precommit race, 42 случая, 10 post-request commit отрицаний | Локальная сортировка событий/commit race, не гарантия обо всех interleavings |
| V03 | Durable STOP/receipt order, 2×32 | Синтетические txn при выбранном backend. Внешний эффект вне модели |
| V04 | independent ingress writer, durable STOP, 64 | Несколько процессов не означают отдельный trust UID |
| V05 | restart disarm/watchdog, 80 | Негатив held tx блокирует watchdog. Верхняя задержка STOP отсутствует |
| V06 | dual guard loss/replay/bypass, 96 включая 24 негатива | После обеих votes/при открытом tx и same-UID DB bypass возможны нарушения. Нельзя заменять OS isolation голосованием процессов |
| V07 | typed TASK/BARRIER/SCREEN/SENSOR/PCM, backpressure, 24 | Кодек/очередь/синтетический payload. Нет испытания всех native permissions и ASR |
| V08 | six-slot sensor freshness, 20/20 направленных, затем RAM safety abort | Свежесть отдельных случаев. Полный stress не завершён, память/тепло продукта не измерены |
| V09 | ранний skip и позднее зануление, 18, reported 3.025×/2.030× | Изолированные execution branches; не портировать коэффициент на весь UNO |
| V10 | cyclic prefix/K/MAC cap, 24 пары +12 abort | Согласование F-only путей, не бюджет полного event |
| V11 | prefix sampler/hazard, 156 решений | Xorshift32 и synthetic fixtures. Не производственный RNG/logprob и не learned selector |
| V12 | after-step state-dependent hazard, 96 trials | Внутренний порядок halting, не глобальная устойчивость |
| V13 | precharge MAC/workspace/tokens/time, 32 | Квоты синтетического полного прохода, не реальные joules или hard deadline |
| V14 | 72 exact/ABA/corruption/pagination случая, 4-slot fixture | Новые host witnesses: TypeError на принятом query и forged next_slot даёт COMPLETE. Полный R52 не покрыт |
| V15 | recovery/transaction journal, 80 и 4 negatives | Integrity и replay с known reference. Same-UID forged chain negative показывает отсутствие аутентификации по SHA |
| V16 | semantic vs raw exact, 72 и 4 negatives | Коллизия/CONFLICT/missing raw. Same-UID semantic poison отрицателен. Ни sum, ни hash не заменяют authority |
| V17 | общий 4096 slots, 48 | Стенд capacity/byte stores. Не PSS всей модели; foreign-model eligibility в fixture исключает записи из scope |
| V18 | SQLite WAL/reader snapshots/revoke, 36 и 4 negatives | Consent TOCTOU отрицателен. Snapshot isolation не заменяет revalidation перед disclosure/decision |
| V19 | causal clock virtual scenarios с CPU background, 56, 8 negatives | 14/14 исходных виртуальных cases повторены. Новые: idle с pending outbox, BOOT пропускает старый outbox. EVENT_LIMIT проверяется перед batch, не до каждого event; нельзя переносить его как cap на любой batch |
| V20 | live STOP/timer vs native F, 48 и 4 negatives | Старый token после STOP rejected, два одинаковых до STOP приняты. Synthetic transaction. Ни effect, ни used-ticket idempotence не проверены |

## W-R4-01

evidence/FROZEN_CARD.md и PRE_RUN_SHA256.txt зафиксированы до запуска. Команда из корня пакета: (ulimit -v 262144 && timeout 30s python -B evidence/recheck.py). Python и SQLite версии, 18 результатов и конкретные observed values в STDOUT.json, stderr пуст. Повторяются только разрешённые AST fragments из 3 файлов под hash guard, sqlite temp files и арифметика. V19 повторяет исходные 14 virtual tests. 18 успешных проверок включают подтверждение контрпримеров, не число пройденных Android тестов. Фактическая новая реализация исправленных контрактов остаётся SPECIFIED_UNTESTED.

На diversity-valid controls N0-07 у исходного F 38/160, persistence 117/160, Markov 100/160 по owner-reported aggregates. Stage 5 csv: F/persistence/Markov все 77/80, переходы 3 при frozen минимуме 8, все прогнозы MOVE. Источник csv установлен хешем Git blob, а не подписью телефона. Нельзя из этих данных вывести причину collapse, прирост owner teaching, phone weight fingerprint или действие Android.

## Официальные источники Android

- elapsedRealtimeNanos учитывает deep sleep. SensorEvent timestamp использует ту же шкалу; проверять generation/boot отдельно. [SystemClock](https://developer.android.com/reference/android/os/SystemClock) · [SensorEvent](https://developer.android.com/reference/android/hardware/SensorEvent)
- CameraManager setTorchMode и TorchCallback сообщают состояние torch, эксклюзивный контроль не обещается. Callback не подтверждает физическую яркость, не несёт ticket UNO. [CameraManager](https://developer.android.com/reference/android/hardware/camera2/CameraManager) · [TorchCallback](https://developer.android.com/reference/android/hardware/camera2/CameraManager.TorchCallback)
- SAF включает local и cloud providers. Mic/FGS и MediaProjection ограничены lifecycle/consent. Подтверждение фактических perms на A52 — G5/device gate. [SAF](https://developer.android.com/guide/topics/providers/document-provider) · [FGS](https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start) · [MediaProjection](https://developer.android.com/media/grow/media-projection)
