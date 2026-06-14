import os
import json
import win32con
import win32api
from core.app_base import SoftApp
from core.chat_client import ChatClient, ChatError
from core.menu import MenuNode, MenuSystem

DATA_DIR = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'chat')
PROFILE_FILE = os.path.join(DATA_DIR, 'profile.json')
SERVER_URL = 'https://technote-messages-280.netlify.app/api'

STATE_LOGIN = 0
STATE_REGISTER = 1
STATE_MENU = 2
STATE_ROOM_LIST = 3
STATE_ROOM_CHAT = 4
STATE_USER_LIST = 5
STATE_COMPOSING = 6
STATE_CHANGE_PASSWORD = 7
STATE_ADMIN_PANEL = 8
STATE_CONFIRM = 9


class ChatApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        os.makedirs(DATA_DIR, exist_ok=True)
        self.client = ChatClient(SERVER_URL)
        self.state = STATE_LOGIN
        self.input_buf = ""
        self.username = ""
        self.password = ""
        self.login_username = ""
        self.login_password = ""
        self.reg_username = ""
        self.reg_password = ""
        self.rooms = []
        self.users = []
        self.messages = []
        self.msg_index = 0
        self.current_room_id = None
        self.current_room_name = ''
        self.menu = None
        self.confirm_action = None
        self.confirm_arg = None
        self.is_admin = False
        self._load_profile()

    def _load_profile(self):
        self.profile = {}
        if os.path.exists(PROFILE_FILE):
            try:
                with open(PROFILE_FILE) as f:
                    self.profile = json.load(f)
            except Exception:
                self.profile = {}

    def _save_profile(self):
        with open(PROFILE_FILE, 'w') as f:
            json.dump(self.profile, f)

    def _poll_events(self):
        while self.active:
            evt = self.client.poll_event()
            if evt is None:
                break
            evt_type, data = evt
            if evt_type == 'room_message':
                self._on_room_message(data)

    def _on_room_message(self, data):
        room_id = data.get('room_id')
        sender = data.get('sender_username', '?')
        content = data.get('content', '')
        msg_type = data.get('type', 'text')
        if sender == self.username:
            return
        if self.current_room_id == room_id and self.state in (STATE_ROOM_CHAT, STATE_COMPOSING):
            display = '[Voice message]' if msg_type == 'voice' else content
            self.messages.append({'sender': sender, 'text': display, 'content': content, 'type': msg_type})
            self.msg_index = len(self.messages) - 1
            self.speak(f"{sender}: {display}")
            self._update_chat_window()

    def _update_chat_window(self):
        if self.messages:
            m = self.messages[self.msg_index]
            self.window.update_text(f"{m['sender']}: {m['text']}")

    def on_focus(self):
        self.client = ChatClient(SERVER_URL)
        self._load_profile()
        stored = self.profile.get('username')
        if stored and self.profile.get('password'):
            self.username = stored
            self.password = self.profile['password']
            try:
                result = self.client.login(self.username, self.password)
                self.is_admin = result.get('role') == 'admin'
                self._load_data()
                self._show_main_menu()
                return
            except ChatError as e:
                self.speak(f"Login failed: {e}")
        self._show_login_menu()

    def _show_main_menu(self):
        self.state = STATE_MENU
        root = MenuNode("Chat")
        root.add_child(MenuNode("Rooms", self._enter_room_list, "r"))
        root.add_child(MenuNode("Users", self._enter_user_list, "u"))
        root.add_child(MenuNode("Change Password", self._enter_change_password, "p"))
        if self.is_admin:
            root.add_child(MenuNode("Admin Panel", self._enter_admin_panel, "a"))
        root.add_child(MenuNode("Logout", self._logout, "l"))
        self.menu = MenuSystem(root, self.speak)
        self.speak("Chat Menu")
        self.window.update_text(f"Chat: {self.username}")

    def _load_data(self):
        try:
            result = self.client.get_rooms()
            self.rooms = result.get('rooms', [])
        except ChatError:
            self.rooms = []
        try:
            result = self.client.get_users()
            self.users = result.get('users', [])
        except ChatError:
            self.users = []

    def _enter_room_list(self):
        self._load_data()
        root = MenuNode("Rooms")
        root.add_child(MenuNode("Create Room", self._start_create_room, "n"))
        for r in self.rooms:
            name = r.get('name', '?')
            mcount = r.get('member_count', 0)
            label = f"{name} ({mcount})"
            root.add_child(MenuNode(label, lambda rid=r['id'], rn=name: self._open_room(rid, rn)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()
        self.state = STATE_ROOM_LIST

    def _open_room(self, room_id, room_name):
        self.current_room_id = room_id
        self.current_room_name = room_name
        try:
            self.client.join_room(room_id)
        except ChatError:
            pass
        self.messages = []
        self.msg_index = 0
        self.state = STATE_ROOM_CHAT
        try:
            result = self.client.get_messages(room_id)
            raw = result.get('messages', [])
            for m in raw:
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                msg_type = m.get('type', 'text')
                display = '[Voice message]' if msg_type == 'voice' else content
                self.messages.append({'sender': sender, 'text': display, 'content': content, 'type': msg_type})
            self.msg_index = len(self.messages) - 1
        except ChatError:
            pass
        if self.messages:
            m = self.messages[self.msg_index]
            self.speak(f"{room_name}. {m['sender']}: {m['text']}")
            self.window.update_text(f"{room_name}: {m['sender']}: {m['text']}")
        else:
            self.speak(f"{room_name}. No messages. Enter to type.")
            self.window.update_text(f"{room_name}: (empty)")

    def _start_create_room(self):
        self.state = STATE_COMPOSING
        self.login_step = 0
        self.input_buf = ""
        self.current_room_id = -99
        self.speak("Enter room name.")
        self.window.update_text("New room name:")

    def _enter_user_list(self):
        try:
            result = self.client.get_users()
            self.users = result.get('users', [])
        except ChatError:
            pass
        root = MenuNode("Users")
        for u in self.users:
            uname = u.get('username', '?')
            role = u.get('role', 'user')
            label = uname
            if role == 'admin':
                label += " [admin]"
            root.add_child(MenuNode(label))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()
        self.state = STATE_USER_LIST

    def _enter_change_password(self):
        self.state = STATE_CHANGE_PASSWORD
        self.login_step = 0
        self.input_buf = ""
        self.speak("Enter current password.")
        self.window.update_text("Current password:")

    def _enter_admin_panel(self):
        self.state = STATE_ADMIN_PANEL
        root = MenuNode("Admin Panel")
        root.add_child(MenuNode("Grant Admin", self._admin_grant, "g"))
        root.add_child(MenuNode("Revoke Admin", self._admin_revoke, "r"))
        root.add_child(MenuNode("List Users", self._admin_list_users, "l"))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _admin_grant(self):
        self.state = STATE_COMPOSING
        self.login_step = -1
        self.input_buf = ""
        self.current_room_id = -1
        self.speak("Enter username to grant admin.")
        self.window.update_text("Grant admin to:")

    def _admin_revoke(self):
        self.state = STATE_COMPOSING
        self.login_step = -1
        self.input_buf = ""
        self.current_room_id = -2
        self.speak("Enter username to revoke admin from.")
        self.window.update_text("Revoke admin from:")

    def _admin_list_users(self):
        try:
            result = self.client.get_users()
            users = result.get('users', [])
            for u in users:
                uname = u.get('username', '?')
                role = u.get('role', 'user')
                self.speak(f"{uname} ({role})")
        except ChatError as e:
            self.speak(f"Failed: {e}")
        self.state = STATE_MENU
        if self.menu:
            self.menu.announce_current()

    def _logout(self):
        self.speak("Logging out.")
        try:
            self.client.logout()
        except Exception:
            pass
        self.profile = {}
        self._save_profile()
        self.login_username = ""
        self.login_password = ""
        self._show_login_menu()

    def on_key(self, vk):
        self._poll_events()
        if self.state == STATE_LOGIN:
            self._handle_login(vk)
        elif self.state == STATE_REGISTER:
            self._handle_register(vk)
        elif self.state == STATE_MENU:
            self._handle_menu(vk)
        elif self.state in (STATE_ROOM_LIST, STATE_USER_LIST, STATE_ADMIN_PANEL):
            self._handle_submenu(vk)
        elif self.state == STATE_ROOM_CHAT:
            self._handle_chat(vk)
        elif self.state == STATE_COMPOSING:
            self._handle_composing(vk)
        elif self.state == STATE_CHANGE_PASSWORD:
            self._handle_change_password(vk)
        elif self.state == STATE_CONFIRM:
            self._handle_confirm(vk)

    def _handle_menu(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

    def _handle_submenu(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

    def _handle_chat(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk == win32con.VK_F1:
            self._refresh_messages()
            return
        if vk == 0x4C:
            if self.current_room_id is not None:
                self.state = STATE_CONFIRM
                self.confirm_action = self._do_leave_room
                self.confirm_arg = self.current_room_id
                self.input_buf = ""
                self.speak("Leave room? Enter to confirm, Escape to cancel.")
                self.window.update_text("Leave room?")
            return
        if vk in (win32con.VK_SPACE):
            if self.messages:
                self.msg_index = (self.msg_index + 1) % len(self.messages)
                m = self.messages[self.msg_index]
                self.speak(f"{m['sender']}: {m['text']}")
                self.window.update_text(f"{m['sender']}: {m['text']}")
        elif vk in (win32con.VK_BACK):
            if self.messages:
                self.msg_index = (self.msg_index - 1) % len(self.messages)
                m = self.messages[self.msg_index]
                self.speak(f"{m['sender']}: {m['text']}")
                self.window.update_text(f"{m['sender']}: {m['text']}")
        elif vk == win32con.VK_RETURN:
            self.state = STATE_COMPOSING
            self.login_step = 0
            self.input_buf = ""
            self.speak("Type your message, then press Enter.")
            self.window.update_text("Message:")

    def _do_leave_room(self, room_id):
        try:
            self.client.leave_room(room_id)
            self.speak("Left room.")
        except ChatError as e:
            self.speak(f"Failed: {e}")
        self.current_room_id = None
        self.state = STATE_MENU
        if self.menu:
            self.menu.announce_current()

    def _refresh_messages(self):
        rid = self.current_room_id
        if not rid:
            return
        try:
            result = self.client.get_messages(rid)
            raw = result.get('messages', [])
            new_msgs = []
            for m in raw:
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                msg_type = m.get('type', 'text')
                display = '[Voice message]' if msg_type == 'voice' else content
                new_msgs.append({'sender': sender, 'text': display, 'content': content, 'type': msg_type})
            if len(new_msgs) > len(self.messages):
                self.speak(f"{len(new_msgs) - len(self.messages)} new message(s)")
            self.messages = new_msgs
            if self.messages:
                self.msg_index = len(self.messages) - 1
                m = self.messages[self.msg_index]
                self.speak(f"{m['sender']}: {m['text']}")
                self.window.update_text(f"{m['sender']}: {m['text']}")
        except ChatError:
            self.speak("Failed to refresh.")

    def _handle_composing(self, vk):
        # Handle login/register field editing
        if hasattr(self, '_editing_field') and self._editing_field:
            if vk == win32con.VK_ESCAPE:
                self._editing_field = None
                self.input_buf = ""
                if self.state == STATE_REGISTER:
                    self._show_register_menu()
                else:
                    self._show_login_menu()
                return
            if vk == win32con.VK_RETURN:
                val = self.input_buf.strip()
                self._editing_field = None
                self.input_buf = ""
                if self.state == STATE_REGISTER:
                    if val:
                        setattr(self, f"reg_{self._editing_field}", val)
                    self._show_register_menu()
                else:
                    if val:
                        setattr(self, f"login_{self._editing_field}", val)
                    self._show_login_menu()
                return
            if vk == win32con.VK_BACK:
                if self.input_buf:
                    self.input_buf = self.input_buf[:-1]
                    self.window.update_text(self.input_buf if self.input_buf else " ")
                return
            ch = self._vk_to_char(vk)
            if ch is not None:
                self.input_buf += ch
                self.window.update_text(self.input_buf)
            return

        if vk == win32con.VK_ESCAPE:
            self.input_buf = ""
            if self.current_room_id == -99:
                self.state = STATE_ROOM_LIST
                if self.menu:
                    self.menu.announce_current()
            elif self.current_room_id in (-1, -2):
                self.state = STATE_ADMIN_PANEL
                if self.menu:
                    self.menu.announce_current()
            elif self.login_step == -1:
                self.state = STATE_MENU
                if self.menu:
                    self.menu.announce_current()
            elif self.current_room_id is not None and self.current_room_id > 0:
                self.state = STATE_ROOM_CHAT
            else:
                self.state = STATE_MENU
                if self.menu:
                    self.menu.announce_current()
            return
        if vk == win32con.VK_RETURN:
            text = self.input_buf.strip()
            if not text:
                return
            self.input_buf = ""

            if self.login_step == -1:
                if self.current_room_id == -1:
                    try:
                        self.client.grant_admin(text)
                        self.speak(f"Granted admin to {text}.")
                    except ChatError as e:
                        self.speak(f"Failed: {e}")
                    self.state = STATE_ADMIN_PANEL
                    if self.menu:
                        self.menu.announce_current()
                    return
                if self.current_room_id == -2:
                    try:
                        self.client.revoke_admin(text)
                        self.speak(f"Revoked admin from {text}.")
                    except ChatError as e:
                        self.speak(f"Failed: {e}")
                    self.state = STATE_ADMIN_PANEL
                    if self.menu:
                        self.menu.announce_current()
                    return

            if self.current_room_id == -99:
                try:
                    self.client.create_room(text)
                    self.speak(f"Room '{text}' created.")
                    self._load_data()
                except ChatError as e:
                    self.speak(f"Failed: {e}")
                self.state = STATE_MENU
                if self.menu:
                    self.menu.announce_current()
                return

            if self.current_room_id is not None and self.current_room_id > 0:
                self.client.send_message(self.current_room_id, text)
                self.messages.append({'sender': self.username, 'text': text, 'content': text, 'type': 'text'})
                self.msg_index = len(self.messages) - 1
                self.speak("Sent.")
                self._update_chat_window()
                self.state = STATE_ROOM_CHAT
                return
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf if self.input_buf else " ")
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.window.update_text(self.input_buf)

    def _handle_change_password(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self.login_step == 0:
                old_pw = val
                self.login_step = 1
                self.input_buf = ""
                self._old_pw = old_pw
                self.speak("Enter new password.")
                self.window.update_text("New password:")
            elif self.login_step == 1:
                new_pw = val
                try:
                    result = self.client.change_password(self._old_pw, new_pw)
                    if result.get('success'):
                        self.speak("Password changed.")
                        if self.profile.get('username'):
                            self.profile['password'] = new_pw
                            self._save_profile()
                    else:
                        self.speak(result.get('message', 'Failed'))
                except ChatError as e:
                    self.speak(f"Failed: {e}")
                self.state = STATE_MENU
                if self.menu:
                    self.menu.announce_current()
            return
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf if self.input_buf else " ")
            return
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.window.update_text(self.input_buf)

    def _handle_confirm(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk == win32con.VK_RETURN:
            if self.confirm_action:
                self.confirm_action(self.confirm_arg)
            self.confirm_action = None
            self.confirm_arg = None

    def _vk_to_char(self, vk):
        shift = win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000
        caps = win32api.GetAsyncKeyState(win32con.VK_CAPITAL) & 1
        if 0x41 <= vk <= 0x5A:
            upper = shift ^ caps
            return chr(vk).upper() if upper else chr(vk).lower()
        if 0x30 <= vk <= 0x39:
            shift_syms = {0x30: ')', 0x31: '!', 0x32: '@', 0x33: '#',
                          0x34: '$', 0x35: '%', 0x36: '^', 0x37: '&',
                          0x38: '*', 0x39: '('}
            return shift_syms[vk] if shift else chr(vk)
        if vk == win32con.VK_SPACE:
            return ' '
        sym_map = {
            0xBD: ('-', '_'), 0xBB: ('=', '+'), 0xC0: ('`', '~'),
            0xDB: ('[', '{'), 0xDD: (']', '}'), 0xDC: ('\\', '|'),
            0xBA: (';', ':'), 0xDE: ("'", '"'),
            0xBC: (',', '<'), 0xBE: ('.', '>'), 0xBF: ('/', '?'),
        }
        if vk in sym_map:
            return sym_map[vk][1] if shift else sym_map[vk][0]
        return None

    def _show_login_menu(self):
        self.state = STATE_LOGIN
        u = self.login_username if self.login_username else "(empty)"
        p = "*" * len(self.login_password) if self.login_password else "(empty)"
        root = MenuNode("Login")
        root.add_child(MenuNode(f"Username: {u}", lambda: self._edit_login_field("username")))
        root.add_child(MenuNode(f"Password: {p}", lambda: self._edit_login_field("password")))
        root.add_child(MenuNode("Login", self._do_login))
        root.add_child(MenuNode("Register", self._show_register_menu))
        root.add_child(MenuNode("Exit", self.exit_app))
        self.menu = MenuSystem(root, self.speak)
        self.speak("Login Menu")
        self.menu.announce_current()
        self._update_login_window()

    def _update_login_window(self):
        u = self.login_username if self.login_username else "(empty)"
        p = "*" * len(self.login_password) if self.login_password else "(empty)"
        self.window.update_text(f"Chat Login\nUsername: {u}\nPassword: {p}")

    def _edit_login_field(self, field):
        self.state = STATE_COMPOSING
        self.input_buf = getattr(self, f"login_{field}", "")
        self._editing_field = field
        self.speak(f"Enter {field}.")
        self.window.update_text(f"{field.capitalize()}:")

    def _do_login(self):
        if not self.login_username.strip() or not self.login_password.strip():
            self.speak("Username and password required.")
            return
        self.username = self.login_username
        self.password = self.login_password
        self.speak("Logging in...")
        self.window.update_text("Connecting...")
        try:
            result = self.client.login(self.username, self.password)
            self.is_admin = result.get('role') == 'admin'
            self.profile['username'] = self.username
            self.profile['password'] = self.password
            self._save_profile()
            self._load_data()
            self._show_main_menu()
        except ChatError as e:
            self.speak(f"Login failed: {e}")

    def _show_register_menu(self):
        self.state = STATE_REGISTER
        u = self.reg_username if self.reg_username else "(empty)"
        p = "*" * len(self.reg_password) if self.reg_password else "(empty)"
        root = MenuNode("Register")
        root.add_child(MenuNode(f"Username: {u}", lambda: self._edit_reg_field("username")))
        root.add_child(MenuNode(f"Password: {p}", lambda: self._edit_reg_field("password")))
        root.add_child(MenuNode("Register", self._do_register))
        root.add_child(MenuNode("Back to Login", self._show_login_menu))
        self.menu = MenuSystem(root, self.speak)
        self.speak("Register Menu")
        self.menu.announce_current()
        self._update_reg_window()

    def _update_reg_window(self):
        u = self.reg_username if self.reg_username else "(empty)"
        self.window.update_text(f"Chat Register\nUsername: {u}")

    def _edit_reg_field(self, field):
        self.state = STATE_COMPOSING
        self.input_buf = getattr(self, f"reg_{field}", "")
        self._editing_field = field
        self.speak(f"Enter {field}.")
        self.window.update_text(f"{field.capitalize()}:")

    def _do_register(self):
        if not self.reg_username.strip() or not self.reg_password.strip():
            self.speak("Username and password required.")
            return
        self.speak("Registering...")
        self.window.update_text("Registering...")
        try:
            self.client.register(self.reg_username, self.reg_password)
            self.speak("Account created! You can now log in.")
            self.login_username = self.reg_username
            self.login_password = self.reg_password
            self._show_login_menu()
        except ChatError as e:
            self.speak(f"Registration failed: {e}")

    def _handle_login(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

    def _handle_register(self, vk):
        if vk == win32con.VK_ESCAPE:
            self._show_login_menu()
            return
        if vk in (win32con.VK_SPACE):
            self.menu.next()
        elif vk in (win32con.VK_BACK):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

    def exit_app(self):
        try:
            self.client.logout()
        except Exception:
            pass
        super().exit_app()
