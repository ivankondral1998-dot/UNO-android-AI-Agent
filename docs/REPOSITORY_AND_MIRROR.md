# UNO — размещение исходников и резервное зеркало

**Статус на 2026-11-01:** GitHub существует. Владелец сообщил адрес второго приватного репозитория GitFlic, однако его доступность, Git-ветки и синхронизация ещё **не проверены**. Доступ к приватному GitFlic из текущего чата отсутствует. Нельзя заявлять о готовом зеркале до сравнения refs.

## Основной источник
- GitHub: `https://github.com/ivankondral1998-dot/UNO-android-AI-Agent`.
- Первичная ветка: `main`.
- Приватность: private.
- История Git нового UNO не должна быть историей или форком JarvisLab.

## Резервное размещение
**GitFlic URL, сообщённый владельцем:** https://gitflic.ru/project/ivankondral/uno-andraid-ai-agent

**Предполагаемый HTTPS Git remote по стандартному шаблону GitFlic:** `https://gitflic.ru/project/ivankondral/uno-andraid-ai-agent.git`. Имя действительно содержит `andraid` (как в присланной ссылке), не исправлять молча на `android`. Пока GitFlic не подтвердил Git remote командой `git ls-remote`, считать адрес непроверенным. Если GitFlic автоматически создал README, независимые коммиты надо сохранить и отдельно разрешить конфликт историй; не форсировать push.

Внутри локального клона UNO:
1. Проверить `git remote -v` и авторизацию на обеих площадках.
2. Проверить `git status`; никогда не отправлять секреты или незафиксированные материалы.
3. Запустить безопасную синхронизацию `tools/sync-gitflic.ps1` с фактическим адресом GitFlic.
4. Сравнить hashes веток/тегов `git ls-remote --heads --tags origin` и `git ls-remote --heads --tags gitflic`; не выдавать `push: OK` за подтверждение полного зеркала без сравнения.

Скрипт не удаляет refs, не делает force-push и не пишет в GitHub. Если на GitFlic найдутся лишние/расходящиеся ветки, остановиться для разбора — не удалять автоматически.

### Пример запуска Windows PowerShell
```powershell
git clone https://github.com/ivankondral1998-dot/UNO-android-AI-Agent.git D:\Projects\UNO
Set-Location D:\Projects\UNO
git switch feature/uno-repository-foundation-20261101
.\tools\sync-gitflic.ps1
.\tools\sync-gitflic.ps1 -Execute
```

Если PowerShell блокирует запуск скриптов, использовать `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\sync-gitflic.ps1 ...` только для этого запуска и после просмотра содержимого. Не менять системную политику и настройки ОС.

### Что НЕ покрывает обычный Git
Git LFS blobs, вложения Releases, GitHub Issues, PR, wiki, проекты, правила защиты, доступы и секреты, keystore. Их резервирование и экспорт — отдельные задачи. Крупные веса/APK хранить в проверяемом артефактном хранилище с SHA-256 и контрольным манифестом, не в обычных Git-коммитах.

### Переезд с GitHub
Если GitHub недоступен: продолжить работу на GitFlic с последнего **подтверждённого** общими SHA коммита; проверить локальные коммиты, отсутствующие в зеркале, до смены основного remote. Ни одна площадка не является единственной резервной копией.
