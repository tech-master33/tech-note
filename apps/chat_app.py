import hashlib
import os
import tempfile
import threading
import time
import winsound
import json
import wave
import win32con
import win32api
from core.app_base import SoftApp
from core.chat_client import ChatClient, ChatError
from core.menu import MenuNode, MenuSystem

DATA_DIR = os.path.join(os.environ['USERPROFILE'], '.tech-soft', 'chat')
PROFILE_FILE = os.path.join(DATA_DIR, 'profile.json')
SERVER_URL = 'https://tech-chat.tech-chat.workers.dev'

# States
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
STATE_DM_LIST = 10
STATE_DM_CHAT = 11
STATE_RECORDING = 12
STATE_PLAYING = 13
STATE_OPTIONS = 14


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
        self.is_mod = False
        self._load_profile()
        # DM state
        self.dm_conversations = []
        self.dm_target_id = None
        self.dm_target_name = ''
        # Voice state
        self._recording = False
        self._record_start = 0
        self._record_duration = 10
        self._record_thread = None
        self._recording_file = None
        # Auto-refresh
        self._last_poll_time = 0
        self._poll_interval = 3

    def _hash_password(self, pw):
        return hashlib.sha256(pw.encode('utf-8')).hexdigest()

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

    def _notify_sound(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            try:
                winsound.Beep(1000, 200)
            except Exception:
                pass

    def _display_content(self, content):
        if ChatClient.is_voice_text(content):
            return 'voice message'
        return content

    def _poll_events(self):
        now = time.time()
        if now - self._last_poll_time < self._poll_interval:
            return
        self._last_poll_time = now
        while self.active:
            evt = self.client.poll_event()
            if evt is None:
                break
            evt_type, data = evt
            if evt_type == 'room_message':
                self._on_room_message(data)
            elif evt_type == 'dm_message':
                self._on_dm_message(data)

    def _on_room_message(self, data):
        room_id = data.get('room_id')
        sender = data.get('sender_username', '?')
        content = data.get('content', '')
        if sender == self.username:
            return
        display = self._display_content(content)
        self._notify_sound()
        if self.current_room_id == room_id and self.state in (STATE_ROOM_CHAT, STATE_COMPOSING):
            self.messages.append({'sender': sender, 'text': display, 'content': content})
            self.msg_index = len(self.messages) - 1
            self.speak(f"{sender}: {display}")
            self._update_chat_window()
        else:
            self.speak(f"New message in room from {sender}")

    def _on_dm_message(self, data):
        sender = data.get('sender_username', '?')
        content = data.get('content', '')
        if sender == self.username:
            return
        display = self._display_content(content)
        self._notify_sound()
        if self.state == STATE_DM_CHAT and self.dm_target_name == sender:
            self.messages.append({'sender': sender, 'text': display, 'content': content})
            self.msg_index = len(self.messages) - 1
            self.speak(f"{sender}: {display}")
            self._update_chat_window()
        else:
            self.speak(f"New DM from {sender}")

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
        root.add_child(MenuNode("Direct Messages", self._enter_dm_list, "d"))
        root.add_child(MenuNode("Users", self._enter_user_list, "u"))
        root.add_child(MenuNode("Change Password", self._enter_change_password, "p"))
        root.add_child(MenuNode("Options", self._enter_options, "o"))
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
        try:
            result = self.client.get_dm_list()
            self.dm_conversations = result.get('conversations', [])
        except ChatError:
            self.dm_conversations = []

    def _enter_room_list(self):
        self._load_data()
        root = MenuNode("Rooms")
        root.add_child(MenuNode("Create Room", self._start_create_room, "n"))
        for r in self.rooms:
            name = r.get('name', '?')
            mcount = r.get('member_count', 0)
            unread = r.get('unread_count', 0)
            label = f"{name} ({mcount} members"
            if unread > 0:
                label += f", {unread} new"
            label += ")"
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
            for m in result.get('messages', []):
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                self.messages.append({'sender': sender, 'text': self._display_content(content), 'content': content})
            self.msg_index = max(0, len(self.messages) - 1)
        except ChatError:
            pass
        if self.messages:
            m = self.messages[self.msg_index]
            self.speak(f"{room_name}. {len(self.messages)} messages. Latest: {m['sender']}: {m['text']}")
            self.window.update_text(f"{room_name}: {m['sender']}: {m['text']}")
        else:
            self.speak(f"{room_name}. No messages. Enter to type, V to record voice.")
            self.window.update_text(f"{room_name}: (empty)")

    def _start_create_room(self):
        self.state = STATE_COMPOSING
        self.login_step = 0
        self.input_buf = ""
        self.current_room_id = -99
        self.speak("Enter room name.")
        self.window.update_text("New room name:")

    def _enter_dm_list(self):
        self._load_data()
        root = MenuNode("Direct Messages")
        root.add_child(MenuNode("New Message", self._start_new_dm, "n"))
        for c in self.dm_conversations:
            uname = c.get('username', '?')
            unread = c.get('unread_count', 0)
            last = c.get('last_message', {})
            label = f"{uname}"
            if unread > 0:
                label += f" ({unread} new)"
            if last:
                snippet = last.get('content', '')
                if ChatClient.is_voice_text(snippet):
                    snippet = 'voice message'
                label += f" - {snippet[:30]}"
            root.add_child(MenuNode(label, lambda uid=c['user_id'], un=uname: self._open_dm(uid, un)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()
        self.state = STATE_DM_LIST

    def _start_new_dm(self):
        self.state = STATE_COMPOSING
        self.login_step = 0
        self.input_buf = ""
        self.current_room_id = -98
        self.speak("Enter username to message.")
        self.window.update_text("To user:")

    def _open_dm(self, other_id, other_name):
        self.dm_target_id = other_id
        self.dm_target_name = other_name
        self.messages = []
        self.msg_index = 0
        self.state = STATE_DM_CHAT
        try:
            result = self.client.get_dm_messages(other_id)
            for m in result.get('messages', []):
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                self.messages.append({'sender': sender, 'text': self._display_content(content), 'content': content})
            self.msg_index = max(0, len(self.messages) - 1)
        except ChatError:
            pass
        if self.messages:
            m = self.messages[self.msg_index]
            self.speak(f"Chat with {other_name}. {len(self.messages)} messages. Latest: {m['text']}")
            self.window.update_text(f"{other_name}: {m['sender']}: {m['text']}")
        else:
            self.speak(f"Chat with {other_name}. No messages. Enter to type, V to record voice.")
            self.window.update_text(f"{other_name}: (empty)")

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
                label += " (admin)"
            user_id = u.get('id')
            root.add_child(MenuNode(label, lambda uid=user_id, un=uname: self._start_dm_from_user(uid, un)))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()
        self.state = STATE_USER_LIST

    def _start_dm_from_user(self, user_id, username):
        if user_id == self.client.user_id:
            self.speak("Cannot message yourself.")
            return
        self._open_dm(user_id, username)

    def _enter_change_password(self):
        self.state = STATE_CHANGE_PASSWORD
        self.login_step = 0
        self.input_buf = ""
        self.speak("Enter current password.")
        self.window.update_text("Current password:")

    def _enter_options(self):
        self.state = STATE_OPTIONS
        root = MenuNode("Options")
        root.add_child(MenuNode(f"Voice record duration: {self._record_duration}s", self._cycle_record_duration, "v"))
        root.add_child(MenuNode("Back", self._show_main_menu, "b"))
        self.menu = MenuSystem(root, self.speak)
        self.menu.announce_current()

    def _cycle_record_duration(self):
        durations = [5, 10, 15, 20, 30]
        idx = durations.index(self._record_duration) if self._record_duration in durations else 0
        self._record_duration = durations[(idx + 1) % len(durations)]
        self.speak(f"Voice record duration: {self._record_duration} seconds")
        self._enter_options()

    def _enter_admin_panel(self):
        self.state = STATE_ADMIN_PANEL
        root = MenuNode("Admin Panel")
        root.add_child(MenuNode("Grant Admin", self._admin_grant, "g"))
        root.add_child(MenuNode("Revoke Admin", self._admin_revoke, "r"))
        root.add_child(MenuNode("List Users", self._admin_list_users, "l"))
        root.add_child(MenuNode("Back", self._show_main_menu, "b"))
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

    def _start_recording(self):
        if self._recording:
            return
        self._recording = True
        self._record_start = time.time()
        self.state = STATE_RECORDING
        self.speak(f"Recording for {self._record_duration} seconds. Press space to stop early.")
        self.window.update_text(f"Recording... 0/{self._record_duration}s")
        self._recording_file = None
        self._record_thread = threading.Thread(target=self._do_record, daemon=True)
        self._record_thread.start()

    def _do_record(self):
        try:
            import sounddevice as sd
            import numpy as np
            sr = 16000
            channels = 1
            frames = []
            duration = self._record_duration

            def callback(indata, frame_count, time_info, status):
                frames.append(indata.tobytes())

            with sd.InputStream(samplerate=sr, channels=channels, dtype='int16', callback=callback):
                time.sleep(duration)

            audio_data = b''.join(frames)
            tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            tmp.close()
            with wave.open(tmp.name, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(audio_data)
            self._recording_file = tmp.name
        except ImportError:
            self.speak("Recording requires sounddevice. Send text instead.")
            self._recording_file = None
        except Exception as e:
            self.speak(f"Recording failed: {e}")
            self._recording_file = None
        finally:
            self._recording = False

    def _stop_recording(self):
        if not self._recording:
            return
        self._recording = False
        elapsed = time.time() - self._record_start
        self.speak(f"Recorded {elapsed:.1f} seconds")
        if self._record_thread:
            self._record_thread.join(timeout=5)
        if self._recording_file:
            self._send_voice(self._recording_file)
        else:
            self.speak("No audio recorded.")
            self._return_to_chat()

    def _send_voice(self, wav_path):
        try:
            voice_text = ChatClient.wav_to_voice_text(wav_path)
            if self.current_room_id and self.current_room_id > 0:
                self.client.send_message(self.current_room_id, voice_text)
                self.messages.append({'sender': self.username, 'text': 'voice message', 'content': voice_text})
                self.msg_index = len(self.messages) - 1
                self.speak("Voice message sent.")
            elif self.dm_target_id:
                self.client.send_dm(self.dm_target_id, voice_text)
                self.messages.append({'sender': self.username, 'text': 'voice message', 'content': voice_text})
                self.msg_index = len(self.messages) - 1
                self.speak("Voice message sent.")
            self._return_to_chat()
        except ChatError as e:
            self.speak(f"Send failed: {e}")
            self._return_to_chat()
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass

    def _play_current_voice(self):
        if not self.messages:
            return
        m = self.messages[self.msg_index]
        content = m.get('content', '')
        if ChatClient.is_voice_text(content):
            self.state = STATE_PLAYING
            self.speak("Playing voice message.")
            self.window.update_text("Playing voice...")
            ChatClient.play_voice_from_text(content)
            self._return_to_chat()
        else:
            self.speak("Not a voice message.")

    def _return_to_chat(self):
        if self.current_room_id and self.current_room_id > 0:
            self.state = STATE_ROOM_CHAT
        elif self.dm_target_id:
            self.state = STATE_DM_CHAT
        else:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()

    def _delete_current_message(self):
        if not self.messages:
            return
        m = self.messages[self.msg_index]
        if m.get('sender') != self.username and not self.is_admin:
            self.speak("Can only delete your own messages.")
            return
        self.state = STATE_CONFIRM
        self.confirm_action = self._do_delete_message
        self.confirm_arg = self.msg_index
        self.speak("Delete this message? Enter to confirm, Escape to cancel.")
        self.window.update_text("Delete message?")

    def _do_delete_message(self, idx):
        try:
            del self.messages[idx]
            if self.messages:
                self.msg_index = min(idx, len(self.messages) - 1)
            else:
                self.msg_index = 0
            self.speak("Message deleted.")
            self._update_chat_window()
        except Exception as e:
            self.speak(f"Delete failed: {e}")
        self._return_to_chat()

    def on_key(self, vk):
        self._poll_events()
        if self.state == STATE_RECORDING:
            self._handle_recording(vk)
            return
        if self.state == STATE_PLAYING:
            return
        if self.state == STATE_LOGIN:
            self._handle_login(vk)
        elif self.state == STATE_REGISTER:
            self._handle_register(vk)
        elif self.state == STATE_MENU:
            self._handle_menu(vk)
        elif self.state in (STATE_ROOM_LIST, STATE_USER_LIST, STATE_ADMIN_PANEL, STATE_DM_LIST, STATE_OPTIONS):
            self._handle_submenu(vk)
        elif self.state == STATE_ROOM_CHAT:
            self._handle_room_chat(vk)
        elif self.state == STATE_DM_CHAT:
            self._handle_dm_chat(vk)
        elif self.state == STATE_COMPOSING:
            self._handle_composing(vk)
        elif self.state == STATE_CHANGE_PASSWORD:
            self._handle_change_password(vk)
        elif self.state == STATE_CONFIRM:
            self._handle_confirm(vk)

    def _handle_recording(self, vk):
        if vk in (win32con.VK_SPACE, win32con.VK_ESCAPE, win32con.VK_RETURN):
            self._stop_recording()
            return
        elapsed = time.time() - self._record_start
        remaining = max(0, self._record_duration - elapsed)
        self.window.update_text(f"Recording... {elapsed:.0f}/{self._record_duration}s (space to stop)")
        if remaining <= 0:
            self._stop_recording()

    def on_key_up(self, vk):
        if vk == win32con.VK_SPACE:
            if getattr(self.manager, 'space_used_in_chord', False):
                return
            if self.state in (STATE_MENU, STATE_ROOM_LIST, STATE_USER_LIST, STATE_ADMIN_PANEL, STATE_DM_LIST, STATE_OPTIONS):
                if self.menu:
                    self.menu.next()
                    item = self.menu.get_current_item()
                    title = item.title if item else self.menu.current_node.title
                    self.window.update_text(title)
            elif self.state == STATE_ROOM_CHAT:
                if self.messages:
                    self.msg_index = (self.msg_index + 1) % len(self.messages)
                    m = self.messages[self.msg_index]
                    self.speak(f"{m['sender']}: {m['text']}")
                    self.window.update_text(f"{m['sender']}: {m['text']}")
            elif self.state == STATE_DM_CHAT:
                if self.messages:
                    self.msg_index = (self.msg_index + 1) % len(self.messages)
                    m = self.messages[self.msg_index]
                    self.speak(f"{m['sender']}: {m['text']}")
                    self.window.update_text(f"{m['sender']}: {m['text']}")

    def _handle_menu(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.exit_app()
            return
        if vk == win32con.VK_BACK:
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
        if vk == win32con.VK_BACK:
            self.menu.previous()
        elif vk == win32con.VK_RETURN:
            self.menu.select()
        elif 0x41 <= vk <= 0x5A:
            self.menu.first_letter_nav(chr(vk))
        if self.menu:
            item = self.menu.get_current_item()
            title = item.title if item else self.menu.current_node.title
            self.window.update_text(title)

    def _handle_room_chat(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_MENU
            if self.menu:
                self.menu.announce_current()
            return
        if vk == win32con.VK_F1:
            self._refresh_room_messages()
            return
        if vk == 0x56:  # V
            self._start_recording()
            return
        if vk == 0x44:  # D
            self._delete_current_message()
            return
        if vk == 0x50:  # P
            self._play_current_voice()
            return
        if vk == 0x4C:  # L
            if self.current_room_id is not None:
                self.state = STATE_CONFIRM
                self.confirm_action = self._do_leave_room
                self.confirm_arg = self.current_room_id
                self.speak("Leave room? Enter to confirm, Escape to cancel.")
                self.window.update_text("Leave room?")
            return
        if vk == win32con.VK_BACK:
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

    def _handle_dm_chat(self, vk):
        if vk == win32con.VK_ESCAPE:
            self.state = STATE_DM_LIST
            self._enter_dm_list()
            return
        if vk == win32con.VK_F1:
            self._refresh_dm_messages()
            return
        if vk == 0x56:  # V
            self._start_recording()
            return
        if vk == 0x44:  # D
            self._delete_current_message()
            return
        if vk == 0x50:  # P
            self._play_current_voice()
            return
        if vk == win32con.VK_BACK:
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

    def _refresh_room_messages(self):
        rid = self.current_room_id
        if not rid:
            return
        try:
            result = self.client.get_messages(rid)
            new_msgs = []
            for m in result.get('messages', []):
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                new_msgs.append({'sender': sender, 'text': self._display_content(content), 'content': content})
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

    def _refresh_dm_messages(self):
        if not self.dm_target_id:
            return
        try:
            result = self.client.get_dm_messages(self.dm_target_id)
            new_msgs = []
            for m in result.get('messages', []):
                sender = m.get('sender_username', '?')
                content = m.get('content', '')
                new_msgs.append({'sender': sender, 'text': self._display_content(content), 'content': content})
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
        if vk == win32con.VK_ESCAPE:
            self.input_buf = ""
            if self.current_room_id == -99:
                self.state = STATE_ROOM_LIST
                self._enter_room_list()
            elif self.current_room_id == -98:
                self.state = STATE_DM_LIST
                self._enter_dm_list()
            elif self.current_room_id in (-1, -2):
                self.state = STATE_ADMIN_PANEL
                if self.menu:
                    self.menu.announce_current()
            elif self.current_room_id and self.current_room_id > 0:
                self.state = STATE_ROOM_CHAT
            elif self.dm_target_id:
                self.state = STATE_DM_CHAT
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
            if self.current_room_id == -98:
                try:
                    result = self.client.search_users(text)
                    users = result.get('users', [])
                    if users:
                        u = users[0]
                        self._open_dm(u['id'], u['username'])
                    else:
                        self.speak(f"User '{text}' not found.")
                        self.state = STATE_DM_LIST
                        self._enter_dm_list()
                except ChatError as e:
                    self.speak(f"Failed: {e}")
                    self.state = STATE_DM_LIST
                    self._enter_dm_list()
                return
            if self.current_room_id and self.current_room_id > 0:
                try:
                    self.client.send_message(self.current_room_id, text)
                    self.messages.append({'sender': self.username, 'text': text, 'content': text})
                    self.msg_index = len(self.messages) - 1
                    self.speak("Sent.")
                    self._update_chat_window()
                except ChatError as e:
                    self.speak(f"Failed: {e}")
                self.state = STATE_ROOM_CHAT
                return
            if self.dm_target_id:
                try:
                    self.client.send_dm(self.dm_target_id, text)
                    self.messages.append({'sender': self.username, 'text': text, 'content': text})
                    self.msg_index = len(self.messages) - 1
                    self.speak("Sent.")
                    self._update_chat_window()
                except ChatError as e:
                    self.speak(f"Failed: {e}")
                self.state = STATE_DM_CHAT
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
                            self.profile['password'] = self._hash_password(new_pw)
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
            self._return_to_chat()
            return
        if vk == win32con.VK_RETURN:
            if self.confirm_action:
                self.confirm_action(self.confirm_arg)
            self.confirm_action = None
            self.confirm_arg = None

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
            self.profile['password'] = self._hash_password(self.password)
            self._save_profile()
            self._load_data()
            self._show_main_menu()
        except ChatError as e:
            self.speak(f"Login failed: {e}")

    def _show_register_menu(self):
        self.state = STATE_REGISTER
        u = self.reg_username if self.reg_username else "(empty)"
        root = MenuNode("Register")
        root.add_child(MenuNode(f"Username: {u}", lambda: self._edit_reg_field("username")))
        root.add_child(MenuNode("Password: (hidden)", lambda: self._edit_reg_field("password")))
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
        if vk in (win32con.VK_BACK):
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
        if vk in (win32con.VK_BACK):
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
