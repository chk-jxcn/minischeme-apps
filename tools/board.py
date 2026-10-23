#!/usr/bin/env python3
"""Develop and debug an app on a real board over its HTTP API (port 80).

    python tools/board.py HOST info                    the board, firmware API, memory
    python tools/board.py HOST install APP [--boot]    upload apps/APP.msbc as /spiffs/apps/APP/app.msbc;
                                                       --boot also makes it the boot app and restarts
    python tools/board.py HOST boot APP                make an installed app the boot app and restart
    python tools/board.py HOST reset                   restart the board
    python tools/board.py HOST exec "(expr)"           compile on the PC, run on the board, print the result
    python tools/board.py HOST shot OUT.png            save the screen (needs Pillow)
    python tools/board.py HOST mem [MINUTES]           (mem-report) and the system heap once a minute
    python tools/board.py HOST market-auto 0|1         market automatic updates off / on
    python tools/board.py COMn log [SECONDS]           print the serial console (needs pyserial)

HOST is the board's IP address (shown on its screen and on the info pages).
A board with a hardware password needs it in the environment variable
MS_PASSWORD (it is sent as the X-MiniScheme-Auth header and never printed).

`exec` runs as the owner (REPL rights, not the app sandbox) between frames on
the board's main loop; it sees the running app's globals. The board has no
compiler: the code is compiled here with tools/compile_to_hex(.exe), which
build_apps.py builds when missing.
"""
import json
import os
import re
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
PASSWORD = os.getenv('MS_PASSWORD', '')


