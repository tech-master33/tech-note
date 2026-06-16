import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

ROWS = 6
COLS = 7


class ConnectFour(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.wins = 0
        self.losses = 0
        self._new_game()

    def _new_game(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.cursor = 3
        self.player = "X"
        self.computer = "O"
        self.game_over = False
        self.winner = None
        self.moves = 0

    def _render(self):
        lines = []
        lines.append(f"Wins: {self.wins}  Losses: {self.losses}  Moves: {self.moves}")
        lines.append("")
        for r in range(ROWS):
            parts = []
            for c in range(COLS):
                ch = self.board[r][c]
                if ch == "X":
                    parts.append(" X ")
                elif ch == "O":
                    parts.append(" O ")
                elif c == self.cursor and not self.game_over:
                    parts.append(" v ")
                else:
                    parts.append(" . ")
            lines.append("|" + "|".join(parts) + "|")
        lines.append("+" + "---+" * COLS)
        nums = ""
        for c in range(COLS):
            nums += f" {c+1} |"
        lines.append(nums)
        return "\n".join(lines)

    def _get_lowest_row(self, col):
        for r in range(ROWS - 1, -1, -1):
            if self.board[r][col] is None:
                return r
        return -1

    def _check_winner(self, mark):
        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c] != mark:
                    continue
                directions = [(0,1),(1,0),(1,1),(1,-1)]
                for dr, dc in directions:
                    count = 0
                    for i in range(4):
                        nr, nc = r + dr*i, c + dc*i
                        if 0 <= nr < ROWS and 0 <= nc < COLS and self.board[nr][nc] == mark:
                            count += 1
                        else:
                            break
                    if count == 4:
                        return True
        return False

    def _is_full(self):
        return all(self.board[0][c] is not None for c in range(COLS))

    def _drop(self, col):
        row = self._get_lowest_row(col)
        if row == -1:
            self.speak("Column is full.")
            return False
        self.board[row][col] = self.player
        self.moves += 1

        if self._check_winner(self.player):
            self.game_over = True
            self.winner = "X"
            self.wins += 1
            self.speak("You win!")
            self.window.update_text(self._render() + "\nYou win!")
            return True

        if self._is_full():
            self.game_over = True
            self.winner = "Tie"
            self.speak("It's a tie!")
            self.window.update_text(self._render() + "\nTie!")
            return True

        self._computer_move()

        if self._check_winner(self.computer):
            self.game_over = True
            self.winner = "O"
            self.losses += 1
            self.speak("Computer wins!")
            self.window.update_text(self._render() + "\nComputer wins!")
            return True

        if self._is_full():
            self.game_over = True
            self.winner = "Tie"
            self.speak("It's a tie!")
            self.window.update_text(self._render() + "\nTie!")
            return True

        return True

    def _computer_move(self):
        best_col = 3
        best_score = -1

        for c in range(COLS):
            row = self._get_lowest_row(c)
            if row == -1:
                continue

            score = 0
            self.board[row][c] = self.computer
            if self._check_winner(self.computer):
                score = 100
            self.board[row][c] = None

            self.board[row][c] = self.player
            if self._check_winner(self.player):
                score = 90
            self.board[row][c] = None

            if c == 3:
                score += 3
            elif c in (2, 4):
                score += 2
            elif c in (1, 5):
                score += 1

            self.board[row][c] = self.computer
            for dc in [-1, 1]:
                nc = c + dc
                if 0 <= nc < COLS and self.board[row][nc] == self.computer:
                    score += 2
            self.board[row][c] = None

            if score > best_score:
                best_score = score
                best_col = c

        row = self._get_lowest_row(best_col)
        if row != -1:
            self.board[row][best_col] = self.computer
            self.moves += 1

    def on_focus(self):
        self.speak("Connect Four. Drop pieces to get four in a row. Left and Right to choose column, Enter to drop.")
        self.window.update_text(self._render())

    def _speak_cursor(self):
        col = self.cursor + 1
        lowest = self._get_lowest_row(self.cursor)
        if lowest == -1:
            self.speak(f"Column {col}. Full.")
        else:
            self.speak(f"Column {col}. Row {lowest + 1} available.")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self._new_game()
                self.speak("New game. Choose a column.")
                self.window.update_text(self._render())
            return

        moved = False
        if vk == win32con.VK_LEFT:
            self.cursor = (self.cursor - 1) % COLS
            moved = True
        elif vk == win32con.VK_RIGHT:
            self.cursor = (self.cursor + 1) % COLS
            moved = True
        elif vk == win32con.VK_RETURN:
            self._drop(self.cursor)
            self.window.update_text(self._render())
            return

        if moved:
            self._speak_cursor()
        self.window.update_text(self._render())

    def get_help_text(self):
        return "Connect Four. Left/Right to choose column, Enter to drop your piece. Get four in a row to win."
