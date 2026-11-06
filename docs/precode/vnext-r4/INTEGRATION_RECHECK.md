# Контрольные локальные проверки при интеграции 06.11.2026

Источник: `UNO_WORK_RETURN_PACKAGE_R4.zip`, распакован без изменения байтов; ZIP CRC `testzip() == None`; полный запуск `python -B verify_package.py` и `python -B evidence/recheck.py` из корня R4 завершился с exit 0. Точное число assertions / observed см. `package/evidence/STDOUT.json` и `package/evidence/SOURCE_VERIFICATION.json`.

Проверенные локальные negative fixtures: V14 cursor.next_slot> (пустой COMPLETE после пропуска), V19 stale authorized outbox при смене boot, V20 2×ACCEPTED с одним token. Это доказательства **дефекта контрактного охвата исторической фикстуры**, а не доказательство готовности нового кода. Source SHA-256 оригиналов V01–V20 воспроизведены скриптом R4. Никакой production APK, обучение или полное Android тестирование в этой интеграции не выполнялись.

Read-only branch SHA validation при постановке задачи: `main` 409f04bf95a0a3fec18934982d76be7285864f0a; docs R5.3 fcddf0f626cc13a60ec13200b4a48b7dee180fb4; research efdb1767ef75cbdb04ff813323c107c3bd22c4b6. Ветка основана на research. До каждого нового изменения проверять актуальный HEAD заново.
