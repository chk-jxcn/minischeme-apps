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
