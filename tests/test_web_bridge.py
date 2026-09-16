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
