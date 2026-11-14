# Cross-check прежнего аудита после frozen blind pass

Дата: 2026-11-02. Сначала сохранён `BLIND_AUDIT.md`, SHA-256 `c6ef0243e337ced7bfd3c1b5d983f7d207d923d6ef07b537b33376961413510a`; только затем прочитаны прежние 07,08,OPEN_QUESTIONS,INDEPENDENT_REVIEW, REVISION_LOG и SOURCES_AND_REPRODUCIBILITY. Совмещённая выдача прежнего review была усечена в начале; соответствующие строки 1–105 затем перечитаны целиком, остальная часть была видна в полной выдаче. Слепой файл после cross-check не менялся.

## Результат сопоставления

| Blind item | Прежний аудит | Состояние после сопоставления |
|---|---|---|
| B01 causal clocks | Старый A2 заметил согласование Δ/deadline; E1 принял pushforward K_ext | Исправление типов kernel не полностью задаёт causal race; это остающийся конкретный refinement, а не отмена корректности pushforward как меры |
| B02 mutable compute snapshot | Старые review упоминали phase/state и delayed traces | Полная atomic/version semantics neural snapshots не обнаружена; требуется новая спецификация |
| B03 h до/после args | Старый B4 исправил κP в policy; delayed h_issue обсуждался | Не закрыта идентичность representation полного proposal для success predictor |
| B04 readback и censoring | Старые 07 §6–7 разделяют causality/UNKNOWN; §13 замечает ограничения IPW | Не закрыт bias success-model при информативном отсутствии receipt; нужен отдельный estimand/observability mechanism |
| B05 crash unresolved effect | Старый B9 и 09 §5 запрещают опасный retry | Основной риск признан. Дополнительное обязательство: durable unresolved record с lifetime/quota/reconciliation, а не только clearing pending |
| B06 DSP/CTC | Старый A4 исправил log/softplus алгебру | Эта исправленная инверсия верна; новый замеченный gap — sequence protocol, collapse order и DSP conventions, а не повтор старой ошибки |
| B07 goals/memory | Старый B1/B3/B5 и E1 задали goal encoder, f_evidence, payload quotas | Дефолты появились, но full insertion/eviction/conflict/pin lifecycle и cross-field validation требуют дальнейшей конкретизации |
| B08 scheduling/arrival | M19–M21 ограничивают claims бюджетом и данными | Bounded RAM ≠ service/latency; arrival/service contract — новое обязательство |
| B09 training completeness | E2 закрыл omitted L_aux и missing score derivatives | Исправления подтверждены. Targets/gradients остаются условны на данных; новые manifest/curriculum/mask coverage gaps не являются опровержением identity |
| B10 multi-fidelity | 07 §13 уже исключает general correction for censoring | Conditional level probabilities/DSL completeness остаются спецификационным долгом; E1 IPW для своего fixed-pool domain не опровергнут |

Прежние критические A1–A5 нельзя механически переобъявить открытыми: в v1.1 действительно появились фазовый reactor, разделение event types, corrected spectral inverse, current-context intact certificate и ограничения reuse holdout. E2 не утверждает отсутствие любых будущих ошибок; его оговорённый CONDITIONAL PASS локальных обязанностей совместим с обнаружением B01–B10 сейчас.

## Матрица M01–M44

Исходные ID и ложные universal claims должны сохраниться. Девять FAIL: M08,M14,M16,M18,M25,M27,M32,M36,M43. M08 — не установленный минимум, восемь остальных — опровергнутые claims. Пять эмпирических NOT_TESTABLE: M07,M09,M21,M29,M41. Не заменять их PASS после документального дополнения.

Новые обязательства лучше добавлять отдельными ID, не скрывая расширение acceptance contract. Для M04/M11 нужно уточнить causal event schedule/полноту state-machine относительно B01/B02/B07. Для M12 точные TTS/CTC input-output conventions должны быть частью области, иначе проверены только явно написанные матричные произведения. Для M19/M20 различать arithmetic operation cap и measured WCET/arrival feasibility. Для M28/M26 различать atomic learn и unresolved physical actions. Для M33/M34 логическая coverage loss и условный gradient не доказывают actual training/data sufficiency. M44 остаётся фактом наличия O1–O14, но не доказательством полного future implementation blueprint.

## Финальный re-audit: обязательная процедура

До объявления готовности новой редакции ASTRA_*.md финальное заключение не выносится. После объявления необходимо перечитать именно конечные bytes, проверить все B01–B10, новый tensor ledger и conditioning/gradients, таблицу retained M01–M44 и новые obligations, затем фиксировать SHA-256 audited files. Если после re-audit файлы меняются, вердикт должен явно указывать, какие изменения были перечитаны. Отсутствие обнаруженной ошибки не становится proof of global completeness.

Никакие прошлые live repository, benchmark или source-hash claims не перепроверены сетевым доступом в данном cross-check; они остаются историческими утверждениями исходного пакета.
