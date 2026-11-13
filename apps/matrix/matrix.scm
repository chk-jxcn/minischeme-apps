;;; =========================================================================
;;; LED matrix effects (矩阵灯), on the app framework (applib.scm).
;;; For a board with an 8 x 8 RGB LED matrix (the `matrix` extension): each
;;; page is one effect, the button goes to the next one (and the carousel of
;;; the app framework turns them by itself: carousel / carousel_seconds).
;;;   clock    the time scrolls by in 3 x 5 digits, the bottom row counts seconds
;;;   rainbow  a diagonal colour wave
;;;   rain     green drops falling
;;;   life     Conway's game of life on a torus, coloured by age
;;;   fire     flames from the bottom row
;;;   drawing  the picture painted on the app's web page (web.html), kept in drawing.txt
;;; The screen (a virtual one on the matrix board: see it in the WebREPL mirror)
;;; shows the same 64 cells once a second. Without the extension only that
;;; preview runs.
;;; =========================================================================

(define mx-has (api-has? "matrix-draw"))
(define mx-buf (make-vector 64 0))       ; #xRRGGBB, row by row from the top left
(define mx-mode -1)                      ; the page whose effect is running
(define mx-next 0)                       ; (time-ms) of the next frame
(define mx-since 0)                      ; (time-ms) when the effect started
(define mx-t 0)                          ; frames of this effect
(define mx-seed 4711)

(define (mx-cfg-int key default lo hi)
  (clamp (or (string->fixed (app-config key default) 0) lo) lo hi))

;; 0 .. n-1 (the API's random is not on every firmware)
(define (mx-rnd n)
  (set! mx-seed (remainder (+ (* mx-seed 1103) 12345) 65536))
  (remainder (quotient mx-seed 7) n))

(define (mx-odd? n) (= (remainder n 2) 1))
(define (mx-rgb r g b) (+ (* r 65536) (* g 256) b))
(define (mx-set! x y c) (vector-set! mx-buf (+ (* y 8) x) c))

;; A colour wheel: 0 red, 85 green, 170 blue, back to red at 256
(define (mx-wheel h)
  (let ((h (remainder h 256)))
    (cond ((< h 85) (mx-rgb (- 255 (* h 3)) (* h 3) 0))
          ((< h 170) (let ((k (- h 85))) (mx-rgb 0 (- 255 (* k 3)) (* k 3))))
          (else (let ((k (- h 170))) (mx-rgb (* k 3) 0 (- 255 (* k 3))))))))

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
        (secs (quotient (* 8 (or (string->fixed app-sec 0) 0)) 60)))
    (let xs ((x 0))
      (if (< x 8)
          (let* ((ci (remainder (+ off x) mx-ncols))
                 (mask (vector-ref mx-cols ci))
                 (color (mx-wheel (+ 120 (* ci 5)))))
            (mx-set! x 0 0)
            (mx-set! x 6 0)
            (mx-set! x 7 (if (<= x secs) #x101040 0))
            (let ys ((r 0) (m mask))
              (if (< r 5)
                  (begin
                    (mx-set! x (+ r 1) (if (mx-odd? m) color 0))
                    (ys (+ r 1) (quotient m 2)))))
            (xs (+ x 1)))))))

;; Rainbow -------------------------------------------------------------------------------------

(define (mx-rainbow-frame!)
  (let loop ((i 0))
    (if (< i 64)
        (begin
          (vector-set! mx-buf i (mx-wheel (+ (* 10 (+ (remainder i 8) (quotient i 8))) (* mx-t 3))))
          (loop (+ i 1))))))

;; Rain ----------------------------------------------------------------------------------------

