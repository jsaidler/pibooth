# -*- coding: utf-8 -*-

import time
import pibooth
import pygame # type: ignore
from pibooth import camera
from pibooth.utils import LOGGER, get_crash_message, PoolingTimer


class ViewPlugin(object):

    """Plugin to manage the pibooth window dans transitions.
    """

    name = 'pibooth-core:view'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.capture_count = 1
        # Seconds to display the failed message
        self.failed_view_timer = PoolingTimer(3)
        self._shutter_speed = None
        self._iso = None
        self._white_balance = None
        self._preview_area = None
        

    @pibooth.hookimpl
    def state_failsafe_enter(self, win):
        win.show_oops()
        self.failed_view_timer.start()
        LOGGER.error(get_crash_message())

    @pibooth.hookimpl
    def state_failsafe_validate(self):
        if self.failed_view_timer.is_timeout():
            return 'wait'

    @pibooth.hookimpl
    def state_wait_enter(self, app, win):
        win.show_intro(app.previous_picture, app.printer.is_ready())
        win.set_print_number(len(app.printer.get_all_tasks()), app.printer.is_ready())
        app.camera.stop_preview()

    @pibooth.hookimpl
    def state_wait_do(self, app, win, events):
        if not app.printer.is_installed():
            return None
        
        event = app.find_print_status_event(events)
        if event:
            win.set_print_number(len(app.printer.get_all_tasks()), app.printer.is_ready())

    @pibooth.hookimpl
    def state_wait_validate(self, app, events):
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-CENTER-LEFT' or interaction == 'TOUCH-MIDDLE-TOP-LEFT' or interaction == 'TOUCH-MIDDLE-BOTTOM-LEFT':
            if len(app.capture_choices) > 1:
                return 'choose'
            else:
                return 'preview'
            #A impressão é controlada pelo state_wait_do
        elif interaction == 'TOUCH-TOP-LEFT':
            exit(0)

    @pibooth.hookimpl
    def state_wait_exit(self, win):
        win.show_image(None)  # Clear currently displayed image

    @pibooth.hookimpl
    def state_choose_enter(self, app, win):
        LOGGER.info("Show picture choice (nothing selected)")
        # win.set_print_number(0, False)  # Hide printer status
        win.show_choice(app.capture_choices)
                       
    @pibooth.hookimpl
    def state_choose_validate(self, app, events):
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-CENTER-LEFT' or interaction == 'TOUCH-MIDDLE-TOP-LEFT' or interaction == 'TOUCH-MIDDLE-BOTTOM-LEFT':
            app.capture_nbr = app.capture_choices[0]
            return 'preview'
        elif interaction == 'TOUCH-CENTER-RIGHT'or interaction == 'TOUCH-MIDDLE-TOP-RIGHT' or interaction == 'TOUCH-MIDDLE-BOTTOM-RIGHT':
            # app.capture_nbr = app.capture_choices[1]            
            app.capture_nbr = app.capture_choices[0]
            return 'preview'
        elif interaction == 'TOUCH-BOTTOM-LEFT':
            return 'wait'

    @pibooth.hookimpl
    def state_preview_enter(self, app, win):
        self._preview_area = app.camera.get_preview_area(win)
        win.show_capture(self._preview_area)
        app.camera.preview(self._preview_area)
        win.set_capture_number(self.capture_count, app.capture_nbr)
        
    @pibooth.hookimpl
    def state_preview_do(self, app, win):
        if self._shutter_speed != app.shutter_speed:
           self._shutter_speed = win.set_shutter_speed(app.shutter_speed)
        if self._iso != app.iso:
           self._iso = win.set_iso(app.iso)
        if self._white_balance != app.white_balance:
           self._white_balance = win.set_white_balance(app.white_balance)

    @pibooth.hookimpl
    def state_preview_validate(self, app, events):
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-BOTTOM-LEFT':
            return 'wait'
        elif interaction == 'TOUCH-CENTER-LEFT' or  interaction == 'TOUCH-CENTER-RIGHT' or  interaction == 'CAPTURE':
            return 'capture'

    # @pibooth.hookimpl
    # def state_capture_do(self, app, win):
    #     win.set_capture_number(self.capture_count, app.capture_nbr)

    @pibooth.hookimpl
    def state_capture_validate(self, app):
        return 'confirm'
    
    @pibooth.hookimpl
    def state_confirm_enter(self, app, win):        
        app.camera.stop_preview()
        LOGGER.info("Display the last captured picture")
        win.show_confirm(app.camera.get_last_capture())
    
    @pibooth.hookimpl
    def state_confirm_validate(self, app, win, events):
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-MIDDLE-TOP-RIGHT' or  interaction == 'CAPTURE':
            self.capture_count += 1
            if self.capture_count > app.capture_nbr:
                return 'processing'
            else:
                return 'preview'
        elif interaction == 'TOUCH-MIDDLE-BOTTOM-RIGHT':
            app.camera.drop_last_capture()
            return 'preview'
    
    @pibooth.hookimpl
    def state_confirm_exit(self, win, app):
        win.show_image(None)  # Clear currently displayed image

    @pibooth.hookimpl
    def state_processing_enter(self, app, win):
        self.capture_count = 1
        win.show_work_in_progress()

    @pibooth.hookimpl
    def state_processing_validate(self, cfg, app):
        if app.printer.is_ready() and app.count.remaining_duplicates > 0:
            return 'print'
        return 'wait'  # Can not print

    @pibooth.hookimpl
    def state_print_enter(self, app, win):
        LOGGER.info("Display the final picture")
        win.show_print(app.previous_picture)
        win.set_print_number(len(app.printer.get_all_tasks()), app.printer.is_ready())

    @pibooth.hookimpl
    def state_print_validate(self, app, win, events):
        interaction = app.user_interaction(events)
        if interaction == 'TOUCH-MIDDLE-TOP-RIGHT':
            win.set_print_number(len(app.printer.get_all_tasks()), app.printer.is_ready())
            return 'wait'
        elif interaction == 'TOUCH-MIDDLE-BOTTOM-RIGHT':
            return 'wait'