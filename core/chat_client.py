import json
import threading
import time
import requests


class ChatError(Exception):
    pass


class ChatClient:
    def __init__(self, api_base=None):
        self.api_base = api_base or 'https://chat.example.com/api'
        self.token = None
        self.user_id = None
        self.username = None
        self.role = 'user'
        self.is_connected = False
        self.event_queue = []
        self._polling = False
        self._poll_thread = None
        self._last_msg_id = 0

    def _headers(self):
        h = {'Content-Type': 'application/json'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h

    def _post(self, path, data=None):
        try:
            r = requests.post(f'{self.api_base}/{path}', json=data or {}, headers=self._headers(), timeout=10)
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
            r = requests.get(f'{self.api_base}/{path}', params=params, headers=self._headers(), timeout=10)
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

    def get_rooms(self):
        return self._get('rooms')

    def create_room(self, name, description=''):
        return self._post('rooms', {'name': name, 'description': description})

    def join_room(self, room_id):
        return self._post(f'rooms/{room_id}/join')

    def leave_room(self, room_id):
        return self._post(f'rooms/{room_id}/leave')

    def send_message(self, room_id, content, msg_type='text'):
        return self._post(f'rooms/{room_id}/messages', {'content': content, 'type': msg_type})

    def get_messages(self, room_id, since_id=None):
        params = {}
        if since_id:
            params['since_id'] = since_id
        return self._get(f'rooms/{room_id}/messages', params)

    def get_users(self):
        return self._get('users')

    def search_users(self, query):
        return self._get('users', {'query': query})

    def grant_admin(self, username):
        return self._post('admin/grant', {'username': username})

    def revoke_admin(self, username):
        return self._post('admin/revoke', {'username': username})

    def _start_polling(self):
        self._polling = True
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def _poll_loop(self):
        while self._polling:
            try:
                rooms_resp = self._get('rooms')
                rooms = rooms_resp.get('rooms', [])
                for room in rooms:
                    rid = room.get('id')
                    since = room.get('_last_seen', 0)
                    if since:
                        result = self.get_messages(rid, since_id=since)
                        for m in result.get('messages', []):
                            mid = m.get('id', 0)
                            if mid > since:
                                self.event_queue.append(('room_message', m))
                                room['_last_seen'] = mid
            except Exception:
                pass
            time.sleep(3)

    def poll_event(self):
        if self.event_queue:
            return self.event_queue.pop(0)
        return None
