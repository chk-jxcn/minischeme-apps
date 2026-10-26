#!/usr/bin/env python3
"""Compiles the bundled MiniScheme apps to MSBC bytecode images and metadata.

Usage:
    python tools/build_apps.py [--system-fonts] [--sync] [--no-inline-arith] [--msbc1] [app1 app2 ...]

Images are MSBC version 2 (each symbol name once, in a table: about a
quarter smaller), which firmware API 1.9 reads, with inline arithmetic
instructions ((+ a b), (< a b) ... of the global procedures), which firmware
API 1.14 runs: every app then needs at least API 1.14. --no-inline-arith
compiles them as calls (API 1.9 is enough); --msbc1 writes version 1 (names
inline, calls) for firmware before 1.9.

Everything is written inside this repository (dist/, apps/, index.json).
--sync also copies the results into sibling checkouts, when they exist:
    ../minischeme-esp32/main/app_*_msbc.h      (embedded calendar and settings)
    ../minischeme-webrepl/apps, ../minischeme-proxy/apps  (images, sources, index)
(The original single repository is retired: nothing is written there.)
Without --sync no file outside this repository is touched.
"""

import gzip
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(ROOT, 'tools')
sys.path.insert(0, TOOLS_DIR)

import make_font  # noqa: E402

MINISCHEME_DIR = os.getenv("MINISCHEME_PATH") or os.path.join(TOOLS_DIR, "minischeme")
COMPILER_EXE = os.path.join(TOOLS_DIR, 'compile_to_hex.exe' if os.name == 'nt' else 'compile_to_hex')
GCC = os.getenv("CC") or (r'C:\TDM-GCC-64\BIN\gcc.exe' if os.path.exists(r'C:\TDM-GCC-64\BIN\gcc.exe') else 'gcc')

APPS_DIR = os.path.join(ROOT, 'dist')
INFO_PAGES = 'apps/lib/infopages.scm'
APP_LIB = ['apps/lib/gui.scm', INFO_PAGES, 'apps/lib/applib.scm']
APP_WEB_LIB = 'apps/lib/appweb.scm'
APP_WEB_MARK = '<!-- appweb -->'

# The app library ("applib"): every file of apps/lib/, versioned as one bundle by
# (define applib-version "MAJOR.MINOR") in applib.scm. A backward compatible change
# raises MINOR, an incompatible one MAJOR. Each build writes the bundle to
# dist/lib/<version>/ (with api.json: its documented definitions); the folders of
# earlier versions stay, and dist/lib/index.json lists them all, so an app written
# for any version can still be built (the WebREPL's editor picks one). An app
# declares the version it needs in meta.ini ([app] applib = 1.0): it builds with
# the same MAJOR and an equal or higher MINOR.
LIB_FILES = ['gui.scm', 'infopages.scm', 'applib.scm', 'appweb.scm', 'combo.scm',
             'combo_web.html', 'appweb.css', 'appweb.js']
APPLIB_VERSION_RE = re.compile(r'\(define\s+applib-version\s+"(\d+)\.(\d+)"\)')


def applib_version():
    """'MAJOR.MINOR' of apps/lib/applib.scm."""
    m = APPLIB_VERSION_RE.search(open(os.path.join(ROOT, 'apps', 'lib', 'applib.scm'), encoding='utf-8').read())
    if not m:
        sys.exit('apps/lib/applib.scm: no (define applib-version "MAJOR.MINOR")')
    return f'{m.group(1)}.{m.group(2)}'


def applib_ok(need, have):
    """Whether library version have serves an app that needs version need."""
    n, h = [int(x) for x in need.split('.')], [int(x) for x in have.split('.')]
    return n[0] == h[0] and n[1] <= h[1]


APPS = {
    'pcmonitor': (['apps/lib/gui.scm', INFO_PAGES, 'apps/pcmonitor/pcmonitor.scm'], [], None),
    'settings': (['apps/lib/gui.scm', 'apps/settings/settings.scm'], [], 'dist/app_settings_msbc.h'),
}

