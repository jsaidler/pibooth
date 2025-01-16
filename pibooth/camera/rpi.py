# -*- coding: utf-8 -*-

import time
import subprocess
import numpy as np  # type: ignore
from io import BytesIO
from PIL import Image # type: ignore
try:
    import picamera # type: ignore
except ImportError:
    picamera = None  # picamera is optional
from pibooth.language import get_translated_text
from pibooth.camera.base import BaseCamera


def get_rpi_camera_proxy(port=None):
    """Return camera proxy if a Raspberry Pi compatible camera is found
    else return None.

    :param port: look on given port number
    :type port: int
    """
    if not picamera:
        return None  # picamera is not installed
    try:
        process = subprocess.Popen(['vcgencmd', 'get_camera'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, _stderr = process.communicate()
        if stdout and u'detected=1' in stdout.decode('utf-8'):
            if port is not None:
                return picamera.PiCamera(camera_num=port)
            return picamera.PiCamera()
    except OSError:
        pass
    return None


class RpiCamera(BaseCamera):

    """Camera management
    """

    if picamera:
        IMAGE_EFFECTS = list(picamera.PiCamera.IMAGE_EFFECTS.keys())
    else:
        IMAGE_EFFECTS = []

    def _specific_initialization(self):
        """Camera initialization.
        """
        self._cam.framerate = 15  # Slower is necessary for high-resolution
        self._cam.video_stabilization = True
        self._cam.vflip = True
        self._cam.hflip = self.capture_flip
        self._cam.resolution = self.resolution
        self._cam.iso = self.preview_iso
        self._cam.rotation = self.preview_rotation
        #drc_strength, na prática, reduz as altas luzes e aumenta as sombras.
        self._cam.drc_strength = 'high'
        self._cam.meter_mode = 'matrix'
        self._cam.sharpness = 33
        self._cam.still_stats = True
        self._cam.zoom = (0.0,0.0556,1.0,0.9443) #proporção 4x6
        self._shutter_values = np.array([15, 20, 25, 30, 40, 50, 60, 80, 100, 125, 180, 200, 250, 500])
        self._iso_values = np.array([0, 100, 200, 320, 400, 640, 800 ])

    def _post_process_capture(self, capture_data):
        """Rework capture data.

        :param capture_data: binary data as stream
        :type capture_data: :py:class:`io.BytesIO`
        """
        # "Rewind" the stream to the beginning so we can read its content
        capture_data.seek(0)
        return Image.open(capture_data)
    
    def set_shutter(self, index):
        max_shutter_index = len(self._shutter_values) - 1
        if speed is not None:
            if index < 0:
                index = 0
            elif index > max_shutter_index:
                index = max_shutter_index
            if self._cam.shutter_speed == 0:
                index = np.absolute(self._shutter_values - self.cam.exposure_speed).argmin()
            speed = self._shutter_values[index]
            self._cam.shutter_speed = 1000//speed
        return (index, self._cam.shutter_speed)
    
    def set_auto_shutter(self):
        self._cam.shutter_speed = 0
    
    def set_iso(self, index):
        max_iso_index = len(self._iso_values) - 1
        if index is not None:
            if index < 0:
                index = 0
            elif index > max_iso_index:
                index = max_iso_index
            self._cam.iso = self._iso_values[index]
        return (index, self._cam.iso)   

    def preview(self, window, flip=True):
        """Display a preview on the given Rect (flip if necessary).
        """
        if self._cam.preview is not None:
            # Already running
            return

        self._window = window
        rect = self.get_rect(self._cam.MAX_RESOLUTION)
        if self._cam.hflip:
            if flip:
                # Don't flip again, already done at init
                flip = False
            else:
                # Flip again because flipped once at init
                flip = True
        self._cam.start_preview(resolution=(rect.width, rect.height), hflip=flip,
                                fullscreen=False, window=tuple(rect))

    def stop_preview(self):
        """Stop the preview.
        """
        self._cam.stop_preview()
        self._window = None

    def capture(self, effect=None):
        """Capture a new picture in a file.
        """
        effect = str(effect).lower()
        if effect not in self.IMAGE_EFFECTS:
            raise ValueError("Invalid capture effect '{}' (choose among {})".format(effect, self.IMAGE_EFFECTS))
        try:
            stream = BytesIO()
            self._cam.image_effect = effect
            self._cam.capture(stream, format='jpeg', quality=100)
            self._captures.append(stream)
        finally:
            self._cam.image_effect = 'none'

    def quit(self):
        """Close the camera driver, it's definitive.
        """
        self._cam.close()
