# MiniScheme Applications & Market Ecosystem

This repository hosts official applications, shared component libraries, and build tools for the MiniScheme desktop info card ecosystem.

## Documentation for Developers & AI Agents
- 📖 **[Application Development Guide](docs/APP_DEVELOPMENT_GUIDE.md)**: Step-by-step instructions for creating new apps.
- 🔗 **[Firmware API Specification](../../minischeme-esp32/docs/api/README.md)**: Full runtime reference for hardware, graphics, and system calls.
- 🔗 **[Standard App Library (applib)](../../minischeme-esp32/docs/api/applib.md)**: Common widgets, cards, and formatting utilities.

## Bundled Applications
| App ID | Name | Description |
| :--- | :--- | :--- |
| `calendar` | 万年历 (Calendar) | Default desktop clock with lunar calendar and weather indicators |
| `weather` | 实时天气 (Weather) | Multi-day meteorological forecasts and environmental indices |
| `stocks` | 股票行情 (Stocks) | Real-time equity market tracker and candlestick trend charts |
| `crypto` | 加密货币 (Crypto) | Cryptocurrency market depth and price tickers |
| `futures` | 期货行情 (Futures) | Commodity futures tracking |
| `news` | 简讯热点 (News) | Multi-channel news summaries and headlines |
| `notifier` | 消息中心 (Notifier) | Push notification receiver and history viewer |
| `memo` | 便签备忘 (Memo) | Notes, to-do lists, and reminders |
| `album` | 电子相册 (Album) | Bitmapped photo gallery display |
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
An app's own server may have an app service password (`proxy_url_password`, edited on the
configuration pages next to the address; apps cannot read it): with one, the device registers an
encrypted channel there; without one it uses plain HTTP with the device id in the
`X-MiniScheme-Device` header, or (`proxy_url_relay = 1`) goes through the system converter.
See applib.md in minischeme-esp32.

Defaults that look like credentials (keys named like token/key/password, long tokens, private
addresses) are packaged empty by the build. Market data shown by the apps comes from the proxy
and is real: when a source fails the app keeps its last data (no demo values).

## Building Applications to MSBC Bytecode
```bash
python tools/build_apps.py [--system-fonts] [--sync] [app ...]
```
This compiles each Scheme app into an MSBC binary package with embedded metadata and font ROM dependencies.
All outputs stay inside this repository: `dist/` (images, all-in-one sources, `index.json`,
`app_default_msbc.h`, `app_settings_msbc.h`), the copies in `apps/`, and the root `index.json`.

The build checks each app's API requirement: it fails when the code needs a newer API than
`meta.ini` declares or than the firmware provides (`tools/api`, now API 1.6.0), or uses an
extension not declared there.

A combined app (`apps/<id>/meta.ini` with `[combo] members = a, b`) is assembled from its
members' code (`apps/lib/combo.scm`); each member's `[app] page_ids` names its pages.

`--sync` (off by default) additionally copies the results into the sibling checkouts when they exist:
`../minischeme-esp32/main/app_*_msbc.h` (embedded calendar and settings), and the images, all-in-one
sources, `index.json` and app sources into `../minischeme-webrepl/apps/` and `../minischeme-proxy/apps/`.
Use it when those repositories are to be released with the new apps.

## License
MIT License
