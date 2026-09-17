from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.core.messages import state_to_notification
from ai_notifier.notifications.base import NotificationSender
from ai_notifier.sensors.base import SensorState


class NotificationDispatcher:
    """Herhangi bir kaynaktan (masaüstü polling, tarayıcı WebSocket) gelen ham
    durumları DecisionEngine üzerinden geçirip onaylanan değişiklikleri TÜM
    bildirim kanallarına (Windows Toast + Push) birlikte gönderir."""

    def __init__(
        self, notifiers: list[NotificationSender], stability_threshold: int = 2
    ):
        self._engine = DecisionEngine(stability_threshold=stability_threshold)
        self._notifiers = notifiers

    def submit(self, source_name: str, raw_state: SensorState) -> None:
        confirmed = self._engine.submit_reading(source_name, raw_state)
        if confirmed is None:
            return
        notification = state_to_notification(source_name, confirmed)
        if notification is None:
            return
        title, message = notification
        for notifier in self._notifiers:
            notifier.send(title, message)
