import random
import time
import threading
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

SYMBOLS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
ROWS = 4
COLS = 4


class MemoryMatch(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.wins = 0
        self._new_game()

    def _new_game(self):
        num_pairs = (ROWS * COLS) // 2
        chosen = random.sample(SYMBOLS, num_pairs)
        deck = chosen * 2
        random.shuffle(deck)
        self.board = []
        for r in range(ROWS):
            row = []
            for c in range(COLS):
                row.append(deck[r * COLS + c])
            self.board.append(row)

        self.revealed = [[False] * COLS for _ in range(ROWS)]
        self.matched = [[False] * COLS for _ in range(ROWS)]
        self.cursor_r = 0
        self.cursor_c = 0
        self.selected = None
        self.moves = 0
        self.pairs_found = 0
        self.total_pairs = num_pairs
        self.locked = False
        self.game_over = False

    def _render(self):
        lines = []
        lines.append(f"Moves: {self.moves}  Pairs: {self.pairs_found}/{self.total_pairs}")
        lines.append("")
        for r in range(ROWS):
            parts = []
            for c in range(COLS):
                is_cursor = r == self.cursor_r and c == self.cursor_c
                if self.matched[r][c]:
                    parts.append(f" {self.board[r][c]} ")
                elif self.revealed[r][c]:
                    parts.append(f"[{self.board[r][c]}]")
                elif is_cursor:
                    parts.append(" [?] ")
                else:
                    parts.append("  ?  ")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def _flip(self):
        r, c = self.cursor_r, self.cursor_c
        if self.locked or self.matched[r][c] or self.revealed[r][c]:
            return

        self.revealed[r][c] = True
        self.speak(self.board[r][c])

        if self.selected is None:
            self.selected = (r, c)
        else:
            sr, sc = self.selected
            self.moves += 1
            self.locked = True

            if self.board[r][c] == self.board[sr][sc]:
                self.matched[r][c] = True
                self.matched[sr][sc] = True
                self.pairs_found += 1
                self.selected = None
                self.locked = False
                self.speak("Match!")
                self.window.update_text(self._render())

                if self.pairs_found == self.total_pairs:
                    self.game_over = True
                    self.wins += 1
                    self.speak(f"Congratulations! You found all pairs in {self.moves} moves!")
                    self.window.update_text(self._render() + "\nYou win!")
            else:
                self.speak("No match.")
                self.window.update_text(self._render())

                def hide():
                    time.sleep(0.8)
                    self.revealed[r][c] = False
                    self.revealed[sr][sc] = False
                    self.selected = None
                    self.locked = False
                    self.window.update_text(self._render())

                threading.Thread(target=hide, daemon=True).start()

    def on_focus(self):
        self.speak(f"Memory Match. {ROWS} by {COLS}. Find matching pairs.")
        self.window.update_text(self._render())

    def _speak_cursor(self):
        r, c = self.cursor_r, self.cursor_c
        pos = f"Row {r + 1}, column {c + 1}."
        if self.matched[r][c]:
            self.speak(f"{pos} {self.board[r][c]}. Matched.")
        elif self.revealed[r][c]:
            self.speak(f"{pos} {self.board[r][c]}.")
        else:
            self.speak(f"{pos} Unknown.")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self._new_game()
                self.speak("New game.")
                self.window.update_text(self._render())
            return

        if self.locked:
            return

        moved = False
        if vk == win32con.VK_UP:
            self.cursor_r = (self.cursor_r - 1) % ROWS
            moved = True
        elif vk == win32con.VK_DOWN:
            self.cursor_r = (self.cursor_r + 1) % ROWS
            moved = True
        elif vk == win32con.VK_LEFT:
            self.cursor_c = (self.cursor_c - 1) % COLS
            moved = True
        elif vk == win32con.VK_RIGHT:
            self.cursor_c = (self.cursor_c + 1) % COLS
            moved = True
        elif vk == win32con.VK_RETURN:
            self._flip()
            return

        if moved:
            self._speak_cursor()
        self.window.update_text(self._render())

    def get_help_text(self):
        return "Memory Match. Arrow keys to move, Enter to flip a card. Find all matching pairs."
