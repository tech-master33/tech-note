import random
import time
import json
import os
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem

SCORES_FILE = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'puzzle_scores.json')


class PuzzleGame(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.size = 4
        self.board = []
        self.empty_pos = (self.size - 1, self.size - 1)
        self.moves = 0
        self.start_time = 0
        self.elapsed = 0
        self.game_over = False
        self.scores = self._load_scores()
        self._init_board()
        self._build_menu()

    def _load_scores(self):
        if os.path.exists(SCORES_FILE):
            try:
                with open(SCORES_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"3": None, "4": None, "5": None}

    def _save_scores(self):
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w') as f:
            json.dump(self.scores, f)

    def _init_board(self):
        nums = list(range(1, self.size * self.size)) + [0]
        random.shuffle(nums)
        self.board = []
        for r in range(self.size):
            row = []
            for c in range(self.size):
                row.append(nums[r * self.size + c])
                if nums[r * self.size + c] == 0:
                    self.empty_pos = (r, c)
            self.board.append(row)
        if not self._is_solvable():
            self._init_board()
        self.game_over = False

    def _is_solvable(self):
        flat = [n for row in self.board for n in row if n != 0]
        inversions = 0
        for i in range(len(flat)):
            for j in range(i + 1, len(flat)):
                if flat[i] > flat[j]:
                    inversions += 1
        empty_row = self.empty_pos[0]
        if self.size % 2 == 0:
            return (inversions + empty_row) % 2 == 0
        return inversions % 2 == 0

    def _build_menu(self):
        root = MenuNode("Puzzle Game")
        best = self.scores.get(str(self.size))
        best_str = f"Best: {best} moves" if best else "Best: ---"
        root.add_child(MenuNode(f"Size: {self.size}x{self.size}", self._cycle_size))
        root.add_child(MenuNode(f"Moves: {self.moves}", self._announce_moves))
        root.add_child(MenuNode(f"Time: {self._format_time(self.elapsed)}", self._announce_time))
        root.add_child(MenuNode(best_str))
        root.add_child(MenuNode("New Game", self._new_game))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _cycle_size(self):
        sizes = [3, 4, 5]
        idx = sizes.index(self.size)
        self.size = sizes[(idx + 1) % 3]
        self._new_game()

    def _format_time(self, secs):
        m = int(secs) // 60
        s = int(secs) % 60
        return f"{m}:{s:02d}"

    def _announce_moves(self):
        self.speak(f"{self.moves} moves.")

    def _announce_time(self):
        self.speak(f"Time: {self._format_time(self.elapsed)}")

    def _new_game(self):
        self.moves = 0
        self.elapsed = 0
        self.start_time = time.time()
        self._init_board()
        self._build_menu()
        self.speak(f"New {self.size} by {self.size} puzzle. Use arrow keys to slide tiles.")
        self.window.update_text(self._render())

    def _render(self):
        lines = []
        best = self.scores.get(str(self.size))
        best_str = f"  Best: {best}" if best else ""
        lines.append(f"Size: {self.size}x{self.size}  Moves: {self.moves}  Time: {self._format_time(self.elapsed)}{best_str}")
        lines.append("")
        border = "+" + "----+" * self.size
        lines.append(border)
        for r in range(self.size):
            parts = []
            for c in range(self.size):
                val = self.board[r][c]
                if val == 0:
                    parts.append("    ")
                else:
                    parts.append(f"{val:3d} ")
            lines.append("|" + "|".join(parts) + "|")
            lines.append(border)
        lines.append("")
        if self.game_over:
            lines.append(f"Solved in {self.moves} moves and {self._format_time(self.elapsed)}!")
            lines.append("Enter for new game. Escape to exit.")
        else:
            lines.append("Arrows to slide tiles. Numbers 1-9 to move tile directly.")
        return "\n".join(lines)

    def _find_tile(self, val):
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == val:
                    return (r, c)
        return None

    def _slide(self, tile_r, tile_c):
        er, ec = self.empty_pos
        if (abs(tile_r - er) + abs(tile_c - ec)) != 1:
            return False
        self.board[er][ec] = self.board[tile_r][tile_c]
        self.board[tile_r][tile_c] = 0
        self.empty_pos = (tile_r, tile_c)
        self.moves += 1
        return True

    def _check_win(self):
        expected = 1
        for r in range(self.size):
            for c in range(self.size):
                if r == self.size - 1 and c == self.size - 1:
                    if self.board[r][c] != 0:
                        return False
                else:
                    if self.board[r][c] != expected:
                        return False
                    expected += 1
        return True

    def _on_win(self):
        self.game_over = True
        self.elapsed = time.time() - self.start_time
        best = self.scores.get(str(self.size))
        if best is None or self.moves < best:
            self.scores[str(self.size)] = self.moves
            self._save_scores()
            self.speak(f"Puzzle solved! New best score: {self.moves} moves in {self._format_time(self.elapsed)}!")
        else:
            self.speak(f"Puzzle solved in {self.moves} moves and {self._format_time(self.elapsed)}!")
        self._build_menu()
        self.window.update_text(self._render())

    def _move_by_number(self, num):
        if self.game_over:
            return
        pos = self._find_tile(num)
        if pos and self._slide(pos[0], pos[1]):
            self.window.update_text(self._render())
            if self._check_win():
                self._on_win()
            else:
                self.speak(str(num))

    def _try_slide_empty(self, direction):
        if self.game_over:
            return False
        er, ec = self.empty_pos
        tr, tc = er, ec
        if direction == "up":
            tr += 1
        elif direction == "down":
            tr -= 1
        elif direction == "left":
            tc += 1
        elif direction == "right":
            tc -= 1
        if 0 <= tr < self.size and 0 <= tc < self.size:
            if self._slide(tr, tc):
                self.window.update_text(self._render())
                if self._check_win():
                    self._on_win()
                return True
        return False

    def on_focus(self):
        if self.start_time == 0:
            self.start_time = time.time()
        self.speak(f"Puzzle game. {self.size} by {self.size}. Use arrows to slide tiles into the empty space.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self._new_game()
            return

        if vk == win32con.VK_UP:
            self._try_slide_empty("up")
        elif vk == win32con.VK_DOWN:
            self._try_slide_empty("down")
        elif vk == win32con.VK_LEFT:
            self._try_slide_empty("left")
        elif vk == win32con.VK_RIGHT:
            self._try_slide_empty("right")
        elif 0x31 <= vk <= 0x39:
            self._move_by_number(vk - 0x30)
        elif vk == 0x30:
            self._move_by_number(0)

    def get_help_text(self):
        return "Puzzle. Arrow keys slide tiles. Numbers 1-9 move that tile. Change size in menu. Best scores saved."
