# UNO / UNOVYRA — GPU-пилот обучения F №001

**Статус: отдельный исследовательский эксперимент. Не production-модель UNO.**

## Что это

- `uno_f_pilot.py`: PyTorch-реализация оригинальных гладких формул Astra R5.3 **S4/S5** на маленькой геометрии `d=128, m=128, b=64, χ=4, J=2, K=2`.
- Точный порядок S4: `z0 → q → memory read r → z=tanh(z0+Wr r) → h0`; даже при пустой памяти `z=tanh(z0)`.
- S5: синхронное обновление блоков, C(z) кешируется один раз за событие, A/B/C **не запускаются** для пропущенного блока.
- `prefix1`: **фиксированный сравнительный** циклический префикс из S6. НЕ обученный S6, НЕ реальный адаптивный выбор. Градиенты обучаются только через фиксированный dense route.
- Тестовая задача `delayed`: показать первый числовой признак, подать отвлекающий следующий признак, позже спросить бинарный знак первого. Метка задана генератором, а не самим F. Выход через существующий тип головы Astra `w_conf`. Это диагностическая задача удержания сигнала, а не разговорный русский и не полноценная причинная память с Wk/Wv.
- Веса обучаются Adam и после каждого обновления проецируются на ограничения row-L1 Astra. LR=0.002 **экспериментальный для короткого пилота**, не официальное предписание полного обучения Astra (у неё иные warmup/cosine параметры).

## Запуск на твоём Windows (только D:)

1. Распаковать ZIP, например, в `D:\OwnNeuralNet\UNO_F_PILOT_001`.
2. В PowerShell:

```powershell
& "D:\OwnNeuralNet\UNO_F_PILOT_001\run_windows.ps1"
```

Если PowerShell запрещает запуск `.ps1`, не менять системную политику; выполнить напрямую:

```powershell
cd "D:\OwnNeuralNet\UNO_F_PILOT_001"
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" test_uno_f.py
& "D:\OwnNeuralNet\.venv\Scripts\python.exe" uno_f_pilot.py --device cuda --steps 400 --batch 64 --output "D:\OwnNeuralNet\uno_f_pilot_001_gpu"
```

**Выходные файлы** на D: `weights_research_only.pt`, `metrics.json`, `config.json`, `SHA256SUMS.txt`. В `metrics.json` accuracy и время полного F против фиксированной маски `prefix1`, количество реальных вызовов A/B/C. Это только сравнение вычислительных путей на RTX 4060 Ti, не батареи A52.

## Основание и границы

- Исходный репозиторий `ivankondral1998-dot/UNO-android-AI-Agent`, `main` `1df9ee7cc592f606939c8f004e1b11edd916b56c`.
- Первичные документы: `docs/precode/r5.3/source-package/SOURCES/ASTRA_CURRENT/ASTRA_01_FINAL_MATH_STATE_AND_DYNAMICS.md` (S4/S5/S6); `ASTRA_02_FINAL_WEIGHTS_CONNECTIVITY_AND_COUNTS.md` (W2, caps); `ASTRA_03_FULL_TRAINING_THEORY_AND_DATA_SPEC.md` (L4/L5, projected Adam).
- Kotlin reference `android/core/src/main/kotlin/org/unovyra/uno/core/UnoFReference.kt` на ветке `feat/uno-permanent-full-foundation-20261111`, Git blob `b7ec46aa7b93bfa619cecb21441b4e76b30076d3`.
- Исследовательские продолжения: `research/uno-f-gradients-20261113`, `research/uno-train-001-20261113`.

**Умышленно не реализовано:** полная Θ с E_text, Wk/Wv causal write→read, S6/L5 sampled selector/halt, L3a terminal/coverage, RU text/ASR/TTS, action gate, Android ABI, независимая Kotlin-PyTorch numerical parity проверка на общих весах. Веса пилота нельзя выдавать за production UNO.

Для независимой числовой сверки между Kotlin и PyTorch нужен экспорт одинаковых синтетических tensor values и event fixtures. В этом пакете есть собственные finite-difference тесты, но кросс-языковой oracle пока не запускался.
