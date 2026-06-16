import random
import win32con
from core.app_base import SoftApp
from core.menu import MenuSystem, MenuNode


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
        self.menu = None
        self._build_menu()

    def _build_menu(self):
        mod_str = f" + {self.modifier}" if self.modifier > 0 else (f" - {abs(self.modifier)}" if self.modifier < 0 else "0")
        root = MenuNode("Dice Roller")
        root.add_child(MenuNode(f"Number of Dice: {self.num_dice}", self._adjust_num_dice))
        root.add_child(MenuNode(f"Dice Type: d{self.dice_type}", self._adjust_dice_type))
        root.add_child(MenuNode(f"Modifier: {mod_str}", self._adjust_modifier))
        root.add_child(MenuNode("Roll!", self._roll))
        if self.history:
            root.add_child(MenuNode("History", self._show_history))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _adjust_num_dice(self):
        self.num_dice = (self.num_dice % 20) + 1
        self.speak(f"{self.num_dice} dice.")
        self._build_menu()

    def _adjust_dice_type(self):
        types = [4, 6, 8, 10, 12, 20, 100]
        idx = types.index(self.dice_type) if self.dice_type in types else 1
        self.dice_type = types[(idx + 1) % len(types)]
        self.speak(f"d{self.dice_type}.")
        self._build_menu()

    def _adjust_modifier(self):
        self.modifier = (self.modifier + 1) % 21 - 10
        mod_str = f"plus {self.modifier}" if self.modifier > 0 else (f"minus {abs(self.modifier)}" if self.modifier < 0 else "no modifier")
        self.speak(f"Modifier: {mod_str}.")
        self._build_menu()

    def _roll(self):
        self.last_roll = [random.randint(1, self.dice_type) for _ in range(self.num_dice)]
        self.total = sum(self.last_roll) + self.modifier
        mod_str = f" + {self.modifier}" if self.modifier > 0 else (f" - {abs(self.modifier)}" if self.modifier < 0 else "")
        roll_str = f"Rolled {self.num_dice}d{self.dice_type}{mod_str}: {self.last_roll} = {self.total}"
        self.history.insert(0, roll_str)
        if len(self.history) > 20:
            self.history.pop()
        die_vals = ", ".join([str(v) for v in self.last_roll])
        self.speak(f"Rolled {die_vals}. Total {self.total}.")
        self._build_menu()
        self.window.update_text(self._render())

    def _show_history(self):
        lines = ["Roll History", ""]
        if not self.history:
            lines.append("No rolls yet.")
        else:
            for h in self.history[:15]:
                lines.append(f"  {h}")
        self.speak(f"{len(self.history)} rolls in history.")
        self.window.update_text("\n".join(lines))

    def _render(self):
        lines = ["Dice Roller", ""]
        if self.last_roll:
            die_vals = ", ".join([str(v) for v in self.last_roll])
            lines.append(f"Last: {die_vals} = {self.total}")
        return "\n".join(lines)

    def on_focus(self):
        self._build_menu()
        self.speak("Dice Roller. Choose dice and roll.")
        self.window.update_text(self._render())

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_SPACE:
            if self.manager.space_used_in_chord:
                return
            self.menu.next()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        self.window.update_text(self._render())

    def get_help_text(self):
        return "Dice Roller. Roll multiple dice with modifiers. Supports d4, d6, d8, d10, d12, d20, d100."
