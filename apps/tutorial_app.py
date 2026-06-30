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
        root.add_child(MenuNode("Phase 5 Apps", lambda: self._show_topic("phase5")))
        root.add_child(MenuNode("Phase 6 Apps", lambda: self._show_topic("phase6")))
        root.add_child(MenuNode("Global Chords", lambda: self._show_topic("chords")))
        self.menu = MenuSystem(root, self.speak)
        self._topic_mode = None

    def _show_topic(self, topic):
        self._topic_mode = topic
        texts = {
            "nav": "Navigation Basics. Use Space to move to the next item. Use Backspace to move to the previous item. Press Enter to select an item. Press Escape to go back or exit. Use the Plus key to stop speech. Use first letter navigation by pressing the first letter of a menu item.",
            "menu": "Main Menu. The main menu contains your applications: Tutorial, Word Processor, Settings, Planner, Address List, Email, Internet, Chat, Media Center, Calculator, File Manager, and more. Navigate with Space and Backspace. Press Enter to open an app. Press Escape to return to the main menu from an app.",
            "tts_menu": "TTS Menu. Press Space plus O to open Options, then select TTS Menu. Here you can change TTS Engine, Speech Rate, Volume, Voice Selection, and Punctuation Level. Navigate with Space and Backspace, adjust values with Plus and Minus. Press Enter to save, Escape to cancel.",
            "keyboard_menu": "Keyboard Menu. Press Space plus O to open Options, then select Keyboard Menu. Here you can toggle Character Echo, Word Echo, and rebind your keys. Character Echo speaks each letter you type. Word Echo speaks completed words when you press Space.",
            "typing": "Typing and Editing. When in a text field, type normally. Use Enter to submit, Backspace to delete. Text input fields support Character Echo and Word Echo based on your Keyboard Menu settings.",

            "shortcuts": "Shortcuts. F1 for context help. Shift F1 for Tutorial. F5 for time, date, and battery status. Backtick for Power Menu. Space plus O for Options. Space plus Q for Quick Switch. Space plus C for Clipboard History. Space plus R to repeat last speech. Space plus V to cycle voice profiles. Space plus L for Run Dialog. Space plus H for Notification History. Space plus S for Session Manager. Escape exits apps. Plus key stops speech.",

            "chords": "Global Chords. Space plus O opens Options. Space plus N reads notifications. Space plus C opens Clipboard History. Space plus R repeats last speech. Space plus V cycles voice profiles. Space plus L opens Run Dialog. Space plus H opens Notification History. Space plus S opens Session Manager. Space plus Q opens Quick Switch. Shift F1 opens Tutorial. F12 opens Audio Control Panel.",

            "phase5": "Phase 5 App Overhauls. Multi Tab Browser with tab switching using T for new tab and W to close. RSS Reader with feed management. Tech Edit with F9 snippet insertion and 11 built-in snippets. Terminal with command history saved to file and Tab auto-complete. Calculator with four modes including scientific, programmer, and unit converter. Media Player with playlists, shuffle, repeat, and podcast support. Notes with categories, tags, and search. File Manager with archive extraction and recursive search. Address Book with email and group fields. Planner with categories, priorities, and due dates. Habit Tracker with notes and weekly view. FM Radio with 20 stations and search.",

            "phase6": "Phase 6 New Apps. Expense Tracker to log expenses by category with monthly totals and CSV export. Password Manager to store credentials with built-in password generator. Sleep Timer with fade out, stop audio, or shutdown options. Ambient Sound Generator with 8 sounds including rain, ocean, and white noise. Pomodoro Timer with configurable work and break times. Network Diagnostics for ping, DNS lookup, and traceroute. App Usage Stats tracking time spent in each app. Auto Backup service for key data files. Bulk File Operations for rename, delete, organize, and find duplicates. Disk Cleanup to analyze space and remove temp files.",
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
        return "Tutorial. Select a topic to learn about TechNote navigation. Topics include navigation, shortcuts, global chords, Phase 5 app overhauls, and Phase 6 new apps. Press Escape to exit."