for _app in ('weather', 'news', 'stocks', 'usage', 'calendar', 'memo', 'futures', 'crypto', 'wxpusher', 'notifier', 'album',
             'tide', 'medicine', 'bilibili', 'agenda'):
    if os.path.exists(os.path.join(ROOT, 'apps', _app, f'{_app}.scm')):
        _web = [APP_WEB_LIB] if os.path.exists(os.path.join(ROOT, 'apps', _app, 'web.html')) else []
        APPS[_app] = (APP_LIB + _web + [f'apps/{_app}/{_app}.scm'], [], None)

if 'calendar' in APPS:
    APPS['calendar'] = (APPS['calendar'][0], [], 'dist/app_default_msbc.h')

# Combined apps (apps/<id>/meta.ini with [combo] members = a, b, ...): the
# members' code in one image (apps/lib/combo.scm); each member reads its
# own config.ini, its meta.ini [config] defaults are carried in the code.
# The WebREPL's 合并应用 builds the same thing in the browser.
COMBO_LIB = 'apps/lib/combo.scm'
COMBO_META = {}


def scheme_string(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def member_glue(app_id, meta_text):
    """(combo-member! "id" '("front" ...) (list (cons "key" "default") ...)) for a member."""
    secs = ini_sections(meta_text)
    ids_line = next((l for l in secs.get('app', []) if re.match(r'\s*page_ids\s*=', l)), '')
    ids = [x.strip() for x in ids_line.split('=', 1)[1].split(';')[0].split(',')] if ids_line else []
    defaults = []
    for line in secs.get('config', []):
        kv = re.match(r'\s*([A-Za-z0-9_]+)\s*=\s*([^;#]*?)\s*(?:[;#].*)?$', line)
        if kv:
            defaults.append(f'(cons {scheme_string(kv.group(1))} {scheme_string(kv.group(2))})')
    return (f';; generated by tools/build_apps.py: {app_id} is loaded\n'
            f'(combo-member! "{app_id}" (list {" ".join(scheme_string(i) for i in ids if i)})\n'
            f'               (list {" ".join(defaults)}))\n')


def ini_sections(text):
    """{section: [lines]} of an ini text (comments and blank lines kept)."""
    out, section = {}, ''
    for line in text.replace('\r\n', '\n').split('\n'):
        m = re.match(r'\s*\[([^\]]+)\]', line)
        if m:
            section = m.group(1).strip().lower()
            out.setdefault(section, [])
            continue
        out.setdefault(section, []).append(line)
    return out


def combo_app(app_id):
    """(sources, merged meta.ini text) of a combined app, None for another app."""
    meta_path = os.path.join(ROOT, 'apps', app_id, 'meta.ini')
    if not os.path.exists(meta_path):
        return None
    meta = open(meta_path, encoding='utf-8').read().replace('\r\n', '\n')
    secs = ini_sections(meta)
    members_line = next((l for l in secs.get('combo', []) if re.match(r'\s*members\s*=', l)), None)
    if not members_line:
        return None
    members = [m.strip() for m in members_line.split('=', 1)[1].split(';')[0].split(',') if m.strip()]
    glue_dir = os.path.join(ROOT, 'build', 'combo', app_id)
    os.makedirs(glue_dir, exist_ok=True)
    sources = list(APP_LIB)
    sources.append(APP_WEB_LIB)       # its own page (apps/lib/combo_web.html) and the members' app-web
    sources.append(COMBO_LIB)
    for m in members:
        src = f'apps/{m}/{m}.scm'
        if not os.path.exists(os.path.join(ROOT, src)):
            sys.exit(f'{app_id}: member {m} has no {src}')
        glue = os.path.join(glue_dir, f'member_{m}.scm')
        with open(glue, 'w', encoding='utf-8', newline='\n') as f:
            f.write(member_glue(m, open(os.path.join(ROOT, 'apps', m, 'meta.ini'), encoding='utf-8').read()))
        # its folder and settings while its code loads (combo.scm)
        loading = os.path.join(glue_dir, f'loading_{m}.scm')
        with open(loading, 'w', encoding='utf-8', newline='\n') as f:
            f.write(f';; generated by tools/build_apps.py: {m} loads next\n(combo-loading! {scheme_string(m)})\n')
        sources += [os.path.relpath(loading, ROOT).replace(os.sep, '/'), src,
                    os.path.relpath(glue, ROOT).replace(os.sep, '/')]
    start = os.path.join(glue_dir, 'start.scm')
    title = next((l.split('=', 1)[1].split(';')[0].strip() for l in secs.get('app', []) if re.match(r'\s*name\s*=', l)), app_id)
    with open(start, 'w', encoding='utf-8', newline='\n') as f:
        f.write(f';; generated by tools/build_apps.py: the entries become this app\'s pages\n(combo-start! "{title}")\n')
    sources.append(os.path.relpath(start, ROOT).replace(os.sep, '/'))
    return sources, meta


for _d in sorted(os.listdir(os.path.join(ROOT, 'apps'))):
    if _d not in APPS and os.path.isdir(os.path.join(ROOT, 'apps', _d)):
        _combo = combo_app(_d)
        if _combo:
            APPS[_d] = (_combo[0], [], None)
            COMBO_META[_d] = _combo[1]


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
    of the API procedures the app calls (its own definitions excluded).
    Errors propagate: a build must never guess an app's API requirement."""
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


SECRET_KEY_RE = re.compile(r'(?i)(key|token|secret|passw|pwd|credential|auth)')
SECRET_VALUE_RE = re.compile(
    r'(?<![\d.])(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])'
    r'|\b[0-9a-fA-F]{24,}\b|\b[A-Za-z0-9_\-]{32,}\b')


def sanitize_config(app_id, meta, quiet=False):
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
                if not quiet:
                    print(f'{app_id}: warning: [config] {key} has a sensitive-looking default: packaged empty')
                line = f'{kv.group(1)}{key} = ' + (comment if comment else '')
        out.append(line)
    return '\n'.join(out)


def app_meta(app_id, source_text, uses_lib=True):
    """apps/<id>/meta.ini with [app] api (and extensions) set to what the code
    needs: added when missing; a build error when declared lower, when newer
    than this firmware API, or when a used extension is not declared. [app]
    applib (an app built with apps/lib/): added as this library's version when
    missing; a build error when this library does not serve the declared one."""
    import api as A
    path = os.path.join(ROOT, 'apps', app_id, 'meta.ini')
    if not os.path.exists(path):
        return None
    raw = COMBO_META.get(app_id) or open(path, 'rb').read().replace(b'\r\n', b'\n').decode('utf-8')
    meta = sanitize_config(app_id, raw)
    need, exts, used, reserved = api_needs(source_text)
    if not MSBC1 and A.version_tuple(need) < A.version_tuple(MSBC2_API):
        need = MSBC2_API   # the image format itself needs it
    if not NO_INLINE and A.version_tuple(need) < A.version_tuple(INLINE_API):
        need = INLINE_API  # so do its arithmetic instructions
    for n in reserved:
        print(f"{app_id}: warning: {n} is a reserved API (not provided yet): guard it with (api-has? '{n})")
    declared = re.search(r'(?m)^api\s*=\s*([0-9.]+)', meta)
    if declared and A.version_tuple(declared.group(1)) < A.version_tuple(need):
        sys.exit(f'{app_id}: meta.ini declares api = {declared.group(1)} but the code needs {need}')
    if A.version_tuple(need) > A.version_tuple(A.API_VERSION):
        sys.exit(f"{app_id}: needs API {need}, newer than this firmware's {A.API_VERSION}")
    add = []
    if not declared:
        add.append(f'api = {need}')
    lib = applib_version()
    declared_lib = re.search(r'(?m)^applib\s*=\s*([0-9]+\.[0-9]+)', meta)
    if uses_lib and declared_lib and not applib_ok(declared_lib.group(1), lib):
        sys.exit(f'{app_id}: meta.ini needs applib {declared_lib.group(1)}, but apps/lib/ is {lib}')
    if uses_lib and not declared_lib:
        add.append(f'applib = {lib}')
    declared_ext = re.search(r'(?m)^extensions\s*=\s*([^;#\n]*)', meta)
    have = {x.strip().split(' ')[0] for x in declared_ext.group(1).split(',')} if declared_ext else set()
    missing = [x for x in exts if x not in have]
    if missing and declared_ext:
        sys.exit(f'{app_id}: the code uses the {", ".join(missing)} extension API, not in meta.ini extensions')
    if missing:
        add.append('extensions = ' + ', '.join(f'{x} {A.EXTENSIONS[x][0].rsplit(".", 1)[0]}' for x in missing))
    print(f'{app_id}: API {need}' + (f' + {", ".join(exts)}' if exts else '') + f' ({len(used)} procedures)')
    if add:   # right after the [app] keys
        m = re.search(r'(?ms)^\[app\]\n.*?(?=^\s*$|^\[)', meta)
        at = m.end() if m else len(meta)
        meta = meta[:at] + ''.join(line + '\n' for line in add) + meta[at:]
    return meta.encode('utf-8')


def fnv1a(data):
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def meta_trailer(app_id, source_text='', uses_lib=True):
    meta = app_meta(app_id, source_text, uses_lib)
    if meta is None:
        return b''
    h = fnv1a(meta)
    return meta + len(meta).to_bytes(4, 'little') + h.to_bytes(4, 'little') + b'MSMD'


def web_section(app_id):
    path = os.path.join(ROOT, 'apps', app_id, 'web.html')
    if not os.path.exists(path) and app_id in COMBO_META:   # a combined app: the shared page
        path = os.path.join(ROOT, 'apps', 'lib', 'combo_web.html')
    if not os.path.exists(path):
        return b''
    with open(path, encoding='utf-8') as f:
        html = f.read()
    if APP_WEB_MARK in html:
        css_path = os.path.join(ROOT, 'apps', 'lib', 'appweb.css')
        js_path = os.path.join(ROOT, 'apps', 'lib', 'appweb.js')
        css = js = ''
        if os.path.exists(css_path):
            with open(css_path, encoding='utf-8') as f:
                css = f.read()
        if os.path.exists(js_path):
            with open(js_path, encoding='utf-8') as f:
                js = f.read()
        html = html.replace(APP_WEB_MARK, f'<style>\n{css}</style>\n<script>\n{js}</script>')
    gz = gzip.compress(html.encode('utf-8'), compresslevel=9, mtime=0)
    return gz + len(gz).to_bytes(4, 'little') + fnv1a(gz).to_bytes(4, 'little') + b'MSWP'


def read_web(data):
    if len(data) < 20 or data[-4:] != b'MSMD':
        return None
    end = len(data) - 12 - int.from_bytes(data[-12:-8], 'little')
    if end < 12 or data[end - 4:end] != b'MSWP':
        return None
    n = int.from_bytes(data[end - 12:end - 8], 'little')
    gz = data[end - 12 - n:end - 12]
    return gz if n and fnv1a(gz) == int.from_bytes(data[end - 8:end - 4], 'little') else None


def read_meta(data):
    if len(data) < 20 or data[-4:] != b'MSMD':
        return None
    n = int.from_bytes(data[-12:-8], 'little')
    if n == 0 or n > len(data) - 20:
        return None
    meta = data[-12 - n:-12]
    h = fnv1a(meta)
    return meta.decode('utf-8') if h == int.from_bytes(data[-8:-4], 'little') else None


def ensure_minischeme():
    if not os.path.exists(MINISCHEME_DIR):
        print(f"[*] Checking out minischeme into {MINISCHEME_DIR}...")
        subprocess.run(['git', 'clone', 'https://github.com/chk-jxcn/minischeme.git', MINISCHEME_DIR], check=True)


def ensure_compiler():
    ensure_minischeme()
    src_dir = os.path.join(MINISCHEME_DIR, 'src')
    inc_dir = os.path.join(MINISCHEME_DIR, 'include')
    c_sources = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.endswith('.c')]
    source = os.path.join(TOOLS_DIR, 'compile_to_hex.c')
    deps = c_sources + [source, os.path.join(TOOLS_DIR, 'msbc.h'), os.path.join(TOOLS_DIR, 'compiler_msbc.h')]

    if os.path.exists(COMPILER_EXE) and all(os.path.getmtime(d) <= os.path.getmtime(COMPILER_EXE) for d in deps if os.path.exists(d)):
        return

    print(f"[*] Building compiler: {COMPILER_EXE}...")
    cmd = [GCC, '-O2', '-std=c99', '-w', '-DMINISCHEME_NO_MAIN', f'-I{TOOLS_DIR}', f'-I{inc_dir}', '-o', COMPILER_EXE, source] + c_sources + ['-lm']
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f'building {os.path.basename(COMPILER_EXE)} failed:\n' + r.stderr)


