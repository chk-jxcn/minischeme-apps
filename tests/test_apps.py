"""Checks of the apps' sources and built images (run after tools/build_apps.py):
python -m unittest discover -s tests -v"""
import gzip
import json
import os
import re
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_apps  # noqa: E402

APPS = os.path.join(ROOT, 'apps')


def app_ids():
    return sorted(d for d in os.listdir(APPS)
                  if d != 'lib' and os.path.isfile(os.path.join(APPS, d, 'meta.ini')))


def web_apps():
    return [a for a in app_ids() if os.path.isfile(os.path.join(APPS, a, 'web.html'))]


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def ini(text):
    """{section: {key: value}} with ; comments removed (the firmware's reading)"""
    out, sec = {}, None
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in ';#':
            continue
        if s.startswith('[') and s.endswith(']'):
            sec = out.setdefault(s[1:-1], {})
            continue
        if '=' in s and sec is not None:
            k, v = s.split('=', 1)
            sec[k.strip()] = v.split(';', 1)[0].split('#', 1)[0].strip()
    return out


class TestAppPages(unittest.TestCase):
    """An app's page reaches the board only through apps/lib/appweb.js."""

    def test_pages_use_the_shared_script(self):
        for app in web_apps():
            html = read(os.path.join(APPS, app, 'web.html'))
            with self.subTest(app=app):
                self.assertIn(build_apps.APP_WEB_MARK, html, 'the page must include appweb (<!-- appweb -->)')
                self.assertIsNone(re.search(r'''fetch\(\s*['"`]/api/''', html),
                                  'call the board with appCall / appFile*, never fetch("/api/...") itself')
                self.assertRegex(html, r'\bapp(Call|File|FileWrite|FileDelete)\(')

    def test_appweb_sends_the_page_token(self):
        # the board serves /app?t=<token>: a sandboxed page has no Referer, so
        # without the token a board with a hardware password refuses (401)
        js = read(os.path.join(APPS, 'lib', 'appweb.js'))
        self.assertRegex(js, r"APP_PAGE_TOKEN\s*=\s*new URLSearchParams\(location\.search\)\.get\('t'\)")
        self.assertRegex(js, r"fetch\(appUrl\('/api/app/call\?fn='")
        self.assertRegex(js, r"fetch\(appUrl\('/api/app/file\?'")
        self.assertEqual(len(re.findall(r"fetch\(", js)), 2, 'every request of appweb.js goes through appUrl')

    def test_built_images_carry_the_current_page(self):
        # a stale image (built before appweb.js or web.html changed) would ship an old page
        for app in web_apps():
            want = gzip.decompress(build_apps.web_section(app)[:-12]).decode('utf-8')
            for folder in ('apps', 'dist'):
                path = os.path.join(ROOT, folder, app + '.msbc')
                if not os.path.exists(path):
                    continue
                with self.subTest(app=app, image=folder):
                    with open(path, 'rb') as f:
                        gz = build_apps.read_web(f.read())
                    self.assertIsNotNone(gz, 'the image has no web page section')
                    self.assertEqual(gzip.decompress(gz).decode('utf-8'), want,
                                     'the image is stale: run python tools/build_apps.py ' + app)


class TestAppMetadata(unittest.TestCase):
    def test_identity(self):
        for app in app_ids():
            meta = ini(read(os.path.join(APPS, app, 'meta.ini')))
            with self.subTest(app=app):
                self.assertEqual(meta['app'].get('id'), app)
                self.assertTrue(meta['app'].get('name'))
                self.assertRegex(meta['app'].get('version', ''), r'^\d+$')

    def test_fields_describe_config_keys(self):
        for app in app_ids():
            meta = ini(read(os.path.join(APPS, app, 'meta.ini')))
            fields, config = meta.get('fields', {}), meta.get('config', {})
            for key, spec in fields.items():
                with self.subTest(app=app, key=key):
                    self.assertIn(key, config, 'a [fields] entry needs a default in [config]')
                    parts = [p.strip() for p in spec.split('|')]
                    self.assertGreaterEqual(len(parts), 2, 'type | label | help')
                    kind, default = parts[0], config[key]
                    if kind.startswith('select:'):
                        values = [o.split('=', 1)[0].strip() for o in kind[7:].split(',')]
                        if default:
                            self.assertIn(default, values)
                    elif kind.startswith('number:'):
                        lo, hi = (float(x) for x in kind[7:].split('-', 1))
                        if default:
                            self.assertTrue(lo <= float(default) <= hi, f'{default} not in {lo}..{hi}')
                    elif kind == 'bool':
                        self.assertIn(default, ('', '0', '1'))
                    else:
                        self.assertEqual(kind, 'text')

    def test_index_lists_every_app(self):
        with open(os.path.join(ROOT, 'apps', 'index.json'), encoding='utf-8') as f:
            index = json.load(f)
        entries = index if isinstance(index, list) else index.get('apps', [])
        listed = {e['id']: e for e in entries}
        for app in app_ids():
            meta = ini(read(os.path.join(APPS, app, 'meta.ini')))
            with self.subTest(app=app):
                self.assertIn(app, listed)
                self.assertEqual(str(listed[app].get('version')), meta['app']['version'])


