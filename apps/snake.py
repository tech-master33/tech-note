import random
import time
import threading
import json
import os
import win32con
from core.app_base import SoftApp

SCORES_FILE = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'snake_scores.json')


class Snake(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.rows = 15
        self.cols = 25
        self.snake = []
        self.direction = (0, 1)
        self.next_direction = (0, 1)
        self.food = None
        self.special_food = None
        self.special_timer = 0
        self.score = 0
        self.high_score = 0
        self.speed_level = 1
        self.game_over = False
        self.paused = False
        self.started = False
        self._timer = None
        self._running = True
        self._last_move = 0
        self._scores = self._load_scores()
        self._new_game()

    def _load_scores(self):
        if os.path.exists(SCORES_FILE):
            try:
                with open(SCORES_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {"high": 0}

    def _save_scores(self):
        os.makedirs(os.path.dirname(SCORES_FILE), exist_ok=True)
        with open(SCORES_FILE, 'w') as f:
            json.dump(self._scores, f)

    def _new_game(self):
        mid_r = self.rows // 2
        mid_c = self.cols // 2
        self.snake = [(mid_r, mid_c), (mid_r, mid_c - 1), (mid_r, mid_c - 2)]
        self.direction = (0, 1)
        self.next_direction = (0, 1)
        self.food = None
        self.special_food = None
        self.special_timer = 0
        self.score = 0
        self.speed_level = 1
        self.game_over = False
        self.paused = False
        self.started = False
        self._last_move = time.time()
        self._spawn_food()
        self._scores = self._load_scores()
        self.high_score = self._scores.get("high", 0)

    def _get_speed(self):
        speeds = {1: 0.22, 2: 0.18, 3: 0.14, 4: 0.11, 5: 0.08}
        return speeds.get(self.speed_level, 0.08)

    def _update_speed(self):
        if self.score >= 20:
            self.speed_level = 5
        elif self.score >= 15:
            self.speed_level = 4
        elif self.score >= 10:
            self.speed_level = 3
        elif self.score >= 5:
            self.speed_level = 2
        else:
            self.speed_level = 1

    def _spawn_food(self):
        empty = [(r, c) for r in range(self.rows) for c in range(self.cols)
                 if (r, c) not in self.snake and (r, c) != self.special_food]
        if empty:
            self.food = random.choice(empty)

    def _spawn_special(self):
        if self.special_food or self.score < 5:
            return
        empty = [(r, c) for r in range(self.rows) for c in range(self.cols)
                 if (r, c) not in self.snake and (r, c) != self.food]
        if empty and random.random() < 0.3:
            self.special_food = random.choice(empty)
            self.special_timer = 8

    def _tick(self):
        if self.game_over or self.paused or not self._running:
            return

        now = time.time()
        if now - self._last_move < self._get_speed():
            self._timer = threading.Timer(self._get_speed(), self._tick)
            self._timer.daemon = True
            self._timer.start()
            return

        self._last_move = now
        self.direction = self.next_direction

        head = self.snake[0]
        new = (head[0] + self.direction[0], head[1] + self.direction[1])

        if new[0] < 0 or new[0] >= self.rows or new[1] < 0 or new[1] >= self.cols:
            self._end_game()
            return

        if new in self.snake:
            self._end_game()
            return

        self.snake = [new] + self.snake

        ate = False
        if new == self.food:
            self.score += 1
            self._spawn_food()
            self._spawn_special()
            self.speak("Munch!")
            ate = True
        elif new == self.special_food:
            self.score += 3
            self.special_food = None
            self.special_timer = 0
            self.speak("Bonus! Plus 3!")
            ate = True

        if not ate:
            self.snake.pop()

        if self.special_food:
            self.special_timer -= 1
            if self.special_timer <= 0:
                self.special_food = None

        self._update_speed()
        self.window.update_text(self._render())

        self._timer = threading.Timer(self._get_speed(), self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _end_game(self):
        self.game_over = True
        if self.score > self.high_score:
            self.high_score = self.score
            self._scores["high"] = self.high_score
            self._save_scores()
            self.speak(f"Game over! New high score: {self.score}!")
        else:
            self.speak(f"Game over! Score {self.score}.")
        self.window.update_text(self._render())

    def _start_loop(self):
        if self._timer:
            self._timer.cancel()
        self._last_move = time.time()
        self._timer = threading.Timer(self._get_speed(), self._tick)
        self._timer.daemon = True
        self._timer.start()

    def _render(self):
        speed_names = {1: "Slow", 2: "Medium", 3: "Fast", 4: "Very Fast", 5: "Insane"}
        lines = [f"Score: {self.score}  High: {self.high_score}  Speed: {speed_names.get(self.speed_level, '?')}"]
        lines.append("")

        border = "+" + "---+" * self.cols
        lines.append(border)
        for r in range(self.rows):
            row_str = "|"
            for c in range(self.cols):
                if (r, c) == self.snake[0]:
                    row_str += " @ "
                elif (r, c) in self.snake:
                    row_str += " O "
                elif (r, c) == self.food:
                    row_str += " * "
                elif (r, c) == self.special_food:
                    row_str += " + "
                else:
                    row_str += "   "
                row_str += "|"
            lines.append(row_str)
            lines.append(border)

        lines.append("")
        lines.append("* = food (+1)   + = bonus (+3)")
        lines.append("")

        if self.game_over:
            if self.score == self.high_score and self.score > 0:
                lines.append("NEW HIGH SCORE!")
            lines.append("Enter for new game. Escape to exit.")
        elif self.paused:
            lines.append("PAUSED. P to resume.")
        elif not self.started:
            lines.append("Press any arrow key to start!")
        else:
            lines.append("Arrows to turn. P to pause. Escape to exit.")
        return "\n".join(lines)

    def on_focus(self):
        self._running = True
        self.speak(f"Snake. High score: {self.high_score}. Press an arrow key to start.")
        self.window.update_text(self._render())

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
                self._new_game()
                self._running = True
                self.speak("New game. Press an arrow key to start.")
                self.window.update_text(self._render())
            return

        if vk == 0x50:
            self.paused = not self.paused
            if not self.paused and self.started:
                self._start_loop()
            self.speak("Paused." if self.paused else "Resumed.")
            self.window.update_text(self._render())
            return

        if self.paused:
            return

        moved = False
        if vk == win32con.VK_UP and self.direction != (1, 0):
            self.next_direction = (-1, 0)
            moved = True
        elif vk == win32con.VK_DOWN and self.direction != (-1, 0):
            self.next_direction = (1, 0)
            moved = True
        elif vk == win32con.VK_LEFT and self.direction != (0, 1):
            self.next_direction = (0, -1)
            moved = True
        elif vk == win32con.VK_RIGHT and self.direction != (0, -1):
            self.next_direction = (0, 1)
            moved = True

        if moved and not self.started:
            self.started = True
            self._start_loop()
            self.speak("Go!")

    def get_help_text(self):
        return "Snake. Arrow keys to change direction. Eat stars to grow. Bonus items worth 3 points. Speed increases as you score."
