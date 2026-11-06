# UNO — адресная ведомость 41 не зеркалированного файла (исправление 2026-11-06)

**Статус после исправления индекса:** первоначально 41 исключение; один paper проверен как точная копия в Git, поэтому **актуальный остаток — 40: 24 индексированных + 16 исследовательских/приватных**. Таблицы ниже сохраняют исходные 41 записи как историческую сверку, включая найденный paper.\n\nЭто дополнение к [полному реестру 396](../archive/OWNER_COMPLETE_WORK_ARCHIVE_INDEX_20261106.json), не замена исходного архива и не разрешение G4/G5. Проверенный источник списка — GitHub JSON; сами байты перечисленных 41 файлов **не** подтверждены в текущем Git tree. Источник: `UNO_ALL_WORK_AND_SOURCES_2026-11-06.zip`, SHA-256 `8c87ebec317f9acd8398a1ff239edfccb193c0e182e0f91ef447bcb3b26ac02b`.

## Исправление классификации

- `INDEXED_NOT_MIRRORED` — 25 записей; это **не значит**, что все дубликаты, ненужные или бинарные. Включены исходный `00_START_HERE.md`, `VERIFY_OUTPUT.txt`, `SHA256SUMS.json`, `UNO_R4_1_ENGINEERING_RECHECK_2026-11-04.sha256`, самостоятельный paper и исторические ZIP.
- `OWNER_PRIVATE_OR_RESEARCH_BINARY_NOT_MIRRORED` — 16 записей. Из них **2** — переписка/память (конфиденциально), остальные **14** — N0-01–N0-07 research ZIP/APK/исходники. Метка «private» не означает, что все 14 исследовательских источников должны быть недоступны агенту: требуется отдельная классификация содержимого.
- Один paper `workspace/UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW.md` имеет **точную локальную SHA-256-копию** в `docs/archive/owner-complete-work-20261106/workspace/project_sources/04-UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW-1-.md`. Следовательно, утверждение «его текст отсутствует в GitHub» ошибочно. Исходная запись сохраняется для происхождения; **удалённый hash readback выполнен**: Git blob SHA-1 `a143cfd1a863a89bbc30f2f11b8d310e31118410`, локальный SHA-256 `b4a65751806d96573d21e727f817582db62764862b19131ca892ddece39affb2`. Статус в машинном реестре исправлен на `MIRRORED_IDENTICAL_CONTENT`.
- Не смешивать «сырой N0-07 полный экспорт с телефона не установлен» с наличием N0-07 APK, source, reports и stage5 реконструкции.

## 25 индексированных без прямой копии

