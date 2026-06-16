import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUIT_SYMBOLS = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}


def card_name(card):
    rank, suit = card
    return f"{rank}{SUIT_SYMBOLS.get(suit, suit[0])}"


def card_full(card):
    rank, suit = card
    return f"{rank} of {suit}"


def is_red(card):
    return card[1] in ("Hearts", "Diamonds")


def can_stack(top, bottom):
    return is_red(top) != is_red(bottom) and RANKS.index(top[0]) == RANKS.index(bottom[0]) + 1


class Solitaire(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.wins = 0
        self._new_game()

    def _new_game(self):
        deck = [(r, s) for s in SUITS for r in RANKS]
        random.shuffle(deck)
        self.tableau = [[] for _ in range(7)]
        self.foundation = [[] for _ in range(4)]
        self.stock = []
        self.waste = []
        self.cursor_col = 0
        self.cursor_row = 0
        self.move_mode = False
        self.move_source = None
        self.game_over = False

        idx = 0
        for col in range(7):
            for row in range(col + 1):
                self.tableau[col].append({"card": deck[idx], "face_up": row == col})
                idx += 1
        self.stock = [{"card": c, "face_up": False} for c in deck[idx:]]

    def _render(self):
        lines = []
        lines.append(f"Wins: {self.wins}")
        stock_top = card_name(self.stock[-1]["card"]) if self.stock else "  "
        waste_top = card_name(self.waste[-1]["card"]) if self.waste else "  "
        f_strs = []
        for f in self.foundation:
            if f:
                f_strs.append(card_name(f[-1]["card"]))
            else:
                f_strs.append("  ")
        lines.append(f"Stock: {stock_top}  Waste: {waste_top}  Foundation: {' '.join(f_strs)}")
        lines.append("")

        max_rows = max((len(col) for col in self.tableau), default=0)

        for row in range(max_rows):
            parts = []
            for col in range(7):
                if row < len(self.tableau[col]):
                    card = self.tableau[col][row]["card"]
                    face = self.tableau[col][row]["face_up"]
                    is_cursor = col == self.cursor_col and row == self.cursor_row
                    if face:
                        name = card_name(card)
                        if is_cursor:
                            parts.append(f"[{name}]")
                        else:
                            parts.append(f" {name} ")
                    else:
                        if is_cursor:
                            parts.append(" [??] ")
                        else:
                            parts.append("  ??  ")
                else:
                    parts.append("      ")
            lines.append(" ".join(parts))

        lines.append("")
        cols = "   ".join([f" {i+1}  " for i in range(7)])
        lines.append(cols)

        if self.move_mode:
            lines.append(f"Moving {card_name(self.move_source[0])}. Enter to place, Escape to cancel.")
        elif self.game_over:
            lines.append("You win! Press Enter for new game.")
        else:
            lines.append("Arrows to move. Enter stock to draw. Enter card to select/move.")

        return "\n".join(lines)

    def _draw_stock(self):
        if not self.stock:
            self.stock = [{"card": c, "face_up": False} for c in reversed(self.waste)]
            self.waste = []
            self.speak("Stock reset.")
        else:
            card = self.stock.pop()
            card["face_up"] = True
            self.waste.append(card)
            self.speak(card_full(card["card"]))

    def _select_card(self):
        col = self.cursor_col
        if not self.tableau[col]:
            if col == 0:
                self._draw_stock()
            return

        row = self.cursor_row
        stack = self.tableau[col]
        if row < len(stack) and stack[row]["face_up"]:
            self.move_mode = True
            self.move_source = (col, row)
            self.speak(f"Selected {card_full(stack[row]['card'])}. Move to column or foundation.")

    def _try_foundation(self, card):
        for i, f in enumerate(self.foundation):
            if not f and card[0] == "A":
                return i
            elif f and f[-1]["card"][1] == card[1] and RANKS.index(f[-1]["card"][0]) == RANKS.index(card[0]) - 1:
                return i
        return -1

    def _place_card(self, dest_col):
        src_col, src_row = self.move_source
        src_stack = self.tableau[src_col]
        moving = src_stack[src_row:]

        if dest_col == -1:
            fi = self._try_foundation(moving[0]["card"])
            if fi == -1:
                self.speak("Cannot place there.")
                return
            self.foundation[fi].append(moving[0])
            self.tableau[src_col] = src_stack[:src_row]
            if self.tableau[src_col] and not self.tableau[src_col][-1]["face_up"]:
                self.tableau[src_col][-1]["face_up"] = True
            self.move_mode = False
            self.move_source = None
            self.speak(f"Placed {card_full(moving[0]['card'])} on foundation.")
            self._check_win()
            return

        if dest_col < 0 or dest_col >= 7:
            self.speak("Invalid column.")
            return

        dest_stack = self.tableau[dest_col]
        if not dest_stack:
            if moving[0]["card"][0] == "K":
                self.tableau[dest_col].extend(moving)
                self.tableau[src_col] = src_stack[:src_row]
                if self.tableau[src_col] and not self.tableau[src_col][-1]["face_up"]:
                    self.tableau[src_col][-1]["face_up"] = True
                self.move_mode = False
                self.move_source = None
                self.speak(f"Placed {card_full(moving[0]['card'])} on empty column.")
            else:
                self.speak("Only Kings can go on empty columns.")
        else:
            top = dest_stack[-1]["card"]
            if dest_stack[-1]["face_up"] and can_stack(top, moving[0]["card"]):
                self.tableau[dest_col].extend(moving)
                self.tableau[src_col] = src_stack[:src_row]
                if self.tableau[src_col] and not self.tableau[src_col][-1]["face_up"]:
                    self.tableau[src_col][-1]["face_up"] = True
                self.move_mode = False
                self.move_source = None
                self.speak(f"Placed {card_full(moving[0]['card'])} on {card_full(top)}.")
            else:
                self.speak("Cannot place there.")

    def _check_win(self):
        total = sum(len(f) for f in self.foundation)
        if total == 52:
            self.game_over = True
            self.wins += 1
            self.speak("Congratulations! You win!")
            self.window.update_text(self._render())

    def on_focus(self):
        self.speak("Solitaire. Klondike. Arrows to move cursor, Enter to select and place cards.")
        self.window.update_text(self._render())

    def _speak_cursor(self):
        col = self.cursor_col + 1
        stack = self.tableau[self.cursor_col]
        if not stack:
            self.speak(f"Column {col}. Empty.")
            return
        if self.cursor_row < len(stack):
            card = stack[self.cursor_row]["card"]
            face = stack[self.cursor_row]["face_up"]
            if face:
                self.speak(f"Column {col}. {card_full(card)}.")
            else:
                self.speak(f"Column {col}. Face down.")
        else:
            self.speak(f"Column {col}. Empty.")

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.move_mode:
                self.move_mode = False
                self.move_source = None
                self.speak("Move cancelled.")
                self.window.update_text(self._render())
            else:
                self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self._new_game()
                self.speak("New game.")
                self.window.update_text(self._render())
            return

        if self.move_mode:
            if vk == win32con.VK_LEFT:
                self.cursor_col = (self.cursor_col - 1) % 7
            elif vk == win32con.VK_RIGHT:
                self.cursor_col = (self.cursor_col + 1) % 7
            elif vk == win32con.VK_RETURN:
                self._place_card(self.cursor_col)
            self._speak_cursor()
            self.window.update_text(self._render())
            return

        moved = False
        if vk == win32con.VK_LEFT:
            self.cursor_col = (self.cursor_col - 1) % 7
            self.cursor_row = min(self.cursor_row, max(0, len(self.tableau[self.cursor_col]) - 1))
            moved = True
        elif vk == win32con.VK_RIGHT:
            self.cursor_col = (self.cursor_col + 1) % 7
            self.cursor_row = min(self.cursor_row, max(0, len(self.tableau[self.cursor_col]) - 1))
            moved = True
        elif vk == win32con.VK_UP:
            self.cursor_row = max(0, self.cursor_row - 1)
            moved = True
        elif vk == win32con.VK_DOWN:
            max_r = len(self.tableau[self.cursor_col]) - 1
            self.cursor_row = min(max_r, self.cursor_row + 1)
            moved = True
        elif vk == win32con.VK_RETURN:
            if self.cursor_col == 0 and not self.tableau[0]:
                self._draw_stock()
            else:
                self._select_card()
        elif vk == 0x46:
            self._try_foundation_from_tableau()

        if moved:
            self._speak_cursor()
        self.window.update_text(self._render())

    def _try_foundation_from_tableau(self):
        col = self.cursor_col
        stack = self.tableau[col]
        if not stack:
            return
        if not stack[-1]["face_up"]:
            return
        card = stack[-1]["card"]
        fi = self._try_foundation(card)
        if fi >= 0:
            self.foundation[fi].append(stack.pop())
            if stack and not stack[-1]["face_up"]:
                stack[-1]["face_up"] = True
            self.speak(f"Moved {card_full(card)} to foundation.")
            self._check_win()

    def get_help_text(self):
        return "Solitaire. Arrows to move cursor. Enter to select card, Enter again to place. F to send to foundation. Escape to cancel or exit."
