// Tech-Chat Worker with KV + DMs
// Voice messages = text with ` prefix, File messages = text with ! prefix (base64 encoded)

async function hash(password, salt) {
  if (!salt) salt = crypto.getRandomValues(new Uint8Array(16));
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' }, key, 256);
  const keyHex = Array.from(new Uint8Array(bits)).map(b => b.toString(16).padStart(2, '0')).join('');
  const saltHex = Array.from(salt).map(b => b.toString(16).padStart(2, '0')).join('');
  return saltHex + ':' + keyHex;
}

async function check(password, stored) {
  if (!stored || !stored.includes(':')) return false;
  const [saltHex, storedKey] = stored.split(':');
  const salt = new Uint8Array(saltHex.match(/.{2}/g).map(b => parseInt(b, 16)));
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey('raw', enc.encode(password), { name: 'PBKDF2' }, false, ['deriveBits']);
  const bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', salt, iterations: 100000, hash: 'SHA-256' }, key, 256);
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

function corsResp() {
  return new Response(null, {
    status: 204,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type,Authorization',
      'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS',
    },
  });
}

async function kvGet(env, key) {
  const raw = await env.CHAT_DATA.get(key);
  return raw ? JSON.parse(raw) : null;
}
async function kvPut(env, key, value) { await env.CHAT_DATA.put(key, JSON.stringify(value)); }
async function kvDelete(env, key) { await env.CHAT_DATA.delete(key); }
async function kvList(env, prefix) { const l = await env.CHAT_DATA.list({ prefix }); return l.keys.map(k => k.name); }

async function nextId(env, type) {
  const key = `counter:${type}`;
  const raw = await env.CHAT_DATA.get(key);
  const current = raw ? parseInt(raw, 10) : 0;
  const next = current + 1;
  await env.CHAT_DATA.put(key, next.toString());
  return next;
}

async function initAdmins(env) {
  const initialized = await kvGet(env, 'initialized');
  if (initialized) return;
  const ADMIN_USERS = ['natan', 'tech'];
  const ADMIN_PASSWORDS = { natan: 'Natan2014!', tech: 'tech' };
  const users = await kvGet(env, 'users') || {};
  for (const u of ADMIN_USERS) {
    if (!users[u]) {
      const id = await nextId(env, 'users');
      users[u] = { id, username: u, password_hash: await hash(ADMIN_PASSWORDS[u]), role: 'admin' };
    }
  }
  await kvPut(env, 'users', users);
  await kvPut(env, 'initialized', true);
}

// --- Auth ---
async function register(env, body) {
  const u = (body.username || '').trim();
  const p = body.password || '';
  if (!u || !p) return jsonResp(400, { error: 'Username and password required' });
  if (u.length > 32) return jsonResp(400, { error: 'Username too long' });
  const users = await kvGet(env, 'users') || {};
  if (users[u]) return jsonResp(409, { error: 'Username taken' });
  const id = await nextId(env, 'users');
  users[u] = { id, username: u, password_hash: await hash(p), role: 'user' };
  await kvPut(env, 'users', users);
  return jsonResp(201, { user_id: id, username: u });
}

async function login(env, body) {
  const u = (body.username || '').trim();
  const p = body.password || '';
  await initAdmins(env);
  const users = await kvGet(env, 'users') || {};
  const user = users[u];
  if (!user) return jsonResp(401, { error: 'Invalid credentials' });
  if (!user.password_hash) {
    user.password_hash = await hash(p);
    await kvPut(env, 'users', users);
  } else if (!(await check(p, user.password_hash))) {
    return jsonResp(401, { error: 'Invalid credentials' });
  }
  // Generate session token
  const tokenBytes = new Uint8Array(32);
  crypto.getRandomValues(tokenBytes);
  const token = Array.from(tokenBytes).map(b => b.toString(16).padStart(2, '0')).join('');
  const sessions = await kvGet(env, 'sessions') || {};
  sessions[token] = { user_id: user.id, created_at: Date.now() };
  await kvPut(env, 'sessions', sessions);
  return jsonResp(200, { user_id: user.id, username: user.username, role: user.role, token });
}

