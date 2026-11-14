# Owner authorization — 2026-11-06

Owner explicitly stated in the conversation: «Я разрешаю производственный код».

Decision: PRODUCTION_CODE_AUTHORIZED = TRUE, effective for UNO production source development on a separate feature branch. This supersedes the earlier prohibition on writing production code only. It does NOT by itself establish OWNER_APPROVED_PRECODE, settle O01–O08, authorize model training, merge to main, GitHub Actions, releases, deletion, or force-push. Existing R5.3 source package remains immutable.

Implementation starts with a small non-neural control primitive whose behavior is directly constrained by ASTRA_01 S2/S3 event priorities and out-of-band STOP. This does not claim to implement Android authority, full F, or a trained organism.
