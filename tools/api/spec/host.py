"""API entries: host (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    # ---- host --------------------------------------------------------------
    api('fasl-to-c', 'host',
        sig='(fasl-to-c in out name exe?)',
        desc='Write a FASL file as an 8-byte aligned C array named name; with exe? #t also a main() that runs it.',
        returns='#t when out was written; #f when in is empty or cannot be read in full. Errors: "%fasl-to-c: '
                'expected (fasl-path out-path sym-name is-exe)" (exe? must be a boolean), "cannot open \'in\' for '
                'reading", "cannot create \'out\'". The header declares name[] and name_len.',
        example='''
(define (main args) 0)
(dump-fasl "app.fasl")                               ; => #t
(fasl-to-c "app.fasl" "app_fasl.h" "app_fasl" #f)    ; => #t
''',
        where=PC,
    ),
    api('file-remove', 'host',
        sig='(file-remove path)',
        desc='Delete a host file.',
        returns='#t when deleted; #f when it does not exist, cannot be deleted or path is not a string. Never an '
                'error.',
        example='''
(write-file-string "out.tmp" "x")
(file-remove "out.tmp")   ; => #t
(file-remove "out.tmp")   ; => #f
''',
        where=PC,
    ),
    api('file-size', 'host',
        sig='(file-size path)',
        desc='Size of a host file in bytes, or -1.',
        returns='An integer (bytes); -1 when the file cannot be opened or path is not a string. Never an error.',
        example='''
(write-file-string "hello.txt" "hello")
(file-size "hello.txt")     ; => 5
(file-size "missing.txt")   ; => -1
''',
        where=PC,
    ),
    api('system', 'host',
        sig='(system command)',
        desc='Run a host shell command and wait for it.',
        returns='The integer C system() returns: the exit code on Windows; on POSIX the wait status (exit code '
                'times 256). Error "system: expected command string".',
        example='''
(system "gcc --version")
(system "exit 3")   ; => 3
''',
        where=PC, check=False,
    ),
    api('write-file-string', 'host',
        sig='(write-file-string path str)',
        desc='Create or replace a host file with the bytes of a string.',
        returns='#t when all bytes were written; #f when the file cannot be created. Error "%write-file-string: '
                'expected (filepath string)" when an argument is not a string.',
        example='''
(write-file-string "version.txt" "1.0.0\\n")   ; => #t
''',
        where=PC,
    ),
]
