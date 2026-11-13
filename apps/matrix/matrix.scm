;;; =========================================================================
;;; LED matrix effects (矩阵灯), on the app framework (applib.scm).
;;; For a board with an 8 x 8 RGB LED matrix (the `matrix` extension): each
;;; page is one effect.
;;;   clock    the time scrolls by in 3 x 5 digits, the bottom row counts seconds
;;;   rainbow  a diagonal colour wave
;;;   rain     drops falling
;;;   life     Conway's game of life on a torus, coloured by age
;;;   fire     flames from the bottom row
;;;   drawing  the picture painted on the app's web page, kept in drawing.txt
;;;   text     a marquee: the web page turns the text into columns (marquee.txt)
;;;   ball     a ball that rolls where the board is tilted (the `imu` extension)
;;; Which one shows: config `mode`, "auto" (the framework's carousel turns the
;;; pages, the button goes to the next) or one page that stays. Every effect
;;; but the drawing has a colour (color_<page>), empty for its own colours.
;;; The web page (web.html) chooses all of this.
;;; The screen (a virtual one on the matrix board: see it in the WebREPL mirror)
;;; shows the same 64 cells once a second. Without the extension only that
;;; preview runs.
;;; =========================================================================

(define mx-has (api-has? "matrix-draw"))
(define mx-imu (api-has? "imu-accel"))
(define mx-buf (make-vector 64 0))       ; #xRRGGBB, row by row from the top left
(define mx-mode -1)                      ; the page whose effect is running
(define mx-next 0)                       ; (time-ms) of the next frame
(define mx-since 0)                      ; (time-ms) when the effect started
(define mx-t 0)                          ; frames of this effect
(define mx-seed 4711)

(define MX-IDS (vector "clock" "rainbow" "rain" "life" "fire" "drawing" "text" "ball"))
(define MX-NAMES (vector "时钟" "彩虹" "数字雨" "生命游戏" "火焰" "画板" "跑马灯" "小球"))
(define MX-PAGES 8)
(define MX-DRAW-PAGE 5)
(define MX-TEXT-PAGE 6)
(define MX-BALL-PAGE 7)

(define (mx-cfg-int key default lo hi)
  (clamp (or (string->fixed (app-config key default) 0) lo) lo hi))