USE_FONT_RE = re.compile(r'\((?:font-use|use-font)\s+([0-9]+)\s+"([^"]+)"(?:\s+([0-9]+))?(?:\s+\'(embed|system))?\s*\)')
SYSTEM_FONTS = False  # --system-fonts
SYNC = False          # --sync: also copy the results into sibling repositories
MSBC1 = False         # --msbc1: MSBC version 1 images (firmware before API 1.9)
MSBC2_API = '1.9'     # the API that reads MSBC version 2
NO_INLINE = False     # --no-inline-arith (or --msbc1): arithmetic as calls (firmware before API 1.14)
INLINE_API = '1.14'   # the API that runs the inline arithmetic instructions


def embed_fonts(name, text):
    chars = set()
    for m in make_font.STRING_RE.finditer(text):
        chars.update(m.group(1))

    def subst(m):
        font_id, face, size = int(m.group(1)), m.group(2), int(m.group(3) or 16)
        if SYSTEM_FONTS or (m.group(4) == 'system'):
            return m.group(0)
        try:
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
            rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
            return f'(font-register! {font_id} (include-bytes "{rel}"))'
        except Exception as e:
            return m.group(0)

    return USE_FONT_RE.sub(subst, text)


def generate_allinone_scm(name, sources):
    meta_path = os.path.join(ROOT, 'apps', name, 'meta.ini')
    meta_header = ''
    if os.path.exists(meta_path):
        meta_lines = open(meta_path, encoding='utf-8').read().replace('\r\n', '\n').splitlines()
        meta_header = ';;; =========================================================================\n'
        meta_header += f';;; MiniScheme Standalone Application: {name}\n'
        meta_header += ';;; All-in-One Standalone Scheme Source (Libraries Included for WebREPL)\n'
        meta_header += ';;; =========================================================================\n'
        for line in meta_lines:
            meta_header += f';;; {line}\n'
        meta_header += '\n'

    code_parts = []
    for s in sources:
        code_parts.append(f';;; =========================================================================\n'
                          f';;; Section: {s}\n'
                          f';;; =========================================================================\n'
                          + open(os.path.join(ROOT, s), encoding='utf-8').read())
    return meta_header + '\n\n'.join(code_parts) + '\n'


