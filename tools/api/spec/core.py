"""API entries: syntax, control, type, io, reflect, vm (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    # ---- syntax ------------------------------------------------------------
    api('when', 'syntax',
        sig='(when test body ...)',
        desc='Evaluate body ... in order when test is true (anything but #f).',
        returns='The value of the last body expression; void when test is #f.',
        example='''
(define level 80)
(when (> level 50) 'warned)          ; => warned
(void? (when (> level 90) 'alarm))   ; => #t
''',
    ),
    api('unless', 'syntax',
        sig='(unless test body ...)',
        desc='Evaluate body ... in order when test is #f.',
        returns='The value of the last body expression; void when test is true.',
        example='''
(define connected #f)
(unless connected 'offline)          ; => offline
(void? (unless #t 'never))           ; => #t
''',
    ),
    api('and', 'syntax',
        sig='(and test ...)',
        desc='Evaluate tests left to right, stopping at the first #f.',
        returns='#f at the first false test (the rest is not evaluated), else the value of the last '
                'test; #t with no tests.',
        example='''
(and 1 2 3)                          ; => 3
(and (> 5 1) (< 5 3))                ; => #f
(define lst '())
(and (pair? lst) (car lst))          ; => #f
(and)                                ; => #t
''',
    ),
    api('or', 'syntax',
        sig='(or test ...)',
        desc='Evaluate tests left to right, stopping at the first true value.',
        returns='The first value that is not #f (the rest is not evaluated); #f when every test is #f '
                'or there are none.',
        example='''
(or #f 2 (car '()))                  ; => 2
(or (memq 'x '(a b)) 'none)          ; => none
(or)                                 ; => #f
''',
    ),
    api('cond', 'syntax',
        sig='(cond (test expr ...) ... [else expr ...])',
        desc='Evaluate the clause of the first true test; (test => proc) calls proc on the test value.',
        returns='The value of the last expression of the selected clause; the test value for a clause '
                'without expressions; proc\'s result for =>. Void when no clause matches and there is '
                'no else.',
        example='''
(define (sign n) (cond ((< n 0) 'negative) ((= n 0) 'zero) (else 'positive)))
(sign -4)                            ; => negative
(cond ((assv 2 '((1 . one) (2 . two))) => cdr) (else 'none))  ; => two
(void? (cond (#f 1)))                ; => #t
''',
    ),
    api('if', 'syntax',
        sig='(if test then [else])',
        desc='Evaluate then when test is true (anything but #f, even 0 and ()), else the else branch.',
        returns='The value of the branch taken; void when test is #f and else is omitted.',
        example='''
(if (> 3 2) 'yes 'no)                ; => yes
(if '() 'true 'false)                ; => true
(void? (if #f #f))                   ; => #t
''',
    ),
    api('lambda', 'syntax',
        sig='(lambda params body ...)',
        desc='Create a procedure. params is (a b ...), (a b . rest) or one symbol bound to the list of all arguments.',
        returns='A procedure (a closure over the variables in scope).',
        example='''
(define add (lambda (a b) (+ a b)))
(add 2 3)                            ; => 5
((lambda (first . rest) rest) 1 2 3) ; => (2 3)
((lambda args (length args)) 'a 'b)  ; => 2
''',
        notes='Calls are not arity-checked: a missing argument reads as void and extra arguments are '
              'ignored.',
    ),
    api('let', 'syntax',
        sig='(let ((var val) ...) body ...) / (let name ((var val) ...) body ...)',
        desc='Bind local variables in parallel and evaluate body; the named form binds name to a loop procedure.',
        returns='The value of the last body expression.',
        example='''
(let ((x 2) (y 3)) (* x y))          ; => 6
(let loop ((i 0) (acc '()))
  (if (= i 3) (reverse acc) (loop (+ i 1) (cons i acc))))  ; => (0 1 2)
''',
    ),
    api('let*', 'syntax',
        sig='(let* ((var val) ...) body ...)',
        desc='Bind local variables sequentially (each init sees the previous ones) and evaluate body.',
        returns='The value of the last body expression.',
        example='''
(let* ((w 4) (area (* w w))) area)   ; => 16
(let* () 'empty)                     ; => empty
''',
    ),
    api('define', 'syntax',
        sig='(define var val) / (define (name args...) body...)',
        desc='Bind a global (at top level) or a local (at the start of a body); the second form defines a procedure.',
        returns='At top level the name as a symbol (a redefinition replaces the value); an internal '
                'define returns void.',
        example='''
(define limit 10)                    ; => limit
(define (square n) (* n n))
(square 7)                           ; => 49
(define (hyp2 a b) (define s (+ (square a) (square b))) s)
(hyp2 3 4)                           ; => 25
''',
    ),
    api('set!', 'syntax',
        sig='(set! var val)',
        desc='Assign a new value to an existing local or global variable.',
        returns='Void. An error "set!: unbound variable" when var is neither a local nor a defined '
                'global.',
        example='''
(define count 0)
(set! count (+ count 1))
count                                ; => 1
(set! no-such-var 5)                 ; => error: unbound variable
''',
    ),
    api('begin', 'syntax',
        sig='(begin expr ...)',
        desc='Evaluate expressions in order; at top level its definitions stay global.',
        returns='The value of the last expression; void for (begin).',
        example='''
(define total 0)
(begin (set! total (+ total 5)) (set! total (* total 2)) total)  ; => 10
(void? (begin))                      ; => #t
''',
    ),
    api('quote', 'syntax',
        sig="(quote datum) / 'datum",
        desc='Return datum without evaluating it.',
        returns='datum itself: a symbol, list, vector or constant. Quoted data is a constant: do not '
                'mutate it (it may live in the read-only Code ROM).',
        example='''
(quote (+ 1 2))                      ; => (+ 1 2)
'(a b c)                             ; => (a b c)
(car '(red green))                   ; => red
'#(1 2)                              ; => #(1 2)
''',
    ),
    api('define-syntax', 'syntax',
        sig='(define-syntax name (syntax-rules ...))',
        desc='Define a syntax-rules macro, expanded at compile time; locals introduced by the template are renamed.',
        returns='The macro name as a symbol. A use that matches no rule is a compile error '
                '"no syntax-rules pattern matched".',
        example='''
(define-syntax swap!
  (syntax-rules () ((_ a b) (let ((tmp a)) (set! a b) (set! b tmp)))))
(define x 1)
(define y 2)
(swap! x y)
(list x y)                           ; => (2 1)
''',
        notes='Template symbols that are pattern variables, literals, special forms or defined '
              'globals are kept as written; other symbols the template introduces get fresh names.',
    ),
    api('syntax-rules', 'syntax',
        sig='(syntax-rules (literal ...) (pattern template) ...)',
        desc='The rules of define-syntax: the first pattern matching the form selects its template; x ... repeats.',
        returns='A macro transformer; valid only as the second operand of define-syntax (elsewhere it '
                'is an unbound variable).',
        example='''
(define-syntax my-or
  (syntax-rules ()
    ((_) #f)
    ((_ e) e)
    ((_ e r ...) (let ((t e)) (if t t (my-or r ...))))))
(my-or #f #f 3)                      ; => 3
''',
        notes='The keyword position of a pattern is ignored (write _). Literals match only the same '
              'symbol.',
    ),
    api('define-macro', 'syntax',
        sig='(define-macro (name args...) body...) / (define-macro name proc)',
        desc='Define a non-hygienic macro: body builds the expansion from the unevaluated operands, at compile time.',
        returns='The macro name as a symbol.',
        example='''
(define-macro (inc! var . by)
  (list 'set! var (list '+ var (if (null? by) 1 (car by)))))
(define n 5)
(inc! n)
(inc! n 10)
n                                    ; => 16
''',
    ),
    api('void', 'type',
        sig='(void)',
        desc='Return the void value, the result of forms with nothing to return.',
        returns='Void (what (if #f #f) returns); arguments are ignored. write prints void as nothing.',
        example='''
(void? (void))                       ; => #t
(eq? (void) (if #f #f))              ; => #t
''',
    ),
    api('include-bytes', 'syntax',
        sig='(include-bytes path)',
        desc="The file's bytes as a string. Compiled code gets them at compile time (embedded in the image), e.g. fonts.",
        returns='A string of the file\'s bytes (NUL bytes included). A missing file is a compile error '
                '"include-bytes: cannot read file".',
        example='''
(define digits (include-bytes "fonts/digits-48.mfnt"))
(font-register! 3 digits)            ; => #t
(include-bytes "no-such-file.bin")   ; => error: include-bytes: cannot read file
''',
        check=False,
        notes='The path is relative to the working directory of the compiler (tools/build_apps.py: '
              'the repository root). The example needs a font file the test VM lacks.',
    ),
    # ---- control -----------------------------------------------------------
    api('exit', 'control',
        sig='(exit [code])',
        desc='Terminate the Scheme process with status code (default 0).',
        returns='Does not return. A code that is not an integer exits with status 0.',
        example='''
(exit)                               ; status 0
(exit 2)                             ; status 2
''',
        check=False,
        notes='Ends the host process (PC REPL). The board has no process to end: the C exit() of the '
              'firmware stops it, and the WASM simulator\'s exit() spins forever. Apps should return '
              'to the launcher instead.',
    ),
    api('error', 'control',
        sig='(error msg obj ...)',
        desc='Raise an error with message msg, aborting the current evaluation.',
        returns='Does not return. The error message is msg when it is a string, else "error"; the '
                'further arguments are ignored.',
        example='''
(define (safe-div a b)
  (if (= b 0) (error "safe-div: division by zero") (/ a b)))
(safe-div 10 2)                      ; => 5
(safe-div 1 0)                       ; => error: division by zero
''',
    ),
    api('call/cc', 'control',
        sig='(call/cc proc)',
        desc='Call proc with the current continuation k; calling (k v) returns v from call/cc.',
        returns='What proc returns, or the value passed to the continuation. Continuations are '
                're-entrant. An error when proc is not a procedure or not exactly 1 argument is given, '
                'and when k is called from inside a C primitive (for-each, map, ...).',
        example='''
(+ 1 (call/cc (lambda (k) (k 10) 20)))      ; => 11
(define (first-neg lst)
  (call/cc (lambda (return)
    (let loop ((l lst)) (cond ((null? l) #f) ((< (car l) 0) (return (car l))) (else (loop (cdr l))))))))
(first-neg '(3 -2 5))                       ; => -2
(call/cc (lambda (k) (for-each k '(1 2))))  ; => error: foreign C frame
''',
        notes='A continuation cannot be invoked across a C primitive that called back into Scheme '
              '(for-each, map, apply of a callback, ...): "cannot invoke continuation across '
              'foreign C frame boundary". Escape from a Scheme loop instead.',
    ),
    api('call-with-current-continuation', 'control',
        sig='(call-with-current-continuation proc)',
        desc='Full name of call/cc.',
        returns='As call/cc: what proc returns, or the value passed to the continuation.',
        example='''
(call-with-current-continuation (lambda (k) (+ 1 (k 42))))  ; => 42
(call-with-current-continuation (lambda (k) 7))             ; => 7
''',
    ),
    api('apply', 'control',
        sig='(apply proc arg1 ... rest)',
        desc='Call proc with arg1 ... followed by the elements of the list rest.',
        returns='What proc returns. An error with fewer than 2 arguments, when rest is not a proper '
                'list, or when proc is not callable.',
        example='''
(apply + 1 2 '(3 4))                 ; => 10
(apply max '(3 9 2))                 ; => 9
(apply list '())                     ; => ()
(apply + 1 2)                        ; => error: proper list
''',
    ),
    # ---- type --------------------------------------------------------------
    api('number?', 'type',
        sig='(number? obj)',
        desc='Test if obj is a number (fixnum, bignum or flonum).',
        returns='#t or #f.',
        example='''
(number? 42)                         ; => #t
(number? 3.5)                        ; => #t
(number? "42")                       ; => #f
''',
    ),
    api('integer?', 'type',
        sig='(integer? obj)',
        desc='Test if obj is an exact integer (fixnum or bignum); integral flonums such as 7.0 are not.',
        returns='#t or #f.',
        example='''
(integer? 7)                         ; => #t
(integer? 7.0)                       ; => #f
(integer? 'a)                        ; => #f
''',
    ),
    api('real?', 'type',
        sig='(real? obj)',
        desc='Test if obj is a real number; the same as number? (there are no complex numbers).',
        returns='#t or #f.',
        example='''
(real? 1.5)                          ; => #t
(real? 2)                            ; => #t
(real? "x")                          ; => #f
''',
    ),
    api('flonum?', 'type',
        sig='(flonum? obj)',
        desc='Test if obj is an inexact flonum.',
        returns='#t or #f.',
        example='''
(flonum? 1.5)                        ; => #t
(flonum? 2)                          ; => #f
(flonum? (/ 1 2))                    ; => #t
''',
    ),
    api('symbol?', 'type',
        sig='(symbol? obj)',
        desc='Test if obj is a symbol.',
        returns='#t or #f.',
        example='''
(symbol? 'alarm)                     ; => #t
(symbol? "alarm")                    ; => #f
(symbol? (string->symbol "x"))       ; => #t
''',
    ),
    api('procedure?', 'type',
        sig='(procedure? obj)',
        desc='Test if obj is a procedure: a closure, a primitive or a continuation.',
        returns='#t or #f.',
        example='''
(procedure? car)                     ; => #t
(procedure? (lambda (x) x))          ; => #t
(procedure? 'car)                    ; => #f
''',
    ),
    api('char?', 'type',
        sig='(char? obj)',
        desc='Test if obj is a character. Characters are fixnum code points (#\\a is 97), so any fixnum passes.',
        returns='#t for any fixnum, else #f.',
        example='''
(char? #\\a)                          ; => #t
(char? "a")                          ; => #f
(char? 97)                           ; => #t
''',
    ),
    api('boolean?', 'type',
        sig='(boolean? obj)',
        desc='Test if obj is a boolean (#t or #f).',
        returns='#t or #f.',
        example='''
(boolean? #f)                        ; => #t
(boolean? '())                       ; => #f
(boolean? 0)                         ; => #f
''',
    ),
    api('eq?', 'type',
        sig='(eq? obj1 obj2)',
        desc='Identity: the same object; fixnums, characters, symbols, booleans and () compare by value.',
        returns='#t or #f (#f also for a wrong argument count).',
        example='''
(eq? 'a 'a)                          ; => #t
(eq? (list 1) (list 1))              ; => #f
(let ((p (list 1))) (eq? p p))       ; => #t
(eq? 100 100)                        ; => #t
''',
        notes='Equal literal constants of one compiled unit may be shared, so (eq? "ab" "ab") can be #t.',
    ),
    api('equal?', 'type',
        sig='(equal? obj1 obj2)',
        desc='Structural equality: pairs, vectors and strings element by element, numbers by type and value.',
        returns='#t or #f (1 and 1.0 are not equal?).',
        example='''
(equal? '(1 (2 #(3))) (list 1 (list 2 (vector 3))))  ; => #t
(equal? "ab" (string-append "a" "b"))                ; => #t
(equal? 1 1.0)                                       ; => #f
''',
    ),
    api('not', 'type',
        sig='(not obj)',
        desc='#t when obj is #f, else #f (only #f is false; () and 0 are true).',
        returns='#t or #f.',
        example='''
(not #f)                             ; => #t
(not '())                            ; => #f
(not 0)                              ; => #f
''',
    ),
    api('void?', 'type',
        sig='(void? obj)',
        desc='Test if obj is the void value.',
        returns='#t or #f.',
        example='''
(void? (void))                       ; => #t
(void? (if #f #f))                   ; => #t
(void? '())                          ; => #f
''',
    ),
    api('eqv?', 'type',
        sig='(eqv? a b)',
        desc='eq? that also compares numbers by value; an exact and an inexact number are never eqv? (0 and 0.0).',
        returns='#t or #f.',
        example='''
(eqv? 'a 'a)                         ; => #t
(eqv? (/ 5 2) (/ 5 2))               ; => #t
(eqv? 2 2.0)                         ; => #f
(eqv? (list 1) (list 1))             ; => #f
''',
    ),
    api('list?', 'type',
        sig='(list? obj)',
        desc='Test if obj is a proper list (ending in ()).',
        returns='#t or #f.',
        example='''
(list? '(1 2))                       ; => #t
(list? '())                          ; => #t
(list? '(1 . 2))                     ; => #f
(list? "abc")                        ; => #f
''',
        notes='Does not detect cycles: a circular list never returns.',
    ),
    # ---- io ----------------------------------------------------------------
    api('display', 'io',
        sig='(display obj)',
        desc='Print obj to the console in human-readable form (strings without quotes).',
        returns='Void.',
        example='''
(display "Temp: ")                   ; prints Temp:
(display 21.5)                       ; prints 21.5
(display '(1 "two" c))               ; prints (1 two c)
(newline)
''',
        notes='Characters are code points and print as numbers (#\\a prints 97); void prints nothing.',
    ),
    api('write', 'io',
        sig='(write obj)',
        desc='Print obj to the console in read-back syntax (strings in quotes).',
        returns='Void.',
        example='''
(write "hi")                         ; prints "hi"
(write '(1 "two" 3.5))               ; prints (1 "two" 3.5)
(newline)
''',
        notes='Strings print in double quotes with \\" \\\\ \\n \\t \\r escaped (other control bytes as \\xHH;); characters print as numbers; void prints nothing.',
    ),
    api('newline', 'io',
        sig='(newline)',
        desc='Print a newline character to the console.',
        returns='Void.',
        example='''
(display "line 1")
(newline)
(void? (newline))                    ; => #t
''',
    ),
    api('print', 'io',
        sig='(print obj ...)',
        desc='Print arguments separated by spaces, followed by a newline.',
        returns='Void.',
        example='''
(print "x =" 42)                     ; prints x = 42
(print)                              ; prints an empty line
''',
        where=PC,
    ),
    api('load', 'io',
        sig='(load filepath)',
        desc='Read, compile and evaluate every expression of a Scheme source file. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='The value of the last expression of the file. An error when the file cannot be '
                'opened, or when the VM has no compiler (the firmware VM: "compiler not available").',
        example='''
(load "lib/util.scm")
(load "missing.scm")                 ; => error: cannot open file
''',
        check=False,
        notes='Needs the Scheme compiler in the VM (PC REPL); the firmware runs precompiled code.',
        where=PC,
    ),
    api('dump-fasl', 'io',
        sig="(dump-fasl filepath ['portable|'native])",
        desc="Serialize the VM heap to a FASL file; the default portable 32-bit layout loads on every target, 'native is for load-fasl-xip.",
        returns="#t. An error when the file cannot be created or written, or the layout is not "
                "'portable or 'native.",
        example='''
(define high-score 120)
(dump-fasl "state.fasl")             ; => #t
(dump-fasl "app.fasl" 'native)       ; => #t
(dump-fasl "state.fasl" 'fast)       ; => error: layout must be
''',
        check=False,
        notes='The example writes files into the working directory. A failed dump removes the '
              'partial file.',
    ),
    api('load-fasl', 'io',
        sig='(load-fasl filepath)',
        desc='Replace the VM heap (globals included) with a FASL image written by dump-fasl.',
        returns='#t. An error when the file cannot be opened or is not a FASL image ("invalid FASL '
                'magic header").',
        example='''
(load-fasl "state.fasl")             ; => #t
high-score                           ; => 120
''',
        check=False,
        notes='The code that called load-fasl does not continue: its top-level form returns #t at '
              'once, so call it last in a form. The example needs the file of dump-fasl.',
    ),
    api('load-fasl-xip', 'io',
        sig='(load-fasl-xip filepath)',
        desc='Load a FASL image for execute-in-place: its objects stay in the read-only image instead of being copied to the heap.',
        returns='#t; (xip-active?) is #t afterwards. An error when the file cannot be opened or is '
                'not a FASL image.',
        example='''
(load-fasl-xip "app.fasl")           ; => #t
(xip-active?)                        ; => #t
''',
        check=False,
        notes="Write the image with (dump-fasl path 'native). As with load-fasl, the calling "
              'top-level form returns #t at once. The example needs the file of dump-fasl.',
    ),
    api('eof-object', 'io',
        sig='(eof-object)',
        desc='The end-of-file object.',
        returns='The unique end-of-file object, written #<eof>.',
        example='''
(eof-object)                         ; => #<eof>
(eq? (eof-object) (eof-object))      ; => #t
''',
    ),
    api('eof-object?', 'io',
        sig='(eof-object? x)',
        desc='True for the end-of-file object.',
        returns='#t or #f.',
        example='''
(eof-object? (eof-object))           ; => #t
(eof-object? "")                     ; => #f
''',
    ),
    # ---- reflect -----------------------------------------------------------
    api('help', 'reflect',
        sig='(help [name])',
        desc='Print the syntax, category and description of name (a symbol or string); (help) lists every entry.',
        returns='Void (the text goes to the console). An error when name is not a symbol or string, or '
                'with more than one argument.',
        example='''
(help 'gpio-write)
(help "car")
(help 42)                            ; => error: expected symbol or string
''',
        notes='An unknown name prints "No documentation found". A firmware built with '
              'MINISCHEME_NO_HELP prints that help is disabled.',
    ),
    api('global-names', 'reflect',
        sig='(global-names)',
        desc='Every global name, including primitives not used yet.',
        returns='A list of symbols in no particular order, internal %-prefixed names included.',
        example='''
(pair? (memq 'car (global-names)))   ; => #t
(define my-setting 1)
(pair? (memq 'my-setting (global-names)))  ; => #t
''',
    ),
    api('user-globals', 'reflect',
        sig='(user-globals)',
        desc='Globals defined after the baseline environment.',
        returns='A list of symbols, oldest definition first; () when nothing was defined.',
        example='''
(user-globals)                       ; => ()
(define threshold 30)
(define (alarm? t) (> t threshold))
(user-globals)                       ; => (threshold alarm?)
''',
    ),
    api('defined?', 'reflect',
        sig="(defined? 'name)",
        desc='True when name has a global binding or primitive.',
        returns='#t or #f (#f for special forms such as if, and for reserved or device-only names the '
                'VM lacks). An error when the argument is not a symbol.',
        example='''
(defined? 'car)                      ; => #t
(defined? 'my-helper)                ; => #f
(define (my-helper) 1)
(defined? 'my-helper)                ; => #t
(defined? "car")                     ; => error: expected symbol
''',
    ),
    # ---- vm ----------------------------------------------------------------
    api('xip-active?', 'vm',
        sig='(xip-active?)',
        desc='True when a FASL image runs in place (load-fasl-xip); an app in the Code ROM shows in vm-rom-bytes instead.',
        returns='#t or #f.',
        example='''
(xip-active?)                        ; => #f
''',
    ),
    api('xip-stats', 'vm',
        sig='(xip-stats)',
        desc='The XIP image: an alist of its base address, size in bytes and count of C function references.',
        returns="() when no XIP image is loaded, else ((cfuncs . n) (rom-size . bytes) "
                "(rom-base . address)).",
        example='''
(xip-stats)                          ; => ()
''',
    ),
    api('vm-allocated-bytes', 'vm',
        sig='(vm-allocated-bytes)',
        desc='Bytes in use in the VM heap (nursery and tenured space, garbage not collected yet included).',
        returns='A non-negative integer.',
        example='''
(integer? (vm-allocated-bytes))      ; => #t
(< 0 (vm-allocated-bytes) (vm-heap-size))  ; => #t
''',
    ),
    api('vm-heap-size', 'vm',
        sig='(vm-heap-size)',
        desc='VM heap capacity in bytes (the tenured space; the nursery is extra).',
        returns='A positive integer.',
        example='''
(> (vm-heap-size) 0)                 ; => #t
''',
    ),
    api('vm-stack-depth', 'vm',
        sig='(vm-stack-depth)',
        desc='Value stack slots in use.',
        returns='A non-negative integer.',
        example='''
(define base (vm-stack-depth))
(define (probe a b) (vm-stack-depth))
(> (probe 1 2) base)                 ; => #t
''',
    ),
    api('vm-frame-depth', 'vm',
        sig='(vm-frame-depth)',
        desc='Call frames in use.',
        returns='A positive integer.',
        example='''
(define (probe) (vm-frame-depth))
(define (caller) (car (list (probe))))
(- (caller) (probe))                 ; => 1
''',
        notes='Tail calls reuse the frame, so (define (f) (g)) does not add one.',
    ),
    api('vm-rom-bytes', 'vm',
        sig='(vm-rom-bytes)',
        desc='Size of the attached Code ROM image (0 when the app runs from RAM).',
        returns='A non-negative integer.',
        example='''
(vm-rom-bytes)                       ; => 0
''',
    ),
    api('vm-stats', 'vm',
        sig='(vm-stats)',
        desc='VM counters: GCs, allocation, live and peak heap, stack and frame peaks.',
        returns='An alist of integers: alloc-kb (allocated since start), minor-gcs, major-gcs, '
                'live-bytes and live-peak (tenured bytes after the last / largest GC), stack-peak, '
                'frame-peak, stack-slots, frame-slots (capacities), rom-bytes.',
        example='''
(map car (vm-stats))
; => (alloc-kb minor-gcs major-gcs live-bytes live-peak stack-peak frame-peak stack-slots frame-slots rom-bytes)
(integer? (cdr (assq 'minor-gcs (vm-stats))))  ; => #t
''',
    ),
    api('vm-stack-trace', 'vm',
        sig='(vm-stack-trace [on?])',
        desc='Query or enable/disable stack trace capture upon errors (enabled by default in WASM, disabled on hardware).',
        returns='A boolean indicating whether stack trace capture is enabled.',
        example='''
(vm-stack-trace)                      ; => #f
(vm-stack-trace #t)                   ; => #t
(vm-stack-trace #f)                   ; => #f
''',
    ),
]
