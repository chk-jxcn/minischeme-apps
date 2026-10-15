"""API entries: esp32 (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    # ---- esp32 -------------------------------------------------------------
    api('esp32-mac', 'esp32',
        sig='(esp32-mac)',
        desc='The factory MAC address of the WiFi station as "aa:bb:cc:dd:ee:ff".',
        returns='A string of 17 characters: six lowercase hex byte pairs joined by colons, read from the eFuse '
                '(the same on every boot, a unique device id). Never an error.',
        example='''
(esp32-mac)                     ; e.g. "24:6f:28:a1:b2:c3"
(substring (esp32-mac) 9 17)    ; e.g. "a1:b2:c3"
(define device-id (if (api-has? 'esp32-mac) (esp32-mac) "unknown"))
''',
        where=DEVICE, ext='esp32', check=False,
    ),
    api('esp32-reset-reason', 'esp32',
        sig='(esp32-reset-reason)',
        desc="Why the chip last started: 'power-on, 'software, 'panic, 'watchdog, 'brownout, 'deep-sleep or 'other.",
        returns="A symbol: power-on (power or the reset pin), software ((restart) or a firmware update), panic "
                "(a crash), watchdog (a task or interrupt watchdog), brownout (supply voltage dropped), deep-sleep "
                "(woke from (deep-sleep)), other. Never an error.",
        example='''
(if (memq (esp32-reset-reason) '(panic watchdog brownout))
    (display "restarted after a fault\\n"))
''',
        where=DEVICE, ext='esp32', check=False,
    ),
    api('esp32-idf-version', 'esp32',
        sig='(esp32-idf-version)',
        desc='The ESP-IDF version the firmware was built with, e.g. "v6.1".',
        returns='A string as the ESP-IDF reports it, e.g. "v6.1" (a development build may add a suffix such as '
                '"-dev-123-gabcdef"). Never an error.',
        example='''
(esp32-idf-version)   ; e.g. "v6.1"
''',
        where=DEVICE, ext='esp32', check=False,
    ),
    api('esp32-touch-read', 'esp32',
        sig='(esp32-touch-read pad)',
        desc='Raw value of a capacitive touch pad (0..9); lower when touched.',
        returns='A non-negative integer, the raw charge count of pad T0..T9 (GPIO 4, 0, 2, 15, 13, 12, 14, 27, 33, '
                '32); it drops when a finger is near, so compare it with an untouched reading. The first read of a '
                'pad sets it up. Error "esp32-touch-read: pad must be 0..9".',
        example='''
(define idle (esp32-touch-read 0))
(define (touched?) (< (esp32-touch-read 0) (quotient (* idle 2) 3)))
''',
        status=RESERVED, where=DEVICE, ext='esp32', check=False,
    ),
    api('esp32-psram-size', 'esp32',
        sig='(esp32-psram-size)',
        desc='Bytes of external PSRAM, 0 without.',
        returns='A non-negative integer: the size of the external PSRAM in bytes (e.g. 4194304), 0 on a board '
                'without one. Never an error.',
        example='''
(define big-cache? (> (esp32-psram-size) 0))
''',
        status=RESERVED, where=DEVICE, ext='esp32', check=False,
    ),
]
