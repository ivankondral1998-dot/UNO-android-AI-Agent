# UNO: обязательная точка входа для всех агентов

**Статус 2026-11-02: R5.3 — кандидат. Владелец НЕ утверждал PRE-CODE BASELINE и НЕ разрешал production-код.**

## Читать строго в следующем порядке
1. [CURRENT_TASK.md](CURRENT_TASK.md) — актуальная задача.
2. [STATUS.md](STATUS.md) — факты и запреты.
3. [precode/r5.3/README.md](precode/r5.3/README.md) — навигация по математике.
4. [precode/r5.3/SOURCE_PRIORITY.md](precode/r5.3/SOURCE_PRIORITY.md) — приоритет конфликтующих источников.
5. [precode/r5.3/ERRATA_AND_INVARIANTS.md](precode/r5.3/ERRATA_AND_INVARIANTS.md) — исправления и границы теорем.
6. Полный документ соответствующей подсистемы в [sources/astra](precode/r5.3/sources/astra/), а не сводка Grok.
7. [GATE_REGISTER.md](precode/r5.3/GATE_REGISTER.md) и [OWNER_DECISIONS.md](precode/r5.3/OWNER_DECISIONS.md) — что остаётся открытым.

Не путать UNO с Jarvis/JNO. Исторический код исследовательской JNO — только свидетельство, не новый мозг UNO. Система должна работать локально без обязательного интернета. Один общий нейронный оператор, не набор независимых рассуждающих агентов. Внешние Android-разрешения обязательны; прежний OwnerGate не обязателен как компонент.

Не удалять материалы. Не изменять main, не делать merge, force push, rebase/reset, не запускать GitHub Actions/CI, не публиковать и не создавать production-код без отдельного согласия владельца. Различать PROVEN_LOCAL, CONDITIONAL, SPECIFIED_UNTESTED и REQUIRES_DATA. Никогда не утверждать baseline автоматически.
