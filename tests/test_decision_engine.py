from ai_notifier.core.decision_engine import DecisionEngine
from ai_notifier.sensors.base import SensorState


def test_confirms_after_stability_threshold_consecutive_reads():
    engine = DecisionEngine(stability_threshold=2)

    assert engine.submit_reading("claude", SensorState.GENERATING) is None
    assert engine.submit_reading("claude", SensorState.GENERATING) is SensorState.GENERATING


def test_does_not_reconfirm_already_confirmed_state():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("claude", SensorState.GENERATING) is None


def test_single_flaky_read_does_not_confirm():
    engine = DecisionEngine(stability_threshold=2)

    assert engine.submit_reading("claude", SensorState.DONE) is None


def test_unknown_reading_resets_pending_streak_and_never_confirms():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.DONE)

    assert engine.submit_reading("claude", SensorState.UNKNOWN) is None
    # DONE'un tek okuması UNKNOWN tarafından sıfırlandı, bu yüzden DONE'un
    # tekrar 2 kez art arda okunması gerekir.
    assert engine.submit_reading("claude", SensorState.DONE) is None
    assert engine.submit_reading("claude", SensorState.DONE) is SensorState.DONE


def test_sensors_are_tracked_independently():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("chatgpt", SensorState.GENERATING) is None


def test_changing_confirmed_state_requires_new_stability_streak():
    engine = DecisionEngine(stability_threshold=2)
    engine.submit_reading("claude", SensorState.GENERATING)
    engine.submit_reading("claude", SensorState.GENERATING)

    assert engine.submit_reading("claude", SensorState.DONE) is None
    assert engine.submit_reading("claude", SensorState.DONE) is SensorState.DONE
