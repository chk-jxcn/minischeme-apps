"""API entries: json, codec, random (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

JSON_NOTES = '''\
Mapping (json-parse, and json-stringify back):

| JSON | Scheme |
|---|---|
| object `{"a":1}` | association list with symbol keys `((a . 1))`, members in document order |
| array `[1,2]` | vector `#(1 2)` |
| string | string (UTF-8; escapes decoded, `\\uXXXX` surrogate pairs combined) |
| integer `42`, `-7` | exact integer (bignum when large) |
| number with `.` or exponent | flonum |
| `true` / `false` | `#t` / `#f` |
| `null` | `()` |

An empty object `{}` also parses to `()`, so it is written back as `null`.
json-stringify also accepts string keys and writes symbols in value position as
strings. Read members with `assq`: `(cdr (assq 'temp obj))`.'''

APIS = [
    # ---- json --------------------------------------------------------------
    api('json-parse', 'json',
        sig='(json-parse text)',
        desc='JSON text to data: objects become alists with symbol keys, arrays vectors, null ().',
        returns='The value of the JSON document (see the mapping). Errors: "json-parse: invalid JSON at byte N" '
                '(also for text after the value), "json-parse: nesting deeper than 32", text not a string.',
        notes=JSON_NOTES,
        example='''
(define doc (json-parse "{\\"t\\":\\"temp\\",\\"v\\":21.5,\\"s\\":[1,2],\\"ok\\":true,\\"x\\":null}"))
doc                      ; => ((t . "temp") (v . 21.5) (s . #(1 2)) (ok . #t) (x))
(cdr (assq 'v doc))      ; => 21.5
(json-parse "[1,")       ; => error: json-parse: invalid JSON at byte 3
''',
        status=RESERVED,
    ),
    api('json-stringify', 'json',
        sig='(json-stringify value)',
        desc='Data to compact JSON text (the inverse of json-parse).',
        returns='A string without whitespace: alists (symbol or string keys) become objects, vectors arrays, '
                'strings and symbols JSON strings (", \\ and control characters escaped, UTF-8 kept), exact '
                'integers and finite flonums numbers, #t/#f true/false, () null. Error "json-stringify: cannot '
                'encode X" for anything else (procedures, characters, improper lists, NaN or infinities).',
        example='''
(json-stringify '((t . "temp") (v . 21) (ok . #t) (s . #(1 2))))
; => "{\\"t\\":\\"temp\\",\\"v\\":21,\\"ok\\":true,\\"s\\":[1,2]}"
(json-stringify #(1 "a" ()))
; => "[1,\\"a\\",null]"
''',
        status=RESERVED,
    ),
    # ---- codec -------------------------------------------------------------
    api('base64-encode', 'codec',
        sig='(base64-encode str)',
        desc="Base64 text of a string's bytes (standard alphabet, = padding, no line breaks).",
        returns='A string of Base64 text (RFC 4648 alphabet with + and /, padded with =); "" for "". Error '
                '"base64-encode: expected a string".',
        example='''
(base64-encode "hello")                ; => "aGVsbG8="
(string-append "Basic " (base64-encode "user:pass"))
; => "Basic dXNlcjpwYXNz"
''',
        status=RESERVED,
    ),
    api('base64-decode', 'codec',
        sig='(base64-decode str)',
        desc='The bytes of Base64 text as a string; padding optional, whitespace ignored.',
        returns='A string of the decoded bytes. The = padding may be left out; spaces and line breaks are '
                'skipped. Error "base64-decode: invalid Base64" for another character or a wrong length, and for '
                'a str that is not a string.',
        example='''
(base64-decode "aGVsbG8=")   ; => "hello"
(base64-decode "aGVsbG8")    ; => "hello"
''',
        status=RESERVED,
    ),
    api('url-encode', 'codec',
        sig='(url-encode str)',
        desc='Percent-encode a string for a URL query: every byte but A-Z a-z 0-9 - _ . ~ becomes %XX.',
        returns='A string: unreserved characters (RFC 3986: letters, digits, - _ . ~) kept, every other byte as '
                '%XX with uppercase hex (a space is %20, UTF-8 characters byte by byte). Error "url-encode: '
                'expected a string".',
        example='''
(url-encode "a b&c=d/é")   ; => "a%20b%26c%3Dd%2F%C3%A9"
(string-append "http://192.168.1.10:8087/app/weather?loc=" (url-encode "New York"))
; => "http://192.168.1.10:8087/app/weather?loc=New%20York"
''',
        status=RESERVED,
    ),
    api('url-decode', 'codec',
        sig='(url-decode str)',
        desc='Decode percent-encoding (and + as space).',
        returns='A string: each %XX (either case) becomes its byte and + a space; a % not followed by two hex '
                'digits is kept as is. Error "url-decode: expected a string".',
        example='''
(url-decode "a+b%26c%3d%E2%9C%93")   ; => "a b&c=✓"
(url-decode "100%")                  ; => "100%"
''',
        status=RESERVED,
    ),
    api('crc32', 'codec',
        sig='(crc32 str)',
        desc="CRC-32 (IEEE 802.3, as zlib and PNG) of a string's bytes.",
        returns='An exact integer 0..4294967295 (reflected polynomial #xEDB88320, initial value and final XOR '
                '#xFFFFFFFF). Error "crc32: expected a string".',
        example='''
(crc32 "123456789")                 ; => 3421780262
(number->string (crc32 "") 16)      ; => "0"
''',
        status=RESERVED,
    ),
    # ---- random ------------------------------------------------------------
    api('random', 'random',
        sig='(random n)',
        desc='A pseudo-random integer in 0..n-1.',
        returns='An exact integer 0 <= r < n. Seeded from the hardware random generator at boot (other sequences '
                'every start) unless random-seed! is called. Error "random: expected a positive integer" when n '
                'is not an integer >= 1.',
        example='''
(define colors #("red" "green" "blue"))
(vector-ref colors (random (vector-length colors)))
(< -1 (random 6) 6)   ; => #t
''',
        status=RESERVED,
    ),
    api('random-seed!', 'random',
        sig='(random-seed! n)',
        desc='Seed the generator: the same seed gives the same numbers on every device and the simulator.',
        returns='Void. n: any exact integer (only its low 32 bits count). Error "random-seed!: expected an '
                'integer".',
        example='''
(random-seed! 42)
(define a (list (random 100) (random 100)))
(random-seed! 42)
(equal? a (list (random 100) (random 100)))   ; => #t
''',
        status=RESERVED,
    ),
]
