# MiniScheme Application Development Guide for AI Agents & Developers

This guide provides complete instructions for AI agents and developers to build new applications for the MiniScheme platform.

---

## 1. Quick Reference to Firmware API Documentation

When designing new apps, refer directly to the official API documentation maintained in the `minischeme-esp32` project:
- **[Core API Overview](../docs/api/README.md)**: Entry point for the MiniScheme runtime and primitive library.
- **[Application Library (applib.scm)](../docs/api/applib.md)**: Standard GUI helpers, cards, status bars, and formatted data components.
- **[Full API Specification v1.5.0](../docs/api/v1.5.0.md)**: Exhaustive reference of every Scheme primitive (graphics, hardware, networking, JSON feed, math, storage).

---

## 2. Anatomy of a MiniScheme App

Every app resides in its own directory under `apps/<app_id>/`:
```
apps/<app_id>/
├── meta.ini          # Application metadata and default settings
├── <app_id>.scm      # Main Scheme source code
└── web.html          # (Optional) Companion HTML web page served at /app
```

### 2.1 The `meta.ini` Specification
```ini
[app]
id = myapp
name = 我的应用
description = A sample application for MiniScheme
version = 1.0.0
pages = 1
storage_kb = 64

[config]
; service endpoints: empty = the system config.ini values ([app] proxy / https_proxy)
proxy_url =
converter_url =
; custom app configuration keys
refresh_interval = 60
```

---

## 3. Application Lifecycle Hooks

The MiniScheme device runtime calls global Scheme procedures defined by the app:

| Hook | Arguments | Description |
| :--- | :--- | :--- |
| `app-init` | `()` | Called once when the app is launched. Initialize state, fonts, and network feeds here. |
| `app-tick` | `(hm sec week date lux bl tick lunar)` | Called every second (1 Hz). `hm` is `"14:30"`, `sec` is `":25"`, `lux` is ambient light. If unsynchronized, `hm` is `"--:--"`. |
| `app-render` | `()` | Pure band-rendering callback. Called once per band slice. Never allocate heavy objects in render. |
| `app-button` | `(type)` | Button press event: `'short`, `'long`, `'mid`. |
| `app-touch` | `(x y)` | Touch screen tap coordinates. |
| `app-web` | `(action payload)` | Receives POST/GET requests from the companion web page `/app`. |

---

## 4. Best Practices for AI Agents

1. **Memory Budget**:
   - The total Scheme VM heap on ESP32 is typically **102 KB**, with a **4 KB Eden** young generation.
   - Live objects must stay below **60 KB** (60% of heap) to avoid frequent full GC pauses.
   - Use `(json-feed-start url interval keys types)` instead of holding huge JSON responses in RAM.
2. **Band Rendering Contract**:
   - The screen is rendered in horizontal slices (e.g., 20 lines per slice).
   - Use `(gui-visible? y h)` to skip drawing elements that are outside the current band slice.
3. **External Services**:
   - Query configured proxy via `(config-get "proxy_url")` or `(config-get "converter_url")`.
   - Never hardcode IP addresses or API keys in Scheme code.
