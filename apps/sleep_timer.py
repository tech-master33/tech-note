import threading
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.background_audio import background_audio


class SleepTimer(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._timer_thread = None
        self._remaining = 0
        self._active = False
        self._action = "fade"
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Sleep Timer")
        if self._active:
            root.add_child(MenuNode(f"Running: {self._format_time(self._remaining)}", None))
            root.add_child(MenuNode("Cancel Timer", self._cancel))
        else:
            root.add_child(MenuNode("5 minutes", lambda: self._start_timer(5)))
            root.add_child(MenuNode("10 minutes", lambda: self._start_timer(10)))
            root.add_child(MenuNode("15 minutes", lambda: self._start_timer(15)))
            root.add_child(MenuNode("30 minutes", lambda: self._start_timer(30)))
            root.add_child(MenuNode("60 minutes", lambda: self._start_timer(60)))
            root.add_child(MenuNode("90 minutes", lambda: self._start_timer(90)))
            root.add_child(MenuNode("Custom", self._custom_time))
            root.add_child(MenuNode(f"Action: {self._action}", self._cycle_action))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"

    def _cycle_action(self):
        actions = ["fade", "stop", "shutdown"]
        idx = actions.index(self._action) if self._action in actions else 0
        self._action = actions[(idx + 1) % len(actions)]
        self.speak(f"Action: {self._action}")
        self._build_menu()
        self.menu.announce_current()

    def _custom_time(self):
        self.speak("Enter minutes.")
        self._input_mode = "custom"
        self._input_text = ""

    def _start_timer(self, minutes):
        self._remaining = minutes * 60
        self._active = True
        self.speak(f"Timer set for {minutes} minutes. Action: {self._action}.")
        if self._timer_thread and self._timer_thread.is_alive():
            self._cancel()
        self._timer_thread = threading.Thread(target=self._run_timer, daemon=True)
        self._timer_thread.start()
        self._build_menu()
        self.menu.announce_current()

    def _run_timer(self):
        while self._remaining > 0 and self._active:
            time.sleep(1)
            self._remaining -= 1
        if self._active:
            self._do_action()
        self._active = False

    def _do_action(self):
        if self._action == "fade":
            self.speak("Timer complete. Fading audio.")
            background_audio.fade_out(duration=5)
        elif self._action == "stop":
            background_audio.stop()
            self.speak("Timer complete. Audio stopped.")
        elif self._action == "shutdown":
            background_audio.stop()
            self.speak("Timer complete. Shutting down.")
            import sys
            sys.exit()

    def _cancel(self):
        self._active = False
        self._remaining = 0
        self.speak("Timer cancelled.")
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if self._active:
            self.speak(f"Sleep Timer running. {self._format_time(self._remaining)} remaining.")
        else:
            self._build_menu()
            item = self.menu.get_current_item()
            self.speak("Sleep Timer. " + (item.title if item else ""))

    def on_key(self, vk):
        if getattr(self, '_input_mode', None):
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                try:
                    mins = int(self._input_text.strip())
                    if mins > 0:
                        self._input_mode = None
                        self._start_timer(mins)
                        return
                except:
                    pass
                self.speak("Invalid number.")
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(self._input_text)
                return
            ch = self._vk_to_char(vk)
            if ch and ch.isdigit():
                self._input_text += ch
                self.window.update_text(f"{self._input_text} minutes")
            return
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        else:
            self._handle_first_letter_nav(vk, self.menu)
        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        return "Sleep Timer. Set audio to fade or stop after a set time. Space next, Backspace previous. Escape exit."
