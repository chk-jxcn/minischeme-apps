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
| `settings` | 系统设置 (Settings) | Device configuration, WiFi management, and app launcher |

## App Configuration
Every application includes proxy and protocol converter configuration options in its `meta.ini`:
```ini
[config]
proxy_url = http://proxy.local:8087
converter_url = http://converter.local:8087
```

## Building Applications to MSBC Bytecode
```bash
python tools/build_apps.py
```
This compiles each Scheme app into an MSBC binary package with embedded metadata and font ROM dependencies.

## License
MIT License
