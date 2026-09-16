from ai_notifier.notifications.windows_toast import WindowsToastNotifier


def test_send_calls_notify_fn_with_title_and_message():
    calls = []

    def fake_toast_fn(title, message, app_id=None):
        calls.append((title, message, app_id))

    notifier = WindowsToastNotifier(toast_fn=fake_toast_fn, app_id="AINotifier.Dev")

    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert calls == [("Claude Desktop", "YZ işlemini tamamladı.", "AINotifier.Dev")]
