;;; A device for the app library's tests (tests/test_applib.py). Loaded after the
;;; generated stand-ins (every firmware procedure the PC VM lacks: it records its call
;;; in device-calls and answers #f) and before apps/lib/, so the library loads and runs
;;; its logic as on a board, without a screen: the procedures below answer like the
;;; firmware for a 320x480 screen, an app config, a file system and a clock.

;; The app's settings: config-get reads them (the app's config.ini, then the system's)
(define device-config '())
(define (device-set-config! key value)
  (set! device-config (cons (cons key value) (filter (lambda (p) (not (equal? (car p) key))) device-config))))
(define (config-get key) (let ((p (assoc key device-config))) (and p (cdr p))))
(define (config-set! key value) (device-set-config! key value) #t)

;; The app's folder: path -> text
(define device-files '())
(define (fs-read path) (let ((p (assoc path device-files))) (and p (cdr p))))
(define (fs-write path text)
  (set! device-files (cons (cons path text) (filter (lambda (p) (not (equal? (car p) path))) device-files)))
  #t)
(define (fs-exists? path) (and (assoc path device-files) #t))
(define (fs-delete path)
  (set! device-files (filter (lambda (p) (not (equal? (car p) path))) device-files))
  #t)

;; The clock: (year month day hour minute second weekday)
(define device-time (list 2026 10 26 9 30 0 1))
(define (time-local) device-time)
(define (time-synced?) #t)

;; The light sensor (lux): a dark room, the night scheme
(define device-lux 10)
(define (light-lux) device-lux)

;; The screen: 320x480; text 8 px a character
(define (gui-width) 320)
(define (gui-height) 480)
(define (gui-text-width s . font) (* 8 (string-length s)))

;; Calls of one firmware procedure the library made (newest first), and forgetting them
(define (device-calls-of name)
  (map cdr (filter (lambda (c) (eq? (car c) name)) device-calls)))
(define (device-forget!) (set! device-calls '()))
