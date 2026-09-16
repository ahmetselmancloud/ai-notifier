from win11toast import notify

from ai_notifier.notifications.base import NotificationSender

# win11toast'ın varsayılan "Python" app_id'si, çıplak python.exe'de geçerli bir
# AUMID (Başlat Menüsü kısayolu) olmadığı için 0x803E0114 hatasıyla başarısız
# oluyor. Bu sabit, scripts/setup_dev_toast_shortcut.py ile oluşturulan
# geliştirme kısayoluyla eşleşir. Paketlenmiş (PyInstaller) sürümde gerçek
# kurulum kendi AUMID'ini kaydedecektir.
APP_ID = "AINotifier.Dev"


class WindowsToastNotifier(NotificationSender):
    """`win11toast.notify` (senkron, fire-and-forget) kullanılır — `win11toast.toast`
    KULLANILMAZ çünkü kullanıcı bildirimi kapatana kadar bloklar; bu, arka planda
    sürekli çalışması gereken servisimiz için uygun değildir."""

    def __init__(self, toast_fn=None, app_id: str = APP_ID):
        self._toast_fn = toast_fn if toast_fn is not None else notify
        self._app_id = app_id

    def send(self, title: str, message: str) -> None:
        self._toast_fn(title, message, app_id=self._app_id)
