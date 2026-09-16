# Tarayıcı Eklentisi (Faz 2, Alt-Proje 1/3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** claude.ai ve chatgpt.com sekmelerindeki YZ durumunu bir tarayıcı eklentisiyle
izleyip, yerel WebSocket bağlantısı üzerinden mevcut Windows masaüstü servisine iletmek;
servis bu bilgiyi zaten var olan `DecisionEngine`/bildirim katmanından geçirsin.

**Architecture:** Content script `MutationObserver` ile `chat-input-stop` elemanının
var/yok olduğunu izler, background service worker yerel bir token alıp WebSocket ile
`web_bridge.py`'a bağlanır. `web_bridge.py`, gelen `{site, state}` mesajlarını mevcut
`DecisionEngine`'e besler — masaüstü sensörleriyle aynı debounce/bildirim mantığı
paylaşılır (bu paylaşımı sağlamak için `service.py`'daki mantık `NotificationDispatcher`
sınıfına çıkarılır).

**Tech Stack:** Manifest V3 tarayıcı eklentisi (vanilla JS), `websockets==12.0` (Python
WebSocket sunucusu), mevcut `ai_notifier` paketi.

## Global Constraints

- Hedef siteler: claude.ai + chatgpt.com (spec bölüm 1).
- Kapsam dışı: cihaz eşleştirme/auth (Next.js+Supabase), mobil FCM app (spec bölüm 1) —
  bu plana dahil edilmez.
- Birincil tespit sinyali: `[data-testid="chat-input-stop"]` DOM'da var/yok (spec
  bölüm 2, gerçek DOM'dan doğrulandı) — sadece claude.ai için doğrulandı.
- chatgpt.com selektörleri ve onay/hata sinyalleri DOĞRULANMADI (spec bölüm 2/6) — tahmini
  kod yazılır, gerçek kullanımda düzeltilir.
- Content script dosya sistemini okuyamaz; token, `GET /token` + CORS ile
  `chrome-extension://<ID>` origin'ine kısıtlı olarak dağıtılır (spec bölüm 3.2).
- Token doğrulanana kadar WebSocket bağlantısından başka mesaj işlenmez (spec bölüm 3.2).
- `DecisionEngine`/`state_to_notification`/`WindowsToastNotifier` DEĞİŞTİRİLMEZ, yeniden
  kullanılır (spec bölüm 3.3).

---

## Dosya Yapısı

```
D:\ai-notifier\
  extension\
    manifest.json
    content_script.js
    background.js
  src\ai_notifier\core\
    dispatcher.py         # YENİ: NotificationDispatcher (service.py'dan çıkarıldı)
    web_bridge.py          # YENİ: token üretimi/doğrulama + WebSocket sunucu
    service.py             # DEĞİŞECEK: dispatcher + web_bridge + polling'i birlikte çalıştırır
  tests\
    test_dispatcher.py
    test_web_bridge.py
```

---

### Task 1: `NotificationDispatcher` — `service.py`'dan Çıkarma (Refactor, TDD)

**Files:**
- Create: `src\ai_notifier\core\dispatcher.py`
- Modify: `src\ai_notifier\core\service.py`
- Test: `tests\test_dispatcher.py`

