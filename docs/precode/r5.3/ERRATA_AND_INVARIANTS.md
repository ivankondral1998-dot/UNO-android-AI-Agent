# Обязательные ограничения математики и системных контрактов

Это консолидированный агентский индекс адресных исправлений R4/R5.1/R5.2, НЕ новая самостоятельная полная математическая теория.

## W4: fixed-mask bound и adaptive selector
При общей фиксированной маске для двух траекторий и заданном ограничении Lipschitz gamma для F:
c_M = max_j [1 - alpha * Mask_j * (1-gamma)].
Полная маска в опорной конфигурации даёт c=0.95; любая неактивная координата даёт c_M=1. Для state-dependent threshold selector может возникать скачок выхода; глобальный Lipschitz и bound 0.95^K запрещено заявлять. Не распространять фиксированные z/Mask доказательства на весь UNO. Полная выкладка: audit/r51/02_W4_CORRECTION_AND_PROOF.md; Astra_01, Astra_08.

## Memory: summary is not exact recall
Взвешенная сумма записей noninjective: одинаковый key, значения v и -v с равными весами дают 0. Разделять RetrieveSemantic(SUMMARY_ONLY) и RetrieveExact(raw references). Предусмотреть COMPLETE/CONFLICT/TRUNCATED/UNKNOWN/DENIED; полное сканирование с version/snapshot consistency, provenance, TTL, revocation, ABA handling, tombstone, conflict scanning, no silently skipping unreadable records. CONFLICT корректен только если проверка полноты действительно выполнена; иначе UNKNOWN/TRUNCATED. COMPLETE не значит, что факты верны во внешнем мире. Не утверждать lossless memory по embedding. Полные определения: Astra_04 и audit/r51/03_MEMORY_EXACT_CONTRACT_DRAFT.md; более поздние уточнения R5.2 — вне текущей текстовой ветки как точный исходный файл.

## WAKE / SENSOR
Текущий w_wake (1x32 metadata) не выполняет acoustic keyword spotting. Наличие CTC/ASR ещё не гарантирует энергоэффективное фоновое пробуждение. Для WAKE Required нужен data manifest acoustic positives, hard negatives, false accepts per hour, false rejects, idle/energy, latency, Android background permission and actual device tests. Для SENSOR Required нужен typed dictionary units/range, source identity, timestamps/freshness TTL, missingness handling, independent oracle, stale/reboot cases. Required vs Optional/Frozen — O01 не принят владельцем; нельзя молча отключить орган UNO.

## Safety, action, trust
Predicted action is NOT permission. Внешний Android controller/permissions/consent/confirmation; прежний Jarvis OwnerGate не требуется как конкретная реализация. STOP до linearization блокирует dispatch; после не может отменить in-flight OS effect. Crash-after-dispatch: MAY_HAVE_EXECUTED / UNKNOWN; no blind retry. Success only fresh ticket/epoch matching readback; receipt alone does NOT establish causality. Fast plasticity P update only after admissible verified evidence; concurrent owner action does not prove UNO caused change.

## Mask family, architecture, resources
At d=1024, 16 blocks: cyclic-prefix family 241 nonempty masks; all arbitrary masks 65535; families not equivalent, choice remains O02. LR2 rank64 is not functionally equivalent to B2; H2 changes model. CPU MAC counts are not latency, RAM peak or joules. Packed weight file != peak Android PSS. SAF provider may access network even if UNO itself lacks INTERNET; external providers disallowed in strict offline by default until explicit local verification.

## Quality and NCR-EVO
Train/dev/calibration/locked-test separation required. Coverage per class with sampling corrections, terminal/incomplete trajectories cannot be silently discarded, positive inclusion probability required. Trained intelligence, bounded forgetting, whole-agent stability, A52 fit, safe self-regeneration NOT PROVEN. NCR-EVO search needs isolated bounded candidates, independent holdouts and equal-cost baseline. No self-modifying production code without separate permission.

Refer to complete Astra_01…12 before implementing any algorithm. This file is a compact *restriction index* and does not replace full L3a gradients or tensor layouts.
