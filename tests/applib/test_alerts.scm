;;; applib section 9: alerts (priorities, preemption and resume, exits, snooze, settings)

(define (render) #t)
(app-define! "提醒测试" (list (app-local-page "一" (lambda (items) #t))))

(define (titles) (map app-al-title app-alerts))
(define (current-title) (let ((a (app-alert-current))) (and a (app-al-title a))))
(define acks 0)

(app-alert! "low" "Low" render (list (cons 'priority 4) (cons 'exit 'time) (cons 'seconds 3)))
(check "one alert" (current-title) "Low")
(app-alert! "high" "High" render (list (cons 'priority 8) (cons 'exit 'button)
                                       (cons 'ack (lambda () (set! acks (+ acks 1))))))
(check "a higher one goes first" (current-title) "High")
(app-alert! "mid" "Mid" render (list (cons 'priority 6)))
(app-alert! "mid2" "Mid2" render (list (cons 'priority 6)))
(check "queue: priority, then arrival" (titles) '("High" "Mid" "Mid2" "Low"))
(check "app-alert-waiting" (app-alert-waiting) 4)
(check "app-alert-active?" (app-alert-active? "mid") #t)
(check "app-alert-active?: none" (app-alert-active? "nope") #f)

;; raising a key again updates that alert
(app-alert! "mid2" "Mid2b" render (list (cons 'priority 6)))
(check "raised again: updated, not added" (titles) '("High" "Mid" "Mid2b" "Low"))

;; a short press: the ack runs, a button alert ends
(app-alert-press! (app-alert-current))
(check "press: ack ran" acks 1)
(check "press: the next one shows" (current-title) "Mid")

;; the app ends one; that key is not raised again
(check "app-alert-done!" (app-alert-done! "mid") #t)
(check "app-alert-done!: gone" (current-title) "Mid2b")
(check "app-alert-done!: unknown" (app-alert-done! "mid") #f)
(check "an ended key is not raised again" (app-alert! "mid" "Mid" render '()) #f)
(check "still the same queue" (titles) '("Mid2b" "Low"))

;; a time alert ignores the press
(app-alert-snooze! (app-alert-current))        ; Mid2b for 5 minutes: Low shows
(check "snoozed: the next one shows" (current-title) "Low")
(app-alert-press! (app-alert-current))
(check "a time alert ignores the press" (current-title) "Low")

;; Low (time, 3 s) counts down while it shows and ends
(app-alert-tick!)
(app-alert-tick!)
(check "counting down" (app-al-left (app-alert-current)) 1)
(app-alert-tick!)
(check "time over: ended" (map app-al-title app-alerts) '("Mid2b"))
(check "nothing shows while it sleeps" (app-alert-current) #f)
(define woke-after
  (let loop ((k 1)) (app-alert-tick!) (if (or (current-title) (> k 400)) k (loop (+ k 1)))))
(check "the snooze is over" (current-title) "Mid2b")
(check "5 minutes after the snooze" (+ woke-after 3) 300)     ; 3 s passed while Low showed
(check "back with its full seconds (that second counted)" (app-al-left (app-alert-current)) 29)

;; the user's settings come first
(device-set-config! "alert_priority" "9")
(device-set-config! "alert_exit" "button")
(app-alert! "set" "Set" render (list (cons 'priority 2) (cons 'exit 'time)))
(check "alert_priority wins" (app-al-priority (app-alert-current)) 9)
(check "alert_exit wins" (app-al-exit (app-alert-current)) 'button)
(device-set-config! "alert" "0")
(check "alert = 0: none" (app-alert! "off" "Off" render '()) #f)

(check-done)
