import random
import win32con
from core.app_base import SoftApp


class Sudoku(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.difficulty = "Medium"
        self.puzzle = []
        self.solution = []
        self.given = []
        self.cursor_row = 0
        self.cursor_col = 0
        self.selected_num = 0
        self.errors = 0
        self.completed = False
        self._new_game()

    def _generate_full(self):
        board = [[0]*9 for _ in range(9)]

        def is_valid(board, row, col, num):
            for i in range(9):
                if board[row][i] == num or board[i][col] == num:
                    return False
            br, bc = 3*(row//3), 3*(col//3)
            for r in range(br, br+3):
                for c in range(bc, bc+3):
                    if board[r][c] == num:
                        return False
            return True

        def fill(board):
            for r in range(9):
                for c in range(9):
                    if board[r][c] == 0:
                        nums = list(range(1, 10))
                        random.shuffle(nums)
                        for n in nums:
                            if is_valid(board, r, c, n):
                                board[r][c] = n
                                if fill(board):
                                    return True
                                board[r][c] = 0
                        return False
            return True

        fill(board)
        return board

    def _make_puzzle(self):
        self.solution = self._generate_full()
        remove = {"Easy": 35, "Medium": 45, "Hard": 55}[self.difficulty]
        self.puzzle = [row[:] for row in self.solution]
        cells = [(r, c) for r in range(9) for c in range(9)]
        random.shuffle(cells)
        for r, c in cells[:remove]:
            self.puzzle[r][c] = 0
        self.given = [[self.puzzle[r][c] != 0 for c in range(9)] for r in range(9)]

    def _new_game(self):
        self._make_puzzle()
        self.cursor_row = 4
        self.cursor_col = 4
        self.selected_num = 0
        self.errors = 0
        self.completed = False
        self.speak(f"Sudoku {self.difficulty}. Use arrows to move, number keys 1 to 9 to place.")

    def _check_complete(self):
        for r in range(9):
            for c in range(9):
                if self.puzzle[r][c] == 0:
                    return False
        self.completed = True
        self.speak(f"Solved! {self.errors} errors.")
        return True

    def _render(self):
        lines = [f"Difficulty: {self.difficulty}  Errors: {self.errors}"]
        lines.append("")
        for r in range(9):
            if r % 3 == 0 and r != 0:
                lines.append("------+-------+------")
            row_str = ""
            for c in range(9):
                if c % 3 == 0 and c != 0:
                    row_str += "| "
                val = self.puzzle[r][c]
                is_cur = r == self.cursor_row and c == self.cursor_col
                if val == 0:
                    cell = " . " if not is_cur else "[. ]"
                else:
                    cell = f" {val} " if not is_cur else f"[{val}]"
                row_str += cell
            lines.append(row_str)

        lines.append("")
        nums = " ".join([f"[{i+1}]" if i+1 == self.selected_num else f" {i+1} " for i in range(9)])
        lines.append(nums)
        lines.append("")
        if self.completed:
            lines.append("You win! Press Enter for new game.")
        else:
            lines.append("Arrows: move. 1-9: place number. 0: clear. N: new game.")
        return "\n".join(lines)

    def on_focus(self):
        self.speak(f"Sudoku {self.difficulty}. Use arrows to move, number keys to place digits.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.completed:
            if vk == win32con.VK_RETURN:
                self._new_game()
                self.window.update_text(self._render())
            return

        if vk == win32con.VK_LEFT:
            self.cursor_col = (self.cursor_col - 1) % 9
        elif vk == win32con.VK_RIGHT:
            self.cursor_col = (self.cursor_col + 1) % 9
        elif vk == win32con.VK_UP:
            self.cursor_row = (self.cursor_row - 1) % 9
        elif vk == win32con.VK_DOWN:
            self.cursor_row = (self.cursor_row + 1) % 9
        elif vk == win32con.VK_RETURN:
            if self.selected_num > 0 and not self.given[self.cursor_row][self.cursor_col]:
                self.puzzle[self.cursor_row][self.cursor_col] = self.selected_num
                if self.puzzle[self.cursor_row][self.cursor_col] != self.solution[self.cursor_row][self.cursor_col]:
                    self.errors += 1
                    self.speak("Wrong!")
                else:
                    self.speak(f"Placed {self.selected_num}.")
                self._check_complete()
        elif vk == win32con.VK_DELETE or vk == 0x30:
            if not self.given[self.cursor_row][self.cursor_col]:
                self.puzzle[self.cursor_row][self.cursor_col] = 0
                self.speak("Cleared.")
        elif 0x31 <= vk <= 0x39:
            num = vk - 0x30
            self.selected_num = num
            self.speak(f"Selected {num}.")
        elif vk == 0x4E:
            self._new_game()
            self.speak("New game.")
        elif vk == 0x44:
            difficulties = ["Easy", "Medium", "Hard"]
            idx = (difficulties.index(self.difficulty) + 1) % 3
            self.difficulty = difficulties[idx]
            self._new_game()
            self.speak(f"Difficulty: {self.difficulty}. New game.")

        self.window.update_text(self._render())

    def get_help_text(self):
        return "Sudoku. Arrows to move. 1-9 to select digit. Enter to place. 0 to clear. D to change difficulty. N for new game. Escape to exit."
