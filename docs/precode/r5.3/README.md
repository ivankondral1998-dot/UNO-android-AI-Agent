# R5.3: канонический агентский индекс кандидатной документации

**CURRENT: PRECODE_CANDIDATE, NOT APPROVED.** Не пытаться использовать один краткий отчёт Grok как полную математическую спецификацию.

## Обязательный маршрут
1. [SOURCE_PRIORITY.md](SOURCE_PRIORITY.md) — какая версия преобладает при коллизии.
2. [ERRATA_AND_INVARIANTS.md](ERRATA_AND_INVARIANTS.md) — что было опровергнуто и какие условия действуют.
3. [SUBSYSTEMS.md](SUBSYSTEMS.md) — адреса полных исходных документов.
4. [GATE_REGISTER.md](GATE_REGISTER.md) — D01–D10, X01–X12, B01–B14, M01–M44.
5. [OWNER_DECISIONS.md](OWNER_DECISIONS.md) — решения, НЕ принятые владельцем.
6. [IMPLEMENTATION_STAGES.md](IMPLEMENTATION_STAGES.md) — правила G4/G5/G6.
7. [PROVENANCE_AND_GAPS.md](PROVENANCE_AND_GAPS.md) — проверенная полнота и ограничения переноса.

## Источники
- [sources/astra](sources/astra/) — сохранившиеся полные первичные математические документы.
- [audit/r4](audit/r4/), [audit/r51](audit/r51/), [audit/grok](audit/grok/), [audit/gpt](audit/gpt/) — независимые замечания и исходные исторические отчёты. **Они не нормативные замены по умолчанию.**

Полный офлайн-архив 64 файлов: UNO_R53_COMPLETE_COMPOSITE_CANDIDATE_2026-11-02.zip; SHA-256 ff5dc6fb54ab57d2d5fc687fd61d3c5d848665eb4b99ee71a1da3c759230f77c. Текущая ветка не должна заявляться полной байтовой копией всех 64 файлов.

Приоритет: явно зафиксированное решение владельца → конкретные исправления этого кандидата (после утверждения) → полные финальные Astra с применением errata → ранние работы как история. Любые спорные замены до утверждения — кандидатные, не действующий baseline.
