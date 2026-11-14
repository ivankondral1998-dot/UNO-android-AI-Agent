# Permanent channel v2 — interface, icon, empty journal, S4/S5 oracle

Source continues `feat/uno-permanent-full-foundation-20261111`. Fast-forward includes S4/S5 numerical oracle `b80b7c5` (`UnoFReference`, host `UNO_F_REFERENCE_HOST_PASS=10`). That oracle is not a trained model.

This change:
- launcher icon `res/mipmap-anydpi-v26/ic_launcher.xml` (dark field, amber ring);
- home screen: mark, memory, offline chat, the existing one-tap check, copy, STOP, honest list of checks that must not be faked;
- empty outcome journal schema is created on startup. No ticket is inserted. A later read-only diagnostic may report the journal as readable with total 0. That is not an Android action;
- exact memory, private marker, owner credential, native dispatch and neural quality stay incomplete until a real fact, a manual marker, a manual confirmation, an authorized port, or a trained model exists.

Host preflight on this tree before the versionCode 2 APK: `UNO_WP01_HOST_PASS=346` and `UNO_LAB_PREFLIGHT_SUCCESS`. Signing key was not rotated. `main` was not changed.

Built APK, code `f30d8832ce53de03262a8362266fbe590b1bcff8`: package `org.unovyra.uno`, versionCode 2, versionName `0.1.0-lab.2`, SHA-256 `e16ebeafafb4d127a0dbeb7b88ea3957fa839194744b7e9163e77105e2cf5167`, same signer as versionCode 1 (`58c92aec4b4ffe2dda8e1cb481e0216b2f51f3aabe4470b919036e7abdb99f51`). Gradle `assembleDebug` and `lintDebug`: `BUILD SUCCESSFUL in 1m 4s`. The owner-channel receipt records `previous_version_code=1`. Phone install of version 2 is not done.
