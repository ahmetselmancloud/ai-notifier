import logging

from pywinauto import Application

from ai_notifier.sensors.base import BaseSensor, SensorState

logger = logging.getLogger(__name__)

# Faz 0 (docs/superpowers/plans/2026-09-16-faz0-findings.md) bulgularına göre
# belirlenen sabitler.
WINDOW_TITLE = "Claude"
STOP_BUTTON_NAME = "Stop"
APPROVAL_BUTTON_NAMES = ("Devam Et", "Allow", "İzin Ver")
ERROR_TEXT_MARKERS = ("Network Error", "Regenerate")


class ClaudeDesktopSensor(BaseSensor):
    name = "Claude Desktop"

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
            logger.debug("Claude Desktop penceresi okunamadı", exc_info=True)
            return SensorState.UNKNOWN

        if any(marker in " ".join(button_names) for marker in ERROR_TEXT_MARKERS):
            return SensorState.ERROR
        if any(name in APPROVAL_BUTTON_NAMES for name in button_names):
            return SensorState.WAITING_APPROVAL
        if STOP_BUTTON_NAME in button_names:
            return SensorState.GENERATING
        return SensorState.DONE
