from abc import ABC, abstractmethod
from enum import Enum


class SensorState(Enum):
    GENERATING = "generating"
    DONE = "done"
    WAITING_APPROVAL = "waiting_approval"
    ERROR = "error"
    UNKNOWN = "unknown"


class BaseSensor(ABC):
    """Tek bir YZ masaüstü uygulamasını izleyen sensör adaptörlerinin ortak arayüzü.

    Faz 0 doğrulamasında `uiautomation`/`pywinauto` kütüphanelerinin gerçek bir UI
    Automation olay aboneliği (event subscription) sunmadığı görüldü (bkz.
    docs/superpowers/plans/2026-09-16-faz0-findings.md). Bu yüzden MVP, event-driven
    yerine hedefe kilitli POLLING kullanır: core servis her sensörün read_state()
    metodunu sabit aralıklarla çağırır. Kararlılık/debounce mantığı burada DEĞİL,
    DecisionEngine'de uygulanır.
    """

    name: str

    @abstractmethod
    def read_state(self) -> SensorState:
        """Hedef pencerede tek, hedefe kilitli bir okuma yapar (tüm ağacı taramaz)
        ve ham (henüz debounce edilmemiş) durumu döner. Pencere bulunamıyorsa
        SensorState.UNKNOWN döner."""
        raise NotImplementedError
