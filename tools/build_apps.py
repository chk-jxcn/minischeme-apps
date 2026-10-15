"""Compiles the bundled Scheme apps to MSBC images and portable FASL snapshots.

Every app is built to web_repl/apps/<id>.msbc: one folder holding all of
them, which tools/install_apps.py (or the device's settings page) uploads to
the board's /spiffs/apps/, and which the WebREPL simulator installs from.

  calendar (the default app): applib + apps/calendar/calendar.scm
      -> examples/app_default_msbc.h (embedded in the firmware)
      -> examples/app.msbc, web_repl/app.msbc
      -> examples/app.fasl, web_repl/app.fasl
  PC monitor:       gui.scm + pcmonitor.scm
      -> examples/pcmonitor.msbc, web_repl/pcmonitor.msbc
      -> examples/pcmonitor.fasl, web_repl/pcmonitor.fasl

Metadata: apps/<id>/meta.ini ([app] id, name, description, version, pages;
[config] the app's default settings, written to /spiffs/apps/<id>.ini on its
first start) is appended to every image and snapshot (minischeme_device.h):
    [image][meta][u32 length][u32 FNV-1a of the meta]["MSMD"]
Readers of the image stop before it, so older firmware runs these files too.

The compiler is the same one the WebREPL runs (web_repl/wasm/compiler_msbc.h),
driven by tools/compile_to_hex.c. Each .fasl is the app booted on the PC by
tools/msbc_to_fasl.c and dumped in the portable 32-bit layout, so it installs
on the board as /spiffs/app.fasl. Both tools are built when needed.

Fonts: each (use-font ID "face" SIZE) in an app becomes
(font-register! ID (include-bytes "build/fonts/<app>-<ID>.mfnt")), a subset
of the face (tools/make_font.py) holding ASCII plus every character of the
app's string literals. In the .msbc image the font is a Code ROM literal
(read in place from Flash); a .fasl snapshot carries it in the heap. A face
ending in .mfnt that exists here is embedded as is; one that does not is left
to load at run time.

An app can also leave its fonts out: then (use-font ...) stays in the code
and finds the font by name "<face>-<size>" in the board's system font ROM
(tools/make_fontrom.py, WebREPL font manager), else /spiffs/fonts/, else the
built-in 16 px font. Per form: (use-font 2 "simsun" 16 'system) is never
embedded, (use-font 2 "simsun" 16 'embed) always is; --system-fonts makes
'system the default for the forms without one.

    python tools/build_apps.py [--system-fonts] [calendar|pcmonitor|settings|weather|news|stocks|usage ...]
"""
import gzip
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_font  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE = ['minischeme.c', 'minischeme_vm.c', 'minischeme_gc.c', 'minischeme_prim.c', 'minischeme_math.c',
        'minischeme_bigint.c', 'minischeme_fasl.c', 'minischeme_lib.c', 'minischeme_gui.c',
        'minischeme_ili9488.c', 'minischeme_fonts.c', 'minischeme_fontreg.c', 'minischeme_fontrom.c', 'minischeme_mirror.c', 'minischeme_image.c', 'minischeme_cfasl.c', 'minischeme_help.c',
        'minischeme_device.c', 'minischeme_jsonfeed.c', 'minischeme_api.c', 'minischeme_market.c']
COMPILER_EXE = os.path.join(ROOT, 'tools', 'compile_to_hex.exe')
FASL_EXE = os.path.join(ROOT, 'tools', 'msbc_to_fasl.exe')
GCC = r'C:\TDM-GCC-64\BIN\gcc.exe' if os.path.exists(r'C:\TDM-GCC-64\BIN\gcc.exe') else 'gcc'

APPS_DIR = 'web_repl/apps'   # every app's image, together
INFO_PAGES = 'apps/lib/infopages.scm'      # hardware pages on a long press, in every app
APP_LIB = ['web_repl/gui.scm', INFO_PAGES, 'apps/lib/applib.scm']
# an app with its own web page (apps/<id>/web.html) also gets the Scheme side
# of its calls (form fields, JSON); the page gets apps/lib/appweb.css and .js
APP_WEB_LIB = 'apps/lib/appweb.scm'
APP_WEB_MARK = '<!-- appweb -->'

