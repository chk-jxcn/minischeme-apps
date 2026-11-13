"""API entries: ble, the Bluetooth Low Energy extension (see api/__init__.py for the fields).

Nothing blocks: a procedure starts an operation and answers at once (#t: started); the
outcome arrives as an event, taken with (ble-event) or handed to the app's own
(app-ble-event ev) hook by the firmware's main loop. Values are hex strings ("0a1b"),
addresses "aa:bb:cc:dd:ee:ff", UUIDs "180f" (16 bit) or 8-4-4-4-12 hex digits (128 bit),
a connection is the number its connected event gave.
"""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

EVENTS = '''
Events (lists, the first element says which):
  (connected conn address role)     a link is up; role: central (we called) or peripheral
  (disconnected conn reason)        a link is gone; conn #f: (ble-connect ...) never got one
  (discovered conn ok?)             (ble-discover conn) finished: (ble-services conn)
  (read conn handle value)          value: hex, #f when the read failed
  (written conn handle ok?)         a write with response finished
  (subscribed conn handle ok?)      notifications are on (or off)
  (notify conn handle value)        a notification or an indication
  (uart conn text)                  a central wrote text to the UART service
  (paired conn ok?)                 the link is encrypted (or the pairing failed)
  (scan-done devices)               a timed scan ended
At most 10 events wait; when more arrive unread, the oldest go.'''

