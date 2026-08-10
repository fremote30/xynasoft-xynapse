# XynaFaith Mobile Services

---

## Purpose

This folder contains the abstraction layer between the XynaFaith application and the native mobile platform.

Application pages should never communicate directly with Capacitor plugins.

Instead, they should communicate with these services.

This allows the application to run in:

- Web browsers
- Android
- iOS

without changing business logic.

---

## Services

app.js

Application initialization.

platform.js

Platform detection.

storage.js

Secure storage.

device.js

Device information.

network.js

Connectivity monitoring.

camera.js

Camera integration.

share.js

Native sharing.

notifications.js

Push notifications.

biometrics.js

Face ID / Touch ID / Fingerprint authentication.