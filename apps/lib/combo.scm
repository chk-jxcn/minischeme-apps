;;; combo.scm - a combined app: pages of several apps in one carousel
;;;
;;; tools/build_apps.py builds apps/combo from its meta.ini [combo] members:
;;; applib, this file, then each member app's code followed by
;;; (combo-member! "weather"), and (combo-start!) at the end.
;;;
;;; - A member's (app-define! title pages) is recorded, not started, and its
;;;   hooks (subtitle, tick, data, long press, views, empty pages) are kept
;;;   per member; the global hooks are cleared for the next member.
;;; - config "entries" (this app's settings) lists what to show, one page
;;;   each: <app>.<page>, the page a number (1 first), a page name or
;;;   "front"; or a view the app declared with app-view!: wxpusher.news[0]
;;;   (its newest message).
;;; - Each entry becomes a page of this app, so applib's carousel, page turns,
;;;   prefetch and per-URL cache work as in any app. While a member's code
;;;   runs (its URL, render, hooks) app-page-index is its own page number
;;;   and app-config reads "<app>.<key>" first (this app's config.ini holds
;;;   every member's settings with their app's prefix).
;;; - Short press: next entry. Mid press: the entry's app itself (app-switch:
;;;   for one boot; its mid press comes back here). Long press: the entry
;;;   app's own long press.

