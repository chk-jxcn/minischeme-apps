"""API entries: api, sys, mem, flash, power, time, app, config, setup, bench (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    # ---- api ---------------------------------------------------------------
    api('api-version', 'api',
        sig='(api-version)',
        desc='The API version this firmware provides, "major.minor.patch".',
        returns='A string such as "1.0.0". Never fails.',
        example='''
(api-version) ; => "1.5.0"
''',
    ),
    api('api-compatible?', 'api',
        sig='(api-compatible? required)',
        desc='Whether an app needing API `required` ("1.0") runs here: same major, minor not higher.',
        returns='#t or #f. `required` is "M", "M.m" or "M.m.p" (the patch level never matters); text '
                'that is not a version gives #f; an error when required is not a string.',
        example='''
(api-compatible? "1.0") ; => #t
(api-compatible? "1.9") ; => #f
(api-compatible? "2") ; => #f
''',
    ),
    api('api-has?', 'api',
        sig='(api-has? name)',
        desc='Whether this device provides the procedure (a symbol or string): known to the API, not reserved, its extension present.',
        returns='#t or #f: #f for unknown and reserved names, for names of an extension the device lacks, and '
                'for names not bound here (device-only names in the PC REPL). Older names count like their '
                'current name; special forms are #t. An error when name is not a symbol or string.',
        example='''
(api-has? 'gpio-write) ; => #t
(api-has? "digital-write") ; => #t
(api-has? 'i2c-open) ; => #f
(if (api-has? 'led-set) (led-set 0 0 255))
''',
    ),
    api('api-info', 'api',
        sig='(api-info name)',
        desc='What the API table says about a name: (component since status extension where), or #f.',
        returns='A list ("component" "since" status extension where): status is the symbol stable, reserved '
                'or alias; extension is the extension id string or #f; where is all, device or pc. #f for a '
                'name the API does not know; an error when name is not a symbol or string.',
        example='''
(api-info 'gpio-write) ; => ("gpio" "1.0.0" stable #f all)
(api-info 'millis) ; => ("time" "1.0.0" alias #f all)
(api-info 'i2c-open) ; => ("i2c" "1.0.0" reserved #f all)
(api-info 'no-such-thing) ; => #f
''',
    ),
    api('api-list', 'api',
        sig='(api-list [component])',
        desc='Names of the API (of one component), as strings.',
        returns='A list of strings in alphabetical order, including reserved entries and older names (check '
                'them with api-has? / api-info). An unknown component gives (); an error when component is '
                'not a symbol or string.',
        example='''
(api-list 'button) ; => ("button-pressed?" "button-read")
(length (api-list 'led)) ; => 6
(api-list 'no-such-component) ; => ()
''',
    ),
    api('api-components', 'api',
        sig='(api-components)',
        desc='The component ids, as strings.',
        returns='A list of strings in reference order, the language core first ("syntax" "math" ...). Never fails.',
        example='''
(car (api-components)) ; => "syntax"
(and (member "gpio" (api-components)) #t) ; => #t
''',
    ),
    api('api-extensions', 'api',
        sig='(api-extensions)',
        desc='The extension APIs on this device: (("esp32" . "1.0.0") ...).',
        returns='An alist of (id . version) strings; () on a host without extensions (the PC REPL). The '
                'firmware and the WASM simulator report (("esp32" . "1.0.0")).',
        example='''
(define esp32-api (assoc "esp32" (api-extensions)))   ; ("esp32" . "1.0.0") on the board
(if esp32-api (cdr esp32-api) "none")
''',
    ),
    # ---- sys ---------------------------------------------------------------
    api('sys-restart', 'sys',
        sig='(sys-restart)',
        desc="Reboot the board at once (the REPL reports a timeout; the file manager's restart replies first). Not for apps: only the system settings and the REPL may (an app gets an error).",
        returns='Does not return on the board (esp_restart). The WASM simulator raises the error "restart: the '
                'simulated device is rebooting" and reboots the simulated device; the PC REPL resets its mock '
                'pins and files and returns void.',
        example='''
(config-set! "system" "boot_app" "apps/weather.msbc")
(sys-restart)   ; the board boots the weather app
''',
        check=False,
    ),
    alias('restart', 'sys-restart', 'sys'),
    api('sys-chip-model', 'sys',
        sig='(sys-chip-model)',
        desc='The chip model as a string: model, revision and cores ("ESP32 rev1.0 2C").',
        returns='A string: "ESP32 rev<major>.<minor> <cores>C" on the board, "ESP32 (WASM simulator)" in the '
                'simulator, "PC-Mock-ESP32-Virtual" in the PC REPL. Never fails.',
        example='''
(sys-chip-model)   ; "ESP32 rev1.0 2C" on the reference board
(string? (sys-chip-model)) ; => #t
''',
    ),
    alias('chip-model', 'sys-chip-model', 'sys'),
    api('sys-chip-info', 'sys',
        sig='(sys-chip-info)',
        desc='Alist describing the chip, the firmware build and the flash.',
        returns='An alist. On the board: (model . "ESP32") (revision . n) (cores . n) (cpu-mhz . n) '
                '(wifi-bt . "WiFi+BT") (mac . "AA:BB:CC:DD:EE:FF") (idf . "v6.1") (build . "Oct 10 2026") '
                '(reset-reason . "power-on") (flash-bytes . n) (app-image-bytes . n) (app-partition-bytes . n) '
                'and, with the file system mounted, (spiffs-bytes . n) (spiffs-used . n). reset-reason is one '
                'of "unknown" "power-on" "external" "software" "panic" "int-watchdog" "task-watchdog" "watchdog" '
                '"deep-sleep" "brownout" "sdio". The simulator gives the same keys; the PC REPL only model, cores '
                'and flash-bytes. Never fails.',
        example='''
(define chip (sys-chip-info))
(cdr (assq 'flash-bytes chip)) ; => 4194304
(assq 'reset-reason chip)   ; (reset-reason . "power-on") on the board after power-up
''',
    ),
    alias('chip-info', 'sys-chip-info', 'sys'),
    api('sys-info', 'sys',
        sig='(sys-info)',
        desc='Nested alist of system figures (memory, flash, network, time, VM).',
        returns='An alist of sections (chip memory flash network time display peripherals), each an alist: '
                'chip is sys-chip-info; memory has free-heap largest-block min-free total vm-used vm-heap '
                'app-rom stack-depth frame-depth; flash has total app-image app-partition app-rom '
                'app-rom-partition; network has connected ssid ip rssi; time has ntp-synced uptime-ms; display '
                'has model width height mode band-lines color-bits color-scheme color buffer-bytes '
                'dma-buffer-bytes; peripherals has backlight light-adc light-lux ws2812 button. Never fails.',
        example='''
(map car (sys-info)) ; => (chip memory flash network time display peripherals)
(define (info section key) (cdr (assq key (cdr (assq section (sys-info))))))
(info 'flash 'total) ; => 4194304
(info 'memory 'free-heap)   ; free system RAM, about 33000 on the board
''',
    ),
    alias('system-info', 'sys-info', 'sys'),
    # ---- mem ---------------------------------------------------------------
    api('mem-free', 'mem',
        sig='(mem-free)',
        desc='Free system RAM in bytes (the C heap outside the VM heap: WiFi, HTTP, buffers).',
        returns='An integer (esp_get_free_heap_size; about 33000 on the reference board while an app runs). '
                'The simulator reports a fixed 15076, the PC REPL 4194304. Never fails.',
        example='''
(if (< (mem-free) 16384) (display "low system memory"))
(integer? (mem-free)) ; => #t
''',
    ),
    alias('free-heap', 'mem-free', 'mem'),
    api('mem-total', 'mem',
        sig='(mem-total)',
        desc='Internal RAM managed by the system heap, in bytes.',
        returns='An integer (heap_caps_get_total_size of internal RAM, about 300 KB on the ESP32); the simulator '
                'and the PC REPL report 323584 (316 KB). Never fails.',
        example='''
(quotient (mem-total) 1024)   ; about 300 (KB) on the board
(> (mem-total) 0) ; => #t
''',
    ),
    alias('heap-total', 'mem-total', 'mem'),
    api('mem-min-free', 'mem',
        sig='(mem-min-free)',
        desc='The lowest free system heap since boot, in bytes.',
        returns='An integer (esp_get_minimum_free_heap_size): the low-water mark, never above mem-free. The '
                'simulator reports a fixed 2788, the PC REPL 12288. Never fails.',
        example='''
(define headroom (mem-min-free))   ; 14000..19000 on the board under load
(if (< headroom 8192) (display "the system heap ran low"))
''',
    ),
    alias('min-free-heap', 'mem-min-free', 'mem'),
    api('mem-max-block', 'mem',
        sig='(mem-max-block)',
        desc='Largest free system heap block in bytes: the biggest single C allocation that can succeed now.',
        returns='An integer (heap_caps_get_largest_free_block of 8-bit capable RAM); the simulator reports a '
                'fixed 10240, the PC REPL 28672. Never fails.',
        example='''
(>= (mem-max-block) 4096) ; => #t
''',
    ),
    alias('max-alloc-heap', 'mem-max-block', 'mem'),
    api('mem-report', 'mem',
        sig='(mem-report)',
        desc='Alist of the system heap figures and the free stack of the firmware tasks; collects the VM heap first.',
        returns='An alist of integers: (free-heap . n) (min-free-heap . n) (largest-block . n) (vm-heap . n) '
                '(vm-live . n) after a full VM collection, then (stack-free:<task> . bytes) for each running '
                'task of main, httpd, jsonfeed, mirror_stream, market, tiT, wifi, sys_evt, esp_timer, ipc0, ipc1, IDLE0, IDLE1, '
                'Tmr Svc (the stack high-water mark). Firmware only: the WASM simulator does not provide it.',
        example='''
(define r (mem-report))
(cdr (assq 'free-heap r))          ; e.g. 33012
(assq 'stack-free:httpd r)         ; e.g. (stack-free:httpd . 2340)
''',
        where=DEVICE,
    ),
    # ---- flash -------------------------------------------------------------
    api('flash-total-bytes', 'flash',
        sig='(flash-total-bytes)',
        desc='Flash chip size in bytes.',
        returns='An integer: 4194304 (4 MB) on the reference board and in the simulator. Never fails.',
        example='''
(flash-total-bytes) ; => 4194304
''',
    ),
    api('flash-app-bytes', 'flash',
        sig='(flash-app-bytes)',
        desc='Size of the running firmware image in bytes.',
        returns='An integer: the verified image length of the running partition (the first call hashes the '
                'image, later calls use the cached figure); 0 when the image cannot be verified. The simulator '
                'and the PC REPL report 1078192. Never fails.',
        example='''
(< (flash-app-bytes) (flash-app-partition-bytes)) ; => #t
(- (flash-app-partition-bytes) (flash-app-bytes))   ; room left for a larger firmware
''',
    ),
    api('flash-app-partition-bytes', 'flash',
        sig='(flash-app-partition-bytes)',
        desc='Size of the partition the firmware runs from, in bytes.',
        returns='An integer: 1572864 (the 1536 KB factory partition) on the reference board and in the '
                'simulator; 0 when the running partition is unknown. Never fails.',
        example='''
(flash-app-partition-bytes) ; => 1572864
''',
    ),
    # ---- power -------------------------------------------------------------
    api('power-deep-sleep', 'power',
        sig='(power-deep-sleep ms)',
        desc='Deep sleep for ms milliseconds; the board then reboots.',
        returns='Does not return on the board: everything but the RTC stops, and the timer wakes the chip, '
                'which boots afresh (reset reason "deep-sleep"; RAM and the VM are lost). ms must be a positive '
                'integer; otherwise nothing happens and void is returned. The WASM simulator returns void at '
                'once; the PC REPL blocks for ms.',
        example='''
(app-config-set! "last_run" "done")
(power-deep-sleep 600000)   ; sleep 10 minutes, then boot again
''',
        check=False,
        notes='The display, WiFi and the LED stay off while the chip sleeps; the boot app starts again on wake.',
    ),
    alias('deep-sleep', 'power-deep-sleep', 'power'),
    api('power-light-sleep', 'power',
        sig='(power-light-sleep ms)',
        desc='Pause the CPU for ms with RAM and WiFi kept.',
        returns='The wake cause as a symbol: timer after ms, button when KEY 18 was pressed first. RAM, the VM, '
                'the panel contents and the WiFi association are kept (traffic waits until the wake). An error '
                'when ms is not a positive integer.',
        example='''
(define (app-step)
  (when (eq? (power-light-sleep 5000) 'button)
    (led-set 0 0 255)))
''',
        status=RESERVED,
    ),
    api('power-battery-mv', 'power',
        sig='(power-battery-mv)',
        desc='Battery voltage in millivolts, or #f without a battery.',
        returns='An integer in millivolts read through the board\'s battery divider (calibrated ADC), or #f on '
                'a board without battery sensing (the reference board). Never fails.',
        example='''
(define mv (power-battery-mv))
(if (and mv (< mv 3400)) (gui-text 10 10 "Battery low" (gui-rgb 255 0 0)))
''',
        status=RESERVED,
    ),
    # ---- time --------------------------------------------------------------
    api('time-sleep-ms', 'time',
        sig='(time-sleep-ms ms)',
        desc='Pause the app for ms milliseconds; the app loop (display, button) waits too.',
        returns='Void. On the board the task yields for ms (1 ms tick); ms <= 0 or a non-integer does nothing. '
                'The WASM simulator returns at once without waiting.',
        example='''
(gpio-mode 5 'output)
(gpio-write 5 1)
(time-sleep-ms 100)
(gpio-write 5 0)
''',
        notes='Long pauses freeze the screen and the button; apps should do periodic work in the app-tick or '
              'app-step hooks instead.',
    ),
    alias('delay-ms', 'time-sleep-ms', 'time'),
    api('time-sleep-us', 'time',
        sig='(time-sleep-us us)',
        desc='Busy-wait for us microseconds (short, precise delays).',
        returns='Void. The CPU spins for us (esp_rom_delay_us) without yielding; us <= 0 or a non-integer does '
                'nothing. The WASM simulator returns at once.',
        example='''
(gpio-mode 5 'output)
(gpio-write 5 1)
(time-sleep-us 10)   ; a 10 us pulse
(gpio-write 5 0)
''',
    ),
    alias('delay-us', 'time-sleep-us', 'time'),
    api('time-ms', 'time',
        sig='(time-ms)',
        desc='Milliseconds since boot (the page load in the simulator).',
        returns='An exact integer, never negative or wrapped: a bignum past the fixnum range (2^28 ms, about 3.1 days of uptime, on 32-bit targets). Never fails.',
        example='''
(define start (time-ms))
(define (elapsed-ms) (- (time-ms) start))
(>= (elapsed-ms) 0) ; => #t
''',
    ),
    alias('millis', 'time-ms', 'time'),
    api('time-us', 'time',
        sig='(time-us)',
        desc='Microseconds since boot, for timing short intervals.',
        returns='An exact integer, never negative or wrapped: a bignum past the fixnum range (2^28 us, about 4.5 minutes, on 32-bit targets; reading a bignum allocates a few bytes). Never fails.',
        example='''
(define t0 (time-us))
(define x (expt 3 40))
(- (time-us) t0)   ; microseconds the computation took
''',
    ),
    alias('micros', 'time-us', 'time'),
    api('time-synced?', 'time',
        sig='(time-synced?)',
        desc='Whether the wall clock has been set (NTP).',
        returns='#t once SNTP has set the clock (time after November 2023), #f before. The simulator and the '
                'PC REPL use the host clock and give #t. Never fails.',
        example='''
(define (status-text) (if (time-synced?) "clock set" "waiting for NTP"))
(boolean? (time-synced?)) ; => #t
''',
        notes='The firmware syncs from ntp.aliyun.com and cn.pool.ntp.org once WiFi is up; the local time zone '
              'is CST-8. The app-tick hook receives the wall time each second.',
    ),
    api('time-epoch', 'time',
        sig='(time-epoch)',
        desc='Seconds since 1970-01-01 UTC, or #f before the clock is set.',
        returns='An exact integer (a bignum on 32-bit targets, where fixnums end at 2^28), or #f while '
                'time-synced? is #f. Never fails.',
        example='''
(define t (time-epoch))
(if t (app-config-set! "last_seen" (number->string t)))
''',
        status=RESERVED,
    ),
    api('time-local', 'time',
        sig='(time-local)',
        desc='The local time: (year month day hour minute second weekday), or #f.',
        returns='A list of 7 integers in the device\'s time zone: month 1..12, day 1..31, hour 0..23, '
                'weekday 0..6 with 0 = Sunday; #f while the clock is not synced. Never fails.',
        example='''
(define now (time-local))   ; e.g. (2026 10 10 14 30 5 6)
(if now (string-append (number->string (list-ref now 3)) ":" (number->string (list-ref now 4))))
''',
        where=DEVICE,
        since='1.7.0',
        notes='The wall time of the last app-tick (once a second), so it can lag the clock by up to a second. '
              'Use it for the year, or to count days (an every-other-day plan). Check it with '
              '(defined? \'time-local) on older firmware.',
    ),
    api('time-utc-offset', 'time',
        sig='(time-utc-offset)',
        desc='Offset of the local time zone from UTC in seconds.',
        returns='An integer, seconds east of UTC at the current time (daylight saving included): 28800 for '
                '"CST-8", the firmware default. Never fails.',
        example='''
(quotient (time-utc-offset) 3600)   ; 8 with the default zone
''',
        status=RESERVED,
    ),
    api('time-set-zone!', 'time',
        sig='(time-set-zone! tz)',
        desc='Set the local time zone (POSIX TZ string such as "CST-8").',
        returns='#t; the zone applies at once to time-local, time-utc-offset and the app-tick wall time and is '
                'kept in config.ini [system] timezone for the next boot. An error when tz is not a string or '
                'not a valid POSIX TZ string.',
        example='''
(time-set-zone! "CET-1CEST,M3.5.0,M10.5.0/3")
(time-utc-offset)   ; 3600 in winter, 7200 in summer
''',
        status=RESERVED,
    ),
    # ---- app ---------------------------------------------------------------
    api('app-rom-capacity', 'app',
        sig='(app-rom-capacity)',
        desc="Bytes of the approm flash partition that holds the app's Code ROM image (vm-rom-bytes is the image); 0 when there is none.",
        returns='An integer: 262144 (one 256 KB slot of the approm partition: 512 KB in two slots since firmware 1.0.71) on the reference board, in the simulator and '
                'the PC REPL; 0 on a firmware whose partition table has no approm. Never fails.',
        example='''
(app-rom-capacity) ; => 262144
(<= (vm-rom-bytes) (app-rom-capacity)) ; => #t
''',
    ),
    api('app-last-stats', 'app',
        sig='(app-last-stats)',
        desc='Figures of the app that ran before the system settings opened (kept across that restart), or #f.',
        returns='#f when no app was recorded (after power-up), else an alist: (id . "weather") (heap . n) '
                '(live . n) (peak . n) (rom . n) (uptime-s . n) (free-heap . n) (min-free . n) in bytes and '
                'seconds, plus (phase . rom|load|crash) (error . "text") when the app failed. Kept in RTC RAM: '
                'survives a restart, not a power cycle. The simulator reports 0 for uptime-s, free-heap and '
                'min-free.',
        example='''
(define s (app-last-stats))
(if s (cdr (assq 'peak s)) 0)        ; e.g. 61240: the app's peak live VM heap
(and s (assq 'error s))              ; e.g. (error . "car: expected a pair")
''',
        where=DEVICE,
    ),
    alias('last-app-stats', 'app-last-stats', 'app', where=DEVICE),
    api('app-info', 'app',
        sig='(app-info)',
        desc='The running app: (path id ini-path folder).',
        returns='A list of four strings: the app image, its id (from its metadata, else its folder), its '
                'settings file <folder>/config.ini and its folder (/spiffs/apps/<id> or /spiffs/user/<id>, '
                'where its files go). In the system settings: id "settings". Never fails.',
        example='''
(app-info)   ; e.g. ("/spiffs/apps/calendar/app.msbc" "calendar" "/spiffs/apps/calendar/config.ini" "/spiffs/apps/calendar")
(define app-id (cadr (app-info)))
''',
        where=DEVICE,
    ),
    api('app-list', 'app',
        sig='(app-list)',
        desc='The installed apps with their metadata: ((path id name description pages version) ...).',
        returns='A list with one list per app: path, id, name (the id when the metadata has none), description '
                'and version are strings ("" when missing), pages an integer (1 when missing). The apps of '
                '/spiffs/apps/<id>/ (the market) and /spiffs/user/<id>/ (uploaded) come first, then the built-in '
                '/spiffs/app.msbc unless the same id is installed from the market; never the system settings; at '
                'most 16 apps. () when none. Never fails.',
        example='''
(map cadr (app-list))   ; e.g. ("calendar" "weather")
(for-each (lambda (a) (display (list-ref a 2)) (newline)) (app-list))
''',
        where=DEVICE,
    ),
    api('app-scheduled', 'app',
        sig='(app-scheduled)',
        desc="The time this run is for, \"HH:MM\": a launch from the app's schedule.ini, or the time its app-schedule hook was called with; #f otherwise.",
        returns='A string "HH:MM" or #f. Never fails.',
        example='''
(if (app-scheduled) (show-reminder) (show-normal))
''',
        where=DEVICE,
        since='1.7.0',
        notes='An app with schedule.ini in its folder ([schedule] times = 08:00, 12:30, 19:00) is started by the '
              'system at those times (wall clock, once synced): the board restarts into it, and (app-scheduled) '
              'tells it why it runs. When the app is already running at such a time it is not restarted: its '
              'app-schedule hook, (define (app-schedule at) ...), is called with the time instead (no hook: '
              'nothing happens). Several apps due at the same time run one after another. A scheduled launch '
              'stays until it calls (app-return), or for return_after seconds when its schedule.ini sets it. '
              'The app (or its web page, through /api/app/file?name=schedule.ini) writes schedule.ini itself.',
    ),
    api('app-return', 'app',
        sig='(app-return)',
        desc='A scheduled launch is done: the next app due at that time, else the boot app, starts after this call (#t); #f when there is nothing to return to.',
        returns='#t when a restart follows (within a second; the app keeps running until then), #f when this '
                'run is not a scheduled launch and no other launch waits. Clears (app-scheduled) then. Never fails.',
        example='''
(define (all-confirmed) (if (not (app-return)) (show-normal)))
''',
        where=DEVICE,
        since='1.7.0',
        notes='The boot app ([system] boot_app) is the app the board ran before the launch. An app that handled '
              'its app-schedule hook while running as the boot app calls (app-return) too: other apps due at '
              'the same time wait for it, then run (#t); with none waiting it stays (#f).',
    ),
    # ---- config ------------------------------------------------------------
    api('config-get', 'config',
        sig='(config-get key [app-id])',
        desc="Value of a key in the running app's own config.ini (its folder), else in /spiffs/config.ini, as a string; #f when neither has it. app-id: a member of the running combined app.",
        returns='A string (trimmed, comment removed, at most 159 bytes) or #f. The key is matched without case '
                'in any section; the first match wins. An error when key is not a string.',
        example='''
(config-get "proxy")                  ; e.g. "http://192.168.1.10:8087"
(define city (or (config-get "city") "Beijing"))
(string->number (or (config-get "backlight") "220"))
''',
        where=DEVICE,
        notes="An app's defaults ([config] of its metadata) are written to its config.ini when it first runs, so "
              'config-get finds them there; the settings web page edits the same file. An app gets no secrets of '
              'config.ini: wifi_* keys, boot_app and keys containing password, passwd, secret or token answer #f '
              '(the system settings and the REPL get them). Since 1.6.0 a combined app (meta [combo] members = '
              'a, b) passes a member\'s id to read that app\'s own config.ini (apps/<id>/, else user/<id>/); '
              'another id is an error. Firmware before 1.6.0 ignores app-id.',
    ),
    api('app-has-config?', 'config',
        sig='(app-has-config? app-id)',
        desc="Whether a member of the running combined app ([combo] members) has its own config.ini.",
        returns='#t or #f. An error when app-id is not a member of the running combined app.',
        example='''
(if (app-has-config? "weather") (config-get "city" "weather") "Beijing")
''',
        where=DEVICE,
        since='1.6.0',
        notes='A member that never ran on its own and was never set up has no config.ini: the combined app then '
              'uses the defaults of that member\'s metadata. Check it with (defined? \'app-has-config?) on older '
              'firmware.',
    ),
    api('config-set!', 'config',
        sig='(config-set! section key value)',
        desc='Write key = value into /spiffs/config.ini (the line replaced in place with its comment kept, else added to [section]); #t when saved. Read again at the next boot.',
        returns='#t when the file was written, #f when it could not be (out of memory, file system full). '
                'Most settings take effect at the next boot. An error when section, key or value is not a '
                'string.',
        example='''
(config-set! "system" "boot_app" "apps/weather/app.msbc") ; => #t
(config-get "boot_app") ; => "apps/weather/app.msbc"
''',
        where=DEVICE,
        notes='An existing key is found in any section and replaced where it is; the file is rewritten through '
              'a temporary file. Values are stored as text: pass numbers with number->string. Not for apps: only the system settings and the REPL may (an app gets an error). An app '
              'keeps its own settings with app-config-set!.',
    ),
    api('app-config-set!', 'config',
        sig='(app-config-set! key value)',
        desc="Store a setting in the running app's own config.ini ([config] section, in its folder).",
        returns='#t when saved, #f when the file could not be written. config-get reads it back at once. An '
                'error when key or value is not a string.',
        example='''
(app-config-set! "city" "Shanghai") ; => #t
(config-get "city") ; => "Shanghai"
''',
        where=DEVICE,
    ),
    # ---- setup -------------------------------------------------------------
    api('setup-mode-start', 'setup',
        sig='(setup-mode-start)',
        desc='Start the setup access point and its web page. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='(ssid ip) strings of the open access point, such as ("MiniScheme-A1B2" "192.168.4.1"), or #f '
                'when it could not start. Starting it again returns the running one. A station that is not '
                'connected stops retrying while the access point runs.',
        example='''
(define ap (setup-mode-start))
(if ap (gui-text 10 40 (string-append "Join " (car ap)) (gui-rgb 255 255 255)))
''',
        where=DEVICE,
        notes='The access point has no password; a captive DNS sends every name to the setup page, which edits '
              'WiFi and config.ini settings.',
    ),
    api('factory-reset', 'setup',
        sig='(factory-reset what)',
        desc="Reset part of the board from the system settings: 'rom (the app Code ROM partition), 'configs (the "
             "apps' /spiffs/apps/<id>.ini), 'fonts (the system font ROM), 'files (every file: apps, data, "
             "config.ini, WiFi) or 'all (the Code ROM and every file; the font ROM stays).",
        returns='#t, and the board restarts 1.5 s later into the built-in system settings (never a copy from the '
                'market); a string saying why when it cannot ("factory-reset: only in the system settings"). '
                'A symbol other than the five is an error.',
        example='''
(factory-reset 'configs)   ; => #t, then the restart
''',
        since='1.1.0', where=DEVICE, check=False,
        notes='Holding KEY 18 from power-on for 10 s (config.ini [system] factory_reset_key = 1) erases the Code ROM '
              'and opens the built-in settings too. After \'files or \'all the firmware writes a default config.ini '
              'on the next boot; WiFi has to be set up again (setup mode).',
    ),
    api('setup-mode-status', 'setup',
        sig='(setup-mode-status)',
        desc='The state of setup mode and the WiFi station, as an alist.',
        returns='An alist: (ap . #t/#f) (ap-ssid . "MiniScheme-A1B2") (ap-ip . "192.168.4.1") (clients . n) '
                '(sta-connected . #t/#f) (sta-ssid . "...") (sta-ip . "...") (saved . n), where clients counts '
                'the phones joined to the access point and saved the settings saved from the page since boot. '
                'Never fails.',
        example='''
(define st (setup-mode-status))
(cdr (assq 'clients st))   ; phones joined to the setup hotspot
(cdr (assq 'sta-connected st))
''',
        where=DEVICE,
    ),
    # ---- market ---------------------------------------------------------------
    api('market-refresh', 'market',
        sig='(market-refresh)',
        desc='Start reading the market index in the background; (market-status) follows it, (market-apps) has the result.',
        returns='#t when the read started; otherwise a string saying why ("market: busy", "market: not connected", '
                '"market: no market_url and no proxy in config.ini"). Never an error.',
        example='''
(market-refresh)                      ; => #t
(eq? (cdr (assq 'state (market-status))) 'refreshing)   ; => #t, until the index arrived
''',
        notes='The market is `config.ini [market] market_url`, else `<[app] proxy>/market` (tools/app_proxy.py serves '
              'web_repl/apps there). Its index.json lists every app with id, name, description, version, api, '
              'extensions, file, size and hash (FNV-1a of the image). The board fetches over plain HTTP. '
              'Automatic updates (`[market] market_auto_update = 1`): an app\'s boot checks once when the '
              'network comes up (within 30 s); with updates the device restarts into the system settings, '
              'installs them and restarts into the app. No network at boot or a failed check: skipped until '
              'the next boot, never retried.',
        since='1.1.0', where=DEVICE, check=False,
    ),
    api('market-status', 'market',
        sig='(market-status)',
        desc='What the market does now: an alist of state, message, app, received, total, queued, install, auto, return and url.',
        returns='((state . s) (message . str) (app . id-or-#f) (received . bytes) (total . bytes) (queued . n) (install . #t/#f) (auto . a) (return . #t/#f) (url . str)); state is idle, refreshing, installing or error; message is the last outcome in English ("5 apps, 1 updates", "weather 2 installed", "auto update: 1 installed, 0 failed"); install: whether installs may run now (on the board only in the system settings); auto: the automatic round of this boot, off, check (an app\'s boot check) or update (the settings installing the updates it found); return: that round is over and the settings go back to the app. Never an error.',
        example='''
(define st (market-status))
(cdr (assq 'state st))      ; => installing
(cdr (assq 'app st))        ; => "weather"
(quotient (* 100 (cdr (assq 'received st))) (max 1 (cdr (assq 'total st))))   ; percent
''',
        since='1.1.0', where=DEVICE, check=False,
    ),
    api('market-apps', 'market',
        sig='(market-apps)',
        desc='The apps of the last index read, each compared with the installed copy.',
        returns="A list of (id name version installed status size description): installed is the installed "
                "copy's version or #f; status is new, installed (same image), update (another image, not an older "
                "version) or incompatible (needs a newer API or an extension this device lacks). () before a refresh.",
        example='''
(for-each (lambda (a) (display (list (car a) (list-ref a 4))) (newline)) (market-apps))
; ("calendar" installed)
; ("weather" update)
''',
        since='1.1.0', where=DEVICE, check=False,
    ),
    api('market-install', 'market',
        sig='(market-install id)',
        desc="Queue the install of an app (a string id), or 'updates for every app with an update; downloads run in the background.",
        returns='The number of apps queued; a string saying why when none is ("market: install and update apps in the system settings" while an app runs on the board, "market: no app x", "market: no updates", "market: refresh the list first", or an incompatible app). Never an error. Each image goes to a temporary file, is checked (size, hash, image, API) and only then replaces the installed file (/spiffs/apps/<id>.msbc, or the root app.msbc when that is the installed copy); the apps run the new version from the next boot.',
        example='''
(market-refresh)
;; ... once (market-status) says idle:
(market-install "weather")    ; => 1
(market-install 'updates)     ; => 2, or "market: no updates"
''',
        since='1.1.0', where=DEVICE, check=False,
    ),
    api('market-cancel', 'market',
        sig='(market-cancel)',
        desc='Stop the read or download in progress and empty the install queue; the installed files are untouched.',
        returns='#t.',
        example='''
(market-cancel)   ; => #t
''',
        since='1.1.0', where=DEVICE, check=False,
    ),
    # ---- bench -------------------------------------------------------------
    api('bench-tick', 'bench',
        sig='(bench-tick [n])',
        desc='Average time of n synthetic clock ticks with a partial redraw to the LCD; diagnostic.',
        returns='An alist of averages per tick: (tick-us . n) (alloc-bytes . n) (minor-gcs . total). n is '
                'clamped to 1..600, default 60; the screen is repainted afterwards. Firmware only: the WASM '
                'simulator does not provide it.',
        example='''
(bench-tick 60)   ; e.g. ((tick-us . 8420) (alloc-bytes . 312) (minor-gcs . 4))
''',
        where=DEVICE,
        notes='Runs the app-tick hook with fixed times (14:00:01 ...): the app shows them until its next real tick.',
    ),
    alias('tick-bench', 'bench-tick', 'bench', where=DEVICE),
    api('bench-display', 'bench',
        sig='(bench-display [n [y h [replay?]]])',
        desc='Time n renders of the screen (or rows y..y+h) through the LCD path; diagnostic.',
        returns='An alist of averages per pass: (full-render-us . n) (lcd-us . n) (alloc-bytes . n). n is '
                'clamped to 1..600, default 10. With replay? true the recorded drawing is replayed instead of '
                're-running the render procedure (the cost of a scrolling-text frame). Firmware only: the WASM '
                'simulator does not provide it.',
        example='''
(bench-display 10)         ; e.g. ((full-render-us . 61000) (lcd-us . 24000) (alloc-bytes . 0))
(bench-display 20 0 40 #t)  ; the top 40 rows, replayed
''',
        where=DEVICE,
    ),
    alias('display-bench', 'bench-display', 'bench', where=DEVICE),
]
