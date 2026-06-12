import os, json, hashlib, hmac
from http.server import HTTPServer, BaseHTTPRequestHandler

DB = {}
NEXT_ID = {'users': 1, 'rooms': 1, 'messages': 1}


def _hash(pw):
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', pw.encode(), salt, 100000)
    return salt.hex() + ':' + key.hex()


def _check(pw, stored):
    if not stored or ':' not in stored: return False
    s = bytes.fromhex(stored.split(':')[0])
    key = hashlib.pbkdf2_hmac('sha256', pw.encode(), s, 100000)
    return hmac.compare_digest(key.hex(), stored.split(':')[1])


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0]
        qs = {}
        if '?' in self.path:
            for p in self.path.split('?')[1].split('&'):
                if '=' in p:
                    k, v = p.split('=', 1)
                    qs[k] = v
        uid = self._get_uid()

        if path == '/rooms':
            rooms = []
            for r in DB.get('rooms', {}).values():
                r['member_count'] = len(DB.get('room_members', {}).get(r['id'], []))
                r['is_member'] = uid and uid in DB.get('room_members', {}).get(r['id'], set())
                rooms.append(r)
            self._send(200, {'rooms': rooms})
        elif path.startswith('/rooms/') and len(path.split('/')) >= 4:
            parts = path.split('/')
            rid = int(parts[2])
            if parts[3] == 'messages':
                since = int(qs.get('since_id', 0))
                msgs = [m for m in DB.get('messages', {}).values() if m['room_id'] == rid and m['id'] > since]
                self._send(200, {'messages': msgs})
            else:
                self._send(404, {'error': 'Not found'})
        elif path == '/users':
            users = [{'id': u['id'], 'username': u['username'], 'role': u['role']} for u in DB.get('users', {}).values()]
            self._send(200, {'users': users})
        elif path == '/status':
            self._send(200, {'status': 'ok'})
        else:
            self._send(404, {'error': 'Not found'})

    def do_POST(self):
        path = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(length).decode()) if length else {}
        uid = self._get_uid()

        if path == '/register':
            u = body.get('username', '').strip()
            p = body.get('password', '')
            if not u or not p:
                return self._send(400, {'error': 'Required'})
            if any(v['username'] == u for v in DB.get('users', {}).values()):
                return self._send(409, {'error': 'Taken'})
            uid = NEXT_ID['users']; NEXT_ID['users'] += 1
            DB.setdefault('users', {})[uid] = {'id': uid, 'username': u, 'password_hash': _hash(p), 'role': 'user'}
            self._send(201, {'user_id': uid, 'username': u})
        elif path == '/login':
            u, p = body.get('username', '').strip(), body.get('password', '')
            for v in DB.get('users', {}).values():
                if v['username'] == u and _check(p, v['password_hash']):
                    self._send(200, {'user_id': v['id'], 'username': v['username'], 'role': v['role']})
                    return
            self._send(401, {'error': 'Invalid'})
        elif path == '/password':
            user = self._get_user(uid)
            if not user or not _check(body.get('old_password', ''), user['password_hash']):
                return self._send(401, {'error': 'Wrong password'})
            DB['users'][uid]['password_hash'] = _hash(body['new_password'])
            self._send(200, {'success': True})
        elif path == '/rooms':
            n = body.get('name', '').strip()
            if not n: return self._send(400, {'error': 'Name required'})
            rid = NEXT_ID['rooms']; NEXT_ID['rooms'] += 1
            r = {'id': rid, 'name': n, 'description': body.get('description', ''), 'created_by': uid}
            DB.setdefault('rooms', {})[rid] = r
            DB.setdefault('room_members', {}).setdefault(rid, set()).add(uid)
            self._send(201, {'room': r})
        elif path.startswith('/rooms/') and len(path.split('/')) >= 4:
            parts = path.split('/'); rid = int(parts[2])
            if parts[3] == 'join':
                DB.setdefault('room_members', {}).setdefault(rid, set()).add(uid)
                self._send(200, {'success': True})
            elif parts[3] == 'leave':
                DB.get('room_members', {}).get(rid, set()).discard(uid)
                self._send(200, {'success': True})
            elif parts[3] == 'messages':
                c = body.get('content', '').strip()
                if not c: return self._send(400, {'error': 'Required'})
                mid = NEXT_ID['messages']; NEXT_ID['messages'] += 1
                user = self._get_user(uid)
                msg = {'id': mid, 'room_id': rid, 'sender_id': uid, 'sender_username': user['username'] if user else '?', 'type': body.get('type', 'text'), 'content': c}
                DB.setdefault('messages', {})[mid] = msg
                self._send(201, {'message': msg})
        elif path == '/admin/grant':
            user = self._get_user(uid)
            if not user or user['role'] != 'admin': return self._send(403, {'error': 'Admin only'})
            for v in DB.get('users', {}).values():
                if v['username'] == body.get('username', ''):
                    v['role'] = 'admin'; return self._send(200, {'success': True})
            self._send(404, {'error': 'Not found'})
        elif path == '/admin/revoke':
            user = self._get_user(uid)
            if not user or user['role'] != 'admin': return self._send(403, {'error': 'Admin only'})
            for v in DB.get('users', {}).values():
                if v['username'] == body.get('username', ''):
                    if v['username'] in ('natan', 'tech'): return self._send(403, {'error': 'Cannot revoke default admin'})
                    v['role'] = 'user'; return self._send(200, {'success': True})
            self._send(404, {'error': 'Not found'})
        else:
            self._send(404, {'error': 'Not found'})

    def _get_uid(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer ') and auth[7:].isdigit():
            return int(auth[7:])
        return None

    def _get_user(self, uid):
        return DB.get('users', {}).get(uid)


if __name__ == '__main__':
    print("Starting dev server on http://localhost:8765")
    HTTPServer(('', 8765), Handler).serve_forever()
