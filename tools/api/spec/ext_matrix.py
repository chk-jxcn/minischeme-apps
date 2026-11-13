"""API entries: matrix, the RGB LED matrix extension (see api/__init__.py for the fields).

The Waveshare ESP32-S3-Matrix has 64 LEDs in 8 rows of 8 and no display. A pixel is (x, y),
(0, 0) at the top left; a colour is one number, #xRRGGBB. matrix-set and matrix-fill change
a buffer, (matrix-show) sends it to the LEDs; matrix-draw, matrix-clear and
matrix-brightness send at once.
"""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    api('matrix-size', 'matrix',
        sig='(matrix-size)',
        desc='The size of the LED matrix.',
        returns='A pair (columns . rows): (8 . 8).',
        example='''
(let ((size (matrix-size)))
  (* (car size) (cdr size)))          ; the number of LEDs
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False,
        notes='An app that needs the matrix declares "extensions = matrix 1.0" in its meta.ini; '
              "(api-has? 'matrix-set) says whether this device has one."),
    api('matrix-set', 'matrix',
        sig='(matrix-set x y color)',
        desc='Sets one pixel of the buffer; (matrix-show) sends the buffer to the LEDs.',
        returns='#t; an error when x or y is outside 0..7 or color outside 0..#xffffff.',
        example='''
(matrix-set 0 0 #xff0000)             ; top left: red
(matrix-set 7 7 #x0000ff)             ; bottom right: blue
(matrix-show)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-get', 'matrix',
        sig='(matrix-get x y)',
        desc='The colour of one pixel of the buffer.',
        returns='A number, #xRRGGBB; an error when x or y is outside 0..7.',
        example='''
(matrix-get 0 0)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-fill', 'matrix',
        sig='(matrix-fill color)',
        desc='Sets every pixel of the buffer to one colour; (matrix-show) sends it.',
        returns='#t; an error when color is outside 0..#xffffff.',
        example='''
(matrix-fill #x00ff00)
(matrix-show)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-draw', 'matrix',
        sig='(matrix-draw colors)',
        desc='Sets all 64 pixels from a vector or a list of colours, row by row from the top left, and shows them.',
        returns='#t (#f when the LEDs could not be driven); an error unless colors holds exactly 64 numbers 0..#xffffff.',
        example='''
(define picture (make-vector 64 0))
(vector-set! picture 27 #xffff00)     ; x 3, y 3
(matrix-draw picture)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-show', 'matrix',
        sig='(matrix-show)',
        desc='Sends the buffer to the LEDs (about 2.5 ms).',
        returns='#t, #f when the LEDs could not be driven.',
        example='''
(matrix-fill 0)
(matrix-set 3 4 #xffffff)
(matrix-show)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-clear', 'matrix',
        sig='(matrix-clear)',
        desc='Turns every LED off (clears the buffer and shows it).',
        returns='#t, #f when the LEDs could not be driven.',
        example='''
(matrix-clear)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False),
    api('matrix-brightness', 'matrix',
        sig='(matrix-brightness [percent])',
        desc='The brightness of the matrix, 0..100; with an argument sets it and shows the buffer again.',
        returns='The brightness in percent; an error when percent is outside 0..100.',
        example='''
(matrix-brightness 10)                ; dim
(matrix-brightness)
''',
        since='1.0.0', where=DEVICE, ext='matrix', check=False,
        notes='The colours of the buffer are scaled when they are sent: 100 is the most the firmware allows '
              '(about a third of what the LEDs can do: 64 LEDs at full power draw several amperes and heat the '
              'board within seconds), the start value is config.ini [matrix] matrix_brightness (25).'),
]
