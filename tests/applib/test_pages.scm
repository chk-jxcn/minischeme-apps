;;; applib section 5 and 8: pages, settings, the carousel's seconds, turning pages

(define (render items) #t)

(check "app-config: missing" (app-config "city" "auto") "auto")
(device-set-config! "city" "")
(check "app-config: empty is missing" (app-config "city" "auto") "auto")
(device-set-config! "city" "深圳")
(check "app-config" (app-config "city" "auto") "深圳")

;; one value per page, at least 3 s; the last one repeats
(device-set-config! "carousel" "1")
(device-set-config! "carousel_seconds" "15,4,1")
(app-define! "测试" (list (app-local-page "一" render) (app-local-page "二" render) (app-local-page "三" render)))
(check "app-npages" (app-npages) 3)
(check "first page" app-page-index 0)
(check "app-local?" (app-local? 0) #t)
(check "seconds of page 1" (app-page-seconds 0) 15)
(check "seconds of page 2" (app-page-seconds 1) 4)
(check "seconds: at least 3" (app-page-seconds 2) 3)
(check "seconds: the last repeats" (app-page-seconds 5) 3)
(app-next-page!)
(check "app-next-page!" app-page-index 1)
(app-next-page!)
(app-next-page!)
(check "app-next-page!: wraps" app-page-index 0)
(app-goto! 2)
(check "app-goto!" app-page-index 2)
(check "app-cur" (vector-ref (app-cur) 0) "三")

;; carousel off, or a single page: no carousel
(device-set-config! "carousel" "0")
(check "app-carousel-config: off" (app-carousel-config) #f)
(device-set-config! "carousel" "1")
(device-set-config! "carousel_seconds" "")
(check "app-carousel-config: the default" (app-carousel-config) '(10))
(app-define! "单页" (list (app-local-page "一" render)))
(check "one page: no carousel" app-carousel #f)
(check "no carousel: 10 s" (app-page-seconds 0) 10)

;; a page with a URL: the url-proc is called once, at app-define!
(define url-calls 0)
(app-define! "数据" (list (app-page "首页" (lambda () (set! url-calls (+ url-calls 1)) "http://x/app/weather") 60000 render)))
(check "url-proc called once" url-calls 1)
(check "app-local?: a feed page" (app-local? 0) #f)

(check-done)
