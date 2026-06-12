import asyncio
import json
import threading
import queue

import websockets


class TitanNetError(Exception):
    pass


class TitanNetClient:
    def __init__(self, server_host='titosofttitan.com', server_port=8001):
        self.server_host = server_host
        self.server_port = server_port
        self.ws_url = f'wss://{server_host}:{server_port}'
        self.http_url = f'https://{server_host}:8000'

        self.ws = None
        self.session_id = None
        self.username = None
        self.user_id = None
        self.titan_number = None
        self.is_connected = False
        self.is_admin = False
        self.user_role = 'user'
        self.has_custom_sounds = False

        self._loop = None
        self._loop_thread = None
        self._loop_ready = threading.Event()
        self._inbox = queue.Queue()
        self.event_queue = queue.Queue()
        self._listener_running = False

    def _start_event_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop_ready.set()
        self._loop.run_forever()

    def _ensure_loop(self):
        if self._loop is None or not self._loop.is_running():
            self._loop_thread = threading.Thread(target=self._start_event_loop, daemon=True)
            self._loop_thread.start()
            self._loop_ready.wait()

    def _run_async(self, coro):
        self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=30)

    def _run_async_ff(self, coro):
        self._ensure_loop()
        asyncio.run_coroutine_threadsafe(coro, self._loop)

    # --- listener ---

    async def _listen_loop(self):
        while self._listener_running and self.ws:
            try:
                raw = await self.ws.recv()
            except websockets.exceptions.ConnectionClosed:
                self.is_connected = False
                self.ws = None
                self.event_queue.put(('connection_lost', {}))
                break
            except Exception:
                break
            if isinstance(raw, bytes):
                self.event_queue.put(('voice_audio_binary', raw))
                continue
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            self._inbox.put(data)

    # --- send / wait ---

    def _send_and_wait(self, msg, expected_type, timeout=10):
        if not self.ws:
            raise TitanNetError('Not connected')
        self._run_async(self._ws_send(json.dumps(msg)))
        deadline = threading.Event()
        self._ensure_loop()
        fut = asyncio.run_coroutine_threadsafe(
            self._wait_for_type(expected_type, timeout), self._loop
        )
        try:
            return fut.result(timeout=timeout + 5)
        except TimeoutError:
            raise TitanNetError(f'Response timeout for {expected_type}')

    async def _wait_for_type(self, expected_type, timeout):
        import time
        start = time.monotonic()
        while time.monotonic() - start < timeout:
            try:
                data = self._inbox.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            msg_type = data.get('type', '')
            if msg_type == expected_type:
                return data
            self._dispatch_event(msg_type, data)
        raise TimeoutError

    async def _ws_send(self, msg):
        if self.ws:
            await self.ws.send(msg)

    # --- dispatch ---

    def _dispatch_event(self, msg_type, data):
        if msg_type == 'private_message':
            self.event_queue.put(('message', data))
        elif msg_type == 'user_status':
            self.event_queue.put(('user_online' if data.get('status') == 'online' else 'user_offline', data))
        elif msg_type == 'room_message':
            self.event_queue.put(('room_message', data))
        elif msg_type == 'new_room':
            self.event_queue.put(('room_created', data))
        elif msg_type == 'room_removed':
            self.event_queue.put(('room_deleted', data))
        elif msg_type == 'user_joined_room':
            self.event_queue.put(('user_joined_room', data))
        elif msg_type == 'user_left_room':
            self.event_queue.put(('user_left_room', data))
        elif msg_type == 'unread_messages_summary':
            self.event_queue.put(('unread_summary', data))

    # --- connect / login ---

    def connect(self):
        self._run_async(self._connect())

    async def _connect(self):
        self.ws = await websockets.connect(
            self.ws_url,
            ping_interval=None,
            max_size=52428800,
            max_queue=1024,
            write_limit=2097152,
            compression=None,
            open_timeout=10.0
        )

    def login(self, username, password):
        return self._run_async(self._login(username, password))

    async def _login(self, username, password):
        await self._connect()
        msg = {'type': 'login', 'username': username, 'password': password, 'language': 'en'}
        await self.ws.send(json.dumps(msg))
        raw = await asyncio.wait_for(self.ws.recv(), timeout=30)
        data = json.loads(raw)
        if data.get('type') != 'login_response' or not data.get('success'):
            await self.ws.close()
            self.ws = None
            raise TitanNetError(data.get('message', 'Login failed'))
        self.session_id = data['session_id']
        user = data.get('user', {})
        self.username = user.get('username', username)
        self.user_id = user.get('id')
        self.titan_number = user.get('titan_number')
        self.is_admin = user.get('is_admin', False)
        self.user_role = user.get('role', 'user')
        self.has_custom_sounds = data.get('has_custom_sounds', False)
        self.is_connected = True
        self._listener_running = True
        self._run_async_ff(self._listen_loop())
        return data

    def register(self, username, password, full_name):
        return self._run_async(self._register(username, password, full_name))

    async def _register(self, username, password, full_name):
        ws = await websockets.connect(
            self.ws_url,
            ping_interval=None,
            max_size=52428800,
            open_timeout=10.0
        )
        msg = {'type': 'register', 'username': username, 'password': password, 'full_name': full_name, 'language': 'en'}
        await ws.send(json.dumps(msg))
        raw = await asyncio.wait_for(ws.recv(), timeout=30)
        data = json.loads(raw)
        await ws.close()
        if data.get('type') != 'register_response' or not data.get('success'):
            raise TitanNetError(data.get('message', 'Registration failed'))
        return data

    def logout(self):
        self._listener_running = False
        if self.ws and self._loop and self._loop.is_running():
            try:
                fut = asyncio.run_coroutine_threadsafe(self._close_ws(), self._loop)
                fut.result(timeout=5)
            except Exception:
                pass
        self.is_connected = False
        self.session_id = None
        return {'success': True}

    async def _close_ws(self):
        if self.ws:
            await self.ws.close()
            self.ws = None

    def _send_and_forget(self, msg):
        if not self.ws:
            raise TitanNetError('Not connected')
        self._run_async(self._ws_send(json.dumps(msg)))

    # --- rooms ---

    def get_rooms(self):
        return self._send_and_wait({'type': 'get_rooms'}, 'rooms_list')

    def create_room(self, name, description='', room_type='Text Chat'):
        return self._send_and_wait(
            {'type': 'create_room', 'name': name, 'description': description, 'room_type': room_type},
            'room_created'
        )

    def join_room(self, room_id):
        return self._send_and_wait({'type': 'join_room', 'room_id': room_id}, 'room_joined')

    def send_room_message(self, room_id, message):
        self._send_and_forget({'type': 'send_room_message', 'room_id': room_id, 'message': message})

    def get_room_messages(self, room_id, limit=50):
        return self._send_and_wait(
            {'type': 'get_room_messages', 'room_id': room_id, 'limit': limit},
            'room_messages'
        )

    def get_online_users(self):
        return self._send_and_wait({'type': 'get_online_users'}, 'online_users')

    def send_private_message(self, username, message):
        self._send_and_forget({'type': 'send_private_message', 'username': username, 'message': message})

    def get_private_messages(self, username, limit=50):
        return self._send_and_wait(
            {'type': 'get_private_messages', 'username': username, 'limit': limit},
            'private_messages'
        )

    # --- polling ---

    def poll_event(self):
        try:
            return self.event_queue.get_nowait()
        except queue.Empty:
            return None
