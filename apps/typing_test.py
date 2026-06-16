import random
import time
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

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
        self.duration = 30
        self.target_text = ""
        self.typed_text = ""
        self.start_time = 0
        self.wpm = 0
        self.accuracy = 0
        self.elapsed = 0
        self.correct = 0
        self.total = 0
        self.menu = None
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Typing Test")
        root.add_child(MenuNode("Start Test (30s)", lambda: self._start_test(30)))
        root.add_child(MenuNode("Start Test (60s)", lambda: self._start_test(60)))
        root.add_child(MenuNode("Start Test (120s)", lambda: self._start_test(120)))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _generate_text(self, word_count=30):
        return " ".join(random.choices(WORDS, k=word_count))

    def _start_test(self, duration):
        self.duration = duration
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
        self.speak(f"Test complete. {self.wpm} words per minute. {self.accuracy}% accuracy. {self.total} words typed, {self.correct} correct.")
        self.window.update_text(self._render())

    def _render(self):
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
            return "\n".join(lines)

        if self.state == "result":
            lines = ["Test Complete!", ""]
            lines.append(f"WPM:           {self.wpm}")
            lines.append(f"Accuracy:      {self.accuracy}%")
            lines.append(f"Time:          {int(self.elapsed)}s")
            lines.append(f"Words typed:   {self.total}")
            lines.append(f"Correct:       {self.correct}")
            return "\n".join(lines)

        return "Typing Test"

    def on_focus(self):
        self.state = "menu"
        self._build_menu()
        self.speak("Typing Test. Choose a duration.")
        self.window.update_text("Typing Test")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.state == "menu":
                self.exit_app()
            elif self.state == "typing":
                self.state = "menu"
                self._build_menu()
                self.speak("Test cancelled.")
                self.window.update_text("Typing Test")
            elif self.state == "result":
                self.state = "menu"
                self._build_menu()
                self.window.update_text("Typing Test")
            return

        if self.state == "result":
            if vk == win32con.VK_RETURN:
                self.state = "menu"
                self._build_menu()
                self.window.update_text("Typing Test")
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
            return

        if self.state == "menu":
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

    def get_help_text(self):
        return "Typing Test. Measure your typing speed in words per minute. Choose 30, 60, or 120 seconds."