# id: sources, extra image copies (each also gets a .fasl), C header
APPS = {
    'pcmonitor': (['web_repl/gui.scm', INFO_PAGES, 'web_repl/pcmonitor.scm'],
                  ['examples/pcmonitor.msbc', 'web_repl/pcmonitor.msbc'], None),
    # the system settings (KEY 18 held 5 s), embedded in the firmware and the WebREPL simulator
    'settings': (['web_repl/gui.scm', 'apps/settings/settings.scm'], [], 'examples/app_settings_msbc.h'),
}
# apps built on the shared app framework (apps/lib/applib.scm): apps/<id>/<id>.scm
for _app in ('weather', 'news', 'stocks', 'usage', 'calendar', 'memo', 'futures', 'crypto', 'wxpusher', 'notifier',
             'album'):
    if os.path.exists(os.path.join(ROOT, 'apps', _app, f'{_app}.scm')):
        _web = [APP_WEB_LIB] if os.path.exists(os.path.join(ROOT, 'apps', _app, 'web.html')) else []
        APPS[_app] = (APP_LIB + _web + [f'apps/{_app}/{_app}.scm'], [], None)
# the calendar is also the default app: /spiffs/app.msbc and the firmware's embedded copy
APPS['calendar'] = (APPS['calendar'][0], ['examples/app.msbc', 'web_repl/app.msbc'], 'examples/app_default_msbc.h')


# ---- The API an app needs (api/spec; docs/api/README.md) ----

TOKEN_RE = re.compile(r'[^\s()\[\]\'`,"]+')
DEFINE_RE = re.compile(r'\((?:define|define-macro|define-syntax)\s+\(?\s*([^\s()]+)')


def scheme_code(text):
    """text without comments and string literals (their words are no calls)."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == ';':
            while i < n and text[i] != '\n':
                i += 1
        elif c == '"':
            i += 1
            while i < n and text[i] != '"':
                i += 2 if text[i] == '\\' else 1
            i += 1
            out.append(' ')
        elif text.startswith('#\\', i):      # character literals: #\( #\space
            i += 3
            while i < n and not text[i].isspace() and text[i] not in '()':
                i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def api_needs(source_text):
    """(version 'M.m', [extension ids], {name: entry} used, [reserved names used])
    of the API procedures the app calls (its own definitions excluded)."""
    import api as A
    from api.spec import ALL
    code = scheme_code(source_text)
    defined = set(DEFINE_RE.findall(code))
    table = {e['name']: e for e in ALL}
    used = {t: table[t] for t in set(TOKEN_RE.findall(code)) if t in table and t not in defined}
    need = max([A.version_tuple(e['since']) for e in used.values() if not e['ext']] + [(1, 0, 0)])
    exts = sorted({e['ext'] for e in used.values() if e['ext']})
    reserved = sorted(n for n, e in used.items() if e['status'] == A.RESERVED)
    return f'{need[0]}.{need[1]}', exts, used, reserved


# ---- No sensitive defaults in an image: its [config] is sent to every board ----

SECRET_KEY_RE = re.compile(r'(?i)(key|token|secret|passw|pwd|credential|auth)')
SECRET_VALUE_RE = re.compile(
    r'(?<![\d.])(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])'
    r'|\b[0-9a-fA-F]{24,}\b|\b[A-Za-z0-9_\-]{32,}\b')


def sanitize_config(app_id, meta):
    """meta with every [config] default that looks sensitive (a key named like
    a credential, a private network address, a long token) packaged empty:
    the placeholder the board's settings page shows for the user to fill."""
    out, section = [], ''
    for line in meta.split('\n'):
        m = re.match(r'\s*\[([^\]]+)\]', line)
        if m:
            section = m.group(1).strip().lower()
        kv = re.match(r'(\s*)([^=;#\s][^=;#]*?)\s*=\s*([^;#]*?)\s*([;#].*)?$', line)
        if section == 'config' and kv and kv.group(3):
            key, value, comment = kv.group(2), kv.group(3), kv.group(4) or ''
            if SECRET_KEY_RE.search(key) or SECRET_VALUE_RE.search(value):
                print(f'{app_id}: warning: [config] {key} has a sensitive-looking default: packaged empty')
                line = f'{kv.group(1)}{key} = ' + (comment if comment else '')
        out.append(line)
    return '\n'.join(out)


