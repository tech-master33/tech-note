import random
import win32con
from core.app_base import SoftApp


class Game2048(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.grid = [[0]*4 for _ in range(4)]
        self.score = 0
        self.best = 0
        self.game_over = False
        self.won = False
        self.cursor_row = 0
        self.cursor_col = 0
        self._spawn()
        self._spawn()

    def _spawn(self):
        empty = [(r, c) for r in range(4) for c in range(4) if self.grid[r][c] == 0]
        if empty:
            r, c = random.choice(empty)
            self.grid[r][c] = 2 if random.random() < 0.9 else 4

    def _slide(self, row):
        row = [x for x in row if x != 0]
        merged = False
        for i in range(len(row) - 1):
            if row[i] == row[i+1] and not merged:
                row[i] *= 2
                self.score += row[i]
                if row[i] == 2048:
                    self.won = True
                row[i+1] = 0
                merged = True
        row = [x for x in row if x != 0]
        return row + [0] * (4 - len(row))

    def _move(self, direction):
        old = [row[:] for row in self.grid]
        if direction == "left":
            self.grid = [self._slide(row) for row in self.grid]
        elif direction == "right":
            self.grid = [self._slide(row[::-1])[::-1] for row in self.grid]
        elif direction == "up":
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)]
                col = self._slide(col)
                for r in range(4):
                    self.grid[r][c] = col[r]
        elif direction == "down":
            for c in range(4):
                col = [self.grid[r][c] for r in range(4)][::-1]
                col = self._slide(col)[::-1]
                for r in range(4):
                    self.grid[r][c] = col[r]

        if self.grid != old:
            self._spawn()
            if not any(self._can_move() for _ in [1]):
                pass
            if not self._can_move():
                self.game_over = True
                self.best = max(self.best, self.score)
                self.speak("Game over!")
            self.speak(f"Score {self.score}.")

    def _can_move(self):
        for r in range(4):
            for c in range(4):
                if self.grid[r][c] == 0:
                    return True
                if c < 3 and self.grid[r][c] == self.grid[r][c+1]:
                    return True
                if r < 3 and self.grid[r][c] == self.grid[r+1][c]:
                    return True
        return False

    def _render(self):
        lines = [f"Score: {self.score}  Best: {self.best}"]
        lines.append("")
        for r in range(4):
            parts = []
            for c in range(4):
                val = self.grid[r][c]
                is_cur = r == self.cursor_row and c == self.cursor_col
                if val == 0:
                    cell = "     "
                else:
                    cell = f"{val:>5}"
                if is_cur:
                    cell = f"[{cell[1:4]}]"
                parts.append(cell)
            lines.append(" ".join(parts))

        lines.append("")
        if self.won:
            lines.append("You reached 2048! Press Enter to continue playing, or N for new game.")
        elif self.game_over:
            lines.append("Game over! Press Enter for new game.")
        else:
            lines.append("Arrows to slide tiles. N: new game. Escape: exit.")
        return "\n".join(lines)

    def on_focus(self):
        self.speak("2048. Slide tiles to merge numbers. Reach 2048 to win.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self.__init__(self.manager, self.window)
                self.speak("New game.")
                self.window.update_text(self._render())
            return

        if self.won and vk == 0x4E:
            self.__init__(self.manager, self.window)
            self.speak("New game.")
            self.window.update_text(self._render())
            return

        if vk == win32con.VK_LEFT:
            self._move("left")
        elif vk == win32con.VK_RIGHT:
            self._move("right")
        elif vk == win32con.VK_UP:
            self._move("up")
        elif vk == win32con.VK_DOWN:
            self._move("down")
        elif vk == 0x4E:
            self.__init__(self.manager, self.window)
            self.speak("New game.")

        self.window.update_text(self._render())

    def get_help_text(self):
        return "2048. Arrow keys to slide tiles. Match numbers to reach 2048. N for new game. Escape to exit."
