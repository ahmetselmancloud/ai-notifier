from pathlib import Path

import requests

from ai_notifier.core.pairing import CONFIG_PATH, SUPABASE_ANON_KEY, SUPABASE_URL, load_config
from ai_notifier.notifications.base import NotificationSender

FIREBASE_SERVICE_ACCOUNT_PATH = "REPLACE_WITH_PATH_TO_YOUR_FIREBASE_SERVICE_ACCOUNT_JSON"

_firebase_app = None


def _headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def get_fcm_token_for_desktop(desktop_instance_id: str, http_post=requests.post) -> str | None:
    response = http_post(
        f"{SUPABASE_URL}/rest/v1/rpc/get_fcm_token_for_desktop",
        headers=_headers(),
        json={"p_desktop_instance_id": desktop_instance_id},
        timeout=10,
    )
    response.raise_for_status()
    token = response.json()
    return token or None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(FIREBASE_SERVICE_ACCOUNT_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def _send_fcm_message(title: str, body: str, token: str) -> None:
    from firebase_admin import messaging

    _get_firebase_app()
    message = messaging.Message(
        notification=messaging.Notification(title=title, body=body),
        token=token,
    )
    messaging.send(message)


class PushNotifier(NotificationSender):
    def __init__(
        self,
        config_path: Path = CONFIG_PATH,
        send_fn=_send_fcm_message,
        http_post=requests.post,
    ):
        self._config_path = config_path
        self._send_fn = send_fn
        self._http_post = http_post

    def send(self, title: str, message: str) -> None:
        config = load_config(self._config_path)
        desktop_instance_id = config.get("desktop_instance_id")
        if not desktop_instance_id:
            return

        token = get_fcm_token_for_desktop(desktop_instance_id, http_post=self._http_post)
        if not token:
            return

        self._send_fn(title, message, token)
