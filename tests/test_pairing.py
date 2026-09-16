from ai_notifier.core.pairing import (
    check_pairing_status,
    generate_pairing_code,
    get_or_create_desktop_instance_id,
    request_pairing_code,
)


def test_generate_pairing_code_has_expected_length_and_charset():
    code = generate_pairing_code()
    assert len(code) == 6
    assert code.isalnum()
    assert code == code.upper()


def test_generate_pairing_code_is_random():
    codes = {generate_pairing_code() for _ in range(20)}
    assert len(codes) > 1


def test_get_or_create_desktop_instance_id_creates_and_persists(tmp_path):
    config_path = tmp_path / "config.json"

    first = get_or_create_desktop_instance_id(config_path)
    second = get_or_create_desktop_instance_id(config_path)

    assert first == second
    assert config_path.exists()


def test_request_pairing_code_posts_pending_row_and_returns_code():
    captured = {}

    def fake_post(url, headers, json, timeout):
        captured["url"] = url
        captured["json"] = json

        class FakeResponse:
            def raise_for_status(self):
                pass

        return FakeResponse()

    code = request_pairing_code("instance-123", http_post=fake_post)

    assert len(code) == 6
    assert captured["json"]["desktop_instance_id"] == "instance-123"
    assert captured["json"]["status"] == "pending"
    assert captured["json"]["code"] == code
    assert "pairing_codes" in captured["url"]


def test_check_pairing_status_returns_none_when_pending():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"status": "pending", "claimed_by_user_id": None}]

        return FakeResponse()

    assert check_pairing_status("A3F9K2", http_get=fake_get) is None


def test_check_pairing_status_returns_user_id_when_claimed():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return [{"status": "claimed", "claimed_by_user_id": "user-abc"}]

        return FakeResponse()

    assert check_pairing_status("A3F9K2", http_get=fake_get) == "user-abc"


def test_check_pairing_status_returns_none_when_code_not_found():
    def fake_get(url, headers, params, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return []

        return FakeResponse()

    assert check_pairing_status("UNKNOWN", http_get=fake_get) is None
