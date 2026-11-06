# First actual FR vs TR message-writing training — 2026-11-06

Owner explicitly authorized this limited training in docs/decisions/2026-11-06_OWNER_AUTHORIZED_LIMITED_MESSAGE_TRAINING.md.

Both models trained on 288 synthetic Russian request/reply pairs, 320 steps each, 16 examples/step, CPU PyTorch. Held-out 32 prompts deliberately used unseen names and an unseen instruction template. No third-party datasets or pretrained weights.

FR: 428,790 trainable float parameters; low-rank feed-forward operator plus shared GRU. TR: 539,382 trainable float parameters; straight-through ternary feed-forward operator plus shared GRU. Not parameter-matched exactly (difference 25.8%); same training steps do not guarantee same FLOPs or energy. The TR saved checkpoint holds float latent weights, not packed ternary weights. Neither checkpoint is deployed as optimized INT8 Android inference.

Results: FR 0/32 exact-match; TR 0/32 exact-match. Example prompt 'Мне нужно: поблагодари Лена.' Expected 'Спасибо за помощь, Лена!'; FR returned 'Спасибо за помощь, Нина!'; TR returned 'Спасибо за помощь, Мария!'. Both failed to copy unseen recipient. No evidence of open-ended Russian language competence. Training accuracy, confidence intervals, task-quality per joule and device measurements are absent.

Reproducible code, checkpoints, metrics are bundled in the conversation artifact UNO_MESSAGE_WEIGHTS_FR_TR_TRAINED_20261106.zip (SHA256 d358b6d7f79368418aeb545af1019e8361d27b915556c68ac4035cc28f51d273). Archive is not committed to GitHub. Next experiment should introduce a character copy/attention mechanism or explicit pointer, stronger baselines, held-out combinations and equal MAC budget before concluding anything about FR vs TR.

Status: HOST_TRAINED and HOST_EVALUATED only. No Android build, no A52 energy measurement, no full UNO organism.