**Interfaces:**
- Consumes: `DecisionEngine` (mevcut), `state_to_notification` (mevcut),
  `NotificationSender` arayüzü (mevcut, Task 5'ten)
- Produces: `NotificationDispatcher(notifier: NotificationSender, stability_threshold: int = 2)`
  - `.submit(source_name: str, raw_state: SensorState) -> None`

Bu, masaüstü sensör polling'i VE web bridge'in AYNI debounce/bildirim mantığını
paylaşmasını sağlayan tek nokta. Önceden bu mantık `service.py` içinde tek bir
`_poll_loop` fonksiyonuna gömülüydü; artık iki farklı kaynaktan (polling + WebSocket)
çağrılabilmesi için sınıfa çıkarılıyor.

- [ ] **Step 1: Başarısız testi yaz**

`tests\test_dispatcher.py`:
```python
from ai_notifier.core.dispatcher import NotificationDispatcher
from ai_notifier.sensors.base import SensorState


class FakeNotifier:
    def __init__(self):
        self.calls = []

    def send(self, title, message):
        self.calls.append((title, message))


def test_submit_sends_notification_after_stability_threshold():
    notifier = FakeNotifier()
    dispatcher = NotificationDispatcher(notifier=notifier, stability_threshold=2)

    dispatcher.submit("Claude Desktop", SensorState.DONE)
    assert notifier.calls == []

    dispatcher.submit("Claude Desktop", SensorState.DONE)
    assert notifier.calls == [("Claude Desktop", "YZ işlemini tamamladı.")]


def test_submit_does_not_resend_unchanged_confirmed_state():
    notifier = FakeNotifier()
    dispatcher = NotificationDispatcher(notifier=notifier, stability_threshold=2)

    dispatcher.submit("Claude Desktop", SensorState.DONE)
    dispatcher.submit("Claude Desktop", SensorState.DONE)
    dispatcher.submit("Claude Desktop", SensorState.DONE)

    assert notifier.calls == [("Claude Desktop", "YZ işlemini tamamladı.")]


def test_submit_tracks_sources_independently():
    notifier = FakeNotifier()
    dispatcher = NotificationDispatcher(notifier=notifier, stability_threshold=2)

    dispatcher.submit("Claude Desktop", SensorState.DONE)
    dispatcher.submit("Claude Desktop", SensorState.DONE)
    dispatcher.submit("Claude (Web)", SensorState.GENERATING)

    assert notifier.calls == [("Claude Desktop", "YZ işlemini tamamladı.")]


def test_submit_ignores_generating_state():
    notifier = FakeNotifier()
    dispatcher = NotificationDispatcher(notifier=notifier, stability_threshold=2)

    dispatcher.submit("Claude Desktop", SensorState.GENERATING)
    dispatcher.submit("Claude Desktop", SensorState.GENERATING)

    assert notifier.calls == []
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dispatcher.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.core.dispatcher'`

- [ ] **Step 3: `dispatcher.py` dosyasını yaz**

```python
from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.core.messages import state_to_notification
from ai_notifier.notifications.base import NotificationSender
from ai_notifier.sensors.base import SensorState


class NotificationDispatcher:
    """Herhangi bir kaynaktan (masaüstü polling, tarayıcı WebSocket) gelen ham
    durumları DecisionEngine üzerinden geçirip onaylanan değişiklikleri bildirime
    çevirir. Tüm sensör kaynakları bu tek noktayı paylaşır."""

    def __init__(self, notifier: NotificationSender, stability_threshold: int = 2):
        self._engine = DecisionEngine(stability_threshold=stability_threshold)
        self._notifier = notifier

    def submit(self, source_name: str, raw_state: SensorState) -> None:
        confirmed = self._engine.submit_reading(source_name, raw_state)
        if confirmed is None:
            return
        notification = state_to_notification(source_name, confirmed)
        if notification is None:
            return
        title, message = notification
        self._notifier.send(title, message)
```

- [ ] **Step 4: Testin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_dispatcher.py -v
```

Expected: 4 test PASS.

- [ ] **Step 5: `service.py`'ı `NotificationDispatcher` kullanacak şekilde güncelle**

`src\ai_notifier\core\service.py` (tam içerik, mevcut dosyanın yerine):
```python
import asyncio

from ai_notifier.core.dispatcher import NotificationDispatcher
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor

SENSORS = [ClaudeDesktopSensor(), ChatGPTDesktopSensor()]
POLL_INTERVAL_SECONDS = 2


async def _poll_sensors(dispatcher: NotificationDispatcher) -> None:
    while True:
        for sensor in SENSORS:
            dispatcher.submit(sensor.name, sensor.read_state())
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _run() -> None:
    dispatcher = NotificationDispatcher(notifier=WindowsToastNotifier())
    await _poll_sensors(dispatcher)


def run() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
```

- [ ] **Step 6: Tüm test paketini çalıştırıp hiçbir şeyin bozulmadığını doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: Tüm testler (mevcut 16 + yeni 4 = 20) PASS.

- [ ] **Step 7: Commit**

```bash
git add src/ai_notifier/core/dispatcher.py src/ai_notifier/core/service.py tests/test_dispatcher.py
git commit -m "refactor: extract NotificationDispatcher so web bridge can share it with polling"
```

---

### Task 2: `web_bridge.py` — Saf Fonksiyonlar (Token, Mesaj Ayrıştırma) (TDD)

**Files:**
- Create: `src\ai_notifier\core\web_bridge.py`
- Test: `tests\test_web_bridge.py`

**Interfaces:**
- Produces:
  - `generate_token() -> str`
  - `parse_client_message(raw: str) -> tuple[str, str] | None` (site, state) veya None
  - `is_valid_token_message(raw: str, expected_token: str) -> bool`
  - `VALID_STATES: set[str]` = `{"generating", "done", "waiting_approval", "error"}`

- [ ] **Step 1: Başarısız testleri yaz**

`tests\test_web_bridge.py`:
```python
import json

from ai_notifier.core.web_bridge import (
    generate_token,
    is_valid_token_message,
    parse_client_message,
)


def test_generate_token_returns_nonempty_unique_strings():
    token1 = generate_token()
    token2 = generate_token()
    assert token1 != token2
    assert len(token1) > 20


def test_parse_client_message_accepts_valid_payload():
    raw = json.dumps({"site": "Claude (Web)", "state": "generating"})
    assert parse_client_message(raw) == ("Claude (Web)", "generating")


def test_parse_client_message_rejects_invalid_state():
    raw = json.dumps({"site": "Claude (Web)", "state": "not_a_real_state"})
    assert parse_client_message(raw) is None


def test_parse_client_message_rejects_malformed_json():
    assert parse_client_message("{not json") is None


def test_parse_client_message_rejects_missing_fields():
    assert parse_client_message(json.dumps({"site": "Claude (Web)"})) is None


def test_is_valid_token_message_accepts_matching_token():
    raw = json.dumps({"token": "abc123"})
    assert is_valid_token_message(raw, "abc123") is True


def test_is_valid_token_message_rejects_wrong_token():
    raw = json.dumps({"token": "wrong"})
    assert is_valid_token_message(raw, "abc123") is False


def test_is_valid_token_message_rejects_malformed_json():
    assert is_valid_token_message("{not json", "abc123") is False
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_bridge.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'ai_notifier.core.web_bridge'`

- [ ] **Step 3: `web_bridge.py`'ın saf fonksiyonlarını yaz**

```python
import json
import secrets

VALID_STATES = {"generating", "done", "waiting_approval", "error"}


def generate_token() -> str:
    return secrets.token_urlsafe(32)


def parse_client_message(raw: str) -> tuple[str, str] | None:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    site = data.get("site")
    state = data.get("state")
    if not isinstance(site, str) or state not in VALID_STATES:
        return None
    return site, state


def is_valid_token_message(raw: str, expected_token: str) -> bool:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return False
    return data.get("token") == expected_token
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_bridge.py -v
```

Expected: 8 test PASS.

- [ ] **Step 5: Commit**

```bash
git add src/ai_notifier/core/web_bridge.py tests/test_web_bridge.py
git commit -m "feat: add web_bridge token generation and message parsing"
```

---

### Task 3: `WebBridgeServer` — WebSocket Sunucusu

**Files:**
- Modify: `src\ai_notifier\core\web_bridge.py`
- Modify: `tests\test_web_bridge.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `generate_token`, `parse_client_message`, `is_valid_token_message` (Task 2'den,
  aynı dosyada)
- Produces:
  - `WebBridgeServer(on_state: Callable[[str, str], None], token: str | None = None, host: str = "127.0.0.1", port: int = 8765)`
    - `.token` (property, üretilen/verilen token)
    - `async def start(self) -> None`
    - `async def stop(self) -> None`
  - `EXTENSION_ORIGIN` sabiti (Task 6'da güncellenecek yer tutucu)

- [ ] **Step 1: `websockets` bağımlılığını ekle**

`pyproject.toml`'daki `dependencies` listesine ekle:
```toml
dependencies = [
    "pywinauto>=0.6.9",
    "pywin32>=306",
    "websockets==12.0",
]
```

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

- [ ] **Step 2: Gerçek bir WebSocket istemcisiyle test edilebilecek entegrasyon testini yaz**

`tests\test_web_bridge.py` dosyasının SONUNA ekle:
```python
import asyncio

import websockets

from ai_notifier.core.web_bridge import WebBridgeServer


def test_server_rejects_connection_with_wrong_token():
    async def scenario():
        received = []
        server = WebBridgeServer(
            on_state=lambda site, state: received.append((site, state)),
            token="expected-token",
            port=8766,
        )
        await server.start()
        try:
            async with websockets.connect("ws://127.0.0.1:8766") as ws:
                await ws.send(json.dumps({"token": "wrong-token"}))
                with pytest.raises(websockets.ConnectionClosed):
                    await ws.recv()
        finally:
            await server.stop()
        assert received == []

    asyncio.run(scenario())


def test_server_forwards_valid_messages_after_correct_token():
    async def scenario():
        received = []
        server = WebBridgeServer(
            on_state=lambda site, state: received.append((site, state)),
            token="expected-token",
            port=8767,
        )
        await server.start()
        try:
            async with websockets.connect("ws://127.0.0.1:8767") as ws:
                await ws.send(json.dumps({"token": "expected-token"}))
                await ws.send(json.dumps({"site": "Claude (Web)", "state": "generating"}))
                await asyncio.sleep(0.1)
        finally:
            await server.stop()
        assert received == [("Claude (Web)", "generating")]

    asyncio.run(scenario())


def test_token_http_endpoint_returns_token_with_cors_header():
    async def scenario():
        server = WebBridgeServer(on_state=lambda site, state: None, token="expected-token", port=8768)
        await server.start()
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", 8768)
            writer.write(b"GET /token HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            await writer.drain()
            response = await reader.read(2048)
        finally:
            await server.stop()
        assert b"200" in response
        assert b"Access-Control-Allow-Origin" in response
        assert b"expected-token" in response

    asyncio.run(scenario())
```

Dosyanın başına `import pytest` satırını ekle (henüz yoksa).

- [ ] **Step 3: Testlerin başarısız olduğunu doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_bridge.py -v
```

Expected: FAIL — `ImportError: cannot import name 'WebBridgeServer'`

- [ ] **Step 4: `WebBridgeServer` sınıfını yaz**

`web_bridge.py`'ın SONUNA ekle:
```python
from http import HTTPStatus

import websockets

HOST = "127.0.0.1"
PORT = 8765

# Task 6'da, eklenti Chrome'a yüklendikten sonra gerçek eklenti ID'siyle
# güncellenecek. Bkz. Task 6 Step 1.
EXTENSION_ORIGIN = "chrome-extension://REPLACE_WITH_YOUR_EXTENSION_ID"


class WebBridgeServer:
    def __init__(self, on_state, token: str | None = None, host: str = HOST, port: int = PORT):
        self._on_state = on_state
        self.token = token or generate_token()
        self._host = host
        self._port = port
        self._server = None

    async def _process_request(self, path, request_headers):
        if path != "/token":
            return None
        body = json.dumps({"token": self.token}).encode()
        headers = [
            ("Content-Type", "application/json"),
            ("Access-Control-Allow-Origin", EXTENSION_ORIGIN),
            ("Content-Length", str(len(body))),
        ]
        return HTTPStatus.OK, headers, body

    async def _handler(self, websocket):
        try:
            first_message = await websocket.recv()
        except websockets.ConnectionClosed:
            return

        if not is_valid_token_message(first_message, self.token):
            await websocket.close()
            return

        async for raw in websocket:
            parsed = parse_client_message(raw)
            if parsed is None:
                continue
            site, state = parsed
            self._on_state(site, state)

    async def start(self) -> None:
        self._server = await websockets.serve(
            self._handler, self._host, self._port, process_request=self._process_request
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
```

- [ ] **Step 5: Testlerin geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/test_web_bridge.py -v
```

Expected: 11 test PASS (8 saf fonksiyon + 3 entegrasyon).

- [ ] **Step 6: Commit**

```bash
git add src/ai_notifier/core/web_bridge.py tests/test_web_bridge.py pyproject.toml
git commit -m "feat: add WebBridgeServer (token-gated WebSocket + HTTP token endpoint)"
```

---

### Task 4: `service.py`'a Web Bridge'i Bağlama

**Files:**
- Modify: `src\ai_notifier\core\service.py`

**Interfaces:**
- Consumes: `WebBridgeServer` (Task 3), `NotificationDispatcher` (Task 1)

- [ ] **Step 1: `service.py`'ı güncelle (tam içerik)**

```python
import asyncio

from ai_notifier.core.dispatcher import NotificationDispatcher
from ai_notifier.core.web_bridge import WebBridgeServer
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
from ai_notifier.sensors.base import SensorState
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor

SENSORS = [ClaudeDesktopSensor(), ChatGPTDesktopSensor()]
POLL_INTERVAL_SECONDS = 2


async def _poll_sensors(dispatcher: NotificationDispatcher) -> None:
    while True:
        for sensor in SENSORS:
            dispatcher.submit(sensor.name, sensor.read_state())
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _run() -> None:
    dispatcher = NotificationDispatcher(notifier=WindowsToastNotifier())

    def on_web_state(site: str, state_str: str) -> None:
        dispatcher.submit(site, SensorState(state_str))

    bridge = WebBridgeServer(on_state=on_web_state)
    await bridge.start()
    print(f"Web bridge token (eklenti kurulumu için gerekmiyor, sadece bilgi): {bridge.token}")
    try:
        await _poll_sensors(dispatcher)
    finally:
        await bridge.stop()


def run() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: Tüm test paketinin hâlâ geçtiğini doğrula**

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

Expected: Tüm testler PASS (20 test).

- [ ] **Step 3: Servisi başlatıp web bridge'in ayakta olduğunu manuel doğrula**

```powershell
.venv\Scripts\python.exe -m ai_notifier.core.service
```

Ayrı bir terminalde:
```powershell
curl http://127.0.0.1:8765/token
```

Expected: `{"token": "..."}` içeren bir JSON yanıt.

- [ ] **Step 4: Commit**

```bash
git add src/ai_notifier/core/service.py
git commit -m "feat: run WebBridgeServer alongside sensor polling in the service"
```

---

### Task 5: Tarayıcı Eklentisi — `manifest.json` + `content_script.js`

**Files:**
- Create: `extension\manifest.json`
- Create: `extension\content_script.js`

**Interfaces:**
- Produces: `chrome.runtime.sendMessage({type: "state", site, state})` çağrıları
  (Task 6'daki background.js tarafından dinlenecek)

- [ ] **Step 1: `manifest.json` dosyasını yaz**

```json
{
  "manifest_version": 3,
  "name": "AI-Notifier Web Sensörü",
  "version": "0.1.0",
  "description": "claude.ai ve chatgpt.com sekmelerini izler, durum değişikliklerini yerel AI-Notifier servisine iletir.",
  "permissions": ["scripting"],
  "host_permissions": [
    "https://claude.ai/*",
    "https://chatgpt.com/*",
    "http://127.0.0.1:8765/*"
  ],
  "background": {
    "service_worker": "background.js"
  },
  "content_scripts": [
    {
      "matches": ["https://claude.ai/*", "https://chatgpt.com/*"],
      "js": ["content_script.js"],
      "run_at": "document_idle"
    }
  ]
}
```

- [ ] **Step 2: `content_script.js` dosyasını yaz**

```javascript
// Faz 0'da (docs/superpowers/specs/2026-09-17-browser-extension-design.md bölüm 2)
// sadece claude.ai gerçek DOM'a karşı doğrulandı. chatgpt.com selektörü TAHMİNİDİR.
const SITE_CONFIGS = {
  "claude.ai": {
    siteName: "Claude (Web)",
    isGenerating: () =>
      document.querySelector('[data-testid="chat-input-stop"]') !== null,
  },
  "chatgpt.com": {
    siteName: "ChatGPT (Web)",
    isGenerating: () =>
      Array.from(document.querySelectorAll("button")).some((button) =>
        (button.getAttribute("aria-label") || "")
          .toLowerCase()
          .includes("stop generating")
      ),
  },
};

function currentSiteConfig() {
  const host = location.hostname.replace(/^www\./, "");
  return SITE_CONFIGS[host] || null;
}

let lastReportedState = null;

function computeState(config) {
  return config.isGenerating() ? "generating" : "done";
}

function reportState(siteName, state) {
  if (state === lastReportedState) {
    return;
  }
  lastReportedState = state;
  chrome.runtime.sendMessage({ type: "state", site: siteName, state: state });
}

function startObserving() {
  const config = currentSiteConfig();
  if (!config) {
    return;
  }

  const observer = new MutationObserver(() => {
    reportState(config.siteName, computeState(config));
  });
  observer.observe(document.body, { childList: true, subtree: true });

  reportState(config.siteName, computeState(config));
}

startObserving();
```

- [ ] **Step 3: Eklentiyi Chrome'a yükle**

`chrome://extensions` → "Geliştirici modu" aç → "Paketlenmemiş öğe yükle" →
`D:\ai-notifier\extension` klasörünü seç.

- [ ] **Step 4: claude.ai'da manuel senaryo testi yap**

claude.ai'a git, DevTools > Console'u aç, bir mesaj gönder. Konsola herhangi bir hata
düşmediğini doğrula (background.js henüz yok, `chrome.runtime.sendMessage` çağrısı
kendi başına hataya sebep OLMAZ — alıcı olmasa da mesaj sessizce kaybolur).

- [ ] **Step 5: Commit**

```bash
git add extension/manifest.json extension/content_script.js
git commit -m "feat: add browser extension manifest and content script"
```

---

### Task 6: Tarayıcı Eklentisi — `background.js` (Token + WebSocket)

**Files:**
- Create: `extension\background.js`
- Modify: `src\ai_notifier\core\web_bridge.py`

**Interfaces:**
- Consumes: `content_script.js`'in gönderdiği `{type: "state", site, state}` mesajları
  (Task 5), `web_bridge.py`'daki `/token` endpoint'i ve WebSocket sunucusu (Task 3)

- [ ] **Step 1: Gerçek eklenti ID'sini al ve `EXTENSION_ORIGIN`'i güncelle**

`chrome://extensions` sayfasında "AI-Notifier Web Sensörü" kartının altındaki ID'yi
kopyala (32 karakterlik harf dizisi). `src\ai_notifier\core\web_bridge.py` içindeki:

```python
EXTENSION_ORIGIN = "chrome-extension://REPLACE_WITH_YOUR_EXTENSION_ID"
```

satırını gerçek ID ile güncelle, örn:
```python
EXTENSION_ORIGIN = "chrome-extension://abcdefghijklmnopqrstuvwxyzabcdef"
```

- [ ] **Step 2: `background.js` dosyasını yaz**

```javascript
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
  } catch (err) {
    scheduleReconnect();
    return;
  }

  socket = new WebSocket(WS_URL);

  socket.addEventListener("open", () => {
    socket.send(JSON.stringify({ token: token }));
    backoffMs = 1000;
  });

  socket.addEventListener("close", scheduleReconnect);
  socket.addEventListener("error", () => {
    socket.close();
  });
}

function scheduleReconnect() {
  setTimeout(connect, backoffMs);
  backoffMs = Math.min(backoffMs * 2, MAX_BACKOFF_MS);
}

chrome.runtime.onMessage.addListener((message) => {
  if (
    message.type === "state" &&
    socket &&
    socket.readyState === WebSocket.OPEN
  ) {
    socket.send(JSON.stringify({ site: message.site, state: message.state }));
  }
});

connect();
```

- [ ] **Step 3: Eklentiyi yeniden yükle (manifest'e background eklendi)**

`chrome://extensions` → "AI-Notifier Web Sensörü" kartında yenile ikonuna bas.

- [ ] **Step 4: Uçtan uca manuel senaryo testi**

```powershell
cd D:\ai-notifier
.venv\Scripts\python.exe -m ai_notifier.core.service
```

claude.ai'a git, bir mesaj gönder. `chrome://extensions` → eklenti kartı → "service
worker" linkine tıkla, açılan DevTools konsolunda WebSocket bağlantısında hata olmadığını
doğrula. Yanıt tamamlandığında masaüstü servisinin (Task 4'te doğrulanan) bildirim akışının
tetiklendiğini gözlemle (Faz 1'in bilinen kısıtı: ekranda görünür bildirim paketleme
sonrasına kalıyor, bu adımda amaç sadece WebSocket mesajının servise ulaştığını
doğrulamak).

- [ ] **Step 5: Commit**

```bash
git add extension/background.js src/ai_notifier/core/web_bridge.py
git commit -m "feat: add background script with token auth and reconnect logic"
```

---

## Self-Review Notları

- **Spec kapsaması:** DOM tespiti (Task 5), token güvenliği (Task 2/3/6), WebSocket veri
  akışı (Task 3/4), mevcut DecisionEngine'in yeniden kullanımı (Task 1) — spec'in 2-4.
  bölümleri kapsandı. Hata yönetimi (spec 3.4): background.js'in reconnect/backoff mantığı
  Task 6'da var; content script'in "hedef konteyner henüz yok" senaryosu MVP'de
  `document.body`'yi doğrudan izlediği için ayrıca ele alınmadı (spec'teki "geçici
  gözlemci" detayı, gerçek kullanımda ihtiyaç çıkarsa eklenecek küçük bir iyileştirme).
- **Placeholder taraması:** `EXTENSION_ORIGIN` yer tutucusu açıkça işaretli ve Task 6
  Step 1'de nasıl doldurulacağı net (gerçek bir değer, sadece kurulum zamanı bilinebilir).
- **Tip tutarlılığı:** `NotificationDispatcher.submit(source_name: str, raw_state: SensorState)`
  imzası Task 1/4'te; `WebBridgeServer.on_state` callback'i `(site: str, state: str)` alır
  (SensorState DEĞİL — ham string, `service.py` içinde `SensorState(state_str)`'e çevrilir)
  Task 3/4'te tutarlı kullanıldı.
