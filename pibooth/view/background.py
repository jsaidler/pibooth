# -*- coding: utf-8 -*-

import os.path as osp
from pibooth.utils import LOGGER
import pygame # type: ignore

from pibooth import fonts, pictures
from pibooth.language import get_translated_text

def multiline_text_to_surfaces(text, color, rect, align='center'):
    """Return a list of surfaces corresponding to each line of the text.
    The surfaces are next to each others in order to fit the given rect.

    The ``align`` parameter can be one of:
       * top-left
       * top-center
       * top-right
       * center-left
       * center
       * center-right
       * bottom-left
       * bottom-center
       * bottom-right
    """
    surfaces = []
    lines = text.splitlines()

    font = fonts.get_pygame_font(max(lines, key=len), fonts.CURRENT,
                                 rect.width, rect.height / len(lines))
    for i, line in enumerate(lines):
        surface = font.render(line, True, color)

        if align.endswith('left'):
            x = rect.left
        elif align.endswith('center'):
            x = rect.centerx - surface.get_rect().width / 2
        elif align.endswith('right'):
            x = rect.right - surface.get_rect().width
        else:
            raise ValueError("Invalid horizontal alignment '{}'".format(align))

        height = surface.get_rect().height
        if align.startswith('top'):
            y = rect.top + i * height
        elif align.startswith('center'):
            y = rect.centery - len(lines) * height / 2 + i * height
        elif align.startswith('bottom'):
            y = rect.bottom - (len(lines) - i) * height
        else:
            raise ValueError("Invalid vertical alignment '{}'".format(align))

        surfaces.append((surface, surface.get_rect(x=x, y=y)))
    return surfaces