def api(host, path, data=None, timeout=30):
    headers = {'X-MiniScheme-Auth': PASSWORD} if PASSWORD else {}
    req = urllib.request.Request(f'http://{host}{path}', data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        hint = ' (set MS_PASSWORD to the board password)' if e.code in (401, 403) else ''
        sys.exit(f'{path}: HTTP {e.code}{hint}: {e.read()[:200].decode("utf-8", "replace")}')
    try:
        return json.loads(body)
    except ValueError:
        return body


def settings(host, **kv):
    return api(host, '/api/settings', urllib.parse.urlencode(kv).encode())


def wait_up(host, seconds=90):
    time.sleep(6)
    t0 = time.time()
    headers = {'X-MiniScheme-Auth': PASSWORD} if PASSWORD else {}
    while time.time() - t0 < seconds:
        try:
            with urllib.request.urlopen(urllib.request.Request(f'http://{host}/api/info', headers=headers), timeout=3):
                return True
        except urllib.error.HTTPError:
            return True        # it answers (a wrong password is reported by the next call)
        except Exception:
            time.sleep(1)
    return False


def reset(host):
    try:
        api(host, '/api/reset', b'', timeout=5)
    except (SystemExit, Exception):
        pass   # the board may drop the connection while restarting
    print('restarting...', 'up' if wait_up(host) else 'not back after 90 s')


def compile_hex(code):
    sys.path.insert(0, TOOLS)
    import build_apps
    build_apps.ensure_compiler()
    r = subprocess.run([build_apps.COMPILER_EXE, '-'], input=code, capture_output=True, text=True, encoding='utf-8')
    if r.returncode:
        sys.exit('compile error:\n' + r.stderr)
    return bytes.fromhex(r.stdout.strip())


def exec_code(host, code):
    reply = api(host, '/api/exec', compile_hex(code))
    if isinstance(reply, dict) and not reply.get('success', True):
        sys.exit('error: ' + str(reply.get('error')))
    return reply.get('result') if isinstance(reply, dict) else reply


def cmd_info(host):
    info = api(host, '/api/info')
    st = api(host, '/api/stats')
    keys = ('device', 'api', 'ip', 'wifi', 'time_synced', 'uptime_ms', 'gui_mode', 'band_lines')
    print(json.dumps({k: info.get(k) for k in keys}, ensure_ascii=False))
    print(f"VM heap {st.get('vm_heap_allocated')} / {st.get('vm_heap_capacity')} B, system free {st.get('free_heap')} B "
          f"(lowest {st.get('min_free_heap')}, largest block {st.get('largest_block')}), "
          f"render {st.get('render_us')} us, {st.get('busy_pct')}% busy")


def cmd_install(host, app, boot):
    image = os.path.join(ROOT, 'apps', f'{app}.msbc')
    if not os.path.exists(image):
        sys.exit(f'{image} not found: run python tools/build_apps.py {app} first')
    with open(image, 'rb') as f:
        r = api(host, f'/api/upload?run=0&path=/spiffs/apps/{app}/app.msbc', f.read(), timeout=120)
    print('uploaded' if r.get('success') else f'upload failed: {r}')
    if boot and r.get('success'):
        cmd_boot(host, app)


def cmd_boot(host, app):
    print(settings(host, **{'system.boot_app': f'apps/{app}/app.msbc'}))
    reset(host)


def cmd_shot(host, out):
    from PIL import Image

    def unpack(data, width):
        px, i = [], 0
        while len(px) < width and i < len(data):
            c = data[i]
            i += 1
            if c < 128:          # c + 1 literal pixels
                for _ in range(c + 1):
                    px.append(struct.unpack_from('<H', data, i)[0])
                    i += 2
            else:                # one pixel repeated c - 126 times
                v = struct.unpack_from('<H', data, i)[0]
                i += 2
                px.extend([v] * (c - 126))
        return px[:width]

    img, start = None, 0
    for _ in range(200):
        raw = api(host, f'/api/screen?since=0&from={start}')
        if raw[:4] != b'MSCR':
            sys.exit(f'unexpected screen answer: {raw[:60]!r}')
        flags, w, h, count = raw[5], *struct.unpack_from('<HHH', raw, 6)
        img = img or Image.new('RGB', (w, h))
        off, last = 16, start
        for _ in range(count):
            y, n = struct.unpack_from('<HH', raw, off)
            off += 4
            for x, v in enumerate(unpack(raw[off:off + n], w)):
                img.putpixel((x, y), ((v >> 11) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31))
            off += n
            last = y + 1
        if not flags & 1 or count == 0:
            break
        start = last
    img.save(out)
    print('saved', out)


def cmd_mem(host, minutes):
    """vm-live is the VM heap that survives a full collection: if it grows minute
    after minute while the app does the same thing, the app keeps data it should drop.
    free / lowest are the system heap (the firmware's), largest the biggest block."""
    t0 = time.time()
    for _ in range(minutes + 1):
        rep = str(exec_code(host, '(mem-report)'))
        st = api(host, '/api/stats')
        m = re.search(r'\(vm-live \. (\d+)\)', rep)
        print(f'{(time.time() - t0) / 60:5.1f} min  vm-live {m.group(1) if m else rep[:80]}  free {st["free_heap"]}  '
              f'lowest {st["min_free_heap"]}  largest {st["largest_block"]}', flush=True)
        if minutes:
            time.sleep(max(0, 60 - (time.time() - t0) % 60))


def cmd_log(port, seconds):
    import serial
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, 115200, 0.5
    s.dtr = s.rts = False     # opened without toggling the lines: the board is not reset
    s.open()
    t0 = time.time()
    while not seconds or time.time() - t0 < seconds:
        line = s.readline().decode('utf-8', 'replace').rstrip()
        if line:
            print(line, flush=True)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    host, cmd, rest = argv[0], argv[1], argv[2:]
    if cmd == 'info':
        cmd_info(host)
    elif cmd == 'install' and rest:
        cmd_install(host, rest[0], '--boot' in rest)
    elif cmd == 'boot' and rest:
        cmd_boot(host, rest[0])
    elif cmd == 'reset':
        reset(host)
    elif cmd == 'exec' and rest:
        print(exec_code(host, rest[0]))
    elif cmd == 'shot' and rest:
        cmd_shot(host, rest[0])
    elif cmd == 'mem':
        cmd_mem(host, int(rest[0]) if rest else 0)
    elif cmd == 'market-auto' and rest:
        print(settings(host, **{'market.market_auto_update': rest[0]}))
    elif cmd == 'log':
        cmd_log(host, int(rest[0]) if rest else 0)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
