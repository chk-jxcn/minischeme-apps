"""MiniScheme device API specification: the single source of truth.

Every procedure an app can call is one entry in api/spec/*.py. tools/gen_api.py
turns the entries into
  - minischeme_api_table.h   the firmware's API table ((api-version), (api-has? ...))
  - minischeme_help_table.h  the runtime help ((help 'name), WebREPL completion)
  - tests/api_examples.h     the examples, run by tests/test_api.c
  - docs/api/v<version>.md   the reference for app authors (and agents)

Versioning (semantic, major.minor.patch):
  - patch: fixes only, no interface change;
  - minor: additions; everything of the same major keeps working (backward
    compatible). A new entry gets since = the new minor version;
  - major: incompatible changes (an entry removed or its behavior changed).
An app declares the API it needs in its meta.ini ([app] api = 1.0); it runs on
a firmware of the same major and an equal or higher minor.

Hardware-specific procedures are extension APIs (ext='esp32'): versioned on
their own, present only on devices that have them (EXTENSIONS below).
"""

API_VERSION = '1.11.0'  # 1.11: font-server, emoji (UTF-8 above U+FFFF); 1.10: fs-download; 1.9: MSBC 2

# Extension APIs and their versions
EXTENSIONS = {
    'esp32': ('1.0.0', 'ESP32 chip features (Espressif SoC only)'),
}

# Entry status
STABLE = 'stable'        # provided by every firmware of this API version
RESERVED = 'reserved'    # name and signature fixed; not implemented yet
ALIAS = 'alias'          # an older name of another entry (alias_of), kept for compatibility

# Where an entry is provided
ALL = 'all'              # firmware, WASM simulator and the PC REPL
DEVICE = 'device'        # firmware and WASM simulator (board services: config, apps, fs)
PC = 'pc'                # the PC REPL only (host files and processes)

FIELDS = ('name', 'component', 'sig', 'desc', 'returns', 'example', 'since', 'status',
          'alias_of', 'ext', 'where', 'check', 'notes')


def api(name, component, sig, desc, returns='', example='', since='1.0.0', status=STABLE,
        alias_of=None, ext=None, where=ALL, check=True, notes=''):
    """One API entry.

    name      the global name ("gpio-write")
    component the component id (api/components.py)
    sig       the prototype: "(gpio-write pin level)"; [x] optional, x ... rest
    desc      one or two sentences: what it does (English, shown by (help))
    returns   the value and its type, and the error cases
    example   Scheme code; a line ending in "; => value" is checked by
              tests/test_api.c when check is True (the value as `write` prints it)
    since     the API version that added it
    status    STABLE, RESERVED or ALIAS
    alias_of  for ALIAS: the canonical name
    ext       an extension id (EXTENSIONS) for hardware-specific entries
    where     ALL, DEVICE or PC
    check     False: the example needs real hardware or state the test VM lacks
    notes     longer remarks for the reference (optional)
    """
    return dict(name=name, component=component, sig=sig, desc=desc, returns=returns,
                example=example.strip('\n'), since=since, status=status, alias_of=alias_of,
                ext=ext, where=where, check=check, notes=notes)


def alias(name, target, component, since='1.0.0', where=ALL):
    """A legacy name kept as an alias: same procedure as `target`."""
    return api(name, component, '', '', since=since, status=ALIAS, alias_of=target, where=where)


def version_tuple(v):
    parts = [int(x) for x in v.split('.')]
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])
