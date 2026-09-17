import asyncio
import threading

from ai_notifier.core.dispatcher import NotificationDispatcher
from ai_notifier.core.pairing import run_pairing_flow
from ai_notifier.core.tray import build_tray_icon
from ai_notifier.core.web_bridge import WebBridgeServer
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
from ai_notifier.sensors.base import SensorState
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor

SENSORS = [ClaudeDesktopSensor(), ChatGPTDesktopSensor()]
POLL_INTERVAL_SECONDS = 2


async def _poll_sensors(dispatcher: NotificationDispatcher) -> None:
    while True:
        for sensor in SENSORS:
            dispatcher.submit(sensor.name, sensor.read_state())
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def _run() -> None:
    dispatcher = NotificationDispatcher(notifier=WindowsToastNotifier())

    def on_web_state(site: str, state_str: str) -> None:
        dispatcher.submit(site, SensorState(state_str))

    bridge = WebBridgeServer(on_state=on_web_state)
    await bridge.start()
    try:
        await _poll_sensors(dispatcher)
    finally:
        await bridge.stop()


def _run_service_loop() -> None:
    asyncio.run(_run())


def run() -> None:
    service_thread = threading.Thread(target=_run_service_loop, daemon=True)
    service_thread.start()

    icon = build_tray_icon(on_pair=run_pairing_flow, on_quit=lambda: None)
    icon.run()


if __name__ == "__main__":
    run()
