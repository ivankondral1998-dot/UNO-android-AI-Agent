# IR02 — конкретный контракт точной памяти / конфликтов (предкодовый кандидат)

## Неинъективность
Для равновесных `v` и `−v`: `r=(v−v)/2=0`. Скалярный итог `r` не кодирует идентификаторы обеих записей. Отдельный флаг `I=∅` различает некоторые состояния, но не восстанавливает две конфликтующие записи и не делает отображение инъективным. Условная ёмкость памяти конечна, архив всех историй без потерь невозможен.

## Типы и безопасная семантика
`MemoryRecordRef=(store_generation,slot,generation,digest,source_id,kind,schema_version,created_monotonic,boot_id,expiry,provenance_ref,consent_scope,model_digest,raw_payload_ref)`. Это **предложение ABI**, а не строка, существующая в текущей ASTRA_04.

`RetrieveExact(query,scope,k,budget)` возвращает один из:

- `COMPLETE(records,scan_certificate,observed_at,expiry)` — все записи, удовлетворяющие валидации и ограниченному query scope, перечислены, число≤k, read+source validation завершены; `COMPLETE` значит полноту **проиндексированных разрешённых записей на snapshot**, не истинность мира.
- `CONFLICT(records,conflict_key,scan_certificate)` — ≥2 разрешённых записи дают несовместимые claims в одном заявленном scope/time; нельзя автоматически выбрать победителя по timestamp или neural score.
- `TRUNCATED(first_k,matched_lower_bound,continuation_or_budget_exhausted)` — >k matches или нельзя закончить полный scan в заданном бюджете. Запрещено утверждать exhaustive recall.
- `UNKNOWN(reason,seen_refs)` — индекс повреждён, нет доверенной исходной записи, истекла квота/TTL, отсутствует provenance/permission, модельная версия несовместима или новые source updates делают snapshot непригодным.
- `DENIED(permission_scope)` — query вне допустимого owner/source scope. Не смешивать с `UNKNOWN` и не выдавать содержимое.

`RetrieveSemantic` сохраняет S4 aggregate, но получает `SummaryOnly` и не имеет права утверждать точное перечисление конфликтующих записей. Все snapshot refs имеют immutable `(slot,generation,digest)`; ни одно устаревшее совпадение slot ID не удовлетворяет валидатору (ABA). `created_monotonic` сам по себе не проверяет свежесть через reboot: boot id+quarantine/revalidation. Нельзя разрешить revoke после чтения: проверить consent на выдаче и на каждом use/commit, а при изменении версии или revocation отклонить и потребовать новый snapshot.

## Детерминированное извлечение и оракул
1. Согласовать `snapshot_model_digest`, `query_scope`, `permissions_digest`, `boot_id`, `ledger_version` до чтения.
2. Фильтровать live записи по правам, generation, signature/provenance, model compatibility и времени. Не использовать untrusted record content как authority.
3. При неизвестной канонизации property/subject/time-scope → `UNKNOWN`, не forced CONFLICT/COMPLETE.
4. Сканировать все допустимые candidates до полного certificate либо выдать `TRUNCATED`. Если найдено несовместимое множество с достоверным scope, `CONFLICT` (даже если k меньше общего числа — пометить неполноту).
5. `records` содержат ссылки на raw bounded payload, `source trust level` и явно отличают `USER_DECLARED`, `OBSERVED`, `VERIFIED_COMPLETION`, `HYPOTHESIS` (последняя по умолчанию только U). `VERIFIED_CURRENT` запрещено выводить из исторической записи без fresh trusted readback.
6. Не допускать model-авторизованного изменения provenance/timestamp/permissions. Точный retrieval — локальная операция данных в controller-store, не второй интеллект, не новый gate.

## Soundness/Completeness — только условные гарантии
- При целостном конечном индексе, истинной provenance, аутентичности raw payload, корректных правах и полностью просмотренном scope, `COMPLETE` доказуемо перечисляет все **хранимые eligible records на этом snapshot**.
- Эта гарантия **не означает**: память о всех прошлых событиях (TTL/eviction), истинность claims источников, причинность native effect или собственную идентичность владельца.
- Если >k релевантных записей, возможен `TRUNCATED`; forbidden silently report COMPLETE. Если конфликт имеет неоднозначный scope, `UNKNOWN` безопаснее ложного слияния.
- При source revocation during reading проверка snapshot version/permission при отдаче ограничивает выдачу, но требует durable version monotonicity в trusted storage и runtime atomicity (`A_tx/A_fs` не проверены на Android).

## Ресурсы и проверки
В ASTRA store≤4096 slots×4096bytes. Exact search worst-case O(4096) index entries плюс ≤k payload reads, сериализация, optional re-encoding/tokens, отдельно от прежнего F MAC ledger. Кандидат k≤16; при k>16 обязательная пагинация/explicit TRUNCATED. Тестовые оракулы: identical-score ±v; 17 conflicting records with k16; ABA slot replacement; late consent revoke; cross-boot TTL; forged timestamp; unverifiable source; missing raw payload; incompatible model digest; changing snapshot while scanning; network-backed provider disabled; multiple claims with overlapping times.

**Статус**: `PROPOSED_CONTRACT`, не D04 PASS. Нужно согласовать normative ABI, exact-data authorization semantics и затем провести fault injection/retention тесты.
