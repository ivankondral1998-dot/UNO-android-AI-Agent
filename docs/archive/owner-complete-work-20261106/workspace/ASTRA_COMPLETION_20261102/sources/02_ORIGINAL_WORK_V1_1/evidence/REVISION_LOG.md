# Изменения после независимого аудита

Исходные замечания сохраняются в INDEPENDENT_REVIEW.md. Текущая спецификация исправлена после первого независимого чтения; исправления не означают, что исходный draft был правильным.

R1: явные микрофазы, producers внутренних events, reactor и pushforward kernel.
R2: время в belief-prediction маргинализировано; информативная Δ требует joint conditioning.
R3: policy в 02 согласована с влиянием P в 03.
R4: TTS использует математически согласованную пару log-target ↔ exp-decoder.
R5: G3 intact-state должен иметь current-context correctness certificate, аутентичности недостаточно.
R6: fixed metadata в pending/M содержит refs; переменные payloads имеют отдельные квоты и RAM.
R7: multiple-testing alpha-spending не заменяет защиту от adaptive holdout reuse; joint power рассмотрена отдельно.
R8: память содержит verified payload/provenance, а outcome-aware value дополняется фиксированными наблюдаемыми признаками.

R9: L_aux задаёт явные targets/градиенты value,risk,conf,wake,halt; sampling πζ параметризован; direct-gradient добавлен к score-function term.
R10: primary statistical endpoint нормирован U∈[0,1] известным K_out; power E2 не относится автоматически к raw yield.
R11: детерминированные QD/control ties и квоты; explicit next DISPATCHED; deadline before ticket; UNKNOWN non-idempotent auto-retry запрещён.
