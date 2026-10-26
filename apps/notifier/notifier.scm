;;; =========================================================================
;;; Notifier (消息提示器), 320x480 portrait, on the app framework (applib.scm).
;;; Messages come two ways and are kept on the board (notifier.txt in its folder,
;;; the newest "keep" of them, 30 by default):
;;;   - pushed to the app proxy (GET/POST /notify?text=..&title=..&level=..; a
;;;     public server: mac=<device id>&password=<its app service password>),
;;;     which keeps all of them (its user portal lists and deletes them) and
;;;     which this app polls at /app/notifier?n=<keep> every 5 s;
;;;   - straight to the board: its web page's app tab, or
;;;     POST /api/app/call?fn=notify (title, text, level, from).
;;; A new message turns to page 1 and blinks the LED (urgent: until read);
;;; a short press marks everything read, then turns pages. Each new message is
;;; also an alert (applib section 9) over any page, in a combined app too:
;;; urgent priority 8 until a press, warn 6 and info 4 also closing by
;;; themselves (60 s, 30 s); a short press on it reads that message.
;;;   1 the newest message   2 all messages
;;; Rich messages (section 3a): the app server keeps text written with markup encoded for this
;;; screen (headings, colors, lists, dividers, pictures); the newest one's card and the alerts
;;; draw it, turning through a long one every NOTE-SCROLL-S seconds; the list shows it plain.
;;; File: first line "P|<last proxy id>", then "id|pid|level|read|time|from|title|text".
;;; An app may touch only its own folder: relative paths are in it.
;;; =========================================================================

(define NOTE-PATH "notifier.txt")        ; in the app's own folder
(define (note-keep) (clamp (or (string->number (app-config "keep" "30")) 30) 5 200))   ; messages kept here
(define NOTE-INTERVAL 5000)

