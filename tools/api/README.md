# API specification (source of truth)

Every procedure an app can call is one entry in `api/spec/*.py`. Nothing else
lists the API by hand: `python tools/gen_api.py` generates the firmware's API
table, the runtime help, the example tests and the reference
(`docs/api/v<version>.md`). `docs/api/README.md` explains the API to app
authors (versioning, hooks, the app framework).

## Entry fields (`api()` in `api/__init__.py`)

| Field | Meaning |
|---|---|
| `name` | The global name. Device procedures are `component-function` (`gpio-write`); the language core keeps standard Scheme names. Extension procedures start with the extension id (`esp32-mac`). |
| `component` | A key of `api/components.py`. |
| `sig` | The prototype: `(gpio-write pin level)`. `[x]` optional, `x ...` rest arguments. |
| `desc` | One or two sentences, present tense, what it does. Compiled into the firmware's help table: keep it short (under ~200 characters), English. |
| `returns` | The value and its type, then the error cases: `#t; an error when pin is not 0..39.` For procedures called for effect say what they return anyway (often `#t` or void). |
| `example` | Scheme code an app would write. A line ending in `; => value` is checked: the value as `write` prints it (`"text"` with quotes, `(1 2)`, `#t`; void prints as nothing, so do not mark void results). `; => error` or `; => error: text` expects an error whose message contains text. Lines without a marker run but are not compared. Each example runs on a fresh firmware-profile VM. |
| `since` | The API version that added the entry (`1.0.0`). |
| `status` | `STABLE` (implemented), `RESERVED` (name and signature fixed, not implemented: still write `returns` and an example of the intended use), `ALIAS` (an older name; made with `alias()`). |
| `where` | `ALL` (firmware, WASM simulator, PC REPL), `DEVICE` (firmware and WASM only: their examples are not run by the tests), `PC` (PC REPL only). |
| `ext` | An extension id of `EXTENSIONS` in `api/__init__.py` for hardware-specific entries. |
| `check` | `False` when the example cannot run on the test VM (real hardware, network, timing) or its values vary; it is still shown in the reference. |
| `notes` | Optional longer text for the reference (units, ranges, interactions). Not in the firmware. |

## Checking

```bash
python tools/check_api_examples.py core data   # the examples of some modules
python tools/gen_api.py                        # regenerate everything
python tools/gen_api.py --strict --check       # what the test suite runs
```

The test VM (`tests/test_api.c`) is the firmware's: no `init.scm`, the shared C
libraries, a 320x480 framebuffer, no network, no files except what the example
writes, GPIO/ADC/WiFi from the host mocks of `minischeme_lib.c`.

## Changing the API

- Fix or document without changing behavior: patch version (1.0.0 -> 1.0.1).
- Add an entry or an optional argument: minor version (1.0 -> 1.1); the new
  entry gets `since='1.1.0'`. Implementing a reserved entry is also a minor
  change: set `status=STABLE` and its `since` to the new version.
- Remove or change the behavior of an entry: major version (1.x -> 2.0).
- Bump `API_VERSION` in `api/__init__.py`, regenerate; the previous
  `docs/api/v<old>.md` stays as the record of that version.
