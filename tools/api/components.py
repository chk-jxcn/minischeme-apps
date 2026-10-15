"""API components: id -> (group, title, description). Names of device
procedures follow component-function ("gpio-write", "wifi-connect"); the
language core keeps the standard Scheme names."""

GROUPS = ['Language', 'System', 'Hardware', 'Display', 'Network', 'Storage', 'Tools', 'Extensions', 'Host']

COMPONENTS = {
    # Language core (standard Scheme names)
    'syntax':   ('Language', 'Special forms', 'Syntax handled by the compiler: binding, branching, macros.'),
    'math':     ('Language', 'Numbers', 'Arithmetic on fixnums, bignums and flonums; comparison; rounding.'),
    'list':     ('Language', 'Pairs and lists', 'Pairs, lists and association lists.'),
    'vector':   ('Language', 'Vectors', 'Fixed-length vectors.'),
    'string':   ('Language', 'Strings', 'Strings (UTF-8 bytes) and conversions; text helpers.'),
    'char':     ('Language', 'Characters', 'Characters and their codes.'),
    'type':     ('Language', 'Types and equivalence', 'Type predicates and equality.'),
    'control':  ('Language', 'Control', 'Procedures, continuations and errors.'),
    'io':       ('Language', 'Output and loading', 'Printing to the console; loading code and snapshots.'),
    'reflect':  ('Language', 'Reflection', 'The global environment and the runtime help.'),
    'vm':       ('Language', 'Virtual machine', 'Heap, stacks and the Code ROM (execute in place) of the running VM.'),
    # System
    'api':      ('System', 'API introspection', 'The API version of the firmware and what this device provides.'),
    'sys':      ('System', 'System', 'Chip, firmware and restart.'),
    'mem':      ('System', 'Memory', 'System RAM of the device (outside the VM heap).'),
    'flash':    ('System', 'Flash', 'Flash size and the partitions of the firmware and the app image.'),
    'power':    ('System', 'Power', 'Sleep modes and supply.'),
    'time':     ('System', 'Time', 'Uptime, delays and the wall clock.'),
    'app':      ('System', 'Apps', 'The running app, the installed apps and their settings.'),
    'config':   ('System', 'Configuration', 'Settings in /spiffs/config.ini and the app\'s own <id>.ini.'),
    'setup':    ('System', 'Setup mode', 'The WiFi access point and web page for first-time setup.'),
    'market':   ('System', 'App market', 'Installing and updating apps from a market server (config.ini [market]).'),
    'bench':    ('System', 'Benchmarks', 'Firmware timing diagnostics.'),
    # Hardware
    'gpio':     ('Hardware', 'GPIO', 'Digital pins.'),
    'adc':      ('Hardware', 'ADC', 'Analog inputs.'),
    'dac':      ('Hardware', 'DAC', 'Analog outputs.'),
    'pwm':      ('Hardware', 'PWM', 'Pulse-width modulated outputs (LED dimming, buzzers, servos).'),
    'i2c':      ('Hardware', 'I2C', 'I2C bus master.'),
    'spi':      ('Hardware', 'SPI', 'SPI bus master.'),
    'uart':     ('Hardware', 'UART', 'Serial ports.'),
    'timer':    ('Hardware', 'Timers', 'Periodic and one-shot callbacks.'),
    'button':   ('Hardware', 'Button', 'The user button (KEY 18 on the reference board).'),
    'led':      ('Hardware', 'RGB LED', 'The addressable RGB status LED (WS2812 on the reference board).'),
    'light':    ('Hardware', 'Light sensor', 'Ambient light.'),
    'backlight':('Hardware', 'Backlight', 'Display backlight level and the automatic (light-driven) mode.'),
    'buzzer':   ('Hardware', 'Buzzer', 'Tones on a piezo buzzer.'),
    # Display
    'display':  ('Display', 'Display', 'The panel: model, rotation, transfer buffers.'),
    'gui':      ('Display', 'Graphics', 'Drawing, text, clipping, buffers and the retained band renderer.'),
    'font':     ('Display', 'Fonts', 'Font slots: loading bitmap fonts and choosing them.'),
    'fontrom':  ('Display', 'Font ROM', 'The system font ROM partition, read in place.'),
    'lunar':    ('Display', 'Lunar calendar', 'Chinese lunar dates computed on the device.'),
    # Network
    'wifi':     ('Network', 'WiFi', 'Station connection and status.'),
    'json-feed':('Network', 'JSON feed', 'Background HTTP polling of a JSON document, parsed into compact rows.'),
    'http':     ('Network', 'HTTP', 'Direct HTTP requests.'),
    'mqtt':     ('Network', 'MQTT', 'MQTT client.'),
    # Storage
    'fs':       ('Storage', 'File system', 'Files under /spiffs (LittleFS on the board).'),
    'kv':       ('Storage', 'Key-value store', 'Small persistent values (NVS on the board).'),
    'cfasl':    ('Storage', 'Compressed bytecode', 'CFASL compression of code and lazily loaded stubs.'),
    # Tools
    'json':     ('Tools', 'JSON', 'JSON text to Scheme data and back.'),
    'codec':    ('Tools', 'Encodings', 'Base64, URL encoding and checksums.'),
    'random':   ('Tools', 'Random numbers', 'Pseudo-random numbers.'),
    # Extensions (hardware-specific; see EXTENSIONS in api/__init__.py)
    'esp32':    ('Extensions', 'ESP32', 'Espressif ESP32 chip features: identity, reset cause, touch pads.'),
    # Host
    'host':     ('Host', 'PC REPL', 'Host files and processes; only in the PC REPL, never on a device.'),
}
