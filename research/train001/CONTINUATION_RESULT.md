# TRAIN-001 — подготовка PyTorch/CUDA, 2026-11-15

**IMPLEMENTED / HOST_TESTED / CONDITIONAL. CUDA и Windows execution НЕ проверены.**
Implementation commit: `d85b9e5b2a69893ec3cb69ce45052cd132614fbc`.

Это результат инженерной подготовки; окончательный аудит качества после RTX-испытаний пока невозможен. Владелец подтвердил PyTorch+CUDA и Kotlin как математический эталон, запретил длительное обучение в облаке и запуск007. Следующий опыт только подготовлен.

База: `44fdc357b1b6ddec5ed97188c7fd2dc3d03b7e2d`; ветка `research/uno-train-001-s4-20261115`. main на сверке: `1df9ee7cc592f606939c8f004e1b11edd916b56c`. Исходная TRAIN-001 ветка не переписывалась. Изменения только research; production/Android/main/Actions не менялись и не запускались.

## Реализация

Существующие ReverseF, LearnedMemory, MemoryReplay, TrainModel, OfflineTrainer и TrainCheckpoint сохранены. Singleton CE теперь0 с нулевым градиентом адресации вместо отказа/искусственного distractor. Replay до96 задаётся явно, default32 сохранён; truncation/отвязки нет. Предел входит в конфиг checkpoint, старые несовместимые конфиги отвергаются, миграция не имитируется.

Kotlin Ladder добавляет пять задач005B, бюджетный loop, отдельные train/validation/test, paired erased controls, memory_off/zero_values и экспорт. Все записи остаются в causal bank; target выбирается только в loss. Wk/Wv применяются к реальному source F, `f_e=0` исключает shortcut с ответом. PRNG отличается от PyTorch005B; одинаковые exported TSV — условие сравнения моделей.

PyTorch порт использует ту же гладкую математику, shared параметры, полный BPTT внутри episode, alpha=rho=.5, K2. Геометрия d64/m128/b64/chi4/J2 — ограниченный исследовательский случай, не production size и не весь B2 inventory. Ug/meta не обучены при нулевых goal/metadata. S6/halt, язык/действия, persistent Android память, AMP/FP16 derivative не реализованы.

FP32 master/gradients/Adam проверены на fixtures. Euclidean L1 threshold вычисляется в FP64 и приводится к master dtype: явный precision contract. Decoded cap tolerance FP32≤2e-6; строгий Ω/Android-export certificate отсутствует. TF32 выключен, deterministic CUBLAS обязателен. CPU fallback при запросе CUDA запрещён.

Единый atomic envelope содержит weights, Adam, RNG CPU/CUDA, step/cursor, config/source/data/runtime identity, history и validation-best. `weights_only=True`, SHA/size bound64MiB, OS writer lock. Ошибки config/data/source/cursor сохраняют отказ даже с `python -O`. Completed resume не переписывает checkpoint. Locked test пинит selection/checkpoint, после сбоя допускает повтор того же выбора; готовый результат возвращается из сохранённого отчёта. Power-loss/fsync каталога, откат диска, злонамеренный подписант и GPU-driver failure не доказаны.

## Независимая математическая сверка

Точные pins Astra01–04, Grok stage1/2 и четырёх документов Terra — `evidence/continuation/source-pins.json`. Terra audit branch сверена на `0af492ee7a8d15b371bf0de1c21d73ca1fd8b050`; исторический304b не выдаётся за актуальный HEAD. Аудиты прочитаны как источники возражений, не разрешение или автоматический PASS.

- S4: `z0→q→softmax(q·k/√m)→r→z`; empty read даёт `z=tanh(z0)`, singleton имеет нулевой score/query/key derivative. Для нескольких записей `bar(v_i)=p_i bar(r)`, `bar(score_i)=p_i bar(r)·(v_i-r)`. Запись только после завершённого F; Wk/Wv и source h в том же графе. Default eligibility/TTL/scope/revoke сохранены в Kotlin. Torch ladder — явный подслучай: одна scope/version, TTL за пределами episode, без revocations, записи только из прошлого.
- S5: все блоки читают один старый h, shared gradients суммируются по событиям/шагам/ветвям. Row-L1 ограничения дают γ≤.9 только fixed-z F; leaky step bound .95, не глобальную устойчивость всего event или меняющей маски. Полный BPTT96 проверен, универсального long-horizon bound нет.
- Projected Adam: mean batch → clip → moments/bias correction → update → Euclidean projection. Проекция не radial scaling; общий nonconvex objective не обязан монотонно убывать. Старые scalar/mutation tests запущены заново по причине изменения loss/config/replay.
- FP16 контрпример сохранён: rounding(1±1e-5)=1, численная производная0 против smooth derivative1. FP32/Double parity не решает FP16/STE/AMP контракт.

Новые дефекты исправлены: singleton rejection; locked-test crash window; нечистый batch/cursor в advance; misleading key accuracy при memory_off; FP32-only gap projection превышала собственный допуск (Us norm1.000003848 вместо≤1+2e-6); TorchVersion object ломал безопасный weights_only resume. Порог projection переведён в FP64, ограничения не ослаблялись. Два негативных memory mutants действительно обнаружены, не засчитаны за compile failure.

## 005B, 006, 007

