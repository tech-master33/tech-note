import threading
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class PomodoroTimer(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._work_min = 25
        self._break_min = 5
        self._remaining = 0
        self._active = False
        self._phase = "idle"
        self._timer_thread = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Pomodoro Timer")
        status = "Idle" if not self._active else f"{self._phase}: {self._format_time(self._remaining)}"
        root.add_child(MenuNode(f"Status: {status}"))
        if not self._active:
            root.add_child(MenuNode("Start Focus", self._start_focus))
            root.add_child(MenuNode(f"Work: {self._work_min} min", self._set_work))
            root.add_child(MenuNode(f"Break: {self._break_min} min", self._set_break))
        else:
            root.add_child(MenuNode("Stop", self._stop))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def _start_focus(self):
        self._remaining = self._work_min * 60
        self._active = True
        self._phase = "Focus"
        self.speak(f"Focus session started. {self._work_min} minutes.")
        self._timer_thread = threading.Thread(target=self._run, daemon=True)
        self._timer_thread.start()
        self._build_menu()
        self.menu.announce_current()

    def _run(self):
        while self._remaining > 0 and self._active:
            time.sleep(1)
            self._remaining -= 1
        if self._active:
            self._phase_complete()

    def _phase_complete(self):
        if self._phase == "Focus":
            self.speak("Focus session complete! Time for a break.")
            self._remaining = self._break_min * 60
            self._phase = "Break"
            self._timer_thread = threading.Thread(target=self._run, daemon=True)
            self._timer_thread.start()
        else:
            self.speak("Break over. Ready to focus again.")
            self._active = False
            self._phase = "idle"
        self._build_menu()
        self.menu.announce_current()

    def _stop(self):
        self._active = False
        self._phase = "idle"
        self._remaining = 0
        self.speak("Timer stopped.")
        self._build_menu()
        self.menu.announce_current()

    def _set_work(self):
        self._input_mode = "work"
        self._input_text = str(self._work_min)
        self.speak(f"Work minutes ({self._work_min}). Enter new value.")
        self.window.update_text(f"Work minutes: ")

    def _set_break(self):
        self._input_mode = "break"
        self._input_text = str(self._break_min)
        self.speak(f"Break minutes ({self._break_min}). Enter new value.")
        self.window.update_text(f"Break minutes: ")

    def on_focus(self):
        if self._active:
            self.speak(f"Pomodoro. {self._phase}: {self._format_time(self._remaining)}.")
        else:
            self._build_menu()
            item = self.menu.get_current_item()
            self.speak("Pomodoro Timer. " + (item.title if item else ""))

    def on_key(self, vk):
        if getattr(self, '_input_mode', None):
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                try:
                    v = int(self._input_text.strip())
                    if v > 0:
                        if self._input_mode == "work":
                            self._work_min = v
                            self.speak(f"Work set to {v} minutes.")
                        else:
                            self._break_min = v
                            self.speak(f"Break set to {v} minutes.")
                except:
                    self.speak("Invalid.")
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(self._input_text)
                return
            if 0x30 <= vk <= 0x39:
                self._input_text += chr(vk)
                self.window.update_text(self._input_text)
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
        return "Pomodoro Timer. Focus for 25 minutes, then take a break. Space next, Backspace previous. Escape exit."
