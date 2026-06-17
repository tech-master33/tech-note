import time
import datetime
import threading
import os
import json
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode
from core.config import TECH_SOFT

ALARMS_FILE = os.path.join(TECH_SOFT, "alarms.json")


class AlarmClock(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.alarms = self._load_alarms()
        self.active_thread = None
        self.running = True
        self.ringing_alarm = None
        self._start_checker()
        self._build_menu()

    def _load_alarms(self):
        if os.path.exists(ALARMS_FILE):
            try:
                with open(ALARMS_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []

    def _save_alarms(self):
        try:
            os.makedirs(os.path.dirname(ALARMS_FILE), exist_ok=True)
            with open(ALARMS_FILE, 'w') as f:
                json.dump(self.alarms, f, indent=2)
        except:
            pass

    def _build_menu(self):
        root = MenuNode("Alarm Clock")
        now = datetime.datetime.now()
        root.add_child(MenuNode(f"Current Time: {now.strftime('%I:%M %p')}"))
        root.add_child(MenuNode("Set Alarm", self._set_alarm))
        for i, alarm in enumerate(self.alarms):
            t = alarm["time"]
            label = alarm.get("label", f"Alarm {i+1}")
            status = " [Disabled]" if not alarm.get("enabled", True) else ""
            root.add_child(MenuNode(f"{t} - {label}{status}", lambda idx=i: self._manage_alarm(idx)))
        if self.alarms:
            root.add_child(MenuNode("Clear All Alarms", self._clear_all))
        root.add_child(MenuNode("Back", self._do_exit))
        self.menu = MenuSystem(root, self.speak)

    def _set_alarm(self):
        now = datetime.datetime.now()
        hour = now.hour
        minute = (now.minute + 1) % 60
        if minute == 0:
            hour = (hour + 1) % 24
        alarm_time = f"{hour:02d}:{minute:02d}"
        self.alarms.append({"time": alarm_time, "label": "Alarm", "enabled": True, "ringing": False})
        self._save_alarms()
        self.speak(f"Alarm set for {alarm_time}. Press Enter to edit time.")
        self._build_menu()
        self.window.update_text(f"Alarm: {alarm_time}")

    def _manage_alarm(self, idx):
        if idx >= len(self.alarms):
            return
        alarm = self.alarms[idx]
        root = MenuNode(alarm["time"])
        root.add_child(MenuNode(f"Label: {alarm.get('label', 'Alarm')}", lambda: self._edit_label(idx)))
        root.add_child(MenuNode(f"Time: {alarm['time']}", lambda: self._edit_time(idx)))
        status = "Disable" if alarm.get("enabled", True) else "Enable"
        root.add_child(MenuNode(status, lambda: self._toggle_alarm(idx)))
        root.add_child(MenuNode("Delete", lambda: self._delete_alarm(idx)))
        root.add_child(MenuNode("Back", self._build_menu_back))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _edit_label(self, idx):
        alarm = self.alarms[idx]
        labels = ["Morning", "Work", "Lunch", "Meeting", "Exercise", "Bedtime"]
        current = labels.index(alarm.get("label", "")) if alarm.get("label", "") in labels else -1
        new_idx = (current + 1) % len(labels)
        alarm["label"] = labels[new_idx]
        self._save_alarms()
        self.speak(f"Label: {alarm['label']}")
        self._manage_alarm(idx)

    def _edit_time(self, idx):
        alarm = self.alarms[idx]
        parts = alarm["time"].split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        minute = (minute + 15) % 60
        if minute == 0:
            hour = (hour + 1) % 24
        alarm["time"] = f"{hour:02d}:{minute:02d}"
        self._save_alarms()
        self.speak(f"Time: {alarm['time']}")
        self._manage_alarm(idx)

    def _toggle_alarm(self, idx):
        alarm = self.alarms[idx]
        alarm["enabled"] = not alarm.get("enabled", True)
        status = "enabled" if alarm["enabled"] else "disabled"
        self._save_alarms()
        self.speak(f"Alarm {status}.")
        self._manage_alarm(idx)

    def _delete_alarm(self, idx):
        self.alarms.pop(idx)
        self._save_alarms()
        self.speak("Alarm deleted.")
        self._build_menu()
        self.menu.announce_current()

    def _clear_all(self):
        self.alarms.clear()
        self._save_alarms()
        self.speak("All alarms cleared.")
        self._build_menu()
        self.menu.announce_current()

    def _build_menu_back(self):
        self._build_menu()
        self.menu.announce_current()

    def _dismiss_alarm(self):
        if self.ringing_alarm is not None:
            self.alarms[self.ringing_alarm]["ringing"] = False
            self.ringing_alarm = None
            self.speak("Alarm dismissed.")
            self._stop_sound()
            self._build_menu()
            self.menu.announce_current()

    def _snooze_alarm(self):
        if self.ringing_alarm is not None:
            alarm = self.alarms[self.ringing_alarm]
            alarm["ringing"] = False
            parts = alarm["time"].split(":")
            hour = int(parts[0])
            minute = int(parts[1]) + 5
            if minute >= 60:
                minute -= 60
                hour = (hour + 1) % 24
            alarm["time"] = f"{hour:02d}:{minute:02d}"
            self._save_alarms()
            self.ringing_alarm = None
            self._stop_sound()
            self.speak(f"Snoozed for 5 minutes. New time {alarm['time']}.")
            self._build_menu()
            self.menu.announce_current()

    def _stop_sound(self):
        try:
            from core.audio_player import AudioPlayer
            AudioPlayer().stop()
        except:
            pass

    def _start_checker(self):
        def check():
            while self.running:
                now = datetime.datetime.now()
                current_time = f"{now.hour:02d}:{now.minute:02d}"
                for i, alarm in enumerate(self.alarms):
                    if alarm.get("enabled") and alarm["time"] == current_time and not alarm.get("ringing"):
                        alarm["ringing"] = True
                        self.ringing_alarm = i
                        self._save_alarms()
                        self.speak(f"Alarm! {alarm.get('label', 'Alarm')} at {alarm['time']}. Press Enter to dismiss. Press S to snooze.")
                        self.window.update_text(f"ALARM: {alarm.get('label', 'Alarm')}!")
                        try:
                            from core.audio_player import AudioPlayer
                            sound = os.path.join(os.path.dirname(__file__), "..", "sounds", "alarm.mp3")
                            if os.path.exists(sound):
                                AudioPlayer().play_file(sound)
                        except:
                            pass
                time.sleep(1)
        self.active_thread = threading.Thread(target=check, daemon=True)
        self.active_thread.start()

    def _do_exit(self):
        self.running = False
        self._stop_sound()
        self.exit_app()

    def on_focus(self):
        now = datetime.datetime.now()
        if self.ringing_alarm is not None:
            alarm = self.alarms[self.ringing_alarm]
            self.speak(f"Alarm ringing! {alarm.get('label', 'Alarm')}. Enter to dismiss. S to snooze.")
            self.window.update_text(f"ALARM: {alarm.get('label', 'Alarm')}!")
        else:
            self.speak(f"Alarm Clock. Current time {now.strftime('%I:%M %p')}. {len(self.alarms)} alarms set.")
            self.window.update_text(now.strftime("%I:%M %p"))

    def on_key(self, vk):
        if self.ringing_alarm is not None:
            if vk == win32con.VK_RETURN:
                self._dismiss_alarm()
                return
            if vk == win32con.VK_ESCAPE:
                self._dismiss_alarm()
                return
            if vk == 0x53:
                self._snooze_alarm()
                return
            return

        if vk == win32con.VK_ESCAPE:
            self._do_exit()
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
        if self.ringing_alarm is not None:
            return
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text(item.title)

    def get_help_text(self):
        if self.ringing_alarm is not None:
            return "Alarm ringing! Enter to dismiss, S to snooze."
        return "Alarm Clock. Set alarms with labels. Space for next, Backspace for previous. Enter to select."
