# R5.3 — приоритет источников, нормативные границы и словарь

## 1. В чём состояла исправленная ошибка комплектации

Исходный `GROK_R53_SPEC_ORIGINAL.md` (8952 байта) не включает всех исходных S/L/W/E/R equations, полную ABI-матрицу весов, tensor JSON, градиенты и статистическую схему. **Он не подменяет 12 полных ASTRA-документов.** Этот составной пакет восстанавливает их без редактирования и добавляет явный индекс поправок. Наличие всех файлов — проверяемый факт комплектации, но не автоматический PASS всех теорем.

## 2. Порядок рассмотрения коллизий (проект нормативного приоритета)

1. **Решение владельца** о согласованных продуктовых требованиях и подписанной редакции имеет наивысший приоритет. Никакого owner sign-off в доступных файлах нет; фразы `APPROVED` в истории — не полномочия.
2. Документы `NORMATIVE/01...06` **в этом кандидате** задают редакционные замены *только для поименованных коллизий и интерпретаций*. Они не создают новый неописанный алгоритм. Их утверждение ещё предстоит.
3. В областях W4, exact memory, WAKE/SENSOR, offline SAF и политики масок специальная поправка `SOURCES/R52/01...05` уточняет или отменяет конкретно пересекающийся фрагмент Astra. `SOURCES/R51/02_W4...` и `03_MEMORY...` — доказательный предшественник, но при разногласиях по памяти применять более поздние `R52/02` (в частности `CONFLICT` только после полной сертификации scan).
4. Остальная **полная** предкодовая система — `SOURCES/ASTRA_CURRENT/ASTRA_01...12`, взятая из `ASTRA_FINAL_UNMODIFIED.zip`, а не из промежуточных R1/R2 input. Там сохраняются все S1–S*, W*, L*, P*, ресурсные ledgers, Android trust и NCR-EVO.
5. `SOURCES/GROK_R53_SPEC_ORIGINAL.md` — историческая кандидатная *сводка*. Если её однострочный контракт неполон, использовать полный Astra/R52; если прямо противоречит им — применять пункт 3/4 и фиксировать unresolved вместо домысла.
6. `SOURCES/R4`, `SOURCES/GROK_STAGE*`, `SOURCES/INDEPENDENT_*`, `WORK_V22_ORIGINAL.zip` — аудиты и история, **не альтернативная runtime-норма**. Отвергнутые исторические M-claims не воскрешаются.

Этот порядок — **предложение конечной нормативной редакции**, не подтверждение владельца.

## 3. Чёткие обозначения

| Символ | Одно значение в составной редакции | Исходник |
|---|---|---|
| `d` | ширина состояния; 512/1024/1536/2048 расчётные варианты | Astra_02 W2 |
| `b=64` | ширина блока F | Astra_02 W2 |
| `n_b=d/b` | число блоков; для d1024 — 16 | Astra_01 S5, Astra_02 W2 |
| `Mask_{t,k}` | двоичная маска блоков *на внутреннем шаге*, повторение каждого бита по `b` координатам | Astra_01 S5/S6, R52/01 |
| `MemStore_t` | хранилище точных и смысловых записей; **не вычислительная маска** | Astra_01 S1/S4, R52/02 |
| `Theta` | slow allocated tensor slots; обучаемы только free coordinates; не равно fast `P` | Astra_02 W2 |
| `P` | ограниченные online corrections; активны строки endpoint E={3..23} | Astra_04 P1/P2 |
| `q` в S6 | длина префикса активных блоков, целое 1..n_b | Astra_01 S6 |
| `q_j` в Astra_02 feasible-set | **порог качества** класса `j`, до owner decision численно не определён | Astra_02 §6 |
| `c_j` | минимальное условное coverage для класса j; .9 только исходный кандидат | Astra_03 L3a |
| `pi_j` | вероятность попадания в класс j в sampling mixture, строго положительная | Astra_03 L3a |
| `q_R`, `q_Y` | вероятности наблюдаемости и результата при наблюдаемости, не гарантия causal effect | Astra_01/03 |
| `M` в исторических S1/S4 | **MemStore**, а в S5/W4 — **Mask**; исходные строки сохраняются, интерпретация только по контексту | Astra_01 + R52 |

## 4. Карта нормативной документации (полные разделы сохранены)

| Подсистема | Первичный полный документ | Поздняя адресная поправка | Условия, не ставшие PASS |
|---|---|---|---|
| Модель состояния, causal clock, event loop, F, selector, goal DSL | `SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` | `R52/01_W4_ERRATUM.md` | whole-agent stability и fairness adaptivity |
| B2/доп. LR2/H2: tensors, counts, ABI, quant | `ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md` | R52 W4; count evidence | trained/export parity, official LR/H2 manifests |
| Полное совместное обучение L3a, L4, L5, QAT, CTC, data manifest | `ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` | `R52/03_WAKE_SENSOR_REQUIREMENTS.md` | training, licensed data, true quality |
| Plasticity P1/P2, retention, checkpoint, recovery | `ASTRA_04_MEMORY_PLASTICITY_RETENTION_RECOVERY.md` | `R52/02_MEMORY_CONTRACT.md` | Android transaction/fault tests |
| Native Android, trust, DSP, MAC/RAM/energy upper bounds | `ASTRA_05_ANDROID_TRUST_AND_RESOURCES.md` | `R52/04_POLICIES_AND_DECISIONS.md` | owner consent protocol, A52 energy/latency |
| NCR-EVO E1–E*, QD archive, statistical study | `ASTRA_06_NCR_EVO_MATH_AND_FALSIFICATION.md` | `R52/05_VERIFICATION_AND_GATE.md` | correctness/performance untested |
| D01–D10, ABI/2, production oracle | `ASTRA_07_PRECODE_ENGINEERING_D01_D10.md` | `NORMATIVE/04...` | owner/experiment gates |
| Conditional proofs and counterexamples, B1/R2 errata | `ASTRA_08_PROOF_OBLIGATIONS_AND_COUNTEREXAMPLES.md` | W4 + memory `NORMATIVE/02` | do not generalize fixed-z |
| M01–M44 legacy traceability | `ASTRA_09_UPDATED_MATRIX_M01_M44_PLUS.md` | `NORMATIVE/04...` | historical FAIL remain FAIL |
| Independent redteam/implementation/unknowns | `ASTRA_10` / `11` / `12` | owner decision register | no production implementation authorized |

## 5. Обязательный инвариант комплектности

Не удалять отдельные разделы Astra ради краткости, не превращать `SPECIFIED_UNTESTED` в `PROVEN`; сохранять исходные timestamps/hash. Ошибочный self-hash исходного R5.3 **остаётся историческим свидетельством**, но новый composite использует manifest без самоссылки. Если потребуются будущие математические изменения, они должны быть адресным erratum с доказательством и отдельной проверкой, а не молчаливым изменением первоисточника.
