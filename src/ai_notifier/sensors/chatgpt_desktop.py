import logging

from pywinauto import Application

from ai_notifier.sensors.base import BaseSensor, SensorState

logger = logging.getLogger(__name__)

# ChatGPT Desktop bu proje geliştirilirken test ortamında kurulu değildi;
# bu sabitler ClaudeDesktopSensor ile aynı desenden tahmin edilmiştir ve
# gerçek uygulamaya karşı DOĞRULANMAMIŞTIR. Selman'ın kendi makinesinde
# scripts/spike_uiautomation_probe.py (pywinauto sürümüyle) veya doğrudan
# bu sensörle test edip gerekirse güncellemesi gerekir.
WINDOW_TITLE = "ChatGPT"
STOP_BUTTON_NAME = "Stop generating"
APPROVAL_BUTTON_NAMES = ("Continue", "Allow", "Devam Et")
ERROR_TEXT_MARKERS = ("Network Error", "Regenerate")


class ChatGPTDesktopSensor(BaseSensor):
    name = "ChatGPT Desktop"

    def read_state(self) -> SensorState:
        try:
            app = Application(backend="uia").connect(title=WINDOW_TITLE)
            window = app.top_window()
            button_names = [
                d.window_text()
                for d in window.descendants(control_type="Button")
                if d.window_text()
            ]
        except Exception:
            logger.debug("ChatGPT Desktop penceresi okunamadı", exc_info=True)
            return SensorState.UNKNOWN

        if any(marker in " ".join(button_names) for marker in ERROR_TEXT_MARKERS):
            return SensorState.ERROR
        if any(name in APPROVAL_BUTTON_NAMES for name in button_names):
            return SensorState.WAITING_APPROVAL
        if STOP_BUTTON_NAME in button_names:
            return SensorState.GENERATING
        return SensorState.DONE
