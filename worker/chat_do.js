// Durable Object for real-time chat
export class ChatRoom {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.sessions = new Map();
  }

  async fetch(request) {
    const url = new URL(request.url);
    if (url.pathname === '/ws') {
      return this.handleWebSocket(request);
    }
    return new Response('Not found', { status: 404 });
  }

  async handleWebSocket(request) {
    const pair = new WebSocketPair();
    const [client, server] = Object.values(pair);

    server.accept();
    this.sessions.set(server, { server });

    server.addEventListener('message', async (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'subscribe') {
          this.sessions.get(server).userId = data.user_id;
          this.sessions.get(server).rooms = data.rooms || [];
        }
      } catch (e) {}
    });

    server.addEventListener('close', () => {
      this.sessions.delete(server);
    });

    return new Response(null, { status: 101, webSocket: client });
  }

  async broadcast(event, data, roomId, excludeUserId) {
    const msg = JSON.stringify({ event, data });
    for (const [ws, info] of this.sessions) {
      if (excludeUserId && info.userId === excludeUserId) continue;
      if (roomId && info.rooms && !info.rooms.includes(roomId)) continue;
      try {
        ws.send(msg);
      } catch (e) {}
    }
  }
}
