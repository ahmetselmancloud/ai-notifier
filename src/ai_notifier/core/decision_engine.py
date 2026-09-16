from dataclasses import dataclass

from ai_notifier.sensors.base import SensorState


@dataclass
class _SensorHistory:
    pending_state: SensorState | None = None
    pending_count: int = 0
    confirmed_state: SensorState | None = None


class DecisionEngine:
    """Sensörlerden gelen ham okumaları, ardışık N aynı okuma ile
    doğrulanana kadar bildirime dönüştürmeyen kararlılık/debounce motoru."""

    def __init__(self, stability_threshold: int = 2):
        self._stability_threshold = stability_threshold
        self._histories: dict[str, _SensorHistory] = {}

    def submit_reading(
        self, sensor_name: str, state: SensorState
    ) -> SensorState | None:
        history = self._histories.setdefault(sensor_name, _SensorHistory())

        if state is SensorState.UNKNOWN:
            history.pending_state = None
            history.pending_count = 0
            return None

        if state == history.pending_state:
            history.pending_count += 1
        else:
            history.pending_state = state
            history.pending_count = 1

        if history.pending_count < self._stability_threshold:
            return None

        if state == history.confirmed_state:
            return None

        history.confirmed_state = state
        return state
