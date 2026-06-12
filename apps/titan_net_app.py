import os
import json
import datetime
import win32con
import win32api
from core.app_base import SoftApp
from core.titan_net_client import TitanNetClient, TitanNetError
from core.titan_sounds import TitanSounds

DATA_DIR = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'titannet')
PROFILE_FILE = os.path.join(DATA_DIR, 'profile.json')

STATE_LOGIN = 0
STATE_MAIN = 1
STATE_ROOM = 2
STATE_CHAT = 3
STATE_CONTACTS = 4
STATE_CONTACT_CHAT = 5
STATE_COMPOSING = 6
STATE_REGISTER = 7

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
        self.room_index = 0
        self.messages = []
        self.msg_index = 0
        self.composing_room = None
        self.composing_contact = None
        self.online_users = []
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
                self.state = STATE_MAIN
                self._load_rooms()
                self._announce_main()
                return
            except TitanNetError as e:
                self.sounds.play_error()
                self.speak(f"Login failed: {e}")
        self.state = STATE_LOGIN
        self.login_step = 0
        self.input_buf = ""
        self.speak("Titan Net. Enter username and press Enter. R to register.")
        self.window.update_text("Titan Net - Username:")

    def on_key(self, vk):
        self._poll_events()
        if self.state == STATE_LOGIN:
            self._handle_login(vk)
        elif self.state == STATE_REGISTER:
            self._handle_register(vk)
        elif self.state == STATE_MAIN:
            self._handle_main(vk)
        elif self.state == STATE_ROOM:
            self._handle_room(vk)
        elif self.state == STATE_CHAT:
            self._handle_chat(vk)
        elif self.state == STATE_CONTACTS:
            self._handle_contacts(vk)
        elif self.state == STATE_CONTACT_CHAT:
            self._handle_chat(vk)
        elif self.state == STATE_COMPOSING:
            self._handle_composing(vk)

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
                    result = self.client.login(self.username, self.password)
                    self.profile['username'] = self.username
                    self.profile['password'] = self.password
                    self._save_profile()
                    self.sounds.play_welcome()
                    self.sounds.play_applist()
                    self.state = STATE_MAIN
                    self._load_rooms()
                    self._announce_main()
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

    def _announce_main(self):
        rc = len(self.rooms)
        uc = len([u for u in self.online_users if u != self.username])
        self.speak(f"Titan Net. {rc} rooms, {uc} online. R rooms, C users, L logout.")
        self.window.update_text(f"Titan Net - {self.username} ({rc}r, {uc}u)")

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

    def _handle_main(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == 0x52:
            self.sounds.play_select()
            self.state = STATE_ROOM
            self.room_index = 0
            if self.rooms:
                r = self.rooms[self.room_index]
                rname = r.get('name', '?')
                self.sounds.play_focus()
                self.speak(f"Rooms. {rname}. Space to navigate, Enter to open.")
                self.window.update_text("Rooms: " + rname)
            else:
                self.speak("No rooms. Press N to create one.")
                self.window.update_text("Rooms: (empty)")
        elif vk == 0x43:
            self.sounds.play_select()
            self.state = STATE_CONTACTS
            self.contact_index = 0
            others = [u for u in self.online_users if u != self.username]
            if others:
                self.sounds.play_focus()
                self.speak(f"Online users. {others[0]}. Space to navigate, Enter to message.")
                self.window.update_text("Online: " + others[0])
            else:
                self.speak("No other users online.")
                self.window.update_text("Online: (none)")
        elif vk == 0x4E:
            self.state = STATE_COMPOSING
            self.composing_room = True
            self.composing_contact = False
            self.input_buf = ""
            self.sounds.play_dialog()
            self.speak("Enter room name.")
            self.window.update_text("New room name:")
        elif vk == 0x4C:
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

    def _handle_room(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MAIN
            self.sounds.play_dialog_close()
            self._announce_main()
            return
        if not self.rooms:
            return
        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            before = self.room_index
            self.room_index = (self.room_index + 1) % len(self.rooms)
            if self.room_index < before:
                self.sounds.play_endoflist()
            r = self.rooms[self.room_index]
            rname = r.get('name', '?')
            self.sounds.play_focus()
            self.speak(rname)
            self.window.update_text("Rooms: " + rname)
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            before = self.room_index
            self.room_index = (self.room_index - 1) % len(self.rooms)
            if self.room_index > before:
                self.sounds.play_endoflist()
            r = self.rooms[self.room_index]
            rname = r.get('name', '?')
            self.sounds.play_focus()
            self.speak(rname)
            self.window.update_text("Rooms: " + rname)
        elif vk == win32con.VK_RETURN:
            self.sounds.play_select()
            self._open_room(self.room_index)

    def _open_room(self, idx):
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
            if self.composing_room is not None:
                self.state = STATE_ROOM
            else:
                self.state = STATE_CONTACTS
            self.sounds.play_dialog_close()
            self.speak("Back.")
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
        if self.composing_room is not None:
            rid = self.composing_room
            try:
                result = self.client.get_room_messages(rid)
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

    def _handle_contacts(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MAIN
            self.sounds.play_dialog_close()
            self._announce_main()
            return
        others = [u for u in self.online_users if u != self.username]
        if not others:
            return
        if vk in (win32con.VK_SPACE, win32con.VK_DOWN):
            before = self.contact_index
            self.contact_index = (self.contact_index + 1) % len(others)
            if self.contact_index < before:
                self.sounds.play_endoflist()
            uname = others[self.contact_index]
            self.sounds.play_focus()
            self.speak(uname)
            self.window.update_text("Online: " + uname)
        elif vk in (win32con.VK_BACK, win32con.VK_UP):
            before = self.contact_index
            self.contact_index = (self.contact_index - 1) % len(others)
            if self.contact_index > before:
                self.sounds.play_endoflist()
            uname = others[self.contact_index]
            self.sounds.play_focus()
            self.speak(uname)
            self.window.update_text("Online: " + uname)
        elif vk == win32con.VK_RETURN:
            self.sounds.play_select()
            self._open_contact_chat(self.contact_index)

    def _open_contact_chat(self, idx):
        others = [u for u in self.online_users if u != self.username]
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
                self.state = STATE_MAIN
                self._announce_main()
            elif self.composing_contact is True:
                self.state = STATE_MAIN
                self._announce_main()
            elif self.composing_room is not None:
                self.state = STATE_CHAT
            elif self.composing_contact is not None:
                self.state = STATE_CONTACT_CHAT
            return

        if vk == win32con.VK_RETURN:
            text = self.input_buf.strip()
            if not text:
                return
            self.input_buf = ""

            if self.composing_room is True:
                try:
                    result = self.client.create_room(text)
                    self.sounds.play_dialog()
                    self.speak(f"Room {text} created.")
                    self._load_rooms()
                except TitanNetError as e:
                    self.sounds.play_error()
                    self.speak(f"Failed: {e}")
                self.state = STATE_MAIN
                self._announce_main()
                return

            if self.composing_contact is True:
                self.sounds.play_error()
                self.speak("Use C to see online users.")
                self.state = STATE_MAIN
                self._announce_main()
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

        if vk == win32con.VK_SPACE:
            self.input_buf += ' '
            self.window.update_text(self.input_buf)
            return
        if 0x30 <= vk <= 0x39:
            self.input_buf += chr(vk)
            self.window.update_text(self.input_buf)
            return
        if 0x41 <= vk <= 0x5A:
            self.input_buf += chr(vk).lower()
            self.window.update_text(self.input_buf)
            return

    def exit_app(self):
        try:
            self.client.logout()
        except Exception:
            pass
        super().exit_app()
