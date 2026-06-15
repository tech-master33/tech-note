import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem


class GameCenter(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Game Center")
        root.add_child(MenuNode("Puzzle", self._open_puzzle))
        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _open_puzzle(self):
        from apps.puzzle_game import PuzzleGame
        self.manager.launch_app(lambda m, w: PuzzleGame(m, w))

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Game Center"
        self.speak("Game Center. " + title)
        self.window.update_text("Games: " + title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Games: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Games: " + item.title)

    def get_help_text(self):
        return "Game Center. Space for next, Backspace for previous. Enter to open a game. Escape to go back."
