import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem

class TutorialApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._build_main_menu()

    def _build_main_menu(self):
        root = MenuNode("Tutorial")
        root.add_child(MenuNode("Navigation Basics", lambda: self._show_topic("nav")))
        root.add_child(MenuNode("Main Menu", lambda: self._show_topic("menu")))
        root.add_child(MenuNode("TTS Menu", lambda: self._show_topic("tts_menu")))
        root.add_child(MenuNode("Keyboard Menu", lambda: self._show_topic("keyboard_menu")))
        root.add_child(MenuNode("Typing and Editing", lambda: self._show_topic("typing")))
        root.add_child(MenuNode("Shortcuts", lambda: self._show_topic("shortcuts")))
        self.menu = MenuSystem(root, self.speak)
        self._topic_mode = None

    def _show_topic(self, topic):
        self._topic_mode = topic
        texts = {
            "nav": "Navigation Basics. Use Space or Down Arrow to move to the next item. Use Backspace or Up Arrow to move to the previous item. Press Enter to select an item. Press Escape to go back or exit. Use the Plus key to stop speech. Use first letter navigation by pressing the first letter of a menu item.",
            "menu": "Main Menu. The main menu contains your applications: Tutorial, Word Processor, Settings, Planner, Address List, Email, Internet, Chat, Media Center, Calculator, and File Manager. Navigate with Space and Backspace. Press Enter to open an app. Press Escape to return to the main menu from an app.",
            "tts_menu": "TTS Menu. Press Space plus O to open Options, then select TTS Menu. Here you can change TTS Engine, Speech Rate, Volume, Voice Selection, and Punctuation Level. Navigate with arrows, adjust values with Plus and Minus. Press Enter to save, Escape to cancel.",
            "keyboard_menu": "Keyboard Menu. Press Space plus O to open Options, then select Keyboard Menu. Here you can toggle Character Echo, Word Echo, and rebind your keys. Character Echo speaks each letter you type. Word Echo speaks completed words when you press Space.",
            "typing": "Typing and Editing. When in a text field, type normally. Use Enter to submit, Backspace to delete. Text input fields support Character Echo and Word Echo based on your Keyboard Menu settings.",
            "shortcuts": "Shortcuts. F1 for context help. Shift F1 for Tutorial. F5 for time, date, and battery status. Backtick for Power Menu. Space plus O for Options. Escape exits apps. Plus key stops speech.",
        }
        self.speak(texts.get(topic, "Topic not found."))
        self.window.update_text(f"Tutorial: {topic.replace('_', ' ').title()}")

    def on_focus(self):
        item = self.menu.get_current_item()
        title = item.title if item else "Tutorial"
        self.speak("Tutorial. " + title)
        self.window.update_text("Tutorial: " + title)

    def on_key(self, vk):
        if self._topic_mode:
            if vk in (win32con.VK_ESCAPE, win32con.VK_RETURN, win32con.VK_BACK):
                self._topic_mode = None
                self._build_main_menu()
                self.menu.announce_current()
            return

        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return

        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_DOWN:
            self.menu.next()
        elif vk == win32con.VK_UP:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            char = chr(vk)
            self.menu.first_letter_nav(char)

        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Tutorial: " + item.title)

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if self._topic_mode:
                return
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Tutorial: " + item.title)

    def get_help_text(self):
        return "Tutorial. Select a topic to learn about TechNote navigation. Press Escape to exit."
