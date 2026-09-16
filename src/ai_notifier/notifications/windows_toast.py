import time

import win32api
import win32con
import win32gui

from ai_notifier.notifications.base import NotificationSender

# Modern WinRT Toast API, AUMID'in Windows Ayarlar > Bildirimler'de kayıtlı
# olmasını gerektiriyor; bu, gerçek bir kurulum paketi (Faz 3, PyInstaller)
# olmadan güvenilir şekilde sağlanamadığı Task 5 manuel doğrulamasında
# görüldü (notifier.setting == DisabledForUser, kısayol+registry ile de
# değişmedi). Bu yüzden MVP, herhangi bir kayıt gerektirmeyen klasik sistem
# tepsisi balon bildirimini (Shell_NotifyIcon) kullanır.

_WINDOW_CLASS_NAME = "AINotifierBalloonWindow"


def _on_destroy(hwnd, msg, wparam, lparam) -> int:
    win32gui.PostQuitMessage(0)
    return 0


def _ensure_window_class_registered(hinst) -> None:
    wc = win32gui.WNDCLASS()
    wc.hInstance = hinst
    wc.lpszClassName = _WINDOW_CLASS_NAME
    wc.lpfnWndProc = {win32con.WM_DESTROY: _on_destroy}
    try:
        win32gui.RegisterClass(wc)
    except win32gui.error:
        pass  # sınıf zaten kayıtlı


def _show_balloon(title: str, message: str) -> None:
    hinst = win32api.GetModuleHandle(None)
    _ensure_window_class_registered(hinst)

    hwnd = win32gui.CreateWindow(
        _WINDOW_CLASS_NAME, "AI-Notifier", 0, 0, 0, 0, 0, 0, 0, hinst, None
    )

    hicon = win32gui.LoadIcon(0, win32con.IDI_APPLICATION)

    add_flags = win32gui.NIF_ICON | win32gui.NIF_MESSAGE | win32gui.NIF_TIP
    win32gui.Shell_NotifyIcon(
        win32gui.NIM_ADD, (hwnd, 0, add_flags, win32con.WM_USER + 20, hicon, "AI-Notifier")
    )

    info_flags = win32gui.NIF_INFO
    win32gui.Shell_NotifyIcon(
        win32gui.NIM_MODIFY,
        (hwnd, 0, info_flags, win32con.WM_USER + 20, hicon, "AI-Notifier", message, 10000, title),
    )

    # Balonun Windows tarafından işlenip gösterilebilmesi için mesaj
    # döngüsüne kısa, sınırlı bir süre ver; sonra tepsi ikonunu temizle.
    for _ in range(15):
        win32gui.PumpWaitingMessages()
        time.sleep(0.1)

    win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, (hwnd, 0))
    win32gui.DestroyWindow(hwnd)


class WindowsToastNotifier(NotificationSender):
    def __init__(self, show_fn=None):
        self._show_fn = show_fn if show_fn is not None else _show_balloon

    def send(self, title: str, message: str) -> None:
        self._show_fn(title, message)
