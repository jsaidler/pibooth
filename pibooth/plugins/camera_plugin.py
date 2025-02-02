# -*- coding: utf-8 -*-

import time
import pygame # type: ignore
import pibooth
from pibooth import camera
from pibooth.utils import LOGGER


class CameraPlugin(object):

    """Plugin to manage the camera captures.
    """

    name = 'pibooth-core:camera'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.count = 0
        self._iso = 0
        self._shutter = 0

    @pibooth.hookimpl(hookwrapper=True)
    def pibooth_setup_camera(self, cfg):
        outcome = yield  # all corresponding hookimpls are invoked here
        cam = outcome.get_result()

        if not cam:
            LOGGER.debug("Fallback to pibooth default camera management system")
            cam = camera.find_camera()

        cam.initialize(cfg.getint('CAMERA', 'iso'),
                       cfg.gettyped('CAMERA', 'resolution'),
                       cfg.gettuple('CAMERA', 'rotation', int, 2),
                       cfg.getboolean('CAMERA', 'flip'),
                       cfg.getboolean('CAMERA', 'delete_internal_memory'))
        outcome.force_result(cam)

    @pibooth.hookimpl
    def pibooth_cleanup(self, app):
        app.camera.quit()

    @pibooth.hookimpl
    def state_failsafe_enter(self, app):
        """Reset variables set in this plugin.
        """
        app.capture_date = None
        app.capture_nbr = None
        app.camera.drop_captures()  # Flush previous captures

    @pibooth.hookimpl
    def state_wait_enter(self, app):
        app.capture_date = None
        if len(app.capture_choices) > 1:
            app.capture_nbr = None
        else:
            app.capture_nbr = app.capture_choices[0]

    @pibooth.hookimpl
    def state_preview_enter(self, app):
        LOGGER.info("Show preview before next capture")
        if not app.capture_date:
            app.capture_date = time.strftime("%Y-%m-%d-%H-%M-%S")

    @pibooth.hookimpl
    def state_preview_do(self, app, events):
        pygame.event.pump()  # Before blocking actions
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-TOP-LEFT':
            self._shutter, app.shutter_speed = app.camera.set_auto_shutter()
        if interaction == 'TOUCH-MIDDLE-TOP-LEFT':
            self._shutter += 1
            self._shutter, app.shutter_speed = app.camera.set_shutter(self._shutter)
        elif interaction == 'TOUCH-MIDDLE-BOTTOM-LEFT':
            self._shutter -= 1
            self._shutter, app.shutter_speed = app.camera.set_shutter(self._shutter)
        elif interaction == 'TOUCH-TOP-RIGHT':
            self._iso, app.iso = app.camera.set_auto_iso()
        elif interaction == 'TOUCH-MIDDLE-TOP-RIGHT':
            self._iso += 1
            self._iso, app.iso = app.camera.set_iso(self._iso)
        elif interaction == 'TOUCH-MIDDLE-BOTTOM-RIGHT':
            self._iso -= 1
            self._iso, app.iso = app.camera.set_iso(self._iso)
        elif interaction == 'TOUCH-CENTER-BOTTOM-LEFT':
            app.white_balance = app.camera.set_white_balance()

    # @pibooth.hookimpl
    # def state_preview_exit(self, cfg, app):
    #     if cfg.getboolean('WINDOW', 'preview_stop_on_capture'):
    #         app.camera.stop_preview()

    @pibooth.hookimpl
    def state_capture_do(self, cfg, app, win):
        effects = cfg.gettyped('PICTURE', 'captures_effects')
        if not isinstance(effects, (list, tuple)):
            # Same effect for all captures
            effect = effects
        elif len(effects) >= app.capture_nbr:
            # Take the effect corresponding to the current capture
            effect = effects[self.count]
        else:
            # Not possible
            raise ValueError("Not enough effects defined for {} captures {}".format(
                app.capture_nbr, effects))

        LOGGER.info("Take a capture")
        app.camera.capture(effect)
        self.count += 1

    # @pibooth.hookimpl
    # def state_capture_exit(self, cfg, app):
    #     if not cfg.getboolean('WINDOW', 'preview_stop_on_capture'):
    #         app.camera.stop_preview()

    @pibooth.hookimpl
    def state_processing_enter(self):
        self.count = 0
