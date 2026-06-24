import base64
import json
import os
import tempfile
import threading
import time
import wave
import requests
import mimetypes


class ChatError(Exception):
    pass


class ChatClient:
    VOICE_PREFIX = '`'
    FILE_PREFIX = '!'

    def __init__(self, api_base=None):
        self.api_base = api_base or 'https://tech-chat.tech-chat.workers.dev'
        self.token = None
        self.user_id = None
        self.username = None
        self.role = 'user'
        self.is_connected = False
        self.event_queue = []
        self._event_lock = threading.Lock()
        self._stop_polling = threading.Event()
        self._stop_polling.set()
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

    def _put(self, path, data=None):
        try:
            r = requests.put(f'{self.api_base}/{path}', json=data or {}, headers=self._headers(), timeout=15)
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
        self.token = result.get('token')
        if not self.token:
            raise ChatError("Server did not return an auth token")
        self.is_connected = True
        self._start_polling()
        return result

    def logout(self):
        self._stop_polling.set()
        self.is_connected = False
        self.token = None
        self.user_id = None
        self.username = None
        self._saved_username = None
        self._saved_password = None

    def save_credentials(self, username, password):
        self._saved_username = username
        self._saved_password = password

    def reconnect(self):
        if not self._saved_username or not self._saved_password:
            return False
        try:
            result = self.login(self._saved_username, self._saved_password)
            return result is not None
        except Exception:
            return False

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

    def edit_message(self, room_id, msg_id, content):
        return self._put(f'rooms/{room_id}/message/{msg_id}', {'content': content})

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

    def edit_dm(self, msg_id, content):
        return self._put(f'dm/message/{msg_id}', {'content': content})

    # --- Users ---
    def get_users(self):
        return self._get('users')

    def search_users(self, query):
        return self._get('users', {'query': query})

    # --- Online Status ---
    def heartbeat(self):
        return self._post('heartbeat')

    def get_online(self):
        return self._get('online')

    def set_typing(self, room_id=None, target_id=None, typing=True):
        data = {'typing': typing}
        if room_id:
            data['room_id'] = room_id
        if target_id:
            data['target_id'] = target_id
        return self._post('typing', data)

    def get_typing(self, room_id=None, target_id=None):
        params = {}
        if room_id:
            params['room_id'] = room_id
        if target_id:
            params['target_id'] = target_id
        return self._get('typing', params)

    # --- Admin ---
    def grant_admin(self, username):
        return self._post('admin/grant', {'username': username})

    def revoke_admin(self, username):
        return self._post('admin/revoke', {'username': username})

    def ban_user(self, username):
        return self._post('admin/ban', {'username': username})

    def unban_user(self, username):
        return self._post('admin/unban', {'username': username})

    def mute_user(self, username, duration_minutes=5):
        return self._post('admin/mute', {'username': username, 'duration_minutes': duration_minutes})

    def unmute_user(self, username):
        return self._post('admin/unmute', {'username': username})

    def broadcast(self, message):
        return self._post('admin/broadcast', {'message': message})

    # --- File Sharing ---
    def upload_file(self, filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('ascii')
        name = os.path.basename(filepath)
        return self._post('files/upload', {'name': name, 'data': b64})

    def get_file(self, file_id):
        return self._get(f'files/{file_id}')

    # --- Voice Helpers ---
    @staticmethod
    def wav_to_voice_text(wav_path):
        with open(wav_path, 'rb') as f:
            data = f.read()
        b64 = base64.b64encode(data).decode('ascii')
        return ChatClient.VOICE_PREFIX + b64

    @staticmethod
    def is_voice_text(content):
        return content.startswith(ChatClient.VOICE_PREFIX)

    @staticmethod
    def voice_text_to_wav(content, save_path):
        b64 = content[1:]
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

    # --- File Helpers (inline base64 with ! prefix) ---
    @staticmethod
    def file_to_text(filepath):
        with open(filepath, 'rb') as f:
            data = f.read()
        mime = mimetypes.guess_type(filepath)[0] or 'application/octet-stream'
        b64 = base64.b64encode(data).decode('ascii')
        name = os.path.basename(filepath)
        return ChatClient.FILE_PREFIX + f"{len(data)}:{name}:{mime}:" + b64

    @staticmethod
    def is_file_text(content):
        return content.startswith(ChatClient.FILE_PREFIX)

    @staticmethod
    def parse_file_text(content):
        parts = content[1:].split(':', 3)
        if len(parts) < 4:
            return None
        size, name, mime, b64 = parts
        return {'size': int(size), 'name': name, 'mime': mime, 'data': base64.b64decode(b64)}

    # --- Polling ---
    def _start_polling(self):
        if self._poll_thread and self._poll_thread.is_alive():
            self._stop_polling.set()
            self._poll_thread.join(timeout=2)
        self._stop_polling.clear()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()
        self._start_websocket()

    def _start_websocket(self):
        try:
            import websocket
            ws_url = self.api_base.replace('https://', 'wss://') + '/ws'
            self._ws = websocket.WebSocketApp(ws_url,
                on_message=lambda ws, msg: self._on_ws_message(msg),
                on_error=lambda ws, err: None,
                on_close=lambda ws, code, msg: None)
            self._ws.on_open = lambda ws: self._ws_send({'type': 'subscribe', 'user_id': self.user_id, 'rooms': []})
            self._ws_thread = threading.Thread(target=self._ws.run_forever, daemon=True)
            self._ws_thread.start()
        except ImportError:
            self._ws = None
        except Exception:
            self._ws = None

    def _ws_send(self, data):
        if self._ws:
            try:
                self._ws.send(json.dumps(data))
            except Exception:
                pass

    def _on_ws_message(self, msg):
        try:
            data = json.loads(msg)
            evt = data.get('event')
            payload = data.get('data')
            if evt and payload:
                with self._event_lock:
                    self.event_queue.append((evt, payload))
        except Exception:
            pass

    def _poll_loop(self):
        failures = 0
        heartbeat_count = 0
        while not self._stop_polling.is_set():
            try:
                heartbeat_count += 1
                if heartbeat_count % 5 == 0:
                    self._post('heartbeat')
                rooms_resp = self._get('rooms')
                failures = 0
                for room in rooms_resp.get('rooms', []):
                    rid = room.get('id')
                    unread = room.get('unread_count', 0)
                    if rid and unread > 0:
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
            except ChatError as e:
                failures += 1
                if "401" in str(e) or "Authentication required" in str(e):
                    if self._saved_username:
                        self.reconnect()
                elif failures >= 3:
                    if self._saved_username:
                        self.reconnect()
                        failures = 0
            except Exception:
                failures += 1
                if failures >= 5:
                    failures = 3
            if self._stop_polling.wait(3):
                break

    def poll_event(self):
        with self._event_lock:
            if self.event_queue:
                return self.event_queue.pop(0)
        return None
