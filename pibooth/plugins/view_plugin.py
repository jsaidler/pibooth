# -*- coding: utf-8 -*-

import pibooth
import pygame # type: ignore
from pibooth.utils import LOGGER, get_crash_message, PoolingTimer


class ViewPlugin(object):

    """Plugin to manage the pibooth window dans transitions.
    """

    name = 'pibooth-core:view'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.count = 0
        # Seconds to display the failed message
        self.failed_view_timer = PoolingTimer(3)

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
        win.show_intro(app.previous_picture, app.printer.is_ready()
                       and app.count.remaining_duplicates > 0)
        if app.printer.is_installed():
            win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

    @pibooth.hookimpl
    def state_wait_do(self, app, win, events):
        if not app.printer.is_installed():
            return None
        
        previous_picture = app.previous_picture
        event = app.find_print_status_event(events)
        
        if event:
            win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

        if app.find_print_event(events) or (win.get_image() and not previous_picture):
            win.show_intro(previous_picture, app.printer.is_ready() and app.count.remaining_duplicates > 0)

    @pibooth.hookimpl
    def state_wait_validate(self, cfg, app, events):
        touch_point = app.touch_screen_points(events)
        if touch_point == 'CENTER-LEFT' or touch_point == 'MIDDLE-TOP-LEFT' or touch_point == 'MIDDLE-BOTTOM-LEFT':
            if len(app.capture_choices) > 1:
                return 'choose'
            else:
                return 'preview'
            #A impressão é controlada pelo state_wait_do
        elif touch_point == 'TOP-LEFT':
            exit(0)

    @pibooth.hookimpl
    def state_wait_exit(self, win):
        self.count = 0
        win.show_image(None)  # Clear currently displayed image

    @pibooth.hookimpl
    def state_choose_enter(self, app, win):
        LOGGER.info("Show picture choice (nothing selected)")
        win.set_print_number(0, False)  # Hide printer status
        win.show_choice(app.capture_choices)
                       
    @pibooth.hookimpl
    def state_choose_validate(self, app, events):
        touch_point = app.touch_screen_points(events)
        if touch_point == 'CENTER-LEFT' or touch_point == 'MIDDLE-TOP-LEFT' or touch_point == 'MIDDLE-BOTTOM-LEFT':
            app.capture_nbr = app.capture_choices[0]
            return 'preview'
        elif touch_point == 'CENTER-RIGHT'or touch_point == 'MIDDLE-TOP-RIGHT' or touch_point == 'MIDDLE-BOTTOM-RIGHT':
            app.capture_nbr = app.capture_choices[1]
            return 'preview'
        elif touch_point == 'BOTTOM-LEFT':
            return 'wait'

    @pibooth.hookimpl
    def state_preview_enter(self, app, win):
        self.count += 1
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_preview_validate(self, app, events):
        touch_point = app.touch_screen_points(events)
        if touch_point == 'BOTTOM-LEFT':
            return 'wait'
        elif touch_point == 'CENTER-LEFT' or  touch_point == 'CENTER-RIGHT':
            return 'capture'

    @pibooth.hookimpl
    def state_capture_do(self, app, win):
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_capture_validate(self, app):
        if self.count >= app.capture_nbr:
            return 'processing'
        return 'preview'

    @pibooth.hookimpl
    def state_processing_enter(self, win):
        win.show_work_in_progress()

    @pibooth.hookimpl
    def state_processing_validate(self, cfg, app):
        if app.printer.is_ready() and cfg.getfloat('PRINTER', 'printer_delay') > 0\
                and app.count.remaining_duplicates > 0:
            return 'print'
        return 'wait'  # Can not print

    @pibooth.hookimpl
    def state_print_enter(self, cfg, app, win):
        LOGGER.info("Display the final picture")
        win.show_print(app.previous_picture)
        win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

    @pibooth.hookimpl
    def state_print_validate(self, app, win, events):
        touch_point = app.touch_screen_points(events)
        if touch_point == 'MIDDLE-TOP-RIGHT':
            win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())
            return 'wait'
        elif touch_point == 'MIDDLE-BOTTOM-RIGHT':
            return 'wait'