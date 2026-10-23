# MiniScheme App Development Guide

A complete, step-by-step guide for developers and AI agents (including small models) who write
apps for the MiniScheme desk display: a 320x480 ESP32 board that runs apps written in a small
Scheme. Follow the steps in order the first time; later, use the checklists and tables.

Contents

1. [Rules that matter most](#1-rules-that-matter-most)
2. [The system in one page](#2-the-system-in-one-page)
3. [File layout](#3-file-layout)
4. [Workflow: from idea to pull request](#4-workflow-from-idea-to-pull-request)
5. [The language](#5-the-language)
6. [The app framework (applib)](#6-the-app-framework-applib)
7. [Screen layout and limits](#7-screen-layout-and-limits)
8. [Colors](#8-colors)
9. [Fonts and text](#9-fonts-and-text)
10. [Buttons and scheduled launches](#10-buttons-and-scheduled-launches)
11. [Talking to servers](#11-talking-to-servers)
12. [Settings and storage](#12-settings-and-storage)
13. [The app's web page](#13-the-apps-web-page)
14. [Testing in the simulator](#14-testing-in-the-simulator)
15. [Testing and debugging on a real board](#15-testing-and-debugging-on-a-real-board)
16. [Memory: budgets, leaks and garbage](#16-memory-budgets-leaks-and-garbage)
17. [Automated tests](#17-automated-tests)
18. [Pull requests](#18-pull-requests)
19. [Release and deployment (maintainers)](#19-release-and-deployment-maintainers)
20. [Troubleshooting](#20-troubleshooting)
21. [References and keeping this guide current](#21-references-and-keeping-this-guide-current)

---

## 1. Rules that matter most

Read these before writing any code. Most failed apps broke one of them.

1. **English in code.** Identifiers, comments, commit messages, log and error messages are
   English. Chinese is fine only inside string literals the user sees (`"潮汐"`) and in
   `meta.ini` `name` / `description` / `[fields]` labels.
2. **Prefix every global name** with the app id (`tide-`, `hello-`). All files (gui.scm,
   infopages.scm, applib.scm, your app) share one global namespace. Never redefine an applib,
   gui.scm or `info-*` name.
3. **Render procedures only draw.** No file reads, no fetches, no settings reads, no state
   changes, and as little allocation as possible. Build lists, vectors and strings when the
   data changes and keep them in globals; the render reads them. (See [section 16](#16-memory-budgets-leaks-and-garbage).)
4. **Never block.** No loops that wait, no `http-get` (it is not even implemented). Data comes
   from the JSON feed in the background; time comes from the ticks.
5. **One JSON feed stream** exists for the whole app. applib owns it; if you start your own
   request, give it back (see [11.6](#116-a-one-off-request-the-medicine-sync-pattern)).
6. **Use only documented procedures.** The device has no R7RS library: no `do`, quasiquote,
   `sort`, `even?`, hash tables, `guard`... ([section 5](#5-the-language)). Check unfamiliar
   procedures in the simulator with `--eval` before using them.
7. **Strings are bytes.** `string-length` of `"中"` is 3. Cut text with the `txt-fit` /
   `txt-wrap` helpers, never with `substring` at arbitrary positions.
8. **Theme colors only** for the interface (`theme-text-main`, `theme-accent`...): never fixed
   RGB values for text, backgrounds or lines ([section 8](#8-colors)).
9. **No embedded fonts.** Load fonts with `'system` and fall back to `F-TEXT`
   ([section 9](#9-fonts-and-text)). Embedded fonts make the image large; for the rest of
   keeping an app small (fewer tiny functions, shared literals) see [16.7](#167-keeping-the-image-small).
10. **Measure memory** in the simulator and on a board before you open a pull request
    ([section 16](#16-memory-budgets-leaks-and-garbage)). "It works" is not enough: the tide app
    worked and still allocated kilobytes per second for nothing.
11. **Contributors open pull requests; they do not tag, release or deploy.** The maintainer does
    that ([section 19](#19-release-and-deployment-maintainers)).
12. **Secrets never go into code, commits, logs or URLs printed to the screen.** Board
    passwords and tokens are passed through environment variables.

---

## 2. The system in one page

```
   ┌──────────────────────┐   build_apps.py    ┌───────────────────────────┐
   │ minischeme-apps      │ ─────────────────► │ apps/<id>.msbc (bytecode  │
   │ apps/<id>/<id>.scm   │  compile_to_hex     │ + gzipped web.html + meta)│
   │ apps/<id>/meta.ini   │                    └─────────────┬─────────────┘
   │ apps/<id>/web.html   │                                  │ market / upload
   └──────────────────────┘                                  ▼
   ┌──────────────────────┐   GET /app/<name>  ┌───────────────────────────┐
   │ minischeme-proxy     │ ◄───────────────── │ ESP32 board (firmware     │
   │ app server: turns    │  {"items":[...]}   │ minischeme-esp32): VM,    │
   │ web APIs into small  │ ─────────────────► │ JSON feed, LCD, button,   │
   │ "items" documents    │                    │ HTTP API on port 80       │
   └──────────────────────┘                    └───────────────────────────┘
   ┌──────────────────────────────────────────────────────────────────────┐
   │ minischeme-webrepl: the same C runtime compiled to WASM (simulator),  │
   │ a copy of the proxy, tools/sim.py (headless simulator for scripts)    │
   └──────────────────────────────────────────────────────────────────────┘
```

| Repository (github.com/chk-jxcn/…) | What it holds | You change it when |
|---|---|---|
| `minischeme-apps` | Apps, the shared app libraries (`apps/lib`), the build, this guide | Always |
| `minischeme-proxy` | The app server (`/app/<name>` endpoints, market, admin) | The app needs new server data |
| `minischeme-webrepl` | WebREPL, the WASM simulator, `tools/sim.py`, a copy of the proxy | Rarely (simulator bugs, proxy copy) |
| `minischeme-esp32` | Firmware, the API reference (`docs/api`) | Never as an app developer |
| `minischeme` | The VM core and the compiler | Never as an app developer |

Check out all five side by side (`repos/minischeme-apps`, `repos/minischeme-webrepl`, ...):
the tools find each other through relative paths.

How an app runs on the board:

- The image is built into a Flash "App ROM" slot and executed in place (bytecode, constants and
  string literals cost no RAM). Only data created at run time lives in the VM heap.
- The firmware calls hooks: `app-tick` every second, `app-step` every main-loop pass,
  `app-button` / `app-long-press` / `app-mid-press` on the key, `gui-render-proc` when rows of
  the screen must be redrawn, `app-web` for calls from the app's web page.
- An app that raises 10 errors in 10 s, fails 3 renders in a row or runs out of memory is
  stopped: the board shows the error and restarts into the system settings.

---

## 3. File layout

```
minischeme-apps/
├── apps/
│   ├── <id>/                 one folder per app (sources; the build adds <id>.msbc etc.)
│   │   ├── <id>.scm          the program
│   │   ├── meta.ini          metadata, settings form, default settings
│   │   └── web.html          optional: the app's page in the device web UI
│   ├── lib/                  shared code put in front of every app
│   │   ├── gui.scm           colors (theme-*), drawing helpers
│   │   ├── infopages.scm     the hardware pages (8 s hold)
│   │   ├── applib.scm        the framework: pages, feed, header, footer, carousel
│   │   ├── appweb.scm/.js/.css  web page helpers (only for apps with web.html)
│   │   └── combo.scm         combined apps (合集)
│   ├── <id>.msbc, <id>.allinone.scm, index.json    build outputs (CI commits them)
├── dist/                     the same outputs plus app_default_msbc.h, app_settings_msbc.h
├── docs/
│   ├── APP_DEVELOPMENT_GUIDE.md   this guide
│   └── app-template/hello/        a working two-page app to copy
├── tests/test_apps.py        checks of all apps and images (CI runs it)
└── tools/
    ├── build_apps.py         the build (APPS table: register new apps here)
    ├── board.py              develop on a real board (install, exec, screenshot, memory)
    ├── msbc_stats.py         where an app image's bytes go (16.7)
    ├── api/                  the firmware API tables the build checks against
    └── compile_to_hex(.exe)  the compiler (built from ../minischeme when missing)
```

On the board an app lives in `/spiffs/apps/<id>/`: `app.msbc`, its `config.ini` (made from
`[config]` at first start) and its own data files.

---

## 4. Workflow: from idea to pull request

Every app goes through the same steps. Do not skip the measuring steps.

### Step 1. Prepare the tools (once)

```bash
# Python 3.10+; pillow for screenshots; pyserial for the serial log; Edge/Chrome/Chromium for sim.py
pip install pillow pyserial pytest
git clone https://github.com/chk-jxcn/minischeme-apps
git clone https://github.com/chk-jxcn/minischeme-webrepl
git clone https://github.com/chk-jxcn/minischeme-proxy        # only when you add an endpoint
cd minischeme-apps && python tools/build_apps.py calendar     # builds the compiler on first use (gcc)
```

On Windows `tools/compile_to_hex.exe` is in the repository; elsewhere the build compiles it
with `gcc` (set `CC` to use another compiler).

### Step 2. Design on paper

Write down, before coding:

- the pages (2-4 is typical) and what each shows, sketched on a 320x480 grid ([section 7](#7-screen-layout-and-limits));
- where every value comes from: the app server (which endpoint, which item types), the clock,
  local files, the web page;
- what the button does (short: next page by default; long / mid: yours);
- the settings (`[config]` keys) and their defaults;
- the memory plan: what is kept in globals and how big it can get.

### Step 3. Create the app from the template

```bash
cp -r docs/app-template/hello apps/myapp
cd apps/myapp && mv hello.scm myapp.scm
# replace every "hello" with "myapp" (id, file names, the hello- prefix), and set name/description
```

Then register the id in `tools/build_apps.py` (the tuple of applib apps):

```python
for _app in ('weather', 'news', ..., 'tide', 'medicine', 'myapp'):
```

### Step 4. Build

```bash
python tools/build_apps.py myapp
```

The build prints `myapp: API 1.9 (N procedures)` and writes `apps/myapp.msbc` (MSBC version 2,
which needs API 1.9; `--msbc1` writes the old format for older firmware). It fails on
compile errors, on an `api` lower than the code needs, and warns about **reserved** (not
implemented) procedures: treat that warning as an error.

### Step 5. Run it in the simulator

```bash
cd ../minischeme-webrepl
python tools/sim.py --fresh --config app.carousel=0 --app ../minischeme-apps/apps/myapp.msbc \
    --wait 6 --shot p1.png --press short --wait 4 --shot p2.png --log
```

Look at every screenshot. Fix, rebuild, repeat. Details: [section 14](#14-testing-in-the-simulator).

### Step 6. Measure memory in the simulator

Run the probe in [16.4](#164-measuring-in-the-simulator). Live heap must stay flat over time;
allocation per idle second should be well under 1 KB.

### Step 7. Run it on a real board (if you have one)

```bash
python tools/build_apps.py myapp
MS_PASSWORD=... python tools/board.py 192.168.x.y install myapp --boot
python tools/board.py 192.168.x.y shot board.png
python tools/board.py 192.168.x.y mem 30        # 30 minutes: vm-live must not grow
```

Details: [section 15](#15-testing-and-debugging-on-a-real-board).

### Step 8. Tests

```bash
python -m unittest discover -s tests -v          # in minischeme-apps (CI runs the same)
```

Add an endpoint test in minischeme-proxy if you added an endpoint ([section 17](#17-automated-tests)).

### Step 9. Pull request

Branch, commit the sources (not the build outputs), push, open a PR ([section 18](#18-pull-requests)).

---

## 5. The language

MiniScheme is a small Scheme compiled to bytecode on the PC. It is **not** R7RS: many common
procedures do not exist on the device. The authoritative list is the API reference
(`minischeme-esp32/docs/api/v1.x.0.md`, "status" column: `stable` exists, `reserved` does not).
The table below was checked on the simulator (firmware API 1.8 / 1.9).

### 5.1 What exists

Procedures marked `reserved` in the API reference are documented but **not implemented**: the
build warns about them and calling one fails with "reserved API ... not provided by this
firmware". Several common names are reserved; the lists below give what really works.

| Area | Available |
|---|---|
| Syntax | `define`, `lambda`, `let`, `let*`, named `let`, `letrec`, internal `define`, `if`, `cond` (with `=>`), `case`, `and`, `or`, `when`, `unless`, `begin`, `set!`, `quote`, `define-syntax` + `syntax-rules`, `define-macro` |
| Lists | `cons car cdr cadr caddr cadddr cddr ... list length append reverse list-ref list-tail list-index memq memv member assq assv assoc map (several lists) for-each filter fold-left fold-right set-car! set-cdr! list? null? pair?` |
| Vectors | `vector make-vector vector-ref vector-set! vector-length vector->list list->vector vector-fill! vector?` |
| Numbers | `+ - * / = < > <= >= abs quotient remainder modulo min max expt sqrt exp log sin cos tan asin acos atan floor round truncate ceiling exact->inexact inexact->exact exact? inexact? integer? number? number->string (radix too) string->number`; big integers work |
| Strings | `string-append substring string-length string-ref string=? string<? string>? string->symbol symbol->string string->list list->string char->integer integer->char`, `string->ints` ("1,2,-3" → (1 2 -3)), `string->fixed` |
| Control | `apply` (short lists only, see below), `call/cc`, `error` |
| Other | `eq? eqv? equal? not boolean? symbol? string? procedure? void`, `time-ms`, `time-synced?` |

applib adds helpers (section 6): `str-split str-part str-empty? str-starts? str-contains?
url-encode pad2 fixed->str int->str clamp list-min list-max list-sum take`, and appweb (apps
with a web page) `web-join web-field web-json`.

### 5.2 What does not exist (write it yourself)

| Missing | Use instead |
|---|---|
| `do` | named `let`: `(let loop ((i 0)) (if (< i n) (begin ... (loop (+ i 1)))))` |
| quasiquote `` `(a ,b) `` | `(list 'a b)` |
| `let-values`, `values` receivers, `case-lambda`, `define-record-type` | lists or vectors with accessor procedures (see tide's `tide-v-*`) |
| `even? odd? zero? positive? negative?` | `(= (remainder n 2) 0)`, `(= n 0)`, `(> n 0)` |
| `sort`, `list-sort` | write an insertion sort for short lists |
| hash tables | association lists (`assoc`, `assq`) or vectors indexed by number |
| `guard`, `with-exception-handler`, `dynamic-wind`, `raise` | validate inputs; an error in a hook is caught by the firmware and counted |
| `string-split`, `string-prefix?`, `string-suffix?`, `string-trim`, `string-upcase`, `string-downcase`, `string-index`, `string-join`, `string-pad-left`, `url-decode`, `make-string`, `string-copy`, `string` | applib's `str-split`, `str-starts?`, `str-contains?`, `pad2`, `url-encode`; `list->string` |
| `json-parse`, `json-stringify`, `base64-encode`, `http-get`, `http-post`, `list-index` | data arrives as items (section 11); JSON answers of the web page through `web-json` |
| `char-upcase`, `char-alphabetic?` | compare byte values (`char->integer`) |
| `iota`, `last-pair`, `list-copy`, `delete`, `remove`, `filter-map` | short recursive helpers with the app's prefix |
| `random` | `(remainder (time-ms) n)` is enough for visual variety |
| `delay`/`force`, string ports, `1+` | not needed |

### 5.3 Behaviors that surprise

- **Strings are byte strings.** `(string-length "中")` is 3, `(string-ref "中" 0)` is 228,
  `(string->list "ab")` gives `(97 98)`. UTF-8 text survives as long as you do not cut it in the
  middle of a character.
- **No rationals.** `(/ 1 3)` is the float `0.333333`; `1/3` is not a number literal.
  `(inexact->exact 2.6)` rounds to 3; `(round 2.5)` is 3.
- **Floats allocate** (each one is a heap object); fixnums do not. In loops over many values
  prefer integer arithmetic (centimeters, tenths), and convert with `fixed->str` for display.
- **`apply` allocates its argument list from the small system heap** on the board: `(apply
  min long-list)` fails there with "out of memory allocating argument list" although it works
  in the simulator. Use `list-min`, `list-max`, `list-sum` or a loop.
- **`#\"`** (the double-quote character literal) is misread by the compiler: use `(integer->char 34)`.
- `eq?` on equal string literals may be `#t` (constants are shared): compare strings with
  `string=?` or `equal?`, never `eq?`, except when you deliberately check "the same object"
  (as tide does to see whether a new feed document arrived).
- `error` stops the current hook; there is no way to catch it in Scheme. The firmware logs it,
  and too many errors stop the app.

---

## 6. The app framework (applib)

Almost every app is built on applib. The full reference is
[applib.md](https://github.com/chk-jxcn/minischeme-esp32/blob/main/docs/api/applib.md); this is
what you need daily.

### 6.1 Declaring pages

```scheme
(app-define! "标题"
  (list (app-page "页名" url-proc interval-ms render-proc)   ; data from the app server
        (app-local-page "页名" render-proc)))                ; no fetch, render gets '()
```

- `url-proc`: `() -> "http://server/app/x?..."`, called **once** at `app-define!`. Use
  `(app-url "/app/x?...")`, which puts the configured server in front. To change a page's
  document while the app runs (a choice made in the web page): `(app-set-url! i url)`, which
  fetches at once when page `i` shows.
- Pages with the same URL share one document (tide's 3 pages use one).
- `interval-ms`: how often the page's data is fetched **while the page is shown**.
- `render-proc`: `(items) -> draws the body`. It is called with `'()` on local pages and on
  pages listed in `app-render-empty-pages` before their data arrives.
- Set `app-subtitle-proc`, `app-tick-proc`, `app-render-empty-pages`, `app-footer-text`
  **before** `app-define!`.
- Any applib app can become a member of a combined app (合集, `apps/combo`), which shows pages
  of several apps in one carousel. Keep that possible: name every page in `page_ids`, read
  settings only through `app-config` (each member reads its own file), keep all globals
  prefixed. See "Combined apps" in applib.md.

### 6.2 The items model

The server answers `{"items":[{"t":"now","a":"23","b":"晴"}, ...]}`. applib copies each item
into a vector `#(type a b c d e)`:

| Procedure | Gives |
|---|---|
| `(items-find items "now")` | the first item of type `"now"` (a **string** argument), or `#f` |
| `(items-all items "day")` | all items of that type |
| `(items-where items "day" 1 "周一")` | the first `"day"` item whose field 1 (`a`) is `"周一"` |
| `(it-t it)` | the type as a **symbol** (`'now`) |
| `(it-a it)` .. `(it-e it)` | the field text, `""` when missing |
| `(it-int it 2)`, `(it-fixed it 2 1)`, `(it-ints it 3)` | field 2 as an integer / fixed-point / integer list; `#f` or `'()` when not a number |

Every field is a string: compare with `string=?`, convert with `it-int`, and always provide a
fallback: `(or (it-int it 3) 0)`.

### 6.3 Hooks and variables you use

| Name | Use |
|---|---|
| `app-tick-proc` | `(lambda (tick) ...)` every second. Update live data, call `gui-invalidate` for the rows that changed. Runs while the info pages show: check `(info-active?)` before invalidating. |
| `app-data-proc` | `(lambda (items) ...)` when a new document arrives: the place to build derived data (parsed numbers, strings, vectors) **once**. |
| `app-subtitle-proc` | `(lambda (items) ...)` text after the title on page 1. |
| `app-footer-text` | the footer of local pages; set it when the data changes. |
| `app-time`, `app-date`, `app-week`, `app-lunar`, `app-utc-sec` | clock fields (`"--:--"` etc. before the clock is synced; `(time-synced?)`). |
| `(app-config "key" default)` | a setting (reads a file each call: read once, keep the value). |
| `(app-goto! i)`, `(app-next-page!)`, `app-page-index` | navigation. |
| `(app-invalidate-all)`, `(app-invalidate-body)` | redraw everything / the body. |
| `app-long-press`, `app-mid-press` | define them to use the long (0.8 s) and mid (3.5 s) presses. |

### 6.4 Lifecycle of one second

1. The firmware calls `app-tick`: applib updates the clock fields, invalidates the header when
   the minute changes and the footer every 2 s, runs the carousel, then your `app-tick-proc`.
2. Each main-loop pass calls `app-step`: a new feed document is copied into items, cached, given
   to `app-data-proc`, and the whole screen is invalidated.
3. At the next display service the renderer calls `gui-render-proc` (applib's `app-render`) for
   the dirty rows. applib draws header, body (your render procedure) and footer, each only if
   `gui-visible?`.

### 6.5 A list longer than one screen

The header shows the title, the subtitle (page 1) or the page's name (other pages), and on
pages 2.. applib's own badge `2/4`, which counts **applib pages**. A list that needs several
screens (20 videos, 5 per screen) is not several applib pages:

- Keep it on **one applib page** and turn its screens yourself: a global screen index, the
  short press (`app-button`) for the next screen, the long press (`app-long-press`) for the
  previous one, both wrapping around; then `(app-invalidate-all)`.
- Show the position **in the header**: `app-subtitle-proc` returns `"综合热门 2/4"`. Keep title
  and subtitle short enough to fit left of the clock (they scroll otherwise).
- Do not make each category (or each screen) an applib page as well: the user then sees two
  page numbers (applib's badge and yours), and the carousel jumps between categories before
  the user saw their later screens. A choice of what to show (a category, a region) is a
  setting and a control on the web page; switch with `(app-set-url! 0 url)`.
- The carousel turns applib pages only: with one page it does nothing. If the screens should
  turn by themselves, do it in `app-tick-proc` (every N seconds, N a setting, 0 = off) and
  restart the count after a key press.
- Pictures of the next screen can be downloaded while the user reads the current one; keep
  the ones already shown, so going back shows them at once (section 11.7).

---

## 7. Screen layout and limits

### 7.1 Geometry

```
y   0 ┌────────────────────────────────┐
      │ title  subtitle   [bar] 2/3 14:30 │  header: HDR-H = 32
   32 ├────────────────────────────────┤
   38 │ (body-top)                     │
      │  body: x 10 .. 310             │
  452 │ (body-bottom)                  │
  456 ├────────────────────────────────┤
      │ 更新于 14:30        2.1KB 180ms │  footer: FTR-H = 24
  480 └────────────────────────────────┘
```

- Portrait 320x480; use `(scr-w)` and `(gui-height)`, not literal numbers, where you can.
- Margins 10 px (content `x` 10..310). Two columns: `x = 10` and `x = 164`, width 146.
- Text rows: 16 px glyphs, 20..28 px pitch (`LINE-H` = 20). A section label:
  `(section y "标签")`, content about 24 px below.
- Lists: draw only what fits: stop when `y` passes `(body-bottom)`. Long text in list rows
  (titles, names): `gui-text-wrap` into a fixed number of lines, not `txt-fit` / `txt-wrap`
  (section 9: they may scroll). Keep every string inside the screen, the right margin
  included: measure with `txt-w`, and give a column the width that is left after the picture
  or number beside it.
- Empty state: one muted line, e.g. `(txt 14 70 "暂无数据" theme-text-muted)`.
- Charts: a `theme-card-hdr` filled rectangle, the chart on top (`line-chart`, `bar-chart`,
  `gui-chart`), axis labels `theme-text-muted`.

### 7.2 Rendering rules

- The board renders in **bands** of a few rows; your render procedure normally runs **once per
  frame**, its drawing recorded into a display list and replayed per band.
- The display list holds 128 commands statically and grows to 512 from the heap. Past that,
  Scheme runs **once per band** (dozens of times per frame): slow, and every allocation is
  multiplied. Keep a page under ~100 commands. Each `txt`, rectangle, line or circle is one
  command; prefer fewer, larger shapes.
- `gui-invalidate` works on **rows**: `(gui-invalidate 0 y (scr-w) h)` redraws rows `y..y+h-1`.
  Invalidate only what changed: a clock line every second, not the whole screen.
- Wrap expensive sections in `(if (gui-visible? y h) ...)` so partial redraws skip them.
- A render must be **deterministic**: the same state draws the same picture. It may run any
  number of times.

### 7.3 Visual style

- Values in `theme-text-main`, secondary text `theme-text-sub`, labels `theme-text-muted`,
  section titles and highlights `theme-accent`, warnings `theme-warning`.
- Cards are outlined, not filled: `(gui-round-rect x y w h 6 theme-card-border #f)`.
- Signed changes: `(rise-color v)` (red up, green down, the Chinese market convention).
- Keep text 16 px; use the big digit font for one or two hero numbers per page.
- Look at the existing apps (weather, tide, calendar) and keep the same look.

---

## 8. Colors

Colors are RGB565 integers resolved through **color schemes** (API 1.8): a day scheme (light)
and a night scheme (dark), switched automatically by the light sensor, fixed times or sunrise
and sunset (`config.ini [theme]`, the device page's 配色方案 tab). Users can change any color
there (each color in the preview opens a color picker) or in `theme.css` files.

- Use the theme variables for everything in the interface. They are set from their aliases at
  the start and again whenever the scheme changes, so code that draws with them follows day
  and night without any work:

| Variable | Alias | Use |
|---|---|---|
| `theme-bg` | `bg` | the canvas (applib clears with it); text on filled color boxes |
| `theme-card-hdr` | `titlebar_bg` | header / footer strip, chart backgrounds |
| `theme-card-border`, `theme-divider` | `card_border`, `divider_border` | outlines, rules, grid lines |
| `theme-text-main`, `theme-text-sub`, `theme-text-muted` | `text_fg`, `text_sub_fg`, `text_muted_fg` | values, secondary text, labels |
| `theme-accent`, `theme-accent-dark` | `accent_fg`, `accent_bg` | highlights; filled badges |
| `theme-success`, `theme-warning`, `theme-danger`, `theme-purple` | `success_fg` ... | status colors |
| `theme-dark-gray` | `inactive_fg` | inactive tracks |
| `theme-seg-on`, `theme-seg-off` | `seg_on_fg`, `seg_off_fg` | seven-segment digits (`gui-seg7`); by day the unlit segments are the background (not shown) |

- **Never keep a color in your own global at load time** (`(define myapp-bar (gui-rgb ...))`):
  it does not follow the scheme. Draw with `(theme-color "alias")` and give your own aliases
  defaults for both schemes at the top level:

  ```scheme
  (theme-defaults! "night" '(("myapp_bar_fg" . "#62d0f0")))
  (theme-defaults! "day"   '(("myapp_bar_fg" . "accent_fg")))   ; a value may name another alias
  ;; in render:
  (gui-rect x y w h (theme-color "myapp_bar_fg") #t)
  ```

  An alias nobody defines falls back to its category (`myapp_bar_fg` → `fg`), so even a
  forgotten default stays readable. Name aliases `<app>_<what>_<fg|bg|border>`.
- Make sure both schemes look right: test with `--config theme.theme=day` and
  `--config theme.theme=night` in the simulator (or the 配色方案 tab on a board).
- Fixed colors are acceptable only for **data** that has an inherent color (a photo, a weather
  icon's sun: give even those an alias with defaults, as the weather app does).
- The user can also change the display output (`color_bits`, `palette`: fewer colors, gray,
  a monochrome panel). Do not encode meaning in hue alone: also use position, text or shape.
- Full reference: applib.md section 4.8.

---

## 9. Fonts and text

| Font | How | Characters |
|---|---|---|
| `F-TEXT` (slot 2) | `txt`, `txt-fit`, `txt-wrap`, `txt-right`, `txt-center` | a 16 px CJK face from the font ROM (applib loads it) |
| `F-BIG` (font 1) | `big`, `big-right`, `big-w` | only `" %-./0123456789:AMP"` (32 px) |
| slots 3..6 | `(use-font 3 "simhei" 24 'system)` | whatever that face has; slot 2 is applib's, 7 the info pages' |

Rules:

- Always load extra faces with `'system` and handle failure, because the board's font ROM may
  contain only one face (often `simsun-16`):
  `(define myapp-font (if (use-font 3 "simhei" 24 'system) 3 F-TEXT))`.
- Do **not** embed fonts (a `use-font` without `'system`): the build then puts a font subset
  into the image, which makes it large, and text from the server may lack glyphs.
- Large text: `(gui-text-scaled x y str color scale font-id)` (API 1.7) scales any font by an
  integer factor; `F-BIG` at scale 2 gives 64 px digits.
- Width: `(txt-w s)`. One line that may be too long: `(txt-fit x y w s color)` (marquee or
  "…" as the user configured). A paragraph: `(txt-wrap x y w h s color)` (it scrolls when the
  user configured `wrap_marquee`).
- **Many long strings on one screen** (a list of titles): `txt-fit` and `txt-wrap` scroll
  (marquee) by default, and every scrolling box redraws its rows several times a second: a
  list of five scrolling titles allocates tens of KB of garbage per second (measure it, 16.4)
  and is hard to read, because each row shows half a sentence at any moment. Draw them with
  `(gui-text-wrap x y w h s color F-TEXT LINE-H)`: it wraps to as many lines as fit in `h` and
  ends cut text with "…", without animation. Keep `txt-fit` for one headline.
- **Which characters exist.** The system face is the font ROM's `simsun-16`: ASCII and
  **GB2312** exactly as Python's `gb2312` codec maps it (simplified Chinese, the common symbols
  and full-width punctuation, kana, Greek and Cyrillic), plus `·` (U+00B7) and `•` (U+2022)
  built into the firmware. Anything else (emoji, traditional or rare characters, many
  symbols) is drawn as a box. Not `gbk`: it accepts traditional characters the font lacks.
  Two common look-alikes have other code points in the font: the dash is `―` (U+2015, not
  `—` U+2014) and the middle dot is `·` (U+00B7, not `・` U+30FB, which the font lacks). Avoid
  rare symbols in your own strings (`"23 度"`, or `"23°"` only after you saw it render on a
  board).
- **Text from the web** (titles, names, comments) is full of characters the face lacks. Clean
  it **on the app server**, before it goes into the document:

  ```python
  BOARD_EXTRA = {"·", "•"}                  # built into the firmware
  BOARD_SAME = {"—": "―", "・": "·"}   # the font's code point for these

  def board_text(s: str) -> str:
      """Only characters the board's font has (ASCII, GB2312, BOARD_EXTRA); the others dropped."""
      out = []
      for ch in s:
          ch = BOARD_SAME.get(ch, ch)
          if " " <= ch <= "~" or ch in BOARD_EXTRA:
              out.append(ch)
              continue
          try:
              ch.encode("gb2312")
              out.append(ch)
          except UnicodeEncodeError:
              out.append(" ")
      return " ".join("".join(out).split())   # no runs of spaces
  ```

  Check a doubt against the font itself: `minischeme-webrepl/tools/make_font.py` has
  `decode_mfnt(data)`, which gives the code points of `fonts/simsun-16.mfnt`.

---

## 10. Buttons and scheduled launches

### 10.1 The key

| Gesture | Default time | Calls | applib default |
|---|---|---|---|
| short press | < 0.8 s | `app-button` | next page |
| long press | ≥ 0.8 s | `app-long-press` | none: define it |
| mid press | ≥ 3.5 s | `app-mid-press` | none: define it |
| hold | ≥ 8 s | (firmware) opens the hardware info pages | – |

On the info pages a short press turns their pages, a long press goes back to the app, a mid
press opens the system settings; the app's button hooks are not called then. The times are
`config.ini [system] button_long_ms / button_mid_ms / button_hold_ms`. `app-touch` exists only
in the simulator (screen click).

To replace the short press: `(set! app-button (lambda () ...))` after applib, or define
`app-button` in your file (it is looked up by name on each call).

### 10.2 Scheduled launches (API 1.7)

An app whose folder holds `schedule.ini` is started by the system at those times:

```ini
[schedule]
times = 08:00, 12:30, 19:00   ; local time
return_after = 0              ; seconds until the automatic return; 0: wait for (app-return)
persist = 1                   ; optional: resume this launch after a reboot or power cut
```

- Started at a scheduled time: `(app-scheduled)` returns `"08:00"`; when done, call
  `(app-return)` and the board goes back to the previous app.
- Already running at that time: the hook `(app-schedule at)` is called instead.
- The app writes `schedule.ini` itself (`fs-write`) or its web page does
  (`/api/app/file?name=schedule.ini`). The medicine app is the complete example.

---

## 11. Talking to servers

### 11.1 The only way: the JSON feed

The board fetches over **plain HTTP** in the background (`json-feed-start`); applib starts and
follows it for the page on screen. There is no TLS on the board (it would need 30-45 KB of RAM):
`https://` URLs go through the protocol converter (`[app] https_proxy`, else the app server's
`/fetch?url=...`).

The device adds two headers to every request to a server named in its configuration:

| Header | Value |
|---|---|
| `X-MiniScheme-Device` | the device id (its WiFi MAC, 12 uppercase hex digits) |
| `X-MiniScheme-Password` | base64 of the app service password set for that server (`<key>_password`), when there is one |

The server registers the device with that password at its first request and answers 403 to a
different one later. Base64 is not encryption: the user accepted that on a home network.

### 11.2 Which server

- `(app-url "/app/x?...")` = the app's `proxy_url` setting, or the system `[app] proxy` when it
  is empty (the normal case). Leave `proxy_url =` empty in `meta.ini`.
- The public app server is maintained with minischeme-proxy; the WebREPL's local server
  (`python server.py`) contains the same proxy, so the simulator has every endpoint.
- Never hardcode an address, a token or an API key. A third-party key belongs in a setting
  (`[config] key =` empty by default; the build blanks credential-like defaults).

### 11.3 The document format (what an endpoint must return)

- `{"items":[{...}, ...]}`, one **flat** object per item, keys `t` (required), `a`..`e`.
  Other keys and nested objects are ignored.
- Values are strings. Send `""` instead of `null` / booleans. No thousands separators.
- Small: about 4 KB of values and at most 64 items per document; values up to 255 bytes. Send
  only what the screen shows. Series as `"12,-3,7"` (integers: scale floats yourself).
- `{"t":"upd","a":"HH:MM"}`: the data time, shown in the footer.
- Failure: the **first** item `{"t":"error","a":"message"}`: the device keeps its old data and
  shows the message in the footer.

### 11.4 Adding an endpoint to the app server

In minischeme-proxy:

1. Write `proxy/<name>.py` with a function that returns the items (look at `proxy/tide.py`:
   `get_tide(place)` caches documents for 10 minutes and turns upstream failures into an error
   item).
2. Route it in `handle_app_query` in `proxy/endpoints.py`:

   ```python
   elif path == "/app/myapp":
       from .myapp import get_myapp
       data = get_myapp(qs.get("x", [""])[0])
   ```
3. Add `tests/test_<name>.py` that builds the items **without network** (feed synthetic upstream
   data, as `tests/test_tide.py` does) and checks types, sizes and the error path.
4. Copy the changed files into `minischeme-webrepl/proxy/` (the two copies are identical) so the
   simulator serves the endpoint; restart `server.py`.
5. Cache upstream answers (a few minutes at least) and set timeouts (≤ 6 s): many boards may
   ask at once.

Run it locally: `python server.py` in minischeme-webrepl (or `python app_proxy.py` in
minischeme-proxy) and open `http://127.0.0.1:8087/app/myapp?x=1` in a browser.

### 11.5 Your own server

An app may use its own server: the user sets the app's `proxy_url` (and optionally
`proxy_url_password`). The server must answer the items format over plain HTTP, should check
`X-MiniScheme-Device` / `X-MiniScheme-Password` if it keeps per-device data, and should keep the
URL short (under ~230 bytes).

### 11.6 A one-off request (the medicine sync pattern)

To send data to the server (uploads, sync), use the feed for one request and hand it back:

```scheme
(define myapp-job #f)                        ; a request in flight

(define (myapp-send! query)
  (set! myapp-job #t)
  (json-feed-start (string-append (app-proxy) "/app/myapp?" query)
                   3600000 '("t" "a" "b" "c" "d" "e") '((0 prefix "")) 4096 64 2))

;; The answer: read it, then give the feed back to applib's pages
(define (myapp-answer!)
  (set! app-last-seq (json-feed-seq))        ; applib must not take it as a page document
  (set! myapp-job #f)
  ;; (json-feed-count) items; (json-feed-field i 0) is t, 1..5 are a..e
  (app-start-feed!))

;; app-step: ours while a request runs, applib's otherwise
(define myapp-applib-step app-step)
(define (app-step)
  (if myapp-job
      (if (and (> (json-feed-seq) 0) (not (= (json-feed-seq) app-last-seq))) (myapp-answer!))
      (myapp-applib-step)))
```

- Keep the query in the URL (GET), under ~230 bytes; split bigger uploads into several requests.
- A request with no answer in 30 s has failed: stop it (`json-feed-stop`), give the feed back,
  retry later (medicine retries after 10 minutes). The app must work without the server.
- See `apps/medicine/medicine.scm` (`sync-start!`, `sync-step!`, `sync-failed!`) for a complete
  implementation with retries and upload queues.

### 11.7 Pictures from the network (API 1.10)

The board draws only **baseline JPEG files in the app's own folder** (`gui-image`). To show a
picture from the web (a cover, an avatar, a map):

1. **The app server prepares it.** Add an endpoint that fetches the original, makes it small and
   baseline, and answers with the JPEG bytes instead of a JSON document. `handle_app_query` may
   return `(status, content_type, body)` itself:

   ```python
   # proxy/endpoints.py, in handle_app_query: a picture, not a JSON document
   elif path == "/app/myapp/pic":
       from .myapp import picture
       return picture(qs.get("id", [""])[0])     # (200, "image/jpeg", jpeg) or (404, "text/plain", b"...")
   ```

   ```python
   # proxy/myapp.py: Pillow is in minischeme-proxy's requirements
   import io
   from PIL import Image

   def board_jpeg(raw: bytes, width: int, height: int) -> bytes:
       im = Image.open(io.BytesIO(raw)).convert("RGB")
       im.thumbnail((width, height))              # keeps the aspect ratio
       out = io.BytesIO()
       im.save(out, "JPEG", quality=70, progressive=False, optimize=True)
       return out.getvalue()
   ```

   - Make it exactly as big as the box it fills on screen (a 96 x 54 picture is 2-4 KB): the
     board decodes every pixel it gets.
   - Cache converted pictures (they rarely change), and accept only what the list document
     named (an id), never any URL: the endpoint must not become an open proxy.
   - Some sites refuse requests without a browser-like `User-Agent` or a `Referer`: send what
     they need, and write a test that converts a sample picture without network.
2. **The document names the pictures.** Each list item carries what the app needs to build the
   picture's URL (an id), e.g. `(app-url (string-append "/app/myapp/pic?id=" id))`.
3. **The app downloads them, one at a time.** `(fs-download url path)` queues a download into the
   app's folder and returns `#t` (`#f` while another one runs). `(fs-download-status)` says when
   it is `done` or failed (`error`); its `seq` grows by one per outcome. Keep a list of the
   pictures the page needs, start the next one from `app-step` (or `app-tick-proc`) when the last
   ended, and invalidate the body when one is done.
4. **Render draws only what is there.** Keep which pictures are ready in a global (set when a
   download is done, after `(image-info path)` returned a list once); render draws
   `(gui-image x y path)` for those and a placeholder box (`theme-card-hdr`) for the others. No
   file access in render.
5. **Keep the folder small.** Pictures count against the app's storage quota (256 KB by
   default, the image included). Reuse a fixed set of names (one per place on the screen,
   overwritten when the page changes, marked not ready until the new one is done) or delete the
   files a new document no longer names (`fs-list`, `fs-remove`). A download replaces a file
   only when complete; a failed one leaves the old file.

- Downloads wait for the JSON feed's current request: keep the picture endpoint fast (cached).
- The same endpoint can serve the app's web page (section 13): the browser loads
  `<img src="PROXY/app/myapp/pic?id=7">` itself, without the device headers, so the endpoint
  must not need them. The page learns PROXY from an `app-web` answer (`(app-proxy)`).
- The simulator fetches through server.py: the picture endpoint must be in minischeme-webrepl's
  `proxy/` copy too (11.4 step 4). Test there before the board.

---

## 12. Settings and storage

### 12.1 meta.ini

```ini
[app]
id = myapp                 ; = the folder and file names
name = 我的应用             ; shown to the user
description = 一句话说明
version = 1                ; bump it on every change you want devices to install
api = 1.9                  ; the firmware API it needs (1.9: the MSBC 2 image format; the build checks it)
pages = 2
page_ids = main, detail    ; English page names (combined apps address pages by them)
; storage_kb = 512         ; only if the app stores much data: replaces the 256 KB folder quota

[fields]
; key = type | label | help        types: text, number:min-max, bool, select:v=label,v=label
city = text | 城市 | 留空表示自动定位

[config]
city =                      ; the default
proxy_url =                 ; empty: the system app server
carousel =                  ; empty: the system setting
carousel_seconds =
```

- `;` and `#` start a comment **anywhere**, also inside values and in `[fields]` help text.
- `(app-config "city" "")` reads the app's `config.ini`, then the system `config.ini`. Choose
  key names that do not clash with system keys. Apps cannot read passwords, tokens or WiFi keys.
- `(app-config-set! key value)` writes the app's own setting.

### 12.2 Files

- Paths are relative to the app's folder (`"data.txt"` = `/spiffs/apps/<id>/data.txt`). The
  sandbox refuses absolute paths outside it and `..`.
- `fs-read`, `fs-write` (whole file), `fs-exists?`, `fs-remove`, `fs-list`; `fs-download` (a
  file from the network, API 1.10: section 11.7). `fs-append`,
  `fs-rename`, `fs-size` and the `kv-*` store are **reserved** (not implemented).
- Keep files small and line-oriented; split growing data into several files (medicine keeps
  one log file per 16 days) so a change rewrites one small file.
- Read files at start (or on change), never in render or every tick. Write only on change.
- The folder quota (default 256 KB, the image included) makes `fs-write` fail when exceeded.

---

## 13. The app's web page

An app may have `apps/<id>/web.html`. The build gzips it into the image; the board shows it as
the first tab of its web UI, and the WebREPL shows it under "🌐 应用网页".

- Put `<!-- appweb -->` in `<head>`: the build replaces it with `appweb.css` + `appweb.js`.
- JavaScript: `await appCall('name', {field: value})` → the parsed JSON answer (throws on
  `{"success":false}`); `say(text, 'ok'|'warn'|'bad')`; `attempt(fn)`; `$(id)`; `esc(s)`.
- Never call `fetch('/api/...')` yourself: the page is sandboxed and only the helpers carry the
  page token (the tests check this).
- Scheme side: define `(app-web name body)` returning a string; use `web-field`,
  `web-field-int`, `web-ok`, `web-error`, `web-json`. Calls run on the main loop between frames;
  the screen is redrawn after each call. Body ≤ 4 KB, answer ≤ 8 KB.
- Calls work only while the app runs.
- Test from the simulator: `--eval "(app-web \"get\" \"\")"` for the answers, and look at the
  page itself: `--install` puts the image into the device's app folder (the web page exists
  only for an installed app, not one started with `--app`), `--webshot` saves the page:

  ```bash
  python tools/sim.py --fresh --install ../minischeme-apps/apps/myapp.msbc --wait 8 \
      --webshot web.png --shot screen.png
  ```
- Design the page as a real control panel, not only a mirror of the screen: what a user would
  want to change or see in more detail (choices that select what the app shows, a longer list,
  links) belongs here. A choice that changes what the board shows should take effect at once
  (the call updates the app's state and settings, the screen redraws), not only after a restart.

See the template (`docs/app-template/hello/web.html`) and the memo and medicine apps.

---

## 14. Testing in the simulator

The simulator is the firmware's C runtime compiled to WASM, inside the WebREPL page, with the
proxy built in. It renders in bands like the board, runs the JSON feed, fonts and clock.

### 14.1 Interactive

```bash
cd minischeme-webrepl && python server.py        # http://127.0.0.1:8087
```

"📦 App 管理": install an app from the list, "设为启动并重启". The list is the market's (GitHub)
plus, when `server.py` serves the page, the apps in minischeme-webrepl's `apps/` that differ
from it, marked 本地编译: run `python tools/build_apps.py myapp --sync` in minischeme-apps to
put your build there. The "KEY 18" button gives short/long presses; a click on the screen is a
touch. The REPL evaluates Scheme in the device.

### 14.2 Headless: tools/sim.py

Commands run in order; each `--eval` prints its result:

```bash
python tools/sim.py --fresh --config app.carousel=0 \
  --app ../minischeme-apps/apps/myapp.msbc --wait 6 --shot p1.png \
  --press short --wait 3 --shot p2.png \
  --press long --wait 2 --eval "myapp-count" \
  --eval "(app-web \"get\" \"\")" --log
```

| Option | Use |
|---|---|
| `--fresh` | a new empty device (always use it for tests) |
| `--app FILE` | boot an image (or a `.scm`, compiled in the page) |
| `--install FILE` | install an image as the market does (its folder, config.ini, web page) and boot it |
| `--webshot F.png` | save the running app's web page (needs `--install`) |
| `--config S.K=V` | set `config.ini [S] K` (e.g. `app.carousel=0` stops page turning) |
| `--press short\|long\|mid\|hold\|SECONDS` | the key |
| `--wait S`, `--shot F.png`, `--eval CODE`, `--log`, `--js EXPR` | wait, screenshot, Scheme, terminal lines, JavaScript |
| `--repl` | read commands from stdin: `eval (+ 1 2)` per line, continues after errors |

Tips:

- A failing `--eval` stops the run (exit 1). To try many expressions use `--repl`.
- Inspect any global of the running app: `--eval "app-page-index"`, `--eval "(app-items)"`.
- Check the footer for fetch errors in screenshots; `--eval "(json-feed-status)"` gives the
  feed's state, error, bytes and memory.
- The simulator has more memory and no `apply` limit: a pass in the simulator is necessary, not
  sufficient. `mem-report` exists only on the board.

---

## 15. Testing and debugging on a real board

### 15.1 Connecting

- The board shows its IP address (hold the key 8 s for the info pages: network page). The PC
  must be on the same network.
- A board with a hardware password needs it for every API call: export it as `MS_PASSWORD`;
  `tools/board.py` sends it in the `X-MiniScheme-Auth` header. Never print or commit it.
- Do not install test builds on a board someone uses daily without asking. Put back the boot app
  you replaced when you finish.
- **Before reflashing a board** (a firmware with a different partition layout erases its file
  system): back up its files in the WebREPL's file manager (**⬇ 备份全部**, one zip) and write
  them back afterwards (**⬆ 恢复备份**). The WebREPL flasher compares the partition tables and
  asks first.

### 15.2 tools/board.py

```bash
export MS_PASSWORD=...                                   # only if the board has one
python tools/board.py 192.168.2.50 info                  # firmware API, VM heap, free system heap
python tools/board.py 192.168.2.50 install myapp --boot  # upload apps/myapp.msbc, boot it, restart
python tools/board.py 192.168.2.50 shot screen.png       # the LCD as a PNG
python tools/board.py 192.168.2.50 exec "(list app-page-index (length app-cache))"
python tools/board.py 192.168.2.50 mem 30                # vm-live and system heap, every minute
python tools/board.py 192.168.2.50 market-auto 0         # stop the market replacing your test build
python tools/board.py 192.168.2.50 boot calendar         # put the previous boot app back
python tools/board.py COM5 log 120                       # the serial console for 2 minutes
```

- `exec` compiles on the PC and runs on the board as the owner (REPL rights); it sees the
  running app's globals. The board itself has no compiler.
- **Market auto-update:** a board with `market_auto_update = 1` replaces an installed app whose
  image differs from the market's, even at the same version. Turn it off while testing
  (`market-auto 0`) and on again afterwards (`market-auto 1`).
- Without the tool: the board's web page (system settings mode) can upload an app, and
  `POST /api/upload?path=/spiffs/apps/<id>/app.msbc&run=0`, `POST /api/settings`
  (`system.boot_app=apps/<id>/app.msbc`), `POST /api/reset` do the same.

### 15.3 What to check on the board

1. Every page, in a screenshot, after the data arrived (footer says "更新于 …").
2. The footer after a server failure (stop the proxy, or point the setting at a wrong
   address): old data stays, a message shows, nothing crashes.
3. Before the clock is synced (just after a restart): no errors with `"--:--"`.
4. `mem 30`: vm-live flat, system free heap stable.
5. The serial log (`log`) for `E (...)` lines and "App ... failure" messages.

### 15.4 When the app crashes

The board shows the error on screen for 5 s and restarts into the system settings. Then:

- `python tools/board.py HOST exec "(app-last-stats)"` and `GET /api/hardware` (`last_app`: the
  previous app's heap, live, peak, allocation, uptime) tell what it used.
- The serial log shows the failing hook and the message (`App render failure (...)`).
- Reproduce in the simulator with the same settings; add `--eval` probes around the failing part.

---

## 16. Memory: budgets, leaks and garbage

### 16.1 Budgets

| Resource | Size | Rule |
|---|---|---|
| VM heap | ~115 KB (firmware 1.0.70+; `/api/info` `heap_capacity`) | the app's **live** data under 32 KB (the tests check it) |
| System heap | ~38 KB free while an app runs | the firmware's (WiFi, HTTP, feed); `apply` and the display list use it |
| Feed document | ~4 KB of values, 64 items | keep endpoints small |
| App ROM slot | 256 KB per image | bytecode and literals are free in RAM |
| App folder | 256 KB by default | `storage_kb` in meta.ini to change |

### 16.2 How the heap behaves

The VM has a generational collector: new objects go to a small young area; a minor collection
copies the survivors to the old area. A **major** collection frees dead objects in the old area.

- `vm-live` / `live-bytes`: what survived the last full collection. This is the app's real
  footprint. **If it grows minute after minute while the app does the same thing, that is a
  leak.**
- `alloc-kb`: everything ever allocated. Its growth per second is the **garbage rate**.
- The heap's "allocated" figure (WebREPL memory panel, `/api/stats` `vm_heap_allocated`) climbs
  between major collections even without a leak, because garbage that happened to be alive at a
  minor collection was promoted. A high garbage rate makes it climb fast, which **looks like a
  leak**, costs CPU and causes long major-GC pauses.

### 16.3 Typical causes

Leaks (live data grows):

- appending to a global list on every fetch or tick without a limit (history, logs, messages):
  cap it (`take`), or keep it in a file;
- a cache keyed by something that changes every time (a URL with the time in it, a new string
  object), so entries are added and never replaced;
- closures stored in globals that capture large documents.

Garbage (allocation per frame or per second):

- building view data in render: `map`, `filter`, `append`, `list->vector`, `string-append`,
  floats, `substring` in render or in procedures render calls;
- recomputing derived data every tick instead of when the data or the minute changes;
- reading settings or files in render or tick (`app-config` reads a file every call);
- calling procedures that build a fresh list each call several times (applib's own footer did
  this with `(json-feed-status)` four times per redraw: fixed by reading it once).

### 16.4 Measuring in the simulator

```bash
P="(let ((s (vm-stats))) (list (cdr (assq 'alloc-kb s)) (cdr (assq 'live-peak s)) (cdr (assq 'major-gcs s))))"
python tools/sim.py --fresh --config app.carousel=0 --app ../minischeme-apps/apps/myapp.msbc \
  --wait 8 --eval "$P" --wait 30 --eval "$P" --wait 30 --eval "$P"
```

- `alloc-kb` difference / 30 s = garbage rate while idle. Aim for well under 1 KB/s.
- Cost of one render of a page (replace with your procedures):

  ```bash
  --eval "(let ((a (cdr (assq 'alloc-kb (vm-stats))))) (let loop ((i 0)) (if (< i 20) (begin (myapp-render-main (app-items)) (loop (+ i 1))))) (- (cdr (assq 'alloc-kb (vm-stats))) a))"
  ```

  The result is KB per 20 renders. More than ~1 KB per render means render builds data.
- Turn pages (`--press short`) and wait several fetch intervals to see the steady state.

### 16.5 Measuring on the board

`python tools/board.py HOST mem 30` prints, once a minute, `vm-live` (after a full collection),
the system free heap, the lowest free heap since boot and the largest block. Healthy: vm-live
flat after the first minute or two; free heap stable. Run it at least 30 minutes, longer for
apps with hourly or daily behavior. `GET /api/stats` (`render_us`, `busy_pct`) shows the render
cost.

Renders per minute and the garbage they make, on the board:

```bash
python tools/board.py HOST exec "(begin (define dbg-n 0) (define dbg-old gui-render-proc) (set! gui-render-proc (lambda () (set! dbg-n (+ dbg-n 1)) (dbg-old))) (define dbg-a (cdr (assq 'alloc-kb (vm-stats)))) #t)"
# one minute later:
python tools/board.py HOST exec "(let ((r (list dbg-n (- (cdr (assq 'alloc-kb (vm-stats))) dbg-a)))) (set! gui-render-proc dbg-old) r)"
```

The result is `(renders KB)`. Such debug globals stay in the heap: restart the app afterwards
(`board.py HOST reset`) before measuring vm-live again.

### 16.6 Case study: the tide app

Reported as "leaking". Findings (2026-10-23, board COM42 and the simulator):

- On the board for 40 minutes: vm-live 23.3 → 24.2 KB in the first minutes, then flat; system
  free heap flat at ~37.7 KB. **No leak.**
- But the board allocated **7.7 KB per second** (a major collection every 30 s), and in the
  simulator the heap's peak climbed 32 → 84 KB before the first major collection. That is
  **garbage**, and it looks like a leak.
- Where it came from (measured with the loops of 16.4 on the board):
  - the location had no tide model, so the app drew from its built-in table, and every render
    rebuilt that view: a vector, the extrema lists (`append`, `map`, `filter`), label strings
    and floats from `tide-at`: a full redraw of page 1 cost 18 KB, page 2 15 KB;
  - the carousel redraws the header every second and the footer's long scrolling error message
    redraws the footer every second: 114 renders a minute;
  - applib's footer called `(json-feed-status)`, which builds a new list, four times per redraw.
- Fixes: the view is cached and rebuilt only when the minute or the lunar day changes
  (`tide-view-local` compares `app-time` and `app-lunar` with `string=?`), the per-day row lists
  are part of the view, and the footer reads the status once. Result on the board: page 1 18 →
  8 KB per full redraw, page 2 15 → 10 KB, the garbage rate 7.7 → 4.3 KB/s with the carousel
  and 0.8 KB/s without it.
- Lessons: compute views when the data or the time changes and keep them in globals; render
  only draws. Count how often each part is redrawn (wrap `gui-render-proc` from `exec` and
  count `gui-visible?` per section), then measure what one redraw allocates.

### 16.7 Keeping the image small

An app's image (`apps/<id>.msbc`) is its bytecode (MSBC), then its gzipped web page and
metadata. On the board the bytecode is built into an App ROM slot (256 KB) and run from flash,
so size costs flash, download time and the app folder's quota (256 KB by default, data
included), not RAM. Measure with:

```bash
python tools/msbc_stats.py apps/myapp.msbc
```

**The build already compacts the format.** Since API 1.9 `build_apps.py` writes MSBC version 2
by default: each symbol name is stored once in a table and referred to by a small index, and
function headers are variable-length. That made every app about 23% smaller (all apps
1,060 KB → 817 KB; medicine 126.6 → 97.5 KB) without touching the code. It is why every
app declares `api = 1.9`. Only for firmware older than API 1.9: `python tools/build_apps.py
--msbc1 <app>` writes the old format (and the app can then declare its real, lower API).

What an image is made of (the medicine app, 97.5 KB):

| Part | Size | Note |
|---|---|---|
| Shared framework | about 40 KB | gui.scm, infopages, applib, appweb (with a web page): in every app |
| The app's own code | about 42 KB | 1,502 lines |
| web.html, gzipped | 13 KB | 30 KB before compression |

By content the bytecode part is 62% instructions, 24% symbol names and references, 8% string
constants and 4% function headers (542 functions). What you can still do:

- **Fewer, fuller functions**: every function (each `define`d procedure, each `lambda`, named
  `let` included) has a header and refers to every global it uses (2-3 bytes each, per
  function). A helper called from one place, or the same `(lambda (x) ...)` written inline in
  many `map` / `filter` calls, costs more than one named helper reused.
- **Repeated literals**: a string literal is stored in each function that uses it. Text used in
  several places goes into one top-level `define`.
- **No embedded fonts** (`use-font` without `'system`): a font subset can be tens of KB.
- **The web page**: rely on `appweb.css` / `appweb.js`; no base64 images, no copied libraries.
- **Data**: large constant tables cost flash and download size; fetch them from the app server,
  or keep them in the app's folder, when they can change.
- Keep the App ROM image (about 1.5x the version 2 bytecode part; the build and the board's boot
  log print it) well inside its 256 KB slot.

---

## 17. Automated tests

| Where | Command | What |
|---|---|---|
| minischeme-apps | `python -m unittest discover -s tests -v` | web pages use the helpers and the token; images carry the current page; metadata; build outputs; the template still builds (CI runs it on every push and PR) |
| minischeme-proxy | `python -m pytest -q` | endpoints, database, security; add `tests/test_<name>.py` for a new endpoint |
| minischeme-webrepl | `python -m pytest -q tests` | the simulator, the CLI, app scenarios (`tests/test_app_medicine.py` drives an app through sim.py) |

An app with logic worth protecting (parsing, scheduling, records) gets a simulator test in
minischeme-webrepl modeled on `tests/test_app_medicine.py`: a list of `(name . expression)`
checks that must each give `#t`, run in order on one fresh device.

---

## 18. Pull requests

Contributors (other agents included) deliver changes as pull requests to `main`.

1. Branch from an up-to-date `main`: `git checkout main && git pull && git checkout -b feat/myapp`.
2. Commit **sources only**: `apps/<id>/<id>.scm`, `meta.ini`, `web.html`, `tools/build_apps.py`,
   tests, docs. Do **not** commit build outputs (`*.msbc`, `*.allinone.scm`, `index.json`,
   `apps/index.json`, `dist/`): CI builds and commits them after the merge. Add files by name
   and put back the outputs you rebuilt:

   ```bash
   git add apps/myapp/myapp.scm apps/myapp/meta.ini apps/myapp/web.html tools/build_apps.py
   git checkout -- '*.msbc' '*.allinone.scm' index.json apps/index.json dist
   git status            # only your sources staged; new build outputs stay untracked
   ```
3. Conventional English commit messages: `feat(myapp): ...`, `fix(tide): ...`, `docs: ...`,
   `test: ...`. One logical change per commit.
4. Push and open the PR:

   ```bash
   git push -u origin feat/myapp
   gh pr create --base main --title "feat(myapp): ..." --body-file pr.md
   ```

   Without `gh`, use the GitHub web page or the REST API with a token from an environment
   variable (`GH_TOKEN`), never written to a file or command history you commit.
5. The PR description must contain:
   - what the app or change does, with screenshots of every page (simulator, and the board
     if you used one);
   - the memory measurements (16.4 / 16.5): idle garbage rate, vm-live over time;
   - the tests run and their results;
   - for a new endpoint: the minischeme-proxy PR link.
6. CI (`Build and Release Applications`) builds every app and runs the tests on the PR. Fix it
   until green.
7. A change to the proxy goes to minischeme-proxy as its own PR (and the same files to
   minischeme-webrepl's `proxy/`).

---

## 19. Release and deployment (maintainers)

For reference; contributors stop at the PR.

1. Merge the PR. CI builds and pushes a `chore(build)` commit with the images.
2. `git pull`, tag `vX.Y.Z` on that commit, push the tag; run the workflow for the tag
   (workflow dispatch with ref = the tag) to publish the GitHub Release.
3. Copy the images into minischeme-webrepl and minischeme-proxy (`apps/`) and, for the built-in
   apps, the headers into minischeme-esp32 (`build_apps.py --sync` does all of it); release
   those repositories the same way.
4. Deploy the public app server (minischeme-proxy, `tools/deploy_public_proxy.py`) after backing
   up its database and configuration; verify the device count and that the market lists the
   new version.
5. Devices with market auto-update install the new version at their next boot.

---

## 20. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `unbound variable: do` / `quasiquote` / `even?` / `sort` | not in MiniScheme: section 5.2 |
| `... (reserved API since 1.0.0: not provided by this firmware ...)` | a documented but unimplemented procedure: find another way |
| `out of memory allocating argument list` (board only) | `apply` on a long list: use a loop |
| Text cut in the middle of a character, garbage glyphs | `substring` on UTF-8: use `txt-fit` / `txt-wrap` |
| `items-find` error or always `#f` | type must be a string (`"day"`), not a symbol |
| Number compare fails | fields are strings: `(or (it-int it 1) 0)` |
| Page shows "正在获取数据..." forever | URL wrong or server missing: check `(json-feed-status)`, open the URL in a browser |
| Footer shows "代理: ..." | the server sent an error item: the message says why |
| A setting change has no effect | URL procedures run once: the app must restart (the settings page restarts it) |
| Embedded font misses characters | do not embed: `'system` fonts |
| Board screen flickers or is slow, `busy_pct` high | too many draw commands (> 512) or heavy render: section 7.2 |
| Heap "allocated" keeps climbing | probably garbage, maybe a leak: measure vm-live (16.5) |
| Test build replaced by the market version | `market-auto 0` while testing |
| Web page calls answer 401 | `fetch('/api/...')` used directly: use `appCall` |
| `meta.ini` value cut short | `;` or `#` inside the value starts a comment |
| App works in the simulator, crashes on the board | `apply`, memory (smaller heap), a font missing from the board's ROM |

---

## 21. References and keeping this guide current

| Topic | Where |
|---|---|
| Framework reference (pages, items, helpers, pitfalls, web pages, sandbox) | [applib.md](https://github.com/chk-jxcn/minischeme-esp32/blob/main/docs/api/applib.md) |
| Every device procedure, with status and examples | [docs/api](https://github.com/chk-jxcn/minischeme-esp32/tree/main/docs/api) (`README.md`, `v1.x.0.md`) |
| Example apps | tide (charts, local fallback), medicine (schedule, sync, web page, files), memo (web page), calendar (live rows), weather (icons, several pages) |
| App server endpoints | minischeme-proxy `proxy/endpoints.py`, `proxy/tide.py`, `proxy/medicine.py` |
| Simulator | minischeme-webrepl `tools/sim.py --help`, `tests/` |

This guide quotes facts from the other repositories: API procedures and limits, applib
behavior, simulator options, endpoint conventions, memory figures and the release flow. Whoever
changes one of those must update this guide in the same change round.
