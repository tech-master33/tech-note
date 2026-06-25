from . import translator
from . import discover
from .humanware_serial import TouchPlusDisplay
from .monarch_terminal import MonarchDisplay


class BrailleManager:
    _plugin_braille_displays = {}

    def __init__(self, grade=2):
        self.grade = grade
        self.display = None
        self._active = False

    @classmethod
    def get_plugin_displays(cls):
        if not cls._plugin_braille_displays:
            try:
                from core.plugin_manager import get_plugin_manager
                pm = get_plugin_manager()
                pm.scan()
                cls._plugin_braille_displays = pm.get_braille_plugins()
            except Exception:
                pass
        return cls._plugin_braille_displays

    def set_display_by_name(self, name):
        if name == "Off":
            self.display = None
            self._active = False
            return True
        if name == "Humanware":
            found = discover.auto_detect()
            if found["touch_plus"]:
                self.display = TouchPlusDisplay(found["touch_plus"])
                self._active = self.display.is_connected()
                return self._active
            return False
        if name == "Monarch":
            found = discover.auto_detect()
            if found["monarch"]:
                self.display = MonarchDisplay(found["monarch"])
                self._active = self.display.is_connected()
                return self._active
            return False
        plugins = self.get_plugin_displays()
        if name in plugins:
            try:
                plugin = plugins[name]
                if not getattr(plugin, '_braille_initialized', False):
                    plugin.initialize()
                    plugin._braille_initialized = True
                self.display = plugin
                self._active = True
                return True
            except Exception:
                pass
        return False

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
        braille = translator.translate(text)
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