| Путь в архиве | Тип | Байт | SHA-256 |
|---|---|---:|---|
| `00_START_HERE.md` | MD | 2274 | `e7c4d4457ade1b5e53ed1ece714ae2d5b905895860762c43b8d6bd477c3962e8` |
| `VERIFY_OUTPUT.txt` | TXT | 2082 | `c8527978398b1f3b879df3ae50db67b969bf8a3afa79e41c4928a882baf9741a` |
| `workspace/UNO_ENGINEERING_RECHECK/SOURCES/REPAIR_INPUT.zip` | ZIP | 6779248 | `90b597134421f796d82a8f10f10ee1ee483d1d854a4ddca820e5cf12527add2c` |
| `workspace/UNO_ENGINEERING_RECHECK/SOURCES/UNO_GITHUB_COMMIT_fcddf0f_SOURCE.zip` | ZIP | 2901171 | `183f40a4d0ba2ee4b75bee530c20e93e1a0fb03258424e8b5184dceb323730d9` |
| `workspace/UNO_MATHEMATICAL_DESIGN_AUDITED_2026-11-01.zip` | ZIP | 150063 | `72609211e79b312586bace29e5d53643a0dc7af422f450febd5770b5d211f86c` |
| `workspace/UNO_MINIMAL_ORGANISM_PAPER_FINAL_FOR_OWNER_REVIEW.md` | MD | 148311 | `b4a65751806d96573d21e727f817582db62764862b19131ca892ddece39affb2` |
| `workspace/UNO_R4_1_ENGINEERING_RECHECK_2026-11-04.sha256` | SHA256 | 110 | `54f9f82e135f283d5152fb7a3870ec3ea744b15ccdc7c32aca9de439a08918d9` |
| `workspace/UNO_R4_1_ENGINEERING_RECHECK_2026-11-04.zip` | ZIP | 9914479 | `19b8eb60db0515acd28ceb2de4c348e9c01e5ad979c4f58898df1f9f2f65553a` |
| `workspace/UNO_R4_REVIEW_CANDIDATE_2026-11-04.zip` | ZIP | 61970 | `8284d4b4358f7cd46a92a44c818da34dde26d7a03b47399e8996403e6ad3b298` |
| `workspace/UNO_WORK_RETURN_PACKAGE.zip` | ZIP | 85379 | `061807f800d668883910021ac953295529c6782b6d272320cbfd014ecc99de58` |
| `workspace/UNO_WORK_RETURN_PACKAGE_R2.zip` | ZIP | 94686 | `4bbf09105f447825ec7f43c4eec22a96ca4b95bf192870b6a82ab098c1cfbe61` |
| `workspace/UNO_WORK_RETURN_PACKAGE_R3.zip` | ZIP | 97615 | `494383efdcde31f1186b4e4c39745dbc394f381d9658211ebaaaa5f1da38c42a` |
| `workspace/completion_source_download/UNOVYRA AI Agent Adaptive Neural Organism/ASTRA_FULL_MATH_COMPLETION_PACKAGE_2026-11-02.zip` | ZIP | 169216 | `8caa1dd02a22716a64c130785d0f07510028059d83426e017ff39fd72359877a` |
| `workspace/project_sources/02-UNO_GROK_CORRECTED_MINIMAL_ORGANISM_2026-11-03.zip` | ZIP | 4266 | `1b6eaf63c731313bf0c7840bda22c3b53269cf7195f4688ee5feef9f1cb1a523` |
| `workspace/project_sources/06-UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03-1-.zip` | ZIP | 841121 | `4f9f59123b40a47a4bc2783f3633f0314a69fbac8c7cdb638dad3b3a1efc59b1` |
| `workspace/upload/01-1793954615763.jpeg` | JPEG | 159905 | `0d6c2ab6e8ac4bbfc66f687d6b0dbff34c8a874a3c7802a66a0619822e0a7ffd` |
| `workspace/upload/UNO_COMPLETE_RESEARCH_HANDOFF_FOR_WORK_2026-11-06.zip` | ZIP | 1460218 | `01edce3dbea39a8a169f27cc85da1ad2e4e815a6f3ada198761bd0b8b5273fed` |
| `workspace/upload/UNO_TO_WORK_R3_FULL_SOURCE_REPAIR_2026-11-04.zip` | ZIP | 6779248 | `90b597134421f796d82a8f10f10ee1ee483d1d854a4ddca820e5cf12527add2c` |
| `workspace/upload/UNO_WORKFLOW_RECOVERY_VERIFIED_V2_20261106.zip` | ZIP | 18451 | `8df81f4ba8fc30d27260504ed90412f37a11698b9857281426a142cb7507ca73` |
| `workspace/upload/UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03.zip` | ZIP | 841121 | `4f9f59123b40a47a4bc2783f3633f0314a69fbac8c7cdb638dad3b3a1efc59b1` |
| `workspace/upload/UNO_WORK_MATHEMATICAL_HANDOFF_2026-11-01.zip` | ZIP | 29224 | `dd54ae37928b1b9f4b97386c7b255740bdf55dfbce3b9aea0b6e4651fd880737` |
| `workspace/upload/uno_handoff/original_assets/UNO_GROK_CORRECTED_MINIMAL_ORGANISM_2026-11-03.zip` | ZIP | 4266 | `1b6eaf63c731313bf0c7840bda22c3b53269cf7195f4688ee5feef9f1cb1a523` |
| `workspace/upload/uno_handoff/original_assets/UNO_LIVING_RELATION_R01_RESEARCH_20261105.zip` | ZIP | 14105 | `046e576a7cc001030214ea24aa1e4d871d952015431eedf728f57d0dde3830d1` |
| `workspace/upload/uno_handoff/original_assets/UNO_WORK_COMPLETE_PAPER_HANDOFF_2026-11-03(1).zip` | ZIP | 841121 | `4f9f59123b40a47a4bc2783f3633f0314a69fbac8c7cdb638dad3b3a1efc59b1` |
| `SHA256SUMS.json` | JSON | 76050 | `2b8c4c41e4aaa03fc409fbf84de97c405a6ecb8aec7f0001ef6552423251e40d` |

## 16 исключённых по приватности/исследовательскому бинарному типу

