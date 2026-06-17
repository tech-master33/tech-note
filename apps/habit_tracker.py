import os
import json
import datetime
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

HABITS_FILE = os.path.join(TECH_SOFT, "habits.json")


class HabitTracker(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.habits = self._load_habits()
        self._build_menu()

    def _load_habits(self):
        if os.path.exists(HABITS_FILE):
            try:
                with open(HABITS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_habits(self):
        try:
            os.makedirs(os.path.dirname(HABITS_FILE), exist_ok=True)
            with open(HABITS_FILE, 'w') as f:
                json.dump(self.habits, f, indent=2)
        except:
            pass

    def _today(self):
        return datetime.date.today().isoformat()

    def _build_menu(self):
        root = MenuNode("Habit Tracker")
        today = self._today()
        root.add_child(MenuNode("New Habit", self._new_habit))
        if self.habits:
            done = sum(1 for h in self.habits if today in h.get("done_dates", []))
            root.add_child(MenuNode(f"Today: {done}/{len(self.habits)} completed"))
            for i, habit in enumerate(self.habits):
                done_today = today in habit.get("done_dates", [])
                streak = self._get_streak(habit)
                status = "Done" if done_today else "Not done"
                root.add_child(MenuNode(f"{habit['name']} - {status} - Streak: {streak} days", lambda idx=i: self._manage_habit(idx)))
            root.add_child(MenuNode("View Stats", self._view_stats))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _get_streak(self, habit):
        dates = sorted(habit.get("done_dates", []), reverse=True)
        if not dates:
            return 0
        streak = 0
        check = datetime.date.today()
        for d in dates:
            if d == check.isoformat():
                streak += 1
                check -= datetime.timedelta(days=1)
            else:
                break
        return streak

    def _new_habit(self):
        self.speak("New habit. Type the name, press Enter when done.")
        self.window.update_text("Habit: ")
        self._input_mode = "name"
        self._input_text = ""
        self._editing_habit = None

    def _save_new_habit(self):
        name = self._input_text.strip()
        if not name:
            name = "Unnamed Habit"
        habit = {"name": name, "done_dates": [], "created": self._today()}
        self.habits.append(habit)
        self._save_habits()
        self.speak(f"Habit {name} created.")
        self._input_mode = None
        self._build_menu()
        self.menu.announce_current()

    def _manage_habit(self, idx):
        if idx >= len(self.habits):
            return
        habit = self.habits[idx]
        today = self._today()
        done_today = today in habit.get("done_dates", [])
        streak = self._get_streak(habit)
        root = MenuNode(habit["name"])
        if done_today:
            root.add_child(MenuNode("Mark as Not Done", lambda: self._toggle_done(idx)))
        else:
            root.add_child(MenuNode("Mark as Done", lambda: self._toggle_done(idx)))
        root.add_child(MenuNode(f"Streak: {streak} days"))
        root.add_child(MenuNode("Rename", lambda: self._rename_habit(idx)))
        root.add_child(MenuNode("Delete", lambda: self._delete_habit(idx)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _toggle_done(self, idx):
        habit = self.habits[idx]
        today = self._today()
        if "done_dates" not in habit:
            habit["done_dates"] = []
        if today in habit["done_dates"]:
            habit["done_dates"].remove(today)
            self.speak(f"{habit['name']} marked as not done.")
        else:
            habit["done_dates"].append(today)
            streak = self._get_streak(habit)
            self.speak(f"{habit['name']} done! Streak: {streak} days.")
        self._save_habits()
        self._manage_habit(idx)

    def _rename_habit(self, idx):
        self._input_mode = "rename"
        self._input_text = ""
        self._editing_habit = idx
        self.speak("Type new name, press Enter when done.")
        self.window.update_text("Name: ")

    def _save_rename(self):
        name = self._input_text.strip()
        if name:
            self.habits[self._editing_habit]["name"] = name
            self._save_habits()
            self.speak(f"Renamed to {name}.")
        self._input_mode = None
        self._editing_habit = None
        self._manage_habit(self._editing_habit if self._editing_habit is not None else 0)

    def _delete_habit(self, idx):
        name = self.habits[idx]["name"]
        self.habits.pop(idx)
        self._save_habits()
        self.speak(f"{name} deleted.")
        self._build_menu()
        self.menu.announce_current()

    def _view_stats(self):
        if not self.habits:
            self.speak("No habits yet.")
            return
        today = datetime.date.today()
        lines = []
        for habit in self.habits:
            dates = habit.get("done_dates", [])
            streak = self._get_streak(habit)
            total = len(dates)
            lines.append(f"{habit['name']}: {total} times, streak {streak} days")
        stats = ". ".join(lines)
        self.speak(f"Stats: {stats}")
        self.window.update_text(stats)

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def on_focus(self):
        if getattr(self, '_input_mode', None):
            self.window.update_text(f"{self._input_text}")
        else:
            today = self._today()
            done = sum(1 for h in self.habits if today in h.get("done_dates", []))
            self.speak(f"Habit Tracker. {done} of {len(self.habits)} done today.")
            self.window.update_text(f"{done}/{len(self.habits)} today")

    def on_key(self, vk):
        if getattr(self, '_input_mode', None):
            if vk == win32con.VK_ESCAPE:
                self._input_mode = None
                self._build_menu()
                self.menu.announce_current()
                return
            if vk == win32con.VK_RETURN:
                if self._input_mode == "name":
                    self._save_new_habit()
                elif self._input_mode == "rename":
                    self._save_rename()
                return
            if vk == win32con.VK_BACK:
                self._input_text = self._input_text[:-1]
                self.window.update_text(self._input_text if self._input_text else " ")
                return
            ch = self._vk_to_char(vk)
            if ch:
                self._input_text += ch
                self.window.update_text(self._input_text)
            return

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
        if getattr(self, '_input_mode', None):
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if getattr(self, '_input_mode', None):
            return "Type text. Enter to confirm, Escape to cancel."
        return "Habit Tracker. Track daily habits and streaks. Space for next, Backspace for previous."