class Background(object):

    def __init__(self, image_name, color=(0, 0, 0), text_color=(255, 255, 255)):
        self._rect = None
        self._name = image_name
        self._need_update = False

        self._background = None
        self._background_color = color
        self._background_image = None
        self._logo_backgrounf_image = None
        
        self._show_exit = False
        self._show_back = False

        self._overlay = None

        self._texts = []  # List of (surface, rect)
        self._text_border = 20  # Distance to other elements
        self._text_color = text_color

        # Build rectangles around some areas for debuging purpose
        self._show_outlines = True
        self._outlines = []

    def __str__(self):
        """Return background final name.

        It is used in the main window to distinguish backgrounds in the cache
        thus each background string shall be uniq.
        """
        return "{}({})".format(self.__class__.__name__, self._name)

    def _make_outlines(self, size):
        """Return a red rectangle surface.
        """
        outlines = pygame.Surface(size, pygame.SRCALPHA, 32)
        pygame.draw.rect(outlines, pygame.Color(255, 0, 0), outlines.get_rect(), 2)
        return outlines

    def _write_text(self, text, rect=None, align='center'):
        """Write a text in the given rectangle.
        """
        if not rect:
            rect = self._rect.inflate(-self._text_border, -self._text_border)
        if self._show_outlines:
            self._outlines.append((self._make_outlines(rect.size), rect))
        self._texts.extend(multiline_text_to_surfaces(text, self._text_color, rect, align))

    def set_color(self, color_or_path):
        """Set background color (RGB tuple) or path to an image that used to
        fill the background.

        :param color_or_path: RGB color tuple or image path
        :type color_or_path: tuple or str
        """
        if isinstance(color_or_path, (tuple, list)):
            assert len(color_or_path) == 3, "Length of 3 is required for RGB tuple"
            if color_or_path != self._background_color:
                self._background_color = color_or_path
                self._need_update = True
        else:
            assert osp.isfile(color_or_path), "Invalid image for window background: '{}'".format(color_or_path)
            if color_or_path != self._background_image:
                self._background_image = color_or_path
                self._background_color = (0, 0, 0)
                self._need_update = True

    def get_color(self):
        """Return the background color (RGB tuple).
        """
        return self._background_color

    def set_text_color(self, color):
        """Set text color (RGB tuple) used to write the texts.

        :param color: RGB color tuple
        :type color: tuple
        """
        assert len(color) == 3, "Length of 3 is required for RGB tuple"
        if color != self._text_color:
            self._text_color = color
            self._need_update = True

    def set_outlines(self, outlines=True):
        """Draw outlines for each rectangle available for drawing
        texts.

        :param outlines: enable / disable outlines
        :type outlines: bool
        """
        if outlines != self._show_outlines:
            self._show_outlines = outlines
            self._need_update = True

    def resize(self, screen):
        """Resize objects to fit to the screen.
        """
        if self._rect != screen.get_rect():
            self._rect = screen.get_rect()
            self._outlines = []

            if self._background_image:
                self._background = pictures.get_pygame_image(
                    self._background_image, (self._rect.width, self._rect.height), crop=True, color=None)
                self._background_color = pictures.get_pygame_main_color(self._background)

            overlay_name = "{}.png".format(self._name)
            if osp.isfile(pictures.get_filename(overlay_name)):
                self._overlay = pictures.get_pygame_image(
                    pictures.get_filename(overlay_name), (self._rect.width, self._rect.height), color=self._text_color, bg_color=self._background_color)

            self.resize_texts()
            self._need_update = True

    def resize_texts(self, rect=None, align='center'):
        """Update text surfaces.
        """
        self._texts = []
        text = get_translated_text(self._name)
        if text:
            self._write_text(text, rect, align)

    def paint(self, screen):
        """Paint and animate the surfaces on the screen.
        """
        if self._background:
            screen.blit(self._background, (0, 0))
        else:
            screen.fill(self._background_color)
        if self._overlay:
            screen.blit(self._overlay, self._overlay.get_rect(center=self._rect.center))
        for text_surface, pos in self._texts:
            screen.blit(text_surface, pos)
        for outline_surface, pos in self._outlines:
            screen.blit(outline_surface, pos)
        if self._logo_backgrounf_image:
            logo_file = pictures.get_pygame_image(self._logo_backgrounf_image, (self._rect.width * 0.70, self._rect.height * 1.07), vflip=False, color=None, crop=True)
            screen.blit(logo_file, (int(self._rect.width * 0.45), int(self._rect.height * -0.07)))
        if self._show_exit:
            exit_icon = pictures.get_pygame_image("exit.png",  (self._rect.width * 0.1, self._rect.height * 0.1), vflip=False, color=self._text_color)
            screen.blit(exit_icon, (int(self._rect.width * 0.01), int(self._rect.width * 0.01)))
        if self._show_back:
            back_icon = pictures.get_pygame_image("back.png",  (self._rect.width * 0.1, self._rect.height * 0.1), vflip=False, color=self._text_color)
            screen.blit(back_icon, (int(self._rect.width * 0.01), int(self._rect.height - (self._rect.width * 0.01) - back_icon.get_rect().height)))
            
        self._need_update = False

class IntroBackground(Background):

    def __init__(self):
        Background.__init__(self, "intro")
        self.camera_icon = None
        self.camera_icon_pos = None
        self._logo_backgrounf_image = "logo.png"
        self._show_exit = True

    def resize(self, screen):
        Background.resize(self, screen)
        if self._need_update:
            camera_icon_size = (self._rect.width * 0.65, self._rect.height * 0.65)
            self.camera_icon = pictures.get_pygame_image("camera.png",  camera_icon_size, vflip=False, color=self._text_color)    
            self.camera_icon_pos = (int(self._rect.width * 0.03), int(self._rect.height *0.2))
            
    def resize_texts(self):
        return None

    def paint(self, screen):
        Background.paint(self, screen)
        screen.blit(self.camera_icon, self.camera_icon_pos)

