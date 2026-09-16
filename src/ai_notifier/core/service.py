import asyncio

from ai_notifier.core.dispatcher import NotificationDispatcher
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
        print(f"[web] {site}: {state_str}")
        dispatcher.submit(site, SensorState(state_str))

    bridge = WebBridgeServer(on_state=on_web_state)
    await bridge.start()
    print(f"Web bridge token (eklenti kurulumu için gerekmiyor, sadece bilgi): {bridge.token}")
    try:
        await _poll_sensors(dispatcher)
    finally:
        await bridge.stop()


def run() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
