"""API entries: display, gui, font, fontrom, lunar (see api/__init__.py for the fields)."""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

# Shared remarks of the drawing entries (reference only, not in the firmware)
_RENDER = ('Draw from `gui-render-proc`: the runtime calls it for the rows queued by '
           '`gui-invalidate` (in band mode it runs once, recorded as a display list that is '
           'replayed for each band, and the drawing is clipped to the rows being redrawn). '
           'Outside it, full mode keeps the pixels and sends them to the panel at the next '
           'display service, direct mode draws straight to the panel, and band mode loses them '
           'when the next band is drawn.')

APIS = [
    # ---- display -----------------------------------------------------------
    api('display-model', 'display',
        sig='(display-model)',
        desc='Panel model string.',
        returns='String, "ILI9488-8BIT-PARALLEL-480x320" on every build.',
        example='''
(display-model)  ; => "ILI9488-8BIT-PARALLEL-480x320"
''',
    ),
    api('display-rotation', 'display',
        sig='(display-rotation [r])',
        desc='Panel rotation 0..3 (0 and 2 portrait 320x480, 1 and 3 landscape 480x320); returns the rotation.',
        returns='Fixnum 0..3, the rotation after the call (r is taken modulo 4). Setting it '
                're-initializes the screen in direct mode with the new size and clears it. A '
                'non-integer r is ignored.',
        example='''
(display-rotation)            ; => 0
(display-rotation 1)          ; => 1
(list (gui-width) (gui-height))  ; => (480 320)
(display-rotation 0)          ; => 0
''',
        notes='The WASM simulator and the PC build keep a simulated rotation. Setting a rotation '
              'goes through `gui-init`, so the buffer mode becomes `direct` (see `gui-mode`) '
              'until the next boot; call `gui-invalidate` to have the app redrawn.',
    ),
    api('display-dma-ram', 'display',
        sig='(display-dma-ram)',
        desc="Bytes of the LCD driver's DMA and staging buffers (0 without DMA).",
        returns='Fixnum >= 0: the bytes on the board; always 0 in the WASM simulator and on the PC.',
        example='''
(>= (display-dma-ram) 0)  ; => #t
''',
    ),
    alias('lcd-dma-ram', 'display-dma-ram', 'display'),
    # ---- gui ---------------------------------------------------------------
    api('gui-init', 'gui',
        sig='(gui-init [w h])',
        desc='Re-initialize the screen as w x h pixels (default 320x480) in direct mode and clear it.',
        returns='Void. Without two integers the default size is used; a size over 480x480 '
                'pixels keeps the current size.',
        example='''
(gui-init 480 320)
(list (gui-width) (gui-height) (gui-mode))  ; => (480 320 direct)
''',
        notes='Legacy: the firmware sets the screen up at boot from config.ini [display] (mode, '
              'band_lines, color_bits). `gui-init` always switches to direct mode; to change the '
              'size only use `gui-set-resolution`.',
    ),
    api('gui-clear', 'gui',
        sig='(gui-clear [color])',
        desc='Fill the current clip (the whole screen without one) with an RGB565 color (default dark slate 2179).',
        returns='Void.',
        example='''
(gui-clear (gui-rgb 0 0 64))
(gui-pixel 100 200)  ; => 8
''',
        notes='In `gui-render-proc` the clip is the span being redrawn, which the runtime has '
              'already cleared to 2179 (#0b1118). ' + _RENDER,
    ),
    api('gui-flush', 'gui',
        sig='(gui-flush)',
        desc='Mark the whole screen changed for the host canvas (simulator). The board sends pixels by itself.',
        returns='Void.',
        example='''
(gui-flush-dirty)
(gui-flush)
(gui-dirty-rect)  ; => (0 0 320 480)
''',
        notes='Legacy. Apps redraw through `gui-invalidate` and `gui-render-proc`; in full mode '
              '`gui-flush-dirty` sends rows drawn outside a render at once.',
    ),
    api('gui-pixel', 'gui',
        sig='(gui-pixel x y [color])',
        desc='Set one pixel to an RGB565 color; (gui-pixel x y) reads the stored color back.',
        returns='Void when setting; with two arguments the RGB565 fixnum at x y (0 outside the '
                'screen or where no pixels are kept: band rows not being drawn, direct mode). '
                'Pixels outside the clip are skipped.',
        example='''
(gui-pixel 10 20 (gui-rgb 255 0 0))
(gui-pixel 10 20)  ; => 63488
''',
        notes='At color bits below 16 the read-back is the palette color the pixel was mapped to. '
              + _RENDER,
    ),
    api('gui-line', 'gui',
        sig='(gui-line x0 y0 x1 y1 color)',
        desc='Draw a one-pixel line between two points, both ends included.',
        returns='Void; ignored unless all five arguments are integers.',
        example='''
(gui-line 0 0 99 99 (gui-rgb 0 255 0))
(gui-pixel 50 50)  ; => 2016
''',
        notes=_RENDER,
    ),
    api('gui-rect', 'gui',
        sig='(gui-rect x y w h color [filled])',
        desc='Draw a rectangle, filled unless filled is #f (then a one-pixel outline).',
        returns='Void; ignored unless x y w h color are integers or when w or h <= 0.',
        example='''
(gui-rect 10 10 100 40 (gui-rgb 0 0 255))
(gui-rect 10 60 100 40 (gui-rgb 255 255 255) #f)
(list (gui-pixel 50 30) (gui-pixel 50 80) (gui-pixel 50 60))  ; => (31 2179 65535)
''',
        notes=_RENDER,
    ),
    api('gui-round-rect', 'gui',
        sig='(gui-round-rect x y w h r color [filled])',
        desc='Draw a rectangle with corners of radius r, filled unless filled is #f.',
        returns='Void; ignored unless the first six arguments are integers. r is limited to '
                'half the width and height; r <= 0 draws a plain rectangle.',
        example='''
(gui-round-rect 10 10 120 40 8 (gui-rgb 255 128 0))
(list (gui-pixel 10 10) (gui-pixel 70 30))  ; => (2179 64512)
''',
        notes=_RENDER,
    ),
    api('gui-circle', 'gui',
        sig='(gui-circle cx cy r color [filled])',
        desc='Draw a circle of radius r around cx cy, filled unless filled is #f.',
        returns='Void; ignored unless the first four arguments are integers. r <= 0 draws the '
                'center pixel.',
        example='''
(gui-circle 160 240 30 (gui-rgb 255 0 0))
(gui-circle 160 240 50 (gui-rgb 255 255 255) #f)
(list (gui-pixel 160 240) (gui-pixel 210 240))  ; => (63488 65535)
''',
        notes=_RENDER,
    ),
    api('gui-text', 'gui',
        sig='(gui-text x y str color [size])',
        desc='Draw UTF-8 text with its top-left corner at x y in the current font; size 2.. draws the built-in 8x8 font scaled.',
        returns='Void; ignored unless x y are integers, str a string and color an integer.',
        example='''
(gui-text 10 10 "Hello" (gui-rgb 255 255 255))
(gui-text 10 40 "BIG" (gui-rgb 255 255 0) 3)
''',
        notes='size 1 (default) is `gui-text-styled` with the current font (`gui-set-font`). '
              'Larger sizes scale the built-in 8x8 ASCII glyphs and 16x16 CJK glyphs by size; a "\\n" '
              'starts a new line. ' + _RENDER,
    ),
    api('gui-set-font', 'gui',
        sig='(gui-set-font font-id)',
        desc='Set the current font: 0 system 16 px, 1 clock 32 px (digits), 2..7 registered or loaded fonts.',
        returns='Void. Any integer is kept; text in an id without a font uses the system font.',
        example='''
(gui-set-font 1)
(gui-get-font)  ; => 1
(gui-set-font 0)
''',
        notes='The current font is global (shared by every app until changed) and used by '
              '`gui-text`, `gui-text-width` and the text procedures whose font argument is left out.',
    ),
    api('gui-get-font', 'gui',
        sig='(gui-get-font)',
        desc='The current font id (see gui-set-font).',
        returns='Fixnum, the id last given to `gui-set-font` (0 at boot).',
        example='''
(gui-get-font)  ; => 0
''',
    ),
    api('gui-text-width', 'gui',
        sig='(gui-text-width str [font-id])',
        desc='Width in pixels of str drawn in a font (default the current font).',
        returns='Fixnum >= 0, the sum of the glyph advances; 0 when str is not a string.',
        example='''
(gui-text-width "Hello" 0)  ; => 40
(gui-text-width "12:30" 1)  ; => 92
''',
        notes='Lay out text with it: right-align at xr with '
              '`(gui-text-styled (- xr (gui-text-width s f)) y s c f)`. A missing glyph counts '
              'as the width it is drawn with (the system font, or a box).',
    ),
    api('gui-text-styled', 'gui',
        sig='(gui-text-styled x y str color [font-id])',
        desc='Draw UTF-8 text with its top-left corner at x y in a font (default the current font).',
        returns='Void; ignored unless x y are integers, str a string and color an integer.',
        example='''
(gui-text-styled 10 10 "Temperature" (gui-rgb 200 200 200) 0)
(gui-text-styled 10 30 "21:45" (gui-rgb 255 255 255) 1)
''',
        notes='Glyphs the font lacks come from the system font, then the built-in font; with none '
              'a box is drawn. "\\n" starts a new line (font height + 2 lower). ' + _RENDER,
    ),
    api('gui-text-box', 'gui',
        sig='(gui-text-box x y w h str color [font-id [halign [valign]]])',
        desc='Draw one line of text aligned in a box and clipped to it. halign 0 left, 1 center, 2 right; valign 0 top, 1 middle, 2 bottom.',
        returns='Void; ignored unless x y w h are integers, str a string and color an integer. '
                'font-id defaults to the current font, halign and valign to 0.',
        example='''
(gui-rect 0 0 320 40 (gui-rgb 24 28 43))
(gui-text-box 0 0 320 40 "Weather" (gui-rgb 255 255 255) 0 1 1)
''',
        notes=_RENDER,
    ),
    api('gui-text-scaled', 'gui',
        sig='(gui-text-scaled x y str color scale [font-id])',
        desc='Draw UTF-8 text in a font (default the current one) with every dot scale x scale (2..8): large text without a large font.',
        returns='Void. scale 1 or less draws as gui-text-styled, more than 8 as 8. An error when x, y, color or '
                'scale is not an integer or str is not a string.',
        example='''
(gui-text-scaled 10 40 "阿莫西林" (gui-rgb 255 255 255) 2)   ; 16 px font -> 32 px
(gui-text-scaled 10 40 'name 0 2)  ; => error: expected
''',
        since='1.7.0',
        notes='The glyphs of the font chain (the system font, its fallbacks) are enlarged: a dot set (an '
              'anti-aliased dot more than half covered) becomes a scale x scale square, so the edges are '
              'blocky but no font file is needed. Lines (\\n) are (height + 2) x scale apart. Check it with '
              '(defined? \'gui-text-scaled) on older firmware. ' + _RENDER,
    ),
    api('gui-chart', 'gui',
        sig='(gui-chart x y w h ring start count lo hi color)',
        desc='Line chart of count values of the vector ring from index start (wrapping), scaled from lo..hi to the box.',
        returns='Void. An error when ring is not a vector or another argument is not an integer; '
                'nothing is drawn when count < 2 or hi <= lo.',
        example='''
(define temps (vector 18 19 21 24 23 20))
(gui-chart 10 300 300 100 temps 0 6 15 25 (gui-rgb 0 200 255))
(gui-chart 10 300 300 100 '(1 2) 0 2 0 9 0)  ; => error: expected
''',
        notes='Values are clamped to lo..hi; elements that are not integers count as lo. count is '
              'limited to the vector length and 320 points, h to 256. Points are spread evenly over '
              'w. A ring buffer of samples draws in order with start = the oldest index. ' + _RENDER,
    ),
    api('gui-image', 'gui',
        sig='(gui-image x y path [frame [speed]])',
        desc='Draw an image file at x y (its top-left corner): a baseline JPEG, or an animation (a MANI file of '
             'JPEG frames, which the photo album\'s web page makes from a GIF).',
        returns='Void. frame: #t (the default) plays an animation by its frame delays, #f shows its first '
                'frame, a number that frame; speed: percent of the delays\' pace, 10..1000 (100). path is in '
                'the app\'s folder like the fs- procedures. Errors: a file that cannot be opened or is not a '
                'baseline JPEG / MANI file (progressive JPEG, PNG and GIF need converting: the album\'s page '
                'does it in the browser).',
        example='''
(gui-image 0 0 "photos/none.jpg")  ; => error: gui-image: cannot open the image file
''',
        notes='One display-list command: a band decodes only the JPEG\'s MCU rows it covers (the decoder '
              'remembers where each one starts), so a full-screen photo needs no frame buffer; about 6 KB '
              'while an image is open. A playing animation redraws only its own box at its shortest frame '
              'delay, its clock starting when it appears. ' + _RENDER,
        since='1.5.0',
    ),
    api('image-info', 'gui',
        sig='(image-info path)',
        desc='The size of an image file and its frames: (width height frames total-ms).',
        returns='The list, or #f when the file is missing or not an image gui-image can draw. total-ms is an '
                'animation\'s length (0 for one frame).',
        example='''
(image-info "photos/none.jpg")  ; => #f
''',
        notes='Center an image: x = (320 - width) / 2. Opening an image reads only its headers.',
        since='1.5.0',
    ),
    api('gui-bitmap', 'gui',
        sig='(gui-bitmap x y w h data scale fg [bg])',
        desc='Draw a 1-bit bitmap of w x h dots, each dot scale x scale pixels: set dots in fg, clear ones in bg (left as they are without bg).',
        returns='Void. data is a string of bytes: h rows of (w + 7) / 8 bytes each, the first dot of a byte '
                'its high bit (a row ends on a byte boundary). Errors: data shorter than that, w or h not '
                '1..4096, scale not 1..255, another argument not an integer.',
        example='''
;; a 2 x 2 checker: rows #b10000000 and #b01000000, 10 px dots
(define checker (list->string (list (integer->char 128) (integer->char 64))))
(gui-bitmap 100 100 2 2 checker 10 (gui-rgb 255 255 255) 0)
(gui-pixel 105 105)  ; => 65535
(gui-pixel 115 105)  ; => 0
(gui-pixel 115 115)  ; => 65535
(gui-bitmap 0 0 16 2 checker 1 0)  ; => error: data has
''',
        notes='One display-list command however many dots (the rows go to its string pool): a QR code or '
              'an icon costs what one rectangle does, where gui-rect per dot or per run used up the '
              '512-command list. A band draws only its rows, each row\'s runs of set dots as single '
              'rectangles. Build data with list->string of (integer->char byte) values; it may hold 0 bytes. '
              + _RENDER,
        since='1.4.0',
    ),
    api('gui-arc', 'gui',
        sig='(gui-arc cx cy r thickness start-deg sweep-deg color)',
        desc="Draw a ring arc of outer radius r: 0 degrees is 3 o'clock, sweeping clockwise.",
        returns='Void. An error when an argument is not an integer; nothing is drawn when r, '
                'thickness or sweep-deg <= 0. sweep-deg >= 360 draws the full ring.',
        example='''
(gui-arc 160 240 50 8 270 90 (gui-rgb 0 255 0))
(gui-pixel 192 208)  ; => 2016
(gui-arc 160 240 50 8 0 90)  ; => error: expected
''',
        notes='A gauge: `(gui-arc cx cy r 8 135 (quotient (* 270 pct) 100) color)` over a dim full '
              '270-degree track. ' + _RENDER,
    ),
    api('gui-push-clip', 'gui',
        sig='(gui-push-clip x y w h)',
        desc='Save the current clip and clip drawing to the rectangle x y w h (no allocation).',
        returns='Void. An error when an argument is not an integer or when pushes nest deeper '
                'than 8.',
        example='''
(gui-push-clip 0 0 100 50)
(gui-get-clip)  ; => (0 0 100 50)
(gui-pop-clip)
(gui-get-clip)  ; => (0 0 320 480)
''',
        notes='Pair every push with a `gui-pop-clip`. The stack is reset each time the runtime '
              'calls `gui-render-proc`. Inside a render the effective clip is also limited to the '
              'rows being redrawn.',
    ),
    api('gui-pop-clip', 'gui',
        sig='(gui-pop-clip)',
        desc='Restore the clip saved by the matching gui-push-clip.',
        returns='Void. An error when no clip is saved.',
        example='''
(gui-push-clip 20 20 80 80)
(gui-rect 0 0 320 480 (gui-rgb 255 0 0))
(gui-pop-clip)
(list (gui-pixel 10 10) (gui-pixel 50 50))  ; => (2179 63488)
(gui-pop-clip)  ; => error: no saved clip
''',
    ),
    api('gui-mode', 'gui',
        sig='(gui-mode)',
        desc='Buffer mode: band (a few rows at a time), full (whole frame) or direct (no buffer).',
        returns='Symbol band, full or direct. Set by config.ini [display] mode; full falls back to '
                'band, band to direct, when RAM is short.',
        example='''
(gui-mode)  ; => full
''',
    ),
    api('gui-color-bits', 'gui',
        sig='(gui-color-bits [n])',
        desc='Bits per stored pixel: 16 (RGB565) or 8, 4, 2, 1 (palette indices); setting it redraws.',
        returns='Fixnum, the bits after the call. An error when n is not 16, 8, 4, 2 or 1.',
        example='''
(gui-color-bits)     ; => 16
(gui-color-bits 4)   ; => 4
(gui-buffer-ram)     ; => 76800
(gui-color-bits 16)  ; => 16
(gui-color-bits 3)   ; => error: expected 16, 8, 4, 2 or 1
''',
        notes='Fewer bits cost less buffer RAM (bits/16 of the RGB565 size); colors are mapped to '
              'the palette of the color scheme (`gui-color-scheme`). Changing it re-creates the '
              'buffer, clears the screen and queues a full redraw. Kept until the next boot '
              '(config.ini [display] color_bits sets the boot value).',
    ),
    api('gui-color-scheme', 'gui',
        sig='(gui-color-scheme [name])',
        desc='Color scheme: color, gray, eink, green, amber, cyan, gameboy, invert (RGB negative) or custom.',
        returns='Symbol, the scheme after the call. name is a symbol or string; older names '
                '(mono, e-ink, matrix, negative, ...) are accepted. An error for an unknown name.',
        example='''
(gui-color-scheme)          ; => color
(gui-color-scheme 'amber)   ; => amber
(gui-color-scheme "color")  ; => color
(gui-color-scheme 'sepia)   ; => error: unknown scheme
''',
        notes='Ramp schemes (gray ... gameboy) map colors by brightness; at 16 bits they tint the '
              'screen with 64 levels. Setting a scheme queues a full redraw; it is kept until the '
              'next boot (config.ini [display] palette).',
    ),
    api('gui-buffer-ram', 'gui',
        sig='(gui-buffer-ram)',
        desc='Bytes held by the band or frame buffer (0 in direct mode).',
        returns='Fixnum: width x rows x bits / 8 (the band rows in band mode, the screen in full mode).',
        example='''
(gui-buffer-ram)  ; => 307200
''',
    ),
    api('gui-card', 'gui',
        sig='(gui-card x y w h r bg-color border-color)',
        desc='Rounded card: a filled background plus a one-pixel outline (border 0 or bg-color: none).',
        returns='Void; ignored unless all seven arguments are integers. r 0 draws square corners.',
        example='''
(gui-card 10 10 300 80 8 (gui-rgb 24 28 43) (gui-rgb 41 48 74))
(list (gui-pixel 160 50) (gui-pixel 160 10))  ; => (6373 10633)
''',
        notes=_RENDER,
    ),
    api('gui-text-wrap', 'gui',
        sig='(gui-text-wrap x y w h str color [font [line-height]])',
        desc='Draw text wrapped to width w, as many lines as fit in h; cut text ends with an ellipsis. Returns the lines drawn.',
        returns='Fixnum, the number of lines drawn (at least 1 line is drawn when h is smaller '
                'than a line). An error when x y w h color are not integers or str is not a string.',
        example='''
(gui-text-wrap 10 10 100 200 "one two three four five six" 65535 0)  ; => 3
(gui-text-wrap 10 10 100 18 "one two three four five six" 65535 0)   ; => 1
''',
        notes='Lines break at spaces, or between two characters when either is CJK (Latin words '
              'and numbers stay whole; closing punctuation never starts a line); "\\n" forces a '
              'break. line-height defaults to the font height + 2. Use `gui-text-area` to scroll '
              'text that does not fit instead. ' + _RENDER,
    ),
    api('gui-text-fit', 'gui',
        sig='(gui-text-fit x y w str color [font])',
        desc='One line of text in a box w pixels wide; a longer line is cut with an ellipsis or scrolls as set by config.ini [text] marquee.',
        returns='Void. An error when x y w color are not integers or str is not a string.',
        example='''
(gui-text-fit 10 10 120 "Short" 65535 0)
(gui-text-fit 10 30 120 "A headline much too long for its box" 65535 0)
''',
        notes='The box is the font height + 2 tall. Modes (`gui-marquee`): none cuts the line '
              'with an ellipsis; pixel and char move it marquee_step pixels or characters '
              'marquee_fps times a second; page shows box-wide pieces in turn. Draw it from '
              '`gui-render-proc` every time: the runtime animates the box by redrawing only its '
              'rows (or its rectangle) without another `gui-invalidate`.',
    ),
    api('gui-text-area', 'gui',
        sig='(gui-text-area x y w h str color [font [line-h]])',
        desc='Text wrapped to a box; text taller than the box is cut with an ellipsis or scrolls as set by config.ini [text] wrap_marquee.',
        returns='Void. An error when x y w h color are not integers or str is not a string.',
        example='''
(gui-text-area 10 10 300 60 "A long news summary that needs several lines to fit in this box." 65535 0)
''',
        notes='Wraps like `gui-text-wrap`; line-h defaults to the font height + 2. Modes '
              '(`gui-marquee \'wrap`): none cuts the text with an ellipsis; pixel rolls it up; line '
              'moves wrap_marquee_step lines at a time; page shows the next box-full; '
              'wrap_marquee_fps times a second. Draw it from `gui-render-proc`; the box animates '
              'by itself.',
    ),
    api('gui-marquee', 'gui',
        sig="(gui-marquee ['wrap] [mode [fps [step [hold]]]])",
        desc="Marquee settings (mode fps step hold) of one-line text, or of wrapped text with 'wrap; arguments set them until the next boot.",
        returns="List (mode fps step hold): mode a symbol, fps a number (0.1..25 refreshes a "
                "second), step a fixnum 1..64 (pixels, characters or lines), hold the seconds "
                "(0..10) the start stays. An error for a mode the kind does not take.",
        example='''
(define saved (gui-marquee))
(gui-marquee 'char 2 1 0.5)  ; => (char 2 1 0.5)
(gui-marquee 'wrap)          ; => (line 0.5 1 1)
(gui-marquee 'line)          ; => error: one-line text takes
(apply gui-marquee saved)
''',
        notes="One-line text (`gui-text-fit`) takes none, pixel, char or page; wrapped text "
              "(`gui-text-area`) none, pixel, line or page. Arguments left out keep their values. "
              "The boot values come from config.ini [text] (marquee, marquee_fps, marquee_step, "
              "marquee_hold and the wrap_ ones); setting them queues a full redraw.",
    ),
    api('gui-text-scroll', 'gui',
        sig='(gui-text-scroll x y w h str color [font [speed [direction]]])',
        desc="Text longer than its box scrolls in a loop: direction 'left (marquee, default) or 'up (wrapped lines); speed in pixels per second (default 30).",
        returns='Void. An error when x y w h color are not integers or str is not a string. '
                'speed is limited to 0..2000.',
        example='''
(define (render)
  (gui-text-scroll 10 10 200 20 "Breaking news: a very long headline scrolls" 65535 0 40))
(define gui-render-proc render)
(gui-invalidate)
''',
        notes='Text that fits is drawn still. Draw it from `gui-render-proc` like other text; the '
              'offset comes from the frame clock and the runtime redraws only the box while it '
              'moves (up to 25 times a second), without running the render procedure again until '
              'the app calls `gui-invalidate`.',
    ),
    api('gui-seg7', 'gui',
        sig='(gui-seg7 x y digit-w digit-h thickness str on off glow highlight)',
        desc='Draw seven-segment digits (0-9, -, : and .); unlit segments in off, lit ones in on with optional glow and highlight colors.',
        returns='Fixnum, the width drawn (as `gui-seg7-width`); 0 and nothing drawn when an argument '
                'has the wrong type.',
        example='''
(define on (gui-rgb 255 80 0))
(define off (gui-rgb 40 20 10))
(gui-seg7 10 10 30 56 6 "12:45" on off on on)  ; => 152
''',
        notes='glow != on draws a halo around lit segments; highlight != on (thickness >= 5) a '
              'thin bright core. Pass on for both to draw plain segments. Characters other than '
              'the digits, "-", ":" and "." leave a blank digit. ' + _RENDER,
    ),
    api('gui-seg7-width', 'gui',
        sig='(gui-seg7-width digit-w thickness str)',
        desc='Width in pixels gui-seg7 draws for str.',
        returns='Fixnum: digit-w per character, thickness + 2 per ":" or ".", plus '
                'thickness / 2 + 3 between characters; 0 for wrong arguments.',
        example='''
(gui-seg7-width 30 6 "12:45")  ; => 152
(gui-seg7-width 30 6 "")       ; => 0
''',
    ),
    api('gui-set-resolution', 'gui',
        sig='(gui-set-resolution w h)',
        desc='Change the logical screen size, keeping the buffer mode; the screen is cleared and redrawn.',
        returns='Void. Ignored when w or h <= 0 or w x h is over 480x480 pixels.',
        example='''
(gui-set-resolution 480 320)
(list (gui-width) (gui-height) (gui-mode))  ; => (480 320 full)
''',
        notes='It does not rotate the panel: use `display-rotation` for that. In band mode a wider '
              'screen gets fewer band rows so the band keeps its RAM.',
    ),
    api('gui-set-clip', 'gui',
        sig='(gui-set-clip x y w h)',
        desc='Clip drawing to a rectangle (limited to the screen).',
        returns='Void; ignored unless all four arguments are integers. w or h <= 0 clips everything away.',
        example='''
(gui-set-clip 0 0 100 50)
(gui-rect 0 0 320 480 (gui-rgb 255 0 0))
(list (gui-pixel 50 25) (gui-pixel 150 25))  ; => (63488 2179)
(gui-reset-clip)
''',
        notes='Prefer `gui-push-clip` / `gui-pop-clip`, which restore the caller\'s clip.',
    ),
    api('gui-reset-clip', 'gui',
        sig='(gui-reset-clip)',
        desc='Remove the clip rectangle: drawing reaches the whole screen again.',
        returns='Void.',
        example='''
(gui-set-clip 10 10 50 50)
(gui-reset-clip)
(gui-get-clip)  ; => (0 0 320 480)
''',
    ),
    api('gui-get-clip', 'gui',
        sig='(gui-get-clip)',
        desc='Current clip rectangle as (x y w h).',
        returns='List of four fixnums; (0 0 width height) without a clip.',
        example='''
(gui-get-clip)  ; => (0 0 320 480)
(gui-set-clip -10 400 50 200)
(gui-get-clip)  ; => (0 400 40 80)
''',
    ),
    api('gui-dirty-rect', 'gui',
        sig='(gui-dirty-rect)',
        desc='Bounding box of the screen area changed since the host canvas last took it, as (x y w h).',
        returns='List of four fixnums; (0 0 0 0) when nothing changed.',
        example='''
(gui-flush-dirty)
(gui-dirty-rect)  ; => (0 0 0 0)
(gui-mark-dirty 10 20 30 40)
(gui-dirty-rect)  ; => (10 20 30 40)
''',
        notes='For hosts that paint a canvas (the WASM simulator); apps do not need it.',
    ),
    api('gui-mark-dirty', 'gui',
        sig='(gui-mark-dirty x y w h)',
        desc='Mark a rectangle as changed for the host canvas.',
        returns='Void; ignored unless all four arguments are integers.',
        example='''
(gui-flush-dirty)
(gui-mark-dirty 0 0 40 40)
(gui-dirty-rect-count)  ; => 1
''',
        notes='It does not redraw anything: to have the app redraw use `gui-invalidate`.',
    ),
    api('gui-dirty-rect-count', 'gui',
        sig='(gui-dirty-rect-count)',
        desc='Number of dirty rectangles after merging (at most 8).',
        returns='Fixnum 0..8.',
        example='''
(gui-flush-dirty)
(gui-mark-dirty 0 0 40 40)
(gui-mark-dirty 200 300 40 40)
(gui-dirty-rect-count)  ; => 2
''',
    ),
    api('gui-dirty-rects', 'gui',
        sig='(gui-dirty-rects)',
        desc='Dirty rectangles after merging into 32-pixel tiles, as a list of (x y w h).',
        returns='List of up to 8 lists (x y w h), top to bottom; () when nothing changed.',
        example='''
(gui-flush-dirty)
(gui-mark-dirty 0 0 40 40)
(gui-mark-dirty 200 300 40 40)
(gui-dirty-rects)  ; => ((0 0 64 64) (192 288 48 52))
''',
    ),
    api('gui-flush-dirty', 'gui',
        sig='(gui-flush-dirty)',
        desc='Full mode: send the rows drawn outside a render to the panel now.',
        returns='Void. On the PC build it also clears the dirty rectangles.',
        example='''
(gui-rect 0 0 320 40 (gui-rgb 0 0 128))
(gui-flush-dirty)
''',
        notes='The runtime sends such rows at its next display service anyway; call it when the '
              'app draws outside `gui-render-proc` and must show the result before a long '
              'computation. Other modes: no effect on the panel.',
    ),
    api('gui-render-bands', 'gui',
        sig='(gui-render-bands band-h proc)',
        desc='Call proc once per slice of band-h rows, drawing clipped to the slice: (lambda (i y h) ...) or (lambda (i) ...).',
        returns='#t; void when band-h is not an integer (nothing is called).',
        example='''
(define n 0)
(gui-render-bands 160 (lambda (i y h) (set! n (+ n 1))))  ; => #t
n  ; => 3
''',
        notes='Legacy immediate rendering: in band mode each slice is sent to the panel after proc '
              'returns, in full mode the frame after the last slice. band-h is limited to the band '
              'rows in band mode. Called from `gui-render-proc` it cannot be recorded, so the '
              'render procedure then runs once per band; prefer `gui-render-proc` with `gui-visible?`.',
    ),
    api('gui-create-buffer', 'gui',
        sig='(gui-create-buffer w h)',
        desc='Create an offscreen RGB565 buffer of w x h pixels; returns its id.',
        returns='Fixnum id 1..15; -1 when w or h is not a positive integer, memory is short or '
                'all 15 buffers are in use.',
        example='''
(define buf (gui-create-buffer 64 64))
(> buf 0)  ; => #t
(gui-destroy-buffer buf)
''',
        notes='The buffer holds w x h x 2 bytes of C heap (not the VM heap) until '
              '`gui-destroy-buffer`; it starts black.',
    ),
    api('gui-destroy-buffer', 'gui',
        sig='(gui-destroy-buffer id)',
        desc='Free an offscreen buffer (drawing returns to the screen if it was the target).',
        returns='Void; an unknown id is ignored.',
        example='''
(define buf (gui-create-buffer 32 32))
(gui-destroy-buffer buf)
(gui-destroy-buffer buf)
''',
    ),
    api('gui-set-target', 'gui',
        sig='(gui-set-target id)',
        desc='Draw into offscreen buffer id (0 = the screen); the clip becomes the whole target.',
        returns='Void; an unknown id is ignored.',
        example='''
(define buf (gui-create-buffer 40 40))
(gui-set-target buf)
(gui-circle 20 20 15 (gui-rgb 255 0 0))
(gui-pixel 20 20)  ; => 63488
(gui-set-target 0)
(gui-destroy-buffer buf)
''',
        notes='Ignored while `gui-render-proc` is being recorded (band mode then runs the render '
              'procedure once per band). Prepare buffers outside the render procedure.',
    ),
    api('gui-reset-target', 'gui',
        sig='(gui-reset-target)',
        desc='Draw to the screen again (same as (gui-set-target 0)).',
        returns='Void.',
        example='''
(define buf (gui-create-buffer 40 40))
(gui-set-target buf)
(gui-reset-target)
(gui-get-clip)  ; => (0 0 320 480)
(gui-destroy-buffer buf)
''',
    ),
    api('gui-blit-buffer', 'gui',
        sig='(gui-blit-buffer x y id)',
        desc='Copy an offscreen buffer to the current target at x y (clipped).',
        returns='Void; an unknown id is ignored.',
        example='''
(define buf (gui-create-buffer 40 40))
(gui-set-target buf)
(gui-clear (gui-rgb 0 255 0))
(gui-reset-target)
(gui-blit-buffer 100 100 buf)
(gui-pixel 120 120)  ; => 2016
(gui-destroy-buffer buf)
''',
        notes='Cannot be recorded: called from `gui-render-proc` in band mode, the render '
              'procedure runs once per band. ' + _RENDER,
    ),
    api('gui-framebuffer-enable', 'gui',
        sig='(gui-framebuffer-enable on?)',
        desc='Switch to full mode (true) or direct mode (#f); returns whether full mode is on.',
        returns='#t in full mode after the call, else #f (full mode needs RAM for the frame: '
                'without it the mode becomes band).',
        example='''
(gui-framebuffer-enable #f)  ; => #f
(gui-mode)                   ; => direct
(gui-framebuffer-enable #t)  ; => #t
''',
        notes='Switching re-creates the buffer, clears the screen and queues a full redraw.',
    ),
    api('gui-framebuffer-enabled?', 'gui',
        sig='(gui-framebuffer-enabled?)',
        desc='True in full (frame buffer) mode.',
        returns='#t in full mode, #f in band or direct mode.',
        example='''
(gui-framebuffer-enabled?)  ; => #t
''',
    ),
    api('gui-framebuffer-ram', 'gui',
        sig='(gui-framebuffer-ram)',
        desc='Bytes held by the band or frame buffer (same as gui-buffer-ram).',
        returns='Fixnum, 0 in direct mode.',
        example='''
(gui-framebuffer-ram)  ; => 307200
''',
    ),
    api('gui-color-depth', 'gui',
        sig='(gui-color-depth [bits])',
        desc='Legacy gui-color-bits: bits per stored pixel; a value other than 16, 8, 4, 2, 1 is ignored.',
        returns='Fixnum, the bits per pixel after the call. Never an error.',
        example='''
(gui-color-depth)    ; => 16
(gui-color-depth 3)  ; => 16
''',
    ),
    api('gui-color-format', 'gui',
        sig='(gui-color-format)',
        desc='Panel bus format: rgb565 or rgb666 (config.ini [display] color_format).',
        returns='Symbol rgb565 or rgb666.',
        example='''
(gui-color-format)  ; => rgb565
''',
    ),
    api('gui-mono-colors', 'gui',
        sig='(gui-mono-colors [fg bg])',
        desc='Two-color custom palette: sets entries 0 = bg and 1 = fg and the custom scheme; returns (fg bg).',
        returns='List (fg bg) of RGB565 fixnums: the ones set, or the brightest and darkest '
                'colors of the current palette (white and 2179 at 16 bits).',
        example='''
(gui-mono-colors)  ; => (65535 2179)
(gui-mono-colors (gui-rgb 255 176 0) 0)  ; => (64896 0)
(gui-color-scheme)  ; => custom
(gui-color-scheme 'color)
''',
        notes='Meant for 1-bit color (`gui-color-bits` 1).',
    ),
    api('gui-palette-set!', 'gui',
        sig='(gui-palette-set! index rgb565)',
        desc='Set palette entry 0..255 and switch to the custom scheme (starting from the current palette).',
        returns='Void; ignored when an argument is not an integer or index is outside 0..255.',
        example='''
(gui-color-bits 2)
(gui-palette-set! 3 (gui-rgb 255 0 0))
(list (gui-color-scheme) (gui-palette-get 3))  ; => (custom 63488)
(gui-color-scheme 'color)
(gui-color-bits 16)
''',
        notes='Only the first 2^bits entries are used (`gui-color-bits`). Queues a full redraw.',
    ),
    api('gui-palette-get', 'gui',
        sig='(gui-palette-get index)',
        desc='RGB565 color of a palette entry of the current scheme.',
        returns='Fixnum; 0 for an index the palette does not have (at 16 bits the color scheme '
                'has no palette) or a non-integer index.',
        example='''
(gui-palette-get 1)  ; => 0
(gui-color-bits 4)
(gui-palette-get 15)  ; => 65535
(gui-color-bits 16)
''',
    ),
    api('gui-palette-preset', 'gui',
        sig='(gui-palette-preset name)',
        desc='Legacy gui-color-scheme: set a scheme by name; #f for an unknown name.',
        returns='#t when name (symbol or string) is a known scheme, else #f (no error).',
        example='''
(gui-palette-preset 'gray)   ; => #t
(gui-palette-preset 'sepia)  ; => #f
(gui-palette-preset 'color)  ; => #t
''',
    ),
    api('gui-band-lines', 'gui',
        sig='(gui-band-lines)',
        desc='Rows per band in band mode (config.ini [display] band_lines).',
        returns='Fixnum: the band rows in band mode; in the other modes the configured value.',
        example='''
(gui-band-lines)  ; => 20
''',
    ),
    alias('gui-rotation', 'display-rotation', 'display'),
    api('gui-rgb', 'gui',
        sig='(gui-rgb r g b)',
        desc='RGB565 color of 8-bit red, green and blue (0..255).',
        returns='Fixnum 0..65535: r and b keep 5 bits, g 6. Components wrap modulo 256; 0 unless '
                'all three are integers.',
        example='''
(gui-rgb 255 0 0)      ; => 63488
(gui-rgb 255 255 255)  ; => 65535
(gui-rgb 11 17 24)     ; => 2179
''',
    ),
    api('gui-width', 'gui',
        sig='(gui-width)',
        desc='Screen width in pixels (320 in portrait, 480 in landscape).',
        returns='Fixnum.',
        example='''
(gui-width)  ; => 320
''',
    ),
    api('gui-height', 'gui',
        sig='(gui-height)',
        desc='Screen height in pixels (480 in portrait, 320 in landscape).',
        returns='Fixnum.',
        example='''
(gui-height)  ; => 480
''',
    ),
    api('gui-touch-poll', 'gui',
        sig='(gui-touch-poll)',
        desc='The touch point as (x . y) while the screen is touched, else #f.',
        returns='Pair of fixnums or #f. Only the WASM simulator reports touches (a click on its '
                'canvas); the board has no touch panel: always #f.',
        example='''
(gui-touch-poll)  ; => #f
''',
    ),
    api('gui-touch-down?', 'gui',
        sig='(gui-touch-down?)',
        desc='True while the screen is touched.',
        returns='#t or #f (always #f on the board, see `gui-touch-poll`).',
        example='''
(gui-touch-down?)  ; => #f
''',
    ),
    api('gui-invalidate', 'gui',
        sig='(gui-invalidate [x y w h])',
        desc='Queue rows y..y+h-1 (the whole screen without arguments) to be redrawn by gui-render-proc.',
        returns='Void. Only y and h count (whole rows are redrawn); (gui-invalidate y h) is also '
                'accepted.',
        example='''
(define count 0)
(define (render) (gui-text-styled 10 10 (number->string count) 65535 0))
(define gui-render-proc render)
(set! count 1)
(gui-invalidate 0 0 320 30)
''',
        notes='The redraw happens after the current event, at the next display service: the runtime '
              'clears the queued rows to 2179 and calls `gui-render-proc` (no arguments) with '
              'drawing clipped to them. Queue only the rows that changed. Calls made while the '
              'render procedure runs are ignored.',
    ),
    api('gui-visible?', 'gui',
        sig='(gui-visible? y h)',
        desc='Whether rows y..y+h-1 meet the area being drawn; skip the drawing of a section when #f.',
        returns='#t or #f; #t when the arguments are not two integers.',
        example='''
(gui-visible? 0 32)  ; => #t
(gui-set-clip 0 100 320 50)
(gui-visible? 0 32)  ; => #f
''',
        notes='Compares with the current clip: in `gui-render-proc` the rows being redrawn. In band '
              'mode the render procedure runs once for the whole span, so it skips sections '
              'outside what `gui-invalidate` queued.',
    ),
    # ---- font --------------------------------------------------------------
    api('font-load', 'font',
        sig="(font-load id path ['stream])",
        desc="Load an MFNT font file (tools/make_font.py) into slot 2..7. Small files go to RAM; large ones (or 'stream) are read glyph by glyph. An app loads only files of its own folder.",
        returns='#t. An error when id is not 2..7, path is not a string, or the file cannot be '
                'read or is not a valid MFNT font.',
        example='''
(font-load 3 "/spiffs/fonts/simhei-24.mfnt")  ; => #t
(gui-text-styled 10 10 "Hello" 65535 3)
(font-load 1 "/spiffs/fonts/simhei-24.mfnt")  ; => error: font id must be 2..7
''',
        check=False,
        notes='Needs an MFNT file on the board (or the simulator\'s file system). Files up to 24 KB '
              'are read into RAM on the board; larger ones stay on flash behind a glyph cache. The '
              'slot then holds only that font; loading queues a full redraw.',
    ),
    api('font-register!', 'font',
        sig='(font-register! id bytes)',
        desc='Use MFNT font bytes for slot 2..7, e.g. (include-bytes "x.mfnt"); a Code ROM literal is read in place, a heap string copied.',
        returns='#t when the slot holds a font afterwards. An error when id is not 2..7, bytes is '
                'not a string or not a valid MFNT font.',
        example='''
(font-register! 3 (include-bytes "fonts/digits-48.mfnt"))  ; => #t
(font-register! 3 "not a font")  ; => error: font-register!
''',
        check=False,
        notes='The font\'s name (stored in it) also brings the other sources of config.ini [fonts] '
              'font_order (font ROM, files) to fill glyphs it lacks. Queues a full redraw.',
    ),
    api('font-unload', 'font',
        sig='(font-unload id)',
        desc='Empty font slot 2..7; its text falls back to the system font.',
        returns='Void. An error when id is not 2..7.',
        example='''
(font-unload 3)
(font-info 3)    ; => #f
(font-unload 0)  ; => error: font id must be 2..7
''',
    ),
    api('font-info', 'font',
        sig='(font-info id)',
        desc='(name height glyphs source bytes) of a font slot; #f for an empty slot.',
        returns='List: name string, height in pixels, glyph count, source symbol (builtin, rom, '
                'ram, file or fontrom: the first source of the chain) and the bytes it holds (0 '
                'for builtin). #f for an empty slot or a non-integer id.',
        example='''
(font-info 0)  ; => ("system_16" 16 406 builtin 0)
(font-info 5)  ; => #f
''',
        notes='Slots 0 and 1 report builtin unless config.ini [fonts] font_override replaces them.',
    ),
    api('font-config', 'font',
        sig='(font-config [order [overrides]])',
        desc='Font sources and replacements (config.ini [fonts] font_order, font_override); with arguments set them and resolve every font again.',
        returns='List (sources overrides): the source symbols in order and a list of '
                '("name" . "replacement") pairs. An error for an unknown source, a source listed '
                'twice, or an override not written name:replacement.',
        example='''
(font-config)  ; => ((app fontrom spiffs) ())
(font-config "fontrom, app" "system_16:simsun-16")  ; => ((fontrom app) (("system_16" . "simsun-16")))
(font-config "app, fontrom, spiffs" "")  ; => ((app fontrom spiffs) ())
(font-config "web")  ; => error: font_order
''',
        notes='Sources: app (fonts the app carries), fontrom (the system font ROM), spiffs '
              '(/spiffs/fonts/<name>.mfnt). An override puts the sources of the replacement first; '
              'system_16 (or 0) and clock_32 (or 1) name the built-in fonts. Kept until the next '
              'boot; queues a full redraw.',
    ),
    api('font-sources', 'font',
        sig='(font-sources id)',
        desc='The chain searched for each glyph of slot id, in order, as ((source name height glyphs bits) ...).',
        returns='List of lists: source symbol (rom, ram, file, fontrom), name, height, glyph '
                'count and bits per pixel (1, 2 or 4). () for an empty slot or a built-in font.',
        example='''
(font-sources 0)  ; => ()
''',
        notes='A glyph no source has comes from the system font.',
    ),
    api('font-use', 'font',
        sig='(font-use id face [size])',
        desc="Font slot 2..7 for this app: face-size from the app's embedded subset, the font ROM or a file (config.ini [fonts] font_order). #f when no source has it.",
        returns='#t when slot id holds a font afterwards (also when it already held one: the slot '
                'is not changed), else #f and its text uses the system font. An error when id is '
                'not 2..7 or face is not a string.',
        example='''
(define f (if (font-use 3 "simhei" 24) 3 0))
f  ; => 0
(font-use 1 "simhei" 24)  ; => error: font id must be 2..7
''',
        notes="tools/build_apps.py embeds a subset of the face (the characters of the app's "
              "strings) unless the form ends with 'system or the build uses --system-fonts. At "
              "run time the name <face>-<size> is looked up in the sources of font_order (app, "
              "fontrom, spiffs): the font the app carries, the system font ROM, "
              "/spiffs/fonts/<face>-<size>.mfnt. A face with a '/' is a file path. Queues a full "
              "redraw when it fills the slot.",
    ),
    alias('use-font', 'font-use', 'font'),
    # ---- fontrom -----------------------------------------------------------
    api('fontrom-list', 'fontrom',
        sig='(fontrom-list)',
        desc='Fonts in the system font ROM (flash partition, read in place) as ((name height glyphs bytes) ...).',
        returns='List of lists: name string, height in pixels, glyph count, size in bytes; () '
                'without a font ROM partition.',
        example='''
(fontrom-list)  ; => ()
''',
        notes='On a board with a font ROM it gives e.g. (("msyh-16" 16 7000 250000) ...). '
              '`font-use` finds the fonts by name <face>-<size>.',
    ),
    api('fontrom-info', 'fontrom',
        sig='(fontrom-info)',
        desc='(used capacity count) of the system font ROM: bytes used, partition bytes, fonts.',
        returns='List of three fixnums; #f when the firmware has no fontrom partition (the WASM '
                'simulator and the PC build have none).',
        example='''
(fontrom-info)  ; => #f
''',
    ),
    api('fontrom-add', 'fontrom',
        sig='(fontrom-add path [name])',
        desc='Copy an MFNT font file into the system font ROM (name defaults to the one in the font; the same name replaces it). Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='String, the name stored. An error when path or name is not a string, there is no '
                'font ROM partition, or the file cannot be read, is not a font or does not fit.',
        example='''
(fontrom-add "/spiffs/fonts/simhei-24.mfnt")  ; => error: no font ROM partition
''',
        notes='On the board: `(fontrom-add "/spiffs/fonts/simhei-24.mfnt")` => "simhei-24". Slots '
              'using font ROM fonts are resolved again; queues a full redraw.',
    ),
    api('fontrom-remove', 'fontrom',
        sig='(fontrom-remove name)',
        desc='Remove a font from the system font ROM; later fonts move down. Not for apps: only the system settings and the REPL may (an app gets an error).',
        returns='#t when removed, #f when there is no such font (or no font ROM). An error when '
                'name is not a string or the flash write fails.',
        example='''
(fontrom-remove "simhei-24")  ; => #f
''',
    ),
    # ---- lunar -------------------------------------------------------------
    api('lunar-date', 'lunar',
        sig='(lunar-date year month day)',
        desc='The Chinese lunar date of a Gregorian date as (month day leap?).',
        returns='List: lunar month 1..12, day 1..30, #t in a leap month. #f for dates before '
                '1900-01-31 or after 2100, months outside 1..12, days outside 1..31 or '
                'non-integer arguments.',
        example='''
(lunar-date 2024 2 10)   ; => (1 1 #f)
(lunar-date 2023 3 22)   ; => (2 1 #t)
(lunar-date 1899 12 31)  ; => #f
''',
        notes='The day is not checked against the month: 2024-02-30 counts as 2024-03-01.',
    ),
    api('lunar-date-string', 'lunar',
        sig='(lunar-date-string year month day)',
        desc='The lunar date as Chinese display text for the screen.',
        returns='String "农历" + optional "闰" (leap) + month + "月" + day; #f where `lunar-date` '
                'gives #f.',
        example='''
(lunar-date-string 2024 2 10)  ; => "农历正月初一"
(lunar-date-string 2023 3 22)  ; => "农历闰二月初一"
''',
    ),
]
