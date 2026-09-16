const TOKEN_URL = "http://127.0.0.1:8765/token";
const WS_URL = "ws://127.0.0.1:8765/";
const MAX_BACKOFF_MS = 30000;

let socket = null;
let backoffMs = 1000;

async function fetchToken() {
  const response = await fetch(TOKEN_URL);
  if (!response.ok) {
    throw new Error(`Token alınamadı: ${response.status}`);
  }
  const data = await response.json();
  return data.token;
}

async function connect() {
  let token;
  try {
    token = await fetchToken();
    console.log("[ai-notifier] token alındı:", token);
  } catch (err) {
    console.error("[ai-notifier] token alma hatası:", err);
    scheduleReconnect();
    return;
  }

  socket = new WebSocket(WS_URL);

  socket.addEventListener("open", () => {
    console.log("[ai-notifier] WebSocket açıldı, token gönderiliyor");
    socket.send(JSON.stringify({ token: token }));
    backoffMs = 1000;
  });

  socket.addEventListener("close", (event) => {
    console.warn("[ai-notifier] WebSocket kapandı:", event.code, event.reason);
    scheduleReconnect();
  });
  socket.addEventListener("error", (event) => {
    console.error("[ai-notifier] WebSocket hatası:", event);
    socket.close();
  });
}

function scheduleReconnect() {
  setTimeout(connect, backoffMs);
  backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
}

chrome.runtime.onMessage.addListener((message) => {
  console.log("[ai-notifier] mesaj alındı:", message, "socket durumu:", socket ? socket.readyState : "yok");
  if (
    message.type === "state" &&
    socket &&
    socket.readyState === WebSocket.OPEN
  ) {
    socket.send(JSON.stringify({ site: message.site, state: message.state }));
    console.log("[ai-notifier] sunucuya gönderildi:", message.site, message.state);
  }
});

connect();
