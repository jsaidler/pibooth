# -*- coding: utf-8 -*-

import time
from tkinter import NO
import pygame
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
from pibooth.pictures import sizing
from pibooth.utils import LOGGER


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
                return picamera.PiCamera(camera_num=port, sensor_mode=2)
            return picamera.PiCamera(sensor_mode=2)
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
        self._cam.iso = self.iso
        self._cam.rotation = self.preview_rotation
        #drc_strength, na prática, reduz as altas luzes e aumenta as sombras.
        # self._cam.drc_strength = 'high'
        self._cam.meter_mode = 'matrix'
        self._cam.sharpness = 33
        # self._cam.still_stats = True
        self._shutter_values = np.array([15, 30, 60, 120, 180, 240, 300, 360, 480, 600, 780, 960, 1200, 1500, 1920, 2400, 3060, 3840, 4860])
        self._iso_values = np.array([100, 200, 320, 400, 640, 800])
        self._white_balance_values = ['auto', 'sunlight', 'cloudy', 'shade', 'tungsten', 'fluorescent', 'incandescent', 'flash', 'horizon']
        self._current_white_balance_value = 0

    def _post_process_capture(self, capture_data):
        """Rework capture data.

        :param capture_data: binary data as stream
        :type capture_data: :py:class:`io.BytesIO`
        """
        # "Rewind" the stream to the beginning so we can read its content
        capture_data.seek(0)
        return Image.open(capture_data)
    
    def get_rect(self, max_size=None, x_offset = 0, y_offset = 0):
        """Return a Rect object (as defined in pygame) for resizing preview and images
        in order to fit to the defined window.
        """
        rect = self._window.get_rect(absolute=True)
        size = (rect.width - 2 * self._border, rect.height - 2 * self._border)
        LOGGER.info("Imagem: %s, Tela: %s", self._cam.resolution, size)
        if max_size:
            size = (min(size[0], max_size[0]), min(size[1], max_size[1]))
        res = sizing.new_size_keep_aspect_ratio(self._cam.resolution, size)
        LOGGER.info("Janela do preview é %s", res)
        return pygame.Rect(rect.centerx - res[0] // 2 + x_offset, rect.centery - res[1] // 2 + y_offset, res[0], res[1])
    
    def set_shutter(self, index = None):
        max_shutter_index = len(self._shutter_values) - 1
        if index is not None:
            if index < 0:
                index = 0
            elif index > max_shutter_index:
                index = max_shutter_index
            speed = self._shutter_values[index]
            self._cam.shutter_speed = 1000000//speed
        else:
            #shutter_speed e exposure_speed são valores inteiros medidos em microsegundos.
            index = np.absolute(self._shutter_values - 1000000/self._cam.exposure_speed).argmin()
        return (index, int(1000000/self._cam.shutter_speed))
    
    def set_auto_shutter(self):
        self._cam.shutter_speed = 0
        return (0, 0)
    
    def set_iso(self, index = None):
        max_iso_index = len(self._iso_values) - 1
        if index is not None:
            if index < 0:
                index = 0
            elif index > max_iso_index:
                index = max_iso_index
            self._cam.iso = self._iso_values[index]
        return (index, self._cam.iso)
    
    def set_auto_iso(self):
        self._cam.iso = 0
        return (0,0)
    
    def set_white_balance(self, value = None):
        if value is None:
            self._current_white_balance_value += 1
            if self._current_white_balance_value >= len(self._white_balance_values):
                self._current_white_balance_value = 0
            self._cam.awb_mode = self._white_balance_values[self._current_white_balance_value]
            return self._cam.awb_mode
        
        if value is not None and (value >= len(self._white_balance_values) or value < 0):
            value = 0
            self._cam.awb_mode = self._white_balance_values[value]
            return self._cam.awb_mode          
        
    def get_preview_area(self, window):
        self._window = window
        rect = self.get_rect(self._cam.resolution, y_offset=-25)
        return tuple(rect)

    def preview(self, area, flip=True):
        """Display a preview on the given Rect (flip if necessary).
        """
        if self._cam.preview is not None:
            # Already running
            return
                
        if self._cam.hflip:
            if flip:
                # Don't flip again, already done at init
                flip = False
            else:
                # Flip again because flipped once at init
                flip = True
                
        self._cam.start_preview(hflip=flip,
                                fullscreen=False,
                                window=area)

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
