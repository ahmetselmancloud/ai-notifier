import threading

from ai_notifier.notifications.windows_toast import WindowsToastNotifier


def test_send_calls_show_fn_with_title_and_message():
    calls = []
    called = threading.Event()

    def fake_show_fn(title, message):
        calls.append((title, message))
        called.set()

    notifier = WindowsToastNotifier(show_fn=fake_show_fn)

    notifier.send("Claude Desktop", "YZ işlemini tamamladı.")

    assert called.wait(timeout=1)
    assert calls == [("Claude Desktop", "YZ işlemini tamamladı.")]
