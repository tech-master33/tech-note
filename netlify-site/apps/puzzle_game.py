import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem


class PuzzleGame(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.size = 4
        self.board = []
        self.empty_pos = (self.size - 1, self.size - 1)
        self.moves = 0
        self._init_board()
        self._build_menu()

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
        root.add_child(MenuNode(f"Moves: {self.moves}", self._announce_moves))
        root.add_child(MenuNode("New Game", self._new_game))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _announce_moves(self):
        self.speak(f"{self.moves} moves.")

    def _new_game(self):
        self.moves = 0
        self._init_board()
        self._build_menu()
        self.speak("New puzzle. Use arrow keys to slide tiles.")
        self.window.update_text(self._render())

    def _render(self):
        lines = []
        lines.append(f"Moves: {self.moves}")
        lines.append("+----+----+----+----+")
        for r in range(self.size):
            parts = []
            for c in range(self.size):
                val = self.board[r][c]
                if val == 0:
                    parts.append("    ")
                else:
                    parts.append(f"{val:3d} ")
            lines.append("|" + "|".join(parts) + "|")
            lines.append("+----+----+----+----+")
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

    def _move_by_number(self, num):
        pos = self._find_tile(num)
        if pos and self._slide(pos[0], pos[1]):
            self.window.update_text(self._render())
            if self._check_win():
                self.speak(f"Congratulations! You solved it in {self.moves} moves!")
            else:
                self.speak(str(num))

    def _try_slide_empty(self, direction):
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
                    self.speak(f"Congratulations! You solved it in {self.moves} moves!")
                return True
        return False

    def on_focus(self):
        self.speak(f"Puzzle game. {self.size} by {self.size}. Use arrows to slide tiles into the empty space. Press numbers to move a tile directly.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
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
        return "Puzzle. Arrow keys slide tiles. Numbers 1-9 move that tile. Escape to exit."
