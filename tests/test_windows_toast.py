from ai_notifier.notifications.windows_toast import WindowsToastNotifier


def test_send_calls_show_fn_with_title_and_message():
    calls = []

    def fake_show_fn(title, message):
        calls.append((title, message))

    notifier = WindowsToastNotifier(show_fn=fake_show_fn)

    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert calls == [("Claude Desktop", "YZ işlemini tamamladı.")]