def app_meta(app_id, source_text):
    """apps/<id>/meta.ini with [app] api (and extensions) set to what the code
    needs: added when missing, an error when declared lower."""
    import api as A
    path = os.path.join(ROOT, 'apps', app_id, 'meta.ini')
    if not os.path.exists(path):
        return None
    meta = sanitize_config(app_id, open(path, 'rb').read().replace(b'\r\n', b'\n').decode('utf-8'))
    need, exts, used, reserved = api_needs(source_text)
    for n in reserved:
        print(f'{app_id}: warning: {n} is a reserved API (not provided yet): guard it with (api-has? \'{n})')
    declared = re.search(r'(?m)^api\s*=\s*([0-9.]+)', meta)
    if declared and A.version_tuple(declared.group(1)) < A.version_tuple(need):
        sys.exit(f'{app_id}: meta.ini declares api = {declared.group(1)} but the code needs {need}')
    if A.version_tuple(need) > A.version_tuple(A.API_VERSION):
        sys.exit(f'{app_id}: needs API {need}, newer than this firmware\'s {A.API_VERSION}')
    add = []
    if not declared:
        add.append(f'api = {need}')
    declared_ext = re.search(r'(?m)^extensions\s*=\s*(.*)$', meta)
    have = {x.strip().split(' ')[0] for x in declared_ext.group(1).split(',')} if declared_ext else set()
    missing = [x for x in exts if x not in have]
    if missing and declared_ext:
        sys.exit(f'{app_id}: the code uses the {", ".join(missing)} extension API, not in meta.ini extensions')
    if missing:
        add.append('extensions = ' + ', '.join(f'{x} {A.EXTENSIONS[x][0].rsplit(".", 1)[0]}' for x in missing))
    if add:   # right after the [app] keys
        m = re.search(r'(?ms)^\[app\]\n.*?(?=^\s*$|^\[)', meta)
        at = m.end() if m else len(meta)
        meta = meta[:at] + ''.join(line + '\n' for line in add) + meta[at:]
    print(f'{app_id}: API {need}' + (f' + {", ".join(exts)}' if exts else '') + f' ({len(used)} procedures)')
    return meta.encode('utf-8')


sys.path.insert(0, ROOT)   # the api package (api/spec)


def meta_trailer(app_id, source_text=''):
    """The metadata trailer of an app: apps/<id>/meta.ini (with its API
    requirement) + length + FNV-1a + "MSMD"."""
    meta = app_meta(app_id, source_text)
    if meta is None:
        return b''
    h = 2166136261
    for b in meta:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return meta + len(meta).to_bytes(4, 'little') + h.to_bytes(4, 'little') + b'MSMD'


def web_section(app_id):
    """The app's web page, gzip'd, as the section before the meta trailer:
    [page.gz][u32 length][u32 FNV-1a]["MSWP"] (minischeme_device.h). The
    marker <!-- appweb --> in apps/<id>/web.html becomes the shared style and
    helpers (apps/lib/appweb.css, appweb.js). b'' without a page."""
    path = os.path.join(ROOT, 'apps', app_id, 'web.html')
    if not os.path.exists(path):
        return b''
    with open(path, encoding='utf-8') as f:
        html = f.read()
    if APP_WEB_MARK in html:
        with open(os.path.join(ROOT, 'apps', 'lib', 'appweb.css'), encoding='utf-8') as f:
            css = f.read()
        with open(os.path.join(ROOT, 'apps', 'lib', 'appweb.js'), encoding='utf-8') as f:
            js = f.read()
        html = html.replace(APP_WEB_MARK, f'<style>\n{css}</style>\n<script>\n{js}</script>')
    gz = gzip.compress(html.encode('utf-8'), compresslevel=9, mtime=0)
    return gz + len(gz).to_bytes(4, 'little') + fnv1a(gz).to_bytes(4, 'little') + b'MSWP'


def read_web(data):
    """The gzip'd page of an image, or None (as mini_app_web_find)."""
    if len(data) < 20 or data[-4:] != b'MSMD':
        return None
    end = len(data) - 12 - int.from_bytes(data[-12:-8], 'little')
    if end < 12 or data[end - 4:end] != b'MSWP':
        return None
    n = int.from_bytes(data[end - 12:end - 8], 'little')
    gz = data[end - 12 - n:end - 12]
    return gz if n and fnv1a(gz) == int.from_bytes(data[end - 8:end - 4], 'little') else None