class TestMedicine(unittest.TestCase):
    """The medicine app's contract with the firmware's scheduler."""

    def test_schedule_ini_format(self):
        src = read(os.path.join(APPS, 'medicine', 'medicine.scm'))
        # the firmware reads [schedule] times = HH:MM, HH:MM
        self.assertIn('"[schedule]"', src)
        self.assertIn('"times = "', src)
        self.assertIn('(app-return)', src)
        self.assertIn('(define (app-schedule at)', src)

    def test_needs_api_1_7(self):
        with open(os.path.join(ROOT, 'apps', 'medicine.msbc'), 'rb') as f:
            meta = ini(build_apps.read_meta(f.read()))
        self.assertGreaterEqual(tuple(int(x) for x in meta['app'].get('api', '0').split('.')), (1, 7))   # scheduled launches; 1.8: color schemes


class TestTemplate(unittest.TestCase):
    """docs/app-template/hello, which the guide tells developers to copy, still builds."""
    DIR = os.path.join('docs', 'app-template', 'hello')

    def test_compiles_with_the_libraries(self):
        build_apps.ensure_compiler()
        code = build_apps.compile_sources(build_apps.APP_LIB + [build_apps.APP_WEB_LIB,
                                                                os.path.join(self.DIR, 'hello.scm')])
        self.assertGreater(len(code), 1000)

    def test_page_and_metadata(self):
        html = read(os.path.join(ROOT, self.DIR, 'web.html'))
        self.assertIn(build_apps.APP_WEB_MARK, html)
        self.assertIsNone(re.search(r'''fetch\(\s*['"`]/api/''', html))
        meta = ini(read(os.path.join(ROOT, self.DIR, 'meta.ini')))
        self.assertEqual(meta['app']['id'], 'hello')
        self.assertEqual(len(meta['app']['page_ids'].split(',')), int(meta['app']['pages']))


class TestAppLib(unittest.TestCase):
    """The app library is versioned (apps/lib/applib.scm applib-version, MAJOR.MINOR):
    a released version's files never change, and every app declares one this library serves."""

    def test_every_app_declares_a_served_version(self):
        lib = build_apps.applib_version()
        for a in app_ids():
            need = ini(read(os.path.join(APPS, a, 'meta.ini')))['app'].get('applib', '')
            self.assertRegex(need, r'^\d+\.\d+$', f'{a}: meta.ini [app] applib = MAJOR.MINOR')
            self.assertTrue(build_apps.applib_ok(need, lib), f'{a} needs applib {need}, apps/lib/ is {lib}')

    def test_served_rule(self):
        self.assertTrue(build_apps.applib_ok('1.0', '1.3'))
        self.assertTrue(build_apps.applib_ok('1.3', '1.3'))
        self.assertFalse(build_apps.applib_ok('1.4', '1.3'))
        self.assertFalse(build_apps.applib_ok('1.0', '2.0'))   # a new MAJOR breaks the old apps

    def test_index_lists_the_built_version(self):
        lib = build_apps.applib_version()
        index = json.loads(read(os.path.join(ROOT, 'dist', 'lib', 'index.json')))
        self.assertEqual(index['current'], lib)
        self.assertIn(lib, [v['version'] for v in index['versions']])
        for name in build_apps.LIB_FILES:
            self.assertEqual(read(os.path.join(ROOT, 'dist', 'lib', lib, name)),   # text mode: LF either way
                             read(os.path.join(APPS, 'lib', name)))

    def test_a_released_version_is_not_changed(self):
        """apps/lib/ as released under this version (the newest tag that has it) is what
        it is now: a change needs a new version (CI checks out the tags)."""
        import subprocess
        lib = build_apps.applib_version()
        tags = subprocess.run(['git', 'tag', '--sort=-v:refname'], cwd=ROOT, capture_output=True, text=True).stdout.split()
        for tag in tags:
            changed = []
            for name in build_apps.LIB_FILES:
                r = subprocess.run(['git', 'show', f'{tag}:dist/lib/{lib}/{name}'], cwd=ROOT, capture_output=True)
                if r.returncode != 0:
                    break
                released = r.stdout.decode('utf-8').replace('\r\n', '\n')
                if released != read(os.path.join(APPS, 'lib', name)):
                    changed.append(name)
            else:
                self.assertEqual(changed, [], f'applib {lib} was released in {tag}; {changed} changed since: '
                                              'raise applib-version (MINOR if compatible, else MAJOR)')
                return
        self.skipTest(f'applib {lib} not released yet (or no tags checked out)')


if __name__ == '__main__':
    unittest.main()
