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
