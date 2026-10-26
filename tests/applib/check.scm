;;; The checks of the app library's tests: (check name got expected) compares with
;;; equal?; a mismatch prints a FAIL line; (check-done) prints the count, which
;;; tests/test_applib.py reads ("checks N failed F").

(define check-count 0)
(define check-failed 0)

(define (check name got expected)
  (set! check-count (+ check-count 1))
  (if (not (equal? got expected))
      (begin
        (set! check-failed (+ check-failed 1))
        (display "FAIL ") (display name) (display ": got ") (write got)
        (display ", expected ") (write expected) (newline))))

(define (check-done)
  (display "checks ") (display check-count) (display " failed ") (display check-failed) (newline))
