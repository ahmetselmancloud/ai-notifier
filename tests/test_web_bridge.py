import asyncio
import json

import pytest
import websockets

from ai_notifier.core.web_bridge import (
    WebBridgeServer,
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
