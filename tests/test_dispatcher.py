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
