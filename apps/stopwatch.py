import time
import threading
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class StopwatchApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.running = False
        self.elapsed = 0.0
        self.start_time = 0.0
        self.laps = []
        self.timer_thread = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Stopwatch")
        root.add_child(MenuNode(self._format_time(self.elapsed)))
        if self.running:
            root.add_child(MenuNode("Stop", self._stop))
            root.add_child(MenuNode("Lap", self._lap))
        else:
            root.add_child(MenuNode("Start", self._start))
        if self.laps:
            root.add_child(MenuNode(f"Laps ({len(self.laps)})", self._show_laps))
        if self.elapsed > 0 and not self.running:
            root.add_child(MenuNode("Reset", self._reset))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _format_time(self, t):
        mins = int(t) // 60
        secs = int(t) % 60
        ms = int((t - int(t)) * 100)
        return f"{mins:02d}:{secs:02d}.{ms:02d}"

    def _start(self):
        if not self.running:
            self.running = True
            self.start_time = time.time() - self.elapsed
            self.timer_thread = threading.Thread(target=self._tick, daemon=True)
            self.timer_thread.start()
            self.speak("Stopwatch started.")
            self._build_menu()
            self.window.update_text(self._format_time(self.elapsed))

    def _stop(self):
        self.running = False
        self.elapsed = time.time() - self.start_time
        self.speak(f"Stopped at {self._format_time(self.elapsed)}.")
        self._build_menu()

    def _reset(self):
        self.running = False
        self.elapsed = 0.0
        self.laps = []
        self.speak("Reset.")
        self._build_menu()
        self.window.update_text("00:00.00")

    def _lap(self):
        if self.running:
            current = time.time() - self.start_time
            lap_num = len(self.laps) + 1
            lap_time = current - (self.laps[-1] if self.laps else 0)
            self.laps.append(current)
            self.speak(f"Lap {lap_num}: {self._format_time(lap_time)}")
            self.window.update_text(f"Lap {lap_num}: {self._format_time(lap_time)}")

    def _show_laps(self):
        if not self.laps:
            self.speak("No laps recorded.")
            return

        root = MenuNode("Laps")
        prev = 0
        for i, lap in enumerate(self.laps):
            lap_time = lap - prev
            prev = lap
            root.add_child(MenuNode(f"Lap {i+1}: {self._format_time(lap_time)}"))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _tick(self):
        while self.running:
            self.elapsed = time.time() - self.start_time
            self.window.update_text(self._format_time(self.elapsed))
            time.sleep(0.05)

    def on_focus(self):
        status = "running" if self.running else "stopped"
        self.speak(f"Stopwatch. {self._format_time(self.elapsed)}. {status}.")
        self.window.update_text(self._format_time(self.elapsed))

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

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
        return "Stopwatch. Start, Stop, Lap, Reset. Space for next, Backspace for previous. Enter to select."
