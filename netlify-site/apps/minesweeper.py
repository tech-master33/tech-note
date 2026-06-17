import random
import win32con
from core.app_base import SoftApp


class Minesweeper(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.rows = 10
        self.cols = 10
        self.mines = 15
        self.cursor_row = 0
        self.cursor_col = 0
        self.grid = []
        self.revealed = []
        self.flagged = []
        self.game_over = False
        self.won = False
        self.first_move = True
        self.flag_mode = False
        self._new_game()

    def _new_game(self):
        self.grid = [[0]*self.cols for _ in range(self.rows)]
        self.revealed = [[False]*self.cols for _ in range(self.rows)]
        self.flagged = [[False]*self.cols for _ in range(self.rows)]
        self.game_over = False
        self.won = False
        self.first_move = True
        self.cursor_row = self.rows // 2
        self.cursor_col = self.cols // 2
        self.flag_mode = False

    def _place_mines(self, safe_r, safe_c):
        cells = [(r, c) for r in range(self.rows) for c in range(self.cols)
                 if abs(r - safe_r) > 1 or abs(c - safe_c) > 1]
        random.shuffle(cells)
        for r, c in cells[:self.mines]:
            self.grid[r][c] = -1

        for r in range(self.rows):
            for c in range(self.cols):
                if self.grid[r][c] == -1:
                    continue
                count = 0
                for dr in [-1, 0, 1]:
                    for dc in [-1, 0, 1]:
                        nr, nc = r + dr, c + dc
                        if 0 <= nr < self.rows and 0 <= nc < self.cols and self.grid[nr][nc] == -1:
                            count += 1
                self.grid[r][c] = count

    def _reveal(self, r, c):
        if r < 0 or r >= self.rows or c < 0 or c >= self.cols:
            return
        if self.revealed[r][c] or self.flagged[r][c]:
            return
        self.revealed[r][c] = True
        if self.grid[r][c] == 0:
            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    self._reveal(r + dr, c + dc)

    def _check_win(self):
        unrevealed = sum(1 for r in range(self.rows) for c in range(self.cols)
                        if not self.revealed[r][c])
        if unrevealed == self.mines:
            self.won = True
            self.game_over = True
            self.speak("You win!")

    def _render(self):
        flag_count = sum(1 for r in range(self.rows) for c in range(self.cols) if self.flagged[r][c])
        lines = [f"Mines: {self.mines}  Flags: {flag_count}  Mode: {'Flag' if self.flag_mode else 'Reveal'}"]
        lines.append("")

        for r in range(self.rows):
            parts = []
            for c in range(self.cols):
                is_cur = r == self.cursor_row and c == self.cursor_col
                if self.revealed[r][c]:
                    if self.grid[r][c] == -1:
                        cell = " * "
                    elif self.grid[r][c] == 0:
                        cell = "   "
                    else:
                        cell = f" {self.grid[r][c]} "
                elif self.flagged[r][c]:
                    cell = " F "
                else:
                    cell = " . "
                if is_cur:
                    cell = f"[{cell[1]}]"
                parts.append(cell)
            lines.append(" ".join(parts))

        lines.append("")
        if self.game_over:
            if self.won:
                lines.append("You win! Press Enter for new game.")
            else:
                lines.append("Boom! Game over. Press Enter for new game.")
        else:
            lines.append("Arrows: move. Enter: act. Tab: toggle mode. Escape: exit.")
        return "\n".join(lines)

    def on_focus(self):
        self.speak(f"Minesweeper. {self.mines} mines. Arrow keys to move, Enter to reveal or flag.")
        self.window.update_text(self._render())

    def _speak_cursor(self):
        r, c = self.cursor_row, self.cursor_col
        if self.revealed[r][c]:
            if self.grid[r][c] == -1:
                self.speak(f"Row {r + 1}, column {c + 1}. Mine.")
            elif self.grid[r][c] == 0:
                self.speak(f"Row {r + 1}, column {c + 1}. Empty.")
            else:
                self.speak(f"Row {r + 1}, column {c + 1}. {self.grid[r][c]} mines nearby.")
        elif self.flagged[r][c]:
            self.speak(f"Row {r + 1}, column {c + 1}. Flagged.")
        else:
            self.speak(f"Row {r + 1}, column {c + 1}. Hidden.")

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

        moved = False
        if vk == win32con.VK_LEFT:
            self.cursor_col = (self.cursor_col - 1) % self.cols
            moved = True
        elif vk == win32con.VK_RIGHT:
            self.cursor_col = (self.cursor_col + 1) % self.cols
            moved = True
        elif vk == win32con.VK_UP:
            self.cursor_row = (self.cursor_row - 1) % self.rows
            moved = True
        elif vk == win32con.VK_DOWN:
            self.cursor_row = (self.cursor_row + 1) % self.rows
            moved = True
        elif vk == win32con.VK_TAB:
            self.flag_mode = not self.flag_mode
            self.speak(f"Mode: {'Flag' if self.flag_mode else 'Reveal'}.")
        elif vk == win32con.VK_RETURN:
            r, c = self.cursor_row, self.cursor_col
            if self.flag_mode:
                if not self.revealed[r][c]:
                    self.flagged[r][c] = not self.flagged[r][c]
                    self.speak("Flagged." if self.flagged[r][c] else "Unflagged.")
            else:
                if self.flagged[r][c]:
                    self.speak("Remove flag first.")
                    return
                if self.revealed[r][c]:
                    return
                if self.first_move:
                    self._place_mines(r, c)
                    self.first_move = False
                if self.grid[r][c] == -1:
                    self.revealed[r][c] = True
                    self.game_over = True
                    self.speak("Boom! Game over.")
                else:
                    self._reveal(r, c)
                    self._check_win()
                    if not self.game_over:
                        val = self.grid[r][c]
                        self.speak(f"{val} mines nearby." if val > 0 else "Empty.")

        if moved:
            self._speak_cursor()
        self.window.update_text(self._render())

    def get_help_text(self):
        return "Minesweeper. Arrows to move. Enter to reveal or flag. Tab to toggle mode. Find all mines without detonating."
