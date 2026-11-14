# Трассировка и ворота vNEXT-R4

R53_ORIGINAL_INDIVIDUAL_GATES.md включает все 80 строк D01–D10, X01–X12, B01–B14, M01–M44 с исходными статусами и обязательствами. R4 не переводит исторические FAIL в PASS. Ниже указано, где новое evidence действительно меняет охват проверки.

| Результат | Статус и предпосылки | Относится к |
|---|---|---|
| Источник R5.3 64 pinned bytes /63 origin SHA и оригинал V01–V20 20 SHA | PROVEN_LOCAL для integrity, SOURCE_VERIFICATION и V01_V20_INTEGRITY | B12, M01–M02; смыслы отдельно |
| S4/S5 W2/W3, mask-count и B overhead | PROVEN_LOCAL для форм/арифметики; training/export absent | D02,D07,X01,X06–X09,B03–B06,M05–M12,M19 |
| Математический градиент L4/L5 и L3a | CONDITIONAL (frozen/eligible labels, support и joint law); QAT/TBPTT названы отдельно | D03,X02,B02–B03,M33–M34 |
| P1 local descent и threshold bound | PROVEN_LOCAL при fixed trace/logit/radius. Reachability/retention REQUIRES_DATA | D03–D04,X05,B03/B09,M35–M37 |
| Новый graph A/B | SPECIFIED_UNTESTED. Fixed common path bound CONDITIONAL. Adaptive jump FAIL для безусловного bound | D02–D04,D07,X06–X07,B04–B06,M13–M20 |
| V14 TypeError/forged cursor | PROVEN_LOCAL на exact excerpt; новый exact protocol SPECIFIED_UNTESTED | D04,B09,M28–M30 |
| V19 pending outbox/boot и V20 duplicate token | PROVEN_LOCAL на exact excerpts; старые 14 virtual cases 14/14 | D05,X03–X05,X11,B07–B08,M23–M29 |
| Контроллер A_cap/A_tx/A_fs, STOP и P/M/G commit | CONDITIONAL для доверенного порядка, native fault/privilege tests REQUIRES_DATA | D05,D10,X03–X05/X11,B07/B08/B14,M23–M32 |
| Stage5 N0-07 | PROVEN_LOCAL арифметика транскрипции 80/80 rows. INVALID_LOW_MOTION_DIVERSITY и FAIL по controls (owner-reported) | D03/D06; не повышает X12/B03 |
| Полезность обучения, субъективное UX, питание/тепло | REQUIRES_DATA. Не переносить V/native load на full app | D01,D03,D06–D07,X09/X12,B01–B06/B13,M07–M09/M21/M33 |
| NCR E4/E6 и terminal limits | CONDITIONAL (полный observed loss, фиксированный sampling и independent units). Варианты превосходства REQUIRES_DATA | D08,X10,B10,M38–M43 |
| Offline/BOM, build parity, closed catalog и G6 | SPECIFIED_UNTESTED / REQUIRES_DATA | D09,D10,B07–B08/B13–B14,M44 |
| G4/O01–O08 и separate G5 | OWNER_DECISION; OWNER_APPROVED_PRECODE=FALSE, PRODUCTION_CODE_AUTHORIZED=FALSE | D01,B01/B14,M44 |

## Страты D01 и расчёт приёмки

Сохраняется исходная батарея 12: RU text/dialogue, RU voice, grounded screen, planning, native controls, local information, TTS RU, memory, plasticity, uncertainty, lifecycle/security, resources/offline. R52/03 добавляет acoustic WAKE и SENSOR как 13–14 для полной кандидатной батареи. Исторический score 13 направлений нельзя переносить. Пороги не выбраны. По классам manifest определяет task/goal, owner consent, expected oracle, допустимые источники, deadline/budget, risk и split unit. Считать отдельно correct/N, coverage/N, false effect/N, UNKNOWN/N, abort/N и censored причина. Correct abstain оценивается по независимому ожидаемому ответу, не исключается из N. Cold boot и resume/idle отдельно. Для WER/audio/MOS считать зависимость по записям/говорящим, не по отдельным кадрам.

N0-07 task scores и все V01–V20 сведены в архитектурной матрице и SOURCE_AUDIT.md. Для будущего device отчёта фиксируются per-stage confusions и human/sensor/native label source, p50/p95/p99 latency, peak PSS, thermal/status trace, measured Joules и warm/cold lifecycle. Full fit/compile/ABI shape не заменяют эти строки. Для разрешённого native эксперимента заранее заморозить контроль, отдельные OS/physical oracle, хеши источников и правила underpowered/invalid. Чем меньше результатов допускается к исполнению, тем важнее сообщать стоимость на все issued. Сырые данные N0-07 отсутствуют среди verified inputs; диагностические гипотезы не выдаются за причину.

## Условия перехода

1. G4 paper acceptance: разрешения и checkpoint подтверждены, решения O01–O08 рассмотрены владельцем, согласованы S1–S7, graph/memory/clock/authority ABI и процедуры quality/coverage/risk. Аудитор сверяет errata и исходные границы; неподтверждённые эмпирические пункты остаются в плане. Требуется явное решение владельца. Для выполнения полноценного продукта ещё нет выбранной нормативной export family, законных данных и измерений.
2. G5 entry: отдельный допуск владельца по версии и scope. Затем пререгистрированные tasks/weights/license, ABI/norm/IPC fixtures, STOP-before-D/after-D/revoke/replay, crash recovery, full task coverage, offline/network audit, held-out scores и ресурсы A52. Разрешение на малые изолированные PC experiments от 05.11 не является G5.
3. G6 release: отдельный acceptance с лицензиями/consent, воспроизводимым билдом/SBOM, security/native/thermal/regression, checked rollback и эксплуатационной документацией. Результаты в этой сдаче — предкодовые.