class IntroWithPrintBackground(IntroBackground):

    def __init__(self):
        IntroBackground.__init__(self)
        self.print_icon = None
        self.print_icon_pos = None
        self._logo_backgrounf_image = ""
        self._show_exit = True

    def __str__(self):
        """Return background final name.

        It is used in the main window to distinguish backgrounds in the cache
        thus each background string shall be uniq.
        """
        return "{}({})".format(self.__class__.__name__, "intro_print")

    def resize(self, screen):
        IntroBackground.resize(self, screen)
        if self._need_update:
            print_icon_size = (self._rect.width * 0.18, self._rect.height * 0.18)
            self.print_icon = pictures.get_pygame_image("print.png",  print_icon_size, vflip=False, color=self._text_color)    
            self.print_icon_pos = (int((self._rect.width * 0.99) - self.print_icon.get_rect().width),
                                   int(self._rect.height - (self._rect.width * 0.01) - self.print_icon.get_rect().height))
            
    def resize_texts(self):
        return None

    def paint(self, screen):
        IntroBackground.paint(self, screen)
        screen.blit(self.print_icon, self.print_icon_pos)

class ChooseBackground(Background):

    def __init__(self, choices):
        Background.__init__(self, "choose")
        self.choices = choices
        self.layout0 = None
        self.layout0_pos = None
        # self.layout1 = None
        # self.layout1_pos = None
        self._logo_backgrounf_image = ""
        self._show_back = True

    def resize(self, screen):
        Background.resize(self, screen)
        if self._need_update:
            size = (self._rect.width * 0.44, self._rect.height)
            # size = (self._rect.width * 0.75, self._rect.height)
            self.layout0  = pictures.get_pygame_image("layout{0}.png".format( self.choices[0]),  size, vflip=False, color=self._text_color)    
            self.layout0_pos = (int(self._rect.width * 0.03), self._rect.height * 0.5 - self.layout0.get_rect().height * 0.5)
            # self.layout0_pos = (int(self._rect.width * 0.125), self._rect.height * 0.5 - self.layout0.get_rect().height * 0.5)
            self.layout1  = pictures.get_pygame_image("layout{0}.png".format( self.choices[1]),  size, vflip=False, color=self._text_color)    
            self.layout1_pos = (int(self._rect.width * 0.53), self._rect.height * 0.5 - self.layout1.get_rect().height * 0.5)
            
    def resize_texts(self):
        return None

    def paint(self, screen):
        Background.paint(self, screen)
        screen.blit(self.layout0, self.layout0_pos)
        screen.blit(self.layout1, self.layout1_pos)

class CaptureBackground(Background):

    def __init__(self, preview_rect):
        Background.__init__(self, "capture")      
        self._logo_backgrounf_image = ""
        self._show_back = True
        self._preview_rect = preview_rect

    def resize(self, screen):
        Background.resize(self, screen)
        if self._need_update:
            size = (self._rect.width * 0.10, self._rect.height * 0.10)
            self.auto_shutter_icon  = pictures.get_pygame_image('auto_shutter_speed.png',  size, vflip=False, color=self._text_color)    
            self.auto_shutter_icon_pos = (int(self._rect.width * 0.02), int(self._rect.height * 0.02))
            self.add_shutter_icon  = pictures.get_pygame_image('add_shutter_speed.png',  size, vflip=False, color=self._text_color)    
            self.add_shutter_icon_pos = (int(self._rect.width * 0.02), int(self._rect.height * 0.35 - self.add_shutter_icon.get_rect().height))
            self.reduce_shutter_icon  = pictures.get_pygame_image('reduce_shutter_speed.png',  size, vflip=False, color=self._text_color)    
            self.reduce_shutter_icon_pos = (int(self._rect.width * 0.02), int(self._rect.height * 0.55))
            self.auto_iso_icon  = pictures.get_pygame_image('auto_iso.png',  size, vflip=False, color=self._text_color)    
            self.auto_iso_icon_pos = (int(self._rect.width * 0.98 - self.auto_iso_icon.get_rect().width), int(self._rect.height * 0.02))
            self.add_iso_icon  = pictures.get_pygame_image('add_iso.png',  size, vflip=False, color=self._text_color)    
            self.add_iso_icon_pos = (int(self._rect.width * 0.98 - self.add_iso_icon.get_rect().width), int(self._rect.height * 0.35 - self.add_iso_icon.get_rect().height))
            self.reduce_iso_icon  = pictures.get_pygame_image('reduce_iso.png',  size, vflip=False, color=self._text_color)    
            self.reduce_iso_icon_pos = (int(self._rect.width * 0.98 - self.reduce_iso_icon.get_rect().width), int(self._rect.height * 0.55))
            
            self.border_thickness = 15
            self.borders = pygame.Surface((self._preview_rect[2] + self.border_thickness * 2,self._preview_rect[3] + self.border_thickness * 2), pygame.SRCALPHA, 32)
            pygame.draw.rect(self.borders, pygame.Color(255,255,255), self.borders.get_rect(), self.border_thickness)
        
    def resize_texts(self):
        return None  
    
    def paint(self, screen):
        Background.paint(self, screen)
        screen.blit(self.auto_shutter_icon, self.auto_shutter_icon_pos)
        screen.blit(self.add_shutter_icon, self.add_shutter_icon_pos)
        screen.blit(self.reduce_shutter_icon, self.reduce_shutter_icon_pos)
        screen.blit(self.auto_iso_icon, self.auto_iso_icon_pos)
        screen.blit(self.add_iso_icon, self.add_iso_icon_pos)
        screen.blit(self.reduce_iso_icon, self.reduce_iso_icon_pos)
        screen.blit(self.borders, (self._preview_rect[0] - self.border_thickness, self._preview_rect[1] - self.border_thickness))
        
