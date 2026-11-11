# Permanent channel v2 — interface, icon, empty journal, S4/S5 oracle

Source continues `feat/uno-permanent-full-foundation-20261111`. Fast-forward includes S4/S5 numerical oracle `b80b7c5` (`UnoFReference`, host `UNO_F_REFERENCE_HOST_PASS=10`). That oracle is not a trained model.

This change:
- launcher icon `res/mipmap-anydpi-v26/ic_launcher.xml` (dark field, amber ring);
- home screen: mark, memory, offline chat, the existing one-tap check, copy, STOP, honest list of checks that must not be faked;
- empty outcome journal schema is created on startup. No ticket is inserted. A later read-only diagnostic may report the journal as readable with total 0. That is not an Android action;
- exact memory, private marker, owner credential, native dispatch and neural quality stay incomplete until a real fact, a manual marker, a manual confirmation, an authorized port, or a trained model exists.

Host preflight on this tree before the versionCode 2 APK: `UNO_WP01_HOST_PASS=346` and `UNO_LAB_PREFLIGHT_SUCCESS`. Signing key was not rotated. `main` was not changed. Device install of versionCode 2 is not claimed here.