def read_meta(data):
    """The meta text appended to an image, or None (as mini_app_meta_find)."""
    if len(data) < 20 or data[-4:] != b'MSMD':
        return None
    n = int.from_bytes(data[-12:-8], 'little')
    if n == 0 or n > len(data) - 20:
        return None
    meta = data[-12 - n:-12]
    h = 2166136261
    for b in meta:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return meta.decode('utf-8') if h == int.from_bytes(data[-8:-4], 'little') else None


def ensure_tool(exe, source, extra_deps=()):
    deps = [os.path.join(ROOT, p) for p in CORE + [source] + list(extra_deps)]
    if os.path.exists(exe) and all(os.path.getmtime(d) <= os.path.getmtime(exe) for d in deps):
        return
    cmd = [GCC, '-O2', '-w', '-I.', '-DMINISCHEME_NO_MAIN', source] + CORE + ['-lm', '-o', exe]
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'building {os.path.basename(exe)} failed:\n' + r.stderr)


def ensure_compiler():
    ensure_tool(COMPILER_EXE, 'tools/compile_to_hex.c', ['compiler.scm', 'web_repl/wasm/compiler_msbc.h'])
    ensure_tool(FASL_EXE, 'tools/msbc_to_fasl.c', ['web_repl/msbc.h'])


def make_fasl(msbc_path):
    fasl_path = msbc_path[:-len('.msbc')] + '.fasl'
    r = subprocess.run([FASL_EXE, msbc_path, fasl_path], cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'{fasl_path}: snapshot failed:\n' + r.stderr + r.stdout)
    return os.path.relpath(fasl_path, ROOT).replace(os.sep, '/')


# (font-use ...) and its older name (use-font ...)
USE_FONT_RE = re.compile(r'\((?:font-use|use-font)\s+([0-9]+)\s+"([^"]+)"(?:\s+([0-9]+))?(?:\s+\'(embed|system))?\s*\)')
SYSTEM_FONTS = False  # --system-fonts


def embed_fonts(name, text):
    """Replaces (font-use ...) / (use-font ...) forms by fonts embedded in the image."""
    chars = set()
    for m in make_font.STRING_RE.finditer(text):
        chars.update(m.group(1))

    def subst(m):
        font_id, face, size = int(m.group(1)), m.group(2), int(m.group(3) or 16)
        if (m.group(4) or ('system' if SYSTEM_FONTS else 'embed')) == 'system':
            print(f'{name}: font {font_id} = {face} {size}px from the system font ROM')
            return m.group(0)
        if face.endswith('.mfnt'):
            local = os.path.join(ROOT, face.lstrip('/'))
            if not os.path.exists(local):
                return m.group(0)
            path = local
        else:
            data = make_font.build_mfnt(face, size, chars)
            path = os.path.join(ROOT, 'build', 'fonts', f'{name}-{font_id}.mfnt')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
            print(f'{name}: font {font_id} = {face} {size}px, {len(data)} bytes -> '
                  f'{os.path.relpath(path, ROOT)}')
        rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
        return f'(font-register! {font_id} (include-bytes "{rel}"))'

    return USE_FONT_RE.sub(subst, text)


def source_text(sources):
    return '\n'.join(open(os.path.join(ROOT, s), encoding='utf-8').read() for s in sources)