(define NOTE-TEXT-MAX 1600)             ; bytes of a message's text kept (a rich one is encoded)
(define note-list '())                  ; #(id pid level read time from title text plain), newest first
(define note-last-pid 0)                ; the newest proxy message taken
(define note-alert 0)                   ; seconds of LED blinking left; -1: until read (urgent)
(define note-synced #f)                 ; a proxy document arrived since the start

;; 1. Storage ---------------------------------------------------------------------------------

(define (note-id m) (vector-ref m 0))
(define (note-pid m) (vector-ref m 1))
(define (note-level m) (vector-ref m 2))
(define (note-read? m) (vector-ref m 3))
(define (note-time m) (vector-ref m 4))
(define (note-from m) (vector-ref m 5))
(define (note-title m) (vector-ref m 6))
(define (note-text m) (vector-ref m 7))
(define (note-plain-head m) (vector-ref m 8))   ; the start of the text without markup: list rows

;; The first n bytes of s, never cutting a UTF-8 character
(define (note-cut s n)
  (if (<= (string-length s) n)
      s
      (let loop ((k n))
        (if (and (> k 0) (let ((b (char->integer (string-ref s k)))) (and (>= b 128) (< b 192))))
            (loop (- k 1))
            (substring s 0 k)))))

(define (note-make id pid level read time from title text)
  (vector id pid level read time from title text (note-cut (note-plain text) 160)))

;; The positions of the first n "|" in line, or #f
(define (note-bars line n)
  (let loop ((i 0) (acc '()))
    (cond ((= (length acc) n) (reverse acc))
          ((>= i (string-length line)) #f)
          ((char=? (string-ref line i) #\|) (loop (+ i 1) (cons i acc)))
          (else (loop (+ i 1) acc)))))

(define (note-parse line)
  (let ((b (note-bars line 7)))
    (if (not b)
        #f
        (let ((field (lambda (k)
                       (substring line (if (= k 0) 0 (+ 1 (list-ref b (- k 1))))
                                  (if (= k 7) (string-length line) (list-ref b k))))))
          (note-make (or (string->number (field 0)) 0) (or (string->number (field 1)) 0) (field 2)
                     (string=? (field 3) "1") (field 4) (field 5) (field 6) (field 7))))))

(define (note-load!)
  (let ((text (and (fs-exists? NOTE-PATH) (fs-read NOTE-PATH))))
    (set! note-list '())
    (if (string? text)
        (for-each (lambda (line)
                    (if (str-starts? line "P|")
                        (set! note-last-pid (or (string->number (substring line 2 (string-length line))) 0))
                        (let ((m (note-parse line))) (if m (set! note-list (append note-list (list m)))))))
                  (str-split text #\newline)))))

;; "|" would end a field early: only the text (the last field) may hold it
(define (note-safe s)
  (list->string (map (lambda (c) (if (or (char=? c #\|) (char=? c #\newline) (char=? c #\return)) #\space c))
                     (string->list (or s "")))))

(define (note-line m)
  (string-append (number->string (note-id m)) "|" (number->string (note-pid m)) "|" (note-level m) "|"
                 (if (note-read? m) "1" "0") "|" (note-time m) "|" (note-from m) "|" (note-title m) "|"
                 (note-text m)))

(define (note-save!)
  (note-pics-clean!)
  (fs-write NOTE-PATH (web-join (cons (string-append "P|" (number->string note-last-pid)) (map note-line note-list))
                                (list->string (list #\newline))))
  (app-invalidate-all))

(define (note-next-id)
  (+ 1 (let loop ((l note-list) (hi 0)) (if (null? l) hi (loop (cdr l) (max hi (note-id (car l))))))))

(define (note-unread) (length (filter (lambda (m) (not (note-read? m))) note-list)))

(define (note-level-ok level) (if (member level '("info" "warn" "urgent")) level "info"))

;; A new message, newest first; alert unless quiet
(define (note-add! pid level time from title text quiet)
  (let ((m (note-make (note-next-id) pid (note-level-ok level) quiet (note-safe time) (note-safe (note-cut from 30))
                      (note-safe (note-cut title 60)) (note-safe (note-cut text NOTE-TEXT-MAX)))))
    (set! note-list (cons m note-list))
    (if (> (length note-list) (note-keep)) (set! note-list (take note-list (note-keep))))
    (if (not quiet)
        (begin
          (set! note-alert (if (string=? (note-level m) "urgent") -1 20))
          (set! note-scroll 0)
          (set! note-pic-failed '())
          (if (not (= app-page-index 0)) (app-goto! 0))
          (note-raise-alert! m)))
    m))

(define (note-alert-key m) (string-append "n" (number->string (note-id m))))

;; One message read (its alert's short press); the LED stops with the last one
(define (note-read-one! m)
  (vector-set! m 3 #t)
  (if (= (note-unread) 0) (begin (set! note-alert 0) (ws2812-clear)))
  (note-save!))

(define (note-render-alert m)
  (let ((y (+ (body-top) 6)))
    (note-badge 10 y m)
    (txt-right 310 (+ y 3) (note-meta-text m) theme-text-muted)
    (txt-wrap 10 (+ y 32) 300 44 (if (str-empty? (note-title m)) "（无标题）" (note-title m)) theme-accent)
    (note-draw-text 10 (+ y 82) 300 (- (body-bottom) y 106) m)))

(define (note-raise-alert! m)
  (let ((l (note-level m)))
    (app-alert! (note-alert-key m) (car (note-level-badge m)) (lambda () (note-render-alert m))
                (list (cons 'ack (lambda () (note-read-one! m)))
                      (cons 'priority (cond ((string=? l "urgent") 8) ((string=? l "warn") 6) (else 4)))
                      (cons 'exit (if (string=? l "urgent") 'button 'both))
                      (cons 'seconds (if (string=? l "warn") 60 30))))))

(define (note-mark-read!)
  (for-each (lambda (m) (vector-set! m 3 #t) (app-alert-done! (note-alert-key m))) note-list)
  (set! note-alert 0)
  (ws2812-clear)
  (note-save!))

(define (note-now) (if (string=? app-time "--:--") "" app-time))

;; 2. The proxy's messages -----------------------------------------------------------------------

;; Each new document: messages with ids past the last taken one, oldest first.
;; The proxy's ids start again at 1 when it restarts (its counter fell back).
(define (note-data! items)
        (let* ((meta (items-find items "meta")) (seq (if meta (or (it-int meta 1) 0) 0))
               (first-sync (and (not note-synced) (= note-last-pid 0) (null? note-list))))
          (set! note-synced #t)
          (if (< seq note-last-pid) (set! note-last-pid 0))
          (let ((fresh (filter (lambda (it) (> (or (it-int it 1) 0) note-last-pid)) (reverse (items-all items "msg")))))
            (if (pair? fresh)
                (begin
                  (for-each (lambda (it)
                              (note-add! (it-int it 1) (it-d it) (str-part (it-e it) #\space 0)
                                         (let ((e (it-e it))) (if (> (string-length e) 6) (substring e 6 (string-length e)) ""))
                                         (it-b it) (it-c it) first-sync))   ; on a first start: no alarm for old ones
                            fresh)
                  (set! note-last-pid (list-max (map (lambda (it) (it-int it 1)) fresh)))
                  (note-save!))))))

(set! app-data-proc note-data!)

;; 3a. Rich messages --------------------------------------------------------------------------------
;; The app server (minischeme-proxy proxy/notes_rich.py) keeps a message written with markup
;; (# 标题, **强调**, {red}..{/}, - 列表, ---, ![](picture)) encoded for this screen: it starts
;; with "^!" and "^/" ends a line. A line may start with "^#" (a heading), "^2" / "^3" (text
;; twice / three times as large: gui-text-scaled), "^-" (a list item),
;; "^=" (a divider) or "^i<id>:<w>x<h>;" (a picture the server keeps, original size w x h:
;; /app/notifier/pic?id=&w=&h= gives it at any size). Inside a line "^a" (accent), "^r" "^g" "^y"
;; "^b" "^m" (red, green, yellow, blue, gray) and "^n" (normal) switch the color; "^^" is a "^".
;; A message is laid out once per box (note-lay: a short cache) into drawing operations:
;;   #(t x y text code scale)  #(l x y w)  #(i x y w h id)        (y from the top of the text)
;; A text taller than its box turns screenful by screenful (note-scroll, every NOTE-SCROLL-S s).
;; Pictures download one at a time into img/ (11.7), only for the newest NOTE-PIC-KEEP messages
;; (what the card and the alerts show); the others' files are deleted.

(define NOTE-MARK "^!")
(define NOTE-PIC-DIR "img")
(define NOTE-PIC-MAX 4)       ; pictures drawn per message (the others: "[图片]")
(define NOTE-PIC-H 160)       ; a picture's height on screen at most (the server crops to the box)
(define NOTE-PIC-KEEP 5)      ; messages whose pictures are kept
(define NOTE-SCROLL-S 6)      ; seconds per screenful of a long rich message
(define NOTE-BLUE 23743)      ; #x5CBF (#5a96fa): no theme color is blue

(define note-scroll 0)        ; the screenful shown (modulo the message's count)
(define note-lay-cache '())   ; (((id w h) layout pages) ...), the newest first
(define note-pics-ready '())  ; picture paths complete on disk
(define note-pic-queue '())   ; (id w h) waiting to download
(define note-pic-current #f)  ; the (id w h) downloading
(define note-pic-failed '())  ; (id w h) that failed (tried again with the next new message)
(define note-drawn-ms 0)      ; when render last drew a rich text of several screenfuls

(define (note-rich? s) (str-starts? s NOTE-MARK))

(define (note-cat l) (fold-left string-append "" l))

;; The index of ch in s from i, else the last index
(define (note-find s ch i)
  (let ((n (string-length s)))
    (let loop ((k i)) (cond ((>= k n) (- n 1)) ((char=? (string-ref s k) ch) k) (else (loop (+ k 1)))))))

;; The text without markup ("^/" a space, items "• ", pictures "[图片]")
(define (note-plain s)
  (if (not (note-rich? s))
      s
      (let ((n (string-length s)))
        (let loop ((i 2) (start 2) (acc '()))
          (cond ((>= i n) (note-cat (reverse (cons (substring s start n) acc))))
                ((and (char=? (string-ref s i) #\^) (< (+ i 1) n))
                 (let ((c (string-ref s (+ i 1))) (acc (cons (substring s start i) acc)))
                   (cond ((char=? c #\^) (loop (+ i 2) (+ i 2) (cons "^" acc)))
                         ((char=? c #\/) (loop (+ i 2) (+ i 2) (cons " " acc)))
                         ((char=? c #\-) (loop (+ i 2) (+ i 2) (cons "• " acc)))
                         ((char=? c #\=) (loop (+ i 2) (+ i 2) (cons "― " acc)))
                         ((char=? c #\i) (let ((e (+ 1 (note-find s #\; i)))) (loop e e (cons "[图片]" acc))))
                         (else (loop (+ i 2) (+ i 2) acc)))))
                (else (loop (+ i 1) start acc)))))))

;; The lines of a rich text (their codes kept)
(define (note-rich-lines s)
  (let ((n (string-length s)))
    (let loop ((i 2) (start 2) (acc '()))
      (cond ((>= i n) (reverse (cons (substring s start n) acc)))
            ((and (char=? (string-ref s i) #\^) (< (+ i 1) n))
             (if (char=? (string-ref s (+ i 1)) #\/)
                 (loop (+ i 2) (+ i 2) (cons (substring s start i) acc))
                 (loop (+ i 2) start acc)))
            (else (loop (+ i 1) start acc))))))

;; A line from byte k as ((code . text) ...): code the color character in effect, #\n at first
(define (note-segs s k)
  (let ((n (string-length s)))
    (let loop ((i k) (start k) (code #\n) (parts '()) (acc '()))
      (cond ((>= i n)
             (reverse (cons (cons code (note-cat (reverse (cons (substring s start n) parts)))) acc)))
            ((and (char=? (string-ref s i) #\^) (< (+ i 1) n))
             (let ((c (string-ref s (+ i 1))) (piece (substring s start i)))
               (if (char=? c #\^)
                   (loop (+ i 2) (+ i 2) code (cons "^" (cons piece parts)) acc)
                   (loop (+ i 2) (+ i 2) c '() (cons (cons code (note-cat (reverse (cons piece parts)))) acc)))))
            (else (loop (+ i 1) start code parts acc))))))

(define (note-color code)
  (cond ((char=? code #\a) theme-accent) ((char=? code #\r) theme-danger) ((char=? code #\g) theme-success)
        ((char=? code #\y) theme-warning) ((char=? code #\b) NOTE-BLUE) ((char=? code #\m) theme-text-muted)
        (else theme-text-main)))

;; Where the token at byte i ends: a space, a run of other ASCII (a word), or one UTF-8 character
(define (note-token-end s i)
  (let ((n (string-length s)) (b (char->integer (string-ref s i))))
    (cond ((= b 32) (+ i 1))
          ((< b 128)
           (let loop ((j (+ i 1)))
             (if (and (< j n) (let ((c (char->integer (string-ref s j)))) (and (< c 128) (not (= c 32)))))
                 (loop (+ j 1))
                 j)))
          (else (min n (+ i (cond ((< b 224) 2) ((< b 240) 3) (else 4))))))))

;; A rich text laid out w wide: #(ops height)
(define (note-layout s w)
  (let ((ops '()) (y 0) (x 0) (indent 0) (para-y 0) (run '()) (run-x 0) (run-code #\n) (pics 0) (sc 1))
    (define (op! v) (set! ops (cons v ops)))
    (define (flush!)
      (if (pair? run) (op! (vector 't run-x y (note-cat (reverse run)) run-code sc)))
      (set! run '()))
    (define (newline!)
      (flush!)
      (set! y (+ y (* sc LINE-H)))
      (set! x indent))
    (define (put! tok tw code)
      (if (or (null? run) (not (char=? code run-code)))
          (begin (flush!) (set! run-code code) (set! run-x x)))
      (set! run (cons tok run))
      (set! x (+ x tw)))
    (define (word! tok code)
      (let ((tw (* sc (txt-w tok))))
        (cond ((and (string=? tok " ") (= x indent) (> y para-y)) #f)   ; a wrapped line starts with no space
              ((<= (+ x tw) w) (put! tok tw code))
              ((string=? tok " ") (newline!))
              ((<= (+ indent tw) w) (newline!) (put! tok tw code))
              ((> (string-length tok) 1)                                ; a word longer than a line: by letters
               (let loop ((i 0))
                 (if (< i (string-length tok)) (begin (word! (substring tok i (+ i 1)) code) (loop (+ i 1))))))
              (else (if (> x indent) (newline!)) (put! tok tw code)))))
    (define (text! segs base)
      (set! x indent)
      (set! para-y y)
      (for-each (lambda (seg)
                  (let ((code (if (char=? (car seg) #\n) base (car seg))) (str (cdr seg)))
                    (let loop ((i 0))
                      (if (< i (string-length str))
                          (let ((j (note-token-end str i)))
                            (word! (substring str i j) code)
                            (loop j))))))
                segs)
      (flush!)
      (set! y (+ y (* sc LINE-H))))
    (define (pic! line)
      (let* ((semi (note-find line #\; 2))
             (d (if (> semi 19) (str-split (substring line 19 semi) #\x) '()))
             (pw (if (pair? d) (or (string->number (car d)) 0) 0))
             (ph (if (and (pair? d) (pair? (cdr d))) (or (string->number (cadr d)) 0) 0)))
        (cond ((or (<= pw 0) (<= ph 0)) #f)
              ((>= pics NOTE-PIC-MAX) (op! (vector 't 0 y "[图片]" #\m 1)) (set! y (+ y LINE-H)))
              (else
               (let* ((dw (min w pw)) (dh (clamp (quotient (* dw ph) pw) 16 NOTE-PIC-H)))
                 (op! (vector 'i 0 y dw dh (substring line 2 18)))
                 (set! pics (+ pics 1))
                 (set! y (+ y dh 4)))))))
    (for-each (lambda (line)
                (cond ((str-starts? line "^=") (op! (vector 'l 0 (+ y 5) w)) (set! y (+ y 11)))
                      ((str-starts? line "^i") (pic! line))
                      ((str-starts? line "^#")
                       (set! indent 0)
                       (text! (note-segs line 2) #\a)
                       (op! (vector 'l 0 (- y 2) w))
                       (set! y (+ y 4)))
                      ((or (str-starts? line "^2") (str-starts? line "^3"))
                       (set! indent 0)
                       (set! sc (if (str-starts? line "^2") 2 3))
                       (text! (note-segs line 2) #\n)
                       (set! sc 1))
                      ((str-starts? line "^-")
                       (op! (vector 't 0 y "•" #\n 1))
                       (set! indent 14)
                       (text! (note-segs line 2) #\n)
                       (set! indent 0))
                      ((= (string-length line) 0) (set! y (+ y 10)))   ; an empty line: a paragraph gap
                      (else (set! indent 0) (text! (note-segs line 0) #\n))))
              (note-rich-lines s))
    (vector (reverse ops) y)))

(define (note-op-bottom op)
  (case (vector-ref op 0)
    ((t) (+ (vector-ref op 2) (* 16 (vector-ref op 5))))
    ((l) (+ (vector-ref op 2) 1))
    (else (+ (vector-ref op 2) (vector-ref op 4)))))

;; Where each screenful of a layout starts in a box h tall: what does not fit whole starts the next
(define (note-pages lay h)
  (let ((ops (vector-ref lay 0)) (total (vector-ref lay 1)))
    (let loop ((p 0) (acc '(0)))
      (let ((next (fold-left (lambda (m op) (if (> (note-op-bottom op) (+ p h)) (min m (vector-ref op 2)) m))
                             total ops)))
        (if (or (<= next p) (>= next total))   ; all there, or one picture taller than the box
            (reverse acc)
            (loop next (cons next acc)))))))

;; (layout pages) of message m in a w x h box
(define (note-lay m w h)
  (let* ((key (list (note-id m) w h)) (hit (assoc key note-lay-cache)))
    (if hit
        (cdr hit)
        (let* ((lay (note-layout (note-text m) w)) (v (list lay (note-pages lay h))))
          (set! note-lay-cache (cons (cons key v) (if (> (length note-lay-cache) 2) (take note-lay-cache 2) note-lay-cache)))
          v))))

(define (note-pic-path job)
  (string-append NOTE-PIC-DIR "/" (car job) "_" (int->str (cadr job)) "x" (int->str (caddr job)) ".jpg"))

;; An id starting with "z": a picture the app's web page writes into img/ itself, never downloaded
(define (note-pic-want! job)
  (if (not (or (str-starts? (car job) "z") (equal? job note-pic-current) (member job note-pic-queue)
               (member job note-pic-failed)))
      (set! note-pic-queue (append note-pic-queue (list job)))))

(define (note-pic-done ok path)
  (if note-pic-current
      (begin
        (if ok
            (set! note-pics-ready (cons (note-pic-path note-pic-current) note-pics-ready))
            (set! note-pic-failed (cons note-pic-current note-pic-failed)))
        (set! note-pic-current #f)
        (app-invalidate-all)
        (note-pic-step!))))

;; One download at a time (on-done starts the next; the tick tries too)
(define (note-pic-step!)
  (if (and (not note-pic-current) (pair? note-pic-queue) (not (str-empty? (app-proxy))))
      (let ((job (car note-pic-queue)))
        (if (fs-download (app-url (string-append "/app/notifier/pic?id=" (car job) "&w=" (int->str (cadr job))
                                                 "&h=" (int->str (caddr job))))
                         (note-pic-path job) (app-callback note-pic-done))
            (begin (set! note-pic-queue (cdr note-pic-queue)) (set! note-pic-current job))))))

;; The picture files of the newest NOTE-PIC-KEEP messages stay; the others go (what an interrupted
;; download left too)
(define (note-pics-clean!)
  (let* ((texts (map note-text (if (> (length note-list) NOTE-PIC-KEEP) (take note-list NOTE-PIC-KEEP) note-list)))
         (wanted? (lambda (name)
                    (and (> (string-length name) 20) (str-starts? (substring name 16 17) "_")
                         (let ((tag (string-append "^i" (substring name 0 16) ":")))
                           (let loop ((l texts)) (and (pair? l) (or (str-contains? (car l) tag) (loop (cdr l))))))))))
    (for-each (lambda (entry)
                (let ((name (car entry)) (path (string-append NOTE-PIC-DIR "/" (car entry))))
                  (if (or (not (wanted? name)) (not (str-contains? name ".jpg")))
                      (begin (fs-remove path) (set! note-pics-ready (filter (lambda (p) (not (string=? p path))) note-pics-ready)))
                      (if (and (not (member path note-pics-ready)) (not (equal? path (and note-pic-current (note-pic-path note-pic-current)))))
                          (set! note-pics-ready (cons path note-pics-ready))))))
              (fs-list NOTE-PIC-DIR))))

(define (note-draw-pic x y op)
  (let* ((job (list (vector-ref op 5) (vector-ref op 3) (vector-ref op 4))) (path (note-pic-path job)))
    (if (member path note-pics-ready)
        (gui-image x y path)
        (begin
          (gui-round-rect x y (cadr job) (caddr job) 4 theme-card-hdr #t)
          (if (>= (caddr job) 24)
              (txt (+ x 8) (+ y (quotient (- (caddr job) 16) 2)) (if (member job note-pic-failed) "图片无法载入" "图片载入中…")
                   theme-text-muted))
          (note-pic-want! job)))))   ; only a note in memory: the tick downloads it

;; The next screenful, while one shows (render drew one lately)
(define (note-scroll-step! tick)
  (if (and (= (remainder tick NOTE-SCROLL-S) 0) (< (- (time-ms) note-drawn-ms) (* 1000 (+ NOTE-SCROLL-S 2))))
      (begin (set! note-scroll (+ note-scroll 1)) (app-invalidate-all))))

;; Message m's text in the box x y w h: a rich one laid out (a long one a screenful at a time,
;; "2/3" on the box's bottom edge), a plain one wrapped
(define (note-draw-text x y w h m)
  (if (not (note-rich? (note-text m)))
      (txt-wrap x y w h (note-text m) theme-text-main)
      (let* ((v (note-lay m w h)) (pages (cadr v)) (np (length pages))
             (top (list-ref pages (remainder note-scroll np))) (bottom (+ top h)))
        (for-each (lambda (op)
                    (let ((oy (vector-ref op 2)))
                      (if (and (>= oy top) (<= (note-op-bottom op) bottom))
                          (let ((dx (+ x (vector-ref op 1))) (dy (+ y (- oy top))))
                            (case (vector-ref op 0)
                              ((t) (if (= (vector-ref op 5) 1)
                                       (txt dx dy (vector-ref op 3) (note-color (vector-ref op 4)))
                                       (gui-text-scaled dx dy (vector-ref op 3) (note-color (vector-ref op 4))
                                                        (vector-ref op 5) F-TEXT)))
                              ((l) (gui-line dx dy (+ dx (vector-ref op 3)) dy theme-divider))
                              (else (note-draw-pic dx dy op)))))))
                  (vector-ref (car v) 0))
        (if (> np 1) (set! note-drawn-ms (time-ms)))
        (if (> np 1)
            (let* ((s (string-append (int->str (+ 1 (remainder note-scroll np))) "/" (int->str np)))
                   (sw (+ (txt-w s) 8)))
              (gui-rect (- (+ x w) sw) (+ y h 2) sw 16 theme-bg #t)
              (txt-right (- (+ x w) 4) (+ y h 2) s theme-text-muted))))))

;; 3. The screen ------------------------------------------------------------------------------

(define (note-level-badge m)
  (let ((l (note-level m)))
    (cond ((string=? l "urgent") (list "紧急" theme-danger))
          ((string=? l "warn") (list "提醒" theme-warning))
          (else (list "通知" theme-accent)))))

(define (note-badge x y m)
  (let* ((b (note-level-badge m)) (w (+ (txt-w (car b)) 12)))
    (gui-round-rect x y w 22 5 (cadr b) (not (note-read? m)))
    (txt (+ x 6) (+ y 3) (car b) (if (note-read? m) (cadr b) theme-bg))
    w))

(define (note-meta-text m)
  (string-append (note-time m) (if (str-empty? (note-from m)) "" (string-append "  " (note-from m)))))

(define (note-hint)
  (if (wifi-connected?)
      (string-append "发送：浏览器打开 http://" (wifi-ip) "/ ，或向代理的 /notify 推送")
      "连接 WiFi 后，从网页或代理的 /notify 推送消息"))

(define NOTE-OLDER 3)        ; older messages under the newest one's card

(define (note-render-latest items)
  (if (null? note-list)
      (begin
        (txt 14 70 "暂无消息" theme-text-muted)
        (txt-wrap 14 100 (- (scr-w) 28) 80 (note-hint) theme-text-sub))
      (let* ((m (car note-list)) (y (+ (body-top) 6)) (w (note-badge 10 y m)))
        (txt-right 310 (+ y 3) (note-meta-text m) theme-text-muted)
        (txt-fit 10 (+ y 32) 300 (if (str-empty? (note-title m)) "（无标题）" (note-title m))
                 (if (note-read? m) theme-text-main theme-accent))
        (let* ((older (min NOTE-OLDER (- (length note-list) 1)))   ; the card takes what older rows leave
               (card-y (+ y 60))
               (card-h (- (body-bottom) card-y (if (> older 0) (+ (* older 26) 10) 2))))
          (gui-round-rect 10 card-y 300 card-h 8 theme-card-border #f)
          (note-draw-text 20 (+ card-y 10) 280 (- card-h 20) m)
          (let loop ((l (cdr note-list)) (yy (+ card-y card-h 12)) (i 0))
            (if (and (pair? l) (< i NOTE-OLDER))
                (let ((o (car l)))
                  (txt 10 yy (note-time o) theme-text-muted)
                  (txt-fit 64 yy 246 (string-append (if (str-empty? (note-title o)) "" (string-append (note-title o) "：")) (note-plain-head o))
                           (if (note-read? o) theme-text-sub theme-text-main))
                  (loop (cdr l) (+ yy 26) (+ i 1)))))))))

(define (note-render-all items)
  (if (null? note-list)
      (txt 14 70 "暂无消息" theme-text-muted)
      (let loop ((l note-list) (y (+ (body-top) 2)) (i 0))
        (if (and (pair? l) (< i 8))
            (let ((m (car l)))
              (if (gui-visible? y 50)
                  (begin
                    (note-badge 10 y m)
                    (txt-fit 64 (+ y 2) 170 (if (str-empty? (note-title m)) (note-plain-head m) (note-title m))
                             (if (note-read? m) theme-text-sub theme-text-main))
                    (txt-right 310 (+ y 2) (note-time m) theme-text-muted)
                    (txt-fit 10 (+ y 26) 300 (note-plain-head m) theme-text-muted)
                    (gui-line 10 (+ y 49) 310 (+ y 49) theme-divider)))
              (loop (cdr l) (+ y 52) (+ i 1)))))))

;; 4. Alert, button --------------------------------------------------------------------------------

;; Each second: the LED, a long rich message's next screenful, the next picture download
(set! app-tick-proc
      (lambda (tick)
        (note-pic-step!)
        (note-scroll-step! tick)
        (if (not (= note-alert 0))
            (begin
              (if (= (remainder tick 2) 0)
                  (if (= note-alert -1) (ws2812-set 255 0 0) (ws2812-set 255 140 0))
                  (ws2812-clear))
              (if (> note-alert 0)
                  (begin (set! note-alert (- note-alert 1))
                         (if (= note-alert 0) (ws2812-clear))))))))

;; A short press first marks everything read
(set! app-button
      (lambda ()
        (if (> (note-unread) 0) (note-mark-read!) (app-next-page!))))

(set! app-subtitle-proc
      (lambda (items)
        (let ((n (note-unread))) (if (> n 0) (string-append "未读 " (number->string n)) #f))))

;; 5. The web page's calls --------------------------------------------------------------------------

(define (note->alist m)
  (list (cons 'id (note-id m)) (cons 'level (note-level m)) (cons 'read (note-read? m)) (cons 'time (note-time m))
        (cons 'from (note-from m)) (cons 'title (note-title m)) (cons 'text (note-text m))))

(define (note-answer)
  (web-ok (cons 'messages (map note->alist note-list)) (cons 'unread (note-unread)) (cons 'proxy (app-proxy))))

(define (app-web name body)
  (cond
    ((string=? name "list") (note-answer))
    ((string=? name "notify")
     (let ((text (or (web-field body "text") "")) (title (or (web-field body "title") "")))
       (if (and (str-empty? text) (str-empty? title))
           (web-error "empty message")
           (begin
             (note-add! 0 (or (web-field body "level") "info") (note-now) (or (web-field body "from") "") title text #f)
             (note-save!)
             (note-answer)))))
    ((string=? name "read") (note-mark-read!) (note-answer))
    ((string=? name "pics")                ; the web page wrote pictures into img/: take them
     (note-pics-clean!)
     (app-invalidate-all)
     (note-answer))
    ((string=? name "delete")
     (let ((id (web-field-int body "id" -1)))
       (set! note-list (filter (lambda (m) (not (= (note-id m) id))) note-list))
       (note-save!)
       (note-answer)))
    ((string=? name "clear")
     (set! note-list '())
     (set! note-alert 0)
     (ws2812-clear)
     (note-save!)
     (note-answer))
    (else (web-error (string-append "unknown call: " name)))))

;; 6. Start ------------------------------------------------------------------------------------------

(note-load!)
(note-pics-clean!)
(set! app-render-empty-pages '(0 1))    ; drawn from the board's own list, also without the proxy

(define (note-url) (app-url (string-append "/app/notifier?n=" (number->string (min 50 (note-keep))))))

(app-watch! note-url 15000 note-data!)   ; new messages also while another app's page shows

(app-define! "消息提示"
  (list (app-page "最新" note-url NOTE-INTERVAL note-render-latest)
        (app-page "全部" note-url NOTE-INTERVAL note-render-all)))
