"""API entries: imu, the accelerometer / gyroscope extension (see api/__init__.py for the fields).

A board with a QMI8658 (the Waveshare ESP32-S3-Matrix). The values are along the chip's own
axes: which way they point on a board is found by tilting it.
"""
from api import api, alias, RESERVED, DEVICE, PC  # noqa: F401

APIS = [
    api('imu-accel', 'imu',
        sig='(imu-accel)',
        desc='The acceleration along the three axes of the sensor; at rest that is gravity.',
        returns='A list (x y z) of integers in mg (1000 is one g; the range is +-4000), or #f when the sensor '
                'does not answer.',
        example='''
(let ((a (imu-accel)))
  (if a (> (abs (caddr a)) 800) #f))  ; lying flat: gravity is along z
''',
        since='1.0.0', where=DEVICE, ext='imu', check=False,
        notes='An app that needs the sensor declares "extensions = imu 1.0" in its meta.ini; '
              "(api-has? 'imu-accel) says whether this device has one. A read takes about 0.3 ms; calls within "
              '4 ms share one read.'),
    api('imu-gyro', 'imu',
        sig='(imu-gyro)',
        desc='How fast the board turns around the three axes of the sensor.',
        returns='A list (x y z) of integers in 0.1 degrees a second (the range is +-5120), or #f when the sensor '
                'does not answer.',
        example='''
(imu-gyro)                            ; => (0 -1 2) at rest
''',
        since='1.0.0', where=DEVICE, ext='imu', check=False),
    api('imu-temperature', 'imu',
        sig='(imu-temperature)',
        desc="The sensor chip's temperature (warmer than the room: the board heats it).",
        returns='An integer in 0.1 degrees Celsius, or #f when the sensor does not answer.',
        example='''
(imu-temperature)                     ; => 312: 31.2 degrees
''',
        since='1.0.0', where=DEVICE, ext='imu', check=False),
]
