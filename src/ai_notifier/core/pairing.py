import json
import os
import random
import string
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

SUPABASE_URL = "https://wvhlikiiqrculbpvphxk.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Ind2aGxpa2lpcXJjdWxicHZwaHhrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk1ODM4NzMsImV4cCI6MjEwNTE1OTg3M30.f2Qztv7xssStlPUAmGGCPAsHYuo-cv9aImBDpThmQs0"
PAIRING_WEB_URL = "https://ai-notifier-tau.vercel.app/pair"

CONFIG_PATH = Path(os.environ.get("APPDATA", ".")) / "ai-notifier" / "config.json"

POLL_INTERVAL_SECONDS = 2
CODE_TTL_MINUTES = 10


def _headers() -> dict:
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
    }


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        return {}
    return json.loads(config_path.read_text(encoding="utf-8"))


def save_config(config_path: Path, config: dict) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


def get_or_create_desktop_instance_id(config_path: Path) -> str:
    config = load_config(config_path)
    if "desktop_instance_id" in config:
        return config["desktop_instance_id"]
    instance_id = str(uuid.uuid4())
    config["desktop_instance_id"] = instance_id
    save_config(config_path, config)
    return instance_id


def generate_pairing_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(random.choices(alphabet, k=6))


def request_pairing_code(desktop_instance_id: str, http_post=requests.post) -> str:
    code = generate_pairing_code()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=CODE_TTL_MINUTES)).isoformat()
    response = http_post(
        f"{SUPABASE_URL}/rest/v1/pairing_codes",
        headers={**_headers(), "Prefer": "return=minimal"},
        json={
            "code": code,
            "desktop_instance_id": desktop_instance_id,
            "status": "pending",
            "expires_at": expires_at,
        },
        timeout=10,
    )
    response.raise_for_status()
    return code


def check_pairing_status(code: str, http_get=requests.get) -> str | None:
    """Kod eşleşmişse claimed_by_user_id'yi döner; henüz eşleşmemişse veya
    bulunamamışsa None döner."""
    response = http_get(
        f"{SUPABASE_URL}/rest/v1/pairing_codes",
        headers=_headers(),
        params={"code": f"eq.{code}", "select": "status,claimed_by_user_id"},
        timeout=10,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return None
    row = rows[0]
    if row["status"] == "claimed":
        return row["claimed_by_user_id"]
    return None


def run_pairing_flow(timeout_seconds: int = 600) -> str | None:
    """Eşleştirmeyi başlatır, tarayıcıyı açar, eşleşene kadar bekler. Başarılı
    olursa user_id'yi config'e yazıp döner; zaman aşımında None döner."""
    import webbrowser

    instance_id = get_or_create_desktop_instance_id(CONFIG_PATH)
    code = request_pairing_code(instance_id)
    webbrowser.open(f"{PAIRING_WEB_URL}?code={code}")

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        user_id = check_pairing_status(code)
        if user_id is not None:
            config = load_config(CONFIG_PATH)
            config["user_id"] = user_id
            save_config(CONFIG_PATH, config)
            return user_id
        time.sleep(POLL_INTERVAL_SECONDS)
    return None


if __name__ == "__main__":
    result = run_pairing_flow()
    if result:
        print(f"Eşleştirme başarılı. user_id: {result}")
    else:
        print("Eşleştirme zaman aşımına uğradı.")
