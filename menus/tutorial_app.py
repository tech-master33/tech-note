import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem

CATEGORIES = [
    ("Navigation", ["nav", "menu"]),
    ("Settings", ["tts_menu", "keyboard_menu", "audio_menu", "braille_menu"]),
    ("Usage", ["typing", "shortcuts", "apps_overview"]),
    ("Advanced", ["power_menu", "lock_screen", "customization"]),
]

TOPIC_TEXTS = {
    "nav": "Navigation Basics. Use Space to move to the next item. Use Backspace to move to the previous item. Press Enter to select an item. Press Escape to go back or exit. Use the Plus key to stop speech. Use first letter navigation by pressing the first letter of a menu item.",
    "menu": "Main Menu. The main menu contains your applications: Tutorial, Word Processor, Settings, Planner, Address List, Email, Internet, Chat, Media Center, Calculator, and File Manager. Navigate with Space and Backspace. Press Enter to open an app. Press Escape to return to the main menu from an app.",
    "tts_menu": "TTS Menu. Press Space plus O to open Options, then select TTS Menu. Here you can change TTS Engine, Speech Rate, Volume, Voice Selection, and Punctuation Level. Navigate with Space and Backspace, adjust values with Plus and Minus. Press Enter to save, Escape to cancel.",
    "keyboard_menu": "Keyboard Menu. Press Space plus O to open Options, then select Keyboard Menu. Here you can toggle Character Echo, Word Echo, and rebind your keys. Character Echo speaks each letter you type. Word Echo speaks completed words when you press Space.",
    "audio_menu": "Audio Menu. Press Space plus O to open Options, then select Audio Menu. Here you can adjust Volume Ducking and change the Sound Scheme. Volume Ducking reduces other sounds while speech is active.",
    "braille_menu": "Braille Menu. Press Space plus O to open Options, then select Braille Menu. Here you can configure Braille Display and Braille Grade settings for supported braille displays.",
    "typing": "Typing and Editing. When in a text field, type normally. Use Enter to submit, Backspace to delete. Text input fields support Character Echo and Word Echo based on your Keyboard Menu settings.",
    "shortcuts": "Shortcuts. F1 for context help. Shift F1 for Tutorial. F5 for time, date, and battery status. Backtick for Power Menu. Space plus O for Options. Escape exits apps. Plus key stops speech.",
    "apps_overview": "Apps Overview. Tech-Note includes a Word Processor for editing documents, a Calculator for math, a Planner for tasks, an Address List for contacts, Email and Chat for communication, and Internet for web browsing.",
    "power_menu": "Power Menu. Press Backtick to open the Power Menu. From here you can restart, shutdown, sleep, schedule shutdown at a specific time, or hibernate Tech-Note.",
    "lock_screen": "Lock Screen. Tech-Note can be locked with a PIN or password. After too many wrong attempts, the device locks for 30 seconds. A custom message can be displayed on the lock screen.",
    "customization": "Customization. From the Options menu you can customize speech, keyboard behavior, audio, braille, and import or export settings. You can also add pronunciation dictionary entries.",
}

