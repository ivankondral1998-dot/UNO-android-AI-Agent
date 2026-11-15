# TRAIN-001 — RTX handoff (2026-11-15)

Статус: CPU HOST_TESTED; CUDA NOT_TESTED, Windows launcher NOT_EXECUTED_ON_WINDOWS.
Это существующий TRAIN-001: Kotlin — эталон, PyTorch — проверяемый исследовательский перенос тех же S4/S5/Wk/Wv. Не production, не 007, не Android.

## Что проверяется до обучения

`RTX.ps1 Check` сначала проверяет SHA всех файлов пакета. Затем сверяет с Kotlin полные named gradients и два projected-Adam updates для трёх fixtures: r2/12, r2/96, singleton/12; проверяет empty-read/zero-value controls, corrupted checkpoint и блокировку второго writer. Отдельный тест (CPU, а в Windows Check также CUDA) делает 12 синтетических updates в разных процессах, принудительно убивает процесс и сравнивает weights, Adam, cursor, RNG, history, best после resume с непрерывным запуском. Это диагностика механизма, не исследование качества.

На RTX те же короткие numerical tests идут в CPU и CUDA, в FP64/FP32. Проверяются фактические устройства параметров и objective, CUDA allocations и CUDA event timing реального matmul. CPU fallback запрещён. Только успешный Check создаёт `cuda-check.json`, который обязателен для Train. Это ещё не достаточное доказательство качества или полного бюджета VRAM/времени. Check также запускает короткий 12-update process-kill/resume тест на CUDA. Здесь он не исполнялся и не заявлен пройденным; успешная CUDA-квитанция на вашем ПК будет означать прохождение именно этих ограниченных проверок. Полный GPU-driver/power-loss recovery и ресурсы длинного запуска отдельно не сертифицированы.

## Windows: установка и запуск

Распаковать отдельный готовый ZIP в новый каталог. Нужны Windows x64, Python 3.12 x64, NVIDIA driver с поддержкой CUDA 12.8; аппаратная цель RTX4060Ti8GB. Индекс PyTorch на момент подготовки содержит torch2.11.0+cu128 cp312 win_amd64. Отдельный CUDA Toolkit для wheel не требуется. В PowerShell внутри каталога:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch==2.11.0 --index-url https://download.pytorch.org/whl/cu128
powershell -ExecutionPolicy Bypass -File .\RTX.ps1 Check
```

Только после успешного Check основной ограниченный запуск выполняет владелец:

```powershell
powershell -ExecutionPolicy Bypass -File .\RTX.ps1 Train
# После прерывания, не меняя код/данные/окружение:
powershell -ExecutionPolicy Bypass -File .\RTX.ps1 Resume
# После полного бюджета; повтор выдаёт сохранённый report, не новую подстройку:
powershell -ExecutionPolicy Bypass -File .\RTX.ps1 Evaluate
```

Здесь **не запускать Train автоматически**. Скрипт по умолчанию только Check. Никаких администраторских прав, сетевого доступа самого тренера, загрузки чужих весов, удаления прежних результатов или silent restart. Загрузка wheel нужна только для установки. Сохранить `logs/`, `cuda-check.json`, `rtx_run/` целиком. В репозиторий большие веса не добавлять.

## Зафиксированный следующий опыт

- Свежий seed150015, initial weights из Kotlin; d64/m128/b64/chi4/J2, K2, alpha=rho=.5, один активный блок. Это диагностическая геометрия, не выбранный production dimension.
- 1000 updates, batch4, train600 episodes; последовательный counter sampler cursor modulo600; validation20 фиксирована. Warmup1000 до2e-4, total schedule2000, floor2e-5; Adam(.9,.999,eps1e-8), mean episode gradients, globalL2 clip1, исходные caps Astra.
- Один запуск максимум1800 секунд; при лимите он завершает работу на сохранённой границе. GPU guard перед update: <78°C, <6500MiB общей занятой GPU-памяти; недоступный `nvidia-smi` — отказ. Проверка предельных условий не прерывает уже начатый отдельный kernel/update.
- `f_e=0` намеренно исключает raw-value shortcut. Только k=tanh(Wk h_write), v=tanh(Wv h_write), все source F и ранние read остаются в графе. Все записи хранятся; нужная/последняя запись выбирается только в loss/oracle, не в банке. Query-адрес — наблюдаемый вход, не gold key. WRITE opcode присутствует у всех baseline.
- Потеря: state MSE по координате0 к ±.8 +.3 retrievalCE +.2 valueMSE по координате0 к исходному observed scalar (r5: slot code). Это ограниченная синтетическая задача, не весь supervised inventory R5.3. Ug/meta не получают сигнал при нулевых goal/metadata.
- FP32 master/градиенты/Adam; **порог Euclidean L1 projection вычисляется в FP64**, затем результат приводится к master dtype. Это явное отклонение арифметики от чистого FP32. После приведения decoded cap excess допускается≤2e-6; strict decoded Ω/export certificate не заявлен. TF32 выключен, deterministic algorithms и CUBLAS_WORKSPACE_CONFIG=:4096:8 обязательны. AMP/FP16 storage/STE отсутствуют.
- CUDA wheel/runtime/GPU identity, source/data SHA, конфиг, weights/m/v, CPU/CUDA RNG, cursor, история и validation-best сохраняются. Один writer через OS file lock; checkpoint — единый atomic checksummed envelope. SHA — integrity, не подпись или авторизация. Process-crash recovery проверена на CPU; power-loss/fsync каталога и GPU-driver-crash recovery не доказаны.
- Test320=5 задач×4 длины12/24/48/96×16; paired erased controls, memory_off и zero_values. Test остаётся закрытым до отдельного Evaluate, выбор weights — только validation. После открытия теста не менять rates/seed/model на основании его качества. Малые коррелированные synthetic группы не дают сильных популяционных гарантий; validation20 недостаточно для заявления готового интеллекта.

## Воспроизведение подготовки из Git

JDK21/Kotlin2.2.21, из корня репозитория:

```bash
bash research/train001/prepare-rtx.sh /path/to/new-bundle
```

Готовый ZIP уже содержит initial.tsv, raw TSV splits, Kotlin parity fixtures и SHA256SUMS; Kotlin на Windows для его использования не нужен. Старые 005B веса не загружаются в этот опыт. Генератор совместим с задачами005B, но PRNG Java/Kotlin отличается от PyTorch005B. При сравнении baseline должны читать именно эти экспортированные TSV. `gru_control.py` поддерживает такой экспорт; старые результаты005B не являются baseline этого нового seed.
