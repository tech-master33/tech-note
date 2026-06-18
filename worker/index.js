function hash(password, salt) {
  if (!salt) salt = crypto.getRandomValues(new Uint8Array(16));
  const enc = new TextEncoder();
  const key = crypto.subtle.importSync('raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']);
  const bits = crypto.subtle.deriveBits({ name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' }, key, 256);
  const keyHex = Array.from(new Uint8Array(bits)).map(b => b.toString(16).padStart(2, '0')).join('');
  const saltHex = Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join('');
  return saltHex + ':' + keyHex;
}

function check(password, stored) {
  if (!stored || !stored.includes(':')) return false;
  const saltHex = stored.split(':')[0];
  const storedKey = stored.split(':')[1];
  const salt = new Uint8Array(saltHex.match(/.{2}/g).map(b => parseInt(b, 16)));
  const enc = new TextEncoder();
  const key = crypto.subtle.importSync('raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']);
  const bits = crypto.subtle.deriveBits({ name: 'PBKDF2', salt: salt, iterations: 100000, hash: 'SHA-256' }, key, 256);
  const keyHex = Array.from(new Uint8Array(bits)).map(b => b.toString(16).padStart(2, '0')).join('');
  return keyHex === storedKey;
}

function jsonResp(code, data) {
  return new Response(JSON.stringify(data), {
    status: code,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    },
  });
}

let DB = null;

function getDb() {
  if (DB) return DB;
  DB = {
    users: {},
    rooms: {},
    room_members: {},
    messages: [],
    next_user_id: 1,
    next_room_id: 1,
    next_msg_id: 1,
  };
  const ADMIN_USERS = ['natan', 'tech'];
  const ADMIN_PASSWORDS = { natan: 'Natan2014!', tech: 'tech' };
  for (const u of ADMIN_USERS) {
    const id = DB.next_user_id++;
    DB.users[u] = { id, username: u, password_hash: hash(ADMIN_PASSWORDS[u]), role: 'admin' };
  }
  return DB;
}

async function register(body) {
  const u = (body.username || '').trim();
  const p = body.password || '';
  if (!u || !p) return jsonResp(400, { error: 'Username and password required' });
  const db = getDb();
  if (db.users[u]) return jsonResp(409, { error: 'Username taken' });
  const id = db.next_user_id++;
  db.users[u] = { id, username: u, password_hash: hash(p), role: 'user' };
  return jsonResp(201, { user_id: id, username: u });
}

async function login(body) {
  const u = (body.username || '').trim();
  const p = body.password || '';
  const db = getDb();
  const user = db.users[u];
  if (!user) return jsonResp(401, { error: 'Invalid credentials' });
  if (!user.password_hash) {
    user.password_hash = hash(p);
  } else if (!check(p, user.password_hash)) {
    return jsonResp(401, { error: 'Invalid credentials' });
  }
  return jsonResp(200, { user_id: user.id, username: user.username, role: user.role });
}

