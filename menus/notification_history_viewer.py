import win32con
from core.app_base import SoftApp
from core.menu import MenuNode, MenuSystem
from core.notification_center import get_center as get_notification_center


class NotificationHistoryViewer(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        self._notifications = get_notification_center()
        self._build_menu()

    def _build_menu(self):
        root = MenuNode("Notification History")
        all_notifs = self._notifications.get_all()
        if not all_notifs:
            root.add_child(MenuNode("No notifications"))
        else:
            for notif in reversed(all_notifs):
                text = f"{notif['source']}: {notif['text'][:80]}"
                root.add_child(MenuNode(text))
            root.add_child(MenuNode("Clear All", lambda: self._clear_all()))
        self.menu = MenuSystem(root, self.speak)
        self._notifications.mark_read()

    def _clear_all(self):
        self._notifications._notifications.clear()
        self._notifications._save()
        self.speak("All notifications cleared")
        self.exit_app()

    def on_focus(self):
        self._build_menu()
        self.menu.announce_current()

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
        self._update_display()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            self.menu.next()
            self._update_display()

    def _update_display(self):
        item = self.menu.get_current_item()
        if item:
            self.window.update_text("Notifications: " + item.title)
