import random
import time
import threading
import win32con
from core.app_base import SoftApp


class Snake(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.rows = 15
        self.cols = 30
        self.snake = [(7, 15), (7, 14), (7, 13)]
        self.direction = (0, 1)
        self.food = None
        self.score = 0
        self.high_score = 0
        self.game_over = False
        self.paused = False
        self._spawn_food()
        self._timer = None
        self._running = True

    def _spawn_food(self):
        empty = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in self.snake]
        if empty:
            self.food = random.choice(empty)

    def _tick(self):
        if self.game_over or self.paused or not self._running:
            return
        head = self.snake[0]
        new = (head[0] + self.direction[0], head[1] + self.direction[1])

        if new[0] < 0 or new[0] >= self.rows or new[1] < 0 or new[1] >= self.cols:
            self.game_over = True
            self.high_score = max(self.high_score, self.score)
            self.speak(f"Game over! Score {self.score}.")
            self.window.update_text(self._render())
            return

        if new in self.snake:
            self.game_over = True
            self.high_score = max(self.high_score, self.score)
            self.speak(f"Game over! Score {self.score}.")
            self.window.update_text(self._render())
            return

        self.snake = [new] + self.snake
        if new == self.food:
            self.score += 1
            self._spawn_food()
            self.speak(f"Ate food! Score {self.score}.")
        else:
            self.snake.pop()

        self.window.update_text(self._render())
        self._timer = threading.Timer(0.2, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _start_loop(self):
        if self._timer:
            self._timer.cancel()
        self._timer = threading.Timer(0.2, self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _render(self):
        lines = [f"Score: {self.score}  High: {self.high_score}"]
        lines.append("")
        for r in range(self.rows):
            row_str = ""
            for c in range(self.cols):
                if (r, c) == self.snake[0]:
                    row_str += "@"
                elif (r, c) in self.snake:
                    row_str += "O"
                elif (r, c) == self.food:
                    row_str += "*"
                else:
                    row_str += "."
            lines.append(row_str)

        lines.append("")
        if self.game_over:
            lines.append("Game over! Enter for new game. Escape to exit.")
        elif self.paused:
            lines.append("Paused. Space to resume.")
        else:
            lines.append("Arrows to turn. P to pause. Escape to exit.")
        return "\n".join(lines)

    def on_focus(self):
        self._running = True
        self.speak("Snake. Eat the stars to grow. Don't hit walls or yourself.")
        self.window.update_text(self._render())
        self._start_loop()

    def on_defocus(self):
        self._running = False
        if self._timer:
            self._timer.cancel()

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._running = False
            if self._timer:
                self._timer.cancel()
            self.exit_app()
            return

        if self.game_over:
            if vk == win32con.VK_RETURN:
                self.__init__(self.manager, self.window)
                self._running = True
                self._start_loop()
                self.speak("New game.")
                self.window.update_text(self._render())
            return

        if vk == 0x50:
            self.paused = not self.paused
            if not self.paused:
                self._start_loop()
            self.speak("Paused." if self.paused else "Resumed.")
            self.window.update_text(self._render())
            return

        if self.paused:
            return

        if vk == win32con.VK_UP and self.direction != (1, 0):
            self.direction = (-1, 0)
        elif vk == win32con.VK_DOWN and self.direction != (-1, 0):
            self.direction = (1, 0)
        elif vk == win32con.VK_LEFT and self.direction != (0, 1):
            self.direction = (0, -1)
        elif vk == win32con.VK_RIGHT and self.direction != (0, -1):
            self.direction = (0, 1)

    def get_help_text(self):
        return "Snake. Arrow keys to change direction. Eat stars to grow. Don't hit walls or yourself. P to pause."
