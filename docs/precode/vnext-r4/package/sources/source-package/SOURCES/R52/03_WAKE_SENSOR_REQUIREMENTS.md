# R5.2 / IR03 — WAKE и SENSOR без подмены функций (КАНДИДАТ)

**Источники:** ASTRA_01 S4/S5, ASTRA_02 tensor inventory, ASTRA_03 L_wake, ASTRA_07 D01, R5.1 Grok. Рекомендация автора — **Option A: WAKE и SENSOR обязательны в продукте**, не Option B (заморозка и исключение). Это НЕ owner-утверждение.

## Обнаруженный скрытый пробел

В ABI B2 `w_wake` имеет форму `1×32` и вычисляется по metadata-only (`f_meta`, см. L_wake). Это **не акустическая модель ключевой фразы**. Наличие `W_audio` и `W_ctc` само по себе также не доказывает работу непрерывной фоновой активации с низким энергопотреблением. Поэтому R5.1 «WAKE head существует» не закрывает продуктовую задачу.

## WAKE: проверяемая спецификация без новых тайных весов

Нормативный **исследовательский baseline** для распознавания голосовой ключевой фразы:

`microphone permission + OS lifecycle → bounded local VAD/speech segment → PCM16/FFT/mel → W_audio → shared F → W_ctc → decode transcript → deterministic wake phrase grammar → wake proposal`.

- VAD — фиксированная цифровая обработка/триггер, не отдельный reasoning-мозг; если пользователь не разрешил микрофон, WAKE недоступен.
- Действительная активация — результат только после проверяемого декодирования аудио; `w_wake(f_meta)` остаётся вспомогательной оценкой релевантности события, **не называется acoustic wake**.
- После срабатывания голосовая команда идёт по обычному пути UNO с внешними разрешениями. Wake сам по себе не даёт право на Android действие.
- Незакрытые вопросы: реальная мощность в idle, надёжная работа в шуме, задержка, wake phrase variation, Android background mic policies. Использование общего ASR на каждом кадре может оказаться слишком дорогим; это обязательный device gate, а не замалчиваемое предположение.
- Если ASR-baseline на устройстве не проходит заданные батарейные/латентностные ворота, **нужна отдельная архитектурная поправка**: акустическая wake-head на `h_audio` (`1×d` вместо metadata `1×32`), с новым полным tensor manifest, пересчётом trainable/free/INT8/MAC и аудитом. Не объявлять эту альтернативу готовым B2 ABI.

### WAKE dataset + oracles

Отдельная размеченная единица — аудиофрагмент / эпизод ожидания с `speaker/session`, start/end, target phrase, distractors и explicit negative silence/noise/background speech. Обязательны независимые тесты на `false activations / hour` в непрерывном background, `false rejects / valid commands`, задержку активации, расход энергопотребления в idle, отсутствие сетевых запросов и OS permission denial. Метрики по разным людям, шумам, устройствам; не считать аудиокадры независимыми пользователями. **Пороги на утверждение** из реального product manifest, сейчас не выдуманы.

## SENSOR: проверяемая спецификация на существующих весах

`Android SensorManager/разрешённый источник → native timestamp+source+units+32 values+32 masks → W_sensor(d×64) → shared F → canonical text/goal/evidence outputs`.

- Текущие 32 физических канала и 32 маски должны иметь typed dictionary, SI units, ranges, availability and freshness TTL в versioned manifest. Sensor absent mask=0 **не означает измеренный ноль**.
- Отдельный `L_sensor`: teacher-forced CE по канонической сериализации `channel, reading, unit, source_generation, freshness state/unknown` через существующий output `E_text`, `F`, `W_sensor`. Это **проект training target, а не уже обученный loss Astra**; новых медленных матриц не требуется, но на числовую точность текстового вывода нужны строгие тесты.
- Oracle сверяет точное значение, шкалу/единицу, timestamp, missing/stale, разрешение/источник. Если readback отсутствует — UNKNOWN, без имитации измерения.
- Данные: согласованные sensor traces (валидные, missing, stale, corrupted, permission denied, reboot), со строгими правами; оценка по independent device/session groups.

## Изменения D01/L3a

ASTRA D01 содержит 12 строк. В **новой кандидатной battery** добавляются две явно названные строки WAKE и SENSOR — будет 14 строк, без заявления, что это в точности совпадает с историческими 13 классами V2.2. Требуется поимённая карта соответствия исторических категорий.

Для обоих стратумов `Z=j, π_j>0`, включая необоснованный отказ/timeout. Их `L_wake_acoustic` выражается через `L_CTC`+wake decision error (при наличии labels), `L_sensor` — через canonical teacher CE. Условия per-class coverage и независимой разметки L3a сохраняются. Изменение m с12 на14 требует обновления sampling mixture и заранее зафиксированного списка задач; исторические результаты других m нельзя переносить без пересчёта.

**Статус:** два обязательных направления специфицированы как **авторский кандидат**; реальное качество, low-power wake и полная battery НЕ PASS. Owner по-прежнему выбирает обязательность WAKE/SENSOR и пороги.
