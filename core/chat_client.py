import base64
import json
import os
import tempfile
import threading
import time
import wave
import requests


class ChatError(Exception):
    pass


class ChatClient:
    VOICE_PREFIX = '`'

    def __init__(self, api_base=None):
        self.api_base = api_base or 'https://tech-chat.tech-chat.workers.dev'
        self.token = None
        self.user_id = None
        self.username = None
        self.role = 'user'
        self.is_connected = False
        self.event_queue = []
        self._event_lock = threading.Lock()
        self._polling = False
        self._poll_thread = None

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h

    def _post(self, path, data=None):
        try:
            r = requests.post(f'{self.api_base}/{path}', json=data or {}, headers=self._headers(), timeout=15)
        except requests.exceptions.RequestException as e:
            raise ChatError(f"Connection failed: {e}")
        if r.status_code >= 400:
            try:
                d = r.json()
                msg = d.get('error', f'HTTP {r.status_code}')
            except Exception:
                msg = f'HTTP {r.status_code}'
            raise ChatError(msg)
        return r.json()

    def _get(self, path, params=None):
        try:
            r = requests.get(f'{self.api_base}/{path}', params=params, headers=self._headers(), timeout=15)
        except requests.exceptions.RequestException as e:
            raise ChatError(f"Connection failed: {e}")
        if r.status_code >= 400:
            try:
                d = r.json()
                msg = d.get('error', f'HTTP {r.status_code}')
            except Exception:
                msg = f'HTTP {r.status_code}'
            raise ChatError(msg)
        return r.json()

    def _delete(self, path):
        try:
            r = requests.delete(f'{self.api_base}/{path}', headers=self._headers(), timeout=15)
        except requests.exceptions.RequestException as e:
            raise ChatError(f"Connection failed: {e}")
        if r.status_code >= 400:
            try:
                d = r.json()
                msg = d.get('error', f'HTTP {r.status_code}')
            except Exception:
                msg = f'HTTP {r.status_code}'
            raise ChatError(msg)
        return r.json()

    # --- Auth ---
    def register(self, username, password):
        return self._post('register', {'username': username, 'password': password})

    def login(self, username, password):
        result = self._post('login', {'username': username, 'password': password})
        self.user_id = result['user_id']
        self.username = result['username']
        self.role = result.get('role', 'user')
        self.token = str(self.user_id)
        self.is_connected = True
        self._start_polling()
        return result

    def logout(self):
        self._polling = False
        self.is_connected = False
        self.token = None
        self.user_id = None
        self.username = None

    def change_password(self, old_password, new_password):
        return self._post('password', {'old_password': old_password, 'new_password': new_password})

    # --- Rooms ---
    def get_rooms(self):
        return self._get('rooms')

    def create_room(self, name, description=''):
        return self._post('rooms', {'name': name, 'description': description})

    def join_room(self, room_id):
        return self._post(f'rooms/{room_id}/join')

    def leave_room(self, room_id):
        return self._post(f'rooms/{room_id}/leave')

    def delete_room(self, room_id):
        return self._post(f'rooms/{room_id}/delete')

    # --- Messages ---
    def send_message(self, room_id, content):
        return self._post(f'rooms/{room_id}/messages', {'content': content})

    def get_messages(self, room_id, since_id=None, limit=50):
        params = {}
        if since_id:
            params['since_id'] = str(since_id)
        if limit:
            params['limit'] = str(limit)
        return self._get(f'rooms/{room_id}/messages', params)

    def delete_message(self, room_id, msg_id):
        return self._delete(f'rooms/{room_id}/message/{msg_id}')

    # --- DMs ---
    def get_dm_list(self):
        return self._get('dm')

    def get_dm_messages(self, other_id, since_id=None, limit=50):
        params = {}
        if since_id:
            params['since_id'] = str(since_id)
        if limit:
            params['limit'] = str(limit)
        return self._get(f'dm/{other_id}', params)

    def send_dm(self, other_id, content):
        return self._post(f'dm/{other_id}', {'content': content})

    def delete_dm(self, msg_id):
        return self._delete(f'dm/message/{msg_id}')

    # --- Users ---
    def get_users(self):
        return self._get('users')

    def search_users(self, query):
        return self._get('users', {'query': query})

    # --- Admin ---
    def grant_admin(self, username):
        return self._post('admin/grant', {'username': username})

    def revoke_admin(self, username):
        return self._post('admin/revoke', {'username': username})

    # --- Voice Helpers ---
    @staticmethod
    def wav_to_voice_text(wav_path):
        """Convert WAV to text with ` prefix."""
        with open(wav_path, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('ascii')
        return ChatClient.VOICE_PREFIX + b64

    @staticmethod
    def is_voice_text(content):
        """Check if content is a voice message."""
        return content.startswith(ChatClient.VOICE_PREFIX)

    @staticmethod
    def voice_text_to_wav(content, save_path):
        """Convert voice text (with ` prefix) to WAV file."""
        b64 = content[1:]  # Remove ` prefix
        data = base64.b64decode(b64)
        with open(save_path, 'wb') as f:
            f.write(data)
        return save_path

    @staticmethod
    def play_voice_from_text(content):
        """Play voice message from text content."""
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        try:
            ChatClient.voice_text_to_wav(content, tmp.name)
            ChatClient.play_voice(tmp.name)
        except Exception:
            pass
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    @staticmethod
    def play_voice(path):
        """Play a WAV file."""
        try:
            import winsound
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            try:
                import sounddevice as sd
                import numpy as np
                with wave.open(path, 'rb') as wf:
                    frames = wf.readframes(wf.getnframes())
                    data = np.frombuffer(frames, dtype=np.int16)
                    sd.play(data, wf.getframerate())
                    sd.wait()
            except Exception:
                pass

    # --- Polling ---
    def _start_polling(self):
        if self._poll_thread and self._poll_thread.is_alive():
            self._polling = False
            self._poll_thread.join(timeout=2)
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._polling:
            try:
                rooms_resp = self._get('rooms')
                for room in rooms_resp.get('rooms', []):
                    rid = room.get('id')
                    unread = room.get('unread_count', 0)
                    if unread > 0:
                        result = self.get_messages(rid, limit=unread)
                        for m in result.get('messages', []):
                            with self._event_lock:
                                self.event_queue.append(('room_message', m))

                dms_resp = self._get('dm')
                for convo in dms_resp.get('conversations', []):
                    unread = convo.get('unread_count', 0)
                    if unread > 0:
                        last = convo.get('last_message')
                        if last:
                            with self._event_lock:
                                self.event_queue.append(('dm_message', last))
            except Exception:
                pass
            time.sleep(3)

    def poll_event(self):
        with self._event_lock:
            if self.event_queue:
                return self.event_queue.pop(0)
        return None