async function changePassword(uid, body) {
  const db = getDb();
  const user = Object.values(db.users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  if (!check(body.old_password || '', user.password_hash))
    return jsonResp(401, { error: 'Old password is incorrect' });
  user.password_hash = hash(body.new_password);
  return jsonResp(200, { success: true });
}

async function getRooms(uid) {
  const db = getDb();
  const rooms = Object.values(db.rooms).map(r => {
    const members = db.room_members[r.id] || [];
    return {
      ...r,
      member_count: members.length,
      is_member: uid ? members.includes(uid) : false,
    };
  });
  rooms.sort((a, b) => a.name.localeCompare(b.name));
  return jsonResp(200, { rooms });
}

async function createRoom(uid, body) {
  const n = (body.name || '').trim();
  if (!n) return jsonResp(400, { error: 'Room name required' });
  const db = getDb();
  const id = db.next_room_id++;
  db.rooms[id] = { id, name: n, description: body.description || '', created_by: uid };
  db.room_members[id] = [uid];
  return jsonResp(201, { room: db.rooms[id] });
}

async function joinRoom(uid, rid) {
  const db = getDb();
  if (!db.room_members[rid]) db.room_members[rid] = [];
  if (!db.room_members[rid].includes(uid)) db.room_members[rid].push(uid);
  return jsonResp(200, { success: true });
}

async function leaveRoom(uid, rid) {
  const db = getDb();
  if (db.room_members[rid]) {
    db.room_members[rid] = db.room_members[rid].filter(m => m !== uid);
  }
  return jsonResp(200, { success: true });
}

async function getMessages(rid, sinceId) {
  const db = getDb();
  sinceId = parseInt(sinceId) || 0;
  const msgs = db.messages.filter(m => m.room_id === rid && m.id > sinceId);
  return jsonResp(200, { messages: msgs });
}

async function sendMessage(uid, rid, body) {
  const c = (body.content || '').trim();
  if (!c) return jsonResp(400, { error: 'Content required' });
  const db = getDb();
  const user = Object.values(db.users).find(u => u.id === uid);
  const id = db.next_msg_id++;
  const msg = {
    id, room_id: rid, sender_id: uid,
    sender_username: user ? user.username : '?',
    type: body.type || 'text', content: c,
    created_at: new Date().toISOString(),
  };
  db.messages.push(msg);
  const keep = {};
  for (let i = db.messages.length - 1; i >= 0; i--) {
    const m = db.messages[i];
    if (!keep[m.room_id]) keep[m.room_id] = 0;
    keep[m.room_id]++;
  }
  const filtered = [];
  for (let i = db.messages.length - 1; i >= 0; i--) {
    const m = db.messages[i];
    if (keep[m.room_id] > 0 && keep[m.room_id] <= 200) {
      filtered.unshift(m);
    } else {
      keep[m.room_id]--;
    }
  }
  db.messages = filtered;
  return jsonResp(201, { message: msg });
}

async function getUsers() {
  const db = getDb();
  const users = Object.values(db.users).map(u => ({
    id: u.id, username: u.username, role: u.role,
  }));
  users.sort((a, b) => a.username.localeCompare(b.username));
  return jsonResp(200, { users });
}

async function searchUsers(query) {
  const db = getDb();
  const q = query.toLowerCase();
  const users = Object.values(db.users)
    .filter(u => u.username.toLowerCase().includes(q))
    .map(u => ({ id: u.id, username: u.username, role: u.role }));
  return jsonResp(200, { users });
}

async function grantAdmin(uid, body) {
  const db = getDb();
  const me = Object.values(db.users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = db.users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  target.role = 'admin';
  return jsonResp(200, { success: true });
}

async function revokeAdmin(uid, body) {
  const db = getDb();
  const me = Object.values(db.users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = db.users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  const ADMIN_USERS = ['natan', 'tech'];
  if (ADMIN_USERS.includes(target.username))
    return jsonResp(403, { error: 'Cannot revoke default admin' });
  target.role = 'user';
  return jsonResp(200, { success: true });
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;
    let path = url.pathname;

    if (path.startsWith('/api/')) path = path.slice(4);
    else if (path === '/api') path = '/';

    if (method === 'OPTIONS') return jsonResp(200, {});

    let body = {};
    if (method !== 'GET' && method !== 'OPTIONS') {
      try { body = await request.json(); } catch (e) {}
    }

    const auth = request.headers.get('Authorization') || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    const uid = /^\d+$/.test(token) ? parseInt(token) : null;

    if (!['/register', '/login', '/status'].includes(path) && !uid)
      return jsonResp(401, { error: 'Authentication required' });

    try {
      if (path === '/register' && method === 'POST') return await register(body);
      if (path === '/login' && method === 'POST') return await login(body);
      if (path === '/password' && method === 'POST') return await changePassword(uid, body);

      if (path === '/rooms' && method === 'GET') return await getRooms(uid);
      if (path === '/rooms' && method === 'POST') return await createRoom(uid, body);

      const parts = path.split('/').filter(Boolean);
      if (parts[0] === 'rooms' && parts.length >= 2) {
        const rid = parseInt(parts[1]);
        if (!rid) return jsonResp(400, { error: 'Invalid room id' });
        const action = parts[2];
        if (action === 'join' && method === 'POST') return await joinRoom(uid, rid);
        if (action === 'leave' && method === 'POST') return await leaveRoom(uid, rid);
        if (action === 'messages' && method === 'GET') return await getMessages(rid, url.searchParams.get('since_id'));
        if (action === 'messages' && method === 'POST') return await sendMessage(uid, rid, body);
      }

      if (path === '/users' && method === 'GET') {
        const query = url.searchParams.get('query');
        if (query) return await searchUsers(query);
        return await getUsers();
      }

      if (path === '/admin/grant' && method === 'POST') return await grantAdmin(uid, body);
      if (path === '/admin/revoke' && method === 'POST') return await revokeAdmin(uid, body);
      if (path === '/status') return jsonResp(200, { status: 'ok' });

      return jsonResp(404, { error: 'Not found' });
    } catch (e) {
      return jsonResp(500, { error: e.message });
    }
  },
};
