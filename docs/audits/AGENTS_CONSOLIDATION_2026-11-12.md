# UNO — аудит консолидации AGENTS.md (12.11.2026)

**Область:** 16 существовавших веток, девять различных корневых blob SHA, вложенные R5.3 instructions и pinned-text snapshot. Источник: GitHub REST branch HEAD/tree и fetch_file, до любых изменений. **Не лицензия удалять математические первоисточники.**

## Сопоставление с разработкой

| Источник root AGENTS SHA | Ветки | Что сохраняется / какой конфликт |
|---|---|---|
| `ca06e97fe37dc694de082c363173a6d6db98b8bc` | feature/uno-repository-foundation-20261101; migration/jarvislab-jno-reference-20261101; research/uno-math-reference-pass-20261101 | Исходная идея собственного локального организма, ограничения Jarvis/GitFlic; раннее «нет production» вытеснено 06.11 |
| `724b911f320f41fb674d062ebb46c0ed36f27da3` | docs/uno-r53-agent-handoff-20261102 | G4 кандидат, запрет production на тот момент; исторический, не действующая запретительная норма |
| `5fd1eb2cb68231e11db6d778ee835d8dc5975ddb` | docs/uno-lab-research-handoff-20261105 | Три источника обучения и узкое research permission; не общее разрешение обучать |
| `b53a92ab56e415a11a42c9ca00c45b34c6818443` | docs/uno-vnext-r4-source-recovery-20261106 | source map/материалы R4, historical documentary stage |
| `a3666218231369f4177967c81a6c30fcaaa853fc` | audit/uno-experiment-evidence-20261107 | исторические ограничения и краткая коммуникация |
| `eb5d81e2474bf8c2944435876d2bfce80b46c215` | feat/uno-production-foundation-20261106; integration/verified-host-utils-20261111 | V3 с более строгим запретом CI; код разрешён с 06.11 |
| `99365f29accd6b17c1629d43c2569527189e7203` | main | V3; 11.11 narrow promotion; CI только по отдельному поручению |
| `3397443f1fbd62d28ed1233e6f4be2851094e95c` | audit/uno-terra-math-training-20261112; design/uno-unified-cycle-data-20261112; feat/uno-foundation-hardening-20261107; feat/uno-permanent-full-foundation-20261111; feat/uno-wp03-s4s5-cpu-reference-20261111 | V3 + узкое разрешение от 08.11 на feature CI; продолжение разработки без самопластичности runtime |
| `53d6603068f4d8fe5b7db5cc4f4458dee3ef23f5` | feat/uno-permanent-single-apk-20261111 | V3 + 08.11 CI + отдельное решение о едином APK/постоянном ключе |

**Разрешения не суммируются автоматически.** В основном документе воспроизводятся фактические решения, а новые рискованные действия требуют явно применимого поручения.

**Архивирование без потери истории:** root `AGENTS.md` других веток удаляются только из новых HEAD и остаются в родительских коммитах; вложенные `docs/precode/r5.3/AGENTS.md` получают имя `docs/precode/r5.3/LEGACY_AGENT_INSTRUCTIONS.md` без изменения содержимого и blob SHA, pinned snapshot аналогично. Это сохраняет первоисточники и исключает их автоматическую активацию как scoped AGENTS. Все ветки сохраняются.

**Важное ограничение:** Git не умеет физически иметь один файл одновременно в нескольких независимых ветках; канонический `main/AGENTS.md` должен явно читаться через README-ссылку. Offline/worktree-агент без main access не гарантированно видит правила, поэтому не должен выводить разрешения из старых текстов.

Текущее поручение НЕ включает изменение Android-кода, обучение, Actions, релизы или межветочные merge.
