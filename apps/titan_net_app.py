import os
import json
import datetime
import win32con
import win32api
from core.app_base import SoftApp
from core.titan_net_client import TitanNetClient, TitanNetError
from core.titan_sounds import TitanSounds
from core.menu import MenuNode, MenuSystem

DATA_DIR = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'titannet')
PROFILE_FILE = os.path.join(DATA_DIR, 'profile.json')

STATE_LOGIN = 0
STATE_MENU = 1
STATE_CHAT = 2
STATE_CONTACT_CHAT = 3
STATE_COMPOSING = 4
STATE_REGISTER = 5

class TitanNetApp(SoftApp):
    def __init__(self, manager, window):
        super().__init__(manager, window)
        os.makedirs(DATA_DIR, exist_ok=True)
        self.client = TitanNetClient()
        self.sounds = TitanSounds()
        self.state = STATE_LOGIN
        self.input_buf = ""
        self.login_step = 0
        self.username = ""
        self.password = ""
        self.full_name = ""
        self.rooms = []
        self.online_users = []
        self.messages = []
        self.msg_index = 0
        self.composing_room = None
        self.composing_contact = None
        
        self.menu = None
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
            elif evt_type == 'message':
                self._on_private_message(data)
            elif evt_type == 'user_online':
                uname = data.get('username', '')
                if uname not in self.online_users and uname != self.username:
                    self.online_users.append(uname)
                    self.sounds.play_online()
                    self.speak(f"{uname} online")
            elif evt_type == 'user_offline':
                uname = data.get('username', '')
                if uname in self.online_users:
                    self.online_users.remove(uname)
                    self.sounds.play_offline()
                    self.speak(f"{uname} offline")
            elif evt_type == 'user_joined_room':
                uname = data.get('username', '')
                self.speak(f"{uname} joined")
            elif evt_type == 'user_left_room':
                uname = data.get('username', '')
                self.speak(f"{uname} left")
            elif evt_type == 'connection_lost':
                self.sounds.play_error()
                self.speak("Connection lost.")
                self.state = STATE_LOGIN

    def _on_room_message(self, data):
        room_id = data.get('room_id')
        sender_raw = data.get('sender', '')
        if isinstance(sender_raw, dict):
            sender = sender_raw.get('username', '?')
        else:
            sender = str(sender_raw)
        text = data.get('message', '')
        if sender == self.username:
            return
        if self.composing_room == room_id and self.state in (STATE_CHAT, STATE_COMPOSING):
            self.sounds.play_chat_message()
            self.messages.append({'sender': sender, 'text': text, 'time': ''})
            self.msg_index = len(self.messages) - 1
            self.speak(f"{sender}: {text}")
            self._update_chat_window()

    def _on_private_message(self, data):
        sender_raw = data.get('sender', '')
        if isinstance(sender_raw, dict):
            sender = sender_raw.get('username', '?')
        else:
            sender = str(sender_raw)
        text = data.get('message', '')
        if self.composing_contact == sender and self.state in (STATE_CONTACT_CHAT, STATE_COMPOSING):
            self.messages.append({'sender': sender, 'text': text, 'time': ''})
            self.msg_index = len(self.messages) - 1
            self.sounds.play_new_message()
            self.speak(f"{sender}: {text}")
            self._update_chat_window()
        else:
            self.sounds.play_new_message()
            self.speak(f"Message from {sender}")

    def _update_chat_window(self):
        if self.messages:
            m = self.messages[self.msg_index]
            self.window.update_text(f"{m['sender']}: {m['text']}")

    def on_focus(self):
        self._load_profile()
        stored = self.profile.get('username')
        if stored and self.profile.get('password'):
            self.username = stored
            self.password = self.profile['password']
            try:
                self.client.login(self.username, self.password)
                self.sounds.play_welcome()
                self.sounds.play_applist()
                self._load_rooms()
                self._show_main_menu()
                return
            except TitanNetError as e:
                self.sounds.play_error()
                self.speak(f"Login failed: {e}")
        self.state = STATE_LOGIN
        self.login_step = 0
        self.input_buf = ""
        self.speak("Titan Net. Enter username and press Enter. R to register.")
        self.window.update_text("Titan Net - Username:")

    def _show_main_menu(self):
        self.state = STATE_MENU
        root = MenuNode("Titan Net")
        root.add_child(MenuNode("Rooms", self._show_rooms, "r"))
        root.add_child(MenuNode("Online Users", self._show_users, "u"))
        root.add_child(MenuNode("Create Room", self._start_create_room, "n"))
        root.add_child(MenuNode("Logout", self._logout, "l"))
        
        self.menu = MenuSystem(root, self.speak)
        self.speak("Titan Net Menu")
        self.window.update_text(f"Titan Net: {self.username}")

    def _show_rooms(self):
        self._load_rooms()
        if not self.rooms:
            self.speak("No rooms available.")
            return
        
        root = MenuNode("Rooms")
        for i, r in enumerate(self.rooms):
            name = r.get('name', f"Room {i}")
            root.add_child(MenuNode(name, lambda idx=i: self._open_room(idx)))
        
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _show_users(self):
        self._load_rooms() # Refreshes online users too
        others = [u for u in self.online_users if u != self.username]
        if not others:
            self.speak("No other users online.")
            return
            
        root = MenuNode("Online Users")
        for i, uname in enumerate(others):
            root.add_child(MenuNode(uname, lambda idx=i: self._open_contact_chat(idx)))
            
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _start_create_room(self):
        self.state = STATE_COMPOSING
        self.composing_room = True
        self.composing_contact = False
        self.input_buf = ""
        self.sounds.play_dialog()
        self.speak("Enter room name.")
        self.window.update_text("New room name:")

    def _logout(self):
        self.sounds.play_dialog_close()
        self.speak("Logging out.")
        try:
            self.client.logout()
        except Exception:
            pass
        while self.client.poll_event() is not None:
            pass
        self.profile = {}
        self._save_profile()
        self.state = STATE_LOGIN
        self.login_step = 0
        self.input_buf = ""
        self.window.update_text("Titan Net - Username:")

    def on_key(self, vk):
        self._poll_events()
        if self.state == STATE_LOGIN:
            self._handle_login(vk)
        elif self.state == STATE_REGISTER:
            self._handle_register(vk)
        elif self.state == STATE_MENU:
            self._handle_menu(vk)
        elif self.state == STATE_CHAT or self.state == STATE_CONTACT_CHAT:
            self._handle_chat(vk)
        elif self.state == STATE_COMPOSING:
            self._handle_composing(vk)

    def _handle_menu(self, vk):
        if vk == win32con.VK_ESCAPE:
            if self.menu and self.menu.current_node.parent:
                self.menu.back()
            else:
                self.exit_app()
            return

        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            self.menu.next()
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

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

    def _input_char(self, vk):
        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf if self.input_buf else " ")
            return True
        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.window.update_text(self.input_buf)
            return True
        return False

    def _handle_login(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self.login_step == 0:
                self.username = val
                self.login_step = 1
                self.input_buf = ""
                self.speak("Enter password.")
                self.window.update_text("Titan Net - Password:")
            elif self.login_step == 1:
                self.password = val
                self.speak("Logging in...")
                self.window.update_text("Connecting...")
                try:
                    self.client.login(self.username, self.password)
                    self.profile['username'] = self.username
                    self.profile['password'] = self.password
                    self._save_profile()
                    self.sounds.play_welcome()
                    self.sounds.play_applist()
                    self._load_rooms()
                    self._show_main_menu()
                except TitanNetError as e:
                    self.sounds.play_error()
                    msg = str(e)
                    self.speak(f"Login failed: {msg}")
                    self.login_step = 0
                    self.input_buf = ""
                    self.window.update_text("Titan Net - Username:")
            return
        if vk == 0x52 and self.login_step == 0 and not self.input_buf:
            self.state = STATE_REGISTER
            self.login_step = 0
            self.input_buf = ""
            self.speak("Register. Enter username and press Enter.")
            self.window.update_text("Register - Username:")
            return
        self._input_char(vk)

    def _handle_register(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_LOGIN
            self.login_step = 0
            self.input_buf = ""
            self.speak("Enter username and press Enter.")
            self.window.update_text("Titan Net - Username:")
            return
        if vk == win32con.VK_RETURN:
            val = self.input_buf.strip()
            if not val:
                self.speak("Cannot be empty.")
                return
            if self.login_step == 0:
                self.username = val
                self.login_step = 1
                self.input_buf = ""
                self.speak("Enter password.")
                self.window.update_text("Register - Password:")
            elif self.login_step == 1:
                self.password = val
                self.login_step = 2
                self.input_buf = ""
                self.speak("Enter your full name.")
                self.window.update_text("Register - Full Name:")
            elif self.login_step == 2:
                self.full_name = val
                self.speak("Registering...")
                self.window.update_text("Registering...")
                try:
                    result = self.client.register(self.username, self.password, self.full_name)
                    self.sounds.play_account_created()
                    self.speak(f"Account created! Titan number: {result.get('titan_number', '?')}")
                except TitanNetError as e:
                    self.sounds.play_error()
                    self.speak(f"Registration failed: {e}")
                self.state = STATE_LOGIN
                self.login_step = 0
                self.input_buf = ""
                self.window.update_text("Titan Net - Username:")
            return
        self._input_char(vk)

    def _load_rooms(self):
        try:
            result = self.client.get_rooms()
            raw = result.get('rooms', [])
            self.rooms = raw if isinstance(raw, list) else []
        except TitanNetError:
            self.rooms = []
        try:
            result = self.client.get_online_users()
            raw = result.get('users', [])
            self.online_users = []
            for u in raw:
                if isinstance(u, dict):
                    uname = u.get('username', '')
                    if uname:
                        self.online_users.append(uname)
                elif isinstance(u, str):
                    self.online_users.append(u)
        except TitanNetError:
            self.online_users = []

    def _open_room(self, idx):
        if idx >= len(self.rooms): return
        r = self.rooms[idx]
        room_id = r.get('id')
        rname = r.get('name', '?')
        self.composing_room = room_id
        self.composing_contact = None
        self.messages = []
        self.msg_index = 0
        self.state = STATE_CHAT
        try:
            result = self.client.get_room_messages(room_id)
            raw = result.get('messages', [])
            if isinstance(raw, list):
                for m in raw:
                    sender_raw = m.get('sender', m.get('username', m.get('user', '?')))
                    if isinstance(sender_raw, dict):
                        sender = sender_raw.get('username', '?')
                    else:
                        sender = str(sender_raw)
                    self.messages.append({
                        'sender': sender,
                        'text': m.get('message', m.get('text', '')),
                        'time': m.get('timestamp', '')
                    })
                self.msg_index = len(self.messages) - 1
        except TitanNetError:
            self.messages = []
        self.sounds.play_dialog()
        if self.messages:
            m = self.messages[self.msg_index]
            self.speak(f"{rname}. {m['sender']}: {m['text']}")
            self.window.update_text(f"{rname}: {m['sender']}: {m['text']}")
        else:
            self.speak(f"{rname}. No messages. Press Enter to type.")
            self.window.update_text(f"{rname}: (empty)")

    def _handle_chat(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.sounds.play_dialog_close()
            self.speak("Back.")
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            if self.messages:
                before = self.msg_index
                self.msg_index = (self.msg_index + 1) % len(self.messages)
                if self.msg_index < before:
                    self.sounds.play_endoflist()
                m = self.messages[self.msg_index]
                self.sounds.play_focus()
                self.speak(f"{m['sender']}: {m['text']}")
                self.window.update_text(f"{m['sender']}: {m['text']}")
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            if self.messages:
                before = self.msg_index
                self.msg_index = (self.msg_index - 1) % len(self.messages)
                if self.msg_index > before:
                    self.sounds.play_endoflist()
                m = self.messages[self.msg_index]
                self.sounds.play_focus()
                self.speak(f"{m['sender']}: {m['text']}")
                self.window.update_text(f"{m['sender']}: {m['text']}")
        elif vk == win32con.VK_RETURN:
            self.state = STATE_COMPOSING
            self.input_buf = ""
            self.sounds.play_dialog()
            self.speak("Type your message, then press Enter.")
            self.window.update_text("Message:")
        elif vk == win32con.VK_F1:
            self._refresh_chat()

    def _refresh_chat(self):
        rid = self.composing_room or self.composing_contact
        if not rid: return
        try:
            if self.composing_room:
                result = self.client.get_room_messages(rid)
            else:
                result = self.client.get_private_messages(rid)
            raw = result.get('messages', [])
            if isinstance(raw, list):
                new_msgs = []
                for m in raw:
                    sender_raw = m.get('sender', m.get('username', m.get('user', '?')))
                    if isinstance(sender_raw, dict):
                        sender = sender_raw.get('username', '?')
                    else:
                        sender = str(sender_raw)
                    new_msgs.append({
                        'sender': sender,
                        'text': m.get('message', m.get('text', '')),
                        'time': m.get('timestamp', '')
                    })
                if len(new_msgs) > len(self.messages):
                    count = len(new_msgs) - len(self.messages)
                    self.speak(f"{count} new message{'s' if count > 1 else ''}")
                    self.sounds.play_new_message()
                self.messages = new_msgs
                if self.messages:
                    self.msg_index = len(self.messages) - 1
                    m = self.messages[self.msg_index]
                    self.speak(f"{m['sender']}: {m['text']}")
                    self.window.update_text(f"{m['sender']}: {m['text']}")
        except TitanNetError:
            self.sounds.play_error()
            self.speak("Failed to refresh.")

    def _open_contact_chat(self, idx):
        others = [u for u in self.online_users if u != self.username]
        if idx >= len(others): return
        uname = others[idx]
        self.composing_contact = uname
        self.composing_room = None
        self.messages = []
        self.msg_index = 0
        self.state = STATE_CONTACT_CHAT
        try:
            result = self.client.get_private_messages(uname)
            raw = result.get('messages', [])
            if isinstance(raw, list):
                for m in raw:
                    sender_raw = m.get('sender', m.get('username', m.get('user', '?')))
                    if isinstance(sender_raw, dict):
                        sender = sender_raw.get('username', '?')
                    else:
                        sender = str(sender_raw)
                    self.messages.append({
                        'sender': sender,
                        'text': m.get('message', m.get('text', '')),
                        'time': m.get('timestamp', '')
                    })
                self.msg_index = len(self.messages) - 1
        except TitanNetError:
            self.messages = []
        self.sounds.play_dialog()
        if self.messages:
            m = self.messages[self.msg_index]
            self.speak(f"{uname}. {m['sender']}: {m['text']}")
            self.window.update_text(f"{uname}: {m['sender']}: {m['text']}")
        else:
            self.speak(f"{uname}. No messages. Press Enter to type.")
            self.window.update_text(f"{uname}: (empty)")

    def _handle_composing(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.input_buf = ""
            self.sounds.play_dialog_close()
            if self.composing_room is True:
                self.state = STATE_MENU
                if self.menu: self.menu.announce_current()
            elif self.composing_room is not None:
                self.state = STATE_CHAT
            elif self.composing_contact is not None:
                self.state = STATE_CONTACT_CHAT
            else:
                self.state = STATE_MENU
                if self.menu: self.menu.announce_current()
            return

        if vk == win32con.VK_RETURN:
            text = self.input_buf.strip()
            if not text:
                return
            self.input_buf = ""

            if self.composing_room is True:
                try:
                    self.client.create_room(text)
                    self.sounds.play_dialog()
                    self.speak(f"Room {text} created.")
                    self._load_rooms()
                except TitanNetError as e:
                    self.sounds.play_error()
                    self.speak(f"Failed: {e}")
                self.state = STATE_MENU
                if self.menu: self.menu.announce_current()
                return

            if self.composing_room is not None:
                try:
                    self.client.send_room_message(self.composing_room, text)
                    self.sounds.play_message_send()
                    self.messages.append({'sender': self.username, 'text': text, 'time': ''})
                    self.msg_index = len(self.messages) - 1
                    self.speak("Sent.")
                    self._update_chat_window()
                except TitanNetError as e:
                    self.sounds.play_error()
                    self.speak(f"Failed: {e}")
                self.state = STATE_CHAT
                return

            if self.composing_contact is not None:
                try:
                    self.client.send_private_message(self.composing_contact, text)
                    self.sounds.play_message_send()
                    self.messages.append({'sender': self.username, 'text': text, 'time': ''})
                    self.msg_index = len(self.messages) - 1
                    self.speak("Sent.")
                    self._update_chat_window()
                except TitanNetError as e:
                    self.sounds.play_error()
                    self.speak(f"Failed: {e}")
                self.state = STATE_CONTACT_CHAT
                return

            return

        if vk == win32con.VK_BACK:
            if self.input_buf:
                self.input_buf = self.input_buf[:-1]
                self.window.update_text(self.input_buf if self.input_buf else "Message:")
            return

        ch = self._vk_to_char(vk)
        if ch is not None:
            self.input_buf += ch
            self.window.update_text(self.input_buf)

    def exit_app(self):
        try:
            self.client.logout()
        except Exception:
            pass
        super().exit_app()
