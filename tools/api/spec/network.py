"""API entries: wifi, json-feed, http, mqtt (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

JSON_FEED_NOTES = '''\
**Model.** One feed per device. On the board a background task fetches the URL
with an HTTP GET (redirects are not followed; timeout: interval-ms clamped to
3..15 s) and streams the response through a JSON scanner: the document itself
is never held in RAM. A failed fetch is retried within 5 s, a good one after
interval-ms (at least 200 ms). The WASM simulator fetches for the feed through
the page (minischeme-webrepl server.py serves the app proxy's `/app/` routes); the PC REPL
and the test VM have no fetcher, so their feed never gets a document. A new
`json-feed-start` replaces the whole configuration and the board fetches the
new URL at once (an app switching pages); documents of an older configuration
are never shown: `json-feed-seq` returns 0 until the first document of the new
one is taken.

**Capture.** `keys` names any number of keys of any length; key k is the
k-th name. Every JSON object nested at most `depth` objects deep (the
top-level object is depth 1; arrays do not count; no depth: every level) is
scanned for those keys; their scalar values are captured as text: strings
unescaped (UTF-8), numbers, `true`, `false` and `null` as written. With a
value-len, at most that many bytes of a value are kept (cut at a UTF-8
character boundary); without one, values are kept whole. Objects and arrays
are not values.

**Selection.** A selector is `(key-index mode string [keep-key ...])`, mode
`'equal` or `'prefix`; there may be any number of them. A captured object
becomes a row when the value of key key-index equals (or starts with) the
string; the first matching selector wins and `(json-feed-selector i)` tells
which. The optional keep-keys limit the values stored for that row (all
captured keys when omitted): `(0 equal "error" 1)` keeps only key 1.
`(0 prefix "")` keeps every object that has key 0. A document keeps any
number of rows; with a pool-bytes, at most that much value text. When rows or
text do not fit (pool-bytes, or memory: on the board the feed leaves 16 KB of
heap free for the system) the status reports `truncated` #t. A document in
which no object had a captured key counts as a failed fetch ("no matching JSON
objects in the response").

**Reading.** `(json-feed-seq)` takes the newest complete document; `count`,
`field`, `ints` and `selector` then read that document, unchanged until a later
`json-feed-seq` takes the next one. Call it once per tick and redraw when the
number changes. `field` and `ints` take a key's index or (since 1.2.0) its name.

**With the app proxy.** The app proxy (minischeme-proxy) turns web APIs into flat documents
`{"items":[{"t":type,"a":..,"b":..,"c":..,"d":..,"e":..}]}` with series as
comma-separated integers; an app may name more keys (applib `app-keys!`).
apps/lib/applib.scm starts the feed with
`(json-feed-start url interval APP-KEYS '((0 prefix "")) 0 0 2)` and reads
every row with `json-feed-field` (`json-feed-ints` for series).

**Memory.** Nothing has a fixed size: the scanner's buffers (one per nesting
level), two snapshots (the one being filled and the one being read) and the
selectors are allocated as a feed needs them and kept for the next document.
`(json-feed-status)` reports the bytes held (`memory`). Until 1.2.0 a feed had
at most 6 keys of 23 bytes, 40 selectors, 64 rows, 16 KB of text, values of
255 bytes, 8 levels and a 255-byte URL.'''

APIS = [
    # ---- wifi --------------------------------------------------------------
    api('wifi-connect', 'wifi',
        sig='(wifi-connect ssid password)',
        desc='Join a WiFi network as a station. The connection completes in the background and is retried automatically when it drops. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='#t when the attempt has started (poll `(wifi-connected?)` for the link); #f when ssid is empty, '
                'an argument is not a string or the WiFi driver failed to start. Never an error. The board joins the '
                'network of config.ini at boot by itself.',
        example='''
(wifi-connect "home-ap" "secret123")   ; => #t
(let wait ((n 0))
  (if (and (not (wifi-connected?)) (< n 100))
      (begin (delay-ms 100) (wait (+ n 1)))))
(wifi-connected?)
''',
    ),
    alias('wifi-status', 'wifi-connected?', 'wifi'),
    api('wifi-ap', 'wifi',
        sig='(wifi-ap ssid password)',
        desc='Start a WiFi access point beside the station (address 192.168.4.1); a password under 8 characters makes it open. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='#t when the access point is up; #f when ssid is empty, an argument is not a string or the driver '
                'refused. Never an error. The station keeps its connection.',
        example='''
(wifi-ap "minischeme-setup" "")   ; => #t
''',
    ),
    api('wifi-connected?', 'wifi',
        sig='(wifi-connected?)',
        desc='Whether the station is connected and has an IP address.',
        returns='#t or #f. Never an error.',
        example='''
(define (ip-label) (if (wifi-connected?) (wifi-ip) "offline"))
(wifi-disconnect)
(ip-label)   ; => "offline"
''',
    ),
    api('wifi-disconnect', 'wifi',
        sig='(wifi-disconnect [reconnect?])',
        desc='Disconnect the station and stop the automatic reconnect; with #t the link drops and reconnects at once. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='Void. Never an error. The reconnect? argument is honored by the firmware only; the simulator and '
                'the PC mocks just disconnect.',
        example='''
(wifi-disconnect)
(wifi-connected?)   ; => #f
(wifi-ip)           ; => "0.0.0.0"
''',
    ),
    api('wifi-ip', 'wifi',
        sig='(wifi-ip)',
        desc='The station IP address as a dotted string.',
        returns='A string such as "192.168.1.42"; "0.0.0.0" while not connected. Never an error.',
        example='''
(define (ip-line) (string-append "IP " (wifi-ip)))
(wifi-disconnect)
(ip-line)   ; => "IP 0.0.0.0"
''',
    ),
    api('wifi-rssi', 'wifi',
        sig='(wifi-rssi)',
        desc='Signal strength of the connected network in dBm.',
        returns='A negative integer such as -52 (dBm; closer to 0 is stronger); 0 while not connected. Never an error.',
        example='''
(define (wifi-bars)
  (let ((r (wifi-rssi)))
    (cond ((= r 0) 0) ((> r -55) 3) ((> r -70) 2) (else 1))))
(wifi-disconnect)
(wifi-bars)   ; => 0
''',
    ),
    api('wifi-ssid', 'wifi',
        sig='(wifi-ssid)',
        desc='The SSID of the connected network.',
        returns='A string; "" while not connected. Never an error.',
        example='''
(define (network-name) (let ((s (wifi-ssid))) (if (string=? s "") "-" s)))
(wifi-disconnect)
(network-name)   ; => "-"
''',
    ),
    # ---- json-feed ---------------------------------------------------------
    api('json-feed-start', 'json-feed',
        sig='(json-feed-start url interval-ms keys selectors [pool-bytes [value-len [depth]]])',
        desc="Poll a JSON URL in the background; keep objects whose captured key matches a selector (key-index 'equal|'prefix string). A new call replaces the feed and fetches at once. An https:// URL goes through the protocol converter (config.ini [app] https_proxy, else proxy) as <it>/fetch?url=...; the board's own address is refused.",
        returns='#t once the feed is configured. Errors: "json-feed-start: expected url interval-ms keys selectors '
                '..." (url not a string, interval-ms not an integer), "keys must be strings", "selector must be '
                '(key-index \'equal|\'prefix string)" (key-index not a key, another mode), "out of memory". '
                'interval-ms under 200 counts as 200. pool-bytes (value text per document), value-len (bytes per '
                'value) and depth (nesting levels captured) are limits the app chooses: omitted, 0 or #f means none '
                '(since 1.2.0; before, they were clamped to 256..16384, 16..256 and 1..8 with defaults 1536, 40 and 8). '
                'Any number of keys and selectors, of any length.',
        notes=JSON_FEED_NOTES,
        example='''
(json-feed-start "http://192.168.1.10:8087/app/news?cat=finance" 300000
                 '("t" "a" "b")
                 '((0 equal "news") (0 equal "error" 1))
                 2048 128 2)   ; => #t
(json-feed-url)   ; => "http://192.168.1.10:8087/app/news?cat=finance"
''',
    ),
    api('json-feed-ints', 'json-feed',
        sig='(json-feed-ints i k)',
        desc='Integers of a comma-separated value of row i, key k: "12,-3,7" => (12 -3 7), or #f.',
        returns='A list of integers (any number; a part without digits is skipped, "2.5" counts as 2); () for an '
                'empty value; #f when row i or its key k does not exist in the taken document. k is an index or '
                '(since 1.2.0) a key name. Never an error.',
        example='''
;; a proxy row {"t":"temp","a":"Mon","b":"12,15,9,-3"} gives (12 15 9 -3)
(define (series i) (or (json-feed-ints i 2) '()))
(json-feed-start "http://192.168.1.10:8087/app/weather?loc=auto" 600000
                 '("t" "a" "b") '((0 prefix "")))
(series 0)   ; => ()
''',
    ),
    api('json-feed-stop', 'json-feed',
        sig='(json-feed-stop)',
        desc='Stop polling: the fetcher idles. The document already taken stays readable.',
        returns='Void. Never an error.',
        example='''
(json-feed-start "http://192.168.1.10:8087/app/ping" 60000 '("t") '((0 prefix "")))
(json-feed-stop)
(json-feed-url)                            ; => #f
(cdr (assq 'state (json-feed-status)))     ; => idle
''',
    ),
    api('json-feed-seq', 'json-feed',
        sig='(json-feed-seq)',
        desc='Take the newest complete document, if one arrived; returns its number (0 = none yet).',
        returns='An integer: the number of the document now readable (one higher per document taken); 0 while the '
                'current feed (since the last json-feed-start) has no document. Never an error.',
        example='''
(define last-seq 0)
(define (feed-poll! redraw)
  (let ((seq (json-feed-seq)))
    (if (and (> seq 0) (not (= seq last-seq)))
        (begin (set! last-seq seq) (redraw)))))
(json-feed-start "http://192.168.1.10:8087/app/ping" 60000 '("t") '((0 prefix "")))
(json-feed-seq)   ; => 0
''',
    ),
    api('json-feed-count', 'json-feed',
        sig='(json-feed-count)',
        desc='Rows (selected objects) of the taken document.',
        returns='An integer, 0 or more; 0 before the current feed has a document. Never an error.',
        example='''
(define (feed-titles)
  (let loop ((i (- (json-feed-count) 1)) (acc '()))
    (if (< i 0) acc (loop (- i 1) (cons (json-feed-field i 1) acc)))))
(json-feed-start "http://192.168.1.10:8087/app/news?cat=finance" 300000
                 '("t" "a") '((0 equal "news")))
(feed-titles)   ; => ()
''',
    ),
    api('json-feed-selector', 'json-feed',
        sig='(json-feed-selector i)',
        desc='Index of the selector that row i matched.',
        returns='An integer (0 for the first selector of json-feed-start); #f when row i does not exist in the '
                'taken document. Never an error.',
        example='''
(define (row-kind i)
  (case (json-feed-selector i) ((0) 'news) ((1) 'error) (else #f)))
(json-feed-start "http://192.168.1.10:8087/app/news?cat=finance" 300000
                 '("t" "a") '((0 equal "news") (0 equal "error")))
(row-kind 0)   ; => #f
''',
    ),
    api('json-feed-field', 'json-feed',
        sig='(json-feed-field i k)',
        desc='Captured value of key k (an index into keys, or since 1.2.0 a key name) for row i, as a string, or #f.',
        returns='A string: the value as text (strings unescaped, numbers and true/false/null as written), whole or '
                'at most value-len bytes; #f when row i does not exist, the object lacked key k (or k names no key), '
                'or the selector did not keep it. Never an error.',
        example='''
;; row {"t":"news","a":"Markets rally","b":"10:42"}: (json-feed-field i 1) => "Markets rally"
(define (field-or i k default) (or (json-feed-field i k) default))
(json-feed-start "http://192.168.1.10:8087/app/news?cat=finance" 300000
                 '("t" "a" "b") '((0 equal "news")))
(field-or 0 1 "(loading)")   ; => "(loading)"
;; by name, the same key as index 1:
(json-feed-field 0 "a")      ; => #f
''',
    ),
    api('json-feed-url', 'json-feed',
        sig='(json-feed-url)',
        desc='The URL being polled, or #f.',
        returns='A string: the URL of the last json-feed-start; #f before any or after json-feed-stop. Never an error.',
        example='''
(json-feed-start "http://192.168.1.10:8087/app/ping" 60000 '("t") '((0 prefix "")))
(json-feed-url)   ; => "http://192.168.1.10:8087/app/ping"
''',
    ),
    api('json-feed-status', 'json-feed',
        sig='(json-feed-status)',
        desc='Feed state as an alist: state, error, fetches, failures, bytes, fetch-ms, age-ms, objects, truncated, memory.',
        returns="An alist in this order: (state . idle|connecting|ok|error), (error . message of the last failed "
                'fetch, "" after a good one: "WiFi not connected", "cannot connect", "HTTP status 404", "read error '
                'after N bytes", "no matching JSON objects in the response"), (fetches . n) and (failures . n) since '
                'boot, (bytes . size of the last response), (fetch-ms . duration of the last fetch, board only, else '
                '0), (age-ms . ms since the last good document, -1 if none), (objects . objects with a captured key '
                'in the taken document), (truncated . #t when rows or value text did not fit: pool-bytes, value-len or '
                'memory), (memory . bytes the feed holds, since 1.2.0). Never an error.',
        example='''
(define (feed-stat key) (cdr (assq key (json-feed-status))))
(json-feed-start "http://192.168.1.10:8087/app/ping" 60000 '("t") '((0 prefix "")))
(feed-stat 'state)    ; => connecting
(feed-stat 'age-ms)   ; => -1
''',
    ),
    api('json-feed-dump', 'json-feed',
        sig='(json-feed-dump)',
        desc='Every object of a document with captured keys, values joined by TAB, one per line.',
        returns='A string (as long as the document needs, memory permitting): one line per object that had any '
                'captured key, selected or not, its values in key order joined by TAB. On the board it waits up to 6 s for the next fetched document; '
                'the simulator lists the last one. #f when no document came (or no feed was started). Never an error.',
        example='''
(json-feed-start "http://192.168.1.10:8087/app/news?cat=finance" 300000
                 '("t" "a") '((0 equal "news")))
(display (or (json-feed-dump) "no document\\n"))
;; prints one line per object, e.g. news<TAB>Markets rally
''',
        check=False,
    ),
    # ---- http --------------------------------------------------------------
    api('http-get', 'http',
        sig='(http-get url [headers])',
        desc='Fetch a URL and wait for the response: (status . body).',
        returns='A pair (status . body): status the HTTP status as an integer (any status, 404 too, is a result; '
                'redirects are not followed), body the response body as a string of its bytes. headers: an alist '
                'of (name . value) strings. Blocks the app until the response is complete, at most 10 s. Errors: '
                '"http-get: WiFi not connected", "http-get: cannot connect", "http-get: timeout", "http-get: '
                'response larger than 16384 bytes", a url not http:// or https://.',
        example='''
(let ((r (http-get "http://192.168.1.10:8087/app/ping"
                   '(("Accept" . "application/json")))))
  (if (= (car r) 200) (json-parse (cdr r)) #f))
; => ((items . #(((t . "ok")))))
''',
        status=RESERVED, check=False,
    ),
    api('http-post', 'http',
        sig='(http-post url body [content-type])',
        desc='Post a string body and wait for the response: (status . body).',
        returns='A pair (status . body) as http-get. content-type defaults to "application/json". Blocks the app '
                'until the response is complete, at most 10 s. Errors as http-get, prefixed "http-post:".',
        example='''
(define r (http-post "http://192.168.1.10:8087/log"
                     (json-stringify '((device . "kitchen") (temp . 21)))))
(car r)
; => 200
''',
        status=RESERVED, check=False,
    ),
    # ---- mqtt --------------------------------------------------------------
    api('mqtt-connect', 'mqtt',
        sig='(mqtt-connect url [client-id])',
        desc='Connect to a broker (mqtt:// or mqtts://, user:password@ allowed); reconnects by itself later.',
        returns='#t once the broker accepted the connection (waits at most 10 s). client-id defaults to '
                '"minischeme-" and the last 6 hex digits of the MAC. A second call replaces the connection. After a '
                'drop the client reconnects and subscribes again by itself. Errors: "mqtt-connect: WiFi not '
                'connected", "cannot connect", "timeout", "refused by the broker (code N)".',
        example='''
(mqtt-connect "mqtt://user:pass@192.168.1.10:1883" "kitchen-display")
; => #t
''',
        status=RESERVED, check=False,
    ),
    api('mqtt-disconnect', 'mqtt',
        sig='(mqtt-disconnect)',
        desc='Close the connection; forget subscriptions and queued messages.',
        returns='Void; also when not connected. Never an error.',
        example='''
(mqtt-disconnect)
''',
        status=RESERVED, check=False,
    ),
    api('mqtt-publish', 'mqtt',
        sig='(mqtt-publish topic payload [qos [retain?]])',
        desc='Publish a string payload to a topic.',
        returns='#t once the message is handed to the client (QoS 1 and 2 are delivered with retries in the '
                'background). qos 0, 1 or 2 (default 0); retain? default #f. Errors: "mqtt-publish: not '
                'connected", "qos must be 0, 1 or 2", a topic or payload not a string.',
        example='''
(mqtt-publish "home/kitchen/temp" (number->string 21) 1 #t)
; => #t
''',
        status=RESERVED, check=False,
    ),
    api('mqtt-subscribe', 'mqtt',
        sig='(mqtt-subscribe topic [qos])',
        desc='Subscribe to a topic filter (+ and # wildcards); messages queue for mqtt-poll.',
        returns='#t once the broker acknowledged the subscription. qos 0, 1 or 2 (default 0). Subscriptions are '
                'renewed after a reconnect. Errors: "mqtt-subscribe: not connected", "qos must be 0, 1 or 2", '
                '"refused by the broker".',
        example='''
(mqtt-subscribe "home/+/temp")
; => #t
''',
        status=RESERVED, check=False,
    ),
    api('mqtt-poll', 'mqtt',
        sig='(mqtt-poll)',
        desc='The next message received: (topic . payload), or #f.',
        returns='A pair of strings (topic . payload), oldest first; #f when the queue is empty or not connected. '
                'The queue keeps 16 messages; when full the oldest is dropped. Never an error.',
        example='''
(let loop ((m (mqtt-poll)))
  (if m
      (begin (show-reading (car m) (string->number (cdr m)))
             (loop (mqtt-poll)))))
''',
        status=RESERVED, check=False,
    ),
]
