;;; libs: combo
;;; combo.scm: members, the page list (entries: app.page), the alerts override

(define (render items) #t)

;; two members, as tools/build_apps.py puts their code after combo.scm
(combo-loading! "weather")
(app-define! "天气" (list (app-local-page "首页" render) (app-local-page "七日" render)))
(combo-member! "weather" (list "front" "sevendays") (list (cons "location" "auto")))
(combo-loading! "notifier")
(app-define! "消息" (list (app-local-page "最新" render) (app-local-page "全部" render)))
(combo-member! "notifier" (list "latest" "all") '())

(check "members" (map combo-id combo-members) '("weather" "notifier"))
(check "a member's title" (combo-title (combo-find-member "notifier")) "消息")
(check "combo-find-member: none" (combo-find-member "stocks") #f)

(define (page-of spec) (let ((e (combo-parse spec))) (and e (vector-ref e 1))))
(check "combo-parse: front" (page-of "weather.front") 0)
(check "combo-parse: English page name" (page-of "weather.sevendays") 1)
(check "combo-parse: number from 1" (page-of "notifier.2") 1)
(check "combo-parse: the page's own name" (page-of "notifier.全部") 1)
(check "combo-parse: spaces" (page-of "  notifier.latest ") 0)
(check "combo-parse: no such page" (combo-parse "weather.hourly") #f)
(check "combo-parse: page number out of range" (combo-parse "weather.3") #f)
(check "combo-parse: no such member" (combo-parse "stocks.front") #f)
(check "combo-parse: no page" (combo-parse "weather") #f)

;; every page of every member when entries is empty; else the entries in order, repeats kept
(check "all entries" (map combo-entry-name (combo-all-entries)) '("首页" "七日" "最新" "全部"))
(device-set-config! "entries" "weather.sevendays, notifier.latest, weather.front, weather.sevendays, bad.x")
(combo-start! "合集")
(check "entries in order, repeated, unknown left out"
       (map combo-entry-name (vector->list combo-entries)) '("七日" "最新" "首页" "七日"))
(check "the combined app's pages" (app-npages) 4)

;; the combined app's alerts setting: id:priority[:exit[:seconds]], 0 = none of that member's
(device-set-config! "alerts" "weather:7:time:20, notifier:0")
(check "override: priority" (combo-alert-override "weather" "alert_priority") "7")
(check "override: exit" (combo-alert-override "weather" "alert_exit") "time")
(check "override: seconds" (combo-alert-override "weather" "alert_seconds") "20")
(check "override: alerts on" (combo-alert-override "weather" "alert") #f)
(check "override: 0 turns them off" (combo-alert-override "notifier" "alert") "0")
(check "override: no priority with 0" (combo-alert-override "notifier" "alert_priority") #f)
(check "override: another member" (combo-alert-override "stocks" "alert_priority") #f)

(check "combo-trim" (combo-trim "  a b  ") "a b")

(check-done)
