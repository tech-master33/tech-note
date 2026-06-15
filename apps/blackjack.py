import random
import win32con
from core.app_base import SoftApp

SUITS = ["Hearts", "Diamonds", "Clubs", "Spades"]
RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
VALUES = {"A": 11, "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, "J": 10, "Q": 10, "K": 10}
SUIT_SYM = {"Hearts": "♥", "Diamonds": "♦", "Clubs": "♣", "Spades": "♠"}


def card_str(card):
    return f"{card[0]}{SUIT_SYM.get(card[1], '')}"


def hand_value(hand):
    val = sum(VALUES[c[0]] for c in hand)
    aces = sum(1 for c in hand if c[0] == "A")
    while val > 21 and aces:
        val -= 10
        aces -= 1
    return val


class Blackjack(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.balance = 100
        self.bet = 10
        self.deck = []
        self.player = []
        self.dealer = []
        self.phase = "bet"
        self.result = ""
        self.cursor = 0
        self._shuffle()

    def _shuffle(self):
        self.deck = [(r, s) for s in SUITS for r in RANKS]
        random.shuffle(self.deck)

    def _deal(self):
        if len(self.deck) < 20:
            self._shuffle()
        self.player = [self.deck.pop(), self.deck.pop()]
        self.dealer = [self.deck.pop(), self.deck.pop()]
        self.phase = "play"
        self.result = ""
        pv = hand_value(self.player)
        dv = hand_value(self.dealer)
        self.speak(f"Your cards: {card_str(self.player[0])} {card_str(self.player[1])}. Total {pv}. Dealer shows {card_str(self.dealer[0])}.")

    def _hit(self):
        self.player.append(self.deck.pop())
        pv = hand_value(self.player)
        self.speak(f"Got {card_str(self.player[-1])}. Total {pv}.")
        if pv > 21:
            self.result = "Bust! You lose."
            self.balance -= self.bet
            self.phase = "result"
            self.speak(self.result)

    def _stand(self):
        self.phase = "dealer"
        while hand_value(self.dealer) < 17:
            self.dealer.append(self.deck.pop())
        dv = hand_value(self.dealer)
        pv = hand_value(self.player)
        if dv > 21:
            self.result = f"Dealer busts with {dv}. You win!"
            self.balance += self.bet
        elif dv > pv:
            self.result = f"Dealer has {dv}, you have {pv}. You lose."
            self.balance -= self.bet
        elif dv < pv:
            self.result = f"Dealer has {dv}, you have {pv}. You win!"
            self.balance += self.bet
        else:
            self.result = f"Both have {pv}. Push."
        self.phase = "result"
        self.speak(self.result)

    def _double(self):
        if self.balance >= self.bet * 2:
            self.bet *= 2
            self.player.append(self.deck.pop())
            pv = hand_value(self.player)
            self.speak(f"Doubled. Got {card_str(self.player[-1])}. Total {pv}.")
            if pv > 21:
                self.result = "Bust! You lose."
                self.balance -= self.bet
                self.phase = "result"
                self.speak(self.result)
            else:
                self._stand()
        else:
            self.speak("Not enough balance to double.")

    def _render(self):
        lines = [f"Balance: ${self.balance}  Bet: ${self.bet}"]
        lines.append("")
        if self.phase in ("play", "dealer", "result"):
            dv = hand_value(self.dealer) if self.phase != "play" else VALUES[self.dealer[0][0]]
            d_str = " ".join([card_str(c) for c in self.dealer]) if self.phase != "play" else f"{card_str(self.dealer[0])} ??"
            lines.append(f"Dealer ({dv}): {d_str}")
            pv = hand_value(self.player)
            p_str = " ".join([card_str(c) for c in self.player])
            lines.append(f"You ({pv}): {p_str}")
            lines.append("")

        if self.phase == "bet":
            lines.append(f"Bet: ${self.bet}")
            opts = ["Decrease Bet", "Increase Bet", "Deal", "Exit"]
            for i, o in enumerate(opts):
                lines.append(f"{'>' if i == self.cursor else ' '} {o}")
        elif self.phase == "play":
            opts = ["Hit", "Stand", "Double"]
            for i, o in enumerate(opts):
                lines.append(f"{'>' if i == self.cursor else ' '} {o}")
        elif self.phase == "result":
            lines.append(self.result)
            lines.append("")
            lines.append("Enter to play again. Escape to exit.")

        return "\n".join(lines)

    def on_focus(self):
        self.speak(f"Blackjack. Balance ${self.balance}. Place your bet.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.phase == "result":
            if vk == win32con.VK_RETURN:
                self.bet = min(10, self.balance)
                self.phase = "bet"
                self.cursor = 0
                self.speak(f"Balance ${self.balance}. Place your bet.")
                self.window.update_text(self._render())
            return

        if vk == win32con.VK_UP:
            if self.phase == "bet":
                self.cursor = (self.cursor - 1) % 4
            elif self.phase == "play":
                self.cursor = (self.cursor - 1) % 3
        elif vk == win32con.VK_DOWN:
            if self.phase == "bet":
                self.cursor = (self.cursor + 1) % 4
            elif self.phase == "play":
                self.cursor = (self.cursor + 1) % 3
        elif vk == win32con.VK_LEFT:
            if self.phase == "bet" and self.cursor == 0:
                self.bet = max(5, self.bet - 5)
                self.speak(f"Bet ${self.bet}.")
        elif vk == win32con.VK_RIGHT:
            if self.phase == "bet" and self.cursor == 0:
                self.bet = min(self.balance, self.bet + 5)
                self.speak(f"Bet ${self.bet}.")
        elif vk == win32con.VK_RETURN:
            if self.phase == "bet":
                if self.cursor == 0:
                    self.bet = max(5, self.bet - 5)
                elif self.cursor == 1:
                    self.bet = min(self.balance, self.bet + 5)
                elif self.cursor == 2:
                    if self.bet > 0:
                        self._deal()
                elif self.cursor == 3:
                    self.exit_app()
                    return
            elif self.phase == "play":
                if self.cursor == 0:
                    self._hit()
                elif self.cursor == 1:
                    self._stand()
                elif self.cursor == 2:
                    self._double()

        self.window.update_text(self._render())

    def get_help_text(self):
        return "Blackjack. Arrows to navigate menu and adjust bet. Enter to select. Hit to draw, Stand to hold, Double to double down."
