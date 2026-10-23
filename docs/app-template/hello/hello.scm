;;; =========================================================================
;;; hello: the app template (docs/APP_DEVELOPMENT_GUIDE.md). 320x480 portrait,
;;; on the app framework (gui.scm, infopages.scm and applib.scm come first).
;;;   1 count  a local page: a counter kept in the app's folder; a long press
;;;            adds one, the web page sets it back to zero
;;;   2 news   a proxy page: /app/news from the app server
;;; Every global name starts with "hello-": all files share one namespace.
;;; =========================================================================

(define HELLO-FILE "count.txt")          ; relative: inside /spiffs/apps/hello/
(define HELLO-NEWS-INTERVAL 600000)     ; ms between fetches while the page shows

;; 1. State: read once at the start, written only when it changes ---------------

(define hello-count
  (let ((s (and (fs-exists? HELLO-FILE) (fs-read HELLO-FILE))))
    (or (and s (string->number s)) 0)))

;; Text built once per change, not in every render
(define hello-count-text (number->string hello-count))

(define (hello-set-count! n)
  (set! hello-count n)
  (set! hello-count-text (number->string n))
  (fs-write HELLO-FILE hello-count-text)
  (set! app-footer-text (string-append "计数已保存 " app-time))
  (app-invalidate-all))                 ; the body and the footer

;; 2. Page 1: local -----------------------------------------------------------------

(define (hello-render-count items)        ; items is always '() on a local page
  (section (body-top) "计数")
  (if (gui-visible? 80 64)
      (gui-text-scaled 20 80 hello-count-text theme-text-main 2 F-BIG))
  (txt 20 160 "长按按键：加一" theme-text-sub)
  (txt 20 184 "设备网页的应用选项卡：清零" theme-text-sub)
  (txt-wrap 20 230 (- (scr-w) 40) 60 "短按翻页；按住 8 秒打开硬件信息页。" theme-text-muted))

;; 3. Page 2: data from the app server ----------------------------------------------
;; /app/news answers {"items":[{"t":"item","a":title,...}, {"t":"upd","a":"HH:MM"}]}

(define (hello-news-url)
  (app-url (string-append "/app/news?cat=realtime&n=" (app-config "news_count" "5"))))

(define (hello-render-news items)
  (let loop ((l (items-all items "item")) (y (body-top)) (i 1))
    (if (and (pair? l) (< (+ y 24) (body-bottom)))
        (begin
          (txt 10 y (number->string i) theme-accent)
          (txt-fit 34 y (- (scr-w) 44) (it-a (car l)) theme-text-main)
          (gui-line 10 (+ y 22) (- (scr-w) 10) (+ y 22) theme-divider)
          (loop (cdr l) (+ y 28) (+ i 1))))))

;; 4. Buttons and the web page ---------------------------------------------------------

(define (app-long-press)
  (hello-set-count! (+ hello-count 1)))

;; The web page's calls (web.html: appCall("get") / appCall("reset"))
(define (app-web name body)
  (cond ((string=? name "get") (web-ok (cons 'count hello-count)))
        ((string=? name "reset")
         (hello-set-count! 0)
         (web-ok (cons 'count hello-count)))
        (else (web-error (string-append "unknown call: " name)))))

;; 5. Start -------------------------------------------------------------------------------

(set! app-footer-text "长按加一")

(app-define! "示例应用"
  (list (app-local-page "计数" hello-render-count)
        (app-page "新闻" hello-news-url HELLO-NEWS-INTERVAL hello-render-news)))