(define combo-members '())       ; #(id title pages subtitle tick data long views empty) per member
(define combo-pending #f)        ; (title . pages) of the member being loaded
(define combo-entries (vector))  ; per page of this app: #(member local-page view-proc view-index)
(define combo-prefix "")         ; "<id>." while a member's code runs
(define combo-index #f)          ; this app's page index while a member's code runs

(define combo-applib-define! app-define!)
(define combo-applib-config app-config)
(define combo-applib-start-feed! app-start-feed!)
(define combo-applib-set-url! app-set-url!)
(define combo-default-button app-button)
(define app-long-press #f)       ; a member may define its own: kept per member

;; A member's app-define!: recorded (combo-member! keeps it)
(define (app-define! title pages) (set! combo-pending (cons title pages)))

(define (app-config key default)
  (if (string=? combo-prefix "")
      (combo-applib-config key default)
      (let ((v (config-get (string-append combo-prefix key))))
        (if (and (string? v) (> (string-length v) 0)) v (combo-applib-config key default)))))

(define (combo-id m) (vector-ref m 0))
(define (combo-title m) (vector-ref m 1))
(define (combo-pages m) (vector-ref m 2))

;; Runs thunk as the member's code: its page number, its settings
(define (combo-in m local thunk)
  (let ((saved-index app-page-index) (saved-prefix combo-prefix) (saved-combo combo-index))
    (set! combo-index (if combo-index combo-index app-page-index))
    (set! combo-prefix (string-append (combo-id m) "."))
    (set! app-page-index local)
    (let ((r (thunk)))
      (set! app-page-index saved-index)
      (set! combo-prefix saved-prefix)
      (set! combo-index saved-combo)
      r)))

;; A member restarting its page's fetch: this app's page, not the member's number
(define (app-start-feed!)
  (if combo-index
      (let ((local app-page-index))
        (set! app-page-index combo-index)
        (combo-applib-start-feed!)
        (set! app-page-index local))
      (combo-applib-start-feed!)))

;; A member changing its page i's URL: every entry showing that page
(define (app-set-url! i url)
  (let ((member-id (if (string=? combo-prefix "") #f
                       (substring combo-prefix 0 (- (string-length combo-prefix) 1))))
        (local app-page-index))
    (if member-id
        (begin
          (if combo-index (set! app-page-index combo-index))
          (let loop ((k 0))
            (if (< k (vector-length combo-entries))
                (let ((e (vector-ref combo-entries k)))
                  (if (and (string=? (combo-id (vector-ref e 0)) member-id) (= (vector-ref e 1) i))
                      (combo-applib-set-url! k url))
                  (loop (+ k 1)))))
          (set! app-page-index local))
        (combo-applib-set-url! i url))))

;; After each member's code: keep what it defined, clear the hooks
(define (combo-member! id)
  (let ((title (if combo-pending (car combo-pending) id))
        (pages (if combo-pending (list->vector (cdr combo-pending)) (vector))))
    (set! combo-members
          (append combo-members
                  (list (vector id title pages app-subtitle-proc app-tick-proc app-data-proc
                                app-long-press app-views app-render-empty-pages))))
    (set! combo-pending #f)
    (set! app-subtitle-proc #f)
    (set! app-header-proc #f)
    (set! app-tick-proc #f)
    (set! app-data-proc #f)
    (set! app-long-press #f)
    (set! app-views '())
    (set! app-render-empty-pages '())
    (set! app-button combo-default-button)))

(define (combo-find-member id)
  (let loop ((ms combo-members))
    (cond ((null? ms) #f)
          ((string=? (combo-id (car ms)) id) (car ms))
          (else (loop (cdr ms))))))

;; The first position of character ch in s at or after start, else #f
(define (combo-char-pos s ch start)
  (let loop ((i start))
    (cond ((>= i (string-length s)) #f)
          ((char=? (string-ref s i) ch) i)
          (else (loop (+ i 1))))))

(define (combo-trim s)
  (let loop ((a 0) (b (string-length s)))
    (cond ((and (< a b) (char=? (string-ref s a) #\space)) (loop (+ a 1) b))
          ((and (< a b) (char=? (string-ref s (- b 1)) #\space)) (loop a (- b 1)))
          (else (substring s a b)))))

;; "weather.2" / "calendar.今日" / "stocks.front" / "wxpusher.news[0]" -> an
;; entry, #f when the app or the page is unknown
(define (combo-parse spec)
  (let* ((s (combo-trim spec)) (dot (combo-char-pos s #\. 0))
         (m (and dot (combo-find-member (substring s 0 dot))))
         (rest (if dot (substring s (+ dot 1) (string-length s)) "")))
    (if (not m)
        #f
        (let* ((open (combo-char-pos rest #\[ 0))
               (close (and open (combo-char-pos rest #\] open)))
               (pages (combo-pages m)) (n (vector-length pages)))
          (cond
            ((and open close)          ; a view
             (let* ((name (substring rest 0 open))
                    (idx (or (string->number (substring rest (+ open 1) close)) 0))
                    (v (let loop ((vs (vector-ref m 7)))
                         (cond ((null? vs) #f) ((string=? (car (car vs)) name) (car vs)) (else (loop (cdr vs)))))))
               (and v (< (cadr v) n) (vector m (cadr v) (caddr v) idx))))
            ((string=? rest "front") (and (> n 0) (vector m 0 #f 0)))
            ((string->number rest)
             (let ((k (- (string->number rest) 1))) (and (>= k 0) (< k n) (vector m k #f 0))))
            (else
             (let loop ((k 0))
               (cond ((>= k n) #f)
                     ((string=? (vector-ref (vector-ref pages k) 0) rest) (vector m k #f 0))
                     (else (loop (+ k 1)))))))))))

;; The entry's name: "<page>" or "<view>[i]" (shown after the app's title)
(define (combo-entry-name e)
  (let ((page (vector-ref (combo-pages (vector-ref e 0)) (vector-ref e 1))))
    (if (vector-ref e 2)
        (string-append (vector-ref page 0) " " (number->string (+ (vector-ref e 3) 1)))
        (vector-ref page 0))))

;; The entry as a page of this app: the member's URL, interval and render
;; (or its view), each run as the member's code
(define (combo-entry-page e)
  (let* ((m (vector-ref e 0)) (local (vector-ref e 1)) (page (vector-ref (combo-pages m) local))
         (view (vector-ref e 2)) (vi (vector-ref e 3)))
    (vector (combo-entry-name e)
            (lambda () (combo-in m local (lambda () ((vector-ref page 1)))))
            (vector-ref page 2)
            (lambda (items)
              (combo-in m local (lambda () (if view (view items vi) ((vector-ref page 3) items))))))))

(define (combo-cur) (vector-ref combo-entries app-page-index))

;; Header: the entry's app and the page (or the app's own subtitle on its first page)
(define (app-header-title items) (combo-title (vector-ref (combo-cur) 0)))

(define (app-header-sub items)
  (let* ((e (combo-cur)) (m (vector-ref e 0)) (sub (vector-ref m 3)))
    (if (and sub items (= (vector-ref e 1) 0) (not (vector-ref e 2)))
        (or (combo-in m 0 (lambda () (sub items))) (combo-entry-name e))
        (combo-entry-name e))))

;; The document that arrived belongs to the entries with its URL: their app's data hook
(define (combo-data items)
  (let ((url (json-feed-url)))
    (let loop ((k 0) (seen '()))
      (if (< k (vector-length combo-entries))
          (let* ((e (vector-ref combo-entries k)) (m (vector-ref e 0)) (proc (vector-ref m 5)))
            (if (and proc (equal? (vector-ref app-urls k) url) (not (memq m seen)))
                (begin (combo-in m (vector-ref e 1) (lambda () (proc items)))
                       (loop (+ k 1) (cons m seen)))
                (loop (+ k 1) seen)))))))

;; Every second: the shown entry's app
(define (combo-tick tick)
  (if (> (vector-length combo-entries) 0)
      (let* ((e (combo-cur)) (m (vector-ref e 0)) (proc (vector-ref m 4)))
        (if proc (combo-in m (vector-ref e 1) (lambda () (proc tick)))))))

(define (combo-long-press)
  (let* ((e (combo-cur)) (m (vector-ref e 0)) (proc (vector-ref m 6)))
    (if proc (combo-in m (vector-ref e 1) proc))))

;; Mid press: the entry's app on its own (installed as apps/<id>/app.msbc)
(define (app-mid-press)
  (let ((r (if (defined? 'app-switch)
               (app-switch (string-append "apps/" (combo-id (vector-ref (combo-cur) 0)) "/app.msbc"))
               "app-switch: this firmware cannot open another app")))
    (if (string? r)
        (begin (set! app-error r) (gui-invalidate 0 (- (gui-height) FTR-H) (scr-w) FTR-H)))))

;; The pages of the entries config lists (unknown ones left out)
(define (combo-start! title)
  (let* ((specs (str-split (app-config "entries" "") #\,))
         (entries (filter (lambda (e) e) (map combo-parse (filter (lambda (s) (> (string-length (combo-trim s)) 0)) specs)))))
    (set! combo-entries (list->vector entries))
    (set! app-index-always #t)
    (set! app-data-proc combo-data)
    (set! app-tick-proc combo-tick)
    (set! app-long-press combo-long-press)   ; after the members: wxpusher defines its own
    ;; entries drawn before their data: their app's local or empty-drawn pages
    (set! app-render-empty-pages
          (let loop ((k 0) (acc '()))
            (if (< k (vector-length combo-entries))
                (let ((e (vector-ref combo-entries k)))
                  (loop (+ k 1) (if (memv (vector-ref e 1) (vector-ref (vector-ref e 0) 8)) (cons k acc) acc)))
                acc)))
    (if (null? entries)
        (combo-applib-define! title
                              (list (app-local-page "合集"
                                                    (lambda (items)
                                                      (txt-wrap 16 (+ HDR-H 20) (- (scr-w) 32) 200
                                                                "没有可显示的页面：在本应用的设置里填写 entries，例如 weather.1, calendar.1, wxpusher.news[0]"
                                                                theme-warning)))))
        (combo-applib-define! title (map combo-entry-page entries)))))