def compile_sources(sources, name=None):
    text = source_text(sources)
    if name:
        text = embed_fonts(name, text)
    r = subprocess.run([COMPILER_EXE, '-'], input=text, capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
    if r.returncode != 0:
        sys.exit('compile error:\n' + r.stderr)
    return bytes.fromhex(r.stdout.strip())


HEADER_BRIEF = {'calendar': 'Calendar Application (the default app)', 'settings': 'System Settings Application'}


def write_header(path, data, name):
    base = os.path.basename(path)            # app_default_msbc.h
    sym = base[:-2]                          # app_default_msbc
    lines = ['/**', f' * @file {base}',
             f' * @brief Pre-compiled MSBC bytecode for {HEADER_BRIEF.get(name, name)}.', ' */',
             f'#ifndef {sym.upper()}_H', f'#define {sym.upper()}_H', '',
             '#include <stdint.h>', '#include <stddef.h>', '',
             f'#define {sym.upper()}_LEN {len(data)}', '',
             f'static const uint8_t {sym}_data[] = {{']
    for i in range(0, len(data), 16):
        lines.append('    ' + ', '.join(f'0x{b:02X}' for b in data[i:i + 16]) + ',')
    lines += ['};', '', f'#endif /* {sym.upper()}_H */\n']
    with open(os.path.join(ROOT, path), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def fnv1a(data):
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def write_index():
    """web_repl/apps/index.json: the app market's index (every image in
    APPS_DIR with its metadata). The WebREPL's app manager offers these apps,
    and boards install and update them from it (tools/app_proxy.py serves the
    folder as /market/; any static HTTP server can). Per app: id, name,
    description, version, pages, api, extensions, kind ("app", or "system"
    for the settings: installed but never a boot app), file, size and hash
    (FNV-1a of the whole file, 8 hex digits, as the board computes it)."""
    out = []
    folder = os.path.join(ROOT, APPS_DIR)
    for name in sorted(os.listdir(folder)):
        if not name.endswith('.msbc'):
            continue
        data = open(os.path.join(folder, name), 'rb').read()
        meta = read_meta(data) or ''
        info = {}
        section = ''
        for line in meta.splitlines():
            t = line.strip()
            if t.startswith('['):
                section = t.strip('[]')
            elif section == 'app' and '=' in t and not t.startswith(';'):
                k, v = t.split('=', 1)
                info[k.strip()] = v.split(';')[0].strip()
        out.append({'id': info.get('id', name[:-5]), 'name': info.get('name', name[:-5]),
                    'description': info.get('description', ''), 'version': info.get('version', ''),
                    'pages': int(info.get('pages', '1') or 1), 'api': info.get('api', '1.0'),
                    'extensions': info.get('extensions', ''), 'kind': info.get('kind', 'app') or 'app',
                    'web': read_web(data) is not None,
                    'file': name, 'size': len(data),
                    'hash': f'{fnv1a(data):08x}'})
    with open(os.path.join(folder, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'{APPS_DIR}/index.json: {len(out)} apps')


def main():
    global SYSTEM_FONTS
    args = sys.argv[1:]
    SYSTEM_FONTS = '--system-fonts' in args
    names = [a for a in args if not a.startswith('--')] or list(APPS)
    ensure_compiler()
    os.makedirs(os.path.join(ROOT, APPS_DIR), exist_ok=True)
    for name in names:
        sources, images, header = APPS[name]
        trailer = meta_trailer(name, source_text(sources))
        web = web_section(name)
        data = compile_sources(sources, name) + web + trailer
        # the settings too: built into the firmware (the bootstrap) and in the
        # market, as a system app ([app] kind = system) that is never a boot app
        images = [f'{APPS_DIR}/{name}.msbc'] + images
        os.makedirs(os.path.join(ROOT, 'build'), exist_ok=True)
        for img in images:
            with open(os.path.join(ROOT, img), 'wb') as f:
                f.write(data)
        if header:
            write_header(header, data, name)
        print(f'{name}: {len(data)} bytes (meta {len(trailer)}{f", web page {len(web)}" if web else ""}) -> '
              f'{", ".join(images + ([header] if header else []))}')
        fasls = [make_fasl(os.path.join(ROOT, img)) for img in images[1:]]
        for fasl in fasls:  # snapshots carry the same metadata
            with open(os.path.join(ROOT, fasl), 'ab') as f:
                f.write(trailer)
        if fasls:
            size = os.path.getsize(os.path.join(ROOT, fasls[0]))
            print(f'{name}: {size} bytes portable snapshot -> {", ".join(fasls)}')
    write_index()
    # keep the examples/ copies of the sources in sync
    for src in ('gui.scm', 'pcmonitor.scm'):
        with open(os.path.join(ROOT, 'web_repl', src), 'rb') as f:
            data = f.read()
        with open(os.path.join(ROOT, 'examples', src), 'wb') as f:
            f.write(data)


if __name__ == '__main__':
    main()
