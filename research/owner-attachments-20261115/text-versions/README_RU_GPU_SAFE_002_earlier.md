# UNO GPU SAFE 002 — безопасный учебный запускатель

**Исследовательский эксперимент. Не полноценная нейросеть UNO, не её production-веса.**

## Что изменилось

Сохранён исходный `uno_f_pilot.py` **побайтно**, SHA-256 `d290ff97eb9c58fd609d97a3c74c2a06c2b5fc0a561a3c9489776e9f8913046a`. Добавлен отдельный `uno_gpu_safe.py`. Ни формулы Astra S4/S5, ни существующие файлы весов не меняются.

- Перед началом и раз в пять шагов вызывается `nvidia-smi`. Если не удалось прочитать температуру или память, запуск прекращается.
- Порог по умолчанию: **80 °C**, **7000 MiB общей занятой GPU-памяти**, **1800 секунд на сеанс**. Порог срабатывает только в точках опроса, а не непрерывно. Это программные ограничения, не гарантия защиты аппаратуры.
- Ограничение памяти аллокатора PyTorch с запасом 256 MiB относительно порога и текущей загрузки. Драйвер, охлаждение, другие процессы остаются независимыми факторами.
- Автоматические checkpoints с моделью, Adam, RNG и состоянием генератора данных. Повторное продолжение воспроизводит CPU-результат побайтно при одинаковых настройках (тестировано).
- Проверка SHA-256 перед загрузкой предыдущих весов или checkpoint. Для импортированных весов Adam создаётся **заново**, поскольку старый пилот сохранил только `state_dict` модели, но не состояние оптимизатора.
- Режимы `fp32` (по умолчанию) и `bf16` (**опционально**). Для BF16 выполняется ограниченная предварительная численная сверка logits; это **не доказательство эквивалентности градиентов или итогового обучения**.
- Записываются `events.jsonl`, уникальные `checkpoint_step_*.pt`, `.sha256.json`, `weights_step_*_research_only.pt`, `metrics_step_*.json`. Старые checkpoints и веса не перезаписываются.
- При достижении ограничений на границе шага сохраняется последний полный checkpoint, если это возможно. Если ОС завершила процесс или GPU аварийно отключилась, сохранение последнего шага не гарантируется. Уже записанные checkpoints остаются.

## Как запустить на твоём Windows / RTX 4060 Ti

1. Распакуй `UNO_GPU_SAFE_002.zip` в `D:\OwnNeuralNet\UNO_GPU_SAFE_002`.
2. Дважды щёлкни `START_SAFE_FP32.cmd`.
3. В нём уже прописаны **твои** пути: Python `D:\OwnNeuralNet\.venv\Scripts\python.exe`, ранее обученные веса `D:\OwnNeuralNet\uno_f_pilot_001_gpu\weights_research_only.pt`, метрики с проверенной контрольной суммой, новый результат `D:\OwnNeuralNet\uno_gpu_safe_002_fp32`.
4. Будут выполнены **50 дополнительных шагов** с новым Adam, и каждые 10 шагов будут сохраняться контрольные точки. Это тест надёжного запуска, а **не полноценное новое обучение языка**.

Чтобы предварительно запустить тесты, открой PowerShell:

```powershell
cd "D:\OwnNeuralNet\UNO_GPU_SAFE_002"
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" test_uno_f.py
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" test_gpu_safe.py
```

Если запуск `.cmd` нежелателен, то эквивалентная одна команда:

```powershell
cd "D:\OwnNeuralNet\UNO_GPU_SAFE_002"
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" uno_gpu_safe.py --device cuda --precision fp32 --steps 50 --batch 64 --checkpoint-every 10 --monitor-every 5 --max-temp 80 --max-gpu-used-mib 7000 --max-seconds 600 --init-weights "D:\OwnNeuralNet\uno_f_pilot_001_gpu\weights_research_only.pt" --init-metrics "D:\OwnNeuralNet\uno_f_pilot_001_gpu\metrics.json" --output "D:\OwnNeuralNet\uno_gpu_safe_002_fp32"
```

Повторное выполнение с тем же `--output` намеренно блокируется, чтобы ничего не перезаписать.

### Продолжение обучения с контрольной точки

Если первый сеанс завершился на шаге 50 и хочется проверить именно механизм продолжения, используй **новую цель 100 шагов** (не 100 дополнительных):

```powershell
cd "D:\OwnNeuralNet\UNO_GPU_SAFE_002"
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" uno_gpu_safe.py --device cuda --precision fp32 --steps 100 --batch 64 --checkpoint-every 10 --monitor-every 5 --max-temp 80 --max-gpu-used-mib 7000 --max-seconds 600 --resume "D:\OwnNeuralNet\uno_gpu_safe_002_fp32\checkpoint_step_000050.pt" --output "D:\OwnNeuralNet\uno_gpu_safe_002_fp32"
```

Если остановился раньше 50, указать существующий номер последнего checkpoint. Нельзя менять seed/batch/lr/task/precision внутри одной серии, зато можно изменить целевое количество шагов и лимиты безопасности.

### Отдельное исследование BF16

**Только после удачного FP32-теста.** Не смешивать веса от BF16 и FP32 и не писать в одну папку:

```powershell
cd "D:\OwnNeuralNet\UNO_GPU_SAFE_002"
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" uno_gpu_safe.py --device cuda --precision bf16 --steps 50 --batch 64 --checkpoint-every 10 --max-temp 80 --max-gpu-used-mib 7000 --max-seconds 600 --init-weights "D:\OwnNeuralNet\uno_f_pilot_001_gpu\weights_research_only.pt" --init-metrics "D:\OwnNeuralNet\uno_f_pilot_001_gpu\metrics.json" --output "D:\OwnNeuralNet\uno_gpu_safe_002_bf16"
```

Для сравнения использовать итоговые `metrics_step_000050.json` из двух папок. `bf16` может оказаться **не быстрее** на такой маленькой сети. Отличие точности, задержки и Grad-CAM не доказано заранее; Grad-CAM вообще здесь неприменим.

## Проверено на стороне подготовки пакета

- Оригинальные **9 тестов** пилота: PASS (CPU).
- 6 новых регрессионных тестов: PASS (CPU): CSV-telemetry, отказ при перегреве, VRAM-порог, отсутствие мониторинга, побайтовая эквивалентность после resume, несоответствие SHA/идентификатора серии, чтение старых весов.
- Успешная загрузка существующего CPU trial и 2 дополнительных шага: PASS (CPU).
- Консистентность исходника и checksum ZIP: проверена в подготовительном окружении.

**Не проверено здесь:** реальный вызов `nvidia-smi` под твоей Windows, BF16 на RTX 4060 Ti, термопорог при реальном нагреве, реальная CUDA-запись и восстановление, parity Kotlin vs Python. Они проверяются непосредственно на твоём компьютере. Никакие GitHub Actions не запускались.

**Рамки безопасности:** программа не меняет драйвер, вентиляторы, частоты, напряжение, power limit, системные настройки и исходный проект UNO. При плохом охлаждении физический риск нельзя исключить никакой программной обёрткой.
