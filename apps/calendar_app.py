import calendar
import datetime
import json
import os
import win32con
from core.app_base import SoftApp

EVENTS_FILE = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'calendar_events.json')


class CalendarApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        now = datetime.datetime.now()
        self.year = now.year
        self.month = now.month
        self.today = now.day
        self.cursor_day = now.day
        self.state = "view"
        self.menu_cursor = 0
        self.events = self._load_events()
        self.input_buf = ""
        self.view_cursor = 0

    def _load_events(self):
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_events(self):
        os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
        with open(EVENTS_FILE, 'w') as f:
            json.dump(self.events, f)

    def _get_event_key(self, day):
        return f"{self.year}-{self.month:02d}-{day:02d}"

    def _get_month_name(self):
        return calendar.month_name[self.month]

    def _render(self):
        if self.state == "input":
            return self._render_input()

        lines = []
        lines.append(f"{self._get_month_name()} {self.year}")
        lines.append("")

        cal = calendar.monthcalendar(self.year, self.month)
        lines.append(" Mon  Tue  Wed  Thu  Fri  Sat  Sun")
        lines.append(" " + "-----" * 7)

        for week in cal:
            parts = []
            for day in week:
                if day == 0:
                    parts.append("     ")
                elif day == self.cursor_day:
                    parts.append(f" [{day:2d}]")
                elif day == self.today and self.month == datetime.datetime.now().month and self.year == datetime.datetime.now().year:
                    parts.append(f" *{day:2d} ")
                else:
                    parts.append(f"  {day:2d} ")
            lines.append(" ".join(parts))

        lines.append("")

        if self.cursor_day:
            key = self._get_event_key(self.cursor_day)
            day_events = self.events.get(key, [])
            if day_events:
                lines.append(f"Events for {self._get_month_name()} {self.cursor_day}:")
                for e in day_events:
                    lines.append(f"  - {e}")
            else:
                lines.append(f"No events for {self._get_month_name()} {self.cursor_day}.")

        lines.append("")
        lines.append("Arrows: navigate. Enter: options. Escape: exit.")
        return "\n".join(lines)

    def _render_input(self):
        lines = ["Add Event", ""]
        lines.append(f"Date: {self._get_month_name()} {self.cursor_day}, {self.year}")
        lines.append("")
        lines.append(f"Event: {self.input_buf}_")
        lines.append("")
        lines.append("Type event name. Enter to save. Escape to cancel.")
        return "\n".join(lines)

    def _show_options(self):
        self.state = "options"
        self.menu_cursor = 0

    def _render_options(self):
        key = self._get_event_key(self.cursor_day)
        day_events = self.events.get(key, [])

        lines = [f"{self._get_month_name()} {self.cursor_day}, {self.year}", ""]
        options = ["Add Event"]
        for e in day_events:
            options.append(f"Delete: {e}")
        options.append("Back")

        for i, opt in enumerate(options):
            prefix = ">" if i == self.menu_cursor else " "
            lines.append(f"{prefix} {opt}")

        return "\n".join(lines)

    def _add_event(self):
        self.state = "input"
        self.input_buf = ""
        self.speak("Enter event name.")

    def _save_event(self):
        text = self.input_buf.strip()
        if not text:
            self.speak("Cannot be empty.")
            return
        key = self._get_event_key(self.cursor_day)
        if key not in self.events:
            self.events[key] = []
        self.events[key].append(text)
        self._save_events()
        self.speak(f"Event added: {text}")
        self.state = "view"
        self.window.update_text(self._render())

    def _delete_event(self, idx):
        key = self._get_event_key(self.cursor_day)
        if key in self.events and idx < len(self.events[key]):
            removed = self.events[key].pop(idx)
            if not self.events[key]:
                del self.events[key]
            self._save_events()
            self.speak(f"Deleted: {removed}")
        self.state = "view"
        self.window.update_text(self._render())

    def _change_month(self, delta):
        self.month += delta
        if self.month > 12:
            self.month = 1
            self.year += 1
        elif self.month < 1:
            self.month = 12
            self.year -= 1
        self.cursor_day = 1
        self.speak(f"{self._get_month_name()} {self.year}")

    def on_focus(self):
        now = datetime.datetime.now()
        self.year = now.year
        self.month = now.month
        self.today = now.day
        self.cursor_day = now.day
        self.state = "view"
        self.events = self._load_events()
        self.speak(f"Calendar. {self._get_month_name()} {self.year}. Today is {self.today}.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if self.state == "input":
            if vk == win32con.VK_ESCAPE:
                self.state = "view"
                self.speak("Cancelled.")
                self.window.update_text(self._render())
            elif vk == win32con.VK_RETURN:
                self._save_event()
            elif vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.window.update_text(self._render())
            elif 0x20 <= vk <= 0x7E:
                self.input_buf += chr(vk)
                self.window.update_text(self._render())
            return

        if self.state == "options":
            key = self._get_event_key(self.cursor_day)
            day_events = self.events.get(key, [])
            option_count = 1 + len(day_events) + 1

            if vk == win32con.VK_ESCAPE:
                self.state = "view"
                self.window.update_text(self._render())
            elif vk == win32con.VK_UP:
                self.menu_cursor = (self.menu_cursor - 1) % option_count
                self.window.update_text(self._render())
            elif vk == win32con.VK_DOWN:
                self.menu_cursor = (self.menu_cursor + 1) % option_count
                self.window.update_text(self._render())
            elif vk == win32con.VK_RETURN:
                if self.menu_cursor == 0:
                    self._add_event()
                elif self.menu_cursor == option_count - 1:
                    self.state = "view"
                    self.window.update_text(self._render())
                else:
                    self._delete_event(self.menu_cursor - 1)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        days_in_month = calendar.monthrange(self.year, self.month)[1]

        if vk == win32con.VK_LEFT:
            self.cursor_day = max(1, self.cursor_day - 1)
        elif vk == win32con.VK_RIGHT:
            self.cursor_day = min(days_in_month, self.cursor_day + 1)
        elif vk == win32con.VK_UP:
            self.cursor_day = max(1, self.cursor_day - 7)
        elif vk == win32con.VK_DOWN:
            self.cursor_day = min(days_in_month, self.cursor_day + 7)
        elif vk == win32con.VK_PAGEUP:
            self._change_month(-1)
        elif vk == win32con.VK_PAGEDOWN:
            self._change_month(1)
        elif vk == win32con.VK_RETURN:
            self._show_options()

        self.window.update_text(self._render())

    def get_help_text(self):
        return "Calendar. Arrows to navigate days. PageUp/PageDown to change month. Enter for options. Add and view events."
