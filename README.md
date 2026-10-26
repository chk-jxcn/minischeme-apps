# MiniScheme Applications & Market Ecosystem

This repository hosts official applications, shared component libraries, and build tools for the MiniScheme desktop info card ecosystem.

## Documentation for Developers & AI Agents
- 📖 **[Application Development Guide](docs/APP_DEVELOPMENT_GUIDE.md)**: the complete workflow (language, layout, colors, fonts, servers, buttons, web pages, simulator, board debugging, memory analysis, tests, pull requests). Start here.
- 🧩 **[App template](docs/app-template/hello)**: a working two-page app to copy.
- 🔧 **`tools/board.py`**: install, run, screenshot and watch the memory of an app on a real board.
- 🔗 **[Firmware API Specification](https://github.com/chk-jxcn/minischeme-esp32/blob/main/docs/api/README.md)**: Full runtime reference for hardware, graphics, and system calls.
- 🔗 **[Standard App Library (applib)](docs/applib.md)**: The app framework: pages, the items model, helpers, web pages, the sandbox.

## Bundled Applications
| App ID | Name | Description |
| :--- | :--- | :--- |
| `calendar` | 万年历 (Calendar) | Default desktop clock with lunar calendar and weather indicators |
| `weather` | 实时天气 (Weather) | Multi-day meteorological forecasts and environmental indices |
| `stocks` | 股票行情 (Stocks) | Real-time equity market tracker and candlestick trend charts |
| `crypto` | 加密货币 (Crypto) | Cryptocurrency market depth and price tickers |
| `futures` | 期货行情 (Futures) | Commodity futures tracking |
| `news` | 热点新闻 (News) | Baidu's realtime, livelihood, finance and sports hot lists and the Zhihu or Toutiao hot list, live from the app proxy |
| `bilibili` | B站热门视频 (Bilibili) | Several Bilibili lists at once (popular, weekly, must-watch, rankings by partition, an UP主's newest videos), each with its own count, screens and seconds per screen, edited on the app's web page; screens turn by themselves through one list or all of them (a mid press stops / starts); covers downloaded with fs-download into one LRU cache; needs API 1.11 |
| `notifier` | 消息中心 (Notifier) | Push notification receiver and history viewer |
| `memo` | 便签备忘 (Memo) | Notes, to-do lists, and reminders |
| `album` | 电子相册 (Album) | Bitmapped photo gallery display |
| `tide` | 潮汐 (Tide) | Today's tide curve, height and highs/lows from the app proxy's /app/tide (Open-Meteo model), the built-in Haikou table offline |
| `medicine` | 吃药提醒 (Medicine) | Medicine reminders started by the system at set times (schedule.ini): photo, name, quantity, a press per medicine, then back to the previous app; needs API 1.7 |
| `pcmonitor` | 电脑监控 (PC Monitor) | CPU/GPU load, temperature, and RAM telemetry dashboard |
| `usage` | AI 用量 (Usage) | LLM token usage and quota tracker |
| `wxpusher` | 微信推送 (WxPusher) | WeChat notification bridge |
| `combo` | 合集 (Combined) | Pages of several apps (weather, calendar, wxpusher, stocks) in one carousel; needs API 1.6 |
| `settings` | 系统设置 (Settings) | Device configuration, WiFi management, and app launcher |

## App Configuration
An app's `meta.ini` `[config]` holds the defaults of its settings (the device copies them into the
app's own `config.ini` on first start). A key left **empty** takes the system `config.ini` value,
so the service addresses and the page carousel are empty by default and follow the system settings:
```ini
[config]
proxy_url =          ; empty: config.ini [app] proxy
converter_url =      ; empty: config.ini [app] https_proxy
carousel =           ; empty: config.ini [app] carousel
carousel_seconds =   ; empty: config.ini [app] carousel_seconds
```
The device talks to app servers over plain HTTP. Every request carries the device id in the
`X-MiniScheme-Device` header and, when the server has an app service password
(`proxy_url_password`, edited on the configuration pages next to the address; apps cannot read
it), the password base64-encoded in `X-MiniScheme-Password`: the server registers the device at
its first request and refuses another password later. Without a password an app's own server
may be reached through the system converter instead (`proxy_url_relay = 1`).

Defaults that look like credentials (keys named like token/key/password, long tokens, private
addresses) are packaged empty by the build. Market data shown by the apps comes from the proxy
and is real: when a source fails the app keeps its last data (no demo values).

## Building Applications to MSBC Bytecode
```bash
python tools/build_apps.py [--system-fonts] [--sync] [--msbc1] [app ...]
```
This compiles each Scheme app into an MSBC binary package with embedded metadata and font ROM dependencies.
Images are MSBC version 2 (each symbol name once, in a table: about a quarter smaller), which needs
firmware API 1.9; `--msbc1` writes version 1 for older firmware. `python tools/msbc_stats.py <image>`
shows where an image's bytes go.
All outputs stay inside this repository: `dist/` (images, all-in-one sources, `index.json`,
`app_default_msbc.h`, `app_settings_msbc.h`), the copies in `apps/`, and the root `index.json`.

The build checks each app's API requirement: it fails when the code needs a newer API than
`meta.ini` declares or than the firmware provides (`tools/api`, now API 1.13.0), or uses an
extension not declared there.

A combined app (`apps/<id>/meta.ini` with `[combo] members = a, b`) is assembled from its
members' code (`apps/lib/combo.scm`); each member's `[app] page_ids` names its pages.

`--sync` (off by default) additionally copies the results into the sibling checkouts when they exist:
`../minischeme-esp32/main/app_*_msbc.h` (embedded calendar and settings), and the images, all-in-one
sources, `index.json`, `api.json`, the library versions (`dist/lib/`) and app sources into the
git-ignored `../minischeme-webrepl/apps/` (a local WebREPL server lists them as 本地编译 and its
editor uses them) and `../minischeme-proxy/apps/`. The published WebREPL and the public market
take the newest release from GitHub by themselves.

The app library is versioned (`(define applib-version "MAJOR.MINOR")` in `apps/lib/applib.scm`;
compatible changes raise MINOR, incompatible ones MAJOR) and each app declares the version it
needs (`applib = 1.0` in meta.ini). Every build writes `dist/lib/<version>/` (the library files
and `api.json`, its documented definitions) and `dist/lib/index.json` (every version kept), and
`dist/api.json` (the firmware API reference, from `tools/api/`), for the WebREPL's editor.

## License
MIT License