def source_text(sources):
    return '\n'.join(open(os.path.join(ROOT, s), encoding='utf-8').read() for s in sources)


def compile_sources(sources, name=None):
    text = source_text(sources)
    if name:
        text = embed_fonts(name, text)
    flags = (['--msbc1'] if MSBC1 else []) + (['--no-inline-arith'] if NO_INLINE else [])
    r = subprocess.run([COMPILER_EXE, '-'] + flags, input=text, capture_output=True,
                       text=True, encoding='utf-8', cwd=ROOT)
    if r.returncode != 0:
        sys.exit(f'Compile error in {name}:\n' + r.stderr)
    return bytes.fromhex(r.stdout.strip())


HEADER_BRIEF = {'calendar': 'Calendar Application (the default app)', 'settings': 'System Settings Application'}


def write_header(path, data, name):
    base = os.path.basename(path)
    sym = base[:-2]
    lines = ['/**', f' * @file {base}',
             f' * @brief Pre-compiled MSBC bytecode for {HEADER_BRIEF.get(name, name)}.', ' */',
             f'#ifndef {sym.upper()}_H', f'#define {sym.upper()}_H', '',
             '#include <stdint.h>', '#include <stddef.h>', '',
             f'#define {sym.upper()}_LEN {len(data)}', '',
             f'static const uint8_t {sym}_data[] = {{']
    for i in range(0, len(data), 16):
        lines.append('    ' + ', '.join(f'0x{b:02X}' for b in data[i:i + 16]) + ',')
    lines += ['};', '', f'#endif /* {sym.upper()}_H */\n']
    content = '\n'.join(lines)

    targets = [os.path.join(ROOT, path)]
    if SYNC:   # --sync: the firmware's embedded copy
        for candidate_dir in [
            os.path.join(ROOT, '..', 'minischeme-esp32', 'main'),
        ]:
            if os.path.isdir(candidate_dir):
                targets.append(os.path.join(candidate_dir, base))

    for target in targets:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, 'w', encoding='utf-8', newline='\n') as f:   # LF on every host
            f.write(content)
        print(f"    [+] Wrote embedded header: {os.path.relpath(target, ROOT)}")


