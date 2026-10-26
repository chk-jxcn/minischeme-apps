"""The app library's own tests: tests/applib/test_*.scm run on the PC.

tools/run_scheme.c (built here from the minischeme core, as compile_to_hex) compiles
and runs a program in a VM configured like the device's. The program is: a stand-in for
every firmware procedure the PC VM lacks (generated from tools/api/spec: it records the
call in device-calls and answers #f), tests/applib/device.scm (config, files, clock,
screen size), tests/applib/check.scm, the library (apps/lib/ gui, infopages, applib,
appweb; combo too for a test whose first line says ";;; libs: combo") and the test,
which ends with (check-done). Logic only: nothing is drawn.
python -m unittest tests.test_applib -v"""
import glob
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_apps  # noqa: E402

HERE = os.path.join(ROOT, 'tests', 'applib')
RUNNER = os.path.join(ROOT, 'tools', 'run_scheme.exe' if os.name == 'nt' else 'run_scheme')
LIBS = ['gui.scm', 'infopages.scm', 'applib.scm', 'appweb.scm']


def ensure_runner():
    build_apps.ensure_minischeme()
    src = os.path.join(build_apps.MINISCHEME_DIR, 'src')
    c_sources = [os.path.join(src, f) for f in os.listdir(src) if f.endswith('.c')]
    main = os.path.join(ROOT, 'tools', 'run_scheme.c')
    deps = c_sources + [main, os.path.join(ROOT, 'tools', 'msbc.h'), os.path.join(ROOT, 'tools', 'compiler_msbc.h')]
    if os.path.exists(RUNNER) and all(os.path.getmtime(d) <= os.path.getmtime(RUNNER) for d in deps):
        return
    cmd = [build_apps.GCC, '-O2', '-std=c99', '-w', '-DMINISCHEME_NO_MAIN', '-I' + os.path.join(ROOT, 'tools'),
           '-I' + os.path.join(build_apps.MINISCHEME_DIR, 'include'), '-o', RUNNER, main] + c_sources + ['-lm']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('building run_scheme failed:\n' + r.stderr)


def run(program, timeout=120):
    r = subprocess.run([RUNNER], input=program, capture_output=True, text=True, encoding='utf-8', timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


_stubs = None


def stubs():
    """(define (name . args) ...) for every firmware procedure of the spec the PC VM lacks."""
    global _stubs
    if _stubs is None:
        from api.spec import ALL
        # procedures only: the syntax (if, let, define ...) is the compiler's, never a global
        names = sorted({e['name'] for e in ALL if e['component'] != 'syntax'})   # older names (aliases) too
        probe = ("(for-each (lambda (n) (if (not (defined? n)) (begin (display n) (newline)))) '("
                 + ' '.join(names) + '))')
        code, out, err = run(probe)
        if code != 0:
            raise RuntimeError('probing the PC VM failed: ' + err)
        missing = [n for n in out.split() if n]
        _stubs = (';; generated: the firmware procedures the PC VM lacks\n'
                  '(define device-calls \'())\n'
                  '(define (device-call name args) (set! device-calls (cons (cons name args) device-calls)) #f)\n'
                  + ''.join(f"(define ({n} . args) (device-call '{n} args))\n" for n in missing))
    return _stubs


class TestAppLibCode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_runner()

    def test_scheme_files(self):
        files = sorted(glob.glob(os.path.join(HERE, 'test_*.scm')))
        self.assertTrue(files)
        for path in files:
            with self.subTest(os.path.basename(path)):
                test = read(path)
                libs = LIBS + (['combo.scm'] if test.startswith(';;; libs: combo') else [])
                program = '\n'.join([stubs(), read(os.path.join(HERE, 'device.scm')), read(os.path.join(HERE, 'check.scm'))]
                                    + [read(os.path.join(ROOT, 'apps', 'lib', n)) for n in libs] + [test])
                code, out, err = run(program)
                fails = [line for line in out.splitlines() if line.startswith('FAIL')]
                self.assertEqual(code, 0, f'{os.path.basename(path)}: {err.strip()}\n{out[-2000:]}')
                self.assertEqual(fails, [], '\n'.join(fails))
                done = [line for line in out.splitlines() if line.startswith('checks ')]
                self.assertTrue(done, f'{os.path.basename(path)} did not reach (check-done): {out[-500:]}')
                self.assertRegex(done[-1], r'^checks [1-9]\d* failed 0$')


if __name__ == '__main__':
    unittest.main()
