import calendar
import datetime
import json
import os
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

EVENTS_FILE = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'calendar_events.json')


class CalendarApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        now = datetime.datetime.now()
        self.year = now.year
        self.month = now.month
        self.today = now.day
        self.cursor_day = now.day
        self.state = "menu"
        self.events = self._load_events()
        self.input_buf = ""
        self.menu = None
        self._build_menu()

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

    def _build_menu(self):
        root = MenuNode("Calendar")
        root.add_child(MenuNode(f"{self._get_month_name()} {self.year}"))
        days_in_month = calendar.monthrange(self.year, self.month)[1]
        for day in range(1, days_in_month + 1):
            key = self._get_event_key(day)
            day_events = self.events.get(key, [])
            marker = " * " if day == self.today and self.month == datetime.datetime.now().month and self.year == datetime.datetime.now().year else ""
            event_tag = f" ({len(day_events)} events)" if day_events else ""
            label = f"{day}{marker}{event_tag}"
            root.add_child(MenuNode(label, lambda d=day: self._select_day(d)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _select_day(self, day):
        self.cursor_day = day
        self.state = "options"
        self._build_options_menu()

    def _build_options_menu(self):
        key = self._get_event_key(self.cursor_day)
        day_events = self.events.get(key, [])

        root = MenuNode(f"{self._get_month_name()} {self.cursor_day}")
        root.add_child(MenuNode("Add Event", self._add_event))
        for i, e in enumerate(day_events):
            root.add_child(MenuNode(f"Delete: {e}", lambda idx=i: self._delete_event(idx)))
        root.add_child(MenuNode("Back", self._back_to_calendar))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _back_to_calendar(self):
        self.state = "menu"
        self._build_menu()
        self.menu.announce_current()

    def _add_event(self):
        self.state = "input"
        self.input_buf = ""
        self.speak("Enter event name.")
        self.window.update_text("Event: ")

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
        self._build_options_menu()

    def _delete_event(self, idx):
        key = self._get_event_key(self.cursor_day)
        if key in self.events and idx < len(self.events[key]):
            removed = self.events[key].pop(idx)
            if not self.events[key]:
                del self.events[key]
            self._save_events()
            self.speak(f"Deleted: {removed}")
        self._build_options_menu()

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
        self._build_menu()

    def on_focus(self):
        now = datetime.datetime.now()
        self.year = now.year
        self.month = now.month
        self.today = now.day
        self.cursor_day = now.day
        self.state = "menu"
        self.events = self._load_events()
        self._build_menu()
        self.speak(f"Calendar. {self._get_month_name()} {self.year}. Today is {self.today}.")
        self.window.update_text(f"{self._get_month_name()} {self.year}")

    def on_key(self, vk):
        if self.state == "input":
            if vk == win32con.VK_ESCAPE:
                self.state = "options"
                self.speak("Cancelled.")
                self._build_options_menu()
            elif vk == win32con.VK_RETURN:
                self._save_event()
            elif vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.window.update_text(f"Event: {self.input_buf}")
            elif 0x20 <= vk <= 0x7E:
                self.input_buf += chr(vk)
                self.window.update_text(f"Event: {self.input_buf}")
            return

        if vk == win32con.VK_ESCAPE:
            if self.state == "options":
                self._back_to_calendar()
            else:
                self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text(item.title)

    def get_help_text(self):
        return "Calendar. Browse days, add and view events. Space for next, Backspace for previous. Enter to select."