def write_index():
    out = []
    folder = APPS_DIR
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
        app_id = info.get('id', name[:-5])
        out.append({'id': app_id, 'name': info.get('name', app_id),
                    'description': info.get('description', ''), 'version': info.get('version', ''),
                    'api': info.get('api', '1.0'),
                    'extensions': info.get('extensions', ''), 'kind': info.get('kind', 'app') or 'app',
                    'pages': int(info['pages']) if info.get('pages', '').isdigit() else 1,
                    'page_ids': [x.strip() for x in info.get('page_ids', '').split(',') if x.strip()],
                    'web': read_web(data) is not None,
                    'file': name, 'size': len(data),
                    'scm': f'{app_id}.allinone.scm',
                    'hash': f'{fnv1a(data):08x}',
                    'applib': info.get('applib', ''),
                    'libs': app_libs(app_id),
                    'source': f'apps/{app_id}/{app_id}.scm'
                    if os.path.exists(os.path.join(ROOT, 'apps', app_id, f'{app_id}.scm')) else '',
                    'meta': f'apps/{app_id}/meta.ini',
                    'web_page': f'apps/{app_id}/web.html'
                    if os.path.exists(os.path.join(ROOT, 'apps', app_id, 'web.html')) else ''})
    for idx_path in [os.path.join(folder, 'index.json'),
                     os.path.join(ROOT, 'apps', 'index.json'),
                     os.path.join(ROOT, 'index.json')]:
        with open(idx_path, 'w', encoding='utf-8', newline='\n') as f:   # LF on every host
            json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'[*] Wrote {len(out)} apps to dist/index.json, apps/index.json, and index.json')


