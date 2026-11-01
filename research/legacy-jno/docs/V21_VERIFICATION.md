# V21: доказательная матрица приёмки

Обязательные уровни: **SOURCE INSPECTED → JVM/HOST TESTED → ANDROID BUILT → APK VERIFIED → DEVICE VERIFIED**. Каждому результату нужны SHA, команда, условия и фактические логи.

| Требование | Нужный тест | Текущее состояние |
| --- | --- | --- |
| Единый JNO и реальные обученные веса | Путь загрузки модели, negative SHA/magic, parity Python/Kotlin | Есть отдельный HOST TESTED пакет; штатная Android интеграция НЕ сделана |
| Пластичность | До/после опыта, сохранение, replay, corruption, migration | Узкая игрушечная G2/host, не device |
| Новый навык/перенос | Незнакомая задача, holdout, сравнение с таблицей | НЕ ДОКАЗАНО |
| Рост без забывания | Gain на новой задаче и сохранение старых | НЕ ДОКАЗАНО |
| Android действие | Permission/OwnerGate/STOP/confirmation/readback | Старый код прочитан; новый E2E не проверен |
| Полная локальность | No INTERNET в merged APK, no network calls, airplane mode | НЕ ГОТОВО: старый manifest содержит INTERNET |
| Офлайн ASR/TTS и диалог | Запуск без сети, речь после cold start/process death | НЕ ПРОВЕРЕНО для нового V21 |
| Оперативность и энергия | P50/P95 latency, CPU, PSS, battery idle/active | НЕ ИЗМЕРЕНО на A52 |
| Сохранность данных | Atomic persist, crash-restart, incompatible state refusal | Host отдельного ядра; device не проверено |
| APK и подпись | assemble, install, package, signer, SHA, launch | НЕ СОБРАН для нового V21 |

Критические отрицательные сценарии: STOP между гипотезой и действием, блокировка экрана, отказ разрешений, устаревшая задача, повреждённая модель, stale readback, ошибка/неизвестный исход, нет интернета. Ни один из них не должен завершаться ложным `STATE_CONFIRMED` или неконтролируемым повторным действием.

**Device target:** Samsung Galaxy A52 / Android 14. Запуск в авиарежиме с первого старта обязателен. Хостовые тесты не подменяют физическую приёмку.
