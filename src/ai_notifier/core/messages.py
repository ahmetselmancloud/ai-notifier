from ai_notifier.sensors.base import SensorState

_MESSAGES: dict[SensorState, str] = {
    SensorState.DONE: "YZ işlemini tamamladı.",
    SensorState.WAITING_APPROVAL: "YZ onay veya seçim bekliyor!",
    SensorState.ERROR: "Bağlantı hatası oluştu, müdahale gerekli.",
}


def state_to_notification(
    sensor_name: str, state: SensorState
) -> tuple[str, str] | None:
    message = _MESSAGES.get(state)
    if message is None:
        return None
    return sensor_name, message
