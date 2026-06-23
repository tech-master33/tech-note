from . import translator
from . import discover
from .humanware_serial import TouchPlusDisplay
from .monarch_terminal import MonarchDisplay

class BrailleManager:
    def __init__(self, grade=2):
        self.grade = grade
        self.display = None
        self._active = False

    def auto_connect(self):
        found = discover.auto_detect()
        if found["touch_plus"]:
            self.display = TouchPlusDisplay(found["touch_plus"])
        elif found["monarch"]:
            self.display = MonarchDisplay(found["monarch"])
        if self.display and self.display.is_connected():
            self._active = True
        return self._active

    def is_active(self):
        return self._active and self.display and self.display.is_connected()

    def display_braille(self, text, cursor_pos=None):
        if not self.is_active():
            return
        braille = translator.translate(text, self.grade)
        if cursor_pos is not None:
            self.display.display_with_cursor(braille, cursor_pos)
        else:
            self.display.display_text(braille)

    def set_grade(self, grade):
        if grade in (1, 2):
            self.grade = grade

    def close(self):
        if self.display:
            self.display.close()
            self.display = None
        self._active = False
