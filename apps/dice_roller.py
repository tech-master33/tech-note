import random
import win32con
from core.app_base import SoftApp


DICE_FACES = {
    1: ["  +-----+  ",
        "  |     |  ",
        "  |  *  |  ",
        "  |     |  ",
        "  +-----+  "],
    2: ["  +-----+  ",
        "  | *   |  ",
        "  |     |  ",
        "  |   * |  ",
        "  +-----+  "],
    3: ["  +-----+  ",
        "  | *   |  ",
        "  |  *  |  ",
        "  |   * |  ",
        "  +-----+  "],
    4: ["  +-----+  ",
        "  | * * |  ",
        "  |     |  ",
        "  | * * |  ",
        "  +-----+  "],
    5: ["  +-----+  ",
        "  | * * |  ",
        "  |  *  |  ",
        "  | * * |  ",
        "  +-----+  "],
    6: ["  +-----+  ",
        "  | * * |  ",
        "  | * * |  ",
        "  | * * |  ",
        "  +-----+  "],
}


class DiceRoller(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self.num_dice = 1
        self.dice_type = 6
        self.modifier = 0
        self.last_roll = []
        self.total = 0
        self.history = []
        self.menu_cursor = 0
        self.menu_items = ["Number of Dice", "Dice Type", "Modifier", "Roll", "History", "Exit"]

    def _roll(self):
        self.last_roll = [random.randint(1, self.dice_type) for _ in range(self.num_dice)]
        self.total = sum(self.last_roll) + self.modifier
        mod_str = f" + {self.modifier}" if self.modifier > 0 else (f" - {abs(self.modifier)}" if self.modifier < 0 else "")
        roll_str = f"Rolled {self.num_dice}d{self.dice_type}{mod_str}: {self.last_roll} = {self.total}"
        self.history.insert(0, roll_str)
        if len(self.history) > 20:
            self.history.pop()
        self.speak(f"{self.total}!")
        self.window.update_text(self._render())

    def _render(self):
        lines = ["Dice Roller", ""]
        lines.append(f"  {'>' if self.menu_cursor == 0 else ' '} Number of Dice: {self.num_dice}")
        lines.append(f"  {'>' if self.menu_cursor == 1 else ' '} Dice Type: d{self.dice_type}")
        lines.append(f"  {'>' if self.menu_cursor == 2 else ' '} Modifier: {'+' if self.modifier >= 0 else ''}{self.modifier}")
        lines.append(f"  {'>' if self.menu_cursor == 3 else ' '} Roll!")
        lines.append(f"  {'>' if self.menu_cursor == 4 else ' '} History")
        lines.append(f"  {'>' if self.menu_cursor == 5 else ' '} Exit")
        lines.append("")

        if self.last_roll:
            lines.append("Last Roll:")
            for i, val in enumerate(self.last_roll):
                for line in DICE_FACES.get(val, DICE_FACES[1]):
                    lines.append(f"  {line}")
                lines.append("")
            mod_str = f" + {self.modifier}" if self.modifier > 0 else (f" - {abs(self.modifier)}" if self.modifier < 0 else "")
            lines.append(f"  Total: {self.total}{mod_str}")

        lines.append("")
        lines.append("Up/Down: navigate. Left/Right: adjust. Enter: select.")
        return "\n".join(lines)

    def _render_history(self):
        lines = ["Roll History", ""]
        if not self.history:
            lines.append("No rolls yet.")
        else:
            for h in self.history[:15]:
                lines.append(f"  {h}")
        lines.append("")
        lines.append("Escape to go back.")
        return "\n".join(lines)

    def on_focus(self):
        self.menu_cursor = 0
        self.speak("Dice Roller. Choose dice and roll.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if self.menu_cursor == 5 and self.menu_cursor != 5:
            pass

        if vk == win32con.VK_UP:
            self.menu_cursor = (self.menu_cursor - 1) % len(self.menu_items)
        elif vk == win32con.VK_DOWN:
            self.menu_cursor = (self.menu_cursor + 1) % len(self.menu_items)
        elif vk == win32con.VK_LEFT:
            if self.menu_cursor == 0:
                self.num_dice = max(1, self.num_dice - 1)
            elif self.menu_cursor == 1:
                types = [4, 6, 8, 10, 12, 20, 100]
                idx = types.index(self.dice_type) if self.dice_type in types else 1
                self.dice_type = types[max(0, idx - 1)]
            elif self.menu_cursor == 2:
                self.modifier -= 1
        elif vk == win32con.VK_RIGHT:
            if self.menu_cursor == 0:
                self.num_dice = min(20, self.num_dice + 1)
            elif self.menu_cursor == 1:
                types = [4, 6, 8, 10, 12, 20, 100]
                idx = types.index(self.dice_type) if self.dice_type in types else 1
                self.dice_type = types[min(len(types) - 1, idx + 1)]
            elif self.menu_cursor == 2:
                self.modifier += 1
        elif vk == win32con.VK_RETURN:
            if self.menu_cursor == 3:
                self._roll()
            elif self.menu_cursor == 4:
                self.window.update_text(self._render_history())
                self.speak("History.")
                return
            elif self.menu_cursor == 5:
                self.exit_app()
                return

        self.window.update_text(self._render())

    def get_help_text():
        return "Dice Roller. Roll multiple dice with modifiers. Supports d4, d6, d8, d10, d12, d20, d100."
