import random
import time
import win32con
from core.app_base import SoftApp

WORDS = [
    "the", "quick", "brown", "fox", "jumps", "over", "lazy", "dog",
    "python", "keyboard", "screen", "window", "folder", "mouse",
    "program", "function", "variable", "network", "digital", "camera",
    "hello", "world", "space", "enter", "escape", "arrow", "power",
    "music", "light", "color", "sound", "dream", "ocean", "river",
    "happy", "brave", "calm", "eager", "fair", "giant", "happy",
    "idea", "jolly", "keen", "lucky", "magic", "noble", "open",
    "proud", "quiet", "rapid", "sharp", "tender", "upper", "vivid",
    "warm", "youth", "zenith", "apple", "beach", "candy", "dance",
    "email", "flame", "grape", "heart", "ivory", "jewel", "knight"
]


class TypingTest(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.state = "menu"
        self.menu_cursor = 0
        self.menu_items = ["Start Test (30s)", "Start Test (60s)", "Start Test (120s)", "Exit"]
        self.duration = 30
        self.target_text = ""
        self.typed_text = ""
        self.start_time = 0
        self.wpm = 0
        self.accuracy = 0
        self.elapsed = 0
        self.correct = 0
        self.total = 0

    def _generate_text(self, word_count=30):
        return " ".join(random.choices(WORDS, k=word_count))

    def _start_test(self):
        self.target_text = self._generate_text(40)
        self.typed_text = ""
        self.start_time = time.time()
        self.correct = 0
        self.total = 0
        self.state = "typing"
        self.speak(f"Type the text. You have {self.duration} seconds.")
        self.window.update_text(self._render())

    def _end_test(self):
        self.elapsed = time.time() - self.start_time
        typed_words = self.typed_text.split()
        target_words = self.target_text.split()

        self.correct = 0
        self.total = len(typed_words)
        for i, word in enumerate(typed_words):
            if i < len(target_words) and word == target_words[i]:
                self.correct += 1

        minutes = self.elapsed / 60
        self.wpm = int(self.correct / minutes) if minutes > 0 else 0
        self.accuracy = int((self.correct / self.total) * 100) if self.total > 0 else 0

        self.state = "result"
        self.speak(f"Test complete. {self.wpm} words per minute. {self.accuracy}% accuracy.")
        self.window.update_text(self._render())

    def _render(self):
        if self.state == "menu":
            lines = ["Typing Test", ""]
            for i, item in enumerate(self.menu_items):
                prefix = ">" if i == self.menu_cursor else " "
                lines.append(f"{prefix} {item}")
            return "\n".join(lines)

        if self.state == "typing":
            remaining = max(0, self.duration - (time.time() - self.start_time))
            lines = [f"Time: {int(remaining)}s"]
            lines.append("")

            target_display = self.target_text[:80]
            if len(self.target_text) > 80:
                target_display += "..."
            lines.append(f"Text: {target_display}")
            lines.append("")
            lines.append(f"You:  {self.typed_text}_")
            lines.append("")
            lines.append("Type to begin. Backspace to delete.")
            return "\n".join(lines)

        if self.state == "result":
            lines = ["Test Complete!", ""]
            lines.append(f"WPM:           {self.wpm}")
            lines.append(f"Accuracy:      {self.accuracy}%")
            lines.append(f"Time:          {int(self.elapsed)}s")
            lines.append(f"Words typed:   {self.total}")
            lines.append(f"Correct:       {self.correct}")
            lines.append("")
            lines.append("Enter to try again. Escape to exit.")
            return "\n".join(lines)

    def on_focus(self):
        self.state = "menu"
        self.menu_cursor = 0
        self.speak("Typing Test. Choose a duration.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.state == "menu":
                self.exit_app()
            elif self.state == "typing":
                self.state = "menu"
                self.speak("Test cancelled.")
                self.window.update_text(self._render())
            elif self.state == "result":
                self.state = "menu"
                self.window.update_text(self._render())
            return

        if self.state == "menu":
            if vk == win32con.VK_UP:
                self.menu_cursor = (self.menu_cursor - 1) % len(self.menu_items)
            elif vk == win32con.VK_DOWN:
                self.menu_cursor = (self.menu_cursor + 1) % len(self.menu_items)
            elif vk == win32con.VK_RETURN:
                if self.menu_cursor == 0:
                    self.duration = 30
                    self._start_test()
                elif self.menu_cursor == 1:
                    self.duration = 60
                    self._start_test()
                elif self.menu_cursor == 2:
                    self.duration = 120
                    self._start_test()
                elif self.menu_cursor == 3:
                    self.exit_app()
                    return
            self.window.update_text(self._render())
            return

        if self.state == "result":
            if vk == win32con.VK_RETURN:
                self.state = "menu"
                self.window.update_text(self._render())
            return

        if self.state == "typing":
            remaining = self.duration - (time.time() - self.start_time)
            if remaining <= 0:
                self._end_test()
                return

            if vk == win32con.VK_BACK:
                if self.typed_text:
                    self.typed_text = self.typed_text[:-1]
            elif vk == win32con.VK_RETURN:
                if self.typed_text.strip():
                    self.typed_text += " "
            elif 0x20 <= vk <= 0x7E:
                ch = chr(vk).lower()
                self.typed_text += ch

                idx = len(self.typed_text) - 1
                if idx < len(self.target_text):
                    if self.typed_text[idx] == self.target_text[idx]:
                        self.correct += 1
                    self.total += 1

            self.window.update_text(self._render())

            remaining = self.duration - (time.time() - self.start_time)
            if remaining <= 0:
                self._end_test()

    def get_help_text(self):
        return "Typing Test. Measure your typing speed in words per minute. Choose 30, 60, or 120 seconds."