class ConfirmBackground(Background):

    def __init__(self):
        Background.__init__(self, "confirm")        
        self._logo_backgrounf_image = ""

    def resize(self, screen):
        Background.resize(self, screen)
        if self._need_update:
            size = (self._rect.width * 0.18, self._rect.height * 0.18)
            self.print_icon  = pictures.get_pygame_image('accept.png',  size, vflip=False, color=self._text_color)    
            self.print_icon_pos = (int((self._rect.width * 0.99) - self.print_icon.get_rect().width),
                                int((self._rect.height * 0.45 - self.print_icon.get_rect().height)))
            self.no_print_icon  = pictures.get_pygame_image('delete.png',  size, vflip=False, color=self._text_color)    
            self.no_print_icon_pos = (int((self._rect.width * 0.99) - self.no_print_icon.get_rect().width),
                                    int(self._rect.height * 0.55))

    def paint(self, screen):
        Background.paint(self, screen)
        screen.blit(self.print_icon, self.print_icon_pos)
        screen.blit(self.no_print_icon, self.no_print_icon_pos)

class ProcessingBackground(Background):

    def __init__(self):
        Background.__init__(self, "processing")
        self._logo_backgrounf_image = "logo.png"

    def resize_texts(self):
        """Update text surfaces.
        """
        rect = pygame.Rect(int(self._rect.width * 0.01), 
                           int(self._rect.height * 0.82),
                           int(self._rect.width * 0.5),
                           int(self._rect.height * 0.18))
        Background.resize_texts(self, rect, align='bottom-left')

class PrintBackground(Background):

    def __init__(self):
        Background.__init__(self, "print")        
        self._logo_backgrounf_image = ""

    def resize(self, screen):
        Background.resize(self, screen)
        if self._need_update:
            size = (self._rect.width * 0.18, self._rect.height * 0.18)
            self.print_icon  = pictures.get_pygame_image('print.png',  size, vflip=False, color=self._text_color)    
            self.print_icon_pos = (int((self._rect.width * 0.99) - self.print_icon.get_rect().width),
                                   int((self._rect.height * 0.45 - self.print_icon.get_rect().height)))
            self.no_print_icon  = pictures.get_pygame_image('no_print.png',  size, vflip=False, color=self._text_color)    
            self.no_print_icon_pos = (int((self._rect.width * 0.99) - self.no_print_icon.get_rect().width),
                                      int(self._rect.height * 0.55))

    def paint(self, screen):
        Background.paint(self, screen)
        screen.blit(self.print_icon, self.print_icon_pos)
        screen.blit(self.no_print_icon, self.no_print_icon_pos)

class OopsBackground(Background):

    def __init__(self):
        Background.__init__(self, "oops")
        self._logo_backgrounf_image = ""
        self._show_exit = True