def app_libs(app_id):
    """The library files an app's image is built with, in order ("gui", "applib", ...)."""
    if app_id not in APPS:
        return []
    return [os.path.splitext(os.path.basename(s))[0] for s in APPS[app_id][0] if s.startswith('apps/lib/')]


def lib_definitions(text, file_name):
    """(definitions, sections) of a library file. definitions: [{name, sig, doc, kind,
    section, file}], a procedure always, a variable when it has a comment; doc is the
    ";;" comment right above the definition, else the comment at the end of its line.
    sections: {title: the comment paragraph under its numbered banner}, the
    reference shown for a definition without a doc of its own."""
    out, comment, section, sections, intro, rule = [], [], '', {}, None, False
    for line in text.replace('\r\n', '\n').split('\n'):
        s = line.strip()
        after_rule, rule = rule, bool(re.match(r';+\s*[=-]{5,}\s*$', s))
        # a numbered title: ";; 9. Alerts ------" or between two ";;; -----" rules
        banner = re.match(r';;;?\s*(\d+[a-z]?\.\s+.+?)\s*(-{3,})?$', s)
        if banner and not line.startswith(' ') and (banner.group(2) or after_rule):
            section, intro, comment = banner.group(1), [], []
            continue
        if s.startswith(';'):
            if not re.match(r';+\s*[=-]{5,}', s):
                (intro if intro is not None else comment).append(re.sub(r'^;+\s?', '', s))
            continue
        if intro is not None:            # the banner's paragraph ends at the first other line
            if intro:
                sections[section] = '\n'.join(intro).strip()
            intro = None
        tail = re.search(r'\)\s*;+\s*(.+)$', line)
        doc = '\n'.join(comment).strip() or (tail.group(1).strip() if tail else '')
        m = re.match(r'\(define\s+(\(([^\s()]+)[^)]*\))', line)
        if m:
            out.append({'name': m.group(2), 'sig': m.group(1), 'doc': doc,
                        'kind': 'procedure', 'section': section, 'file': file_name})
        else:
            m = re.match(r'\(define\s+([^\s()]+)', line)
            if m and doc:
                out.append({'name': m.group(1), 'sig': m.group(1), 'doc': doc,
                            'kind': 'variable', 'section': section, 'file': file_name})
        comment = []
    return out, sections


