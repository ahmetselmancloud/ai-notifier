import asyncio

from ai_notifier.core.dispatcher import NotificationDispatcher
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
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
    await _poll_sensors(dispatcher)


def run() -> None:
    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