Вложения прочитаны; пользовательский TXT побайтно совпал с CODEX_TASK.txt. ZIP SHA: handoff `69518b914c65035259abef803fd65a25bbc7dc4cbf17dfe084123840698c0313`, compact005B `38e6a42fe84c652245fdb76a656fbfc6e5a95f13844f8f4131e6f5914e74a7f5`. Сверены173 included files, handoff manifest, duplicate JSON и их train/final поля. Все10 final state_dict загружены безопасно, finite/shapes совпали. Промежуточные Adam checkpoints исключены: точный resume старого005B из передачи невозможен.

005B — SOURCE_REPORTED CUDA-run. Его F не получает S4 entries; Wk/Wv там отсутствуют, query не влияет на ответ. Lag gradients резко затухают; равные ~399k/395k параметры F/GRU не означают compute/constraint/tuning fairness. GRU cuDNN и Python unroll F имеют разные условия. Decoded FP32 caps исходных весов имеют excess порядка2.2e-7; это rounding, не доказанная причина plateau. Новых тысяч шагов005B не запускалось.

006 — SOURCE_REPORTED CPU external write-gate: удерживает state на noise/query, не S4/S6. 007 — SOURCE_REPORTED CPU prototype: фиксированные slot keys, внешняя таблица raw values, замороженная основная F; query-slot является наблюдаемым адресом, однако это не обучение Wk/Wv. Их98–99% не переносятся на нормативную память. Ни006, ни007 здесь не запускались;007 не CUDA-tested.

## Новые фактические проверки

Логи только этого продолжения: `evidence/continuation/`; исходные `evidence/*.txt` не переименовывались.

| Проверка | Факт / предел |
|---|---|
| Kotlin ContinuationTest | singleton/empty; causal prefix96 + plain-reference forward и source-event finite difference; Wk/Wv/Wq/Wr/projection/Us finite differences; batch2 exact interrupted resume; config/corruption/pending rejection; locked report crash/retry/cache |
| TrainTest | `TRAIN001_CHECKS_PASS=446`, новая сборка; тот же известный suite, не446 новых научных результатов |
| negative.sh | 4 исходных mutants ловятся нужными assertions |
| continuation-negative.sh | detached key и detached value ломают независимые gradient checks |
| cli-smoke.sh | два diagnostic updates в разных JVM; третий отвергнут без изменения checkpoint |
| host_verify.sh | existing core runner446; сборки APK/device здесь нет |
| parity.py | torch2.11 CPU: все named gradients Double/FP32 и два projected-Adam weights/m/v, отдельный FP16 forward drift. Это не весь Jacobian/все данные |
| torch_backend_test.py ×3 | r2/12, r2/96, singleton/12: actual port gradients+updates vs Kotlin, empty-read/zero_values, missing target, exact in-process resume, corruption, concurrent writer rejection, Double/FP32 |
| torch_crash_test.py |12 synthetic updates: отдельные процессы, принудительное убийство, exact weights/moments/cursor/RNG/history/best после resume; completed resume immutable; mismatch under -O rejects; CUDA unavailable не превращается в CPU |
| Windows/CUDA | NOT_EXECUTED. RTX Check должен выполнить CPU/CUDA fixtures и CPU/CUDA process-kill, проверить CUDA devices/gradients/moments, allocations/event timing; только тогда создаётся Check receipt |

Ранний100-step CPU опыт (seed47,batch4,train60) сохранён как отрицательный: mean train joint loss `.951874257→.950329178`, validation MSE `.635507138→.635896939`; selected step0. F test/erased/memory_off/zero_values168/320; GRU169/320, тоже selected0. Это **QUALITY FAIL**, не полезное обучение или превосходство S4. Одинаковые TSV и grouped GRU results сохранены; objective/fairness различия явно отмечены. Новый GPU seed150015 test ещё не открывался.

Сигнал памяти, а не качество: на фиксированном r2/96 начальный source-value derivative с S4≈8.45e-5, без memory≈−1.20e-64; Wv terminal-answer gradient~6.8e-4. Wk/Wq намного слабее (~1e-7). Это подтверждает путь через запись/чтение и отсутствие detach, не решает адресацию/обобщение. Нормы Astra самовольно не изменялись.

## Передача на RTX

Использовать только новый пакет `UNO_TRAIN001_RTX_READY_20261115.zip`; ранний `UNO_TRAIN001_RTX_20261115.zip` superseded, не передавать. Полный SHA/размер — `evidence/continuation/package-final.txt`. Windows инструкции — `README_RTX.md`; запускатель `RTX.ps1`, default Check. Источники пакета сверяются с Git-working-copy и ZIP побайтно. Материалы005B и007 в новый training bank не подмешаны.

Следующий1000-update опыт seed150015/train600/batch4/30min-per-invocation только подготовлен. Quality, actual CUDA/Windows, GPU process-crash и полный resource budget остаются до выполнения Check/Train/Resume/Evaluate владельцем. Ни результата CUDA, ни готовых полезных весов, ни RELEASE_READY не заявлено.

Основной журнал на другой feature-ветке не публиковался: **NOT_PUBLISHED**. Готовая контрольная запись этого этапа: 2026-11-15, Codex; BASE44fdc357; RESULT — `d85b9e5b2a69893ec3cb69ce45052cd132614fbc`; изменён только research; действия/проверки/ограничения перечислены выше. Публиковать её в существующий основной журнал отдельным append, не выдавать этот документ за обновление канонического журнала.