APIS = [
    # ---- state -------------------------------------------------------------
    api('ble-status', 'ble',
        sig='(ble-status)',
        desc='The Bluetooth stack: enabled, state, the device address and name, connections, heap it took.',
        returns="An association list: (enabled . #t/#f) (state . off / starting / idle / scanning / connecting / "
                "advertising) (address . \"aa:bb:cc:dd:ee:ff\") (name . \"Desk-6C92\") (connections . n) (heap . bytes). "
                "Never an error; with the stack off (config.ini [bluetooth] bt_enabled = 0) enabled is #f.",
        example='''
(if (cdr (assq 'enabled (ble-status)))
    (ble-scan-start 5))
''',
        where=DEVICE, ext='ble', check=False,
        notes='The stack starts at boot when config.ini has [bluetooth] bt_enabled = 1 (bt_only = 1: without WiFi; '
              'bt_name: the advertised name). An app that needs it declares "extensions = ble 1.0" in its meta.ini; '
              "(api-has? 'ble-status) says whether this boot has it."),
    api('ble-event', 'ble',
        sig='(ble-event)',
        desc='The next Bluetooth event, or #f when none waits.',
        returns='A list (kind ...) or #f.' + EVENTS,
        example='''
(define (app-step)
  (let ((ev (ble-event)))
    (if ev (handle ev))))
;; or let the firmware call you:
(define (app-ble-event ev) (handle ev))
''',
        where=DEVICE, ext='ble', check=False),

    # ---- observer ----------------------------------------------------------
    api('ble-scan-start', 'ble',
        sig='(ble-scan-start [seconds [active? [filter]]])',
        desc='Starts scanning for advertisements; the 12 strongest devices are kept for (ble-scan-results).',
        returns="#t when the scan started, #f when the stack refused (busy connecting). seconds: 0 or absent, until "
                "(ble-scan-stop); a timed scan ends with a (scan-done n) event. active? (default #t): also ask each "
                "device for its scan response (names are often there). filter: an address, \"name:<prefix>\" or a "
                "service UUID; only matching devices are kept. Raises when the stack is off.",
        example='''
(ble-scan-start 5)                       ; everything near, for 5 s
(ble-scan-start 0 #f "fe95")             ; passive, Xiaomi devices only, until stopped
(ble-scan-start 10 #t "name:LYWSD")
''',
        where=DEVICE, ext='ble', check=False),
    api('ble-scan-stop', 'ble',
        sig='(ble-scan-stop)',
        desc='Stops a scan; what it found stays for (ble-scan-results).',
        returns='#t.',
        example='(ble-scan-stop)',
        where=DEVICE, ext='ble', check=False),
    api('ble-scan-results', 'ble',
        sig='(ble-scan-results)',
        desc='The devices the scan has seen, the strongest first.',
        returns='A list of (address type rssi name connectable? adv): type public or random (symbols), rssi in dBm, '
                'name "" when it sends none, adv the advertisement and scan response bytes (hex, AD structures: see '
                '(ble-adv-field)). The empty list before a scan.',
        example='''
(for-each (lambda (d) (display (car d)) (display " ") (display (caddr d)) (newline))
          (ble-scan-results))
''',
        where=DEVICE, ext='ble', check=False),
    api('ble-adv-field', 'ble',
        sig='(ble-adv-field adv type)',
        desc='One field of an advertisement: the bytes of its first AD structure of that type.',
        returns='A hex string (without the length and type bytes), or #f when the advertisement has no such field. '
                'Types: 9 complete name, 22 (#x16) service data (the UUID first, low byte first), 255 (#xff) '
                'manufacturer data (the company id first).',
        example='''
(ble-adv-field "02010603031a18" 3)    ; => "1a18"
(ble-adv-field "02010603031a18" 255)  ; => #f
''',
        where=DEVICE, ext='ble', check=False),

    # ---- central -----------------------------------------------------------
    api('ble-connect', 'ble',
        sig='(ble-connect address [type])',
        desc='Connects to a peripheral; a (connected conn address central) event follows, or (disconnected #f reason).',
        returns="#t when the attempt started (it gives up after 10 s), #f when another one is under way or the stack "
                "refused. type: 'public or 'random; absent, the type the last scan saw for this address, else public. "
                "A running scan is stopped. Raises on a malformed address or when the stack is off.",
        example='''
(ble-connect "a4:c1:38:4c:87:a2")
''',
        where=DEVICE, ext='ble', check=False),
    api('ble-disconnect', 'ble',
        sig='(ble-disconnect conn)',
        desc='Ends a connection (a disconnected event follows), or gives up an attempt that has no connection yet.',
        returns='#t when the link is being closed, #f when there is no such connection.',
        example='(ble-disconnect 0)',
        where=DEVICE, ext='ble', check=False),
    api('ble-connections', 'ble',
        sig='(ble-connections)',
        desc='The links that are up.',
        returns='A list of (conn address role mtu encrypted?): role central or peripheral (symbols).',
        example='(ble-connections)   ; e.g. ((0 "a4:c1:38:4c:87:a2" central 23 #f))',
        where=DEVICE, ext='ble', check=False),
    api('ble-discover', 'ble',
        sig='(ble-discover conn)',
        desc="Reads a peer's services and characteristics; a (discovered conn ok?) event follows.",
        returns='#t when the discovery started, #f when there is no such connection or no memory for it. Up to 10 '
                'services and 40 characteristics are kept.',
        example='(ble-discover 0)',
        where=DEVICE, ext='ble', check=False),
    api('ble-services', 'ble',
        sig='(ble-services conn)',
        desc='What (ble-discover conn) found.',
        returns='A list of (service-uuid (characteristic-uuid handle properties) ...): handle is the number '
                '(ble-read), (ble-write) and (ble-subscribe) take; properties a list of read, write, '
                'write-no-response, notify, indicate. #f until a discovery has finished.',
        example='''
(ble-services 0)
;; e.g. (("180f" ("2a19" 37 (read notify))) ...)
''',
        where=DEVICE, ext='ble', check=False),
    api('ble-read', 'ble',
        sig='(ble-read conn handle)',
        desc='Reads a characteristic; a (read conn handle value) event follows.',
        returns='#t when the read started, #f when there is no such connection.',
        example='(ble-read 0 37)',
        where=DEVICE, ext='ble', check=False),
    api('ble-write', 'ble',
        sig='(ble-write conn handle value [no-response?])',
        desc='Writes a characteristic; a (written conn handle ok?) event follows unless no-response? is true.',
        returns='#t when the write started (or was sent, without response), #f when there is no such connection. '
                'value: a hex string or a list of bytes, up to 128 bytes. Raises on a malformed value.',
        example='''
(ble-write 0 61 "0100")
(ble-write 0 61 (list 1 0) #t)
''',
        where=DEVICE, ext='ble', check=False),
    api('ble-subscribe', 'ble',
        sig='(ble-subscribe conn handle [on?])',
        desc="Turns a characteristic's notifications on (or off): (subscribed conn handle ok?), then (notify conn handle value) events.",
        returns='#t when the request started, #f when there is no such connection. The peer must have been '
                'discovered: the characteristic\'s configuration descriptor is looked up.',
        example='(ble-subscribe 0 54)',
        where=DEVICE, ext='ble', check=False),
    api('ble-pair', 'ble',
        sig='(ble-pair conn)',
        desc='Encrypts a link, pairing and bonding when the peer is new ("just works": no passkey); a (paired conn ok?) event follows.',
        returns='#t when it started, #f when there is no such connection or the firmware has no security manager. '
                'Bonds are kept in flash (3 at most).',
        example='(ble-pair 0)',
        where=DEVICE, ext='ble', check=False),
    api('ble-bonds', 'ble',
        sig='(ble-bonds)',
        desc='The addresses of the bonded devices.',
        returns='A list of address strings (empty: none).',
        example='(ble-bonds)   ; e.g. ("a4:c1:38:4c:87:a2")',
        where=DEVICE, ext='ble', check=False),
    api('ble-unpair', 'ble',
        sig='(ble-unpair address-or-#t)',
        desc='Forgets one bond, or all of them (#t).',
        returns='#t when something was forgotten, else #f.',
        example='(ble-unpair #t)',
        where=DEVICE, ext='ble', check=False),

    # ---- peripheral --------------------------------------------------------
    api('ble-advertise', 'ble',
        sig='(ble-advertise [connectable? [manufacturer-data]])',
        desc="Advertises the device's name; connectable (the default), a phone can connect and use the UART service.",
        returns='#t when advertising started. manufacturer-data: hex or bytes, the company id (2 bytes) first, up to '
                '24 bytes. Connectable advertising ends when a central connects (a connected event with role '
                'peripheral): call it again to be found once more. Raises when the stack is off.',
        example='''
(ble-advertise)                ; a phone finds "Desk-6C92" and connects
(ble-advertise #f "ffff0102")  ; a beacon: not connectable, 2 bytes of data
''',
        where=DEVICE, ext='ble', check=False,
        notes='The UART service is the Nordic one (6e400001-b5a3-f393-e0a9-e50e24dcca9e): what a central writes to '
              'its RX characteristic arrives as a (uart conn text) event, (ble-uart-write) notifies TX. Phone apps '
              'such as nRF Connect or a "Bluetooth serial terminal" speak it.'),
    api('ble-advertise-stop', 'ble',
        sig='(ble-advertise-stop)',
        desc='Stops advertising.',
        returns='#t.',
        example='(ble-advertise-stop)',
        where=DEVICE, ext='ble', check=False),
    api('ble-uart-write', 'ble',
        sig='(ble-uart-write text [conn])',
        desc='Sends text to the centrals connected to the UART service (or to one).',
        returns='The number of centrals it was sent to (0: nobody is connected and subscribed). Long text goes in '
                'pieces of the link\'s size.',
        example='(ble-uart-write "27.8 C\\n")',
        where=DEVICE, ext='ble', check=False),

    # ---- values ------------------------------------------------------------
    api('ble-bytes->hex', 'ble',
        sig='(ble-bytes->hex bytes)',
        desc='A list of bytes as a hex string.',
        returns='A string of two lowercase hex digits a byte. Raises unless every element is 0..255.',
        example='(ble-bytes->hex (list 1 171))   ; => "01ab"',
        where=DEVICE, ext='ble', check=False),
    api('ble-hex->bytes', 'ble',
        sig='(ble-hex->bytes hex)',
        desc='A hex string as a list of bytes.',
        returns='A list of numbers 0..255 (spaces, colons and dashes between bytes are skipped). Raises on anything '
                'else.',
        example='(ble-hex->bytes "de0a51")   ; => (222 10 81)',
        where=DEVICE, ext='ble', check=False),

    # ---- reserved: fixed names for what a later firmware (ESP32-S3) adds ----
    api('ble-service-add', 'ble',
        sig='(ble-service-add service-uuid characteristics)',
        desc="Adds a GATT service of the app's own: characteristics is a list of (uuid properties [initial-value]).",
        returns='The list of the characteristics\' handles. Reads are answered from the stored value; writes arrive '
                'as (written-by conn handle value) events.',
        example='(ble-service-add "181a" (list (list "2a6e" (list (quote read) (quote notify)) "0000")))',
        status=RESERVED, where=DEVICE, ext='ble', check=False),
    api('ble-value-set!', 'ble',
        sig='(ble-value-set! handle value [notify?])',
        desc="Sets the value of one of the app's own characteristics, and notifies the subscribed centrals.",
        returns='The number of centrals notified.',
        example='(ble-value-set! 42 "e20a" #t)',
        status=RESERVED, where=DEVICE, ext='ble', check=False),
    api('ble-hid-connect', 'ble',
        sig='(ble-hid-connect address)',
        desc='Connects a Bluetooth LE keyboard or remote (HID over GATT): its keys arrive as (key conn usage down?) events.',
        returns='#t when the attempt started.',
        example='(ble-hid-connect "c0:11:22:33:44:55")',
        status=RESERVED, where=DEVICE, ext='ble', check=False),
    api('ble-mtu', 'ble',
        sig='(ble-mtu conn [size])',
        desc="A link's ATT MTU; with size, asks the peer for a larger one.",
        returns='The MTU in bytes (23 until exchanged).',
        example='(ble-mtu 0)',
        status=RESERVED, where=DEVICE, ext='ble', check=False),
    api('ble-rssi', 'ble',
        sig='(ble-rssi conn)',
        desc="A link's signal strength.",
        returns='dBm, or #f when there is no such connection.',
        example='(ble-rssi 0)',
        status=RESERVED, where=DEVICE, ext='ble', check=False),
]
