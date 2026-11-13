;;; =========================================================================
;;; Bluetooth thermometer (蓝牙温湿度), on the app framework (applib.scm).
;;; Reads a Xiaomi LYWSD03MMC over Bluetooth LE (the `ble` extension): the
;;; characteristic ebe0ccc1 notifies 5 bytes, temperature (0.01 C, signed, low
;;; byte first), humidity (%), battery (mV, low byte first).
;;; The layout follows the screen width (172 to 320 px).
;;;
;;; One reading every `interval` minutes: scan (unless `address` is set),
;;; connect, discover, subscribe, take the first notification, disconnect.
;;; interval = 0 keeps the link and shows every notification.
;;; =========================================================================

(define TH-NAME "LYWSD03")               ; the scan filter: advertised name prefix
(define TH-CHAR "ebe0ccc1")              ; temperature / humidity / battery
(define TH-STEP-TIMEOUT 20000)           ; a step (scan, connect, discover, first value) may take this long
(define TH-SCAN-S 15)                    ; seconds of scanning for it
(define TH-RETRY 15000)                  ; after a failure
(define TH-HISTORY 48)

(define th-state 'start)                 ; start scan connect discover wait live sleep off
(define th-addr "")
(define th-conn #f)
(define th-deadline 0)                   ; (time-ms) when the state gives up, or wakes (sleep)
(define th-step-ms 0)
(define th-note "")                      ; why the last attempt failed
(define th-temp #f)                      ; 0.01 C
(define th-hum #f)
(define th-mv #f)
(define th-at "")                        ; clock time of the reading
(define th-temps '())                    ; newest first, 0.1 C
(define th-shown "")                     ; the status line on screen

(define (th-ble?) (and (api-has? "ble-status") (cdr (assq 'enabled (ble-status)))))
(define (th-interval-ms)
  (* 60000 (clamp (or (string->fixed (app-config "interval" "5") 0) 5) 0 120)))

(define (th-go! state ms)
  (set! th-state state)
  (set! th-deadline (+ (time-ms) ms))
  (app-invalidate-body))

(define (th-fail! why)
  (set! th-note why)
  (if th-conn (ble-disconnect th-conn) (ble-disconnect 0))
  (set! th-conn #f)
  (th-go! 'sleep TH-RETRY))

(define (th-connect! addr)
  (set! th-addr addr)
  (if (ble-connect addr)
      (th-go! 'connect TH-STEP-TIMEOUT)
      (th-fail! "蓝牙忙")))

(define (th-begin!)
  (let ((addr (app-config "address" "")))
    (cond ((not (th-ble?)) (set! th-state 'off) (app-invalidate-body))
          ((not (str-empty? addr)) (th-connect! addr))
          ((not (str-empty? th-addr)) (th-connect! th-addr))
          ;; it advertises every couple of seconds and the radio is shared with WiFi: 8 s missed it
          ((ble-scan-start TH-SCAN-S #t (string-append "name:" TH-NAME))
           (th-go! 'scan (+ (* TH-SCAN-S 1000) 5000)))
          (else (th-fail! "无法扫描")))))

;; The strongest device of the scan: (address type rssi name connectable? adv)
(define (th-strongest)
  (let loop ((ds (ble-scan-results)) (best #f))
    (cond ((null? ds) (and best (car best)))
          ((or (not best) (> (caddr (car ds)) (caddr best))) (loop (cdr ds) (car ds)))
          (else (loop (cdr ds) best)))))

;; (uuid handle properties) of the characteristic whose UUID starts with prefix
(define (th-find services prefix)
  (let ((n (string-length prefix)))
    (let loop ((ss services))
      (if (null? ss)
          #f
          (let inner ((cs (cdr (car ss))))
            (cond ((null? cs) (loop (cdr ss)))
                  ((and (>= (string-length (car (car cs))) n) (string=? (substring (car (car cs)) 0 n) prefix))
                   (car cs))
                  (else (inner (cdr cs)))))))))

(define (th-reading! hex)
  (let ((b (ble-hex->bytes hex)))
    (if (>= (length b) 5)
        (let* ((raw (+ (car b) (* 256 (cadr b))))
               (t (if (>= raw 32768) (- raw 65536) raw)))
          (set! th-temp t)
          (set! th-hum (caddr b))
          (set! th-mv (+ (cadddr b) (* 256 (list-ref b 4))))
          (set! th-at app-time)
          (set! th-note "")
          #t)
        #f)))

(define (th-keep! t)
  (set! th-temps (cons (quotient (+ t (if (< t 0) -5 5)) 10) th-temps))
  (if (> (length th-temps) TH-HISTORY)
      (set! th-temps (reverse (cdr (reverse th-temps))))))

(define (app-ble-event ev)
  (let ((kind (car ev)))
    (cond ((eq? kind 'scan-done)
           (if (eq? th-state 'scan)
               (let ((addr (th-strongest)))
                 (if addr (th-connect! addr) (th-fail! "没有找到温湿度计")))))
          ((eq? kind 'connected)
           (if (and (eq? th-state 'connect) (eq? (cadddr ev) 'central))
               (begin
                 (set! th-conn (cadr ev))
                 (if (ble-discover th-conn) (th-go! 'discover TH-STEP-TIMEOUT) (th-fail! "无法读取服务")))))
          ((eq? kind 'discovered)
           (if (and (eq? th-state 'discover) (equal? (cadr ev) th-conn))
               (let ((c (and (caddr ev) (th-find (ble-services th-conn) TH-CHAR))))
                 (if (and c (ble-subscribe th-conn (cadr c)))
                     (th-go! 'wait TH-STEP-TIMEOUT)
                     (th-fail! "不是米家温湿度计")))))
          ((eq? kind 'notify)
           (if (and (equal? (cadr ev) th-conn) (memq th-state '(wait live)) (th-reading! (cadddr ev)))
               (if (= (th-interval-ms) 0)
                   (begin
                     (if (eq? th-state 'wait) (th-keep! th-temp))
                     (th-go! 'live 60000))
                   (begin
                     (th-keep! th-temp)
                     (ble-disconnect th-conn)
                     (set! th-conn #f)
                     (th-go! 'sleep (th-interval-ms))))))
          ((eq? kind 'disconnected)
           (cond ((and (cadr ev) (equal? (cadr ev) th-conn))       ; our link went away
                  (set! th-conn #f)
                  (if (not (eq? th-state 'sleep))
                      (begin (set! th-note "连接断开") (th-go! 'sleep TH-RETRY))))
                 ((and (not (cadr ev)) (eq? th-state 'connect))    ; the attempt never got a link
                  (set! th-note "连接失败")
                  (th-go! 'sleep TH-RETRY)))))))

;; Once a second: timeouts, the next reading, one history point a minute while live
(define th-live-min "")
(define (th-tick!)
  (let ((now (time-ms)))
    (cond ((eq? th-state 'start) (th-begin!))
          ((eq? th-state 'off) (if (th-ble?) (th-begin!)))
          ((eq? th-state 'sleep) (if (>= now th-deadline) (th-begin!)))
          ((eq? th-state 'live)
           (if (>= now th-deadline) (th-fail! "没有收到数据"))
           (if (and th-temp (not (equal? th-live-min app-time)))
               (begin (set! th-live-min app-time) (th-keep! th-temp) (app-invalidate-body))))
          ((>= now th-deadline)
           (th-fail! (cond ((eq? th-state 'scan) "扫描超时")
                           ((eq? th-state 'connect) "连接超时")
                           (else "读取超时")))))
    (let ((s (th-status)))                 ; the countdown in the status line
      (if (not (equal? s th-shown)) (app-invalidate-body)))))

(set! app-step-proc
      (lambda ()
        (let ((ms (time-ms)))
          (if (or (< ms th-step-ms) (>= (- ms th-step-ms) 1000))
              (begin (set! th-step-ms ms) (th-tick!))))
        #f))

;; Text ---------------------------------------------------------------------------------------

(define (th-status)
  (cond ((eq? th-state 'off) "蓝牙未开启")
        ((eq? th-state 'scan) "正在搜索…")
        ((eq? th-state 'connect) "正在连接…")
        ((eq? th-state 'discover) "读取服务…")
        ((eq? th-state 'wait) "等待数据…")
        ((eq? th-state 'live) "实时")
        ((eq? th-state 'sleep)
         (let* ((ms (max 0 (- th-deadline (time-ms))))
                (left (if (< ms 60000)             ; seconds in steps of 5: the line is redrawn when it changes
                          (string-append (int->str (* 5 (quotient (+ ms 4999) 5000))) " 秒后")
                          (string-append (int->str (quotient (+ ms 59999) 60000)) " 分钟后"))))
           (string-append (if (str-empty? th-note) "" (string-append th-note "，"))
                          left (if (str-empty? th-note) "更新" "重试"))))
        (else "")))

(define (th-battery-pct mv) (clamp (quotient (- mv 2100) 10) 0 100))

;; The page: sizes from the screen ------------------------------------------------------------

(define (th-big-center cx y num unit color)
  (let ((w (+ (big-w num) 2 (txt-w unit))))
    (big-unit (- cx (quotient w 2)) y num unit color)))

(define (th-render items)
  (let* ((w (scr-w)) (cx (quotient w 2)) (m (if (< w 240) 6 12))
         (y (body-top)) (bottom (body-bottom))
         (status (th-status)))
    (set! th-shown status)
    (cond ((eq? th-state 'off)
           (txt-wrap m (+ y 8) (- w m m) 120
                     "蓝牙未开启。在 config.ini 的 [bluetooth] 段设置 bt_enabled = 1 后重启。" theme-text-muted))
          ((not th-temp)
           (txt-center cx (+ y 40) "蓝牙温湿度计" theme-accent)
           (txt-wrap m (+ y 70) (- w m m) 80 status theme-text-muted))
          (else
           (let* ((t10 (quotient (+ th-temp (if (< th-temp 0) -5 5)) 10))
                  (two (>= w 280))                              ; wide: temperature and humidity side by side
                  (tx (if two (quotient w 4) cx))
                  (hy (if two y (+ y 62)))
                  (hx (if two (* 3 (quotient w 4)) cx))
                  (by (+ hy 62)))
             (txt-center tx y "温度" theme-text-muted)
             (th-big-center tx (+ y 20) (fixed->str t10 1) "°C"
                            (cond ((>= t10 300) theme-danger) ((< t10 160) theme-accent) (else theme-text-main)))
             (txt-center hx hy "湿度" theme-text-muted)
             (th-big-center hx (+ hy 20) (int->str th-hum) "%" theme-success)
             (gui-line m by (- w m) by theme-divider)
             (let ((pct (th-battery-pct th-mv)))
               (txt m (+ by 6) "电量" theme-text-muted)
               (txt-right (- w m) (+ by 6) (string-append (int->str pct) "%")
                          (if (< pct 15) theme-danger theme-text-sub)))
             (txt m (+ by 28) "更新" theme-text-muted)
             (txt-right (- w m) (+ by 28) th-at theme-text-sub)
             ;; the temperature line, when the body has room for it
             (let* ((cy (+ by 54)) (ch (- bottom cy 24)))
               (if (and (>= ch 36) (>= (length th-temps) 2))
                   (let* ((vals (reverse th-temps))
                          (lo (- (list-min vals) 5)) (hi (+ (list-max vals) 5)))
                     (gui-rect m cy (- w m m) ch theme-card-hdr #t)
                     (line-chart m cy (- w m m) ch vals lo hi theme-warning)
                     (txt (+ m 2) cy (fixed->str hi 1) theme-text-muted)
                     (txt (+ m 2) (- (+ cy ch) 18) (fixed->str lo 1) theme-text-muted))))
             (txt-fit m (- bottom 18) (- w m m) status theme-text-muted))))))

(app-define! "蓝牙温湿度" (list (app-local-page "温湿度" th-render)))
