from ai_notifier.notifications.push import PushNotifier, get_fcm_token_for_desktop


def test_get_fcm_token_for_desktop_returns_token_when_present():
    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return "fcm-token-abc"

        return FakeResponse()

    assert get_fcm_token_for_desktop("instance-1", http_post=fake_post) == "fcm-token-abc"


def test_get_fcm_token_for_desktop_returns_none_when_null():
    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return None

        return FakeResponse()

    assert get_fcm_token_for_desktop("instance-1", http_post=fake_post) is None


def test_push_notifier_does_nothing_without_desktop_instance_id(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text("{}", encoding="utf-8")
    calls = []

    notifier = PushNotifier(
        config_path=config_path, send_fn=lambda t, m, tok: calls.append((t, m, tok))
    )
    notifier.send("title", "message")

    assert calls == []


def test_push_notifier_does_nothing_without_fcm_token(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"desktop_instance_id": "instance-1"}', encoding="utf-8")
    calls = []

    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return None

        return FakeResponse()

    notifier = PushNotifier(
        config_path=config_path,
        send_fn=lambda t, m, tok: calls.append((t, m, tok)),
        http_post=fake_post,
    )
    notifier.send("title", "message")

    assert calls == []


def test_push_notifier_sends_when_token_found(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text('{"desktop_instance_id": "instance-1"}', encoding="utf-8")
    calls = []

    def fake_post(url, headers, json, timeout):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return "fcm-token-xyz"

        return FakeResponse()

    notifier = PushNotifier(
        config_path=config_path,
        send_fn=lambda t, m, tok: calls.append((t, m, tok)),
        http_post=fake_post,
    )
    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert calls == [("Claude Desktop", "YZ işlemini tamamladı.", "fcm-token-xyz")]
