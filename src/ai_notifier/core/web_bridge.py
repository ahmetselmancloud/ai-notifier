import json
import secrets
from http import HTTPStatus

import websockets

HOST = "127.0.0.1"
PORT = 8765

# Task 6'da, eklenti Chrome'a yüklendikten sonra gerçek eklenti ID'siyle
# güncellenecek. Bkz. docs/superpowers/plans/2026-09-17-browser-extension.md Task 6.
EXTENSION_ORIGIN = "chrome-extension://REPLACE_WITH_YOUR_EXTENSION_ID"

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


class WebBridgeServer:
    """Tarayıcı eklentisinin bağlandığı yerel token-korumalı WebSocket sunucusu
    ve `/token` HTTP endpoint'i. Doğrulanan her `{site, state}` mesajı için
    `on_state(site, state)` çağrılır."""

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