class TutorialApp(SoftApp):
    app_id = "tutorial"
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._topic_mode = None
        self._walkthrough_step = None
        self._walkthrough_steps = []
        self._category_mode = None
        self._build_main_menu()

    def _build_main_menu(self):
        root = MenuNode("Tutorial")
        categories = root.add_child(MenuNode("Categories"))
        for cat_name, _ in CATEGORIES:
            categories.add_child(MenuNode(cat_name, lambda cn=cat_name: self._show_category(cn)))
        root.add_child(MenuNode("Interactive Walkthrough", self._start_walkthrough))
        root.add_child(MenuNode("All Topics", self._show_all_topics))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)

    def _show_category(self, cat_name):
        self._category_mode = cat_name
        root = MenuNode(cat_name)
        for name, topics in CATEGORIES:
            if name == cat_name:
                for t in topics:
                    root.add_child(MenuNode(TOPIC_TEXTS[t].split(".")[0], lambda tt=t: self._show_topic(tt)))
                break
        root.add_child(MenuNode("Back", self._exit_category))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)
        self.menu.announce_current()

    def _exit_category(self):
        self._category_mode = None
        self._build_main_menu()
        self.menu.announce_current()

    def _show_all_topics(self):
        root = MenuNode("All Topics")
        for key in sorted(TOPIC_TEXTS):
            title = TOPIC_TEXTS[key].split(".")[0]
            root.add_child(MenuNode(title, lambda k=key: self._show_topic(k)))
        root.add_child(MenuNode("Back", self._build_main_menu))
        self.menu = MenuSystem(root, self.speak, stop_func=self.stop)
        self.menu.announce_current()

    def _start_walkthrough(self):
        self._walkthrough_steps = [
            ("Welcome to the Tech-Note interactive walkthrough. Press Space to continue.", None),
            ("Step 1: Use Space to navigate to the next menu item. Try it now.", "space"),
            ("Good. Step 2: Use Backspace to navigate to the previous menu item. Try it now.", "backspace"),
            ("Step 3: Press Enter to select an item. Try it now.", "enter"),
            ("Step 4: Press Escape to go back. Try it now.", "escape"),
            ("Congratulations. You have completed the interactive walkthrough. Press Enter or Escape to finish.", None),
        ]
        self._walkthrough_step = 0
        self.speak(self._walkthrough_steps[0][0])
        self.window.update_text("Walkthrough: " + self._walkthrough_steps[0][0])

    def _advance_walkthrough(self):
        self._walkthrough_step += 1
        if self._walkthrough_step >= len(self._walkthrough_steps):
            self._walkthrough_step = None
            self._walkthrough_steps = []
            self.speak("Walkthrough completed.")
            self._build_main_menu()
            return
        text, expected = self._walkthrough_steps[self._walkthrough_step]
        self.speak(text)
        self.window.update_text("Walkthrough: " + text)

    def _show_topic(self, topic):
        self._topic_mode = topic
        text = TOPIC_TEXTS.get(topic, "Topic not found.")
        self.speak(text)
        self.window.update_text(f"Tutorial: {topic.replace('_', ' ').title()}")

    def on_focus(self):
        if self._walkthrough_step is not None:
            return
        item = self.menu.get_current_item()
        title = item.title if item else "Tutorial"
        self.speak("Tutorial. " + title)
        self.window.update_text("Tutorial: " + title)

    def on_key(self, vk):
        if self._walkthrough_step is not None:
            if self._walkthrough_step < len(self._walkthrough_steps):
                _, expected = self._walkthrough_steps[self._walkthrough_step]
                if expected is None:
                    self._advance_walkthrough()
                elif (expected == "space" and vk == win32con.VK_SPACE) or \
                     (expected == "backspace" and vk == win32con.VK_BACK) or \
                     (expected == "enter" and vk == win32con.VK_RETURN) or \
                     (expected == "escape" and vk == win32con.VK_ESCAPE):
                    self._advance_walkthrough()
            return

        if self._topic_mode:
            if vk in (win32con.VK_ESCAPE, win32con.VK_RETURN, win32con.VK_BACK):
                self._topic_mode = None
                self._build_main_menu()
                self.menu.announce_current()
            return

        if vk == win32con.VK_ESCAPE:
            if self._category_mode:
                self._exit_category()
                return
            self.exit_app()
            return

        if vk == win32con.VK_BACK:
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
        if self._walkthrough_step is not None or self._topic_mode:
            return
        if vk == win32con.VK_SPACE:
            self.menu.next()
            item = self.menu.get_current_item()
            if item:
                self.window.update_text("Tutorial: " + item.title)

    def get_help_text(self):
        return "Tutorial. Select a topic to learn about TechNote navigation. Press Escape to exit."
