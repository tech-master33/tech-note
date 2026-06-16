import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


class TicTacToe(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.board = [" "] * 9
        self.player = "X"
        self.computer = "O"
        self.game_over = False
        self.winner = None
        self.cursor = 0
        self.scores = {"X": 0, "O": 0, "Ties": 0}
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Tic Tac Toe")
        root.add_child(MenuNode(f"Score - You: {self.scores['X']}  Computer: {self.scores['O']}  Ties: {self.scores['Ties']}"))
        root.add_child(MenuNode("New Game", self._new_game))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _render(self):
        b = self.board
        lines = []
        for row in range(3):
            cells = []
            for col in range(3):
                idx = row * 3 + col
                ch = b[idx]
                if idx == self.cursor and not self.game_over:
                    cells.append(f"[{ch if ch != ' ' else ' '}]")
                else:
                    cells.append(f" {ch if ch != ' ' else ' '} ")
            lines.append(" | ".join(cells))
            if row < 2:
                lines.append("-----------")
        return "\n".join(lines)

    def _new_game(self):
        self.board = [" "] * 9
        self.cursor = 0
        self.game_over = False
        self.winner = None
        self.player = "X"
        self.computer = "O"
        self.speak("New game. You are X. Use arrows to move, Enter to place.")
        self.window.update_text(self._render())

    def _check_winner(self, b, mark):
        wins = [
            (0,1,2),(3,4,5),(6,7,8),
            (0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6)
        ]
        for i,j,k in wins:
            if b[i] == b[j] == b[k] == mark:
                return True
        return False

    def _is_full(self):
        return " " not in self.board

    def _get_empty(self):
        return [i for i in range(9) if self.board[i] == " "]

    def _minimax(self, b, is_maximizing):
        if self._check_winner(b, self.computer):
            return 10
        if self._check_winner(b, self.player):
            return -10
        if self._is_full():
            return 0

        if is_maximizing:
            best = -100
            for i in range(9):
                if b[i] == " ":
                    b[i] = self.computer
                    score = self._minimax(b, False)
                    b[i] = " "
                    best = max(best, score)
            return best
        else:
            best = 100
            for i in range(9):
                if b[i] == " ":
                    b[i] = self.player
                    score = self._minimax(b, True)
                    b[i] = " "
                    best = min(best, score)
            return best

    def _computer_move(self):
        empty = self._get_empty()
        if not empty:
            return

        best_score = -100
        best_move = empty[0]

        for i in empty:
            self.board[i] = self.computer
            score = self._minimax(self.board, False)
            self.board[i] = " "
            if score > best_score:
                best_score = score
                best_move = i

        self.board[best_move] = self.computer

    def _place(self):
        if self.game_over or self.board[self.cursor] != " ":
            return

        self.board[self.cursor] = self.player

        if self._check_winner(self.board, self.player):
            self.game_over = True
            self.winner = "X"
            self.scores["X"] += 1
            self._build_menu()
            self.speak("You win!")
            self.window.update_text(self._render() + "\nYou win!")
            return

        if self._is_full():
            self.game_over = True
            self.winner = "Ties"
            self.scores["Ties"] += 1
            self._build_menu()
            self.speak("It's a tie!")
            self.window.update_text(self._render() + "\nTie!")
            return

        self._computer_move()

        if self._check_winner(self.board, self.computer):
            self.game_over = True
            self.winner = "O"
            self.scores["O"] += 1
            self._build_menu()
            self.speak("Computer wins!")
            self.window.update_text(self._render() + "\nComputer wins!")
            return

        if self._is_full():
            self.game_over = True
            self.winner = "Ties"
            self.scores["Ties"] += 1
            self._build_menu()
            self.speak("It's a tie!")
            self.window.update_text(self._render() + "\nTie!")
            return

        self.speak("Your turn.")
        self.window.update_text(self._render())

    def on_focus(self):
        self.speak("Tic Tac Toe. You are X, computer is O. Use arrows to move, Enter to place.")
        self.window.update_text(self._render())

    def _speak_cursor(self):
        row = self.cursor // 3 + 1
        col = self.cursor % 3 + 1
        cell = self.board[self.cursor]
        if cell != " ":
            self.speak(f"Row {row}, column {col}. {cell}.")
        else:
            self.speak(f"Row {row}, column {col}. Empty.")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.game_over:
            return

        moved = False
        if vk == win32con.VK_UP:
            self.cursor = (self.cursor - 3) % 9
            moved = True
        elif vk == win32con.VK_DOWN:
            self.cursor = (self.cursor + 3) % 9
            moved = True
        elif vk == win32con.VK_LEFT:
            self.cursor = (self.cursor - 1) % 9
            moved = True
        elif vk == win32con.VK_RIGHT:
            self.cursor = (self.cursor + 1) % 9
            moved = True
        elif vk == win32con.VK_RETURN:
            self._place()
            return

        if moved:
            self._speak_cursor()
        self.window.update_text(self._render())

    def get_help_text(self):
        return "Tic Tac Toe. Arrows to move cursor, Enter to place X. You play against the computer."
