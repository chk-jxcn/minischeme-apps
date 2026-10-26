;;; =========================================================================
;;; MiniScheme Standalone Application: agenda
;;; All-in-One Standalone Scheme Source (Libraries Included for WebREPL)
;;; =========================================================================
;;; [app]
;;; pages = 2
;;; page_ids = list, countdown ; English page names: <app>.<id> in a combined app (front: the first)
;;; id = agenda
;;; name = 日程提醒
;;; description = 一段日程、某一天或倒计时，支持农历和各种重复（每天、每周、每月、每年，或自定义间隔、星期、日期、月份、年份），按提醒时刻和提前提醒强提醒；在设备网页的应用选项卡中编辑；不需要联网
;;; version = 2
;;; api = 1.14 ; the device API it needs: 1.14 runs the inline arithmetic instructions the build emits (--no-inline-arith: 1.9); MSBC 2 images (a symbol table) since 1.9; time-local (1.7), lunar-date (1.0)
;;; applib = 1.0 ; the app library version it needs (apps/lib/, MAJOR.MINOR: the same MAJOR, an equal or higher MINOR)
;;; 
;;; [fields]
;;; ; how the settings page shows each [config] key: type | label | help
;;; ; types: text, number:min-max, bool, select:value=label,value=label
;;; ; (no ASCII ; or # in these lines: they start a comment)
;;; carousel = bool | 自动翻页 | 在日程和倒计时之间自动切换
;;; carousel_seconds = text | 每页秒数 | 一个值，或每页一个，如 20,10
;;; alert = bool | 强提醒 | 到提醒时间时切换到提醒页面，在合集里也会抢占屏幕
;;; alert_priority = text | 提醒优先级 | 1-9，越大越优先。留空：6
;;; alert_exit = select:=应用默认,button=按键确认,time=到时自动关闭,both=按键或到时 | 提醒怎样结束 | 留空：按键或到时
;;; alert_seconds = text | 提醒秒数 | 到时自动关闭的秒数。留空：60
;;; alert_snooze = text | 稍后提醒（分钟） | 长按提醒后，多少分钟再提醒一次。留空：5
;;; 
;;; [config]
;;; carousel = ; empty: config.ini [app] carousel (1: turn the pages by themselves, 0: manual)
;;; carousel_seconds = ; empty: config.ini [app] carousel_seconds (seconds per page, or one per page)
;;; proxy_url = ; Application proxy service URL (empty: use system config.ini)
;;; converter_url = ; Protocol converter URL (empty: use system config.ini)
;;; alert = 1 ; 1: reminders take the screen (0: none)
;;; alert_priority = ; 1..9 (empty: the app's own)
;;; alert_exit = ; button, time or both (empty: the app's own)
;;; alert_seconds = ; seconds before a reminder closes by itself (empty: the app's own)
;;; alert_snooze = ; minutes a long press puts a reminder off (empty: 5)

;;; =========================================================================
;;; Section: apps/lib/gui.scm
;;; =========================================================================
;;; =========================================================================
;;; MiniScheme Embedded GUI & CSS-like Layout Engine
;;; Tailored for ESP32 ILI9488 480x320 Screen & WASM WebREPL Simulator
;;; =========================================================================

;;; -------------------------------------------------------------------------
;;; 1. Standard RGB565 Palette & Modern Dark Theme Constants
;;; -------------------------------------------------------------------------

(define col-black         0)     ; #x0000
(define col-white         65535) ; #xFFFF
(define col-red           63488) ; #xF800
(define col-green         2016)  ; #x07E0
(define col-blue          31)    ; #x001F
(define col-cyan          2047)  ; #x07FF
(define col-magenta       63519) ; #xF81F
(define col-yellow        65504) ; #xFFE0
(define col-orange        64800) ; #xFD20
(define col-gray          33808) ; #x8410
(define col-dark-gray     12710) ; #x31A6
(define col-light-gray    50712) ; #xC618

;; IPS theme: dark slate canvas, outline-only surfaces, bright but not pure
;; white text, luminous accents; plus flat green segment colors for the
;; clock (plain instrument-panel LCD, no glow)
(define theme-bg           2179  ) ; #x0883: Canvas (#0b1118)
(define theme-card-bg      2179  ) ; #x0883: Surfaces are outlined, not filled (#0b1118)
(define theme-card-border  23442 ) ; #x5B92: Slate Outline (#5b7090)
(define theme-card-hdr     4358  ) ; #x1106: Header Strip (#152030)
(define theme-text-main    59262 ) ; #xE77E: Soft White (#e6ecf3)
(define theme-text-sub     48698 ) ; #xBE3A: Light Slate (#bac7d6)
(define theme-text-muted   42392 ) ; #xA598: Label Gray-Blue (#a2b2c6)
(define theme-accent       26270 ) ; #x669E: Sky Cyan (#62d0f0)
(define theme-accent-dark  4586  ) ; #x11EA: Deep Teal (#173f52)
(define theme-success      30386 ) ; #x76B2: Mint Green (#72d696)
(define theme-warning      62954 ) ; #xF5EA: Amber (#f0bc55)
(define theme-danger       60399 ) ; #xEBEF: Coral (#ee7c7c)
(define theme-purple       50462 ) ; #xC51E: Lavender (#c0a2f2)
(define theme-dark-gray    12809 ) ; #x3209: Inactive Element (#34414f)
(define theme-divider      27667 ) ; #x6C13: Divider lines (#688098): darker ones vanish on the panel
(define theme-seg-on       28271 ) ; #x6E6F: Flat LCD segment green (#6fcf7f)
(define theme-seg-off      4419  ) ; #x1143: Unlit segment ghost (#142a1c)

;;; -------------------------------------------------------------------------
;;; 1b. Color schemes: color aliases, a day and a night scheme
;;; -------------------------------------------------------------------------
;; Colors are named by alias: titlebar_bg, text_fg, card_border, bar_fg ...
;; The value of an alias, the first found wins:
;;   1. a color given to the call itself (a number, "#rrggbb", rgb(r, g, b))
;;   2. the app's theme.css (in its folder), the block of the scheme in use
;;   3. the system's /spiffs/theme.css (theme-css, API 1.8), the same block
;;   4. the app's own defaults (theme-defaults!)
;;   5. the built-in day or night scheme (THEME-DAY, THEME-NIGHT)
;; When none of them names the alias, the same steps for its category, the
;; part after the last "_" (titlebar_bg -> bg, text_sub_fg -> fg,
;; card_border -> border). A value is #rgb, #rrggbb, rgb(r, g, b) or
;; another alias, so names of your own work too:
;;   day   { my_orange: #f08c32; warning_fg: my_orange; }
;;   night { titlebar_bg: #152030; }
;;   *     { seg_on_fg: #6fcf7f; }        (every scheme)
;;   sakura { bg: #fff4f6; }              (a scheme of your own)
;; The mode (config.ini [theme], an app's own config.ini may override):
;;   theme        auto (default), day or night
;;   theme_switch light (default: light-lux at or over theme_light_day is
;;                day, at or under theme_light_night night), time
;;                (theme_day_start .. theme_night_start) or sun (sunrise to
;;                sunset at theme_lat / theme_lon; the time when unknown)
;;   theme_day / theme_night  the scheme each mode uses: day / night, or a
;;                block of theme.css of your own
;; The theme-* colors above are set from the aliases at the start and again
;; whenever the mode or a theme.css changes (theme-tick!, from the app loop).

(define THEME-NIGHT
  '(("bg" . "#0b1118") ("fg" . "#e6ecf3") ("border" . "#5b7090")
    ("card_bg" . "bg") ("card_border" . "#5b7090") ("titlebar_bg" . "#152030")
    ("text_fg" . "#e6ecf3") ("text_sub_fg" . "#bac7d6") ("text_muted_fg" . "#a2b2c6")
    ("accent_fg" . "#62d0f0") ("accent_bg" . "#173f52")
    ("success_fg" . "#72d696") ("warning_fg" . "#f0bc55") ("danger_fg" . "#ee7c7c") ("purple_fg" . "#c0a2f2")
    ("inactive_fg" . "#34414f") ("divider_border" . "#688098")
    ("seg_on_fg" . "#6fcf7f") ("seg_off_fg" . "#142a1c")
    ("bar_fg" . "accent_fg") ("bar_bg" . "titlebar_bg") ("icon_fg" . "accent_fg")))

(define THEME-DAY
  '(("bg" . "#ffffff") ("fg" . "#17202b") ("border" . "#8d9cae")
    ("card_bg" . "bg") ("card_border" . "#8d9cae") ("titlebar_bg" . "#d7e1ec")
    ("text_fg" . "#17202b") ("text_sub_fg" . "#33404f") ("text_muted_fg" . "#556377")
    ("accent_fg" . "#0a6f9c") ("accent_bg" . "#c2e0ee")
    ("success_fg" . "#1d7f45") ("warning_fg" . "#b8700a") ("danger_fg" . "#bf3434") ("purple_fg" . "#6c49b0")
    ("inactive_fg" . "#c4cdd8") ("divider_border" . "#a3b0bf")
    ("seg_on_fg" . "#000000") ("seg_off_fg" . "bg")      ; unlit segments not shown by day
    ("bar_fg" . "accent_fg") ("bar_bg" . "titlebar_bg") ("icon_fg" . "accent_fg")))

(define theme-mode "night")        ; "day" or "night"
(define theme-scheme "night")      ; the block of theme.css in use
(define theme-sys-text #f)         ; the files as last read, to notice a change
(define theme-app-text #f)
(define theme-sys-css '())         ; parsed: ((block (alias . value) ...) ...)
(define theme-app-css '())
(define theme-app-defaults '())    ; ((block (alias . value) ...) ...), theme-defaults!
(define theme-cache '())           ; (alias . rgb565) of the scheme in use
(define theme-ticks 0)
(define theme-utc-offset #f)       ; seconds east of UTC, learnt from the app loop

;; -- small text helpers (gui.scm comes before applib.scm) --

(define (theme-space? c) (let ((b (char->integer c))) (or (= b 32) (= b 9) (= b 10) (= b 13))))

(define (theme-trim s)
  (let* ((n (string-length s))
         (a (let loop ((i 0)) (if (and (< i n) (theme-space? (string-ref s i))) (loop (+ i 1)) i)))
         (b (let loop ((j n)) (if (and (> j a) (theme-space? (string-ref s (- j 1)))) (loop (- j 1)) j))))
    (substring s a b)))

(define (theme-split s ch)
  (let ((n (string-length s)))
    (let loop ((i 0) (start 0) (acc '()))
      (cond ((= i n) (reverse (cons (substring s start n) acc)))
            ((char=? (string-ref s i) ch) (loop (+ i 1) (+ i 1) (cons (substring s start i) acc)))
            (else (loop (+ i 1) start acc))))))

(define (theme-index s ch)
  (let ((n (string-length s)))
    (let loop ((i 0)) (cond ((= i n) #f) ((char=? (string-ref s i) ch) i) (else (loop (+ i 1)))))))

(define (theme-last-index s ch)
  (let loop ((i (- (string-length s) 1))) (cond ((< i 0) #f) ((char=? (string-ref s i) ch) i) (else (loop (- i 1))))))

;; s without /* comments */
(define (theme-uncomment s)
  (let ((n (string-length s)))
    (let loop ((i 0) (acc '()) (in #f))
      (cond ((>= i n) (list->string (reverse acc)))
            ((and (not in) (< (+ i 1) n) (char=? (string-ref s i) #\/) (char=? (string-ref s (+ i 1)) #\*))
             (loop (+ i 2) acc #t))
            ((and in (< (+ i 1) n) (char=? (string-ref s i) #\*) (char=? (string-ref s (+ i 1)) #\/))
             (loop (+ i 2) acc #f))
            (in (loop (+ i 1) acc #t))
            (else (loop (+ i 1) (cons (string-ref s i) acc) #f))))))

;; "name, name { alias: value; ... }" blocks -> ((name (alias . value) ...) ...)
(define (theme-parse text)
  (if (not (string? text))
      '()
      (let loop ((chunks (theme-split (theme-uncomment text) #\})) (acc '()))
        (if (null? chunks)
            (reverse acc)
            (let* ((c (car chunks)) (open (theme-index c #\{)))
              (loop (cdr chunks)
                    (if (not open)
                        acc
                        (let ((pairs (theme-pairs (substring c (+ open 1) (string-length c)))))
                          (let add ((names (theme-split (substring c 0 open) #\,)) (acc acc))
                            (if (null? names)
                                acc
                                (let ((nm (theme-trim (car names))))
                                  (add (cdr names) (if (> (string-length nm) 0) (cons (cons nm pairs) acc) acc)))))))))))))

(define (theme-pairs body)
  (let loop ((parts (theme-split body #\;)) (acc '()))
    (if (null? parts)
        (reverse acc)
        (let ((colon (theme-index (car parts) #\:)))
          (loop (cdr parts)
                (if colon
                    (let ((k (theme-trim (substring (car parts) 0 colon)))
                          (v (theme-trim (substring (car parts) (+ colon 1) (string-length (car parts))))))
                      (if (and (> (string-length k) 0) (> (string-length v) 0)) (cons (cons k v) acc) acc))
                    acc))))))

;; The value of alias in the blocks named scheme (else "*"), the last one wins
(define (theme-block-get css scheme alias)
  (let loop ((l css) (own #f) (any #f))
    (if (null? l)
        (or own any)
        (let* ((b (car l)) (hit (and (or (string=? (car b) scheme) (string=? (car b) "*")) (assoc alias (cdr b)))))
          (cond ((not hit) (loop (cdr l) own any))
                ((string=? (car b) scheme) (loop (cdr l) (cdr hit) any))
                (else (loop (cdr l) own (cdr hit))))))))

;; -- values --

(define (theme-hex s i n) (string->number (substring s i (+ i n)) 16))

;; "#rgb", "#rrggbb", "rgb(r, g, b)" -> rgb565, else #f
(define (theme-literal v)
  (let ((n (string-length v)))
    (cond ((and (= n 7) (char=? (string-ref v 0) #\#))
           (let ((r (theme-hex v 1 2)) (g (theme-hex v 3 2)) (b (theme-hex v 5 2)))
             (and r g b (gui-rgb r g b))))
          ((and (= n 4) (char=? (string-ref v 0) #\#))
           (let ((r (theme-hex v 1 1)) (g (theme-hex v 2 1)) (b (theme-hex v 3 1)))
             (and r g b (gui-rgb (* r 17) (* g 17) (* b 17)))))
          ((and (> n 5) (string=? (substring v 0 4) "rgb(") (char=? (string-ref v (- n 1)) #\)))
           (let ((p (map (lambda (x) (string->number (theme-trim x))) (theme-split (substring v 4 (- n 1)) #\,))))
             (and (= (length p) 3) (integer? (car p)) (integer? (cadr p)) (integer? (caddr p))
                  (gui-rgb (max 0 (min 255 (car p))) (max 0 (min 255 (cadr p))) (max 0 (min 255 (caddr p)))))))
          (else #f))))

;; Steps 2-5 for exactly this alias: its value as written, or #f
(define (theme-lookup alias)
  (or (theme-block-get theme-app-css theme-scheme alias)
      (theme-block-get theme-sys-css theme-scheme alias)
      (theme-block-get theme-app-defaults theme-scheme alias)
      (theme-block-get theme-app-defaults theme-mode alias)
      (let ((d (assoc alias (if (string=? theme-mode "day") THEME-DAY THEME-NIGHT)))) (and d (cdr d)))))

(define (theme-resolve name depth)
  (or (theme-literal name)
      (and (< depth 8)
           (let ((v (theme-lookup name)))
             (or (and v (theme-resolve v (+ depth 1)))
                 (let ((u (theme-last-index name #\_)))   ; the category: titlebar_bg -> bg
                   (and u (theme-resolve (substring name (+ u 1) (string-length name)) (+ depth 1)))))))))

;; A color for drawing: a number as it is, else an alias or a literal resolved
;; through the scheme in use (the foreground for a name nothing resolves)
(define (theme-color c)
  (cond ((number? c) c)
        ((symbol? c) (theme-color (symbol->string c)))
        ((not (string? c)) 0)
        (else
         (let ((hit (assoc c theme-cache)))
           (if hit
               (cdr hit)
               (let ((v (or (theme-resolve c 0) (theme-resolve "fg" 0) 65535)))
                 (set! theme-cache (cons (cons c v) theme-cache))
                 v))))))

;; The app's own defaults: (theme-defaults! "day" '(("titlebar_bg" . "#ffe9a8")))
;; for the day scheme ("night", a scheme of theme.css or "*" for every one)
(define (theme-defaults! scheme alist)
  (set! theme-app-defaults (append theme-app-defaults (list (cons scheme alist))))
  (theme-apply!))

;; -- the mode --

(define (theme-setting key default)
  (let ((v (config-get key))) (if (and (string? v) (> (string-length (theme-trim v)) 0)) (theme-trim v) default)))

(define (theme-number key default)
  (let ((n (string->number (theme-setting key "")))) (if n n default)))

;; "07:30" -> minutes, else default
(define (theme-hm key default)
  (let ((p (theme-split (theme-setting key "") #\:)))
    (if (= (length p) 2)
        (let ((h (string->number (car p))) (m (string->number (cadr p))))
          (if (and (integer? h) (integer? m)) (+ (* h 60) m) default))
        default)))

(define (theme-now-minutes)
  (let ((t (time-local))) (and t (+ (* 60 (list-ref t 3)) (list-ref t 4)))))

(define (theme-in-day? now from to)
  (if (<= from to) (and (>= now from) (< now to)) (or (>= now from) (< now to))))

(define (theme-by-time)
  (let ((now (theme-now-minutes)))
    (if (not now)
        theme-mode
        (if (theme-in-day? now (theme-hm "theme_day_start" 420) (theme-hm "theme_night_start" 1140)) "day" "night"))))

(define (theme-by-light)
  (let ((lux (light-lux))
        (on (theme-number "theme_light_day" 120))
        (off (theme-number "theme_light_night" 50)))
    (cond ((>= lux on) "day")
          ((<= lux off) "night")
          ((= theme-ticks 0) (if (>= lux (quotient (+ on off) 2)) "day" "night"))   ; at the start: the nearer
          (else theme-mode))))                                                  ; between: as it was

;; Sunrise and sunset (minutes of the local day) at lat / lon, #f without
;; the place or the local time's offset (NOAA's approximation, about a minute)
(define (theme-sun-times)
  (let ((lat (theme-number "theme_lat" #f)) (lon (theme-number "theme_lon" #f)) (t (time-local)))
    (and lat lon t theme-utc-offset
         (let* ((pi 3.141592653589793) (rad (/ pi 180.0))
                (doy (theme-day-of-year (car t) (cadr t) (caddr t)))
                (g (* (/ (* 2.0 pi) 365.0) (- doy 1)))
                (eq (* 229.18 (+ 0.000075 (* 0.001868 (cos g)) (* -0.032077 (sin g))
                                 (* -0.014615 (cos (* 2 g))) (* -0.040849 (sin (* 2 g))))))
                (decl (+ 0.006918 (* -0.399912 (cos g)) (* 0.070257 (sin g)) (* -0.006758 (cos (* 2 g)))
                         (* 0.000907 (sin (* 2 g))) (* -0.002697 (cos (* 3 g))) (* 0.00148 (sin (* 3 g)))))
                (la (* lat rad))
                (x (- (/ (cos (* 90.833 rad)) (* (cos la) (cos decl))) (* (/ (sin la) (cos la)) (/ (sin decl) (cos decl)))))
                (ha (/ (acos (max -1.0 (min 1.0 x))) rad))
                (tz (/ theme-utc-offset 60.0))
                (rise (+ (- 720.0 (* 4.0 (+ lon ha)) eq) tz))
                (down (+ (- 720.0 (* 4.0 (- lon ha)) eq) tz)))
           (cons (modulo (inexact->exact (round rise)) 1440) (modulo (inexact->exact (round down)) 1440))))))

(define (theme-day-of-year y m d)
  (let loop ((i 1) (n d))
    (if (>= i m)
        n
        (loop (+ i 1) (+ n (list-ref (list 31 (if (and (= (modulo y 4) 0) (or (not (= (modulo y 100) 0)) (= (modulo y 400) 0))) 29 28)
                                            31 30 31 30 31 31 30 31 30 31)
                                      (- i 1)))))))

(define (theme-by-sun)
  (let ((s (theme-sun-times)) (now (theme-now-minutes)))
    (if (and s now) (if (theme-in-day? now (car s) (cdr s)) "day" "night") (theme-by-time))))

(define (theme-pick-mode)
  (let ((m (theme-setting "theme" "auto")))
    (cond ((string=? m "day") "day")
          ((string=? m "night") "night")
          (else (let ((how (theme-setting "theme_switch" "light")))
                  (cond ((string=? how "time") (theme-by-time))
                        ((string=? how "sun") (theme-by-sun))
                        (else (theme-by-light))))))))

;; The theme-* colors from the aliases of the scheme in use
(define (theme-apply!)
  (set! theme-scheme (theme-setting (if (string=? theme-mode "day") "theme_day" "theme_night") theme-mode))
  (set! theme-cache '())
  (set! theme-bg          (theme-color "bg"))
  (set! theme-card-bg     (theme-color "card_bg"))
  (set! theme-card-border (theme-color "card_border"))
  (set! theme-card-hdr    (theme-color "titlebar_bg"))
  (set! theme-text-main   (theme-color "text_fg"))
  (set! theme-text-sub    (theme-color "text_sub_fg"))
  (set! theme-text-muted  (theme-color "text_muted_fg"))
  (set! theme-accent      (theme-color "accent_fg"))
  (set! theme-accent-dark (theme-color "accent_bg"))
  (set! theme-success     (theme-color "success_fg"))
  (set! theme-warning     (theme-color "warning_fg"))
  (set! theme-danger      (theme-color "danger_fg"))
  (set! theme-purple      (theme-color "purple_fg"))
  (set! theme-dark-gray   (theme-color "inactive_fg"))
  (set! theme-divider     (theme-color "divider_border"))
  (set! theme-seg-on      (theme-color "seg_on_fg"))
  (set! theme-seg-off     (theme-color "seg_off_fg")))

;; Reads the files again; #t when one changed
(define (theme-read!)
  (let ((sys (if (defined? 'theme-css) (theme-css) #f))
        (app (fs-read "theme.css")))
    (let ((changed (not (and (equal? sys theme-sys-text) (equal? app theme-app-text)))))
      (if changed
          (begin (set! theme-sys-text sys)
                 (set! theme-app-text app)
                 (set! theme-sys-css (theme-parse sys))
                 (set! theme-app-css (if (equal? app sys) '() (theme-parse app)))))   ; the settings read the system's
      changed)))

(define (theme-load!)
  (theme-read!)
  (set! theme-mode (theme-pick-mode))
  (theme-apply!))

;; From the app loop once a second (utc: the second of the UTC day, the
;; app-tick's tick once the clock is set: with the local time it gives the
;; time zone, for the sunset); every 10 s the mode and the files are
;; checked. #t when the colors changed: the screen is to be drawn again.
(define (theme-tick! . utc)
  (if (and (pair? utc) (integer? (car utc)) (>= (car utc) 0) (< (car utc) 86400))
      (let ((t (time-local)))
        (if t (set! theme-utc-offset
                    (let ((d (- (+ (* 3600 (list-ref t 3)) (* 60 (list-ref t 4)) (list-ref t 5)) (car utc))))
                      (* 900 (round->exact (/ (cond ((> d 50400) (- d 86400)) ((< d -50400) (+ d 86400)) (else d)) 900))))))))
  (set! theme-ticks (+ theme-ticks 1))
  (if (= (remainder theme-ticks 10) 0)
      (let* ((files (theme-read!)) (mode (theme-pick-mode)) (changed (or files (not (string=? mode theme-mode)))))
        (if changed (begin (set! theme-mode mode) (theme-apply!)))
        changed)
      #f))

(define (round->exact x) (let ((r (round x))) (if (exact? r) r (inexact->exact r))))

(theme-load!)

;; Fonts
(define FONT-SYS-16   0) ; 16px Crisp System UI & CJK Font
(define FONT-CLOCK-32 1) ; 32px Hero Digital Number Font

;; Color constructor
(define (rgb r g b)
  (gui-rgb r g b))

;;; -------------------------------------------------------------------------
;;; 2. CSS-like Box Model & Alignment Primitives
;;; -------------------------------------------------------------------------

;; Render a styled card/box with seamless background and optional border
(define (gui-box x y w h bg border radius)
  (gui-card x y w h radius (if bg bg 0) (if border border 0)))

;; Scoped Clipping helper: executes thunk with clipping region, then restores previous clip
(define (gui-with-clip x y w h thunk)
  (gui-push-clip x y w h)
  (thunk)
  (gui-pop-clip))

;; Scoped Offscreen Sub-Buffer helper: executes thunk on offscreen buffer, then restores main target
(define (gui-with-buffer buf thunk)
  (gui-set-target buf)
  (thunk)
  (gui-reset-target))

;; Content box padding helper: returns (list inner-x inner-y inner-w inner-h)
(define (gui-content-box x y w h pad-x pad-y)
  (list (+ x pad-x)
        (+ y pad-y)
        (max 0 (- w (* 2 pad-x)))
        (max 0 (- h (* 2 pad-y)))))

;; Align text inside a container: halign: 0=left, 1=center, 2=right; valign: 0=top, 1=middle, 2=bottom
(define (gui-text-align x y w h str color font-id halign valign)
  (gui-text-box x y w h str color font-id halign valign))

;; Pill Badge with auto-measured width and centered text
(define (gui-badge x y str bg-col text-col)
  (let* ((tw (gui-text-width str FONT-SYS-16))
         (w (+ tw 14))
         (h 22))
    (gui-round-rect x y w h 11 bg-col #t)
    (gui-text-box x y w h str text-col FONT-SYS-16 1 1)
    w))

;; Sleek Progress Bar
(define (gui-progress-bar x y w h percent fg-col bg-col)
  (let* ((p (max 0 (min 100 percent)))
         (track-bg (if bg-col bg-col theme-card-hdr))
         (fill-fg  (if fg-col fg-col theme-accent))
         (fill-w   (quotient (* (- w 4) p) 100)))
    (gui-round-rect x y w h 4 theme-card-border #f)
    (gui-round-rect (+ x 1) (+ y 1) (- w 2) (- h 2) 3 track-bg #t)
    (if (> fill-w 0)
        (gui-round-rect (+ x 2) (+ y 2) fill-w (- h 4) 2 fill-fg #t))))

;; Interactive Button with centered label and solid seamless background
(define (gui-button x y w h label pressed? bg-col text-col)
  (let* ((bg (if bg-col bg-col (if pressed? theme-accent-dark theme-card-bg)))
         (tc (if text-col text-col theme-text-main))
         (border (if pressed? theme-accent theme-card-border)))
    (gui-card x y w h 6 bg border)
    (gui-text-box x y w h label tc FONT-SYS-16 1 1)))

;;; -------------------------------------------------------------------------
;;; 3. CSS Grid & Flex Layout Calculations
;;; -------------------------------------------------------------------------

;; Compute bounding box for a cell in an N-column, M-row grid
(define (gui-grid-cell origin-x origin-y total-w total-h cols rows col-idx row-idx gap-x gap-y)
  (let* ((usable-w (- total-w (* gap-x (- cols 1))))
         (cell-w   (quotient usable-w cols))
         (usable-h (- total-h (* gap-y (- rows 1))))
         (cell-h   (quotient usable-h rows))
         (x        (+ origin-x (* col-idx (+ cell-w gap-x))))
         (y        (+ origin-y (* row-idx (+ cell-h gap-y)))))
    (list x y cell-w cell-h)))

;; Stat Tile: Display icon/title, hero 32px digital number, and unit with padding & clipping
(define (gui-stat-tile x y w h title val-str unit-str val-col)
  ;; Outline only: no fill behind the numbers
  (gui-round-rect x y w h 8 theme-card-border #f)
  ;; Title with 10px padding
  (gui-text-box (+ x 10) (+ y 6) (- w 20) 18 title theme-text-muted FONT-SYS-16 0 1)
  ;; Big value centred in the space under the title, clipped to the tile
  ;; push/pop instead of gui-with-clip: no closure, no heap environment
  (let ((vy (+ y 24 (max 0 (quotient (- h 24 40) 2)))))
    (gui-push-clip (+ x 10) vy (- w 18) 44)
    (gui-text-styled (+ x 10) vy val-str val-col FONT-CLOCK-32)
    (if (> (string-length unit-str) 0)
        (let ((val-w (gui-text-width val-str FONT-CLOCK-32)))
          (gui-text-styled (+ x 12 val-w) (+ vy 12) unit-str theme-text-sub FONT-SYS-16)))
    (gui-pop-clip)))

;;; -------------------------------------------------------------------------
;;; 4. WiFi Signal & System Indicators
;;; -------------------------------------------------------------------------

(define (gui-draw-wifi-icon x y connected? rssi)
  (let loop ((i 0))
    (if (< i 4)
        (let* ((bx (+ x (* i 5)))
               (bh (+ 4 (* i 3)))
               (by (+ y 14 (- bh)))
               (active? (and connected? (>= rssi (- -90 (* i 15)))))
               (col (if active? theme-success theme-dark-gray)))
          (gui-rect bx by 3 bh col #t)
          (loop (+ i 1))))))

;;; -------------------------------------------------------------------------
;;; 5. Declarative Widget Representation & Touch Dispatch
;;; -------------------------------------------------------------------------

(define (make-widget type id x y w h props on-click)
  (list type id x y w h props on-click))

(define (widget-type w)     (car w))
(define (widget-id w)       (cadr w))
(define (widget-x w)        (caddr w))
(define (widget-y w)        (cadddr w))
(define (widget-w w)        (car (cddddr w)))
(define (widget-h w)        (cadr (cddddr w)))
(define (widget-props w)    (caddr (cddddr w)))
(define (widget-handler w)  (cadddr (cddddr w)))

(define (gui-hit-test widgets tx ty)
  (let loop ((ws widgets))
    (if (null? ws)
        #f
        (let ((w (car ws)))
          (let ((x (widget-x w))
                (y (widget-y w))
                (width (widget-w w))
                (height (widget-h w)))
            (if (and (>= tx x) (< tx (+ x width))
                     (>= ty y) (< ty (+ y height)))
                w
                (loop (cdr ws))))))))

(define (gui-dispatch-touch widgets)
  (let ((touch (gui-touch-poll)))
    (if touch
        (let ((hit (gui-hit-test widgets (car touch) (cdr touch))))
          (if (and hit (procedure? (widget-handler hit)))
              ((widget-handler hit) hit touch)))
        #f)))

;;; -------------------------------------------------------------------------
;;; 6. Framebuffer, Color Depth & Palette Configuration Helpers
;;; -------------------------------------------------------------------------

(define (gui-fb? . args)
  (if (null? args)
      (gui-framebuffer-enabled?)
      (gui-framebuffer-enable (car args))))

(define (gui-bpp . args)
  (if (null? args)
      (gui-color-depth)
      (gui-color-depth (car args))))

(define (gui-vfb-ram)
  (gui-framebuffer-ram))

;;; -------------------------------------------------------------------------
;;; 7. Multi-Dirty Rects & Scanline Banding Helpers
;;; -------------------------------------------------------------------------

(define (gui-dirty-count)
  (gui-dirty-rect-count))

(define (gui-get-dirty-list)
  (gui-dirty-rects))

(define (gui-flush-partial)
  (gui-flush-dirty))

(define (gui-with-bands band-height thunk)
  (gui-render-bands band-height thunk))




;;; =========================================================================
;;; Section: apps/lib/infopages.scm
;;; =========================================================================
;;; =========================================================================
;;; Hardware pages, shared by every app (tools/build_apps.py puts this file
;;; after gui.scm in each app's image; it needs only gui.scm).
;;;
;;; KEY 18 held 8 s opens them over whatever the app shows (the short, the
;;; long and the mid press belong to the app); short presses turn them
;;; (memory, storage, network, system); a long press goes back to the app;
;;; a mid press (3.5 s) opens the system settings (the firmware does that).
;;; The device layer (minischeme_device.c) calls the hooks below:
;;; info-long-press for the hold and, while (info-active?), for the long
;;; press; info-button for short presses while open; info-tick every second. While open, the app's
;;; gui-render-proc is set aside and restored afterwards; the app keeps
;;; running underneath (its ticks and feeds), only its drawing is replaced.
;;;
;;; An app that needs to know (applib pauses its carousel) sets
;;; info-on-change to (lambda (open?) ...).
;;; =========================================================================

(define INFO-PAGE-NAMES '("内存" "存储" "网络" "系统"))
(define info-page #f)                 ; 0..3 while the pages show, else #f
(define info-on-change #f)            ; the app's (lambda (open?) ...), or #f
(define info-app-render #f)           ; the app's gui-render-proc while they show
(define info-time "--:--")            ; the clock, from the device tick
(define INFO-F 7)                     ; font slot: a 16 px CJK font while open
(define INFO-HDR-H 32)
(define INFO-TOP 42)
(define INFO-ROW 26)

;; ---- Hooks --------------------------------------------------------------------------------

(define (info-active?) (and info-page #t))

(define (info-long-press)
  (if info-page (info-close!) (info-open!)))

(define (info-button)
  (set! info-page (remainder (+ info-page 1) (length INFO-PAGE-NAMES)))
  (info-invalidate))

;; Every second, open or not: keeps the clock; open, the figures every 2 s
(define (info-tick hm . rest)
  (let ((tick (if (and (pair? rest) (>= (length rest) 6)) (list-ref rest 5) 0)))
    (if (string? hm) (set! info-time hm))
    (if (and info-page (number? tick) (= (remainder tick 2) 0)) (info-invalidate))))

;; ---- Open / close -------------------------------------------------------------------------

;; The same 16 px font the apps use: the system font when it is a 16 px ROM
;; font, else msyh or simsun from the font ROM (the built-in font lacks most
;; Chinese characters)
(define (info-load-font!)
  (let ((sys (font-info 0)))
    (or (and (pair? sys) (= (cadr sys) 16) (not (eq? (list-ref sys 3) 'builtin)) (use-font INFO-F (car sys)))
        (use-font INFO-F "msyh" 16 'system)
        (use-font INFO-F "simsun" 16 'system))))

(define (info-open!)
  (set! info-app-render gui-render-proc)
  (set! info-page 0)
  (info-load-font!)
  (set! gui-render-proc info-render)
  (if info-on-change (info-on-change #t))
  (info-invalidate))

(define (info-close!)
  (set! info-page #f)
  (set! gui-render-proc info-app-render)
  (set! info-app-render #f)
  (font-unload INFO-F)
  (if info-on-change (info-on-change #f))
  (info-invalidate))

(define (info-invalidate) (gui-invalidate 0 0 (gui-width) (gui-height)))

;; ---- Text and figures ---------------------------------------------------------------------

(define (info-txt x y s c) (gui-text-styled x y s c INFO-F))
(define (info-txt-w s) (gui-text-width s INFO-F))
(define (info-txt-right xr y s c) (info-txt (- xr (info-txt-w s)) y s c))
(define (info-int n) (number->string n))
(define (info-pad2 n) (if (< n 10) (string-append "0" (number->string n)) (number->string n)))

(define (info-ref alist . keys)              ; nested assq, #f when missing
  (let loop ((v alist) (ks keys))
    (cond ((null? ks) v)
          ((not (pair? v)) #f)
          (else (let ((e (assq (car ks) v))) (loop (if e (cdr e) #f) (cdr ks)))))))

;; n / scale with `digits` decimals: (info-fixed 1234 100 2) => "12.34"
(define (info-fixed n scale digits)
  (let* ((unit (expt 10 digits)) (v (quotient (* n unit) scale))
         (frac (number->string (remainder v unit))))
    (string-append (number->string (quotient v unit))
                   (if (> digits 0)
                       (string-append "." (if (< (string-length frac) digits) (string-append "0" frac) frac))
                       ""))))

(define (info-bytes n)
  (cond ((not (number? n)) "-")
        ((>= n 1048576) (string-append (info-fixed n 1048576 2) " MB"))
        ((>= n 1024) (string-append (info-fixed n 1024 1) " KB"))
        (else (string-append (info-int n) " B"))))

(define (info-of a b) (string-append (info-bytes a) " / " (info-bytes b)))

(define (info-duration s)                    ; seconds -> "3天 04:05" / "04:05:06"
  (let ((d (quotient s 86400)) (h (quotient (remainder s 86400) 3600)) (m (quotient (remainder s 3600) 60)))
    (if (> d 0)
        (string-append (info-int d) "天 " (info-pad2 h) ":" (info-pad2 m))
        (string-append (info-pad2 h) ":" (info-pad2 m) ":" (info-pad2 (remainder s 60))))))

;; The clock time of the boot: now minus the uptime ("09:12", "昨天 22:10", "3天前 08:00")
(define (info-boot-time uptime-s)
  (let ((h (string->fixed info-time 0))
        (m (and (>= (string-length info-time) 5) (string->fixed (substring info-time 3 5) 0))))
    (if (not (and h m))
        "-"
        (let* ((at (- (+ (* 60 h) m) (quotient uptime-s 60)))
               (days (if (>= at 0) 0 (+ 1 (quotient (- -1 at) 1440))))
               (clock (+ at (* days 1440)))
               (hm (string-append (info-pad2 (quotient clock 60)) ":" (info-pad2 (remainder clock 60)))))
          (cond ((= days 0) hm)
                ((= days 1) (string-append "昨天 " hm))
                (else (string-append (info-int days) "天前 " hm)))))))

(define (info-ends? s e)
  (and (>= (string-length s) (string-length e))
       (string=? (substring s (- (string-length s) (string-length e)) (string-length s)) e)))

(define (info-starts? s p)
  (and (>= (string-length s) (string-length p)) (string=? (substring s 0 (string-length p)) p)))

;; ---- Rows ---------------------------------------------------------------------------------

(define (info-right) (- (gui-width) 14))

;; label on the left, value right-aligned; a value too wide for that starts
;; after the label column and scrolls or is cut (config.ini [text] marquee)
(define (info-row i label value . color)
  (let ((y (+ INFO-TOP (* i INFO-ROW))) (c (if (pair? color) (car color) theme-text-main))
        (vw (- (info-right) 116)))
    (info-txt 14 y label theme-text-muted)
    (if (> (info-txt-w value) vw)
        (gui-text-fit 116 y vw value c INFO-F)
        (info-txt-right (info-right) y value c))))

;; A thin bar under row i: used of total
(define (info-bar i used total color)
  (let ((y (+ INFO-TOP (* i INFO-ROW) 20)) (w (- (info-right) 14)))
    (gui-rect 14 y w 3 theme-dark-gray #t)
    (if (and (number? used) (number? total) (> total 0) (> used 0))
        (gui-rect 14 y (max 2 (quotient (* w (min used total)) total)) 3 color #t))))

(define (info-divider i)
  (let ((y (+ INFO-TOP (* i INFO-ROW) -6)))
    (gui-line 14 y (info-right) y theme-divider)))

;; ---- Pages --------------------------------------------------------------------------------

(define (info-memory)
  (let* ((info (system-info)) (st (vm-stats))
         (free (info-ref info 'memory 'free-heap)) (total (info-ref info 'memory 'total))
         (heap (info-ref info 'memory 'vm-heap)) (used (info-ref info 'memory 'vm-used)))
    (let ((in-use (if (and free total (<= free total)) (- total free) #f)))
      (info-row 0 "系统内存" (info-of in-use total))
      (info-bar 0 in-use total theme-accent))
    (info-row 1 "空闲" (info-bytes free))
    (info-row 2 "最低空闲" (info-bytes (info-ref info 'memory 'min-free)))
    (info-row 3 "最大连续块" (info-bytes (info-ref info 'memory 'largest-block)))
    (info-divider 4)
    (info-row 4 "VM 堆" (info-of used heap))
    (info-bar 4 used heap theme-success)
    (info-row 5 "存活 / 峰值" (info-of (info-ref st 'live-bytes) (info-ref st 'live-peak)))
    (info-row 6 "累计分配" (string-append (info-int (or (info-ref st 'alloc-kb) 0)) " KB"))
    (info-row 7 "小回收" (info-int (or (info-ref st 'minor-gcs) 0)))
    (info-row 8 "全回收" (info-int (or (info-ref st 'major-gcs) 0)))
    (info-divider 9)
    (info-row 9 "代码 ROM" (info-bytes (info-ref st 'rom-bytes)))
    (info-row 10 "栈峰值" (string-append (info-int (or (info-ref st 'stack-peak) 0)) " / "
                                        (info-int (or (info-ref st 'stack-slots) 0))))))

(define (info-image? name) (or (info-ends? name ".msbc") (info-ends? name ".fasl")))

(define (info-storage)
  ;; an app sees only its own folder: the image's size from there, when it is there
  (let* ((fs (fs-info)) (rom (fontrom-info))
         (me (app-info)) (dir (if (and (pair? me) (= (length me) 4)) (cadddr me) #f))
         (mine (let loop ((f (if dir (fs-list dir) '())))
                 (cond ((null? f) #f)
                       ((info-image? (car (car f))) (cdr (car f)))
                       (else (loop (cdr f)))))))
    (info-row 0 "文件系统" (if fs (info-of (cadr fs) (car fs)) "-"))
    (if fs (info-bar 0 (cadr fs) (car fs) theme-accent))
    (info-row 1 "应用" (info-int (length (app-list))))
    (info-row 2 "本应用" (info-bytes mine))
    ;; program ROM: the firmware image in its partition; the app's Code ROM
    ;; image in the approm partition (0 when the app runs from RAM)
    (let ((fw (flash-app-bytes)) (fw-part (flash-app-partition-bytes))
          (code (vm-rom-bytes)) (code-part (app-rom-capacity)))
      (info-divider 3)
      (info-row 3 "程序 ROM" (info-of fw fw-part))
      (info-bar 3 fw fw-part theme-warning)
      (info-row 4 "应用 ROM" (if (> code 0) (info-of code code-part) "RAM 运行"))
      (if (> code 0) (info-bar 4 code code-part theme-success)))
    (info-divider 5)
    (info-row 5 "系统字库" (if rom (info-of (car rom) (cadr rom)) "-"))
    (if rom (info-bar 5 (car rom) (cadr rom) theme-purple))
    (let loop ((fonts (fontrom-list)) (i 6))
      (if (and (pair? fonts) (< i 14))
          (begin
            (info-row i (car (car fonts)) (info-bytes (cadddr (car fonts))) theme-text-sub)
            (loop (cdr fonts) (+ i 1)))))))

;; Four signal bars for an RSSI
(define (info-signal-bars x y rssi)
  (let ((n (cond ((not (number? rssi)) 0) ((>= rssi -55) 4) ((>= rssi -67) 3) ((>= rssi -78) 2) ((< rssi 0) 1) (else 0))))
    (let loop ((i 0))
      (if (< i 4)
          (begin
            (gui-rect (+ x (* i 5)) (- (+ y 14) (* (+ i 1) 3)) 3 (* (+ i 1) 3)
                      (if (< i n) theme-success theme-dark-gray) #t)
            (loop (+ i 1)))))))

(define (info-proxy)
  (let* ((p1 (config-get "proxy_url"))
         (p (if (and (string? p1) (> (string-length p1) 0)) p1 (config-get "proxy"))))
    (cond ((not (and (string? p) (> (string-length p) 0))) "-")
          ((info-starts? p "http://") (substring p 7 (string-length p)))
          (else p))))

(define (info-network)
  (let* ((info (system-info)) (rssi (info-ref info 'network 'rssi))
         (on (info-ref info 'network 'connected)) (st (json-feed-status))
         (state (info-ref st 'state)))
    (info-row 0 "WiFi" (if on (info-ref info 'network 'ssid) "未连接") (if on theme-text-main theme-warning))
    (info-row 1 "IP" (if on (info-ref info 'network 'ip) "-"))
    (info-row 2 "信号" (if (and on (number? rssi)) (string-append (info-int rssi) " dBm") "-"))
    (if on (info-signal-bars (- (info-right) 86) (+ INFO-TOP (* 2 INFO-ROW)) rssi))
    (info-row 3 "MAC" (or (info-ref info 'chip 'mac) "-"))
    (info-row 4 "时间同步" (if (info-ref info 'time 'ntp-synced) "已同步" "未同步"))
    (info-divider 5)
    (info-row 5 "代理" (info-proxy))
    (info-row 6 "数据源" (cond ((eq? state 'ok) "正常") ((eq? state 'error) "失败")
                              ((eq? state 'idle) "未使用") (else "连接中"))
              (if (eq? state 'error) theme-warning theme-text-main))
    (if (not (eq? state 'idle))
        (begin
          (info-row 7 "上次" (string-append (info-bytes (info-ref st 'bytes)) "  "
                                           (info-int (or (info-ref st 'fetch-ms) 0)) " ms"))
          (info-row 8 "抓取 / 失败" (string-append (info-int (or (info-ref st 'fetches) 0)) " / "
                                                  (info-int (or (info-ref st 'failures) 0))))))))

(define (info-system)
  (let* ((info (system-info)) (up (quotient (or (info-ref info 'time 'uptime-ms) 0) 1000))
         (me (app-info)) (id (if (pair? me) (cadr me) ""))
         (entry (let loop ((as (app-list)))
                  (cond ((null? as) #f) ((string=? (cadr (car as)) id) (car as)) (else (loop (cdr as))))))
         (model (info-ref info 'display 'model)))
    ;; the system fonts may lack "·": figures are set apart by spaces
    (info-row 0 "芯片" (string-append (or (info-ref info 'chip 'model) "-") "  "
                                      (info-int (or (info-ref info 'chip 'cores) 1)) " 核  "
                                      (info-int (or (info-ref info 'chip 'cpu-mhz) 0)) " MHz"))
    (info-row 1 "Flash" (info-bytes (info-ref info 'chip 'flash-bytes)))
    (info-row 2 "ESP-IDF" (or (info-ref info 'chip 'idf) "-"))
    (info-row 3 "固件" (string-append (or (info-ref info 'chip 'build) "-") "  API " (api-version)))
    (info-divider 4)
    (info-row 4 "运行时长" (info-duration up))
    (info-row 5 "启动于" (info-boot-time up))
    (info-row 6 "复位原因" (or (info-ref info 'chip 'reset-reason) "-"))
    (info-divider 7)
    (info-row 7 "应用" (if entry (string-append (caddr entry) " v" (list-ref entry 5)) (if (string=? id "") "-" id)))
    (info-row 8 "显示屏" (if (string? model)
                            (let loop ((i 0))   ; the part before the first "-"
                              (cond ((= i (string-length model)) model)
                                    ((char=? (string-ref model i) #\-) (substring model 0 i))
                                    (else (loop (+ i 1)))))
                            "-"))
    (info-row 9 "显示模式" (string-append (let ((m (info-ref info 'display 'mode))) (if (symbol? m) (symbol->string m) "-"))
                                          "  " (info-int (or (info-ref info 'display 'color-bits) 16)) " 位色"))))

;; ---- The screen ---------------------------------------------------------------------------

(define (info-render)
  (let* ((w (gui-width))
         (ind (string-append (info-int (+ info-page 1)) "/" (info-int (length INFO-PAGE-NAMES))))
         (iw (+ (info-txt-w ind) 12)) (badge (- w 8 (info-txt-w info-time) 8 iw)))
    (gui-clear theme-bg)
    (gui-rect 0 0 w INFO-HDR-H theme-card-hdr #t)
    (info-txt 8 8 "硬件信息" theme-text-main)
    (info-txt (+ 8 (info-txt-w "硬件信息") 10) 8 (list-ref INFO-PAGE-NAMES info-page) theme-accent)
    (gui-round-rect badge 5 iw 22 6 theme-accent-dark #t)
    (info-txt (+ badge 6) 8 ind theme-accent)
    (info-txt-right (- w 8) 8 info-time theme-text-main))
  (cond ((= info-page 0) (info-memory))
        ((= info-page 1) (info-storage))
        ((= info-page 2) (info-network))
        (else (info-system)))
  (info-render-footer))

;; How to leave: over the page's last rows
(define INFO-FTR-H 24)
(define (info-render-footer)
  (let ((y (- (gui-height) INFO-FTR-H)))
    (gui-rect 0 y (gui-width) INFO-FTR-H theme-card-hdr #t)
    (info-txt 8 (+ y 4) "短按翻页  长按返回  中长按：系统设置" theme-text-muted)))


;;; =========================================================================
;;; Section: apps/lib/applib.scm
;;; =========================================================================
;;; =========================================================================
;;; App framework shared by the proxy apps (weather, news, stocks, usage).
;;; Loaded after gui.scm and before the app (tools/build_apps.py).
;;;
;;; An app declares its pages and the framework does the rest:
;;;
;;;   (app-define! "天气预报"
;;;     (list (app-page "首页" url-proc interval-ms render-proc) ...))
;;;
;;;   url-proc     () -> the URL of the page's data, built once at the start;
;;;                pages with the same URL share one document
;;;   interval-ms  how often the board fetches it while the page is shown
;;;   render-proc  (items) -> draws the body between header and footer
;;;
;;; Data: the app proxy (minischeme-proxy) answers {"items":[{t a..e}]}.
;;; Each document is copied into vectors #(t a b c d e) and kept per URL, so a
;;; page switch shows the last data at once while its new fetch runs.
;;; Screen: header (title, page n/N except on the home page, clock), body,
;;; footer (update time, fetch state or the last error).
;;; Button: short press = next page; long press = the hardware pages (memory,
;;; storage, network, system), where a short press turns the page and a long
;;; press goes back; touch = next.
;;; Carousel (the app's ini): carousel = 1 turns the pages by themselves,
;;; carousel_seconds = 10 per page, or one value per page ("15,10,10", the
;;; last one repeats); a faint bar left of the page number counts down.
;;; =========================================================================

;; The version of the app library (every file of apps/lib/, one bundle): MAJOR.MINOR.
;; A backward compatible change raises MINOR, an incompatible one MAJOR; an app
;; declares the version it needs in meta.ini ([app] applib = 1.0) and builds with
;; the same MAJOR and an equal or higher MINOR (tools/build_apps.py, the WebREPL).
(define applib-version "1.0")

;; 1. Fonts, layout, text -------------------------------------------------------

(define F-TEXT 2)               ; CJK text: a 16 px face from the system font ROM
(define F-BIG FONT-CLOCK-32)    ; digits " %-./0123456789:AMP" only

;; Font slot 2: the default font chosen for the system text (font 0, set by
;; config.ini [fonts] font_override system_16:<name>) when it is 16 px like
;; the layouts, else msyh / simsun 16 from the font ROM. The built-in font 0
;; has too few CJK characters for headlines, so it is never used here.
(define (app-init-fonts!)
  (let ((sys (font-info 0)))   ; (name height glyphs source bytes), #f when built in
    (or (and (pair? sys) (= (cadr sys) 16) (use-font 2 (car sys)))
        (use-font 2 "msyh" 16 'system)
        (use-font 2 "simsun" 16 'system))))

;; The default font changed (WebREPL font manager): load slot 2 again
(define (app-refresh-fonts!)
  (font-unload 2)
  (app-init-fonts!)
  (gui-invalidate 0 0 (gui-width) (gui-height)))

(define HDR-H 32)
(define FTR-H 24)
(define LINE-H 20)
(define (body-top) (+ HDR-H 6))
(define (body-bottom) (- (gui-height) FTR-H 4))
(define (scr-w) (gui-width))

(define (txt x y s c) (gui-text-styled x y s c F-TEXT))
(define (txt-w s) (gui-text-width s F-TEXT))
(define (txt-right xr y s c) (txt (- xr (txt-w s)) y s c))
(define (txt-center cx y s c) (txt (- cx (quotient (txt-w s) 2)) y s c))
(define (txt-fit x y w s c) (gui-text-fit x y w s c F-TEXT))  ; one line; too long: marquee or "…" (config.ini [text])
(define (txt-wrap x y w h s c) (gui-text-area x y w h s c F-TEXT LINE-H))  ; too tall: wrap_marquee or "…"

(define (big x y s c) (gui-text-styled x y s c F-BIG))
(define (big-w s) (gui-text-width s F-BIG))
(define (big-right xr y s c) (big (- xr (big-w s)) y s c))

;; Big number followed by a small unit ("26" "°C")
(define (big-unit x y num unit c)
  (big x y num c)
  (txt (+ x (big-w num) 2) (+ y 2) unit c))

;; Section label with a thin rule after it
(define (section y label)
  (txt 10 y label theme-accent)
  (gui-line (+ 18 (txt-w label)) (+ y 9) (- (scr-w) 10) (+ y 9) theme-divider))

;; Section label, rule, and a note at the right end
(define (section-note y label note)
  (let ((nw (txt-w note)))
    (txt 10 y label theme-accent)
    (gui-line (+ 18 (txt-w label)) (+ y 9) (- (scr-w) 18 nw) (+ y 9) theme-divider)
    (txt-right (- (scr-w) 10) y note theme-text-muted)))

;; 2. Strings and numbers ---------------------------------------------------------

(define (str-split s ch)                 ; "a,b,,c" -> ("a" "b" "" "c")
  (let ((n (string-length s)))
    (let loop ((i 0) (start 0) (acc '()))
      (cond ((= i n) (reverse (cons (substring s start n) acc)))
            ((char=? (string-ref s i) ch) (loop (+ i 1) (+ i 1) (cons (substring s start i) acc)))
            (else (loop (+ i 1) start acc))))))

(define (str-part s ch k)                ; k-th field, "" when missing
  (let ((parts (str-split s ch)))
    (if (< k (length parts)) (list-ref parts k) "")))

(define (str-empty? s) (or (not s) (= (string-length s) 0)))

(define (str-starts? s prefix)
  (and (>= (string-length s) (string-length prefix))
       (string=? (substring s 0 (string-length prefix)) prefix)))

(define (str-contains? s sub)
  (let ((n (string-length s)) (m (string-length sub)))
    (if (> m n)
        #f
        (let loop ((i 0))
          (cond
            ((> (+ i m) n) #f)
            ((string=? (substring s i (+ i m)) sub) #t)
            (else (loop (+ i 1))))))))

;; Percent-encodes a query value byte by byte (strings are UTF-8 bytes)
(define (url-encode s)
  (let ((hex "0123456789ABCDEF") (n (string-length s)))
    (let loop ((i 0) (acc '()))
      (if (= i n)
          (list->string (reverse acc))
          (let* ((c (string-ref s i)) (b (char->integer c)))
            (if (or (and (>= b 48) (<= b 57)) (and (>= b 65) (<= b 90)) (and (>= b 97) (<= b 122))
                    (memv b '(44 45 46 95 126)))
                (loop (+ i 1) (cons c acc))
                (loop (+ i 1) (cons (string-ref hex (remainder b 16))
                                    (cons (string-ref hex (quotient b 16)) (cons #\% acc))))))))))

(define (int->str n) (number->string n))

(define (pad2 n) (if (< n 10) (string-append "0" (number->string n)) (number->string n)))

;; Fixed point to text: (fixed->str 1234 2) -> "12.34", (fixed->str -5 1) -> "-0.5"
(define (fixed->str v digits)
  (if (not v)
      "--"
      (let* ((neg (< v 0)) (a (abs v)) (scale (expt 10 digits))
             (frac (number->string (remainder a scale)))
             (frac (string-append (make-string-of #\0 (- digits (string-length frac))) frac)))
        (string-append (if neg "-" "") (number->string (quotient a scale))
                       (if (> digits 0) (string-append "." frac) "")))))

(define (make-string-of ch n)
  (let loop ((i 0) (acc '())) (if (>= i n) (list->string acc) (loop (+ i 1) (cons ch acc)))))

(define (clamp v lo hi) (if (< v lo) lo (if (> v hi) hi v)))

(define (list-min l) (fold-left min (car l) l))
(define (list-max l) (fold-left max (car l) l))
(define (list-sum l) (fold-left + 0 l))

(define (take l n) (if (or (null? l) (<= n 0)) '() (cons (car l) (take (cdr l) (- n 1)))))

;; Chinese market colors: red rises, green falls
(define (rise-color v)
  (cond ((not v) theme-text-muted) ((> v 0) theme-danger) ((< v 0) theme-success) (else theme-text-sub)))

;; 3. Proxy items ------------------------------------------------------------------

(define (it-t it) (vector-ref it 0))                    ; a symbol: 'now, 'day ...
(define (it-f it k) (or (vector-ref it k) ""))          ; k 1..5 = a..e
(define (it-a it) (it-f it 1))
(define (it-b it) (it-f it 2))
(define (it-c it) (it-f it 3))
(define (it-d it) (it-f it 4))
(define (it-e it) (it-f it 5))
(define (it-ints it k) (let ((v (vector-ref it k))) (if v (string->ints v) '())))
(define (it-fixed it k digits) (let ((v (vector-ref it k))) (if v (string->fixed v digits) #f)))
(define (it-int it k) (it-fixed it k 0))

;; A field the app named with app-keys! ("topic"), "" when the item lacks it
(define (it-key it name)
  (let loop ((ks APP-KEYS) (k 0))
    (cond ((null? ks) "")
          ((string=? (car ks) name) (if (< k (vector-length it)) (it-f it k) ""))
          (else (loop (cdr ks) (+ k 1))))))

;; type: the "t" text ("day"); items hold it as a symbol
(define (items-find items type)
  (if (not (pair? items))
      #f
      (let ((sym (string->symbol type)))
        (let loop ((xs items))
          (cond ((not (pair? xs)) #f)
                ((eq? (it-t (car xs)) sym) (car xs))
                (else (loop (cdr xs))))))))

(define (items-all items type)
  (if (not (pair? items))
      '()
      (let ((sym (string->symbol type)))
        (filter (lambda (it) (eq? (it-t it) sym)) items))))

(define (items-where items type k value)   ; first of a type whose field k is value
  (if (not (pair? items))
      #f
      (let ((sym (string->symbol type)))
        (let loop ((xs items))
          (cond ((not (pair? xs)) #f)
                ((and (eq? (it-t (car xs)) sym) (equal? (vector-ref (car xs) k) value)) (car xs))
                (else (loop (cdr xs))))))))

;; 4. Charts ---------------------------------------------------------------------------

;; Polyline of a list of integers in [lo, hi]
(define (line-chart x y w h vals lo hi color)
  (if (>= (length vals) 2)
      (gui-chart x y w h (list->vector vals) 0 (length vals) lo hi color)))

;; Vertical bars of a list of integers in [0, hi]; returns the bar pitch
(define (bar-chart x y w h vals hi color)
  (let* ((n (max 1 (length vals))) (pitch (quotient w n)) (bw (max 1 (- pitch 2))))
    (let loop ((v vals) (i 0))
      (if (pair? v)
          (let ((bh (if (> hi 0) (quotient (* (clamp (car v) 0 hi) h) hi) 0)))
            (if (> bh 0) (gui-rect (+ x (* i pitch) 1) (- (+ y h) bh) bw bh color #t))
            (loop (cdr v) (+ i 1)))))
    pitch))

;; Range of a series with a little head room; never empty
(define (series-range vals min-span)
  (if (null? vals)
      (cons 0 min-span)
      (let* ((lo (list-min vals)) (hi (list-max vals)) (span (max min-span (- hi lo)))
             (pad (max 1 (quotient span 8))))
        (cons (- lo pad) (+ lo span pad)))))

(define (progress-bar x y w h pct color)
  (gui-round-rect x y w h 3 theme-dark-gray #t)
  (let ((fw (quotient (* (clamp pct 0 100) w) 100)))
    (if (> fw 0) (gui-round-rect x y (max fw 6) h 3 color #t))))

;; 5. State -------------------------------------------------------------------------------

(define APP-BASE-KEYS '("t" "a" "b" "c" "d" "e"))
(define APP-KEYS APP-BASE-KEYS)              ; read per item: (app-keys! name ...) adds more
(define APP-SELECTORS '((0 prefix "")))      ; every object with a "t"
(define APP-POOL 0)                          ; value text per document: no limit (memory bounds it)
(define APP-VALUE-LEN 0)                     ; bytes per value: no limit
(define APP-CACHE-MAX 3)                     ; documents kept for quick page switches
(define CAROUSEL-BAR-H 4)                    ; countdown bar in the header
(define CAROUSEL-BAR-COLOR 46552)            ; #xB5D8 (#b2b9c2): 3/4 of the way from the header to the text

(define app-carousel #f)                     ; seconds per page (a list) while turning, else #f
(define app-carousel-left 0)                 ; seconds left on this page
(define app-carousel-paused #f)              ; (app-carousel-pause): the page stays until resumed

(define app-title "APP")
(define app-subtitle-proc #f)                ; (items) -> text after the title on page 1
(define app-header-proc #f)                  ; (items x w): draws page 1's title in [x, x + w) itself
(define app-page-title-only #f)              ; #t: pages after the first are titled by their name alone
(define app-tick-proc #f)                    ; (tick) -> called every second
(define app-render-empty-pages '())          ; pages drawn before their data comes (with no items)
(define app-data-proc #f)                    ; (items) -> called when a new document arrives
(define app-views '())                       ; (name . (lambda (items i) ...)): views a combined app can show
(define app-index-always #f)                 ; #t: the page number also on page 1 (a combined app)
(define app-footer-text "")                  ; the footer of a local page (no proxy data)
(define app-long-press #f)                   ; () -> the app's long press, if it has one
(define app-schedule #f)                     ; (at) -> a time of the app's schedule.ini came while it runs
(define app-hold-proc #f)                    ; () -> #t: the carousel waits on this page (the app's own cycle
                                             ; runs); once it says #f again the carousel goes on at once
(define app-show-proc #f)                    ; () -> a page of the app came on screen (app-goto!)
(define app-step-proc #f)                    ; () -> every main-loop pass; #t: it used the feed stream itself
                                             ; (a sync), the framework's step waits
(define app-pages (vector))
(define app-urls (vector))
(define app-page-index 0)
(define app-time "--:--")
(define app-sec "--")                        ; the device clock's seconds, weekday and date (月日)
(define app-week "")
(define app-date "")
(define app-utc-sec 0)                       ; second of the UTC day (the tick once the clock is synced)
(define app-lunar "")                       ; the device's lunar month and day (八月十九), "" unsynced
(define app-cache '())                       ; #(url items time second) per fetched URL
(define app-error #f)                        ; message of the last error object
(define app-error-url "")                    ; the page URL whose document carried it
(define app-last-seq 0)
(define app-feed-url "")
(define app-loading #f)                      ; fetch requested, no document yet

;; More fields per item beyond t, a..e, by name: (app-keys! "topic" "text") before
;; app-define!; read them with (it-key it "topic")
(define (app-keys! . names) (set! APP-KEYS (append APP-BASE-KEYS names)))

(define (app-page name url-proc interval render) (vector name url-proc interval render))
;; A view of the app's data a combined app (apps/lib/combo.scm) may show as
;; one of its pages: "news[0]" calls (proc items 0) on the page it belongs to
(define (app-view! name page proc) (set! app-views (cons (list name page proc) app-views)))
;; A page drawn from the app's own data (memos, messages): no fetch, render gets '()
(define (app-local-page name render) (vector name (lambda () "") 0 render))
(define (app-local? i) (string=? (vector-ref app-urls i) ""))
(define (app-npages) (vector-length app-pages))
(define (app-cur) (vector-ref app-pages app-page-index))

(define (app-config key default)
  (let ((v (config-get key)))
    (if (and (string? v) (> (string-length v) 0)) v default)))

;; config.ini [server] proxy_url / [app] proxy = http://<host>:8087 (minischeme-proxy); "" when unset
(define (app-proxy)
  (let* ((p (app-config "proxy_url" (app-config "proxy" ""))) (n (string-length p)))
    (if (and (> n 0) (char=? (string-ref p (- n 1)) #\/)) (substring p 0 (- n 1)) p)))

(define (app-url path) (string-append (app-proxy) path))

(define (app-cache-entry url)
  (let loop ((c app-cache))
    (cond ((null? c) #f)
          ((equal? (vector-ref (car c) 0) url) (car c))
          (else (loop (cdr c))))))

;; Keep all page documents in memory so page switches are instantaneous
(define (app-cache-max) (max APP-CACHE-MAX (app-npages)))

;; Newest first; past (app-cache-max) documents the oldest one goes, never the
;; home page's (the page shown most)
(define (app-cache-put! url items)
  (let ((c (cons (vector url items app-time app-utc-sec)
                 (filter (lambda (e) (not (equal? (vector-ref e 0) url))) app-cache))))
    (set! app-cache
          (if (<= (length c) (app-cache-max))
              c
              (let ((home (vector-ref app-urls 0)))
                (reverse (let drop ((r (reverse c)))
                           (cond ((null? r) r)
                                 ((equal? (vector-ref (car r) 0) home) (cons (car r) (drop (cdr r))))
                                 (else (cdr r))))))))))

;; Page i's data is younger than the page's interval: shown again without
;; fetching (a page turn or the carousel does not fetch it every time)
(define (app-fresh? i)
  (let ((e (app-cache-entry (vector-ref app-urls i))))
    (and e (< (* 1000 (modulo (- app-utc-sec (vector-ref e 3)) 86400))
              (vector-ref (vector-ref app-pages i) 2)))))

;; The one stream follows the page on screen once its data is due
(define (app-follow-page!)
  (if (and (not (equal? (vector-ref app-urls app-page-index) app-feed-url))
           (not (app-local? app-page-index))
           (not (app-fresh? app-page-index)))
      (app-start-feed!)))

(define (app-items)
  (let ((e (app-cache-entry (vector-ref app-urls app-page-index))))
    (if e (vector-ref e 1) #f)))

;; (json-feed-status) builds a new list on each call: a caller that needs
;; several fields reads it once and passes it as st
(define (app-status key . st)
  (let ((e (assq key (if (pair? st) (car st) (json-feed-status))))) (if e (cdr e) #f)))

;; 6. Feed --------------------------------------------------------------------------------

(define APP-NO-PROXY "未设置代理：在设置页或 config.ini [app] proxy 填写 http://电脑IP:8087")

(define (app-start-feed!)
  (set! app-feed-url (vector-ref app-urls app-page-index))
  (cond
    ((string=? app-feed-url "")     ; a local page: nothing to fetch
     (set! app-loading #f))
    ((string=? (app-proxy) "")
     (set! app-loading #f)          ; nothing to fetch from: say where to set it
     (set! app-error APP-NO-PROXY))
    (else
        (if (eq? app-error APP-NO-PROXY) (set! app-error #f))   ; set since (a snapshot made without one)
        (set! app-loading #t)
        (json-feed-start app-feed-url (vector-ref (app-cur) 2) APP-KEYS APP-SELECTORS
                         APP-POOL APP-VALUE-LEN 2))))

;; #(type a b c d e ...): the type as a symbol, a slot per key of APP-KEYS,
;; empty values as #f (heap is scarce)
(define (app-read-item i)
  (let* ((n (length APP-KEYS)) (v (make-vector n #f)))
    (let loop ((k 1))
      (if (< k n)
          (let ((s (json-feed-field i k)))
            (if (and s (> (string-length s) 0)) (vector-set! v k s))
            (loop (+ k 1)))))
    (let ((t (json-feed-field i 0)))
      (vector-set! v 0 (if t (string->symbol t) 'none)))
    v))

;; Pre-fetches the next uncached page in the background right after boot
(define (app-prefetch-next!)
  (let loop ((i 0))
    (if (< i (app-npages))
        (let ((url (vector-ref app-urls i)))
          (cond
            ((or (string=? url "") (app-cache-entry url))
             (loop (+ i 1)))
            (else
             (set! app-feed-url url)
             (set! app-loading #t)
             (json-feed-start url (vector-ref (vector-ref app-pages i) 2) APP-KEYS APP-SELECTORS
                              APP-POOL APP-VALUE-LEN 2)
             #t)))
        #f)))

;; A new document: copy it, or keep the old data when the proxy sent an error
(define (app-take-document!)
  (let ((items (let loop ((i (- (json-feed-count) 1)) (acc '()))
                 (if (< i 0) acc (loop (- i 1) (cons (app-read-item i) acc))))))
    (set! app-loading #f)
    (if (and (pair? items) (eq? (it-t (car items)) 'error))
        (begin (set! app-error (it-a (car items))) (set! app-error-url (json-feed-url)))
        (if (app-page-url? (json-feed-url))
            (begin
              (set! app-error #f)
              (app-cache-put! (json-feed-url) items)
              (if app-data-proc (app-data-proc items)))
            (app-watch-deliver! (json-feed-url) items)))
    (if (not (and (pair? items) (eq? (it-t (car items)) 'error)))
        (begin
          ;; every page cached: the firmware's one stream goes back to the
          ;; page on screen when its data is due (app-tick checks again)
          (if (not (app-prefetch-next!)) (app-follow-page!))))
    (if (app-page-url? (json-feed-url)) (app-invalidate-all))))   ; a watched feed's: its alert draws itself

;; 7. Drawing --------------------------------------------------------------------------------

(define (app-invalidate-all) (gui-invalidate 0 0 (scr-w) (gui-height)))
(define (app-invalidate-body) (gui-invalidate 0 HDR-H (scr-w) (- (gui-height) HDR-H)))

;; The text after the title: the home page's subtitle (a city), else the page
;; name. Drawn in another color, not after a separator: the system fonts
;; may lack "·".
(define (app-header-sub items)
  (if (= app-page-index 0)
      (if (and app-subtitle-proc items) (app-subtitle-proc items) #f)
      (vector-ref (app-cur) 0)))

(define (app-demo-data? items)
  (and (pair? items)
       (or (items-find items "demo")
           (let ((loc (items-find items "loc")))
             (and loc (or (string=? (it-b loc) "MiniScheme-Proxy")
                          (string=? (it-b loc) "和风天气(回退)")
                          (str-contains? (it-b loc) "演示")))))))

(define (app-header-title items)
  (let ((t-it (if (pair? items) (items-find items "title") #f)))
    (cond
      ((and t-it (not (str-empty? (it-a t-it))))
       (it-a t-it))
      ((app-demo-data? items)
       (if (str-contains? app-title "【演示数据】")
           app-title
           (string-append app-title "【演示数据】")))
      (else app-title))))

;; 2 px per second, 1 px for pages shown longer than 30 s (at most 90 px)
(define (carousel-px secs) (if (> secs 30) 1 2))
(define (carousel-bar-w secs) (min 90 (* secs (carousel-px secs))))

;; The countdown, right-aligned at xr: a faint track and what is left of it
(define (app-render-countdown xr)
  (let* ((secs (app-page-seconds app-page-index))
         (full (carousel-bar-w secs))
         (left (min full (* (max 0 app-carousel-left) (carousel-px secs))))
         (y (quotient (- HDR-H CAROUSEL-BAR-H) 2)))
    (gui-rect (- xr full) y full CAROUSEL-BAR-H (if app-carousel-paused theme-divider theme-dark-gray) #t)
    (if (and (> left 0) (not app-carousel-paused))  ; paused: one even bar, no countdown
        (gui-rect (- xr left) y left CAROUSEL-BAR-H CAROUSEL-BAR-COLOR #t))))

(define (app-render-header items)
  (let* ((w (scr-w))
         (tw (txt-w app-time))
         (ind (if (or app-index-always (> app-page-index 0))
                  (string-append (int->str (+ app-page-index 1)) "/" (int->str (app-npages)))
                  #f))
         (iw (if ind (+ (txt-w ind) 12) 0))
         (badge (- w 8 tw 8 iw))
         ;; the carousel's countdown sits left of the page number (of the clock on page 1)
         (bar-r (- badge (if ind 6 0)))
         (right (if (pair? app-carousel) (- bar-r (carousel-bar-w (app-page-seconds app-page-index)) 6) badge)))
    (gui-rect 0 0 w HDR-H theme-card-hdr #t)
    (if (pair? app-carousel) (app-render-countdown bar-r))
    (txt-right (- w 8) 8 app-time theme-text-main)
    (if ind
        (begin
          (gui-round-rect badge 5 iw 22 6 theme-accent-dark #t)
          (txt (+ badge 6) 8 ind theme-accent)))
    (if (and app-header-proc (= app-page-index 0))
        (app-header-proc items 8 (- right 14))
        (let* ((named (and app-page-title-only (> app-page-index 0)))
               (title (if named (vector-ref (app-cur) 0) (app-header-title items)))
               (sub (if named #f (app-header-sub items)))
               (title-w (txt-w title)))
          (txt-fit 8 8 (- right 14) title theme-text-main)
          (if (and (not (str-empty? sub)) (< (+ 8 title-w 10) (- right 20)))
              (txt-fit (+ 8 title-w 10) 8 (- right 14 title-w 10) sub theme-accent))))))

(define (app-render-local-footer)
  (let ((y (- (gui-height) FTR-H)))
    (gui-rect 0 y (scr-w) FTR-H theme-card-hdr #t)
    (txt-fit 8 (+ y 3) (- (scr-w) 16) app-footer-text theme-text-muted)))

(define (app-render-footer)
  (if (app-local? app-page-index) (app-render-local-footer) (app-render-feed-footer)))

;; What the footer shows now, as one string: app-tick redraws the footer only
;; when it changed (a redraw also makes the screen be recorded again, which
;; every scrolling title would pay for)
(define app-footer-shown #f)
(define (app-footer-key)
  (cond
    ((app-alert-current) (string-append "alert|" (app-al-id (app-alert-current))))
    ((app-local? app-page-index)
     app-footer-text)
    (else
      (let ((parts (app-feed-footer-parts)))
        (string-append (vector-ref parts 0) "|" (vector-ref parts 1) (if (vector-ref parts 2) "!" ""))))))

;; "http://host:port" shown as "host:port"
(define (app-server-name s)
  (cond ((not (string? s)) "服务器")
        ((str-starts? s "http://") (substring s 7 (string-length s)))
        ((str-starts? s "tcp://") (substring s 6 (string-length s)))
        (else s)))

(define (app-render-feed-footer)
  (let* ((y (- (gui-height) FTR-H))
         (w (scr-w))
         (parts (app-feed-footer-parts))
         (text (vector-ref parts 0))
         (right (vector-ref parts 1)))
    (gui-rect 0 y w FTR-H theme-card-hdr #t)
    (txt-right (- w 8) (+ y 3) right theme-text-muted)
    (txt-fit 8 (+ y 3) (- w 24 (txt-w right)) text (if (vector-ref parts 2) theme-warning theme-text-muted))))

;; #(text right failed?) of the shown page's feed footer
(define (app-feed-footer-parts)
  (let* ((url (vector-ref app-urls app-page-index))
         (entry (app-cache-entry url))
         (upd (and entry (items-find (vector-ref entry 1) "upd")))  ; the server's data time
         ;; the time the server gives for its data ({"t": "upd"}), else when
         ;; this device fetched it (unknown before the clock was set)
         (last (cond ((and upd (it-a upd)) (string-append "更新于 " (it-a upd)))
                     ((not entry) #f)
                     ((string=? (vector-ref entry 2) "--:--") "已更新")
                     (else (string-append "更新于 " (vector-ref entry 2)))))
         ;; this page's fetch only: a prefetch of another page failing says nothing about it
         (mine (equal? (json-feed-url) url))
         (fs (json-feed-status))
         (state (if mine (app-status 'state fs) 'ok))
         (page-error (and app-error (or (eq? app-error APP-NO-PROXY) (equal? app-error-url url)) app-error))
         ;; what the fetch waits for now (firmware 1.0.57+): it replaces an old error
         (step (app-status 'step fs))
         (busy (memq step '(clock register wifi)))
         (failed (and (not busy) (or page-error (eq? state 'error))))
         (text (cond ((eq? step 'register)
                      (string-append "正在向 " (app-server-name (app-status 'step-server fs)) " 注册加密通道..."))
                     ((eq? step 'clock) "等待网络对时...")
                     ((eq? step 'wifi) "等待 WiFi 连接...")      ; firmware 1.0.61+
                     (page-error (string-append "代理: " page-error))
                     ((eq? state 'error) (string-append "连接失败: " (app-status 'error fs)))
                     ((and app-loading mine) (if last (string-append last "，刷新中...") "加载中..."))
                     (last last)
                     (else "等待数据")))
         (ms (app-status 'fetch-ms fs))
         (right (if (and mine (eq? state 'ok) (number? ms) (> ms 0))
                    (string-append (fixed->str (quotient (+ (app-status 'bytes fs) 51) 102) 1) "KB "
                                   (int->str ms) "ms")
                    "")))
    (vector text right failed)))

(define (app-render-waiting)
  (let ((cx (quotient (scr-w) 2)) (y (- (quotient (gui-height) 2) 60)))
    (txt-center cx y "正在获取数据..." theme-text-sub)
    ;; the address without its query: a token there would show on the screen and mirror
    (gui-text-wrap 16 (+ y 34) (- (scr-w) 32) 60 (car (str-split app-feed-url #\?)) theme-text-muted F-TEXT LINE-H)
    (if (or app-error (eq? (app-status 'state) 'error))
        (txt-wrap 16 (+ y 100) (- (scr-w) 32) 80
                  "请在设备网页的常用设置里填写应用代理地址（minischeme-proxy 或公网服务器），并确认能连上"
                  theme-warning))))

(define (app-render)
  (gui-clear theme-bg)
  (app-render-page)
  (gui-flush))

(define (app-render-page)
  (let ((a (app-alert-current)))
    (if a (app-alert-render a) (app-render-pages))))

(define (app-render-pages)
  (let ((items (if (app-local? app-page-index) '() (app-items))))   ; a local page: no document
    (if (gui-visible? 0 HDR-H) (app-render-header items))
    (if (gui-visible? HDR-H (- (gui-height) HDR-H FTR-H))
        (cond ((app-local? app-page-index) ((vector-ref (app-cur) 3) '()))
              (items ((vector-ref (app-cur) 3) items))
            ((memv app-page-index app-render-empty-pages) ((vector-ref (app-cur) 3) '()))
            (else (app-render-waiting)))))
  (if (gui-visible? (- (gui-height) FTR-H) FTR-H) (app-render-footer)))

;; 8. Firmware hooks ---------------------------------------------------------------------------

(define gui-render-proc app-render)

;; carousel = 1 in the app's ini (or config.ini [app]): seconds per page
(define (app-carousel-config)
  (if (member (app-config "carousel" "1") '("1" "on" "yes" "true"))
      (let ((secs (map (lambda (n) (clamp n 3 3600)) (string->ints (app-config "carousel_seconds" "10")))))
        (if (null? secs) '(10) secs))
      #f))

(define (app-page-seconds i)
  (cond
    ((or (not (pair? app-carousel)) (null? app-carousel)) 10)
    ((< i (length app-carousel)) (list-ref app-carousel i))
    (else (list-ref app-carousel (- (length app-carousel) 1)))))

(define (app-carousel-reset!)
  (if (pair? app-carousel) (set! app-carousel-left (app-page-seconds app-page-index))))

(define (app-define! title pages)
  (set! app-title title)
  (set! app-pages (list->vector pages))
  (set! app-urls (list->vector (map (lambda (p) ((vector-ref p 1))) pages)))
  (set! app-page-index 0)
  (set! app-carousel (if (> (length pages) 1) (app-carousel-config) #f))
  (app-carousel-reset!)
  (app-init-fonts!)
  (app-start-feed!)
  (app-alert-wrap-buttons!)
  (app-invalidate-all))

(define (app-goto! i)
  (set! app-page-index i)
  (set! app-carousel-held #f)
  (app-carousel-reset!)
  (if app-show-proc (app-show-proc))
  (app-follow-page!)                 ; its data still fresh: shown from the cache
  (app-invalidate-all))

(define (app-next-page!) (app-goto! (remainder (+ app-page-index 1) (app-npages))))

;; Page i fetches from url from now on (the URL procedures run once, at
;; app-define!); the page shown fetches it at once
(define (app-set-url! i url)
  (if (not (equal? (vector-ref app-urls i) url))
      (begin
        (vector-set! app-urls i url)
        (if (= i app-page-index) (app-start-feed!)))))

;; From the REPL (WebREPL quick commands "暂停翻页" / "恢复翻页"): the carousel
;; stops on this page, or counts it from the start again. Short presses still
;; turn pages. => paused, running, or off (no carousel = 1 in the app's ini).
(define (app-carousel-state) (cond ((not app-carousel) 'off) (app-carousel-paused 'paused) (else 'running)))

(define (app-carousel-pause)
  (set! app-carousel-paused #t)
  (app-carousel-reset!)
  (gui-invalidate 0 0 (scr-w) HDR-H)
  (app-carousel-state))

(define (app-carousel-resume)
  (set! app-carousel-paused #f)
  (app-carousel-reset!)
  (gui-invalidate 0 0 (scr-w) HDR-H)
  (app-carousel-state))

;; One second of the carousel: the next page when this one's time is up. A page whose app
;; cycles through its own screens (app-hold-proc) keeps it waiting, and is left as soon as
;; its cycle went round.
(define app-carousel-held #f)
(define (app-carousel-tick!)
  (cond ((and app-hold-proc (app-hold-proc))
         (if (not app-carousel-held) (gui-invalidate 0 0 (scr-w) HDR-H))
         (set! app-carousel-held #t)
         (app-carousel-reset!))
        (app-carousel-held
         (set! app-carousel-held #f)
         (app-next-page!))
        (else
         (set! app-carousel-left (- app-carousel-left 1))
         (if (<= app-carousel-left 0)
             (app-next-page!)
             (gui-invalidate 0 0 (scr-w) HDR-H)))))

(define (app-step)
  (if (not (and app-step-proc (app-step-proc)))
      (let ((seq (json-feed-seq)))
        (if (and (> seq 0) (not (= seq app-last-seq)))
            (begin
              (set! app-last-seq seq)
              (app-take-document!))))))

(define (app-tick hm sec week date lux bl . rest)
  (let ((tick (if (pair? rest) (car rest) 0)))
    (set! app-sec sec)
    (set! app-utc-sec tick)
    (set! app-week week)
    (set! app-date date)
    (if (and (pair? rest) (pair? (cdr rest))) (set! app-lunar (cadr rest)))
    (if (not (equal? hm app-time))
        (begin
          (set! app-time hm)
          (gui-invalidate 0 0 (scr-w) HDR-H)))
    (if (= (remainder tick 2) 0)   ; the fetch's state, shown only when it changed
        (let ((key (app-footer-key)))
          (if (not (equal? key app-footer-shown))
              (begin
                (set! app-footer-shown key)
                (gui-invalidate 0 (- (gui-height) FTR-H) (scr-w) FTR-H)))))
    (app-alert-tick!)
    ;; also stops on the hardware pages and while an alert shows
    (if (and app-carousel (not (info-active?)) (not app-carousel-paused) (not (app-alert-current)))
        (app-carousel-tick!))
    (if (> (app-npages) 0) (app-follow-page!))   ; the shown page's cached data became due
    (app-watch-step!)                            ; else a watched feed that is due
    (if (theme-tick! tick) (app-invalidate-all))   ; the day / night scheme or a theme.css changed
    (if app-tick-proc (app-tick-proc tick))))

;; Short press: next page (the home page after the last; a carousel's
;; countdown starts again there). A long press opens the hardware pages
;; (apps/lib/infopages.scm, shared by every app); the carousel's countdown
;; starts again when they open and close.
(define (app-button) (app-next-page!))

(set! info-on-change (lambda (open?) (app-carousel-reset!)))

(define (app-touch x y) (app-button))

(define (app-resume)
  (app-init-fonts!)
  (app-start-feed!)
  (app-invalidate-all))

;; 9. Alerts (强提醒) ---------------------------------------------------------------------------
;; Something that needs the user now (a dose due, a new message) takes the screen over the
;; pages: (app-alert! key title render [opts]). The alert with the highest priority shows
;; (1..9, 9 the highest; equal ones in the order they came); a higher one raised meanwhile
;; goes in front, and the one it covered comes back after it with the seconds it had left.
;; While one shows the carousel stops, a short press confirms it (its ack runs, then it
;; closes) and a long press puts it off for a few minutes. How it ends: button (a short
;; press), time (after its seconds), both, or app (only the app's own (app-alert-done! key),
;; e.g. once every dose is taken; a short press still runs its ack). The user's settings
;; come first: a combined app's alerts setting for the member (combo.scm), then the app's
;; own alert (0: none of its alerts), alert_priority, alert_exit (button, time, both),
;; alert_seconds, alert_snooze (minutes); then the options the app passes; then 5 / both /
;; 30 s / 5 min. opts: an alist of (ack . thunk), (priority . n), (exit . symbol),
;; (seconds . n), (snooze . minutes), (full . #t) (render draws the whole screen, its own
;; title bar and hints: the medicine reminder). key: a string the app picks (one per message, per
;; dose time); raising it again updates the alert; an alert that ended is not raised again
;; under the same key until the app restarts.
;; (app-watch! url-proc interval-ms proc): a feed fetched in the background at its
;; interval while the page on screen does not need the stream (a combined app's member
;; that is not on screen still sees its new messages); proc gets its documents.

(define APP-ALERT-PRIORITY 5)
(define APP-ALERT-EXIT 'both)
(define APP-ALERT-SECONDS 30)
(define APP-ALERT-SNOOZE 5)
(define APP-ALERT-DONE-MAX 40)

;; #(id owner app title render ack priority exit seconds snooze seq left wake full)
(define app-alerts '())                      ; in queue order: priority, then arrival
(define app-alert-seq 0)
(define app-alert-clock 0)                   ; seconds since the start (snoozes wake on it)
(define app-alert-done-ids '())              ; alerts that ended: raising one again does nothing
(define app-alert-user-button #f)            ; the app's own presses (app-define! wraps them)
(define app-alert-user-long #f)

(define (app-al-id a) (vector-ref a 0))
(define (app-al-owner a) (vector-ref a 1))
(define (app-al-app a) (vector-ref a 2))
(define (app-al-title a) (vector-ref a 3))
(define (app-al-render a) (vector-ref a 4))
(define (app-al-ack a) (vector-ref a 5))
(define (app-al-priority a) (vector-ref a 6))
(define (app-al-exit a) (vector-ref a 7))
(define (app-al-seconds a) (vector-ref a 8))
(define (app-al-snooze a) (vector-ref a 9))
(define (app-al-seq a) (vector-ref a 10))
(define (app-al-left a) (vector-ref a 11))
(define (app-al-wake a) (vector-ref a 12))
(define (app-al-full a) (vector-ref a 13))

;; A combined app's hooks (combo.scm): which member raises an alert, running code as that
;; member, its name and its settings. Alone, the app itself.
(define (app-alert-owner) #f)
(define (app-alert-owner-id owner) "")
(define (app-alert-run owner thunk) (thunk))
(define (app-alert-app-name owner) app-title)
(define (app-alert-setting owner name) (app-config name #f))   ; runs inside app-alert-run

;; A callback the firmware calls later (fs-download's on-done): it runs as the code that made it
;; (in a combined app, as that member: its folder, its settings)
(define (app-callback proc)
  (let ((owner (app-alert-owner)))
    (lambda args (app-alert-run owner (lambda () (apply proc args))))))

(define (app-alert-opt opts key) (let ((p (assq key opts))) (and p (cdr p))))

;; One setting: the user's (as text), else the app's option, else the default
(define (app-alert-value owner opts key name default)
  (let* ((s (app-alert-run owner (lambda () (app-alert-setting owner name))))
         (v (and (string? s) (> (string-length s) 0) s))
         (given (app-alert-opt opts key)))
    (cond ((and v (eq? key 'exit) (not (eq? given 'app)))      ; app: the app ends it, always
           (let ((sym (string->symbol v))) (if (memq sym '(button time both)) sym (or given default))))
          ((and v (not (eq? key 'exit)) (string->number v)) (string->number v))
          (else (or given default)))))

(define (app-alert-find id)
  (let loop ((l app-alerts))
    (cond ((null? l) #f) ((string=? (app-al-id (car l)) id) (car l)) (else (loop (cdr l))))))

;; The queue with a in its place: a higher priority first, then the one that came first
(define (app-alert-insert a l)
  (cond ((null? l) (list a))
        ((> (app-al-priority a) (app-al-priority (car l))) (cons a l))
        (else (cons (car l) (app-alert-insert a (cdr l))))))

;; The alert on screen: the first one not put off, or #f
(define (app-alert-current)
  (let loop ((l app-alerts))
    (cond ((null? l) #f) ((app-al-wake (car l)) (loop (cdr l))) (else (car l)))))

(define (app-alert-waiting) (length (filter (lambda (a) (not (app-al-wake a))) app-alerts)))

(define (app-alert-changed!)
  (if (not (app-alert-current)) (app-carousel-reset!))   ; the pages again: a full count
  (app-invalidate-all))

(define (app-alert-key-id owner key) (string-append (app-alert-owner-id owner) "/" key))

(define (app-alert! key title render . rest)
  (let* ((opts (if (pair? rest) (car rest) '()))
         (owner (app-alert-owner))
         (id (app-alert-key-id owner key))
         (old (app-alert-find id)))
    (cond
      ((member id app-alert-done-ids) #f)
      ((equal? (app-alert-run owner (lambda () (app-alert-setting owner "alert"))) "0") #f)
      (old (vector-set! old 3 title)
           (vector-set! old 4 render)
           (vector-set! old 5 (app-alert-opt opts 'ack))
           (if (eq? old (app-alert-current)) (app-invalidate-all))
           #t)
      (else
        (let* ((secs (clamp (app-alert-value owner opts 'seconds "alert_seconds" APP-ALERT-SECONDS) 3 3600))
               (a (vector id owner (app-alert-app-name owner) title render (app-alert-opt opts 'ack)
                          (clamp (app-alert-value owner opts 'priority "alert_priority" APP-ALERT-PRIORITY) 1 9)
                          (app-alert-value owner opts 'exit "alert_exit" APP-ALERT-EXIT)
                          secs
                          (clamp (app-alert-value owner opts 'snooze "alert_snooze" APP-ALERT-SNOOZE) 1 120)
                          app-alert-seq secs #f (and (app-alert-opt opts 'full) #t))))
          (set! app-alert-seq (+ app-alert-seq 1))
          (set! app-alerts (app-alert-insert a app-alerts))
          (app-alert-changed!)
          #t)))))

;; The alert leaves the queue for good (its ack first when confirmed)
(define (app-alert-end! a)
  (set! app-alerts (filter (lambda (x) (not (eq? x a))) app-alerts))
  (set! app-alert-done-ids (cons (app-al-id a) app-alert-done-ids))
  (if (> (length app-alert-done-ids) APP-ALERT-DONE-MAX)
      (set! app-alert-done-ids (take app-alert-done-ids APP-ALERT-DONE-MAX)))
  (app-alert-changed!))

;; The app ends its alert (every dose taken, the message read elsewhere)
(define (app-alert-done! key)
  (let ((a (app-alert-find (app-alert-key-id (app-alert-owner) key))))
    (if a (app-alert-end! a))
    (and a #t)))

(define (app-alert-active? key) (and (app-alert-find (app-alert-key-id (app-alert-owner) key)) #t))

;; Short press on an alert: its ack; it closes unless only time ends it, or the app does
(define (app-alert-press! a)
  (let ((ack (app-al-ack a)) (exit (app-al-exit a)))
    (if (not (eq? exit 'time))
        (begin
          (if ack (app-alert-run (app-al-owner a) ack))
          (if (and (not (eq? exit 'app)) (app-alert-find (app-al-id a))) (app-alert-end! a))
          (app-invalidate-all)))))

;; Long press: put off for its snooze minutes; it comes back with its full seconds
(define (app-alert-snooze! a)
  (vector-set! a 12 (+ app-alert-clock (* 60 (app-al-snooze a))))
  (app-alert-changed!))

;; Every second: alerts put off come back; the one on screen counts down when time ends it
(define (app-alert-tick!)
  (set! app-alert-clock (+ app-alert-clock 1))
  (for-each (lambda (a)
              (if (and (app-al-wake a) (>= app-alert-clock (app-al-wake a)))
                  (begin (vector-set! a 12 #f) (vector-set! a 11 (app-al-seconds a)) (app-alert-changed!))))
            app-alerts)
  (let ((a (app-alert-current)))
    (if (and a (memq (app-al-exit a) '(time both)))
        (begin
          (vector-set! a 11 (- (app-al-left a) 1))
          (if (<= (app-al-left a) 0)
              (app-alert-end! a)
              (begin (gui-invalidate 0 0 (scr-w) HDR-H)
                     (gui-invalidate 0 (- (gui-height) FTR-H) (scr-w) FTR-H)))))))

;; The presses go to the alert on screen, else to the app (app-define! wraps them once)
(define (app-alert-wrap-buttons!)
  (if (not app-alert-user-button)
      (begin
        (set! app-alert-user-button app-button)
        (set! app-alert-user-long app-long-press)
        (set! app-button
              (lambda () (let ((a (app-alert-current))) (if a (app-alert-press! a) (app-alert-user-button)))))
        (set! app-long-press
              (lambda ()
                (let ((a (app-alert-current)))
                  (cond (a (app-alert-snooze! a))
                        (app-alert-user-long (app-alert-user-long)))))))))

;; Screen: a title bar in the priority's color with the app's name and the alert's title,
;; the alerts waiting and the countdown; the alert's own body; a footer saying what the
;; presses do
(define (app-alert-color a)
  (let ((p (app-al-priority a))) (cond ((>= p 8) theme-danger) ((>= p 5) theme-warning) (else theme-accent))))

(define (app-alert-render-header a)
  (let* ((w (scr-w)) (tw (txt-w app-time))
         (n (app-alert-waiting))
         (ind (if (> n 1) (string-append "提醒 1/" (int->str n)) #f))
         (iw (if ind (+ (txt-w ind) 12) 0))
         (badge (- w 8 tw 8 iw))
         (timed (memq (app-al-exit a) '(time both)))
         (secs (app-al-seconds a))
         (bar-r (- badge (if ind 6 0)))
         (right (if timed (- bar-r (carousel-bar-w secs) 6) badge))
         (name (app-al-app a)) (nw (txt-w name)))
    (gui-rect 0 0 w HDR-H (app-alert-color a) #t)
    (if timed
        (let* ((full (carousel-bar-w secs)) (left (min full (* (max 0 (app-al-left a)) (carousel-px secs))))
               (y (quotient (- HDR-H CAROUSEL-BAR-H) 2)))
          (gui-rect (- bar-r full) y full CAROUSEL-BAR-H theme-card-hdr #t)
          (if (> left 0) (gui-rect (- bar-r left) y left CAROUSEL-BAR-H theme-bg #t))))
    (txt-right (- w 8) 8 app-time theme-bg)
    (if ind
        (begin (gui-round-rect badge 5 iw 22 6 theme-bg #t)
               (txt (+ badge 6) 8 ind (app-alert-color a))))
    (txt-fit 8 8 (- right 14) name theme-bg)
    (if (< (+ 8 nw 10) (- right 20))
        (txt-fit (+ 8 nw 10) 8 (- right 14 nw 10) (app-al-title a) theme-bg))))

(define (app-alert-hint a)
  (let ((exit (app-al-exit a)) (secs (int->str (max 0 (app-al-left a)))))
    (cond ((eq? exit 'time) (string-append secs " 秒后关闭  长按稍后提醒"))
          ((eq? exit 'both) (string-append "短按确认  " secs " 秒后关闭  长按稍后"))
          (else (string-append "短按确认  长按 " (int->str (app-al-snooze a)) " 分钟后再提醒")))))

(define (app-alert-render-footer a)
  (let ((y (- (gui-height) FTR-H)))
    (gui-rect 0 y (scr-w) FTR-H theme-card-hdr #t)
    (txt-fit 8 (+ y 3) (- (scr-w) 16) (app-alert-hint a) theme-text-sub)))

(define (app-alert-render a)
  (if (app-al-full a)
      (app-alert-run (app-al-owner a) (lambda () ((app-al-render a))))
      (app-alert-render-framed a)))

(define (app-alert-render-framed a)
  (if (gui-visible? 0 HDR-H) (app-alert-render-header a))
  (if (gui-visible? HDR-H (- (gui-height) HDR-H FTR-H))
      (app-alert-run (app-al-owner a) (lambda () ((app-al-render a)))))
  (if (gui-visible? (- (gui-height) FTR-H) FTR-H) (app-alert-render-footer a)))

;; Watched feeds: #(url-proc interval owner proc due), due on app-alert-clock
(define app-watches '())

(define (app-watch! url-proc interval proc)
  (set! app-watches (append app-watches (list (vector url-proc interval (app-alert-owner) proc 0)))))

(define (app-watch-url w) (app-alert-run (vector-ref w 2) (vector-ref w 0)))

(define (app-page-url? url)
  (let loop ((i 0))
    (cond ((>= i (vector-length app-urls)) #f)
          ((equal? (vector-ref app-urls i) url) #t)
          (else (loop (+ i 1))))))

;; A document of a watched feed no page shows: to its proc, as its app's code
(define (app-watch-deliver! url items)
  (for-each (lambda (w)
              (if (equal? (app-watch-url w) url)
                  (begin
                    (vector-set! w 4 (+ app-alert-clock (quotient (vector-ref w 1) 1000)))
                    (app-alert-run (vector-ref w 2) (lambda () ((vector-ref w 3) items))))))
            app-watches))

;; Every second: a due watched feed takes the stream while no fetch is in flight; the page on
;; screen takes it back right after when its data is due (app-take-document!, app-follow-page!),
;; also when its fetch keeps failing
(define (app-watch-step!)
  (if (and (pair? app-watches) (not app-loading) (> (app-npages) 0) (not (string=? (app-proxy) "")))
      (let loop ((l app-watches))
        (if (pair? l)
            (let* ((w (car l)) (url (app-watch-url w)))
              (if (and (>= app-alert-clock (vector-ref w 4)) (not (string=? url ""))
                       (not (equal? url (vector-ref app-urls app-page-index))))
                  (begin
                    (vector-set! w 4 (+ app-alert-clock (quotient (vector-ref w 1) 1000)))
                    (set! app-feed-url url)
                    (set! app-loading #t)
                    (json-feed-start url (vector-ref w 1) APP-KEYS APP-SELECTORS APP-POOL APP-VALUE-LEN 2))
                  (loop (cdr l))))))))


;;; =========================================================================
;;; Section: apps/lib/appweb.scm
;;; =========================================================================
;;; =========================================================================
;;; appweb.scm: the Scheme side of an app's own web page (apps/<id>/web.html).
;;;
;;; The board serves the page at /app (the first tab of its web page); the
;;; page's appCall(name, fields) posts to /api/app/call?fn=name with the fields
;;; form-encoded, and the firmware calls the app's hook
;;;
;;;   (app-web name body)  ->  a string sent back as the answer
;;;
;;; on the main loop, between frames. Answer JSON with (web-json value); read
;;; the fields with (web-field body "key"). The WASM simulator calls the same
;;; hook from its app page panel (minischeme-webrepl js/app_web.js).
;;; =========================================================================

;; Percent-decoding of a form value ("a+b%41" -> "a bA"): bytes in, bytes out
(define (web-hex-digit c)
  (let ((b (char->integer c)))
    (cond ((and (>= b 48) (<= b 57)) (- b 48))
          ((and (>= b 65) (<= b 70)) (- b 55))
          ((and (>= b 97) (<= b 102)) (- b 87))
          (else #f))))

(define (web-decode s)
  (let ((n (string-length s)))
    (let loop ((i 0) (acc '()))
      (if (>= i n)
          (list->string (reverse acc))
          (let ((c (string-ref s i)))
            (cond ((char=? c #\+) (loop (+ i 1) (cons #\space acc)))
                  ((and (char=? c #\%) (< (+ i 2) n)
                        (web-hex-digit (string-ref s (+ i 1))) (web-hex-digit (string-ref s (+ i 2))))
                   (loop (+ i 3) (cons (integer->char (+ (* 16 (web-hex-digit (string-ref s (+ i 1))))
                                                         (web-hex-digit (string-ref s (+ i 2)))))
                                       acc)))
                  (else (loop (+ i 1) (cons c acc)))))))))

;; The value of field key in a form body ("a=1&b=x%20y"), or #f
(define (web-field body key)
  (let ((parts (str-split (or body "") #\&)) (k (string-append key "=")))
    (let loop ((p parts))
      (cond ((null? p) #f)
            ((str-starts? (car p) k)
             (web-decode (substring (car p) (string-length k) (string-length (car p)))))
            ((string=? (car p) key) "")
            (else (loop (cdr p)))))))

;; A field as an integer, or default
(define (web-field-int body key default)
  (let ((v (web-field body key)))
    (or (and v (string->number v)) default)))

;; The double quote character
(define WEB-QUOTE #\")

;; JSON text of a value: strings, numbers, #t/#f, symbols (as strings),
;; vectors (arrays), alists with symbol or string keys (objects), other lists (arrays)
(define (web-json-string s)
  (let ((n (string-length s)) (hex "0123456789abcdef"))
    (let loop ((i 0) (acc (list WEB-QUOTE)))
      (if (>= i n)
          (list->string (reverse (cons WEB-QUOTE acc)))
          (let* ((c (string-ref s i)) (b (char->integer c)))
            (loop (+ i 1)
                  (cond ((= b 34) (cons WEB-QUOTE (cons #\\ acc)))
                        ((= b 92) (cons #\\ (cons #\\ acc)))
                        ((= b 10) (cons #\n (cons #\\ acc)))
                        ((= b 13) (cons #\r (cons #\\ acc)))
                        ((= b 9) (cons #\t (cons #\\ acc)))
                        ((< b 32) (append (list (string-ref hex (remainder b 16)) (string-ref hex (quotient b 16))
                                                #\0 #\0 #\u #\\)
                                          acc))
                        (else (cons c acc)))))))))

(define (web-alist? v)
  (and (pair? v)
       (let loop ((l v))
         (cond ((null? l) #t)
               ((and (pair? l) (pair? (car l)) (or (symbol? (caar l)) (string? (caar l)))) (loop (cdr l)))
               (else #f)))))

(define (web-join strs sep)
  (if (null? strs)
      ""
      (let loop ((l (cdr strs)) (acc (list (car strs))))
        (if (null? l)
            (apply string-append (reverse acc))
            (loop (cdr l) (cons (car l) (cons sep acc)))))))

(define (web-json v)
  (cond ((string? v) (web-json-string v))
        ((eq? v #t) "true")
        ((eq? v #f) "false")
        ((null? v) "[]")
        ((number? v) (number->string v))
        ((symbol? v) (web-json-string (symbol->string v)))
        ((vector? v) (string-append "[" (web-join (map web-json (vector->list v)) ",") "]"))
        ((web-alist? v)
         (string-append "{"
                        (web-join (map (lambda (p)
                                         (string-append (web-json-string (if (symbol? (car p))
                                                                             (symbol->string (car p))
                                                                             (car p)))
                                                        ":" (web-json (cdr p))))
                                       v)
                                  ",")
                        "}"))
        ((pair? v) (string-append "[" (web-join (map web-json v) ",") "]"))
        (else "null")))

;; {"success":false,"error":msg}: the page's appCall throws it
(define (web-error msg) (web-json (list (cons 'success #f) (cons 'error msg))))

;; {"success":true, ...fields}
(define (web-ok . fields) (web-json (cons (cons 'success #t) fields)))


;;; =========================================================================
;;; Section: apps/agenda/agenda.scm
;;; =========================================================================
;;; =========================================================================
;;; Agenda (日程提醒), 320x480 portrait, on the app framework (applib.scm). Offline: no proxy.
;;; Events are written on the board's web page (apps/agenda/web.html, app-web below) and kept
;;; in events.txt. An event is
;;;   a range      (从 年月日时分 到 年月日时分),
;;;   a date       (one whole day), or
;;;   a countdown  (one moment),
;;; in the solar or the lunar calendar (lunar-date: 1900..2100; a lunar 30th falls on the last day
;;; of a 29-day month, a solar day the month lacks is skipped: "L" means the last day), repeated or not:
;;;   every N days / weeks / months / years (months and years of the event's own calendar),
;;;   and/or only on given weekdays, days of the month (the last one too), months, years.
;;; Reminders are strong alerts (applib 6.6) while the app runs, alone or in a combined app
;;; (app-step-proc runs for every member), never a scheduled launch:
;;;   - reminder times (每天的提醒时刻): each such time of day inside an occurrence; without
;;;     any, a range or a countdown reminds at its start;
;;;   - advance reminders (提前提醒): "D/H:M" D days before the occurrence's day at H:M, or "M"
;;;     M minutes before its start, each with its own word (提前提醒词).
;;; A reminder whose minute passed while the app was not running is not shown later.
;;;   1 日程: every event's next occurrence   2 倒计时: the nearest countdowns
;;; File events.txt, one event per line:
;;;   id|on|title|kind|cal|start|end|times|advance|repeat
;;;   kind r d c; cal s (solar), l (lunar), L (lunar, its leap month); start and end "Y-M-D H:M"
;;;   in that calendar (end: ranges only); times "H:M,H:M"; advance "D/H:M~word;M~word";
;;;   repeat "N,U,W,MD,MO,Y" ("" none): N the interval (0: none) in U (d w m y), then sets with
;;;   "." between values: W weekdays 0..6 (0 Sunday), MD days 1..31 and 32 (the last day),
;;;   MO months 1..12, Y years.
;;; Days are counted from 1970-01-01, minutes from midnight of day 0 (local wall time).
;;; Every global name starts with "ag-".
;;; =========================================================================

(define AG-PATH "events.txt")          ; in the app's own folder
(define AG-MAX 40)                     ; events kept
(define AG-TITLE-MAX 60)               ; bytes
(define AG-WORD-MAX 40)
(define AG-SCAN-DAYS 3700)             ; how far an event's next occurrence is looked for (~10 years)
(define AG-AHEAD-DAYS 8)               ; reminders are worked out this far ahead
(define AG-ROW-H 54)
(define AG-WEEK (vector "日" "一" "二" "三" "四" "五" "六"))

(define ag-events '())                 ; event vectors, in file order
(define ag-rem '())                    ; #(minute event word start) the coming reminders, soonest first
(define ag-rem-at #f)                  ; the minute they were worked out
(define ag-last-min #f)                ; the last minute checked for reminders
(define ag-step-ms 0)
(define ag-drawn-min #f)               ; the minute the pages were drawn for

;; 1. Days and calendars ---------------------------------------------------------------------

;; Days since 1970-01-01 of a solar date
(define (ag-days y m d)
  (let* ((y (if (<= m 2) (- y 1) y))
         (era (quotient (if (>= y 0) y (- y 399)) 400))
         (yoe (- y (* era 400)))
         (doy (+ (quotient (+ (* 153 (+ m (if (> m 2) -3 9))) 2) 5) (- d 1)))
         (doe (+ (* yoe 365) (quotient yoe 4) (- (quotient yoe 100)) doy)))
    (+ (* era 146097) doe -719468)))

;; The solar date of day n: (y m d)
(define (ag-civil n)
  (let* ((z (+ n 719468))
         (era (quotient (if (>= z 0) z (- z 146096)) 146097))
         (doe (- z (* era 146097)))
         (yoe (quotient (- (+ (- doe (quotient doe 1460)) (quotient doe 36524)) (quotient doe 146096)) 365))
         (doy (- doe (- (+ (* 365 yoe) (quotient yoe 4)) (quotient yoe 100))))
         (mp (quotient (+ (* 5 doy) 2) 153))
         (d (+ (- doy (quotient (+ (* 153 mp) 2) 5)) 1))
         (m (if (< mp 10) (+ mp 3) (- mp 9))))
    (list (+ yoe (* era 400) (if (<= m 2) 1 0)) m d)))

(define (ag-wday n) (modulo (+ n 4) 7))          ; 0 Sunday

(define (ag-month-days y m)
  (- (if (= m 12) (ag-days (+ y 1) 1 1) (ag-days y (+ m 1) 1)) (ag-days y m 1)))

;; Now: minutes since day 0, or #f before the clock is set
(define (ag-now)
  (let ((t (time-local)))
    (and t (+ (* 1440 (ag-days (car t) (cadr t) (caddr t))) (* 60 (list-ref t 3)) (list-ref t 4)))))

;; The lunar date of day n: (year month day leap?), the year being the one its 正月 starts
;; (months 11 and 12 in January and February belong to the year before); #f outside 1900..2100
(define (ag-lunar-of n)
  (let* ((c (ag-civil n)) (l (lunar-date (car c) (cadr c) (caddr c))))
    (and l (list (if (and (>= (car l) 11) (<= (cadr c) 2)) (- (car c) 1) (car c)) (car l) (cadr l) (caddr l)))))

;; The day of lunar year ly, month lm (leap: its leap month), day ld; a 30th the month lacks
;; is its last day; #f when there is no such month
(define (ag-lunar-day ly lm ld leap)
  (let ((to (ag-days (+ ly 1) 3 31)))
    (let loop ((n (+ (ag-days ly 1 21) (* 29 (- lm 1)))) (seen #f))
      (if (> n to)
          seen
          (let ((l (ag-lunar-of n)))
            (cond ((not l) (loop (+ n 1) seen))
                  ((and (= (car l) ly) (= (cadr l) lm) (eq? (cadddr l) leap))
                   (cond ((= (caddr l) ld) n)
                         ((< (caddr l) ld) (loop (+ n (max 1 (- (min ld 29) (caddr l)))) n))   ; every month has a 29th
                         (else (loop (+ n 1) n))))
                  (seen seen)                    ; past the month: its last day
                  (else (loop (+ n 1) #f))))))))

;; Day n in the calendar c (#t lunar): #(year month day leap? last?), or #f
(define (ag-fields lunar n)
  (if lunar
      (let ((l (ag-lunar-of n)) (next (ag-lunar-of (+ n 1))))
        (and l (vector (car l) (cadr l) (caddr l) (cadddr l) (or (not next) (= (caddr next) 1)))))
      (let ((c (ag-civil n)))
        (vector (car c) (cadr c) (caddr c) #f (= (caddr c) (ag-month-days (car c) (cadr c)))))))

;; 2. Events -------------------------------------------------------------------------------------

;; #(id on title kind cal start end times advance repeat     <- the stored fields, as text
;;   base-day base-min dur time-list advance-list rule base-fields next)   <- worked out
(define (ag-id e) (vector-ref e 0))
(define (ag-on? e) (string=? (vector-ref e 1) "1"))
(define (ag-title e) (vector-ref e 2))
(define (ag-kind e) (vector-ref e 3))
(define (ag-cal e) (vector-ref e 4))
(define (ag-lunar? e) (not (string=? (ag-cal e) "s")))
(define (ag-bday e) (vector-ref e 10))           ; the first occurrence's day, #f: no such date
(define (ag-bmin e) (vector-ref e 11))           ; its minute of the day
(define (ag-dur e) (vector-ref e 12))            ; minutes from start to end
(define (ag-times e) (vector-ref e 13))          ; minutes of the day
(define (ag-advs e) (vector-ref e 14))           ; #(days minute-of-day minutes word): days #f = minutes before
(define (ag-rule e) (vector-ref e 15))           ; #(N U W MD MO Y), #f: no repeat
(define (ag-bf e) (vector-ref e 16))             ; #(year month day leap) of the first occurrence
(define (ag-next e) (vector-ref e 17))           ; the start minute of the current or next occurrence, #f

(define (ag-ints s sep) (filter (lambda (x) x) (map string->number (str-split s sep))))

;; "Y-M-D H:M" -> (y m d h mi), #f when malformed
(define (ag-parse-dt s)
  (let* ((parts (str-split s #\space)) (d (ag-ints (car parts) #\-))
         (t (if (and (pair? (cdr parts)) (not (str-empty? (cadr parts)))) (ag-ints (cadr parts) #\:) '(0 0))))
    (and (= (length d) 3) (= (length t) 2)
         (ag-in? (cadr d) 1 12) (ag-in? (caddr d) 1 31) (ag-in? (car t) 0 23) (ag-in? (cadr t) 0 59)
         (append d t))))

(define (ag-in? x a b) (and (>= x a) (<= x b)))

;; The day of a parsed date in the event's calendar, or #f
(define (ag-day-of cal p leap)
  (if (string=? cal "s")
      (and (<= (caddr p) (ag-month-days (car p) (cadr p))) (ag-days (car p) (cadr p) (caddr p)))
      (and (ag-in? (car p) 1900 2099) (<= (caddr p) 30) (ag-lunar-day (car p) (cadr p) (caddr p) leap))))

(define (ag-parse-rule s)
  (let ((f (str-split s #\,)))
    (and (= (length f) 6)
         (let ((v (vector (or (string->number (car f)) 0) (cadr f) (ag-ints (list-ref f 2) #\.)
                          (ag-ints (list-ref f 3) #\.) (ag-ints (list-ref f 4) #\.) (ag-ints (list-ref f 5) #\.))))
           (and (or (> (vector-ref v 0) 0) (pair? (vector-ref v 2)) (pair? (vector-ref v 3))
                    (pair? (vector-ref v 4)) (pair? (vector-ref v 5)))
                (member (vector-ref v 1) '("d" "w" "m" "y"))
                v)))))

;; "D/H:M~word;M~word" -> #(days minute-of-day minutes word) ...
(define (ag-parse-advs s)
  (filter (lambda (a) a)
          (map (lambda (item)
                 (let* ((p (str-split item #\~)) (off (car p)) (word (if (pair? (cdr p)) (cadr p) ""))
                        (slash (str-split off #\/)))
                   (if (pair? (cdr slash))
                       (let ((d (string->number (car slash))) (t (ag-ints (cadr slash) #\:)))
                         (and d (= (length t) 2) (vector d (+ (* 60 (car t)) (cadr t)) 0 word)))
                       (let ((m (string->number off))) (and m (> m 0) (vector #f 0 m word))))))
               (filter (lambda (x) (not (str-empty? x))) (str-split s #\;)))))

;; The fields worked out from the text ones; base-day #f when the date does not exist
(define (ag-compute! e)
  (let* ((cal (ag-cal e)) (kind (ag-kind e)) (leap (string=? cal "L"))
         (p (ag-parse-dt (vector-ref e 5)))
         (day (and p (ag-day-of cal p leap)))
         (bmin (if (and p (not (string=? kind "d"))) (+ (* 60 (list-ref p 3)) (list-ref p 4)) 0))
         (q (and (string=? kind "r") (ag-parse-dt (vector-ref e 6))))
         (eday (and q (ag-day-of cal q (and leap (= (cadr q) (cadr p))))))
         (dur (cond ((string=? kind "d") 1439)
                    ((and day eday) (max 0 (- (+ (* 1440 eday) (* 60 (list-ref q 3)) (list-ref q 4))
                                              (+ (* 1440 day) bmin))))
                    (else 0))))
    (vector-set! e 10 day)
    (vector-set! e 11 bmin)
    (vector-set! e 12 dur)
    (vector-set! e 13 (filter (lambda (x) x)
                              (map (lambda (t) (let ((hm (ag-ints t #\:)))
                                                 (and (= (length hm) 2) (+ (* 60 (car hm)) (cadr hm)))))
                                   (filter (lambda (x) (not (str-empty? x))) (str-split (vector-ref e 7) #\,)))))
    (vector-set! e 14 (ag-parse-advs (vector-ref e 8)))
    (vector-set! e 15 (and (not (str-empty? (vector-ref e 9))) (ag-parse-rule (vector-ref e 9))))
    (vector-set! e 16 (and p (vector (car p) (cadr p) (caddr p) leap)))
    (vector-set! e 17 #f)
    e))

;; 3. Repeats --------------------------------------------------------------------------------

;; Does an occurrence start on day n (n after the first one)?
(define (ag-repeat-on? e n)
  (let* ((r (ag-rule e)) (bf (ag-bf e)) (b (ag-bday e)) (f (ag-fields (ag-lunar? e) n)))
    (and f
         (let* ((N (vector-ref r 0)) (U (vector-ref r 1)) (W (vector-ref r 2)) (MD (vector-ref r 3))
                (MO (vector-ref r 4)) (Y (vector-ref r 5))
                (y (vector-ref f 0)) (m (vector-ref f 1)) (d (vector-ref f 2)) (wd (ag-wday n))
                (by (vector-ref bf 0)) (bm (vector-ref bf 1)) (bd (vector-ref bf 2))
                (day-free (or (pair? W) (pair? MD)))
                ;; a lunar 30th the month lacks: its last day (除夕 in a 29-day 腊月)
                (same-day (lambda () (or (= d bd) (and (ag-lunar? e) (vector-ref f 4) (> bd d)))))
                (same-month (lambda () (= m bm))))
           (and (or (null? W) (memv wd W))
                (or (null? MD) (memv d MD) (and (vector-ref f 4) (memv 32 MD)))
                (or (null? MO) (memv m MO))
                (or (null? Y) (memv y Y))
                ;; a lunar leap month only for an event of a leap month, unless days or weeks count
                (or (not (ag-lunar? e)) (and (> N 0) (member U '("d" "w")))
                    (eq? (vector-ref f 3) (vector-ref bf 3)))
                (cond ((= N 0) (and (or day-free (same-day))
                                    (or day-free (pair? MO) (null? Y) (same-month))))
                      ((string=? U "d") (= 0 (remainder (- n b) N)))
                      ((string=? U "w") (and (= 0 (remainder (- (quotient (+ n 3) 7) (quotient (+ b 3) 7)) N))
                                             (or (pair? W) (= wd (ag-wday b)))))
                      ((string=? U "m") (and (= 0 (remainder (- (+ (* 12 y) m) (+ (* 12 by) bm)) N))
                                             (or day-free (same-day))))
                      (else (and (= 0 (remainder (- y by) N))
                                 (or (pair? MO) (same-month))
                                 (or day-free (same-day))))))))))

;; The days from a to b (at most k) an occurrence of e starts on, ascending
(define (ag-occ-days e a b k)
  (let ((base (ag-bday e)))
    (cond ((not base) '())
          ((not (ag-rule e)) (if (and (>= base a) (<= base b)) (list base) '()))
          (else
           (let loop ((n (max a base)) (acc '()) (c 0))
             (cond ((or (> n b) (>= c k)) (reverse acc))
                   ((or (= n base) (ag-repeat-on? e n)) (loop (+ n 1) (cons n acc) (+ c 1)))
                   (else (loop (+ n 1) acc c))))))))

(define (ag-start e n) (+ (* 1440 n) (ag-bmin e)))

;; The start minute of the occurrence going on at now or the next one, or #f
(define (ag-find-next e now)
  (let ((today (quotient now 1440)) (back (+ 1 (quotient (ag-dur e) 1440))))
    (if (not (ag-rule e))
        (let ((s (ag-start e (ag-bday e)))) (and (>= (+ s (ag-dur e)) now) s))
    (let loop ((a (- today back)))
      (if (> a (+ today AG-SCAN-DAYS))
          #f
          (let* ((b (+ a 60)) (l (filter (lambda (n) (>= (+ (ag-start e n) (ag-dur e)) now)) (ag-occ-days e a b 40))))
            (if (pair? l) (ag-start e (car l)) (loop (+ b 1)))))))))

;; 4. Reminders ------------------------------------------------------------------------------

;; Insertion sort on a key
(define (ag-sort l key)
  (let ins-all ((l l) (out '()))
    (if (null? l)
        out
        (ins-all (cdr l)
                 (let ins ((x (car l)) (s out))
                   (cond ((null? s) (list x))
                         ((< (key x) (key (car s))) (cons x s))
                         (else (cons (car s) (ins x (cdr s))))))))))

(define (ag-adv-days e)
  (fold-left (lambda (m a) (max m (if (vector-ref a 0) (+ 1 (vector-ref a 0)) (+ 1 (quotient (vector-ref a 2) 1440)))))
             0 (ag-advs e)))

;; e's reminders from minute from to minute until: #(minute event word start)
(define (ag-reminders e from until)
  (let* ((today (quotient from 1440)) (dur (ag-dur e))
         (days (ag-occ-days e (- today 1 (quotient dur 1440)) (+ (quotient until 1440) (ag-adv-days e)) 80))
         (out '()))
    (define (add! m word s) (if (and (>= m from) (<= m until)) (set! out (cons (vector m e word s) out))))
    (for-each
     (lambda (n)
       (let* ((s (ag-start e n)) (end (+ s dur)))
         (if (pair? (ag-times e))
             (let day ((k (quotient s 1440)))
               (if (<= k (quotient end 1440))
                   (begin
                     (for-each (lambda (t) (let ((m (+ (* 1440 k) t))) (if (and (>= m s) (<= m end)) (add! m "" s))))
                               (ag-times e))
                     (day (+ k 1)))))
             (if (not (string=? (ag-kind e) "d")) (add! s "" s)))
         (for-each (lambda (a)
                     (add! (if (vector-ref a 0) (+ (* 1440 (- n (vector-ref a 0))) (vector-ref a 1)) (- s (vector-ref a 2)))
                           (vector-ref a 3) s))
                   (ag-advs e))))
     days)
    out))

;; Every event's next occurrence and the coming reminders, worked out again
(define (ag-refresh! now)
  (set! ag-rem-at now)
  (set! ag-rem '())
  (for-each (lambda (e)
              (vector-set! e 17 (and (ag-bday e) (ag-find-next e now)))
              (if (and (ag-on? e) (ag-bday e))
                  (set! ag-rem (append (ag-reminders e now (+ now (* 1440 AG-AHEAD-DAYS))) ag-rem))))
            ag-events)
  (set! ag-rem (ag-sort ag-rem (lambda (r) (vector-ref r 0))))
  (app-invalidate-all))

;; Once a second (app-step-proc): a new minute raises its reminders; the list is worked out
;; again every hour and on a new day
(define (ag-minute!)
  (let ((now (ag-now)))
    (if (and now (not (equal? now ag-last-min)))
        (begin
          (if (or (not ag-rem-at) (>= (- now ag-rem-at) 60) (< now ag-rem-at)
                  (not (= (quotient now 1440) (quotient ag-rem-at 1440))))
              (ag-refresh! now))
          (let ((since (if (and ag-last-min (< ag-last-min now) (<= (- now ag-last-min) 2)) ag-last-min (- now 1))))
            (for-each (lambda (r) (if (and (> (vector-ref r 0) since) (<= (vector-ref r 0) now)) (ag-fire! r))) ag-rem))
          (set! ag-last-min now)))))

(set! app-step-proc
      (lambda ()
        (let ((ms (time-ms)))
          (if (or (< ms ag-step-ms) (>= (- ms ag-step-ms) 1000))
              (begin (set! ag-step-ms ms) (ag-minute!))))
        #f))

;; 5. Text -------------------------------------------------------------------------------------

(define (ag-hm m) (string-append (pad2 (quotient (modulo m 1440) 60)) ":" (pad2 (modulo m 60))))

;; "10月28日 周三", with the year when it is not this one
(define (ag-date-text n)
  (let ((c (ag-civil n)) (now (ag-now)))
    (string-append (if (and now (= (car c) (car (ag-civil (quotient now 1440))))) "" (string-append (int->str (car c)) "年"))
                   (int->str (cadr c)) "月" (int->str (caddr c)) "日 周" (vector-ref AG-WEEK (ag-wday n)))))

(define (ag-lunar-text n)
  (let ((c (ag-civil n))) (or (lunar-date-string (car c) (cadr c) (caddr c)) "")))

;; When an occurrence starting at minute s is
(define (ag-when-text e s)
  (let ((n (quotient s 1440)) (end (+ s (ag-dur e))))
    (cond ((string=? (ag-kind e) "d") (ag-date-text n))
          ((string=? (ag-kind e) "c") (string-append (ag-date-text n) " " (ag-hm s)))
          ((= (quotient end 1440) n) (string-append (ag-date-text n) " " (ag-hm s) "-" (ag-hm end)))
          (else (string-append (ag-date-text n) " " (ag-hm s) " 至 " (ag-date-text (quotient end 1440)) " " (ag-hm end))))))

;; "3天后", "明天 08:00", "进行中", "已结束"
(define (ag-left-text e s now)
  (let* ((end (+ s (ag-dur e))) (dd (- (quotient s 1440) (quotient now 1440))) (time? (not (string=? (ag-kind e) "d"))))
    (cond ((> s now)
           (cond ((= dd 0) (if time? (string-append "今天 " (ag-hm s)) "今天"))
                 ((= dd 1) (if time? (string-append "明天 " (ag-hm s)) "明天"))
                 ((= dd 2) "后天")
                 (else (string-append (int->str dd) "天后"))))
          ((and (<= now end) (string=? (ag-kind e) "d")) "今天")
          ((<= now end) (if (string=? (ag-kind e) "c") "到了" "进行中"))
          (else "已结束"))))

;; "还有 2天3小时5分", or how far past
(define (ag-span-text mins)
  (let ((d (quotient mins 1440)) (h (quotient (modulo mins 1440) 60)) (m (modulo mins 60)))
    (string-append (if (> d 0) (string-append (int->str d) "天") "")
                   (if (> h 0) (string-append (int->str h) "小时") "")
                   (if (or (> m 0) (and (= d 0) (= h 0))) (string-append (int->str m) "分") ""))))

(define (ag-unit-text u lunar)
  (cond ((string=? u "d") "天") ((string=? u "w") "周") ((string=? u "m") (if lunar "个农历月" "个月"))
        (else (if lunar "农历年" "年"))))

;; "每年", "每2周 周一三五", "每月最后一天", "每年 3、6月" ...
(define (ag-rule-text e)
  (let ((r (ag-rule e)) (lunar (ag-lunar? e)))
    (if (not r)
        ""
        (let* ((N (vector-ref r 0)) (U (vector-ref r 1)) (W (vector-ref r 2)) (MD (vector-ref r 3))
               (MO (vector-ref r 4)) (Y (vector-ref r 5))
               (join (lambda (l f sep) (fold-left (lambda (a x) (if (str-empty? a) (f x) (string-append a sep (f x)))) "" l)))
               (parts (list
                       (cond ((> N 1) (string-append "每" (int->str N) (ag-unit-text U lunar)))
                             ((= N 1) (string-append "每" (cond ((string=? U "m") (if lunar "农历月" "月"))
                                                                ((string=? U "y") (if lunar "农历年" "年"))
                                                                (else (ag-unit-text U lunar)))))
                             ((pair? W) "每")
                             ((pair? MD) (if (pair? MO) "" (if lunar "每农历月" "每月")))
                             ((pair? MO) (if lunar "每农历年" "每年"))
                             (else ""))
                       (if (pair? W) (string-append "周" (join W (lambda (w) (vector-ref AG-WEEK w)) "")) "")
                       (join MD (lambda (d) (if (= d 32) "最后一天" (string-append (int->str d) "日"))) "、")
                       (if (pair? MO) (string-append (join MO int->str "、") "月") "")
                       (if (pair? Y) (string-append (join Y int->str "、") "年") ""))))
          ;; "每" joins what follows it; the other parts are apart
          (fold-left (lambda (a p) (cond ((str-empty? p) a) ((or (str-empty? a) (string=? a "每") (string=? a "每月") (string=? a "每农历月")) (string-append a p))
                                         (else (string-append a " " p))))
                     "" parts)))))

(define (ag-kind-text e)
  (cond ((string=? (ag-kind e) "r") "日程") ((string=? (ag-kind e) "d") "日期") (else "倒计时")))

;; 6. Storage --------------------------------------------------------------------------------

(define (ag-clean s n)
  (let ((flat (list->string (map (lambda (c) (if (member c (list #\| #\newline #\return #\~ #\;)) #\space c))
                                 (string->list (or s ""))))))
    (if (<= (string-length flat) n)
        flat
        (let back ((k n))
          (if (and (> k 0) (= (quotient (char->integer (string-ref flat k)) 64) 2)) (back (- k 1)) (substring flat 0 k))))))

(define (ag-line e)
  (web-join (map (lambda (i) (let ((v (vector-ref e i))) (if (number? v) (int->str v) v))) '(0 1 2 3 4 5 6 7 8 9)) "|"))

(define (ag-parse line)
  (let ((f (str-split line #\|)))
    (and (= (length f) 10) (string->number (car f))
         (ag-compute! (list->vector (append (cons (string->number (car f)) (cdr f)) (list #f 0 0 '() '() #f #f #f)))))))

(define (ag-load!)
  (let ((text (and (fs-exists? AG-PATH) (fs-read AG-PATH))))
    (set! ag-events (if (string? text)
                        (filter (lambda (e) e) (map ag-parse (filter (lambda (l) (not (str-empty? l))) (str-split text #\newline))))
                        '()))))

(define (ag-save!)
  (fs-write AG-PATH (fold-left (lambda (acc e) (string-append acc (ag-line e) (list->string (list #\newline)))) "" ag-events))
  (let ((now (ag-now))) (if now (ag-refresh! now) (app-invalidate-all))))

(define (ag-next-id) (+ 1 (fold-left (lambda (m e) (max m (ag-id e))) 0 ag-events)))

(define (ag-find id)
  (let loop ((l ag-events)) (cond ((null? l) #f) ((= (ag-id (car l)) id) (car l)) (else (loop (cdr l))))))

;; An event from the web page's fields (id 0: a new one); an error text when it cannot be
(define (ag-from-fields body id)
  (let* ((field (lambda (k n) (ag-clean (or (web-field body k) "") n)))
         (kind (field "kind" 1)) (cal (field "cal" 1))
         (adv (list->string (map (lambda (c) (if (member c (list #\| #\newline #\return)) #\space c))
                                 (string->list (or (web-field body "advance") "")))))
         (e (vector id (if (equal? (web-field body "on") "0") "0" "1")
                    (let ((t (field "title" AG-TITLE-MAX))) (if (str-empty? t) "日程" t))
                    kind cal (field "start" 20) (field "end" 20) (field "times" 200) (ag-clean-adv adv) (field "repeat" 300)
                    #f 0 0 '() '() #f #f #f)))
    (cond ((not (member kind '("r" "d" "c"))) "kind: r, d or c")
          ((not (member cal '("s" "l" "L"))) "cal: s, l or L")
          ((not (ag-parse-dt (vector-ref e 5))) "开始时间格式不对")
          (else
           (ag-compute! e)
           (cond ((not (ag-bday e)) "没有这一天（农历：这一年没有这个月或闰月）")
                 ((and (string=? kind "r") (not (ag-parse-dt (vector-ref e 6)))) "结束时间格式不对")
                 ((and (string=? kind "r") (= (ag-dur e) 0)) "结束要晚于开始")
                 ((and (not (str-empty? (vector-ref e 9))) (not (ag-rule e))) "重复规则不对")
                 (else e))))))

;; Advance items keep their words up to AG-WORD-MAX bytes each
(define (ag-clean-adv s)
  (web-join (map (lambda (item)
                   (let ((p (str-split item #\~)))
                     (if (pair? (cdr p)) (string-append (car p) "~" (ag-clean (cadr p) AG-WORD-MAX)) (car p))))
                 (filter (lambda (x) (not (str-empty? x))) (str-split s #\;)))
            ";"))

;; 7. The screen ------------------------------------------------------------------------------

;; Enabled events with an occurrence to come, soonest first, then the others
(define (ag-shown)
  (let ((on (filter ag-on? ag-events)))
    (append (ag-sort (filter ag-next on) ag-next) (filter (lambda (e) (not (ag-next e))) on))))

(define (ag-hint)
  (if (wifi-connected?)
      (string-append "在设备网页的应用选项卡里添加：http://" (wifi-ip) "/")
      "连接 WiFi 后，在设备网页的应用选项卡里添加日程"))

(define (ag-render-list items)
  (let ((now (ag-now)) (l (ag-shown)))
    (cond ((not now) (txt 14 70 "等待时钟同步…" theme-text-muted))
          ((null? l)
           (txt 14 70 "暂无日程" theme-text-muted)
           (txt-wrap 14 100 (- (scr-w) 28) 80 (ag-hint) theme-text-sub))
          (else
           (let loop ((l l) (y (+ (body-top) 2)))
             (if (and (pair? l) (<= (+ y AG-ROW-H) (+ (body-bottom) 4)))
                 (let* ((e (car l)) (s (ag-next e)) (left (if s (ag-left-text e s now) "已结束"))
                        (lw (txt-w left)) (soon (and s (<= (- s now) 1440))))
                   (if (gui-visible? y AG-ROW-H)
                       (begin
                         (txt-fit 10 y (- 300 lw 10) (ag-title e) theme-text-main)
                         (txt-right 310 y left (cond ((not s) theme-text-muted) ((<= s now) theme-success)
                                                     (soon theme-warning) (else theme-accent)))
                         (txt-fit 10 (+ y 24) 300
                                  (if s
                                      (string-append (ag-when-text e s)
                                                     (if (ag-lunar? e) (string-append " " (ag-lunar-text (quotient s 1440))) "")
                                                     (let ((r (ag-rule-text e))) (if (str-empty? r) "" (string-append " · " r))))
                                      (ag-rule-text e))
                                  theme-text-muted)
                         (gui-line 10 (+ y 49) 310 (+ y 49) theme-divider)))
                   (loop (cdr l) (+ y AG-ROW-H)))))))))

;; The nearest countdowns (events of kind c; without any, the nearest events)
(define (ag-countdowns)
  (let* ((l (filter ag-next (ag-shown))) (c (filter (lambda (e) (string=? (ag-kind e) "c")) l)))
    (if (pair? c) c l)))

(define (ag-render-count items)
  (let ((now (ag-now)) (l (ag-countdowns)))
    (cond ((not now) (txt 14 70 "等待时钟同步…" theme-text-muted))
          ((null? l) (txt 14 70 "暂无倒计时" theme-text-muted)
                     (txt-wrap 14 100 (- (scr-w) 28) 80 (ag-hint) theme-text-sub))
          (else
           (let* ((e (car l)) (s (ag-next e)) (left (- s now)) (y (+ (body-top) 10))
                  (title (ag-title e)))
             (if (<= (* 2 (txt-w title)) 300)
                 (gui-text-scaled (- 160 (txt-w title)) y title theme-accent 2 F-TEXT)
                 (txt-center 160 (+ y 8) title theme-accent))
             (cond
               ((and (> left 0) (< left 1440))                    ; under a day: hours and minutes, large
                (let ((hm (string-append (pad2 (quotient left 60)) ":" (pad2 (modulo left 60)))))
                  (txt-center 160 (+ y 48) "还有（时:分）" theme-text-muted)
                  (gui-text-scaled (- 160 (big-w hm)) (+ y 80) hm theme-warning 2 F-BIG)))
               ((> left 0)
                 (let* ((days (int->str (quotient left 1440))) (dw (* 2 (big-w days))) (x (- 160 (quotient (+ dw 36) 2))))
                   (txt-center 160 (+ y 48) "还有" theme-text-muted)
                   (gui-text-scaled x (+ y 72) days theme-text-main 2 F-BIG)
                   (gui-text-scaled (+ x dw 4) (+ y 104) "天" theme-text-main 2 F-TEXT)
                   (let ((hm (string-append (pad2 (quotient (modulo left 1440) 60)) ":" (pad2 (modulo left 60)))))
                     (big (- 160 (quotient (big-w hm) 2)) (+ y 146) hm theme-text-sub))))
               (else (gui-text-scaled (- 160 (txt-w (ag-left-text e s now))) (+ y 90) (ag-left-text e s now) theme-success 2 F-TEXT)))
             (txt-center 160 (+ y 192) (ag-when-text e s) theme-text-sub)
             (if (ag-lunar? e) (txt-center 160 (+ y 214) (ag-lunar-text (quotient s 1440)) theme-text-muted))
             (let loop ((l (cdr l)) (yy (+ y 248)) (i 0))
               (if (and (pair? l) (< i 4) (<= (+ yy 20) (body-bottom)))
                   (let* ((o (car l)) (os (ag-next o)) (t (ag-left-text o os now)))
                     (if (= i 0) (gui-line 10 (- yy 8) 310 (- yy 8) theme-divider))
                     (txt-fit 10 yy (- 290 (txt-w t)) (ag-title o) theme-text-main)
                     (txt-right 310 yy t theme-accent)
                     (loop (cdr l) (+ yy 26) (+ i 1))))))))))

;; A reminder's alert body
(define (ag-render-alert r)
  (let* ((e (vector-ref r 1)) (word (vector-ref r 2)) (s (vector-ref r 3)) (now (or (ag-now) (vector-ref r 0)))
         (y (+ (body-top) 10)) (title (ag-title e)))
    (if (<= (* 2 (txt-w title)) 300)
        (gui-text-scaled 10 y title theme-accent 2 F-TEXT)
        (txt-wrap 10 y 300 40 title theme-accent))
    (txt 10 (+ y 46) (ag-kind-text e) theme-text-muted)
    (txt-wrap 10 (+ y 72) 300 44 (ag-when-text e s) theme-text-main)
    (if (ag-lunar? e) (txt 10 (+ y 120) (ag-lunar-text (quotient s 1440)) theme-text-sub))
    (let ((rel (cond ((> s now) (string-append "还有 " (ag-span-text (- s now))))
                     ((<= now (+ s (ag-dur e))) (ag-left-text e s now))
                     (else "已结束"))))
      (gui-text-scaled 10 (+ y 150) rel theme-warning 2 F-TEXT))
    (if (not (str-empty? word)) (txt-wrap 10 (+ y 200) 300 80 word theme-text-main))))

(define (ag-fire! r)
  (let ((e (vector-ref r 1)) (word (vector-ref r 2)))
    (app-alert! (string-append "a" (int->str (ag-id e)) "-" (int->str (vector-ref r 0)))
                (if (str-empty? word) "日程提醒" word)
                (lambda () (ag-render-alert r))
                (list (cons 'priority 6) (cons 'exit 'both) (cons 'seconds 60)))))

;; The pages follow the minute (countdowns, "今天" ...)
(set! app-tick-proc
      (lambda (tick)
        (let ((now (ag-now)))
          (if (and now (not (equal? now ag-drawn-min)))
              (begin (set! ag-drawn-min now) (gui-invalidate 0 (body-top) (scr-w) (- (body-bottom) (body-top))))))))

(set! app-subtitle-proc
      (lambda (items)
        (let* ((now (ag-now))
               (n (if now (length (filter (lambda (e) (let ((s (ag-next e))) (and s (<= (quotient s 1440) (quotient now 1440)))))
                                          (filter ag-on? ag-events)))
                      0)))
          (if (> n 0) (string-append "今天 " (int->str n)) #f))))

;; 8. The web page's calls ----------------------------------------------------------------------

(define (ag->alist e now)
  (let ((s (ag-next e)))
    (list (cons 'id (ag-id e)) (cons 'on (ag-on? e)) (cons 'title (ag-title e)) (cons 'kind (ag-kind e))
          (cons 'cal (ag-cal e)) (cons 'start (vector-ref e 5)) (cons 'end (vector-ref e 6))
          (cons 'times (vector-ref e 7)) (cons 'advance (vector-ref e 8)) (cons 'repeat (vector-ref e 9))
          (cons 'rule (ag-rule-text e))
          (cons 'next (if s (ag-when-text e s) ""))
          (cons 'lunar (if (and s (ag-lunar? e)) (ag-lunar-text (quotient s 1440)) ""))
          (cons 'left (if (and s now) (ag-left-text e s now) "已结束")))))

(define (ag-answer)
  (let ((now (ag-now)))
    (web-ok (cons 'events (map (lambda (e) (ag->alist e now)) ag-events))
            (cons 'clock (if now (string-append (ag-date-text (quotient now 1440)) " " (ag-hm now)) "")))))

;; The next occurrences and reminders of an event not saved yet
(define (ag-preview e)
  (let* ((now (or (ag-now) (* 1440 (ag-bday e)))) (today (quotient now 1440))
         (occ (filter (lambda (n) (>= (+ (ag-start e n) (ag-dur e)) now))
                      (ag-occ-days e (- today 1 (quotient (ag-dur e) 1440)) (+ today AG-SCAN-DAYS) 6)))
         (rem (ag-sort (ag-reminders e now (+ now (* 1440 400))) (lambda (r) (vector-ref r 0)))))
    (web-ok (cons 'first (string-append (ag-when-text e (ag-start e (ag-bday e)))
                                        (if (ag-lunar? e) (string-append " " (ag-lunar-text (ag-bday e))) "")))
            (cons 'occurrences (map (lambda (n) (string-append (ag-when-text e (ag-start e n))
                                                               (if (ag-lunar? e) (string-append " " (ag-lunar-text n)) "")))
                                    occ))
            (cons 'reminders (map (lambda (r) (string-append (ag-date-text (quotient (vector-ref r 0) 1440)) " "
                                                             (ag-hm (vector-ref r 0))
                                                             (if (str-empty? (vector-ref r 2)) "" (string-append "  " (vector-ref r 2)))))
                                  (if (> (length rem) 10) (take rem 10) rem)))
            (cons 'rule (ag-rule-text e)))))

(define (app-web name body)
  (cond
    ((string=? name "list") (ag-answer))
    ((or (string=? name "save") (string=? name "preview"))
     (let* ((id (web-field-int body "id" 0)) (e (ag-from-fields body (if (> id 0) id (ag-next-id)))))
       (cond ((string? e) (web-error e))
             ((string=? name "preview") (ag-preview e))
             ((ag-find id) (set! ag-events (map (lambda (x) (if (= (ag-id x) id) e x)) ag-events)) (ag-save!) (ag-answer))
             ((>= (length ag-events) AG-MAX) (web-error (string-append "最多 " (int->str AG-MAX) " 个日程")))
             (else (set! ag-events (append ag-events (list e))) (ag-save!) (ag-answer)))))
    ((string=? name "toggle")
     (let ((e (ag-find (web-field-int body "id" -1))))
       (if e (begin (vector-set! e 1 (if (ag-on? e) "0" "1")) (ag-save!)))
       (ag-answer)))
    ((string=? name "delete")
     (let ((id (web-field-int body "id" -1)))
       (set! ag-events (filter (lambda (e) (not (= (ag-id e) id))) ag-events))
       (ag-save!)
       (ag-answer)))
    ((string=? name "lunar")                      ; a solar date's lunar text
     (let ((y (web-field-int body "y" 0)) (m (web-field-int body "m" 0)) (d (web-field-int body "d" 0)))
       (web-ok (cons 'lunar (or (and (> y 0) (lunar-date-string y m d)) "")))))
    (else (web-error (string-append "unknown call: " name)))))

;; 9. Start ------------------------------------------------------------------------------------

(ag-load!)
(let ((now (ag-now))) (if now (ag-refresh! now)))

(app-define! "日程提醒"
  (list (app-local-page "日程" ag-render-list)
        (app-local-page "倒计时" ag-render-count)))

