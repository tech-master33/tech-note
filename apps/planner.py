import os
import json
import re
import time
import win32con
from core.app_base import SoftApp
from core.config import TECH_SOFT
from core.menu import MenuNode, MenuSystem

RECUR_OPTIONS = ["none", "daily", "weekly", "monthly"]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
STATE_LIST = 0
STATE_WEEK = 1


class PlannerApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.data_file = os.path.join(TECH_SOFT, 'planner.json')
        self.tasks = []
        self.menu = None
        self.input_mode = None
        self.input_buf = ""
        self.state = STATE_LIST
        self._week_day = 0
        self._last_notify = {}
        self.load_tasks()

    def load_tasks(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                self.tasks = [{"title": t} if isinstance(t, str) else t for t in data]
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = []

    def save_tasks(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.tasks, f)

    def _task_label(self, task):
        title = task.get("title", task) if isinstance(task, dict) else task
        parts = [title]
        recur = task.get("recur", "none") if isinstance(task, dict) else "none"
        if recur != "none":
            parts.append(f"({recur})")
        day = task.get("day", "") if isinstance(task, dict) else ""
        if day:
            parts.append(f"[{day}]")
        t = task.get("time", "") if isinstance(task, dict) else ""
        if t:
            parts.append(f"@{t}")
        return " ".join(parts)

    def _build_menu(self):
        root = MenuNode("Planner")
        if self.state == STATE_WEEK:
            root = MenuNode(f"Week View - {WEEKDAYS[self._week_day]}")
            for task in self.tasks:
                task_day = task.get("day", "") if isinstance(task, dict) else ""
                recur = task.get("recur", "none") if isinstance(task, dict) else "none"
                if task_day == WEEKDAYS[self._week_day] or (recur != "none" and not task_day):
                    root.add_child(MenuNode(self._task_label(task)))
                    root.children[-1].data = task
            root.add_child(MenuNode("Back to List", self._switch_to_list))
        else:
            root.add_child(MenuNode("Add Task", self._start_add_task, "n"))
            for task in self.tasks:
                root.add_child(MenuNode(self._task_label(task)))
                root.children[-1].data = task
            if not self.tasks:
                root.add_child(MenuNode("No tasks"))
            root.add_child(MenuNode("Export ICS", self._export_ics))
            root.add_child(MenuNode("Import ICS", self._import_ics))

        self.menu = MenuSystem(root, self.speak)

    def _start_add_task(self):
        self.input_mode = "add"
        self.input_buf = ""
        self.speak("Enter task name.")
        self.window.update_text("Task: ")

    def _switch_to_list(self):
        self.state = STATE_LIST
        self._build_menu()
        self.menu.announce_current()

    def _switch_to_week(self):
        self.state = STATE_WEEK
        self._week_day = time.localtime().tm_wday
        self._build_menu()
        self.menu.announce_current()

    def _cycle_recur(self):
        item = self.menu.get_current_item()
        if not item or not hasattr(item, 'data') or not item.data:
            self.speak("No task selected.")
            return
        tasks = [t for t in self.tasks if (isinstance(t, dict) and t.get("title", t) == item.data.get("title")) or t == item.data]
        for task in tasks:
            if not isinstance(task, dict):
                continue
            cur = task.get("recur", "none")
            idx = (RECUR_OPTIONS.index(cur) + 1) % len(RECUR_OPTIONS)
            task["recur"] = RECUR_OPTIONS[idx]
            self.speak(f"Recurrence: {RECUR_OPTIONS[idx]}")
        self.save_tasks()
        self._build_menu()

    def _set_task_day(self):
        item = self.menu.get_current_item()
        if not item or not hasattr(item, 'data') or not item.data:
            self.speak("No task selected.")
            return
        tasks = [t for t in self.tasks if (isinstance(t, dict) and t.get("title", t) == item.data.get("title")) or t == item.data]
        if not tasks:
            return
        task = tasks[0]
        if not isinstance(task, dict):
            return
        cur = task.get("day", "")
        if cur in WEEKDAYS:
            idx = (WEEKDAYS.index(cur) + 1) % len(WEEKDAYS)
        else:
            idx = 0
        task["day"] = WEEKDAYS[idx]
        self.speak(f"Day: {WEEKDAYS[idx]}")
        self.save_tasks()
        self._build_menu()

    def _set_task_time(self):
        item = self.menu.get_current_item()
        if not item or not hasattr(item, 'data') or not item.data:
            self.speak("No task selected.")
            return
        self.input_mode = "set_time"
        self.input_buf = ""
        self.speak("Enter time (HH:MM).")
        self.window.update_text("Time: ")

    def _apply_time(self):
        val = self.input_buf.strip()
        if not re.match(r'^\d{1,2}:\d{2}$', val):
            self.speak("Invalid time. Use HH:MM format.")
            return
        item = self.menu.get_current_item()
        if not item or not hasattr(item, 'data') or not item.data:
            return
        tasks = [t for t in self.tasks if (isinstance(t, dict) and t.get("title", t) == item.data.get("title")) or t == item.data]
        for task in tasks:
            if isinstance(task, dict):
                task["time"] = val
        self.save_tasks()
        self.input_mode = None
        self.speak(f"Time set: {val}")
        self._build_menu()
        self.menu.announce_current()

    def _export_ics(self):
        path = os.path.join(TECH_SOFT, "planner_export.ics")
        try:
            lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TechSoft//Planner//EN"]
            for task in self.tasks:
                title = task.get("title", task) if isinstance(task, dict) else task
                recur = task.get("recur", "none") if isinstance(task, dict) else "none"
                day = task.get("day", "") if isinstance(task, dict) else ""
                t = task.get("time", "1200") if isinstance(task, dict) else "1200"
                lines.append("BEGIN:VEVENT")
                lines.append(f"SUMMARY:{title}")
                lines.append(f"DTSTART;VALUE=DATE:20250101T{t.replace(':', '')}00")
                if recur == "daily":
                    lines.append("RRULE:FREQ=DAILY")
                elif recur == "weekly":
                    lines.append("RRULE:FREQ=WEEKLY")
                elif recur == "monthly":
                    lines.append("RRULE:FREQ=MONTHLY")
                lines.append("END:VEVENT")
            lines.append("END:VCALENDAR")
            with open(path, 'w') as f:
                f.write("\n".join(lines))
            self.speak(f"Exported {len(self.tasks)} events to planner_export.ics")
        except Exception:
            self.speak("Export failed.")

    def _import_ics(self):
        path = os.path.join(TECH_SOFT, "planner_export.ics")
        if not os.path.exists(path):
            self.speak("No planner_export.ics found.")
            return
        try:
            with open(path, 'r') as f:
                content = f.read()
            imported = 0
            for event in re.finditer(r'BEGIN:VEVENT(.*?)END:VEVENT', content, re.DOTALL):
                block = event.group(1)
                m = re.search(r'SUMMARY:(.*)', block)
                title = m.group(1).strip() if m else "Untitled"
                task = {"title": title, "recur": "none", "day": "", "time": ""}
                rr = re.search(r'RRULE:FREQ=(\w+)', block)
                if rr:
                    freq = rr.group(1).lower()
                    if freq in ("daily", "weekly", "monthly"):
                        task["recur"] = freq
                if not any(t.get("title") == title if isinstance(t, dict) else t == title for t in self.tasks):
                    self.tasks.append(task)
                    imported += 1
            self.save_tasks()
            self.speak(f"Imported {imported} events.")
            self._build_menu()
        except Exception:
            self.speak("Import failed.")

    def _check_alarms(self):
        now = time.localtime()
        current = f"{now.tm_hour:02d}:{now.tm_min:02d}"
        for task in self.tasks:
            if not isinstance(task, dict):
                continue
            t = task.get("time", "")
            if t and t == current:
                key = f"{task.get('title', '')}_{t}"
                if self._last_notify.get(key) != current:
                    self._last_notify[key] = current
                    self.speak(f"Alarm: {task.get('title', '')} at {t}")

    def on_focus(self):
        self._check_alarms()
        self._build_menu()
        item = self.menu.get_current_item()
        self.speak("Planner. " + item.title)
        self.window.update_text("Planner: " + item.title)

    def on_key(self, vk):
        if self.input_mode:
            self._handle_input(vk)
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_F5:
            if self.state == STATE_WEEK:
                self._switch_to_list()
            else:
                self._switch_to_week()
            return

        if vk == win32con.VK_F6:
            self._cycle_recur()
            return

        if vk == win32con.VK_F7:
            self._set_task_day()
            return

        if vk == win32con.VK_F8:
            self._set_task_time()
            return

        if vk == win32con.VK_F9:
            self._export_ics()
            return

        if vk == win32con.VK_F10:
            self._import_ics()
            return

        if vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif vk == win32con.VK_DELETE:
            self._delete_task()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Planner: " + item.title)

    def _handle_input(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_mode = None
            self.speak("Cancelled.")
            self.on_focus()
            return

        if vk == win32con.VK_RETURN:
            if self.input_mode == "set_time":
                self._apply_time()
                return
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            self.tasks.append({"title": val, "recur": "none", "day": "", "time": ""})
            self.save_tasks()
            self.input_mode = None
            self.speak(f"Added: {val}")
            self.on_focus()
            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                label = "Time" if self.input_mode == "set_time" else "Task"
                self.window.update_text(f"{label}: {self.input_buf}")
            return

        ch = self._vk_to_char(vk)
        if ch:
            self.input_buf += ch
            label = "Time" if self.input_mode == "set_time" else "Task"
            self.window.update_text(f"{label}: {self.input_buf}")

    def _delete_task(self):
        item = self.menu.get_current_item()
        if not item or item.title in ("No tasks", "Add Task", "Export ICS", "Import ICS", "Back to List"):
            return
        idx = self.menu.current_index if hasattr(self.menu, 'current_index') else -1
        if idx < 0 or idx >= len(self.tasks):
            if self.state == STATE_WEEK:
                return
            return
        if self.state == STATE_LIST:
            base_idx = 1
            task_idx = idx - base_idx
            if task_idx < 0 or task_idx >= len(self.tasks):
                return
            task = self.tasks[task_idx]
            del self.tasks[task_idx]
        else:
            return
        self.save_tasks()
        title = task.get("title", task) if isinstance(task, dict) else task
        self.speak(f"Deleted: {title}")
        self._build_menu()
        if self.menu.get_current_item():
            self.window.update_text("Planner: " + self.menu.get_current_item().title)
        else:
            self.window.update_text("Planner: Empty")

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.state == STATE_WEEK:
                self._week_day = (self._week_day + 1) % 7
                self._build_menu()
                self.menu.announce_current()
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Planner: " + item.title)
    def get_help_text(self):
        if self.state == STATE_WEEK:
            return f"Week View - {WEEKDAYS[self._week_day]}. Space for next day. F5 for list. Delete to remove. Escape to exit."
        return "Planner. Space for next, Backspace for previous. Enter to select. F5 week view, F6 recurrence, F7 day, F8 time, F9 export ICS, F10 import ICS. Delete to remove. Escape to exit."
