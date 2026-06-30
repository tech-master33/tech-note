import os
import json
import sys
import importlib
import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.config import TECH_SOFT

APPS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "apps")
INSTALLED_FILE = os.path.join(TECH_SOFT, "installed_apps.json")
RECENT_FILE = os.path.join(TECH_SOFT, "recent_games.json")
FAVORITES_FILE = os.path.join(TECH_SOFT, "favorite_games.json")


class GameCenter(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._recent = self._load_list(RECENT_FILE)
        self._favorites = self._load_list(FAVORITES_FILE)
        self._build_menu()

    def _load_list(self, path):
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    return json.load(f)
        except:
            pass
        return []

    def _save_list(self, path, data):
        try:
            with open(path, 'w') as f:
                json.dump(data, f)
        except:
            pass

    def _track_launch(self, name):
        self._recent = [g for g in self._recent if g != name]
        self._recent.append(name)
        self._save_list(RECENT_FILE, self._recent[-20:])

    def _is_favorite(self, name):
        return name in self._favorites

    def _toggle_favorite(self, name):
        if name in self._favorites:
            self._favorites = [g for g in self._favorites if g != name]
        else:
            self._favorites.append(name)
        self._save_list(FAVORITES_FILE, self._favorites)
        self._build_menu()
        self.menu.announce_current()

    def _build_menu(self):
        root = MenuNode("Game Center")

        if self._recent:
            recent_root = MenuNode("Recent")
            for name in reversed(self._recent[-5:]):
                recent_root.add_child(MenuNode(name + (" (fav)" if self._is_favorite(name) else ""), lambda n=name: self._launch_by_name(n)))
            root.add_child(recent_root)

        builtins = [
            ("Puzzle", "puzzle_game", "PuzzleGame"),
            ("Snake", "snake", "SnakeGame"),
            ("Solitaire", "solitaire", "SolitaireGame"),
            ("Sudoku", "sudoku", "SudokuGame"),
            ("Minesweeper", "minesweeper", "MinesweeperGame"),
            ("Memory Match", "memory_match", "MemoryMatchGame"),
            ("2048", "game2048", "Game2048"),
            ("Blackjack", "blackjack", "BlackjackGame"),
            ("Hangman", "hangman", "HangmanGame"),
            ("Connect Four", "connect_four", "ConnectFourGame"),
            ("Tic Tac Toe", "tictactoe", "TicTacToeGame"),
        ]

        for name, module, cls_name in builtins:
            label = name + (" (fav)" if self._is_favorite(name) else "")
            root.add_child(MenuNode(label, lambda m=module, c=cls_name, n=name: self._load_builtin(m, c, n)))

        installed_games = self._load_installed_games()
        for name, loader in installed_games:
            label = name + (" (fav)" if self._is_favorite(name) else "")
            root.add_child(MenuNode(label, lambda n=name, l=loader: self._track_and_launch(n, l)))

        if self._favorites:
            fav_root = MenuNode("Favorites")
            for name in self._favorites:
                fav_root.add_child(MenuNode(name, lambda n=name: self._launch_by_name(n)))
            root.add_child(fav_root)

        root.add_child(MenuNode("Back", self.exit_app))
        self.menu = MenuSystem(root, self.speak)

    def _track_and_launch(self, name, loader):
        self._track_launch(name)
        loader()

    def _launch_by_name(self, name):
        for n, m, cls_name in [
            ("Puzzle", "puzzle_game", "PuzzleGame"),
            ("Snake", "snake", "SnakeGame"),
            ("Solitaire", "solitaire", "SolitaireGame"),
            ("Sudoku", "sudoku", "SudokuGame"),
            ("Minesweeper", "minesweeper", "MinesweeperGame"),
            ("Memory Match", "memory_match", "MemoryMatchGame"),
            ("2048", "game2048", "Game2048"),
            ("Blackjack", "blackjack", "BlackjackGame"),
            ("Hangman", "hangman", "HangmanGame"),
            ("Connect Four", "connect_four", "ConnectFourGame"),
            ("Tic Tac Toe", "tictactoe", "TicTacToeGame"),
        ]:
            if n == name:
                self._load_builtin(m, cls_name, n)
                return
        self.speak(f"Game {name} not found.")

    def _load_builtin(self, module_name, class_name, display_name):
        try:
            self._track_launch(display_name)
            mod = importlib.import_module(f"apps.{module_name}")
            cls = getattr(mod, class_name)
            self.manager.launch_app(lambda m, w, c=cls: c(m, w))
        except Exception as e:
            self.speak(f"Failed to load {module_name}.")

    def _load_installed_games(self):
        games = []
        if not os.path.exists(INSTALLED_FILE):
            return games
        try:
            with open(INSTALLED_FILE, 'r') as f:
                installed = json.load(f)
        except:
            return games

        for app_id, info in installed.items():
            category = info.get("category", "").lower()
            if category != "games":
                continue
            filename = info.get("filename", "")
            entry_point = info.get("entry_point", "")
            name = info.get("name", app_id)
            filepath = os.path.join(APPS_DIR, filename)
            if not os.path.exists(filepath) or not filename.endswith('.py'):
                continue
            mod_name = filename[:-3]

            def make_loader(mn=mod_name, ep=entry_point, nm=name):
                def load():
                    self._track_launch(nm)
                    try:
                        if mn not in sys.modules:
                            if APPS_DIR not in sys.path:
                                sys.path.insert(0, APPS_DIR)
                            mod = importlib.import_module(mn)
                        else:
                            mod = sys.modules[mn]
                        if ep and hasattr(mod, ep):
                            cls = getattr(mod, ep)
                        else:
                            classes = [v for v in vars(mod).values()
                                       if isinstance(v, type) and hasattr(v, 'on_key') and hasattr(v, 'exit_app')]
                            cls = classes[0] if classes else None
                        if cls:
                            self.manager.launch_app(lambda m, w, c=cls: c(m, w))
                    except Exception as e:
                        print(f"Failed to load game {mn}: {e}")
                return load

            games.append((name, make_loader()))
        return games

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Game Center"
        self.speak("Game Center. " + title)
        self.window.update_text("Games: " + title)

    def on_key(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_F5 and self.menu.get_current_item():
            name = self.menu.get_current_item().title.split(" (")[0]
            self._toggle_favorite(name)
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
        return "Game Center. Space for next, Backspace for previous. Enter to open a game. F5 to favorite or unfavorite a game. Escape to go back."
