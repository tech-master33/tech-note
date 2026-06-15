import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

WORDS = [
    "python", "keyboard", "window", "screen", "folder", "mouse", "printer",
    "memory", "battery", "speaker", "monitor", "internet", "website",
    "program", "function", "variable", "network", "digital", "camera",
    "guitar", "piano", "rocket", "planet", "ocean", "forest", "desert",
    "castle", "dragon", "wizard", "bridge", "market", "garden", "forest",
    "island", "river", "mountain", "thunder", "blanket", "diamond",
    "emerald", "silver", "golden", "copper", "marble", "velvet", "cotton"
]

MAX_WRONG = 6


class Hangman(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.wins = 0
        self.losses = 0
        self._new_game()

    def _new_game(self):
        self.word = random.choice(WORDS).upper()
        self.guessed = set()
        self.wrong = 0
        self.cursor = 0
        self.alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        self.game_over = False
        self.won = False

    def _render(self):
        display = ""
        for ch in self.word:
            if ch in self.guessed:
                display += ch + " "
            else:
                display += "_ "
        
        lines = []
        lines.append(f"Wins: {self.wins}  Losses: {self.losses}")
        lines.append("")
        lines.append(display.strip())
        lines.append(f"Wrong: {self.wrong}/{MAX_WRONG}")
        lines.append("")
        
        row1 = ""
        row2 = ""
        for i, letter in enumerate(self.alphabet):
            if letter in self.guessed:
                mark = f"[{letter}]" if letter in self.word else f"({letter})"
            else:
                mark = f" {letter} " if i != self.cursor else f"[{letter}]"
            if i < 13:
                row1 += mark
            else:
                row2 += mark
        lines.append(row1)
        lines.append(row2)
        return "\n".join(lines)

    def _guess(self):
        letter = self.alphabet[self.cursor]
        if letter in self.guessed:
            return

        self.guessed.add(letter)

        if letter in self.word:
            self.speak(f"Correct. {letter} is in the word.")
            remaining = [ch for ch in self.word if ch not in self.guessed]
            if not remaining:
                self.game_over = True
                self.won = True
                self.wins += 1
                self.speak(f"You win! The word was {self.word}.")
                self.window.update_text(self._render() + f"\nYou win! {self.word}")
        else:
            self.wrong += 1
            self.speak(f"Wrong. {letter} is not in the word.")
            if self.wrong >= MAX_WRONG:
                self.game_over = True
                self.won = False
                self.losses += 1
                self.speak(f"Game over. The word was {self.word}.")
                self.window.update_text(self._render() + f"\nGame over! {self.word}")
            else:
                self.window.update_text(self._render())

    def on_focus(self):
        self.speak("Hangman. Guess letters to find the word.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self._new_game()
                self.speak("New game. Guess a letter.")
                self.window.update_text(self._render())
            return

        if vk == win32con.VK_LEFT:
            self.cursor = (self.cursor - 1) % 26
        elif vk == win32con.VK_RIGHT:
            self.cursor = (self.cursor + 1) % 26
        elif vk == win32con.VK_UP:
            self.cursor = (self.cursor - 13) % 26
        elif vk == win32con.VK_DOWN:
            self.cursor = (self.cursor + 13) % 26
        elif vk == win32con.VK_RETURN:
            self._guess()
            return
        elif 0x41 <= vk <= 0x5A:
            self.cursor = vk - 0x41
            self._guess()
            return

        self.window.update_text(self._render())

    def get_help_text(self):
        return "Hangman. Arrows to select a letter, Enter to guess. Type a letter directly to guess it. Escape to exit."