def write_lib():
    """dist/lib/<applib version>/: the library files and api.json; dist/lib/index.json:
    every version there (earlier ones are kept), with the firmware API each needs."""
    lib = applib_version()
    folder = os.path.join(APPS_DIR, 'lib', lib)
    os.makedirs(folder, exist_ok=True)
    defs, sections = [], {}
    for name in LIB_FILES:
        src = os.path.join(ROOT, 'apps', 'lib', name)
        data = open(src, 'rb').read().replace(b'\r\n', b'\n')
        with open(os.path.join(folder, name), 'wb') as f:
            f.write(data)
        if name.endswith('.scm'):
            d, secs = lib_definitions(data.decode('utf-8'), name)
            defs += d
            sections.update({f'{name}: {k}': v for k, v in secs.items()})
    need = api_needs(source_text([f'apps/lib/{n}' for n in ('gui.scm', 'infopages.scm', 'applib.scm')]))[0]
    if not MSBC1 and tuple(map(int, need.split('.'))) < tuple(map(int, MSBC2_API.split('.'))):
        need = MSBC2_API
    with open(os.path.join(folder, 'api.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'applib': lib, 'api': need, 'files': LIB_FILES, 'sections': sections, 'definitions': defs},
                  f, ensure_ascii=False, indent=1)
    versions = []
    for v in os.listdir(os.path.join(APPS_DIR, 'lib')):
        info = os.path.join(APPS_DIR, 'lib', v, 'api.json')
        if re.fullmatch(r'\d+\.\d+', v) and os.path.exists(info):
            d = json.load(open(info, encoding='utf-8'))
            versions.append({'version': v, 'api': d.get('api', ''), 'files': d.get('files', [])})
    versions.sort(key=lambda x: tuple(int(p) for p in x['version'].split('.')), reverse=True)
    with open(os.path.join(APPS_DIR, 'lib', 'index.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'current': lib, 'versions': versions}, f, ensure_ascii=False, indent=1)
    print(f'[*] applib {lib} (API {need}, {len(defs)} definitions) -> dist/lib/{lib}/; {len(versions)} version(s) listed')


def write_api_reference():
    """dist/api.json: the firmware API (tools/api/spec) for the WebREPL's reference list."""
    import api as A
    from api.spec import ALL
    keep = ('name', 'component', 'sig', 'desc', 'returns', 'example', 'since', 'status', 'alias_of', 'ext',
            'where', 'notes')
    with open(os.path.join(APPS_DIR, 'api.json'), 'w', encoding='utf-8', newline='\n') as f:
        json.dump({'api': A.API_VERSION, 'extensions': {k: v[0] for k, v in A.EXTENSIONS.items()},
                   'entries': [{k: e[k] for k in keep if e.get(k) not in (None, '')} for e in ALL]},
                  f, ensure_ascii=False, indent=1)


def main():
    global SYSTEM_FONTS, SYNC, MSBC1, NO_INLINE
    args = sys.argv[1:]
    SYSTEM_FONTS = '--system-fonts' in args
    SYNC = '--sync' in args
    MSBC1 = '--msbc1' in args
    NO_INLINE = MSBC1 or '--no-inline-arith' in args
    names = [a for a in args if not a.startswith('--')] or list(APPS)

    ensure_compiler()
    os.makedirs(APPS_DIR, exist_ok=True)

    print(f"[*] Compiling {len(names)} apps to MSBC bytecode and all-in-one Scheme in {os.path.relpath(APPS_DIR, ROOT)}/...")
    for name in names:
        sources, images, header = APPS[name]
        trailer = meta_trailer(name, source_text(sources), any(s.startswith('apps/lib/') for s in sources))
        web = web_section(name)
        data = compile_sources(sources, name) + web + trailer

        # Write MSBC binary to dist/, apps/, and apps/<name>/
        for msbc_dest in [
            os.path.join(APPS_DIR, f'{name}.msbc'),
            os.path.join(ROOT, 'apps', f'{name}.msbc'),
            os.path.join(ROOT, 'apps', name, f'{name}.msbc'),
        ]:
            with open(msbc_dest, 'wb') as f:
                f.write(data)

        if header:
            write_header(header, data, name)

        # Generate standalone all-in-one Scheme source file
        allinone_text = generate_allinone_scm(name, sources)
        for scm_dest in [
            os.path.join(APPS_DIR, f'{name}.allinone.scm'),
            os.path.join(ROOT, 'apps', f'{name}.allinone.scm'),
            os.path.join(ROOT, 'apps', name, f'{name}.allinone.scm'),
        ]:
            with open(scm_dest, 'w', encoding='utf-8', newline='\n') as f:
                f.write(allinone_text)

        print(f"  [OK] {name}: {len(data)} bytes -> {name}.msbc & {name}.allinone.scm ({len(allinone_text)} chars)")

    write_lib()
    write_api_reference()
    write_index()

    if not SYNC:
        print("[*] Cross-repository sync skipped (pass --sync to copy into sibling checkouts)")
    # --sync: the compiled apps and all-in-one sources into the git-ignored apps/ of a
    # minischeme-webrepl checkout (its local server and editor take them before GitHub's)
    # and of minischeme-proxy (deploy_public_proxy.py --with-apps)
    for dest_repo in (['minischeme-webrepl', 'minischeme-proxy'] if SYNC else []):
        dest_apps = os.path.join(ROOT, '..', dest_repo, 'apps')
        if os.path.isdir(os.path.dirname(dest_apps)):
            os.makedirs(dest_apps, exist_ok=True)
            import shutil
            for fn in os.listdir(APPS_DIR):
                if fn.endswith('.msbc') or fn.endswith('.allinone.scm') or fn in ('index.json', 'api.json'):
                    shutil.copy2(os.path.join(APPS_DIR, fn), os.path.join(dest_apps, fn))
            # the app library's versions (dist/lib/<version>/, index.json): the WebREPL's editor
            shutil.copytree(os.path.join(APPS_DIR, 'lib'), os.path.join(dest_apps, 'lib'), dirs_exist_ok=True)
            # the sources: the library and each app's folder (code, meta.ini, web page)
            for sub in sorted(os.listdir(os.path.join(ROOT, 'apps'))):
                src_dir = os.path.join(ROOT, 'apps', sub)
                if os.path.isdir(src_dir):
                    shutil.copytree(src_dir, os.path.join(dest_apps, sub), dirs_exist_ok=True,
                                    ignore=shutil.ignore_patterns('*.msbc', '*.allinone.scm', '__pycache__'))
            print(f"[*] Synced compiled apps to {os.path.relpath(dest_apps, ROOT)}")

    print("[*] Build completed successfully!")


if __name__ == '__main__':
    main()
