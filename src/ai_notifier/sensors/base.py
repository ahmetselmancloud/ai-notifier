from abc import ABC, abstractmethod
from enum import Enum
from typing import Callable


class SensorState(Enum):
    GENERATING = "generating"
    DONE = "done"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    UNKNOWN = "unknown"


class BaseSensor(ABC):
    """Tek bir YZ masaüstü uygulamasını izleyen sensör adaptörlerinin ortak arayüzü.

    Bir adaptör, hedef pencerede UI Automation olayına her tetiklendiğinde
    hedefe kilitli bir sorgu yapar ve ham okumayı (henüz debounce edilmemiş)
    on_state_changed callback'i ile bildirir. Kararlılık/debounce mantığı
    burada DEĞİL, DecisionEngine'de uygulanır.
    """

    name: str

    @abstractmethod
    def start(self, on_state_changed: Callable[[str, SensorState], None]) -> None:
        """İzlemeyi başlatır; UI Automation olayına her tetiklendiğinde
        on_state_changed(self.name, state) çağrılır."""
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        """UI Automation olay aboneliğini kaldırır, kaynakları temizler."""
        raise NotImplementedError
