# UNO 1.0 — локальный канал обновления одного установленного APK, R1

**Дата:** 2026-11-10. **Ветка:** `feat/uno-foundation-hardening-20261107`. **Исходная точка:** `dc4c7de154c430d0bc8fdb71c579900320dd5ca7`. **Полномочия:** корневой `AGENTS.md` V3. Это ограниченная инженерная инфраструктура Android Lab, **не** выпуск коммерческого продукта и **не** решение о финальном packageId.

## Проблема и доказательства

1. Старая CI-команда `-PunoIsolatedDebugSuffix=ci<run_id>` намеренно создаёт **разные Android applicationId** и отдельно устанавливаемые ярлыки. Это пригодно для независимых экспериментов, но не для регулярных испытаний владельца. По GitHub Actions R3 #42805696859 исходники/host/SDK35 PASS, однако полученный `org.unovyra.uno.scaffold.ci42805696859` не обновляет прежнее приложение.
2. В Jarvis V20 `scripts/verify_lab_update.sh` уже применяет правильное правило: **тот же package, тот же сертификат, больший versionCode**. Исходник из `kolakbro5995-cpu/JarvisLab`, `recovery/v20-original-baseline-3ab8dd9-20261031`. Предоставленный ранее Jarvis экспериментальный APK сам имеет другое имя `io.jarvis.mobile.lab.experiment`, поэтому его нельзя выдавать за каноническое обновление `io.jarvis.mobile.lab`.
3. Доступный старый UNO WP04 APK `UNO_WP04_DEBUG_ci42670625565.apk` имеет по независимому binary-XML анализу manifest: `org.unovyra.uno.scaffold.ci42670625565`, `versionCode=1`, SHA-256 файла `af331736d568a14a1b8b9e05e1ce5ccfee626cd847a67780da5eba7801fcf6b5`. Владелец ранее показывал запуск этой версии, **но это не доказательство, что именно она сейчас установлена**. Её исходная signing private key через APK восстановлению не подлежит. Наличие старого подписанного APK не даёт права считать будущую новую подпись совместимой. **Дополнительный локальный read-only разбор ZIP/APK Signing Block v2:** извлечён X.509 сертификат с SHA-256 `023545379f57e611e2782ff5101048b253a7ab8eda639b708f08db1ef484cd45` (`CN=Android Debug`); это отпечаток публичного сертификата, **не** доказательство проверки APK-подписи как `apksigner verify`. Ключ из сертификата восстановить нельзя.

## Реализованная схема

- `android/app/build.gradle.kts`: режим **только при явных** `-PunoOwnerUpdateApplicationId=<existing>` и `-PunoOwnerUpdateVersionCode=<greater>`; разрешено лишь точное семейство исторических UNO Lab packageId. Запрещено соединять режим с новым CI suffix и запускать его в `GITHUB_ACTIONS=true`. `signingConfigs.unoOwnerUpdate` читает keystore/alias/password только через локальные переменные окружения. Никаких signing keys, паролей или бинарников в GitHub.
- `android/scripts/owner_update_build.py`: требует **APK, отдельно подтверждённый как установленный**, и новое число версии; `aapt` + `apksigner` читают baseline, `keytool` определяет публичный отпечаток локального keystore через `-storepass:env`; любое несовпадение **останавливает работу до Gradle**. Далее строятся `:app:assembleDebug`, `:app:lintDebug`, повторно вызывается `apk_update_gate.inspect/evaluate`; только при совпадении сформированного APK создаются **новые неперезаписываемые** `android/dist/owner-updates/uno-update-....apk` и JSON provenance. **Никакой установки, удаления, публикации или нового ключа.**
- `android/scripts/test_owner_update_build.py`: чистые локальные mock-регрессии по другой подписи, версии, чужому пакету, новому суффиксу, запрету CI, секретам в command args, невозможности overwrite и отсутствию install. Испытания с mock-подписанным APK **не заменяют** реальную проверку apksigner/Gradle/device. Скрипт подключён к `run_all_preflight.sh`.
- `.gitignore`: локальное `android/dist/` исключено из Git. Все исторические APK, Git-коммиты и пользовательские данные остаются нетронутыми.

## Локальная команда после получения подтверждённой baseline и соответствующего ключа

На **владельческом ПК**, за пределами репозитория, должна уже существовать та самая signing keypair, сертификат которой использован в APK установленной версии. Пути вроде `D:\\UNO-keys\\lab.jks` подходят для ПК-клуба; путь к секретам и значения паролей не коммитить. В терминале установить четыре локальных environment variables:

`UNO_OWNER_UPDATE_KEYSTORE`, `UNO_OWNER_UPDATE_STORE_PASSWORD`, `UNO_OWNER_UPDATE_KEY_ALIAS`, `UNO_OWNER_UPDATE_KEY_PASSWORD`.

После этого из каталога `android`:

```bash
python3 scripts/owner_update_build.py \
  --confirmed-installed-baseline-apk "/private/confirmed-installed-UNO.apk" \
  --new-version-code 2 \
  --preflight-only

# Только после успешной сверки; --new-version-code обязан быть > baseline:
python3 scripts/owner_update_build.py \
  --confirmed-installed-baseline-apk "/private/confirmed-installed-UNO.apk" \
  --new-version-code 2
```

Установить `aapt`, `apksigner`, `keytool`, Gradle/Android SDK35/NDK и существующие зависимости проекта. В данном ChatGPT host нет Android SDK/aapt/apksigner; полноценную owner-key сборку здесь нельзя выдавать за выполненную. **Если прежний ключ неизвестен/утрачен, pipeline выдаст FAIL и не создаст очередное приложение.** Новый ключ можно использовать только для **отдельно утверждённого первого запуска постоянного канала**; он не обновит старую подпись и не перенесёт приватные данные между packageId автоматически.

## Owner/device gate (ещё открыт)

- В одном установленном UNO, выбранном владельцем, получить фактические applicationId/versionCode/signature digest: через уже реализованный R3 one-tap отчёт (если именно R3 установлен), либо с телефона/подтверждённого APK другими проверяемыми средствами. Сравнить с `--confirmed-installed-baseline-apk`. Отчёт из самого приложения **не является криптографической аттестацией удалённого устройства**.
- Получить приватный **тот же** ключ подписи, либо честно объявить прежний апдейт невозможным и выбрать безопасный переход с отдельным разрешением владельца, без удаления старой программы.
- Только затем подготовить **один** подписанный локальный обновляемый APK; проверить совпадение signer, неизменность package, рост versionCode и сохранность старых данных после установки на A52. Не ставить CI-suffixed APK; не просить удалять прежние приложения.
- После истинной установки выполнить **один единый Self-Test и один JSON**, а не отдельные stress APK. STOP, AndroidKeyStore, native actions и neural quality требуют независимых evidence. Сам упаковочный контур не завершает продукт UNO.

**Статусы на момент написания:** signing pipeline `IMPLEMENTED`; tests `PENDING`; actual owner signed APK `NOT_BUILT`; A52 `DEVICE_VERIFIED=FALSE`; product `RELEASE_READY=FALSE`. Не повышать статус без логов.
