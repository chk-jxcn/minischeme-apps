"""API entries: gpio, adc, dac, pwm, i2c, spi, uart, timer, button, led, light, backlight, buzzer (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    # ---- gpio --------------------------------------------------------------
    api('gpio-mode', 'gpio',
        sig='(gpio-mode pin mode)',
        desc="Set a pin's mode: 0 or 'input, 1 or 'output, 2 or 'pullup (also 'input-pullup): input with pull-up.",
        returns="Void. Never raises an error: a non-integer pin is ignored, other numbers and unknown symbols "
                "mean output. On the board pins of the display bus (2 4 12-17 25-27 32 33) are left alone, and "
                "34..39 are input only.",
        example='''
(gpio-mode 5 'output)
(gpio-mode 19 'pullup)   ; a switch from GPIO 19 to GND
(gpio-mode 34 0)         ; input
''',
        notes='Free pins on the reference board: 0, 5, 19, 23 (in/out) and 34, 36, 39 (input only). KEY 18, the '
              'LED (21), the backlight (22) and the light sensor (35) have their own procedures.',
    ),
    alias('pin-mode', 'gpio-mode', 'gpio'),
    api('gpio-write', 'gpio',
        sig='(gpio-write pin level)',
        desc='Set the output level of a pin: 0 low, any other integer high.',
        returns='Void. Never raises an error: non-integer arguments are ignored; on the board pins of the '
                'display bus are left alone. Set the pin to output with gpio-mode first.',
        example='''
(gpio-mode 5 'output)
(gpio-write 5 1)   ; LED on
(time-sleep-ms 200)
(gpio-write 5 0)
''',
    ),
    alias('digital-write', 'gpio-write', 'gpio'),
    api('gpio-read', 'gpio',
        sig='(gpio-read pin)',
        desc='Read the input level of a pin (0 or 1).',
        returns='0 or 1; 0 when pin is not an integer. A pin set to output reads back the level last written (on the board its input stays enabled).',
        example='''
(gpio-mode 19 'pullup)
(define (switch-closed?) (= (gpio-read 19) 0))
(integer? (gpio-read 19)) ; => #t
''',
    ),
    alias('digital-read', 'gpio-read', 'gpio'),
    api('gpio-toggle', 'gpio',
        sig='(gpio-toggle pin)',
        desc='Invert an output pin.',
        returns='The new level, 0 or 1. An error when pin is not an output-capable pin (0..33) set to output '
                'by gpio-mode, or belongs to the display bus.',
        example='''
(gpio-mode 5 'output)
(define (app-tick . args) (gpio-toggle 5))   ; blink once a second
''',
        status=RESERVED,
    ),
    api('gpio-on-change', 'gpio',
        sig='(gpio-on-change pin edge proc)',
        desc="Call (proc pin level) from the app loop when the pin changes; edge is 'rising, 'falling or 'both.",
        returns='#t. The interrupt only records the edge; proc runs from the app loop on its next pass, once per '
                'pass however many edges came (level is the level then). A new call for the same pin replaces '
                'its watcher; watchers end with the app. An error when pin is not 0..39, edge is not one of '
                'the three symbols or proc is not a procedure.',
        example='''
(gpio-mode 19 'pullup)
(gpio-on-change 19 'falling
  (lambda (pin level) (led-set 0 255 0)))
''',
        status=RESERVED,
    ),
    api('gpio-off-change', 'gpio',
        sig='(gpio-off-change pin)',
        desc='Stop watching a pin.',
        returns='#t when a watcher was removed, #f when the pin had none. An error when pin is not an integer.',
        example='''
(gpio-off-change 19)
''',
        status=RESERVED,
    ),
    # ---- adc ---------------------------------------------------------------
    api('adc-read', 'adc',
        sig='(adc-read pin)',
        desc='Raw 12-bit reading (0..4095) of an analog input pin.',
        returns='An integer 0..4095 (12 bits, 0..about 3.3 V at the default 12 dB attenuation) for the ADC1 pins 32..39; 0 for other pins or a non-integer pin. The simulator returns the light sensor for pin 35 and 2048 for the other ADC1 pins.',
        example='''
(define raw (adc-read 34))
(quotient (* raw 3300) 4095)   ; rough millivolts at 11 dB attenuation
''',
        notes='ADC1 pins are 32..39 (34, 36 and 39 are free on the reference board); ADC2 cannot be used while '
              'WiFi runs.',
    ),
    alias('analog-read', 'adc-read', 'adc'),
    api('adc-read-mv', 'adc',
        sig='(adc-read-mv pin)',
        desc='Calibrated input voltage in millivolts.',
        returns='An integer in millivolts, corrected with the chip\'s eFuse calibration for the pin\'s '
                'attenuation (11 dB by default: about 150..2450 mV). An error when pin is not an ADC1 pin (32..39).',
        example='''
(define mv (adc-read-mv 34))
(if (> mv 2000) (led-set 255 0 0))
''',
        status=RESERVED,
    ),
    api('adc-config', 'adc',
        sig='(adc-config pin attenuation-db)',
        desc='Input range of an analog pin: attenuation 0, 2.5, 6 or 11 dB.',
        returns='#t. Full-scale ranges: 0 dB about 950 mV, 2.5 dB 1250 mV, 6 dB 1750 mV, 11 dB 2450 mV (the '
                'default). An error when pin is not an ADC1 pin (32..39) or the attenuation is not one of the four.',
        example='''
(adc-config 34 6)
(adc-read-mv 34)
''',
        status=RESERVED,
    ),
    # ---- dac ---------------------------------------------------------------
    api('dac-write', 'dac',
        sig='(dac-write pin value)',
        desc='Output a voltage: value 0..255 of the supply.',
        returns='#t; the pin then holds value / 255 x 3.3 V until the next call. An error when pin is not a DAC '
                'pin (25 or 26 on the ESP32) or is in use (on the reference board both drive the display bus), '
                'or value is not 0..255.',
        example='''
(dac-write 25 128)   ; about 1.65 V
''',
        status=RESERVED,
    ),
    # ---- pwm ---------------------------------------------------------------
    api('pwm-write', 'pwm',
        sig='(pwm-write pin freq duty)',
        desc='PWM output on a pin: frequency in Hz and duty cycle 0..255.',
        returns='Void. Never raises an error: non-integer arguments are ignored, duty is clamped to 0..255. On the board each pin gets one of 7 LEDC channels on a shared timer (the latest freq applies to all of them; freq <= 0 means 5000 Hz); pins of the display bus are left alone and pin 22 sets the backlight, as in the simulator (use backlight-set for that).',
        example='''
(pwm-write 23 1000 128)   ; 1 kHz, 50 %
(pwm-write 23 1000 0)     ; off
''',
    ),
    api('pwm-config', 'pwm',
        sig='(pwm-config pin freq-hz [resolution-bits])',
        desc='Frequency and resolution of a PWM pin.',
        returns='#t. resolution-bits is 1..16 (default 8) and freq-hz x 2^bits must not exceed 80 MHz; '
                'pwm-write\'s duty then ranges 0..2^bits - 1 on that pin. An error when the pin is not '
                'output-capable or belongs to the display bus, the combination is not possible, or no PWM '
                'channel is free (7 are; the backlight uses one).',
        example='''
(pwm-config 23 50 14)        ; servo: 50 Hz, 14 bits
(pwm-write 23 50 1229)       ; 1.5 ms pulse: centre
''',
        status=RESERVED,
    ),
    api('pwm-stop', 'pwm',
        sig='(pwm-stop pin)',
        desc='Stop PWM on a pin and release its channel.',
        returns='#t when PWM ran on the pin (now driven low), #f when it had none. An error when pin is not an integer.',
        example='''
(pwm-stop 23)
''',
        status=RESERVED,
    ),
    # ---- i2c ---------------------------------------------------------------
    api('i2c-open', 'i2c',
        sig='(i2c-open port sda scl [freq-hz])',
        desc='Start an I2C master on two pins.',
        returns='#t. port is 0 or 1; freq-hz defaults to 100000 (up to 1000000); the internal pull-ups are '
                'enabled. An error when the port is already open or not 0/1, or a pin is not output-capable or '
                'belongs to the display bus.',
        example='''
(i2c-open 0 19 23 400000)   ; SDA 19, SCL 23, 400 kHz
''',
        status=RESERVED,
    ),
    api('i2c-close', 'i2c',
        sig='(i2c-close port)',
        desc='Release an I2C port.',
        returns='#t when the port was open, #f otherwise. Ports close when the app ends.',
        example='''
(i2c-close 0)
''',
        status=RESERVED,
    ),
    api('i2c-scan', 'i2c',
        sig='(i2c-scan port)',
        desc='Addresses of the devices that answer.',
        returns='A list of the 7-bit addresses (8..119) that acknowledge, ascending; () when none. An error '
                'when the port is not open.',
        example='''
(i2c-open 0 19 23)
(i2c-scan 0)   ; e.g. (60 118): an SSD1306 and a BME280
''',
        status=RESERVED,
    ),
    api('i2c-write', 'i2c',
        sig='(i2c-write port addr bytes)',
        desc='Write bytes (a string or a list of integers) to a device.',
        returns='#t when the device acknowledged every byte, #f when it did not answer (NAK or a 50 ms '
                'timeout). An error when the port is not open, addr is not 0..127 or a byte is not 0..255.',
        example='''
(i2c-write 0 118 '(244 39))   ; BME280: ctrl_meas = normal mode
''',
        status=RESERVED,
    ),
    api('i2c-read', 'i2c',
        sig='(i2c-read port addr n)',
        desc='Read n bytes from a device.',
        returns='A list of n integers 0..255, or #f when the device did not answer. An error when the port is '
                'not open, addr is not 0..127 or n is not 1..256.',
        example='''
(i2c-read 0 72 2)   ; e.g. (25 128): two bytes of a temperature sensor
''',
        status=RESERVED,
    ),
    api('i2c-write-read', 'i2c',
        sig='(i2c-write-read port addr bytes n)',
        desc='Write then read in one transaction (register reads).',
        returns='A list of n integers 0..255 read after a repeated start, or #f when the device did not answer. '
                'Errors as i2c-write and i2c-read.',
        example='''
(i2c-write-read 0 118 '(208) 1)   ; BME280 chip id register => (96)
''',
        status=RESERVED,
    ),
    # ---- spi ---------------------------------------------------------------
    api('spi-open', 'spi',
        sig='(spi-open port sck mosi miso [freq-hz [mode]])',
        desc='Start an SPI master.',
        returns='#t. port is 2 (SPI2) or 3 (SPI3); miso -1 for write-only devices; freq-hz defaults to 1000000 '
                '(up to 26000000 through the GPIO matrix); mode 0..3, default 0. An error when the port is open '
                'already or invalid, or a pin is unusable or belongs to the display bus.',
        example='''
(spi-open 2 18 23 19 8000000)
''',
        status=RESERVED,
    ),
    api('spi-close', 'spi',
        sig='(spi-close port)',
        desc='Release an SPI port.',
        returns='#t when the port was open, #f otherwise. Ports close when the app ends.',
        example='''
(spi-close 2)
''',
        status=RESERVED,
    ),
    api('spi-transfer', 'spi',
        sig='(spi-transfer port cs bytes)',
        desc='Clock bytes out with chip select cs low; the bytes clocked in.',
        returns='A list of integers 0..255, as many as were sent (all 0 without miso). bytes is a string or a '
                'list of integers 0..255, at most 4096; cs -1 leaves chip select to the app. An error when the '
                'port is not open or a byte is out of range.',
        example='''
(spi-transfer 2 5 '(159 0 0 0))   ; flash JEDEC id, e.g. (0 239 64 22)
''',
        status=RESERVED,
    ),
    # ---- uart --------------------------------------------------------------
    api('uart-open', 'uart',
        sig='(uart-open port tx rx baud)',
        desc='Open a serial port.',
        returns='#t. port is 1 or 2 (UART0 is the console and the REPL); 8 data bits, no parity, 1 stop bit; a '
                '1024-byte receive buffer. An error when the port is open already or invalid, a pin is unusable '
                'or baud is not 300..5000000.',
        example='''
(uart-open 1 23 19 9600)   ; TX 23, RX 19
''',
        status=RESERVED,
    ),
    api('uart-close', 'uart',
        sig='(uart-close port)',
        desc='Close a serial port.',
        returns='#t when the port was open, #f otherwise. Ports close when the app ends.',
        example='''
(uart-close 1)
''',
        status=RESERVED,
    ),
    api('uart-write', 'uart',
        sig='(uart-write port data)',
        desc='Send a string or a list of bytes.',
        returns='The number of bytes queued (an integer); waits only while the transmit buffer is full. An '
                'error when the port is not open or a byte is not 0..255.',
        example='''
(uart-write 1 "AT\\r\\n") ; => 4
''',
        status=RESERVED,
    ),
    api('uart-read', 'uart',
        sig='(uart-read port [max])',
        desc='The bytes received so far (a string, maybe empty).',
        returns='A string of up to max bytes (default: all buffered) taken from the receive buffer; "" when '
                'nothing arrived. Never waits. An error when the port is not open.',
        example='''
(define (app-step)
  (let ((line (uart-read 1)))
    (if (> (string-length line) 0) (display line))))
''',
        status=RESERVED,
    ),
    api('uart-available', 'uart',
        sig='(uart-available port)',
        desc='Number of bytes waiting.',
        returns='An integer 0..1024: the bytes in the receive buffer. An error when the port is not open.',
        example='''
(if (> (uart-available 1) 0) (uart-read 1))
''',
        status=RESERVED,
    ),
    # ---- timer -------------------------------------------------------------
    api('timer-start', 'timer',
        sig='(timer-start ms proc [repeat?])',
        desc='Call (proc) from the app loop after ms (every ms when repeat?).',
        returns='A timer id (a positive integer). proc runs on the first app-loop pass after it is due, never '
                'from an interrupt; a repeating timer that falls behind skips the missed calls. Timers end with '
                'the app. An error when ms is not a positive integer, proc is not a procedure or all 8 timers '
                'are in use.',
        example='''
(define blink (timer-start 500 (lambda () (gpio-toggle 5)) #t))
(timer-start 3000 (lambda () (led-clear)))   ; once, in 3 s
''',
        status=RESERVED,
    ),
    api('timer-stop', 'timer',
        sig='(timer-stop id)',
        desc='Cancel a timer.',
        returns='#t when the timer was pending, #f when the id is unknown or a one-shot timer already ran.',
        example='''
(timer-stop blink)
''',
        status=RESERVED,
    ),
    # ---- button ------------------------------------------------------------
    api('button-read', 'button',
        sig='(button-read)',
        desc='The user button (KEY 18) now: 1 pressed, 0 released.',
        returns='0 or 1. The firmware samples the button once per app-loop pass (a press shorter than a pass '
                'still counts once); the WebREPL\'s KEY 18 counts too. Never fails.',
        example='''
(define (app-step)
  (if (= (button-read) 1) (led-set 0 0 255) (led-clear)))
''',
        notes='For presses use the hooks: app-button (short press), app-long-press (0.8 s), app-mid-press '
              '(3.5 s); an 8 s hold opens the hardware pages, where a mid press opens the system settings. Inside the system settings (since 1.3.0) the mid press reaches the settings app (back) and there is no hold. The '
              'times are config.ini [system] button_long_ms, button_mid_ms, button_hold_ms.',
    ),
    api('button-pressed?', 'button',
        sig='(button-pressed?)',
        desc='Whether the user button (KEY 18) is held now.',
        returns='#t or #f, the same sample as button-read. Never fails.',
        example='''
(define (app-step)
  (if (button-pressed?) (backlight-set 255)))
(boolean? (button-pressed?)) ; => #t
''',
    ),
    # ---- led ---------------------------------------------------------------
    api('led-set', 'led',
        sig='(led-set r g b)',
        desc='Set the RGB status LED (WS2812) color, each channel 0..255.',
        returns='Void. Each value is taken modulo 256 (300 gives 44); with fewer than three integers nothing '
                'changes. Never raises an error.',
        example='''
(led-set 255 0 0)
(led-get) ; => (255 0 0)
''',
    ),
    alias('ws2812-set', 'led-set', 'led'),
    api('led-get', 'led',
        sig='(led-get)',
        desc='The LED color last set, as (r g b).',
        returns='A list of three integers 0..255; (0 0 0) after boot. Never fails.',
        example='''
(led-set 0 64 255)
(led-get) ; => (0 64 255)
''',
    ),
    alias('ws2812-get', 'led-get', 'led'),
    api('led-clear', 'led',
        sig='(led-clear)',
        desc='Turn the RGB status LED off.',
        returns='Void; the same as (led-set 0 0 0). Never fails.',
        example='''
(led-set 0 255 0)
(led-clear)
(led-get) ; => (0 0 0)
''',
    ),
    alias('ws2812-clear', 'led-clear', 'led'),
    # ---- light -------------------------------------------------------------
    api('light-read', 'light',
        sig='(light-read)',
        desc='Raw photoresistor reading (0..4095): higher is brighter.',
        returns='An integer 0..4095: on the board a trimmed mean of 16 ADC samples of GPIO 35, refreshed every '
                '3 s by the firmware (or the WebREPL\'s simulated value); 2048 until the first sample. Never fails.',
        example='''
(define (dark?) (< (light-read) 400))
(<= 0 (light-read) 4095) ; => #t
''',
    ),
    api('light-lux', 'light',
        sig='(light-lux)',
        desc='Rough brightness 0..1000, scaled linearly from light-read; not a calibrated lux value.',
        returns='An integer: (quotient (* (light-read) 1000) 4095). Never fails.',
        example='''
(= (light-lux) (quotient (* (light-read) 1000) 4095)) ; => #t
''',
    ),
    # ---- backlight ---------------------------------------------------------
    api('backlight-set', 'backlight',
        sig='(backlight-set val)',
        desc='Set LCD backlight brightness PWM (0-255); turns the automatic backlight off. Kept in config.ini [display] backlight.',
        returns='Void. val is clamped to 0..255 (0 is dark); a non-integer is ignored. The firmware saves the '
                'level and auto_backlight = 0 to config.ini once changes stop for 3 s.',
        example='''
(backlight-set 128)
(backlight-get) ; => 128
(backlight-auto) ; => #f
''',
    ),
    api('backlight-get', 'backlight',
        sig='(backlight-get)',
        desc='Current LCD backlight brightness (0-255), set by backlight-set or by the automatic backlight.',
        returns='An integer 0..255. Never fails.',
        example='''
(backlight-set 200)
(backlight-get) ; => 200
''',
    ),
    api('backlight-auto', 'backlight',
        sig='(backlight-auto [on?])',
        desc='Automatic backlight from the light sensor: #t while on; (backlight-auto #t) / #f turns it on / off. backlight-set turns it off. Kept in config.ini [display] auto_backlight.',
        returns='#t or #f: the state after the call. Any value but #f turns it on, which moves the level half '
                'way to the target at once. Never fails.',
        example='''
(backlight-auto #t) ; => #t
(backlight-set 180)
(backlight-auto) ; => #f
''',
        notes='Once a second the level moves half way to 60 + 195 x sqrt(light-read / 4095): about 70 in a dark '
              'room, 190 indoors, 255 in direct light.',
    ),
    # ---- buzzer ------------------------------------------------------------
    api('buzzer-tone', 'buzzer',
        sig='(buzzer-tone freq-hz ms)',
        desc='Play a tone.',
        returns='#t at once: the tone (a 50 % PWM square wave) plays in the background for ms, or until '
                'buzzer-stop when ms is 0; a new tone replaces the one playing. An error when freq-hz is not '
                '20..20000 or ms is negative. Absent on boards without a buzzer (the reference board).',
        example='''
(buzzer-tone 880 150)
''',
        status=RESERVED,
    ),
    api('buzzer-stop', 'buzzer',
        sig='(buzzer-stop)',
        desc='Silence the buzzer.',
        returns='#t when a tone was playing, #f otherwise.',
        example='''
(buzzer-tone 440 0)   ; until stopped
(buzzer-stop)
''',
        status=RESERVED,
    ),
]
