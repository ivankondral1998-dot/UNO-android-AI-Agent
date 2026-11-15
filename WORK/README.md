# WORK — текущий интеграционный каркас (кандидат)

**Сначала:** [STATUS.md](STATUS.md); правила только в [main/AGENTS.md](../../blob/main/AGENTS.md) и корневом AGENTS.md этого checkout.

- `android/`: исходное Android приложение и `core/` с `UnoFReference`, `UnoFSession`, memory, controller, gates, tests, scripts. Production-исходники взяты **без переписывания** из `fix/uno-consent-freshness-20261114@d439a19320e74a3a2760fbe48a53d801812aeaff`; два test-only исправления устаревших ожиданий C3 сделаны позже на интеграционной ветке (см. `STATUS.md`, Actions #3).
- `organism/`: существующие control events из того же SHA; **не** второй мозг.
- `tools/`: существующие инструменты, не новый менеджер проекта.
- `docs/implementation/`, `docs/decisions/`, `docs/agent-work-log/`: история исправлений и решений. Они не отменяют математические источники и свежий код.

**Репозиторий структурно собран, но весь каркас ещё НЕ является работоспособным UNO.** Research train001 не копируется сюда, пока нет проверенного контракта интеграции. Любой `HOST_TESTED` в старом отчёте относится к указанному старому commit, не к этому объединённому checkout.

Проверки из корня checkout: `bash WORK/android/scripts/host_verify.sh`. Android сборка из `WORK/android/` с установленными JDK/SDK/Gradle и submodule; пока **НЕ ЗАПУЩЕНА**. Не выдать найденный GGUF-текстовый путь за единый F.

**Не изменять weights, не запускать training и не выдавать DenyAllAndroidPort за проверенный исполнитель действий.**
 
**HOST_TESTED (только Kotlin/JVM):** `97365c9348f8fc1e5a824d23ebb5767180f7b965` — [GitHub Actions #3](https://github.com/ivankondral1998-dot/UNO-android-AI-Agent/actions/runs/43664557345), `UNO_WP01_HOST_PASS=492`, `success`. Это **не** Android build/device verification. Production `core/src/main` не менялся; S4 retrieval mismatch в reference port остаётся открытым.
