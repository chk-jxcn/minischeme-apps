"""API entries: fs, kv, cfasl (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

FS_NOTES = '''\
Files of the board's file system live under `/spiffs/` (LittleFS). An app may
touch only its own folder (`/spiffs/apps/<id>/`, or `/spiffs/user/<id>/` for an
uploaded app): a relative path such as `"notes.txt"` is in that folder, an
absolute one must be; its image there (app.msbc) is read-only and the folder
holds at most config.ini [system] app_storage_kb (256 KB, the image included).
Anything else is an error. The system settings and code from the REPL are not
limited (relative paths are then under `/spiffs`). The WASM simulator keeps its
files in the page and accepts only paths under `/spiffs/` (at most 63 bytes, no
`..`); the PC REPL and the test VM keep them in memory. Strings are byte
strings, so any UTF-8 text round-trips.'''

APIS = [
    # ---- fs ----------------------------------------------------------------
    api('fs-read', 'fs',
        sig='(fs-read path)',
        desc='Read a whole file as a string.',
        returns="A string of the file's bytes (binary-safe: NUL bytes included); #f when the file cannot be opened (missing) or path is not a string. Never an error.",
        notes=FS_NOTES,
        example='''
(fs-write "/spiffs/note.txt" "buy milk")
(fs-read "/spiffs/note.txt")      ; => "buy milk"
(fs-read "/spiffs/missing.txt")   ; => #f
''',
    ),
    api('fs-write', 'fs',
        sig='(fs-write path str)',
        desc='Create or replace a file with the bytes of a string.',
        returns='#t when the whole string was written; #f when the file cannot be created (missing directory, file '
                'system full, in the simulator a path outside /spiffs/) or an argument is not a string. Never an '
                'error.',
        example='''
(define (save-count! n) (fs-write "/spiffs/count.txt" (number->string n)))
(save-count! 42)                                 ; => #t
(string->number (fs-read "/spiffs/count.txt"))   ; => 42
''',
    ),
    api('fs-exists?', 'fs',
        sig='(fs-exists? path)',
        desc='Whether a file exists (paths under /spiffs/).',
        returns='#t when the file exists and can be opened; #f otherwise or when path is not a string. Never an error.',
        example='''
(define (load-or path default) (if (fs-exists? path) (fs-read path) default))
(load-or "/spiffs/city.txt" "Shanghai")   ; => "Shanghai"
(fs-write "/spiffs/city.txt" "Beijing")
(load-or "/spiffs/city.txt" "Shanghai")   ; => "Beijing"
''',
    ),
    api('fs-remove', 'fs',
        sig='(fs-remove path)',
        desc='Delete a file.',
        returns='#t when the file was deleted; #f when it does not exist, cannot be deleted or path is not a string. '
                'Never an error.',
        example='''
(fs-write "/spiffs/tmp.txt" "x")
(fs-remove "/spiffs/tmp.txt")    ; => #t
(fs-remove "/spiffs/tmp.txt")    ; => #f
(fs-exists? "/spiffs/tmp.txt")   ; => #f
''',
    ),
    api('fs-info', 'fs',
        sig='(fs-info)',
        desc='Total and used bytes of the file system: (total used).',
        returns='A list of two integers (total used) in bytes. Never an error.',
        example='''
(let* ((info (fs-info)) (free (- (car info) (cadr info))))
  (string-append (number->string (quotient free 1024)) " KB free"))
; e.g. "1210 KB free"
''',
        where=DEVICE, check=False,
    ),
    api('fs-list', 'fs',
        sig='(fs-list dir)',
        desc='Files directly in a directory with their sizes: (("name" . bytes) ...).',
        returns='A list of pairs (name . size) for the regular files directly in dir (subdirectories are left out; '
                'names without the directory); () when dir does not exist or is not /spiffs or under /spiffs/. '
                'Error "fs-list: expected a directory path" when dir is missing or not a string.',
        example='''
(map car (fs-list "/spiffs/apps"))
; e.g. ("weather.msbc" "stocks.msbc")
(apply + (map cdr (fs-list "/spiffs")))
''',
        where=DEVICE, check=False,
    ),
    api('fs-download', 'fs',
        sig='(fs-download url path [on-done])',
        desc='Download a file from the network into the app\'s folder, in the background (an image for gui-image, '
             'for example); one download at a time. on-done, if given, is called as (on-done ok path) when it ends.',
        returns='#t when the download is queued; #f while another download is still running (try again after it, '
                'see fs-download-status). Errors: url not http:// or https://, path outside the app\'s folder '
                '(the same rule as fs-write), the app\'s storage full, on-done not a procedure.',
        example='''
;; a picture from the app server into the app's folder, then drawn
(define (cover-done ok path)        ; ok: #t when the file is complete
  (if ok (gui-invalidate 0 0 320 480)))   ; render then draws (gui-image x y "cache/7.jpg")
(fs-download (app-url "/app/myapp/pic?id=7") "cache/7.jpg" cover-done)   ; => #t
''',
        where=DEVICE, check=False, since='1.10.0',
        notes='The board fetches over plain HTTP like the JSON feed (the device headers go to configured servers; an '
              'https:// URL goes through the protocol converter), after the feed\'s current request. The body is '
              'written to path.part and replaces path only when complete: a failed download leaves the old file. '
              'At most 256 KB, and no more than the app\'s storage quota has left. gui-image draws baseline JPEG '
              'only: let the app server convert pictures (size and format) before the board downloads them. In '
              'the WebREPL simulator the page fetches the file through server.py. on-done (since 1.12.0) is '
              'called by the main loop, between two app steps, as soon as the download is done (ok #t) or failed '
              '(ok #f; the message is in fs-download-status); it may start the next download at once. It is '
              'called once, and not at all when another app runs by then. Firmware before 1.12 ignores on-done: '
              'an app that also runs there checks fs-download-status from app-tick-proc as well.',
    ),
    api('fs-download-status', 'fs',
        sig='(fs-download-status)',
        desc='The state of the last fs-download: (state path bytes error seq) as an alist.',
        returns='An alist: (state . s) with s one of idle, queued, running, done, error; (path . "the path given"); '
                '(bytes . n) written when done; (error . "message") when it failed ("" otherwise); (seq . k), which '
                'grows by one each time a download ends (done or error), so a change means a new outcome. '
                'Never an error.',
        example='''
(define (download-state) (cdr (assq 'state (fs-download-status))))
(download-state)   ; => idle
''',
        where=DEVICE, check=False, since='1.10.0',
    ),
    api('fs-rename', 'fs',
        sig='(fs-rename from to)',
        desc='Rename or move a file; an existing target is not replaced.',
        returns='#t when renamed; #f when from does not exist, to already exists or the file system refuses. Error '
                '"fs-rename: expected two path strings" when an argument is not a string.',
        example='''
(fs-write "/spiffs/log.tmp" "boot ok\\n")
(fs-rename "/spiffs/log.tmp" "/spiffs/log.txt")   ; => #t
(fs-exists? "/spiffs/log.tmp")                    ; => #f
''',
        status=RESERVED,
    ),
    api('fs-append', 'fs',
        sig='(fs-append path data)',
        desc='Append the bytes of a string to a file, creating it when missing.',
        returns='#t when all of data was appended; #f when the file cannot be opened or written (file system full). '
                'Error "fs-append: expected a path and a string" when an argument is not a string.',
        example='''
(define (log! line) (fs-append "/spiffs/events.log" (string-append line "\\n")))
(log! "button pressed")   ; => #t
''',
        status=RESERVED,
    ),
    api('fs-size', 'fs',
        sig='(fs-size path)',
        desc='Size of a file in bytes, or #f.',
        returns='An integer (bytes); #f when the file does not exist. Error "fs-size: expected a path string" when '
                'path is not a string.',
        example='''
(fs-write "/spiffs/note.txt" "hello")
(fs-size "/spiffs/note.txt")      ; => 5
(fs-size "/spiffs/missing.txt")   ; => #f
''',
        status=RESERVED,
    ),
    # ---- kv ----------------------------------------------------------------
    api('kv-get', 'kv',
        sig='(kv-get key [default])',
        desc="A value stored with kv-set! (a string), or default. Each app has its own keys.",
        returns='The stored string; default (#f when omitted) when the key is not stored. key: a string or symbol '
                'of 1..15 bytes, else error "kv-get: key must be 1..15 bytes". Keys belong to the running app (its '
                'id is the namespace).',
        example='''
(define city (kv-get "city" "Shanghai"))
(kv-set! "city" "Beijing")
(kv-get "city")   ; => "Beijing"
''',
        status=RESERVED,
    ),
    api('kv-set!', 'kv',
        sig='(kv-set! key value)',
        desc='Store a string under a key, kept across restarts (NVS on the board).',
        returns='#t once the value is committed to flash. Errors: "kv-set!: key must be 1..15 bytes", "value must '
                'be a string of at most 4000 bytes", "store full".',
        example='''
(kv-set! "volume" (number->string 7))          ; => #t
(string->number (kv-get "volume" "5"))         ; => 7
''',
        status=RESERVED,
    ),
    api('kv-remove', 'kv',
        sig='(kv-remove key)',
        desc='Delete a key of the running app.',
        returns='#t when the key was removed; #f when it was not stored. Error "kv-remove: key must be 1..15 bytes".',
        example='''
(kv-set! "token" "abc")
(kv-remove "token")   ; => #t
(kv-get "token")      ; => #f
''',
        status=RESERVED,
    ),
    api('kv-keys', 'kv',
        sig='(kv-keys)',
        desc="The keys stored by the running app.",
        returns='A list of key strings in no particular order; () when none. Never an error.',
        example='''
(for-each kv-remove (kv-keys))
(kv-keys)   ; => ()
''',
        status=RESERVED,
    ),
    # ---- cfasl -------------------------------------------------------------
    api('cfasl-compress', 'cfasl',
        sig='(cfasl-compress byte-str)',
        desc='Compress a byte string with LZSS (4 KB window, matches of 3..18 bytes).',
        returns='The compressed bytes as a string (keep the original length: cfasl-decompress needs it); () when byte-str is empty or not a string. Incompressible data can grow to twice its size (bytes >= 128 cost two bytes each). Never an error.',
        example='''
(define s "ABCDEF1234567890ABCDEF1234567890")
(string-length (cfasl-compress s))   ; => 19
(cfasl-compress "")                  ; => ()
''',
    ),
    api('cfasl-decompress', 'cfasl',
        sig='(cfasl-decompress comp-str uncomp-size)',
        desc='Decompress LZSS bytes made by cfasl-compress; uncomp-size is the original length.',
        returns='A string of exactly uncomp-size bytes (a smaller uncomp-size gives the first bytes); () when the '
                'data is corrupt or yields fewer bytes, or an argument has the wrong type. Never an error.',
        example='''
(define s "ABCDEF1234567890ABCDEF1234567890")
(define c (cfasl-compress s))
(equal? (cfasl-decompress c (string-length s)) s)   ; => #t
(cfasl-decompress c 6)     ; => "ABCDEF"
(cfasl-decompress c 100)   ; => ()
''',
    ),
    api('cfasl-make-stub', 'cfasl',
        sig='(cfasl-make-stub comp-code code-bytes nparams max-stack variadic? inner-lambdas? constants)',
        desc='Make a demand-paged procedure stub from compressed bytecode; cfasl-call decompresses and runs it.',
        returns='The stub, a vector #(cfasl-stub comp-code code-bytes nparams max-stack variadic? inner-lambdas? '
                'constants); () when fewer than 7 arguments are given, comp-code is not a non-empty string or '
                'code-bytes (the uncompressed length) is not an integer. The bytecode is not checked: it must come '
                'from this VM version\'s compiler. Never an error.',
        example='''
;; the bytecode of (lambda (x) x): GET_LOCAL 0, RETURN
(define code (cfasl-compress (list->string (map integer->char '(7 0 20)))))
(define id (cfasl-make-stub code 3 1 8 #f #f #()))
(cfasl-stub? id)     ; => #t
(cfasl-call id 42)   ; => 42
''',
    ),
    api('cfasl-call', 'cfasl',
        sig='(cfasl-call stub arg ...)',
        desc='Decompress the bytecode of a procedure stub and run it with the arguments.',
        returns='The value the procedure returns (void when called without a stub). Errors: a wrong argument count ("cfasl-call: expected N arguments, got M"; at least N - 1 for a variadic procedure), a corrupt stub ("cfasl_call_chunk: invalid chunk stub", "expected cfasl-stub object", "corrupt compressed data", "cfasl-call: corrupt stub", "empty procedure"), "procedure chunk exceeds scratch buffer limit (N > 32768)", "decompression failure", "out of memory". The bytecode itself is trusted (made by the compiler).',
        example='''
;; the bytecode of (lambda () 42): INT8 42, RETURN
(define code (cfasl-compress (list->string (map integer->char '(2 42 20)))))
(define answer (cfasl-make-stub code 3 0 8 #f #f #()))
(cfasl-call answer)            ; => 42
(cfasl-call (vector 1 2))      ; => error: invalid chunk stub
''',
    ),
    api('cfasl-stub?', 'cfasl',
        sig='(cfasl-stub? obj)',
        desc='Whether obj is a procedure stub made by cfasl-make-stub.',
        returns='#t for a stub (a vector of 8 or more elements whose first is the symbol cfasl-stub), else #f. Never an error.',
        example='''
(cfasl-stub? (cfasl-make-stub (cfasl-compress "abc") 3 0 8 #f #f #()))   ; => #t
(cfasl-stub? (vector 1 2 3))   ; => #f
''',
    ),
]
