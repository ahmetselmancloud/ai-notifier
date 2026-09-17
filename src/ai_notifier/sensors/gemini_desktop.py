import logging

from pywinauto import Application

from ai_notifier.sensors.base import BaseSensor, SensorState

logger = logging.getLogger(__name__)

# 2026-09-18'de gerçek Gemini masaüstü uygulamasına (Chrome PWA olarak kurulu) karşı
# doğrulandı: uzun bir mesaj gönderilip pywinauto ile buton listesi izlendi, "İptal"
# butonu üretim sırasında belirip bitince kayboldu. Onay/hata sinyalleri bu turda
# gözlemlenmedi (Gemini'de Claude Desktop'taki gibi bir araç izni istemi yok);
# WAITING_APPROVAL/ERROR şimdilik desteklenmiyor.
WINDOW_TITLE = "Gemini"
STOP_BUTTON_NAME = "İptal"


class GeminiDesktopSensor(BaseSensor):
    name = "Gemini Desktop"

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
            logger.debug("Gemini Desktop penceresi okunamadı", exc_info=True)
            return SensorState.UNKNOWN

        if STOP_BUTTON_NAME in button_names:
            return SensorState.GENERATING
        return SensorState.DONE