(define mx-drops (make-vector 8 0))      ; the head's row in each column (above the top: waiting)
(define MX-TRAIL (vector #xb0ffb0 #x00e000 #x007000 #x002800 #x000c00))

(define (mx-rain-start!)
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
                  (mx-set! x y (if (and (>= d 0) (< d 5)) (vector-ref MX-TRAIL d) 0))
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
  (let loop ((i 0))
    (if (< i 64)
        (let ((age (vector-ref mx-cells i)))
          (vector-set! mx-buf i (if (= age 0) 0 (mx-wheel (+ 85 (* 10 (- age 1))))))   ; green, then to blue
          (loop (+ i 1))))))

;; Fire ----------------------------------------------------------------------------------------

(define mx-heat (make-vector 64 0))      ; 0 .. 255

(define (mx-heat-at x y) (vector-ref mx-heat (+ (* y 8) (clamp x 0 7))))

(define (mx-fire-color h)
  (cond ((< h 85) (mx-rgb (* h 3) 0 0))
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
  (let loop ((i 0))
    (if (< i 64)
        (begin (vector-set! mx-buf i (mx-fire-color (vector-ref mx-heat i))) (loop (+ i 1))))))

;; Drawing: the web page's picture -----------------------------------------------------------

(define MX-DRAW-PATH "drawing.txt")      ; in the app's folder: 64 colours as 384 hex digits
(define MX-DRAW-PAGE 5)
(define mx-pic (make-vector 64 0))
(define mx-pic-hex "")                   ; as stored; "": nothing drawn yet
(define mx-drawn-at #f)                  ; (time-ms) of the web page's last stroke
(define MX-DRAW-HOLD 120000)             ; the carousel stays on the drawing this long after it

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

;; The effects: pages in this order ----------------------------------------------------------

(define MX-NAMES (vector "时钟" "彩虹" "数字雨" "生命游戏" "火焰" "画板"))
(define MX-PERIODS (vector 110 50 90 280 70 500))                  ; ms a frame

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
        ((= mode 4) (vector-fill! mx-heat 0)))
  (if mx-has (matrix-brightness (mx-cfg-int "brightness" "25" 1 100)))
  (app-invalidate-body))

(define (mx-frame!)
  (cond ((= mx-mode 0) (mx-clock-frame!))
        ((= mx-mode 1) (mx-rainbow-frame!))
        ((= mx-mode 2) (mx-rain-frame!))
        ((= mx-mode 3) (mx-life-frame!))
        ((= mx-mode 4) (mx-fire-frame!))
        (else (mx-draw-frame!)))
  (set! mx-t (+ mx-t 1))
  (if mx-has (matrix-draw mx-buf)))

(set! app-step-proc
      (lambda ()
        (let ((now (time-ms)) (page (clamp app-page-index 0 5)))
          (if (not (= page mx-mode)) (mx-start! page now))
          (if (or (>= now mx-next) (< now mx-since))               ; (the clock wrapped)
              (begin
                (mx-frame!)
                (set! mx-next (+ now (vector-ref MX-PERIODS mx-mode))))))
        #f))

;; The screen: the 64 cells as they are now, redrawn once a second
(set! app-tick-proc (lambda (tick) (app-invalidate-body)))

(define (mx-screen-color c)
  (if (= c 0)
      (gui-rgb 24 28 36)
      (gui-rgb (quotient c 65536) (remainder (quotient c 256) 256) (remainder c 256))))

(define (mx-render items)
  (let* ((w (scr-w)) (cx (quotient w 2)) (y (body-top))
         (cell (quotient (min (- w 12) (- (body-bottom) y 60)) 8))
         (x0 (- cx (* cell 4))) (y0 (+ y 28)))
    (txt-center cx y (vector-ref MX-NAMES (clamp app-page-index 0 5)) theme-accent)
    (let loop ((i 0))
      (if (< i 64)
          (begin
            (gui-rect (+ x0 (* cell (remainder i 8))) (+ y0 (* cell (quotient i 8))) (- cell 2) (- cell 2)
                      (mx-screen-color (vector-ref mx-buf i)))
            (loop (+ i 1)))))
    (txt-fit 6 (+ y0 (* cell 8) 8) (- w 12)
             (cond ((not mx-has) "这块板没有 LED 矩阵，只有预览")
                   ((= app-page-index MX-DRAW-PAGE) "在设备网页的应用选项卡里画")
                   (else "按键切换效果"))
             theme-text-muted)))

;; The web page (web.html) -------------------------------------------------------------------
;;   get                  => pixels (384 hex digits), brightness, matrix (whether the board has LEDs)
;;   draw pixels=<hex>    shows the picture at once (and goes to the drawing page); not saved
;;   save pixels=<hex>    the same, and keeps it in drawing.txt
;;   brightness value=<1..100>

(define (mx-web-state)
  (web-ok (cons 'pixels (if (str-empty? mx-pic-hex) #f mx-pic-hex))
          (cons 'brightness (mx-cfg-int "brightness" "25" 1 100))
          (cons 'matrix mx-has)))

(define (mx-web-show! body)
  (and (mx-pic-set! (web-field body "pixels"))
       (begin
         (if (not (= app-page-index MX-DRAW-PAGE)) (app-goto! MX-DRAW-PAGE))
         (if (not (= mx-mode MX-DRAW-PAGE)) (mx-start! MX-DRAW-PAGE (time-ms)))
         (set! mx-drawn-at (time-ms))
         (mx-frame!)
         #t)))

(define (app-web name body)
  (cond
    ((string=? name "get") (mx-web-state))
    ((string=? name "draw")
     (if (mx-web-show! body) (web-ok) (web-error "pixels: expected 384 hex digits")))
    ((string=? name "save")
     (cond ((not (mx-web-show! body)) (web-error "pixels: expected 384 hex digits"))
           ((fs-write MX-DRAW-PATH mx-pic-hex) (web-ok))
           (else (web-error "the picture could not be saved"))))
    ((string=? name "brightness")
     (let ((v (clamp (web-field-int body "value" 25) 1 100)))
       (app-config-set! "brightness" (number->string v))
       (if mx-has (begin (matrix-brightness v) (matrix-show)))
       (web-ok (cons 'brightness v))))
    (else (web-error (string-append "unknown call: " name)))))

;; While someone draws, the carousel does not turn the page away
(set! app-hold-proc
      (lambda ()
        (and mx-drawn-at (= app-page-index MX-DRAW-PAGE)
             (let ((d (- (time-ms) mx-drawn-at))) (and (>= d 0) (< d MX-DRAW-HOLD))))))

(mx-pic-load!)

(app-define! "矩阵灯"
             (list (app-local-page "时钟" mx-render) (app-local-page "彩虹" mx-render)
                   (app-local-page "数字雨" mx-render) (app-local-page "生命游戏" mx-render)
                   (app-local-page "火焰" mx-render) (app-local-page "画板" mx-render)))
