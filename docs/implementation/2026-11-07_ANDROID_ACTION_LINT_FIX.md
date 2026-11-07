# UNO WP-01 Android CI — конкретное исправление Lint

- Первый Actions run: https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42390742176 (FAILED at Android lint; Gradle `:app:assembleDebug` succeeded).
- Ошибка: `LabSystemMetrics.kt:66`, метод `Debug.getRss()` требует Android API 35. Прежняя проверка допускала API 29, поэтому была несовместима с целевым Samsung A52 Android 14 (API 34).
- Исправление: вызываем `getRss()` **только при SDK_INT>=35**; на Android 14 `self_rss_kib` записывается как null/UNAVAILABLE. PSS остаётся доступной метрикой и не подменяется RSS.
- Сборка только debug и в приватном Actions artifact. Никаких production-релизов, сертификатов и изменения `main`.
- Приёмка: повторный CI lint, сборка APK, SHA-256 и метаданные пакета. Device test A52 отдельно.
