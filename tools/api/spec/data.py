"""API entries: math, list, vector, string, char (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

# Shared remarks for the reference (not compiled into the firmware)
_NUMBERS = ('Numbers are exact integers (fixnums, promoted to bignums automatically when a result '
            'leaves the fixnum range: 29 bits on the 32-bit device and WASM, 61 bits on a 64-bit PC) '
            'or inexact flonums (C doubles). There are no rationals or complex numbers. A flonum '
            'argument makes the result a flonum. `write` prints a flonum with up to 15 significant '
            'digits and a trailing `.0` when it is integral (`3.5`, `2.0`, `0.333333333333333`).')
_CHARS = ('MiniScheme has no separate character type: a character is its integer code. `#\\a` '
          'reads as 97, and `write` prints characters as integers.')
_BYTES = ('Strings are UTF-8 byte strings: lengths and indexes count bytes, and the elements '
          'are byte values 0..255, so a non-ASCII character spans several positions.')
_ROM = ('Quoted literals of an app loaded from the read-only code image (XIP) cannot be '
        'modified: mutating one raises "cannot modify a literal constant". Mutate freshly '
        'allocated data (list, vector, cons, make-vector) instead.')

APIS = [
    # ---- math --------------------------------------------------------------
    api('+', 'math',
        sig='(+ z ...)',
        desc='Return the sum of the arguments (0 if no arguments).',
        returns='The sum: an exact integer (a bignum when it overflows the fixnum range), or a '
                'flonum when any argument is a flonum; an error when an argument is not a number.',
        example='''
(+ 1 2 3)            ; => 6
(+ 1 2.5)            ; => 3.5
(+)                  ; => 0
(define big (expt 2 62))
(+ big 1)            ; => 4611686018427387905
(+ 1 "2")            ; => error: expected number
''',
        notes=_NUMBERS,
    ),
    api('-', 'math',
        sig='(- z1 [z2 ...])',
        desc='Subtract following arguments from z1, or negate z1.',
        returns='The difference, or the negation of z1 alone: exact integer or flonum as for `+`; '
                'an error with no argument or when an argument is not a number.',
        example='''
(- 10 1 2)           ; => 7
(- 5)                ; => -5
(- 0.5 1)            ; => -0.5
(-)                  ; => error: requires at least 1 argument
''',
    ),
    api('*', 'math',
        sig='(* z ...)',
        desc='Return the product of the arguments (1 if no arguments).',
        returns='The product: an exact integer (a bignum when it overflows), or a flonum when any '
                'argument is a flonum; an error when an argument is not a number.',
        example='''
(* 2 3 4)            ; => 24
(* 2 1.5)            ; => 3.0
(*)                  ; => 1
(define n (expt 10 10))
(* n n)              ; => 100000000000000000000
''',
    ),
    api('/', 'math',
        sig='(/ z1 [z2 ...])',
        desc='Divide z1 by the following arguments, or return 1/z1. An inexact quotient of '
             'integers is a flonum (no rationals).',
        returns='An exact integer when every division is exact, otherwise a flonum; an error '
                '"division by zero" when a divisor is 0 or 0.0, or when an argument is not a number.',
        example='''
(/ 8 2)              ; => 4
(/ 7 2)              ; => 3.5
(/ 1 3)              ; => 0.333333333333333
(/ 2)                ; => 0.5
(/ 7 0)              ; => error: division by zero
''',
    ),
    api('<', 'math',
        sig='(< x1 x2 ...)',
        desc='Test if numbers are strictly monotonically increasing.',
        returns='#t or #f; exact and inexact numbers compare by value. With fewer than two '
                'arguments #t. An error when a compared argument is not a number (comparison stops '
                'at the first #f).',
        example='''
(< 1 2 3)            ; => #t
(< 1 3 2)            ; => #f
(< 1 2.5)            ; => #t
(< 1 'a)             ; => error: expected numbers
''',
    ),
    api('>', 'math',
        sig='(> x1 x2 ...)',
        desc='Test if numbers are strictly monotonically decreasing.',
        returns='#t or #f, as for `<`; an error when a compared argument is not a number.',
        example='''
(> 3 2 1)            ; => #t
(> 3 3)              ; => #f
(> 2.5 2)            ; => #t
''',
    ),
    api('<=', 'math',
        sig='(<= x1 x2 ...)',
        desc='Test if numbers are monotonically non-decreasing.',
        returns='#t or #f, as for `<`; an error when a compared argument is not a number.',
        example='''
(<= 1 1 2)           ; => #t
(<= 2 1)             ; => #f
(let ((t 21.5)) (<= 18 t 25))  ; => #t
''',
    ),
    api('>=', 'math',
        sig='(>= x1 x2 ...)',
        desc='Test if numbers are monotonically non-increasing.',
        returns='#t or #f, as for `<`; an error when a compared argument is not a number.',
        example='''
(>= 3 3 1)           ; => #t
(>= 1 2)             ; => #f
''',
    ),
    api('=', 'math',
        sig='(= z1 z2 ...)',
        desc='Test if all numbers are numerically equal.',
        returns='#t or #f; an exact and an inexact number are equal when their values are '
                '(`(= 1 1.0)` is #t). An error when a compared argument is not a number.',
        example='''
(= 2 2 2)            ; => #t
(= 1 1.0)            ; => #t
(= 1 2)              ; => #f
''',
    ),
    api('modulo', 'math',
        sig='(modulo n1 n2)',
        desc='Return n1 modulo n2: the remainder with the sign of n2.',
        returns='An exact integer with the sign of n2 (floor division); an error when an argument '
                'is not an exact integer (flonums are refused) or n2 is 0.',
        example='''
(modulo 13 4)        ; => 1
(modulo -7 2)        ; => 1
(modulo 7 -2)        ; => -1
(modulo 7 0)         ; => error: division by zero
''',
    ),
    api('remainder', 'math',
        sig='(remainder n1 n2)',
        desc='Return the remainder of dividing n1 by n2, with the sign of n1.',
        returns='An exact integer with the sign of n1 (truncating division); an error when an '
                'argument is not an exact integer or n2 is 0.',
        example='''
(remainder 17 5)     ; => 2
(remainder -7 2)     ; => -1
(remainder 17 -5)    ; => 2
''',
    ),
    api('quotient', 'math',
        sig='(quotient n1 n2)',
        desc='Return the integer quotient of dividing n1 by n2, truncated towards zero.',
        returns='An exact integer (bignums allowed); an error when an argument is not an exact '
                'integer (`(quotient 7.0 2)` fails) or n2 is 0.',
        example='''
(quotient 17 5)      ; => 3
(quotient -7 2)      ; => -3
(quotient 7.0 2)     ; => error: expected 2 integers
''',
    ),
    api('abs', 'math',
        sig='(abs x)',
        desc='Return the absolute value of x.',
        returns='A number of the same exactness as x; an error when x is not a number.',
        example='''
(abs -5)             ; => 5
(abs -2.5)           ; => 2.5
(abs 3)              ; => 3
''',
    ),
    api('sqrt', 'math',
        sig='(sqrt z)',
        desc='Return the square root of z as a flonum.',
        returns='A flonum, also for exact arguments (`(sqrt 16)` is 4.0); an error when z is '
                'negative or not a number.',
        example='''
(sqrt 16)            ; => 4.0
(sqrt 2)             ; => 1.4142135623731
(sqrt -1)            ; => error: negative number
''',
    ),
    api('sin', 'math',
        sig='(sin z)',
        desc='Return the sine of z (in radians).',
        returns='A flonum; an error when z is not a number.',
        example='''
(sin 0)              ; => 0.0
(sin 1.5707963267949)  ; => 1.0
''',
    ),
    api('cos', 'math',
        sig='(cos z)',
        desc='Return the cosine of z (in radians).',
        returns='A flonum; an error when z is not a number.',
        example='''
(cos 0)              ; => 1.0
(cos 3.14159265358979)  ; => -1.0
''',
    ),
    api('tan', 'math',
        sig='(tan z)',
        desc='Return the tangent of z (in radians).',
        returns='A flonum; an error when z is not a number.',
        example='''
(tan 0)              ; => 0.0
(tan 0.785398163397448)  ; => 0.999999999999999
''',
    ),
    api('asin', 'math',
        sig='(asin z)',
        desc='Return the arcsine of z, in radians.',
        returns='A flonum in [-pi/2, pi/2]; NaN when z is outside [-1, 1]; an error when z is not '
                'a number.',
        example='''
(asin 1)             ; => 1.5707963267949
(asin 0)             ; => 0.0
''',
    ),
    api('acos', 'math',
        sig='(acos z)',
        desc='Return the arccosine of z, in radians.',
        returns='A flonum in [0, pi]; NaN when z is outside [-1, 1]; an error when z is not a '
                'number.',
        example='''
(acos 1)             ; => 0.0
(acos -1)            ; => 3.14159265358979
''',
    ),
    api('atan', 'math',
        sig='(atan y [x])',
        desc='Return the arctangent of y, or with x the angle of the point (x, y) (atan2).',
        returns='A flonum in radians: in [-pi/2, pi/2] for one argument, in [-pi, pi] for two; an '
                'error when an argument is not a number.',
        example='''
(atan 1)             ; => 0.785398163397448
(atan 1 0)           ; => 1.5707963267949
(atan 0 -1)          ; => 3.14159265358979
''',
    ),
    api('exp', 'math',
        sig='(exp z)',
        desc='Return e raised to the power of z.',
        returns='A flonum; an error when z is not a number.',
        example='''
(exp 0)              ; => 1.0
(exp 1)              ; => 2.71828182845905
''',
    ),
    api('log', 'math',
        sig='(log z)',
        desc='Return the natural logarithm of z.',
        returns='A flonum; an error when z is not positive or not a number. There is no '
                'two-argument form: divide by `(log base)`.',
        example='''
(log 1)              ; => 0.0
(log 100)            ; => 4.60517018598809
(/ (log 1000) (log 10))  ; => 3.0
(log 0)              ; => error: expected positive number
''',
    ),
    api('expt', 'math',
        sig='(expt z1 z2)',
        desc='Return z1 raised to the power of z2.',
        returns='An exact integer (bignum when large) for an exact base and a non-negative exact '
                'exponent; otherwise a flonum (also for a negative exact exponent); an error when '
                'an argument is not a number.',
        example='''
(expt 2 10)          ; => 1024
(expt 2 100)         ; => 1267650600228229401496703205376
(expt 2 -1)          ; => 0.5
(expt 4 0.5)         ; => 2.0
''',
    ),
    api('floor', 'math',
        sig='(floor x)',
        desc='Return the largest integer <= x.',
        returns='x itself for an exact integer, an integral flonum for a flonum (use '
                '`inexact->exact` for an exact result); an error when x is not a number.',
        example='''
(floor 2.5)          ; => 2.0
(floor -2.5)         ; => -3.0
(floor 7)            ; => 7
(inexact->exact (floor 2.7))  ; => 2
''',
    ),
    api('ceiling', 'math',
        sig='(ceiling x)',
        desc='Return the smallest integer >= x.',
        returns='x itself for an exact integer, an integral flonum for a flonum; an error when x '
                'is not a number.',
        example='''
(ceiling 2.1)        ; => 3.0
(ceiling -2.1)       ; => -2.0
(ceiling 4)          ; => 4
''',
    ),
    api('round', 'math',
        sig='(round x)',
        desc='Round x to the nearest integer; halves round away from zero (2.5 -> 3.0).',
        returns='x itself for an exact integer, an integral flonum for a flonum; an error when x '
                'is not a number.',
        example='''
(round 2.4)          ; => 2.0
(round 2.5)          ; => 3.0
(round -2.5)         ; => -3.0
(round 7)            ; => 7
''',
        notes='Unlike R7RS (round half to even), halves round away from zero (C `round`).',
    ),
    api('truncate', 'math',
        sig='(truncate x)',
        desc='Truncate x towards zero.',
        returns='x itself for an exact integer, an integral flonum for a flonum; an error when x '
                'is not a number.',
        example='''
(truncate 2.7)       ; => 2.0
(truncate -2.7)      ; => -2.0
(truncate 5)         ; => 5
''',
    ),
    api('exact?', 'math',
        sig='(exact? z)',
        desc='Test if z is an exact number (fixnum or bignum).',
        returns='#t for an exact integer, #f for a flonum; #f (no error) for a non-number.',
        example='''
(exact? 1)           ; => #t
(exact? 1.0)         ; => #f
(exact? (expt 2 100))  ; => #t
''',
    ),
    api('inexact?', 'math',
        sig='(inexact? z)',
        desc='Test if z is an inexact number (flonum).',
        returns='#t for a flonum, #f for an exact integer; #f (no error) for a non-number.',
        example='''
(inexact? 1.5)       ; => #t
(inexact? 2)         ; => #f
''',
    ),
    api('exact->inexact', 'math',
        sig='(exact->inexact z)',
        desc='Convert an exact number to an inexact flonum.',
        returns='A flonum (a flonum argument is returned as a flonum of the same value; large '
                'bignums lose precision); an error when z is not a number.',
        example='''
(exact->inexact 3)   ; => 3.0
(exact->inexact 1.5) ; => 1.5
(/ (exact->inexact 1) 4)  ; => 0.25
''',
    ),
    api('inexact->exact', 'math',
        sig='(inexact->exact z)',
        desc='Convert z to an exact integer, rounding a flonum to the nearest integer (halves '
             'away from zero).',
        returns='An exact integer: z itself when exact, otherwise the flonum rounded to the nearest integer (no rationals), a bignum when large; an error when z is not a number, or is a NaN or infinity.',
        example='''
(inexact->exact 2.6)  ; => 3
(inexact->exact 2.5)  ; => 3
(inexact->exact -2.4) ; => -2
(inexact->exact 7)    ; => 7
''',
    ),
    api('max', 'math',
        sig='(max x1 x2 ...)',
        desc='The largest argument.',
        returns='The largest argument itself, unconverted: `(max 3 2.0)` is the exact 3 (no '
                'inexact contagion, unlike R7RS); an error with no argument or a non-number.',
        example='''
(max 1 5 3)          ; => 5
(max 1 2.0)          ; => 2.0
(max 3 2.0)          ; => 3
(max)                ; => error: requires at least 1 argument
''',
    ),
    api('min', 'math',
        sig='(min x1 x2 ...)',
        desc='The smallest argument.',
        returns='The smallest argument itself, unconverted (no inexact contagion); an error with '
                'no argument or a non-number.',
        example='''
(min 4 1 3)          ; => 1
(min 1.0 2)          ; => 1.0
(min 0 (max 255 300))  ; => 0
''',
    ),
    # ---- list --------------------------------------------------------------
    api('cons', 'list',
        sig='(cons obj1 obj2)',
        desc='Construct a new pair with car obj1 and cdr obj2.',
        returns='A newly allocated pair; an error unless exactly 2 arguments are given.',
        example='''
(cons 1 2)           ; => (1 . 2)
(cons 1 '(2 3))      ; => (1 2 3)
(cons 'a '())        ; => (a)
''',
    ),
    api('car', 'list',
        sig='(car pair)',
        desc='Return the first element of pair.',
        returns='The car of pair; an error when pair is not a pair (including the empty list).',
        example='''
(car '(1 2 3))       ; => 1
(car '((a . b) c))   ; => (a . b)
(car '())            ; => error: requires a pair
''',
    ),
    api('cdr', 'list',
        sig='(cdr pair)',
        desc='Return the second element of pair.',
        returns='The cdr of pair (the rest of a list); an error when pair is not a pair.',
        example='''
(cdr '(1 2 3))       ; => (2 3)
(cdr '(1 . 2))       ; => 2
(cdr '())            ; => error: requires a pair
''',
    ),
    api('set-car!', 'list',
        sig='(set-car! pair obj)',
        desc='Mutate the car field of pair.',
        returns='Void; an error when pair is not a pair or is a quoted literal in the read-only '
                'code image.',
        example='''
(define p (cons 1 2))
(set-car! p 9)
p                    ; => (9 . 2)
''',
        notes=_ROM,
    ),
    api('set-cdr!', 'list',
        sig='(set-cdr! pair obj)',
        desc='Mutate the cdr field of pair.',
        returns='Void; an error when pair is not a pair or is a quoted literal in the read-only '
                'code image.',
        example='''
(define p (list 1 2))
(set-cdr! p '(3 4))
p                    ; => (1 3 4)
''',
        notes=_ROM,
    ),
    api('pair?', 'list',
        sig='(pair? obj)',
        desc='Return #t if obj is a pair, #f otherwise.',
        returns='#t or #f; the empty list is not a pair.',
        example='''
(pair? '(1))         ; => #t
(pair? '(1 . 2))     ; => #t
(pair? '())          ; => #f
(pair? (vector 1))   ; => #f
''',
    ),
    api('null?', 'list',
        sig='(null? obj)',
        desc='Return #t if obj is empty list (), #f otherwise.',
        returns='#t only for the empty list; #f for anything else (also #f and "").',
        example='''
(null? '())          ; => #t
(null? '(1))         ; => #f
(null? #f)           ; => #f
''',
    ),
    api('list', 'list',
        sig='(list obj ...)',
        desc='Return a newly allocated list of its arguments.',
        returns='A new proper list; `()` with no arguments.',
        example='''
(list 1 2 3)         ; => (1 2 3)
(list 'a "b" (+ 1 2))  ; => (a "b" 3)
(list)               ; => ()
''',
    ),
    api('length', 'list',
        sig='(length list)',
        desc='Return the number of elements in list.',
        returns='An exact integer; an error "not a proper list" for an improper list or a '
                'non-list.',
        example='''
(length '(1 2 3))    ; => 3
(length '())         ; => 0
(length '(1 . 2))    ; => error: not a proper list
''',
    ),
    api('reverse', 'list',
        sig='(reverse list)',
        desc='Return a newly allocated list with elements in reverse order.',
        returns='A new list; the argument is not changed. Not checked: the tail of an improper '
                'list is dropped and a non-list gives `()`.',
        example='''
(reverse '(1 2 3))   ; => (3 2 1)
(reverse '())        ; => ()
''',
    ),
    api('append', 'list',
        sig='(append list ...)',
        desc='Concatenate lists into a single list.',
        returns='A list whose elements are copied from all arguments but the last, which is '
                'shared (it may be any object, giving an improper list); `()` with no arguments. '
                'Not checked: a non-list argument before the last counts as empty.',
        example='''
(append '(1) '(2 3) '(4))  ; => (1 2 3 4)
(append '(1 2) 3)    ; => (1 2 . 3)
(append)             ; => ()
''',
    ),
    api('map', 'list',
        sig='(map proc list ...)',
        desc='Apply proc element-wise across lists and return list of results.',
        returns='A new list of the results, in order; with several lists it stops at the end of '
                'the shortest. An error with no list or more than 4 lists, when proc is not a '
                'procedure, or when proc raises one.',
        example='''
(map (lambda (x) (* x x)) '(1 2 3))  ; => (1 4 9)
(map + '(1 2 3) '(10 20))  ; => (11 22)
(map car '((a 1) (b 2)))  ; => (a b)
''',
    ),
    api('filter', 'list',
        sig='(filter pred list)',
        desc='Return a list of elements satisfying predicate pred.',
        returns='A new list of the elements for which pred returns a true value, in their '
                'original order; an error unless 2 arguments are given or when pred raises one.',
        example='''
(filter (lambda (x) (> x 1)) '(1 2 3))  ; => (2 3)
(filter string? '(1 "a" b "c"))  ; => ("a" "c")
(filter pair? '())   ; => ()
''',
    ),
    api('fold-left', 'list',
        sig='(fold-left proc init list)',
        desc='Left-associative fold: (proc ... (proc init x1) x2).',
        returns='The last value of proc, called as (proc acc x) for each element from the left; '
                'init for an empty list. Exactly one list: an error otherwise.',
        example='''
(fold-left + 0 '(1 2 3))  ; => 6
(fold-left - 0 '(1 2 3))  ; => -6
(fold-left (lambda (acc x) (cons x acc)) '() '(1 2 3))  ; => (3 2 1)
''',
    ),
    api('fold-right', 'list',
        sig='(fold-right proc init list)',
        desc='Right-associative fold: (proc x1 (proc x2 ... init)).',
        returns='The last value of proc, called as (proc x acc) for each element from the right; '
                'init for an empty list. Exactly one list: an error otherwise.',
        example='''
(fold-right cons '() '(1 2 3))  ; => (1 2 3)
(fold-right - 0 '(1 2 3))  ; => 2
''',
    ),
    api('caar', 'list',
        sig='(caar x)',
        desc='Equivalent to (car (car x)).',
        returns='The car of the car of x; an error when x or its car is not a pair.',
        example='''
(caar '((1 2) 3))    ; => 1
(caar '(1))          ; => error: requires a pair in car
''',
    ),
    api('cadr', 'list',
        sig='(cadr x)',
        desc='Equivalent to (car (cdr x)): the second element.',
        returns='The second element of x; an error when x or its cdr is not a pair.',
        example='''
(cadr '(1 2 3))      ; => 2
(cadr '(1))          ; => error: requires a pair in cdr
''',
    ),
    api('cdar', 'list',
        sig='(cdar x)',
        desc='Equivalent to (cdr (car x)).',
        returns='The cdr of the car of x; an error when x or its car is not a pair.',
        example='''
(cdar '((1 2) 3))    ; => (2)
(cdar '((a . b)))    ; => b
''',
    ),
    api('cddr', 'list',
        sig='(cddr x)',
        desc='Equivalent to (cdr (cdr x)).',
        returns='x without its first two elements; an error when x or its cdr is not a pair.',
        example='''
(cddr '(1 2 3))      ; => (3)
(cddr '(1 2))        ; => ()
''',
    ),
    api('list-tail', 'list',
        sig='(list-tail list k)',
        desc='The list without its first k elements.',
        returns='The k-th tail of list (shared, not copied); an error when k is not a '
                'non-negative fixnum or the list has fewer than k elements.',
        example='''
(list-tail '(1 2 3 4) 2)  ; => (3 4)
(list-tail '(1 2) 2)  ; => ()
(list-tail '(1 2) 3)  ; => error: index out of range
''',
    ),
    api('memv', 'list',
        sig='(memv x list)',
        desc='First tail whose car is eqv? to x, or #f.',
        returns='The first tail of list whose car is eqv? to x (numbers compare by value and '
                'exactness), or #f; #f also when list is not a list.',
        example='''
(memv 2 '(1 2 3))    ; => (2 3)
(memv 1.5 '(1 1.5 2))  ; => (1.5 2)
(memv 5 '(1 2 3))    ; => #f
''',
    ),
    api('assv', 'list',
        sig='(assv key alist)',
        desc='First pair whose car is eqv? to key, or #f.',
        returns='The first pair of alist whose car is eqv? to key, or #f; elements that are not '
                'pairs are skipped.',
        example='''
(assv 2 '((1 . one) (2 . two)))  ; => (2 . two)
(assv 9 '((1 . one)))  ; => #f
''',
    ),
    api('cdddr', 'list',
        sig='(cdddr x)',
        desc='(cdr (cdr (cdr x))): x without its first three elements.',
        returns='The third tail of x; an error "list too short" when x has fewer than 3 pairs.',
        example='''
(cdddr '(1 2 3 4))   ; => (4)
(cdddr '(1 2))       ; => error: list too short
''',
    ),
    api('cadddr', 'list',
        sig='(cadddr x)',
        desc='Fourth element: (car (cdddr x)).',
        returns='The fourth element of x; an error "list too short" when x has fewer than 4 '
                'elements.',
        example='''
(cadddr '(1 2 3 4))  ; => 4
(cadddr '(1 2 3))    ; => error: list too short
''',
    ),
    api('cddddr', 'list',
        sig='(cddddr x)',
        desc='(cdr (cdddr x)): x without its first four elements.',
        returns='The fourth tail of x; an error "list too short" when x has fewer than 4 pairs.',
        example='''
(cddddr '(1 2 3 4 5))  ; => (5)
(cddddr '(1 2 3 4))  ; => ()
''',
    ),
    api('assoc', 'list',
        sig='(assoc key alist)',
        desc='First pair of alist whose car is equal? to key, or #f.',
        returns='The first pair whose car is equal? to key (strings and lists compare by '
                'content), or #f; elements that are not pairs are skipped.',
        example='''
(assoc "b" '(("a" . 1) ("b" . 2)))  ; => ("b" . 2)
(assoc '(1) '(((1) . x)))  ; => ((1) . x)
(assoc "z" '(("a" . 1)))  ; => #f
''',
    ),
    api('assq', 'list',
        sig='(assq key alist)',
        desc='First pair of alist whose car is eq? to key, or #f.',
        returns='The first pair whose car is eq? to key (identity: use for symbols, small '
                'integers, booleans), or #f.',
        example='''
(assq 'b '((a 1) (b 2)))  ; => (b 2)
(cadr (assq 'a '((a 1) (b 2))))  ; => 1
(assq "b" '(("b" . 2)))  ; => #f
''',
    ),
    api('caddr', 'list',
        sig='(caddr list)',
        desc='The third element.',
        returns='The third element of list; an error "list too short" when it has fewer than 3 '
                'elements.',
        example='''
(caddr '(1 2 3))     ; => 3
(caddr '(1 2))       ; => error: list too short
''',
    ),
    api('for-each', 'list',
        sig='(for-each proc list ...)',
        desc='Call proc on the elements in order, for effect.',
        returns='Void; with several lists it stops at the end of the shortest. An error with no '
                'list or more than 4 lists, when proc is not a procedure, or when proc raises one.',
        example='''
(define total 0)
(for-each (lambda (x) (set! total (+ total x))) '(1 2 3))
total                ; => 6
''',
    ),
    api('list-ref', 'list',
        sig='(list-ref list k)',
        desc='The k-th element (0-based).',
        returns='The element at index k; an error when k is not a non-negative fixnum or is not '
                'less than the length.',
        example='''
(list-ref '(a b c) 1)  ; => b
(list-ref '(a b c) 0)  ; => a
(list-ref '(a b c) 3)  ; => error: index out of range
''',
    ),
    api('member', 'list',
        sig='(member obj list)',
        desc='First tail of list whose car is equal? to obj, or #f.',
        returns='The first tail whose car is equal? to obj (structural comparison), or #f; #f '
                'also when list is not a list.',
        example='''
(member '(1) '((0) (1) (2)))  ; => ((1) (2))
(member "b" '("a" "b"))  ; => ("b")
(member 9 '(1 2))    ; => #f
''',
    ),
    api('memq', 'list',
        sig='(memq obj list)',
        desc='First tail of list whose car is eq? to obj, or #f.',
        returns='The first tail whose car is eq? to obj (identity: use for symbols, small '
                'integers, booleans), or #f.',
        example='''
(memq 'c '(a b c d))  ; => (c d)
(memq 'z '(a b))     ; => #f
(if (memq 'red '(red green)) 'known 'unknown)  ; => known
''',
    ),
    api('list-sort', 'list',
        sig='(list-sort less? list)',
        desc='A new list sorted by (less? a b); stable.',
        returns='A newly allocated list of the elements of list in ascending order according to '
                'less? (a stable merge sort: equal elements keep their order; list is not '
                'changed); `()` for `()`. An error when list is not a proper list, less? is not a '
                'procedure, or less? raises one.',
        example='''
(list-sort < '(3 1 2))  ; => (1 2 3)
(list-sort string<? '("pear" "apple"))  ; => ("apple" "pear")
(list-sort (lambda (x y) (< (cdr x) (cdr y))) '((b . 2) (a . 1) (c . 2)))
; => ((a . 1) (b . 2) (c . 2))
''',
        notes='The argument order is R6RS `(list-sort proc list)` and SRFI 132.',
        status=RESERVED,
    ),
    api('list-index', 'list',
        sig='(list-index pred list)',
        desc='Index of the first element satisfying pred, or #f.',
        returns='The 0-based index of the first element for which pred returns a true value, or '
                '#f when none does; an error when list is not a list or pred raises one.',
        example='''
(list-index even? '(1 3 4 5))  ; => 2
(list-index (lambda (s) (string=? s "b")) '("a" "b"))  ; => 1
(list-index zero? '(1 2))  ; => #f
''',
        status=RESERVED,
    ),
    # ---- vector ------------------------------------------------------------
    api('vector?', 'vector',
        sig='(vector? obj)',
        desc='Test if obj is a vector.',
        returns='#t or #f.',
        example='''
(vector? (vector 1 2))  ; => #t
(vector? '#(1 2))    ; => #t
(vector? '(1 2))     ; => #f
''',
    ),
    api('make-vector', 'vector',
        sig='(make-vector k [fill])',
        desc='Create vector of length k, filled with fill (default 0).',
        returns='A new vector of k elements, all fill (0 when omitted); an error when k is not a '
                'non-negative fixnum.',
        example='''
(make-vector 3 'x)   ; => #(x x x)
(make-vector 2)      ; => #(0 0)
(make-vector -1)     ; => error: negative length
''',
    ),
    api('vector', 'vector',
        sig='(vector obj ...)',
        desc='Create vector containing the given elements.',
        returns='A new vector of the arguments; `#()` with no arguments.',
        example='''
(vector 1 "a" 'b)    ; => #(1 "a" b)
(vector)             ; => #()
''',
    ),
    api('vector-length', 'vector',
        sig='(vector-length vec)',
        desc='Return the number of elements in vec.',
        returns='An exact integer; an error when vec is not a vector.',
        example='''
(vector-length (vector 1 2 3))  ; => 3
(vector-length (make-vector 0))  ; => 0
(vector-length '(1))  ; => error: expected vector
''',
    ),
    api('vector-ref', 'vector',
        sig='(vector-ref vec k)',
        desc='Return element at index k (0-based) in vec.',
        returns='The element at index k; an error when vec is not a vector, k is not a fixnum '
                '(flonums are refused), or k is outside 0..length-1.',
        example='''
(define v (vector 'a 'b 'c))
(vector-ref v 1)     ; => b
(vector-ref v 3)     ; => error: out of bounds
''',
    ),
    api('vector-set!', 'vector',
        sig='(vector-set! vec k obj)',
        desc='Set element at index k in vec to obj.',
        returns='Void; an error when vec is not a vector, k is not a fixnum in 0..length-1, or '
                'vec is a quoted literal in the read-only code image.',
        example='''
(define v (make-vector 3 0))
(vector-set! v 1 'x)
v                    ; => #(0 x 0)
(vector-set! v 3 'y) ; => error: out of bounds
''',
        notes=_ROM,
    ),
    api('vector->list', 'vector',
        sig='(vector->list vec)',
        desc='Convert vector elements to a newly allocated list.',
        returns='A new list of the elements in order; an error when vec is not a vector.',
        example='''
(vector->list (vector 1 2 3))  ; => (1 2 3)
(vector->list (vector))  ; => ()
''',
    ),
    api('list->vector', 'vector',
        sig='(list->vector list)',
        desc='Convert list elements to a newly allocated vector.',
        returns='A new vector of the elements in order. Not checked: a non-list gives `#()` and '
                'the tail of an improper list is dropped.',
        example='''
(list->vector '(1 2 3))  ; => #(1 2 3)
(list->vector '())   ; => #()
''',
    ),
    api('vector-fill!', 'vector',
        sig='(vector-fill! vec fill)',
        desc='Set all elements of vec to fill.',
        returns='Void; an error when vec is not a vector or is a quoted literal in the read-only '
                'code image.',
        example='''
(define v (vector 1 2 3))
(vector-fill! v 0)
v                    ; => #(0 0 0)
''',
        notes=_ROM,
    ),
    # ---- string ------------------------------------------------------------
    api('string?', 'string',
        sig='(string? obj)',
        desc='Test if obj is a string.',
        returns='#t or #f; symbols and characters (integers) are not strings.',
        example='''
(string? "abc")      ; => #t
(string? 'abc)       ; => #f
(string? #\\a)        ; => #f
''',
    ),
    api('string-length', 'string',
        sig='(string-length str)',
        desc='Return the length of str in bytes (UTF-8: a non-ASCII character counts 2-4).',
        returns='An exact integer, the number of bytes; an error when str is not a string.',
        example='''
(string-length "abc")  ; => 3
(string-length "")   ; => 0
(string-length "été")  ; => 5
''',
        notes=_BYTES,
    ),
    api('string-ref', 'string',
        sig='(string-ref str k)',
        desc='Return the byte at byte index k of str as an integer (a character code).',
        returns='An integer 0..255 (for ASCII the character code: `(string-ref "abc" 0)` is 97 = '
                '`#\\a`); an error when str is not a string, k not a fixnum, or k outside '
                '0..length-1.',
        example='''
(string-ref "abc" 1)  ; => 98
(= (string-ref "abc" 0) #\\a)  ; => #t
(string-ref "abc" 3)  ; => error: out of bounds
''',
        notes=_BYTES + ' ' + _CHARS,
    ),
    api('string-append', 'string',
        sig='(string-append str ...)',
        desc='Concatenate strings into a new string.',
        returns='A new string; `""` with no arguments; an error when an argument is not a string '
                '(convert numbers with `number->string`).',
        example='''
(string-append "foo" "bar" "!")  ; => "foobar!"
(string-append "T=" (number->string 21) "C")  ; => "T=21C"
(string-append)      ; => ""
(string-append "a" 1)  ; => error: expected string
''',
    ),
    api('substring', 'string',
        sig='(substring str start end)',
        desc='Return the bytes [start, end) of str as a new string.',
        returns='A new string of end - start bytes; an error when str is not a string, start or '
                'end is not a fixnum (end is required), or not 0 <= start <= end <= length.',
        example='''
(substring "hello" 1 3)  ; => "el"
(substring "hello" 0 0)  ; => ""
(substring "hello" 2 9)  ; => error: invalid slice
''',
        notes=_BYTES + ' Cutting inside a multi-byte character gives invalid UTF-8.',
    ),
    api('symbol->string', 'string',
        sig='(symbol->string sym)',
        desc='Convert symbol to string.',
        returns='A new string of the symbol name; an error when sym is not a symbol.',
        example='''
(symbol->string 'abc)  ; => "abc"
(symbol->string "abc")  ; => error: expected symbol
''',
    ),
    api('string->symbol', 'string',
        sig='(string->symbol str)',
        desc='Convert string to interned symbol.',
        returns='The interned symbol named str (eq? to the same name written literally); an error '
                'when str is not a string.',
        example='''
(string->symbol "hello")  ; => hello
(eq? (string->symbol "hello") 'hello)  ; => #t
''',
    ),
    api('string->number', 'string',
        sig='(string->number str [radix])',
        desc='Parse a number from str (radix 10 by default; #x #b #o #d prefixes), or return #f '
             'if invalid.',
        returns='An exact integer (bignum when large), a flonum for decimal notation with "." or '
                'an exponent (radix 10 only), or #f when str is not a whole number (no '
                'surrounding text, no rationals); an error when str is not a string.',
        example='''
(string->number "42")    ; => 42
(string->number "-3.25") ; => -3.25
(string->number "ff" 16) ; => 255
(string->number "#b101") ; => 5
(string->number "12abc") ; => #f
''',
        notes='Leading whitespace is accepted only by the flonum parser: `(string->number " 12")` '
              'gives 12.0, `"12 "` gives #f.',
    ),
    api('number->string', 'string',
        sig='(number->string num [radix])',
        desc='Convert number to string; integers in radix (default 10), flonums with up to 6 '
             'significant digits.',
        returns='A new string. Integers are exact in any radix 2..36; flonums use C "%g": 6 '
                'significant digits and no ".0" (`2.0` gives "2"). An error when num is not a '
                'number.',
        example='''
(number->string 42)      ; => "42"
(number->string 255 16)  ; => "ff"
(number->string 3.5)     ; => "3.5"
(number->string (/ 1 3)) ; => "0.333333"
''',
        notes='For a fixed number of decimals, scale and round an integer, or format with '
              '`string->fixed` on input.',
    ),
    api('list->string', 'string',
        sig='(list->string chars)',
        desc='Convert a list of byte values (character codes 0..255) to a string.',
        returns='A new string with one byte per element. Not checked: values are truncated to '
                'their low byte, non-integer elements become NUL bytes, and a non-list gives "".',
        example='''
(list->string (list 104 105))  ; => "hi"
(list->string (list #\\o #\\k))  ; => "ok"
(list->string '())   ; => ""
''',
        notes=_BYTES + ' ' + _CHARS,
    ),
    api('string->list', 'string',
        sig='(string->list str)',
        desc='Convert a string to the list of its bytes (character codes 0..255).',
        returns='A new list of integers 0..255, one per byte; an error when str is not a string.',
        example='''
(string->list "hi")  ; => (104 105)
(string->list "")    ; => ()
(list->string (reverse (string->list "abc")))  ; => "cba"
''',
        notes=_BYTES + ' ' + _CHARS,
    ),
    api('string->ints', 'string',
        sig='(string->ints str)',
        desc='Integers of a comma-separated string: (string->ints "12,-3,7") => (12 -3 7). Reads the series fields sent by the app proxy.',
        returns='A list of exact integers, at most 160 of them, bignums past the fixnum range. Spaces around fields are skipped, a field keeps its leading signed digits (up to 15) and fields without digits are dropped; an error when str is not a string.',
        example='''
(string->ints "12,-3,7")  ; => (12 -3 7)
(string->ints "1, 2 ,x,3")  ; => (1 2 3)
(string->ints "")    ; => ()
''',
    ),
    api('string->fixed', 'string',
        sig='(string->fixed str [digits])',
        desc='Leading decimal number of str times 10^digits as an integer: (string->fixed "12.3 %" 1) => 123.',
        returns='An exact integer, rounded half up on the next digit, or #f when str (after '
                'leading spaces) does not start with a number; "." or "," separates decimals and '
                'trailing text is ignored. digits defaults to 0; an error when str is not a string '
                'or digits is outside 0..9. Allocates no flonum.',
        example='''
(string->fixed "12.3 %" 1)  ; => 123
(string->fixed "-0,5 V" 2)  ; => -50
(string->fixed "3.145" 2)   ; => 315
(string->fixed "n/a" 1)     ; => #f
''',
    ),
    api('string=?', 'string',
        sig='(string=? s1 s2 s3 ...)',
        desc='String equality: all arguments have the same bytes.',
        returns='#t or #f; an error with fewer than 2 arguments or when an argument is not a '
                'string.',
        example='''
(string=? "abc" "abc")  ; => #t
(string=? "abc" "ABC")  ; => #f
(string=? "a" "a" "a")  ; => #t
''',
    ),
    api('string<?', 'string',
        sig='(string<? s1 s2 s3 ...)',
        desc='Lexicographic byte order: each argument is less than the next.',
        returns='#t or #f, comparing bytes (case-sensitive: "B" < "a"; a proper prefix is less); '
                'an error with fewer than 2 arguments or a non-string.',
        example='''
(string<? "apple" "banana")  ; => #t
(string<? "ab" "abc")  ; => #t
(string<? "B" "a")   ; => #t
''',
    ),
    api('string>?', 'string',
        sig='(string>? s1 s2 s3 ...)',
        desc='Lexicographic byte order: each argument is greater than the next.',
        returns='#t or #f, comparing bytes as for `string<?`; an error with fewer than 2 '
                'arguments or a non-string.',
        example='''
(string>? "b" "a")   ; => #t
(string>? "c" "b" "a")  ; => #t
(string>? "a" "a")   ; => #f
''',
    ),
    api('string-split', 'string',
        sig='(string-split str sep)',
        desc='The pieces of str between occurrences of sep.',
        returns='A list of new strings: the bytes of str between non-overlapping occurrences of '
                'sep, scanned from the left. sep is a non-empty string or a character (byte '
                'value). Adjacent separators give empty strings; `("")` for "". An error when str '
                'is not a string or sep is empty or of another type.',
        example='''
(string-split "a,b,,c" ",")  ; => ("a" "b" "" "c")
(string-split "k=v" #\\=)     ; => ("k" "v")
(string-split "abc" ";")     ; => ("abc")
''',
        notes=_BYTES,
        status=RESERVED,
    ),
    api('string-join', 'string',
        sig='(string-join strings [sep])',
        desc='Concatenate strings with sep between them.',
        returns='A new string: the elements of the list strings with sep (default " ") between '
                'consecutive ones; "" for `()`. An error when strings is not a list of strings or '
                'sep is not a string.',
        example='''
(string-join '("a" "b" "c") ",")  ; => "a,b,c"
(string-join '("hello" "world"))  ; => "hello world"
(string-join '() ",")  ; => ""
''',
        status=RESERVED,
    ),
    api('string-trim', 'string',
        sig='(string-trim str)',
        desc='str without leading and trailing whitespace.',
        returns='A new string without the leading and trailing ASCII whitespace bytes (space, '
                'tab, LF, CR, VT, FF); other bytes are kept. An error when str is not a string.',
        example='''
(string-trim "  42 \\r\\n")  ; => "42"
(string-trim "a b")  ; => "a b"
(string-trim "   ")  ; => ""
''',
        status=RESERVED,
    ),
    api('string-index', 'string',
        sig='(string-index str sub [start])',
        desc='Byte index of the first sub at or after start, or #f.',
        returns='The byte offset in str of the first occurrence of sub (a string, or a character '
                'byte value) that begins at or after start (default 0), or #f; an empty sub gives '
                'start. An error when start is not in 0..length or an argument has the wrong '
                'type.',
        example='''
(string-index "key=value" "=")  ; => 3
(string-index "a.b.c" #\\. 2)    ; => 3
(string-index "abc" "x")        ; => #f
''',
        notes=_BYTES + ' The result can be passed to `substring`.',
        status=RESERVED,
    ),
    api('string-upcase', 'string',
        sig='(string-upcase str)',
        desc='ASCII letters to upper case.',
        returns='A new string with a-z changed to A-Z; every other byte (including UTF-8 '
                'sequences) unchanged. An error when str is not a string.',
        example='''
(string-upcase "Hello, world")  ; => "HELLO, WORLD"
(string-upcase "abc123")  ; => "ABC123"
''',
        status=RESERVED,
    ),
    api('string-downcase', 'string',
        sig='(string-downcase str)',
        desc='ASCII letters to lower case.',
        returns='A new string with A-Z changed to a-z; every other byte (including UTF-8 '
                'sequences) unchanged. An error when str is not a string.',
        example='''
(string-downcase "Hello, World")  ; => "hello, world"
(string=? (string-downcase "OK") "ok")  ; => #t
''',
        status=RESERVED,
    ),
    api('string-prefix?', 'string',
        sig='(string-prefix? prefix str)',
        desc='Whether str starts with prefix.',
        returns='#t when the first bytes of str equal prefix (always #t for ""), else #f; an '
                'error when an argument is not a string.',
        example='''
(string-prefix? "temp:" "temp:21.5")  ; => #t
(string-prefix? "abc" "ab")  ; => #f
(string-prefix? "" "x")  ; => #t
''',
        status=RESERVED,
    ),
    api('string-suffix?', 'string',
        sig='(string-suffix? suffix str)',
        desc='Whether str ends with suffix.',
        returns='#t when the last bytes of str equal suffix (always #t for ""), else #f; an '
                'error when an argument is not a string.',
        example='''
(string-suffix? ".scm" "main.scm")  ; => #t
(string-suffix? ".scm" "scm")  ; => #f
''',
        status=RESERVED,
    ),
    api('string-pad-left', 'string',
        sig='(string-pad-left str n [char])',
        desc='str padded on the left to n characters.',
        returns='A new string of exactly n bytes: str preceded by copies of char (a byte value, '
                'default #\\space) when shorter, or its last n bytes when longer. An error when n '
                'is not a non-negative fixnum or char is not 0..255.',
        example='''
(string-pad-left "7" 2 #\\0)    ; => "07"
(string-pad-left "42" 5)       ; => "   42"
(string-pad-left "12345" 3)    ; => "345"
''',
        notes=_BYTES + ' Meant for ASCII text such as clock digits.',
        status=RESERVED,
    ),
    # ---- char --------------------------------------------------------------
    api('char->integer', 'char',
        sig='(char->integer char)',
        desc='Return the code of char; characters are already integers, so this is the identity.',
        returns='The integer itself (`#\\A` is 65); an error when char is not a fixnum.',
        example='''
(char->integer #\\A)  ; => 65
(char->integer #\\space)  ; => 32
(char->integer "a")  ; => error: expected fixnum/char
''',
        notes=_CHARS,
    ),
    api('integer->char', 'char',
        sig='(integer->char k)',
        desc='Return the character with code k; characters are integers, so this is the identity.',
        returns='k itself (written as an integer); an error when k is not a fixnum.',
        example='''
(integer->char 65)   ; => 65
(= (integer->char 97) #\\a)  ; => #t
(list->string (list (integer->char 72) (integer->char 105)))  ; => "Hi"
''',
        notes=_CHARS,
    ),
    api('char=?', 'char',
        sig='(char=? c1 c2 c3 ...)',
        desc='Character equality: all codes are equal.',
        returns='#t or #f; an error with fewer than 2 arguments or when an argument is not a '
                'fixnum (character).',
        example='''
(char=? #\\a #\\a)     ; => #t
(char=? #\\a #\\A)     ; => #f
(char=? (string-ref "x" 0) #\\x)  ; => #t
''',
        notes=_CHARS,
    ),
    api('char<?', 'char',
        sig='(char<? c1 c2 c3 ...)',
        desc='Character order: each code is less than the next.',
        returns='#t or #f by code; an error with fewer than 2 arguments or a non-fixnum.',
        example='''
(char<? #\\a #\\b #\\c)  ; => #t
(char<? #\\b #\\a)     ; => #f
(char<? #\\a)         ; => error: expected 2 arguments
''',
    ),
    api('char>?', 'char',
        sig='(char>? c1 c2 c3 ...)',
        desc='Character order: each code is greater than the next.',
        returns='#t or #f by code; an error with fewer than 2 arguments or a non-fixnum.',
        example='''
(char>? #\\b #\\a)     ; => #t
(char>? #\\a #\\a)     ; => #f
''',
    ),
    api('char<=?', 'char',
        sig='(char<=? c1 c2 c3 ...)',
        desc='Character order: each code is less than or equal to the next.',
        returns='#t or #f by code; an error with fewer than 2 arguments or a non-fixnum.',
        example='''
(define c (string-ref "7" 0))
(and (char<=? #\\0 c) (char<=? c #\\9))  ; => #t
(char<=? #\\b #\\a)    ; => #f
''',
    ),
    api('char>=?', 'char',
        sig='(char>=? c1 c2 c3 ...)',
        desc='Character order: each code is greater than or equal to the next.',
        returns='#t or #f by code; an error with fewer than 2 arguments or a non-fixnum.',
        example='''
(char>=? #\\b #\\a #\\a)  ; => #t
(char>=? #\\a #\\b)    ; => #f
''',
    ),
]