async function changePassword(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  if (!(await check(body.old_password || '', user.password_hash)))
    return jsonResp(401, { error: 'Old password is incorrect' });
  user.password_hash = await hash(body.new_password);
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

// --- Rooms ---
async function getRooms(env, uid) {
  const rooms = await kvGet(env, 'rooms') || {};
  const memberships = await kvGet(env, 'memberships') || {};
  const unread = await kvGet(env, 'unread') || {};
  const result = Object.values(rooms).map(r => {
    const members = memberships[r.id] || [];
    return {
      ...r,
      member_count: members.length,
      is_member: members.includes(uid),
      unread_count: (unread[uid] && unread[uid][r.id]) || 0,
    };
  });
  result.sort((a, b) => a.name.localeCompare(b.name));
  return jsonResp(200, { rooms: result });
}

async function createRoom(env, uid, body) {
  const n = (body.name || '').trim();
  if (!n) return jsonResp(400, { error: 'Room name required' });
  const rooms = await kvGet(env, 'rooms') || {};
  const memberships = await kvGet(env, 'memberships') || {};
  const id = await nextId(env, 'rooms');
  rooms[id] = { id, name: n, description: body.description || '', created_by: uid, created_at: new Date().toISOString() };
  memberships[id] = [uid];
  await kvPut(env, 'rooms', rooms);
  await kvPut(env, 'memberships', memberships);
  return jsonResp(201, { room: rooms[id] });
}

async function joinRoom(env, uid, rid) {
  const memberships = await kvGet(env, 'memberships') || {};
  if (!memberships[rid]) memberships[rid] = [];
  if (!memberships[rid].includes(uid)) memberships[rid].push(uid);
  await kvPut(env, 'memberships', memberships);
  return jsonResp(200, { success: true });
}

async function leaveRoom(env, uid, rid) {
  const memberships = await kvGet(env, 'memberships') || {};
  if (memberships[rid]) memberships[rid] = memberships[rid].filter(m => m !== uid);
  await kvPut(env, 'memberships', memberships);
  return jsonResp(200, { success: true });
}

async function deleteRoom(env, uid, rid) {
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user || user.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const rooms = await kvGet(env, 'rooms') || {};
  const memberships = await kvGet(env, 'memberships') || {};
  delete rooms[rid];
  delete memberships[rid];
  await kvPut(env, 'rooms', rooms);
  await kvPut(env, 'memberships', memberships);
  return jsonResp(200, { success: true });
}

// --- Messages ---
async function getMessages(env, rid, sinceId, limit) {
  sinceId = parseInt(sinceId) || 0;
  limit = Math.min(parseInt(limit) || 50, 200);
  const msgs = await kvGet(env, `msgs:${rid}`) || [];
  return jsonResp(200, { messages: msgs.filter(m => m.id > sinceId).slice(-limit) });
}

async function sendMessage(env, uid, rid, body) {
  const c = (body.content || '').trim();
  if (!c) return jsonResp(400, { error: 'Content required' });
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  const block = user ? isBannedOrMuted(user) : null;
  if (block) return jsonResp(403, { error: block });
  const msgs = await kvGet(env, `msgs:${rid}`) || [];
  const id = await nextId(env, 'messages');
  const msg = {
    id, room_id: rid, sender_id: uid,
    sender_username: user ? user.username : '?',
    content: c,
    created_at: new Date().toISOString(),
  };
  msgs.push(msg);
  if (msgs.length > 500) msgs.splice(0, msgs.length - 500);
  await kvPut(env, `msgs:${rid}`, msgs);
  // Update unread
  const memberships = await kvGet(env, 'memberships') || {};
  const members = memberships[rid] || [];
  const unread = await kvGet(env, 'unread') || {};
  for (const mid of members) {
    if (mid === uid) continue;
    if (!unread[mid]) unread[mid] = {};
    unread[mid][rid] = (unread[mid][rid] || 0) + 1;
  }
  await kvPut(env, 'unread', unread);
  // Broadcast via DO
  try {
    const doId = env.CHAT_ROOM.idFromName('global');
    const stub = env.CHAT_ROOM.get(doId);
    stub.broadcast('room_message', msg, rid, uid);
  } catch (e) {}
  return jsonResp(201, { message: msg });
}

async function deleteMessage(env, uid, rid, msgId) {
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  const msgs = await kvGet(env, `msgs:${rid}`) || [];
  const msg = msgs.find(m => m.id === msgId);
  if (!msg) return jsonResp(404, { error: 'Message not found' });
  if (msg.sender_id !== uid && user.role !== 'admin')
    return jsonResp(403, { error: 'Cannot delete others message' });
  msgs.splice(msgs.indexOf(msg), 1);
  await kvPut(env, `msgs:${rid}`, msgs);
  return jsonResp(200, { success: true });
}

async function editMessage(env, uid, rid, msgId, body) {
  const c = (body.content || '').trim();
  if (!c) return jsonResp(400, { error: 'Content required' });
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  const msgs = await kvGet(env, `msgs:${rid}`) || [];
  const msg = msgs.find(m => m.id === msgId);
  if (!msg) return jsonResp(404, { error: 'Message not found' });
  if (msg.sender_id !== uid) return jsonResp(403, { error: 'Can only edit your own messages' });
  msg.content = c;
  msg.edited_at = new Date().toISOString();
  await kvPut(env, `msgs:${rid}`, msgs);
  return jsonResp(200, { success: true });
}

// --- DMs ---
async function getDMList(env, uid) {
  const dms = await kvGet(env, 'dms') || {};
  const users = await kvGet(env, 'users') || {};
  const unread = await kvGet(env, 'dm_unread') || {};
  const conversations = [];
  for (const [key, lastMsg] of Object.entries(dms)) {
    const [a, b] = key.split('-').map(Number);
    if (a !== uid && b !== uid) continue;
    const otherId = a === uid ? b : a;
    const other = Object.values(users).find(u => u.id === otherId);
    if (!other) continue;
    conversations.push({
      user_id: otherId,
      username: other.username,
      last_message: lastMsg,
      unread_count: (unread[uid] && unread[uid][otherId]) || 0,
    });
  }
  conversations.sort((a, b) => (b.last_message?.created_at || '').localeCompare(a.last_message?.created_at || ''));
  return jsonResp(200, { conversations });
}

async function getDMessages(env, uid, otherId, sinceId, limit) {
  sinceId = parseInt(sinceId) || 0;
  limit = Math.min(parseInt(limit) || 50, 200);
  const key = uid < otherId ? `${uid}-${otherId}` : `${otherId}-${uid}`;
  const msgs = await kvGet(env, `dm:${key}`) || [];
  const unread = await kvGet(env, 'dm_unread') || {};
  if (unread[uid]) unread[uid][otherId] = 0;
  await kvPut(env, 'dm_unread', unread);
  return jsonResp(200, { messages: msgs.filter(m => m.id > sinceId).slice(-limit) });
}

async function sendDM(env, uid, otherId, body) {
  const c = (body.content || '').trim();
  if (!c) return jsonResp(400, { error: 'Content required' });
  const users = await kvGet(env, 'users') || {};
  const sender = Object.values(users).find(u => u.id === uid);
  const block = sender ? isBannedOrMuted(sender) : null;
  if (block) return jsonResp(403, { error: block });
  const receiver = Object.values(users).find(u => u.id === otherId);
  if (!receiver) return jsonResp(404, { error: 'User not found' });
  const key = uid < otherId ? `${uid}-${otherId}` : `${otherId}-${uid}`;
  const msgs = await kvGet(env, `dm:${key}`) || [];
  const id = await nextId(env, 'messages');
  const msg = {
    id, sender_id: uid, receiver_id: otherId,
    sender_username: sender ? sender.username : '?',
    content: c,
    created_at: new Date().toISOString(),
  };
  msgs.push(msg);
  if (msgs.length > 500) msgs.splice(0, msgs.length - 500);
  await kvPut(env, `dm:${key}`, msgs);
  const dms = await kvGet(env, 'dms') || {};
  dms[key] = msg;
  await kvPut(env, 'dms', dms);
  const unread = await kvGet(env, 'dm_unread') || {};
  if (!unread[otherId]) unread[otherId] = {};
  unread[otherId][uid] = (unread[otherId][uid] || 0) + 1;
  await kvPut(env, 'dm_unread', unread);
  // Broadcast via DO
  try {
    const doId = env.CHAT_ROOM.idFromName('global');
    const stub = env.CHAT_ROOM.get(doId);
    stub.broadcast('dm_message', msg, null, uid);
  } catch (e) {}
  return jsonResp(201, { message: msg });
}

async function deleteDM(env, uid, msgId) {
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  const keys = await kvList(env, 'dm:');
  for (const key of keys) {
    const msgs = await kvGet(env, key) || [];
    const msg = msgs.find(m => m.id === msgId);
    if (msg) {
      if (msg.sender_id !== uid && user.role !== 'admin')
        return jsonResp(403, { error: 'Cannot delete others message' });
      msgs.splice(msgs.indexOf(msg), 1);
      await kvPut(env, key, msgs);
      return jsonResp(200, { success: true });
    }
  }
  return jsonResp(404, { error: 'Message not found' });
}

async function editDM(env, uid, msgId, body) {
  const c = (body.content || '').trim();
  if (!c) return jsonResp(400, { error: 'Content required' });
  const users = await kvGet(env, 'users') || {};
  const user = Object.values(users).find(u => u.id === uid);
  if (!user) return jsonResp(404, { error: 'User not found' });
  const keys = await kvList(env, 'dm:');
  for (const key of keys) {
    const msgs = await kvGet(env, key) || [];
    const msg = msgs.find(m => m.id === msgId);
    if (msg) {
      if (msg.sender_id !== uid) return jsonResp(403, { error: 'Can only edit your own messages' });
      msg.content = c;
      msg.edited_at = new Date().toISOString();
      await kvPut(env, key, msgs);
      return jsonResp(200, { success: true });
    }
  }
  return jsonResp(404, { error: 'Message not found' });
}

// --- Users ---
async function getUsers(env) {
  const users = await kvGet(env, 'users') || {};
  const result = Object.values(users).map(u => ({ id: u.id, username: u.username, role: u.role }));
  result.sort((a, b) => a.username.localeCompare(b.username));
  return jsonResp(200, { users: result });
}

async function searchUsers(env, query) {
  const users = await kvGet(env, 'users') || {};
  const q = query.toLowerCase();
  return jsonResp(200, { users: Object.values(users).filter(u => u.username.toLowerCase().includes(q)).map(u => ({ id: u.id, username: u.username, role: u.role })) });
}

// --- Admin ---
async function grantAdmin(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  target.role = 'admin';
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

async function revokeAdmin(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  if (['natan', 'tech'].includes(target.username)) return jsonResp(403, { error: 'Cannot revoke default admin' });
  target.role = 'user';
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

// --- Admin: Ban / Mute / Broadcast ---
async function banUser(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  target.banned = true;
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

async function unbanUser(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  target.banned = false;
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

async function muteUser(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  const durationMs = (parseInt(body.duration_minutes) || 5) * 60 * 1000;
  target.muted_until = Date.now() + durationMs;
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true, duration_minutes: body.duration_minutes || 5 });
}

async function unmuteUser(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const target = users[body.username];
  if (!target) return jsonResp(404, { error: 'User not found' });
  delete target.muted_until;
  await kvPut(env, 'users', users);
  return jsonResp(200, { success: true });
}

async function broadcastMsg(env, uid, body) {
  const users = await kvGet(env, 'users') || {};
  const me = Object.values(users).find(u => u.id === uid);
  if (!me || me.role !== 'admin') return jsonResp(403, { error: 'Admin only' });
  const text = (body.message || '').trim();
  if (!text) return jsonResp(400, { error: 'Message required' });
  const rooms = await kvGet(env, 'rooms') || {};
  const systemMsg = { sender_id: 0, sender_username: 'System', content: `[Broadcast] ${text}`, created_at: new Date().toISOString() };
  for (const [rid, room] of Object.entries(rooms)) {
    const msgs = await kvGet(env, `msgs:${rid}`) || [];
    systemMsg.id = await nextId(env, 'messages');
    msgs.push({ ...systemMsg, room_id: parseInt(rid) });
    if (msgs.length > 500) msgs.splice(0, msgs.length - 500);
    await kvPut(env, `msgs:${rid}`, msgs);
  }
  return jsonResp(200, { success: true });
}

function isBannedOrMuted(user) {
  if (user.banned) return 'You are banned from the chat';
  if (user.muted_until && Date.now() < user.muted_until) return 'You are muted';
  return null;
}

// --- File Sharing ---
async function uploadFile(env, uid, body) {
  const name = (body.name || 'file').trim();
  const data = body.data || '';
  if (!data) return jsonResp(400, { error: 'File data required' });
  const maxSize = 1024 * 1024; // 1MB limit
  if (data.length > maxSize) return jsonResp(413, { error: 'File too large (max 1MB)' });
  const fileId = await nextId(env, 'files');
  await kvPut(env, `file:${fileId}`, { id: fileId, name, data, uploaded_by: uid, uploaded_at: new Date().toISOString() });
  return jsonResp(201, { file_id: fileId, name, url: `/files/${fileId}` });
}

async function getFile(env, fileId) {
  const file = await kvGet(env, `file:${fileId}`);
  if (!file) return jsonResp(404, { error: 'File not found' });
  return jsonResp(200, file);
}

// --- Online Status ---
async function heartbeat(env, uid) {
  const online = await kvGet(env, 'online') || {};
  online[uid] = Date.now();
  await kvPut(env, 'online', online);
  return jsonResp(200, { success: true });
}

async function getOnline(env, uid) {
  const online = await kvGet(env, 'online') || {};
  const users = await kvGet(env, 'users') || {};
  const now = Date.now();
  const timeout = 30_000; // 30s without heartbeat = offline
  const result = {};
  for (const [uId, lastSeen] of Object.entries(online)) {
    if (now - lastSeen < timeout) {
      const user = Object.values(users).find(u => u.id === parseInt(uId));
      if (user) result[uId] = 'online';
    }
  }
  return jsonResp(200, { online: result });
}

async function setTyping(env, uid, body) {
  const roomId = body.room_id;
  const targetId = body.target_id;
  const isTyping = body.typing === true;
  const key = roomId ? `typing:room:${roomId}` : `typing:dm:${targetId}`;
  const typing = await kvGet(env, key) || {};
  if (isTyping) {
    typing[uid] = Date.now();
  } else {
    delete typing[uid];
  }
  await kvPut(env, key, typing);
  return jsonResp(200, { success: true });
}

async function getTyping(env, uid, url) {
  const roomId = url.searchParams.get('room_id');
  const targetId = url.searchParams.get('target_id');
  const key = roomId ? `typing:room:${roomId}` : `typing:dm:${targetId}`;
  const typing = await kvGet(env, key) || {};
  const now = Date.now();
  const timeout = 5_000;
  const result = {};
  for (const [userId, ts] of Object.entries(typing)) {
    if (now - ts < timeout) result[userId] = true;
  }
  return jsonResp(200, { typing: result });
}

// --- Rate Limiter (in-memory, per-IP) ---
const rateLimitMap = new Map();
const RATE_LIMIT_WINDOW = 60_000; // 1 minute
const RATE_LIMIT_MAX = 60;        // max requests per window

function rateLimit(request) {
  const ip = request.headers.get('CF-Connecting-IP') || 'unknown';
  const now = Date.now();
  let entry = rateLimitMap.get(ip);
  if (!entry || now - entry.windowStart > RATE_LIMIT_WINDOW) {
    entry = { windowStart: now, count: 0 };
    rateLimitMap.set(ip, entry);
  }
  entry.count++;
  return entry.count <= RATE_LIMIT_MAX;
}

// --- Router ---
export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const method = request.method;
    let path = url.pathname;

    if (method === 'OPTIONS') return corsResp();
    if (!rateLimit(request)) return jsonResp(429, { error: 'Too many requests. Slow down.' });
    if (path.startsWith('/api/')) path = path.slice(4);
    else if (path === '/api') path = '/';

    let body = {};
    if (method !== 'GET' && method !== 'OPTIONS' && method !== 'DELETE') {
      try { body = await request.json(); } catch (e) {}
    }

    const auth = request.headers.get('Authorization') || '';
    const token = auth.startsWith('Bearer ') ? auth.slice(7) : '';
    let uid = null;
    if (token) {
      const sessions = await kvGet(env, 'sessions') || {};
      const session = sessions[token];
      if (session) uid = session.user_id;
    }

    if (!['/register', '/login', '/status'].includes(path) && !uid)
      return jsonResp(401, { error: 'Authentication required' });

    try {
      if (path === '/status') return jsonResp(200, { status: 'ok', version: '3.1.0' });

      if (path === '/register' && method === 'POST') return await register(env, body);
      if (path === '/login' && method === 'POST') return await login(env, body);
      if (path === '/password' && method === 'POST') return await changePassword(env, uid, body);

      if (path === '/rooms' && method === 'GET') return await getRooms(env, uid);
      if (path === '/rooms' && method === 'POST') return await createRoom(env, uid, body);

      const parts = path.split('/').filter(Boolean);
      if (parts[0] === 'rooms' && parts.length >= 2) {
        const rid = parseInt(parts[1]);
        if (!rid) return jsonResp(400, { error: 'Invalid room id' });
        const action = parts[2];
        if (action === 'join' && method === 'POST') return await joinRoom(env, uid, rid);
        if (action === 'leave' && method === 'POST') return await leaveRoom(env, uid, rid);
        if (action === 'delete' && method === 'POST') return await deleteRoom(env, uid, rid);
        if (action === 'messages' && method === 'GET') return await getMessages(env, rid, url.searchParams.get('since_id'), url.searchParams.get('limit'));
        if (action === 'messages' && method === 'POST') return await sendMessage(env, uid, rid, body);
        if (action === 'message' && parts[3] && method === 'DELETE') return await deleteMessage(env, uid, rid, parseInt(parts[3]));
        if (action === 'message' && parts[3] && method === 'PUT') return await editMessage(env, uid, rid, parseInt(parts[3]), body);
      }

      if (parts[0] === 'dm' && parts.length === 1 && method === 'GET') return await getDMList(env, uid);
      if (parts[0] === 'dm' && parts.length === 2 && method === 'GET') return await getDMessages(env, uid, parseInt(parts[1]), url.searchParams.get('since_id'), url.searchParams.get('limit'));
      if (parts[0] === 'dm' && parts.length === 2 && method === 'POST') return await sendDM(env, uid, parseInt(parts[1]), body);
      if (parts[0] === 'dm' && parts[1] === 'message' && parts[2] && method === 'DELETE') return await deleteDM(env, uid, parseInt(parts[2]));
      if (parts[0] === 'dm' && parts[1] === 'message' && parts[2] && method === 'PUT') return await editDM(env, uid, parseInt(parts[2]), body);

      // --- Online Status ---
      if (path === '/heartbeat' && method === 'POST') return await heartbeat(env, uid);
      if (path === '/online' && method === 'GET') return await getOnline(env, uid);
      if (path === '/typing' && method === 'POST') return await setTyping(env, uid, body);
      if (path === '/typing' && method === 'GET') return await getTyping(env, uid, url);

      if (path === '/users' && method === 'GET') {
        const query = url.searchParams.get('query');
        return query ? await searchUsers(env, query) : await getUsers(env);
      }

      if (path === '/admin/grant' && method === 'POST') return await grantAdmin(env, uid, body);
      if (path === '/admin/revoke' && method === 'POST') return await revokeAdmin(env, uid, body);
      if (path === '/admin/ban' && method === 'POST') return await banUser(env, uid, body);
      if (path === '/admin/unban' && method === 'POST') return await unbanUser(env, uid, body);
      if (path === '/admin/mute' && method === 'POST') return await muteUser(env, uid, body);
      if (path === '/admin/unmute' && method === 'POST') return await unmuteUser(env, uid, body);
      if (path === '/admin/broadcast' && method === 'POST') return await broadcastMsg(env, uid, body);

      // --- File Sharing ---
      if (path === '/files/upload' && method === 'POST') return await uploadFile(env, uid, body);
      if (path.startsWith('/files/') && method === 'GET') {
        const fileId = path.split('/')[2];
        return await getFile(env, fileId);
      }

      // WebSocket upgrade
      if (path === '/ws') {
        const doId = env.CHAT_ROOM.idFromName('global');
        const stub = env.CHAT_ROOM.get(doId);
        return stub.fetch(request);
      }

      return jsonResp(404, { error: 'Not found' });
    } catch (e) {
      return jsonResp(500, { error: e.message });
    }
  },
};