;; 0 .. n-1 (the API's random is not on every firmware)
(define (mx-rnd n)
  (set! mx-seed (remainder (+ (* mx-seed 1103) 12345) 65536))
  (remainder (quotient mx-seed 7) n))

(define (mx-odd? n) (= (remainder n 2) 1))
(define (mx-rgb r g b) (+ (* r 65536) (* g 256) b))
(define (mx-r c) (quotient c 65536))
(define (mx-g c) (remainder (quotient c 256) 256))
(define (mx-b c) (remainder c 256))
(define (mx-set! x y c) (vector-set! mx-buf (+ (* y 8) x) c))

;; c at num / den of its brightness
(define (mx-dim c num den)
  (mx-rgb (quotient (* (mx-r c) num) den) (quotient (* (mx-g c) num) den) (quotient (* (mx-b c) num) den)))

;; c with pct percent of the way to white
(define (mx-whiten c pct)
  (let ((r (mx-r c)) (g (mx-g c)) (b (mx-b c)))
    (mx-rgb (+ r (quotient (* (- 255 r) pct) 100)) (+ g (quotient (* (- 255 g) pct) 100))
            (+ b (quotient (* (- 255 b) pct) 100)))))

;; A colour wheel: 0 red, 85 green, 170 blue, back to red at 256
(define (mx-wheel h)
  (let ((h (remainder h 256)))
    (cond ((< h 85) (mx-rgb (- 255 (* h 3)) (* h 3) 0))
          ((< h 170) (let ((k (- h 85))) (mx-rgb 0 (- 255 (* k 3)) (* k 3))))
          (else (let ((k (- h 170))) (mx-rgb (* k 3) 0 (- 255 (* k 3))))))))

;; "ff8800" -> the number, #f for anything else
(define (mx-hex-color s)
  (and (string? s) (= (string-length s) 6)
       (let ((c (string->number s 16))) (and c (>= c 0) c))))

;; Settings: read once, changed by the web page -----------------------------------------------

(define mx-colors (make-vector MX-PAGES #f)) ; a page's colour, #f: its own colours
(define mx-fixed #f)                     ; the page that stays, #f: the pages turn (mode = auto)
(define mx-boot-page #f)                 ; shown on the first pass
(define mx-text-ms 100)                  ; the marquee: ms a column
(define mx-tilt 3)                       ; the ball: quarter turns of the sensor against the matrix, +4 mirrored

(define (mx-page-of id)
  (let loop ((i 0))
    (cond ((= i MX-PAGES) #f)
          ((string=? (vector-ref MX-IDS i) id) i)
          (else (loop (+ i 1))))))

(define (mx-settings-load!)
  (let loop ((i 0))
    (if (< i MX-PAGES)
        (begin
          (vector-set! mx-colors i (mx-hex-color (app-config (string-append "color_" (vector-ref MX-IDS i)) "")))
          (loop (+ i 1)))))
  (set! mx-fixed (mx-page-of (app-config "mode" "auto")))
  (set! mx-boot-page mx-fixed)
  (set! mx-text-ms (mx-cfg-int "text_speed" "100" 30 500))
  (set! mx-tilt (mx-cfg-int "tilt" "3" 0 7)))

;; Clock ---------------------------------------------------------------------------------------

;; 3 x 5 digits: five rows each, the left pixel is 4
(define MX-DIGITS
  (vector (vector 7 5 5 5 7) (vector 2 6 2 2 7) (vector 7 1 7 4 7) (vector 7 1 7 1 7) (vector 5 5 7 1 1)
          (vector 7 4 7 1 7) (vector 7 4 7 5 7) (vector 7 1 1 1 1) (vector 7 5 7 5 7) (vector 7 5 7 1 7)))
(define MX-COL-BIT (vector 4 2 1))
(define mx-cols (make-vector 32 0))      ; the text as columns: bit r (1, 2, 4 ...) is row r
(define mx-ncols 8)
(define mx-clock-text "")

(define (mx-col-add! mask)
  (if (< mx-ncols 32)
      (begin (vector-set! mx-cols mx-ncols mask) (set! mx-ncols (+ mx-ncols 1)))))

(define (mx-digit-col d c)
  (let ((rows (vector-ref MX-DIGITS d)) (bit (vector-ref MX-COL-BIT c)))
    (let loop ((r 0) (w 1) (mask 0))
      (if (= r 5)
          mask
          (loop (+ r 1) (* w 2)
                (if (mx-odd? (quotient (vector-ref rows r) bit)) (+ mask w) mask))))))

;; "12:34" -> columns, after 8 empty ones (the text comes in from the right)
(define (mx-clock-text! s)
  (set! mx-clock-text s)
  (set! mx-ncols 0)
  (let pad ((i 0)) (if (< i 8) (begin (mx-col-add! 0) (pad (+ i 1)))))
  (let loop ((i 0))
    (if (< i (string-length s))
        (let ((ch (char->integer (string-ref s i))))
          (cond ((and (>= ch 48) (<= ch 57))
                 (mx-col-add! (mx-digit-col (- ch 48) 0))
                 (mx-col-add! (mx-digit-col (- ch 48) 1))
                 (mx-col-add! (mx-digit-col (- ch 48) 2))
                 (mx-col-add! 0))
                ((= ch 58) (mx-col-add! 10) (mx-col-add! 0))       ; a colon: rows 1 and 3
                (else (mx-col-add! 4) (mx-col-add! 0)))            ; "-" before the clock is set
          (loop (+ i 1))))))

(define (mx-clock-frame!)
  (if (and (= (remainder mx-t mx-ncols) 0) (not (equal? app-time mx-clock-text)))
      (mx-clock-text! app-time))                                   ; a new time starts with a new pass
  (let ((off (remainder mx-t mx-ncols))
        (secs (quotient (* 8 (or (string->fixed app-sec 0) 0)) 60))
        (own (vector-ref mx-colors 0)))
    (let xs ((x 0))
      (if (< x 8)
          (let* ((ci (remainder (+ off x) mx-ncols))
                 (mask (vector-ref mx-cols ci))
                 (color (or own (mx-wheel (+ 120 (* ci 5))))))
            (mx-set! x 0 0)
            (mx-set! x 6 0)
            (mx-set! x 7 (if (<= x secs) (if own (mx-dim own 1 5) #x101040) 0))
            (let ys ((r 0) (m mask))
              (if (< r 5)
                  (begin
                    (mx-set! x (+ r 1) (if (mx-odd? m) color 0))
                    (ys (+ r 1) (quotient m 2)))))
            (xs (+ x 1)))))))

;; Rainbow (one colour: a wave of its brightness) ----------------------------------------------

(define (mx-rainbow-frame!)
  (let ((own (vector-ref mx-colors 1)))
    (let loop ((i 0))
      (if (< i 64)
          (let ((h (+ (* 10 (+ (remainder i 8) (quotient i 8))) (* mx-t 3))))
            (vector-set! mx-buf i
                         (if own
                             (let ((v (remainder (* h 2) 512)))    ; a triangle 0 .. 255 .. 0
                               (mx-dim own (+ 30 (if (< v 256) v (- 511 v))) 285))
                             (mx-wheel h)))
            (loop (+ i 1)))))))

;; Rain ----------------------------------------------------------------------------------------

(define mx-drops (make-vector 8 0))      ; the head's row in each column (above the top: waiting)
(define mx-trail (vector #xb0ffb0 #x00e000 #x007000 #x002800 #x000c00))

(define (mx-rain-colors!)
  (let ((own (vector-ref mx-colors 2)))
    (set! mx-trail
          (if own
              (vector (mx-whiten own 60) own (mx-dim own 1 2) (mx-dim own 1 5) (mx-dim own 1 16))
              (vector #xb0ffb0 #x00e000 #x007000 #x002800 #x000c00)))))

(define (mx-rain-start!)
  (mx-rain-colors!)
  (let loop ((x 0))
    (if (< x 8) (begin (vector-set! mx-drops x (- (mx-rnd 12))) (loop (+ x 1))))))

(define (mx-rain-frame!)
  (let xs ((x 0))
    (if (< x 8)
        (let ((head (+ (vector-ref mx-drops x) 1)))
          (vector-set! mx-drops x (if (> head 12) (- (mx-rnd 10)) head))
          (let ys ((y 0))
            (if (< y 8)
                (let ((d (- head y)))
                  (mx-set! x y (if (and (>= d 0) (< d 5)) (vector-ref mx-trail d) 0))
                  (ys (+ y 1)))))
          (xs (+ x 1))))))

;; Life ----------------------------------------------------------------------------------------

(define mx-cells (make-vector 64 0))     ; 0: dead, else the cell's age in generations
(define mx-cells2 (make-vector 64 0))
(define mx-gen 0)
(define mx-alive 0)
(define mx-still 0)                      ; generations with the same number of cells

(define (mx-life-seed!)
  (set! mx-gen 0)
  (set! mx-still 0)
  (let loop ((i 0))
    (if (< i 64)
        (begin (vector-set! mx-cells i (if (< (mx-rnd 100) 38) 1 0)) (loop (+ i 1))))))

(define (mx-cell x y)
  (if (> (vector-ref mx-cells (+ (* 8 (remainder (+ y 8) 8)) (remainder (+ x 8) 8))) 0) 1 0))

(define (mx-life-step!)
  (let loop ((i 0) (alive 0))
    (if (< i 64)
        (let* ((x (remainder i 8)) (y (quotient i 8))
               (n (+ (mx-cell (- x 1) (- y 1)) (mx-cell x (- y 1)) (mx-cell (+ x 1) (- y 1))
                     (mx-cell (- x 1) y) (mx-cell (+ x 1) y)
                     (mx-cell (- x 1) (+ y 1)) (mx-cell x (+ y 1)) (mx-cell (+ x 1) (+ y 1))))
               (age (vector-ref mx-cells i))
               (next (cond ((and (> age 0) (or (= n 2) (= n 3))) (if (< age 12) (+ age 1) age))
                           ((and (= age 0) (= n 3)) 1)
                           (else 0))))
          (vector-set! mx-cells2 i next)
          (loop (+ i 1) (if (> next 0) (+ alive 1) alive)))
        (let ((old mx-cells))
          (set! mx-cells mx-cells2)
          (set! mx-cells2 old)
          (set! mx-still (if (= alive mx-alive) (+ mx-still 1) 0))
          (set! mx-alive alive)
          (set! mx-gen (+ mx-gen 1))))))

(define (mx-life-frame!)
  (if (> mx-t 0) (mx-life-step!))
  (if (or (= mx-alive 0) (>= mx-still 12) (> mx-gen 150)) (mx-life-seed!))   ; died out or settled
  (let ((own (vector-ref mx-colors 3)))
    (let loop ((i 0))
      (if (< i 64)
          (let ((age (vector-ref mx-cells i)))
            (vector-set! mx-buf i
                         (cond ((= age 0) 0)
                               (own (mx-dim own (- 100 (* 6 (- age 1))) 100))       ; the young ones bright
                               (else (mx-wheel (+ 85 (* 10 (- age 1)))))))          ; green, then to blue
            (loop (+ i 1)))))))

;; Fire ----------------------------------------------------------------------------------------

(define mx-heat (make-vector 64 0))      ; 0 .. 255

(define (mx-heat-at x y) (vector-ref mx-heat (+ (* y 8) (clamp x 0 7))))

(define (mx-fire-color h own)
  (cond (own (if (< h 150) (mx-dim own h 150) (mx-whiten own (quotient (* (- h 150) 60) 105))))
        ((< h 85) (mx-rgb (* h 3) 0 0))
        ((< h 170) (mx-rgb 255 (* (- h 85) 3) 0))
        (else (mx-rgb 255 255 (* (- h 170) 2)))))

(define (mx-fire-frame!)
  (let ys ((y 0))                        ; each row from the one below it (not yet changed this frame)
    (if (< y 7)
        (begin
          (let xs ((x 0))
            (if (< x 8)
                (let ((h (- (quotient (+ (mx-heat-at (- x 1) (+ y 1)) (* 2 (mx-heat-at x (+ y 1)))
                                         (mx-heat-at (+ x 1) (+ y 1)))
                                      4)
                            (+ 14 (mx-rnd 30)))))
                  (vector-set! mx-heat (+ (* y 8) x) (if (< h 0) 0 h))
                  (xs (+ x 1)))))
          (ys (+ y 1)))))
  (let xs ((x 0))
    (if (< x 8) (begin (vector-set! mx-heat (+ 56 x) (+ 150 (mx-rnd 106))) (xs (+ x 1)))))
  (let ((own (vector-ref mx-colors 4)))
    (let loop ((i 0))
      (if (< i 64)
          (begin (vector-set! mx-buf i (mx-fire-color (vector-ref mx-heat i) own)) (loop (+ i 1)))))))

;; Drawing: the web page's picture -----------------------------------------------------------

(define MX-DRAW-PATH "drawing.txt")      ; in the app's folder: 64 colours as 384 hex digits
(define mx-pic (make-vector 64 0))
(define mx-pic-hex "")                   ; as stored; "": nothing drawn yet

;; 384 hex digits -> mx-pic; #f (and nothing changed) when hex is not that
(define (mx-pic-set! hex)
  (and (string? hex) (= (string-length hex) 384)
       (let loop ((i 0))
         (if (= i 64)
             (begin (set! mx-pic-hex hex) #t)
             (let ((c (string->number (substring hex (* i 6) (+ (* i 6) 6)) 16)))
               (and c (>= c 0) (begin (vector-set! mx-pic i c) (loop (+ i 1)))))))))

(define (mx-pic-load!)
  (if (not (mx-pic-set! (and (fs-exists? MX-DRAW-PATH) (fs-read MX-DRAW-PATH))))
      (begin                             ; nothing saved: a heart
        (vector-fill! mx-pic 0)
        (for-each (lambda (i) (vector-set! mx-pic i #xff2040))
                  '(9 10 13 14 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
                    33 34 35 36 37 38 42 43 44 45 51 52)))))

(define (mx-draw-frame!)
  (let loop ((i 0))
    (if (< i 64) (begin (vector-set! mx-buf i (vector-ref mx-pic i)) (loop (+ i 1))))))

;; Text: a marquee -------------------------------------------------------------------------------
;; The web page draws the text (any language) and sends its columns: two hex digits each, bit
;; r (1, 2, 4 ...) is row r. marquee.txt: the columns, a newline, the text (for the page).

(define MX-TEXT-PATH "marquee.txt")
(define MX-TEXT-MAX 600)                 ; columns
(define MX-TEXT-DEFAULT "7f0808087f00417f4100005f")   ; HI!
(define mx-tcols (make-vector 8 0))
(define mx-tn 0)
(define mx-text "HI!")
(define mx-text-hex MX-TEXT-DEFAULT)

;; hex -> mx-tcols; #f (and nothing changed) when it is not 1 .. MX-TEXT-MAX columns
(define (mx-text-set! hex text)
  (and (string? hex) (>= (string-length hex) 2) (= (remainder (string-length hex) 2) 0)
       (<= (quotient (string-length hex) 2) MX-TEXT-MAX)
       (let* ((n (quotient (string-length hex) 2)) (v (make-vector n 0)))
         (let loop ((i 0))
           (if (= i n)
               (begin (set! mx-tcols v) (set! mx-tn n) (set! mx-text-hex hex) (set! mx-text text) #t)
               (let ((c (string->number (substring hex (* i 2) (+ (* i 2) 2)) 16)))
                 (and c (>= c 0) (begin (vector-set! v i c) (loop (+ i 1))))))))))

(define (mx-text-load!)
  (let* ((s (and (fs-exists? MX-TEXT-PATH) (fs-read MX-TEXT-PATH)))
         (parts (if (string? s) (str-split s #\newline) '())))
    (if (not (and (pair? parts) (pair? (cdr parts)) (mx-text-set! (car parts) (cadr parts))))
        (mx-text-set! MX-TEXT-DEFAULT "HI!"))))

(define (mx-text-frame!)
  (let* ((len (+ mx-tn 8))               ; 8 empty columns: the text comes in from the right
         (off (remainder mx-t len))
         (own (vector-ref mx-colors MX-TEXT-PAGE)))
    (let xs ((x 0))
      (if (< x 8)
          (let* ((ci (- (remainder (+ off x) len) 8))
                 (mask (if (< ci 0) 0 (vector-ref mx-tcols ci)))
                 (color (or own (mx-wheel (* (+ ci 8) 4)))))
            (let ys ((r 0) (m mask))
              (if (< r 8)
                  (begin
                    (mx-set! x r (if (mx-odd? m) color 0))
                    (ys (+ r 1) (quotient m 2)))))
            (xs (+ x 1)))))))

;; Ball: rolls downhill ------------------------------------------------------------------------
;; Positions in 1/16 of a cell (0 .. 112), speeds in the same a frame.

(define mx-bx 56)
(define mx-by 56)
(define mx-vx 5)
(define mx-vy 3)

;; The pull along the matrix (x to the right, y down) in mg, from the sensor's x and y:
;; mx-tilt quarter turns, +4 mirrors left and right. #f without a sensor.
;; (On the ESP32-S3-Matrix standing upright the sensor reads about (-1000 0 0): 3 makes that down.)
(define (mx-pull)
  (let ((a (and mx-imu (imu-accel))))
    (and a
         (let* ((sx (car a)) (sy (cadr a)) (q (remainder mx-tilt 4))
                (x (cond ((= q 0) sx) ((= q 1) (- sy)) ((= q 2) (- sx)) (else sy)))
                (y (cond ((= q 0) sy) ((= q 1) sx) ((= q 2) (- sy)) (else (- sx)))))
           (cons (if (>= mx-tilt 4) (- x) x) y)))))

;; Off a wall: back at three quarters of the speed; a slow ball stays (with a sensor: it would
;; hop on the low side for ever)
(define (mx-bounce v)
  (if (and mx-imu (< v 17) (> v -17)) 0 (quotient (* (- v) 3) 4)))

(define (mx-ball-frame!)
  (let ((pull (mx-pull)))
    (if pull
        (begin                           ; rolling: the tilt speeds it up, friction slows it down
          (set! mx-vx (quotient (* (+ mx-vx (quotient (car pull) 60)) 15) 16))
          (set! mx-vy (quotient (* (+ mx-vy (quotient (cdr pull) 60)) 15) 16)))))
  (set! mx-vx (clamp mx-vx -24 24))
  (set! mx-vy (clamp mx-vy -24 24))
  (set! mx-bx (+ mx-bx mx-vx))
  (set! mx-by (+ mx-by mx-vy))
  (if (< mx-bx 0) (begin (set! mx-bx 0) (set! mx-vx (mx-bounce mx-vx))))
  (if (> mx-bx 112) (begin (set! mx-bx 112) (set! mx-vx (mx-bounce mx-vx))))
  (if (< mx-by 0) (begin (set! mx-by 0) (set! mx-vy (mx-bounce mx-vy))))
  (if (> mx-by 112) (begin (set! mx-by 112) (set! mx-vy (mx-bounce mx-vy))))
  (let loop ((i 0))                      ; the trail fades
    (if (< i 64)
        (begin (vector-set! mx-buf i (mx-dim (vector-ref mx-buf i) 5 9)) (loop (+ i 1)))))
  (mx-set! (quotient (+ mx-bx 8) 16) (quotient (+ mx-by 8) 16)
           (or (vector-ref mx-colors MX-BALL-PAGE) (mx-wheel (* mx-t 2)))))

;; The effects: pages in this order ----------------------------------------------------------

(define (mx-period mode)
  (cond ((= mode 0) 110) ((= mode 1) 50) ((= mode 2) 90) ((= mode 3) 280) ((= mode 4) 70)
        ((= mode MX-DRAW-PAGE) 500) ((= mode MX-TEXT-PAGE) mx-text-ms) (else 40)))

(define (mx-start! mode now)
  (set! mx-mode mode)
  (set! mx-t 0)
  (set! mx-since now)
  (set! mx-next now)
  (set! mx-seed (+ 1 (remainder now 60000)))
  (vector-fill! mx-buf 0)
  (cond ((= mode 0) (mx-clock-text! app-time))
        ((= mode 2) (mx-rain-start!))
        ((= mode 3) (mx-life-seed!) (set! mx-alive 1))
        ((= mode 4) (vector-fill! mx-heat 0))
        ((= mode MX-BALL-PAGE)
         (set! mx-bx 56) (set! mx-by 56)
         (set! mx-vx (if mx-imu 0 7)) (set! mx-vy (if mx-imu 0 4))))
  (if mx-has (matrix-brightness (mx-cfg-int "brightness" "25" 1 100)))
  (app-invalidate-body))

(define (mx-frame!)
  (cond ((= mx-mode 0) (mx-clock-frame!))
        ((= mx-mode 1) (mx-rainbow-frame!))
        ((= mx-mode 2) (mx-rain-frame!))
        ((= mx-mode 3) (mx-life-frame!))
        ((= mx-mode 4) (mx-fire-frame!))
        ((= mx-mode MX-DRAW-PAGE) (mx-draw-frame!))
        ((= mx-mode MX-TEXT-PAGE) (mx-text-frame!))
        (else (mx-ball-frame!)))
  (set! mx-t (+ mx-t 1))
  (if mx-has (matrix-draw mx-buf)))

;; Shows a page now (the web page chose it)
(define (mx-show! page)
  (if (not (= app-page-index page)) (app-goto! page))
  (mx-start! page (time-ms))
  (mx-frame!))

(set! app-step-proc
      (lambda ()
        (if mx-boot-page                                           ; mode = one page: it comes first
            (let ((p mx-boot-page))
              (set! mx-boot-page #f)
              (if (not (= app-page-index p)) (app-goto! p))))
        (let ((now (time-ms)) (page (clamp app-page-index 0 (- MX-PAGES 1))))
          (if (not (= page mx-mode)) (mx-start! page now))
          (if (or (>= now mx-next) (< now mx-since))               ; (the clock wrapped)
              (begin
                (mx-frame!)
                (set! mx-next (+ now (mx-period mx-mode))))))
        #f))

;; mode = one page: the carousel does not turn it away (the button still goes on)
(set! app-hold-proc (lambda () (if mx-fixed #t #f)))

;; The screen: the 64 cells as they are now, redrawn once a second
(set! app-tick-proc (lambda (tick) (app-invalidate-body)))

(define (mx-screen-color c)
  (if (= c 0)
      (gui-rgb 24 28 36)
      (gui-rgb (mx-r c) (mx-g c) (mx-b c))))

(define (mx-render items)
  (let* ((w (scr-w)) (cx (quotient w 2)) (y (body-top))
         (cell (quotient (min (- w 12) (- (body-bottom) y 60)) 8))
         (x0 (- cx (* cell 4))) (y0 (+ y 28)))
    (txt-center cx y (vector-ref MX-NAMES (clamp app-page-index 0 (- MX-PAGES 1))) theme-accent)
    (let loop ((i 0))
      (if (< i 64)
          (begin
            (gui-rect (+ x0 (* cell (remainder i 8))) (+ y0 (* cell (quotient i 8))) (- cell 2) (- cell 2)
                      (mx-screen-color (vector-ref mx-buf i)))
            (loop (+ i 1)))))
    (txt-fit 6 (+ y0 (* cell 8) 8) (- w 12)
             (cond ((not mx-has) "这块板没有 LED 矩阵，只有预览")
                   ((and (= app-page-index MX-BALL-PAGE) (not mx-imu)) "没有姿态传感器，小球自己弹")
                   (else "在设备网页的应用选项卡里设置"))
             theme-text-muted)))

;; The web page (web.html) -------------------------------------------------------------------
;;   get                          => everything the page shows
;;   mode value=auto|<page id>    which page shows (kept)
;;   color page=<id> value=<rrggbb or empty>
;;   draw pixels=<384 hex>        the drawing at once, not saved
;;   save pixels=<384 hex>        the same, kept in drawing.txt; the mode becomes the drawing
;;   text cols=<hex> text=<text>  the marquee (kept); the mode becomes the marquee
;;   speed value=<30..500>        the marquee's ms a column
;;   tilt value=<0..7>            the ball: how the sensor sits against the matrix
;;   brightness value=<1..100>

(define (mx-color-hex i) (app-config (string-append "color_" (vector-ref MX-IDS i)) ""))

(define (mx-web-state)
  (web-ok (cons 'pixels (if (str-empty? mx-pic-hex) #f mx-pic-hex))
          (cons 'brightness (mx-cfg-int "brightness" "25" 1 100))
          (cons 'matrix mx-has)
          (cons 'imu mx-imu)
          (cons 'mode (if mx-fixed (vector-ref MX-IDS mx-fixed) "auto"))
          (cons 'page (vector-ref MX-IDS (clamp app-page-index 0 (- MX-PAGES 1))))
          (cons 'colors (list->vector (map mx-color-hex '(0 1 2 3 4 5 6 7))))
          (cons 'text mx-text)
          (cons 'cols mx-text-hex)
          (cons 'speed mx-text-ms)
          (cons 'tilt mx-tilt)
          (cons 'accel (let ((a (and mx-imu (imu-accel)))) (if a (list->vector a) #f)))))

(define (mx-mode-set! page)
  (set! mx-fixed page)
  (app-config-set! "mode" (if page (vector-ref MX-IDS page) "auto"))
  (if page (mx-show! page)))

(define (app-web name body)
  (cond
    ((string=? name "get") (mx-web-state))
    ((string=? name "mode")
     (let* ((v (or (web-field body "value") "")) (page (mx-page-of v)))
       (if (or page (string=? v "auto"))
           (begin (mx-mode-set! page) (mx-web-state))
           (web-error "mode: expected auto or a page"))))
    ((string=? name "color")
     (let ((page (mx-page-of (or (web-field body "page") ""))) (v (or (web-field body "value") "")))
       (cond ((not page) (web-error "color: no such page"))
             ((not (or (str-empty? v) (mx-hex-color v))) (web-error "color: expected rrggbb or nothing"))
             (else
              (app-config-set! (string-append "color_" (vector-ref MX-IDS page)) v)
              (vector-set! mx-colors page (mx-hex-color v))
              (if (= page mx-mode) (begin (if (= page 2) (mx-rain-colors!)) (mx-frame!)))
              (web-ok)))))
    ((string=? name "draw")
     (if (mx-pic-set! (web-field body "pixels"))
         (begin (if (= mx-mode MX-DRAW-PAGE) (mx-frame!) (mx-show! MX-DRAW-PAGE)) (web-ok))
         (web-error "pixels: expected 384 hex digits")))
    ((string=? name "save")
     (cond ((not (mx-pic-set! (web-field body "pixels"))) (web-error "pixels: expected 384 hex digits"))
           ((fs-write MX-DRAW-PATH mx-pic-hex) (mx-mode-set! MX-DRAW-PAGE) (web-ok))
           (else (web-error "the picture could not be saved"))))
    ((string=? name "text")
     (let ((text (or (web-field body "text") "")))
       (cond ((not (mx-text-set! (web-field body "cols") text)) (web-error "cols: expected 1 to 600 columns in hex"))
             ((fs-write MX-TEXT-PATH (string-append mx-text-hex (list->string (list #\newline)) text))
              (mx-mode-set! MX-TEXT-PAGE)
              (web-ok))
             (else (web-error "the text could not be saved")))))
    ((string=? name "speed")
     (let ((v (clamp (web-field-int body "value" 100) 30 500)))
       (set! mx-text-ms v)
       (app-config-set! "text_speed" (number->string v))
       (web-ok (cons 'speed v))))
    ((string=? name "tilt")
     (let ((v (clamp (web-field-int body "value" 0) 0 7)))
       (set! mx-tilt v)
       (app-config-set! "tilt" (number->string v))
       (web-ok (cons 'tilt v))))
    ((string=? name "brightness")
     (let ((v (clamp (web-field-int body "value" 25) 1 100)))
       (app-config-set! "brightness" (number->string v))
       (if mx-has (begin (matrix-brightness v) (matrix-show)))
       (web-ok (cons 'brightness v))))
    (else (web-error (string-append "unknown call: " name)))))

(mx-settings-load!)
(mx-pic-load!)
(mx-text-load!)

(app-define! "矩阵灯"
             (list (app-local-page "时钟" mx-render) (app-local-page "彩虹" mx-render)
                   (app-local-page "数字雨" mx-render) (app-local-page "生命游戏" mx-render)
                   (app-local-page "火焰" mx-render) (app-local-page "画板" mx-render)
                   (app-local-page "跑马灯" mx-render) (app-local-page "小球" mx-render)))
