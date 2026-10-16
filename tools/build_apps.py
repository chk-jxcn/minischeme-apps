#!/usr/bin/env python3
"""Compiles the bundled MiniScheme apps to MSBC bytecode images and metadata.

Usage:
    python tools/build_apps.py [--system-fonts] [app1 app2 ...]
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

APPS = {
    'pcmonitor': (['apps/lib/gui.scm', INFO_PAGES, 'apps/pcmonitor/pcmonitor.scm'], [], None),
    'settings': (['apps/lib/gui.scm', 'apps/settings/settings.scm'], [], 'dist/app_settings_msbc.h'),
}

for _app in ('weather', 'news', 'stocks', 'usage', 'calendar', 'memo', 'futures', 'crypto', 'wxpusher', 'notifier', 'album'):
    if os.path.exists(os.path.join(ROOT, 'apps', _app, f'{_app}.scm')):
        _web = [APP_WEB_LIB] if os.path.exists(os.path.join(ROOT, 'apps', _app, 'web.html')) else []
        APPS[_app] = (APP_LIB + _web + [f'apps/{_app}/{_app}.scm'], [], None)

if 'calendar' in APPS:
    APPS['calendar'] = (APPS['calendar'][0], [], 'dist/app_default_msbc.h')


TOKEN_RE = re.compile(r'[^\s()\[\]\'`,"]+')
DEFINE_RE = re.compile(r'\((?:define|define-macro|define-syntax)\s+\(?\s*([^\s()]+)')


def scheme_code(text):
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == ';':
            while i < n and text[i] != '\n':
                i += 1
        elif c == '"':
            i += 1
            while i < n and text[i] != '"':
                if text[i] == '\\':
                    i += 1
                i += 1
            i += 1
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def api_needs(source_text):
    try:
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
    except Exception as e:
        return '1.0', [], {}, []


SECRET_KEY_RE = re.compile(r'(?i)(key|token|secret|passw|pwd|credential|auth)')
SECRET_VALUE_RE = re.compile(
    r'(?<![\d.])(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![\d.])'
    r'|\b[0-9a-fA-F]{24,}\b|\b[A-Za-z0-9_\-]{32,}\b')


def sanitize_config(app_id, meta):
    out, section = [], ''
    for line in meta.split('\n'):
        m = re.match(r'\s*\[([^\]]+)\]', line)
        if m:
            section = m.group(1).strip().lower()
        kv = re.match(r'(\s*)([^=;#\s][^=;#]*?)\s*=\s*([^;#]*?)\s*([;#].*)?$', line)
        if section == 'config' and kv and kv.group(3):
            key, value, comment = kv.group(2), kv.group(3), kv.group(4) or ''
            if SECRET_KEY_RE.search(key) or SECRET_VALUE_RE.search(value):
                print(f'{app_id}: warning: [config] {key} has sensitive default: packaged empty')
                line = f'{kv.group(1)}{key} = ' + (comment if comment else '')
        out.append(line)
    return '\n'.join(out)


def app_meta(app_id, source_text):
    path = os.path.join(ROOT, 'apps', app_id, 'meta.ini')
    if not os.path.exists(path):
        return None
    meta = sanitize_config(app_id, open(path, 'rb').read().replace(b'\r\n', b'\n').decode('utf-8'))
    need, exts, used, reserved = api_needs(source_text)
    declared = re.search(r'(?m)^api\s*=\s*([0-9.]+)', meta)
    add = []
    if not declared:
        add.append(f'api = {need}')
    if add:
        m = re.search(r'(?ms)^\[app\]\n.*?(?=^\s*$|^\[)', meta)
        at = m.end() if m else len(meta)
        meta = meta[:at] + ''.join(line + '\n' for line in add) + meta[at:]
    return meta.encode('utf-8')


def fnv1a(data):
    h = 2166136261
    for b in data:
        h = ((h ^ b) * 16777619) & 0xFFFFFFFF
    return h


def meta_trailer(app_id, source_text=''):
    meta = app_meta(app_id, source_text)
    if meta is None:
        return b''
    h = fnv1a(meta)
    return meta + len(meta).to_bytes(4, 'little') + h.to_bytes(4, 'little') + b'MSMD'


def web_section(app_id):
    path = os.path.join(ROOT, 'apps', app_id, 'web.html')
    if not os.path.exists(path):
        return b''
    with open(path, encoding='utf-8') as f:
        html = f.read()
    if APP_WEB_MARK in html:
        css_path = os.path.join(ROOT, 'apps', 'lib', 'appweb.css')
        js_path = os.path.join(ROOT, 'apps', 'lib', 'appweb.js')
        css = open(css_path, encoding='utf-8').read() if os.path.exists(css_path) else ''
        js = open(js_path, encoding='utf-8').read() if os.path.exists(js_path) else ''
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
SYSTEM_FONTS = False


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
    r = subprocess.run([COMPILER_EXE, '-'], input=text, capture_output=True, text=True, encoding='utf-8', cwd=ROOT)
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
    target = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


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
                    'pages': int(info.get('pages', '1') or 1), 'api': info.get('api', '1.0'),
                    'extensions': info.get('extensions', ''), 'kind': info.get('kind', 'app') or 'app',
                    'web': read_web(data) is not None,
                    'file': name, 'size': len(data),
                    'scm': f'{app_id}.allinone.scm',
                    'hash': f'{fnv1a(data):08x}'})
    with open(os.path.join(folder, 'index.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'[*] Wrote {len(out)} apps to {os.path.relpath(folder, ROOT)}/index.json')


def main():
    global SYSTEM_FONTS
    args = sys.argv[1:]
    SYSTEM_FONTS = '--system-fonts' in args
    names = [a for a in args if not a.startswith('--')] or list(APPS)

    ensure_compiler()
    os.makedirs(APPS_DIR, exist_ok=True)

    print(f"[*] Compiling {len(names)} apps to MSBC bytecode and all-in-one Scheme in {os.path.relpath(APPS_DIR, ROOT)}/...")
    for name in names:
        sources, images, header = APPS[name]
        trailer = meta_trailer(name, source_text(sources))
        web = web_section(name)
        data = compile_sources(sources, name) + web + trailer
        target_file = os.path.join(APPS_DIR, f'{name}.msbc')
        with open(target_file, 'wb') as f:
            f.write(data)
        if header:
            write_header(header, data, name)

        # Generate standalone all-in-one Scheme source file
        allinone_text = generate_allinone_scm(name, sources)
        dist_allinone = os.path.join(APPS_DIR, f'{name}.allinone.scm')
        with open(dist_allinone, 'w', encoding='utf-8') as f:
            f.write(allinone_text)

        # Also store in app directory
        app_allinone = os.path.join(ROOT, 'apps', name, f'{name}.allinone.scm')
        with open(app_allinone, 'w', encoding='utf-8') as f:
            f.write(allinone_text)

        print(f"  [OK] {name}: {len(data)} bytes -> {name}.msbc & {name}.allinone.scm ({len(allinone_text)} chars)")

    write_index()
    print("[*] Build completed successfully!")


if __name__ == '__main__':
    main()
