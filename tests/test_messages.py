from ai_notifier.core.messages import state_to_notification
from ai_notifier.sensors.base import SensorState


def test_done_maps_to_completion_message():
    title, message = state_to_notification("Claude Desktop", SensorState.DONE)

    assert title == "Claude Desktop"
    assert message == "YZ işlemini tamamladı."


def test_waiting_approval_maps_to_approval_message():
    title, message = state_to_notification("ChatGPT Desktop", SensorState.WAITING_APPROVAL)

    assert title == "ChatGPT Desktop"
    assert message == "YZ onay veya seçim bekliyor!"


def test_error_maps_to_error_message():
    title, message = state_to_notification("Claude Desktop", SensorState.ERROR)

    assert title == "Claude Desktop"
    assert message == "Bağlantı hatası oluştu, müdahale gerekli."


def test_generating_and_unknown_have_no_notification():
    assert state_to_notification("Claude Desktop", SensorState.GENERATING) is None
    assert state_to_notification("Claude Desktop", SensorState.UNKNOWN) is None
