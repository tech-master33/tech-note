import win32con
from core.app_base import SoftApp

try:
    import pygame
    HAS_PYGAME = True
except ImportError:
    HAS_PYGAME = False

class FMRadioApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        if HAS_PYGAME:
            pygame.mixer.init()
        self.stations = {
            "Jazz": "http://example.com/jazz.mp3",
            "Rock": "http://example.com/rock.mp3"
        }
        self.keys = list(self.stations.keys())
        self.index = 0

    def on_focus(self):
        self.speak("FM Radio. " + self.keys[self.index])

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if HAS_PYGAME:
                pygame.mixer.music.stop()
            self.exit_app()
        elif vk == win32con.VK_BACK or vk == win32con.VK_UP:
            self.index = (self.index - 1) % len(self.keys)
            self.speak(self.keys[self.index])
        elif vk == win32con.VK_SPACE or vk == win32con.VK_DOWN:
            self.index = (self.index + 1) % len(self.keys)
            self.speak(self.keys[self.index])
        elif vk == win32con.VK_RETURN:
            self.speak("Tuning to " + self.keys[self.index])
            if HAS_PYGAME:
                try:
                    pygame.mixer.music.load(self.stations[self.keys[self.index]])
                    pygame.mixer.music.play()
                except Exception as e:
                    self.speak("playback failed")