| Путь в архиве | Тип | Байт | SHA-256 |
|---|---|---:|---|
| `workspace/project_sources/08-CHATGPT_HISTORY_10_OF_10_AGENT_MEMORY_2026-11-03-1-.zip` | ZIP | 101750 | `77abdaaeb35436f231a33662a965a671f8a6565f4bdfb90fd0884a60b85a520f` |
| `workspace/project_sources/09-MASTER_CHATGPT_DIALOGUE_MEMORY-1-.md` | MD | 127063 | `2e588fada97369977e751e0d44d5dd5f3b4c46aecc33ed67a465163085f79e84` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_01_RESEARCH_TRAINED_2026-11-05.zip` | ZIP | 21008 | `0abbaafcafe8912be75f7bc0b36d43f6d0f715bda8884af81d89594909c49226` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_02_LOCAL_PLASTICITY_RESEARCH_2026-11-05.zip` | ZIP | 23747 | `8a94fe5e9b82e5732691967e47170e2bbe9a85ba7f83ca0f1c713538a889a1fe` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_03_ANDROID_SOURCE_2026-11-05.zip` | ZIP | 12375 | `fd65678d489977a614a74b93198c0f216f4a608b1473eb7ea125e36316709c79` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_04_ANDROID_RESEARCH.apk` | APK | 41387 | `791b171351c600eb6f493767ecdfe16efbc4b608e21a07fe22dffd9c4fb905c9` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_04_ANDROID_RESEARCH_ARTIFACT.zip` | ZIP | 21835 | `b6c7360f0138d2380d28c1c44b37d66c00430c272ab09c08a58f89dc9b3382ce` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_04_ANDROID_SOURCE_FINAL_2026-11-05.zip` | ZIP | 20825 | `defda9ac135c8b6ba02834c50cacbf628327850b73eee0011f42447ece22d76c` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_05_DIAGNOSTIC_20261105_SOURCE.zip` | ZIP | 27565 | `b32100e58ee79b7f5a30d0a5530c9e95936550d6ec7bbea0b78f31b16cfbf5f2` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_05_NEURAL_AUDIT.apk` | APK | 45483 | `052335fadd1c81d9ddf47488ac05ec4cb911d3ab527a265d6a8b637b364fe511` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_05_NEURAL_AUDIT_CI_ARTIFACT.zip` | ZIP | 25236 | `138dbe7ec4a2fb7613f2937c8b72a06f47d75f59fd1e3f6969373e106e1152da` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_06_HOST_PILOT_20261105.zip` | ZIP | 19940 | `d0679dedef983935078b0a1c4b435eeda72763a632cf80a4a7338da926f5ac35` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_07_APK_FOR_PHONE.zip` | ZIP | 27414 | `6b9495f535e103d7d0f4a8e05ad27c375f39394431ab382f57790c5658861e5d` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_07_TINY_F_CI_ARTIFACT.zip` | ZIP | 30749 | `edb93e1611d8dc1a9cc416ec15db3dece4fd789468d0c526d529dd7336641698` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_07_TINY_F_ORGANISM_20261105.zip` | ZIP | 67585 | `5469dbd65d1df53bac3314b00135ea35693d7c6e5cae465bcc5faedd310d1531` |
| `workspace/upload/uno_handoff/original_assets/UNO_N0_07_TINY_F_RESEARCH.apk` | APK | 53675 | `642d17365e3f5d40baf90450800da5b626735cec5e1ef92a51e5ffc0334ecf2e` |

## Правило доступа следующего агента

1. Сначала искать эквивалент **по SHA-256**, а не только по имени. Если точная копия есть в Git, фиксировать `PRESENT_GIT_EXACT`; если есть только вложенные распакованные документы, фиксировать `EXTRACTED_CONTENT_PRESENT / ORIGINAL_ZIP_NOT_MIRRORED`.
2. Для исходных ZIP N0-01–N0-07 не говорить «исследования отсутствуют»: отчёты, часть исходников и экспериментов уже доступны в `research/`. Для точного повтора нужны оригинальные байты архива или verified extracted source; отдельные APK не являются обязательными для чтения математики.
3. Приватные чаты и память не переносить в Git автоматически. Для исследовательских исходников перед размещением проверить вложенные данные, лицензии и секреты; APK не считать доказательством успешного испытания.
4. Если требуются байты только приватного архива, писать `PRESENT_OWNER_ARCHIVE_ONLY` с конкретным путём и хешем, **не** `DOES_NOT_EXIST`.
5. Этот реестр не доказывает 41/41 byte-availability в Git. Устранение этого остатка — отдельная задача передачи, без стирания исторических версий.
