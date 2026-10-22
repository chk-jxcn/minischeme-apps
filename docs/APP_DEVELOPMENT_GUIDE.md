# MiniScheme Application Development Guide for AI Agents & Developers

This guide provides complete instructions for AI agents and developers to build new applications for the MiniScheme platform.

---

## 1. Quick Reference to Firmware API Documentation

When designing new apps, refer directly to the official API documentation maintained in the `minischeme-esp32` project:
- **[Core API Overview](../../minischeme-esp32/docs/api/README.md)**: Entry point for the MiniScheme runtime and primitive library, versioning and the API history.
- **[Application Library (applib.scm)](../../minischeme-esp32/docs/api/applib.md)**: The app framework: pages, the items model, settings, header, carousel, combined apps.
- **[Full API Specification v1.7.0](../../minischeme-esp32/docs/api/v1.7.0.md)**: Exhaustive reference of every Scheme primitive (graphics, hardware, networking, JSON feed, math, storage).

The current device API is **1.7.0** (firmware 1.0.66+): 1.7.0 added scheduled launches (an app's
`schedule.ini` lists times; `(app-scheduled)`, `(app-return)` and the `app-schedule` hook) and
`(gui-text-scaled x y str color scale [font-id])` for large text; 1.6.0 added `(config-get key app-id)` and
`(app-has-config? app-id)` for combined apps. `tools/build_apps.py` finds the API version an
app's code needs and writes `api = ` into its meta.ini; the firmware refuses an app that needs
a newer API than it has.

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
version = 1
pages = 1
page_ids = front ; English page names, one per page: <app>.<id> in a combined app
storage_kb = 64

[config]
; service endpoints: empty = the system config.ini values ([app] proxy / https_proxy)
proxy_url =
converter_url =
; custom app configuration keys
refresh_interval = 60
```

### 2.2 Combined apps (合集)

An app whose meta.ini has `[combo] members = weather, calendar, ...` is assembled by the
build from the members' code (`apps/lib/combo.scm`); its `entries` setting picks the pages
(`calendar.month`, `weather.front`, `wxpusher.news[0]`). Give every app `page_ids` so its pages
can be named, and keep an app's settings in its own `config.ini`: in a combined app each
member reads its own file through `(config-get key app-id)`. See "Combined apps" in
[applib.md](../../minischeme-esp32/docs/api/applib.md).

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

## 4. Testing without a board

`tools/sim.py` in minischeme-webrepl runs the WebREPL simulator (the firmware's C runtime in
WASM, the local proxy) headless from the command line:

```bash
cd ../minischeme-webrepl
python tools/sim.py --app ../minischeme-apps/apps/myapp.msbc --wait 5 --shot page1.png --press short --wait 2 --shot page2.png
python tools/sim.py --app ../minischeme-apps/apps/myapp/myapp.allinone.scm --log    # source, compiled in the page
python tools/sim.py --eval "(config-get \"proxy\")"
```

## 5. Best Practices for AI Agents

1. **Memory Budget**:
   - The total Scheme VM heap on ESP32 is typically **101 KB** (firmware 1.0.64), with a **4 KB Eden** young generation.
   - Live objects must stay below **60 KB** (60% of heap) to avoid frequent full GC pauses.
   - Use `(json-feed-start url interval keys types)` instead of holding huge JSON responses in RAM.
2. **Band Rendering Contract**:
   - The screen is rendered in horizontal slices (e.g., 20 lines per slice).
   - Use `(gui-visible? y h)` to skip drawing elements that are outside the current band slice.
3. **External Services**:
   - Query configured proxy via `(config-get "proxy_url")` or `(config-get "converter_url")`.
   - Never hardcode IP addresses or API keys in Scheme code.
