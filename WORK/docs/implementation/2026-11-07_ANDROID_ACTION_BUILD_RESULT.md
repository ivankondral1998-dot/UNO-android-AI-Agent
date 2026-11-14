# UNO WP-01 — первый успешный Android Actions debug APK

**Дата:** 2026-11-07. **Источник:** GitHub Actions run [42391092683](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/42391092683), job 128458628296, status `completed/success`.

- **Ветка и точный CI source SHA:** `6bf9d5f406d27ef758d6f3059c790ee381c55729`.
- **Пакет:** `org.unovyra.uno.scaffold`; versionCode 1; versionName `0.1.0-skeleton`; minSdk 26; targetSdk 35; compileSdk 35.
- **APK:** `app/build/outputs/apk/debug/app-debug.apk`, **880638 байт**.
- **SHA-256 APK:** `fb49afa67cbb4cc3591d72728da5ae8b649e5560e6d3c754b65ad58c610a728f`. Совпало между файлом, независимым локальным подсчётом и CI `sha256sum`.
- **Private Actions artifact:** ID `13581726608`, имя `UNO-WP01-debug-apk-2`, хранение 14 дней.
- **Tests:** Kotlin self-test runner `UNO_WP01_HOST_PASS=100`; 6 Python tests PASS; static preflight `STATIC_PREFLIGHT_PASS=7`; `assembleDebug` SUCCESS; `lintDebug` SUCCESS (0 errors, 7 warnings). Toolchain Ubuntu24.04/JDK17/Gradle8.7/AGP8.6.1/SDK35.
- **Исходная проблема CI:** run 42390742176 нашёл неверную проверку для `Debug.getRss()` (API35, а guard допускал API29). Исправлено отдельным коммитом до успешной повторной сборки.
- **Manifest:** в текущих исходниках отсутствуют `uses-permission`, включая `INTERNET`. Существование сетевого поведения будущих зависимостей так не проверяется; текущая диагностическая сборка не содержит облачного ядра.

## Граница утверждений

**Статус:** `ANDROID_BUILT`, но **НЕ `DEVICE_VERIFIED`**. На Samsung A52 установка и физические показатели не проверялись. Это тестовая лаборатория, без обученной модели, голосового ИИ или настоящего Android-dispatch. APK подписан временным debug-ключом runner: дальнейшие сборки могут потребовать стабильной подписи для бесшовного обновления без потери данных.

**Известные предупреждения Lint:** 7 непадающих предупреждений; включая отсутствие постоянной иконки приложения и условия экспорта/UX. Не путать lint PASS с UX/безопасностью готового продукта. App label в выводе `aapt dump badging` пустой, хотя в манифесте указан текст; требуется проверить отображение названия на реальном устройстве.

Никакой release-подписи, публикации или изменения `main`. Следующая независимая приёмка — Android14 / Samsung A52, установка, запуск и raw ADB-трассы.
