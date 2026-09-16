import asyncio

from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.core.messages import state_to_notification
from ai_notifier.notifications.windows_toast import WindowsToastNotifier
from ai_notifier.sensors.chatgpt_desktop import ChatGPTDesktopSensor
from ai_notifier.sensors.claude_desktop import ClaudeDesktopSensor

SENSORS = [ClaudeDesktopSensor(), ChatGPTDesktopSensor()]
POLL_INTERVAL_SECONDS = 2


async def _poll_loop() -> None:
    engine = DecisionEngine(stability_threshold=2)
    notifier = WindowsToastNotifier()

    while True:
        for sensor in SENSORS:
            raw_state = sensor.read_state()
            confirmed = engine.submit_reading(sensor.name, raw_state)
            if confirmed is None:
                continue
            notification = state_to_notification(sensor.name, confirmed)
            if notification is None:
                continue
            title, message = notification
            notifier.send(title, message)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def run() -> None:
    try:
        asyncio.run(_poll_loop())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
