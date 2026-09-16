import pytest

from ai_notifier.sensors.base import BaseSensor, SensorState


def test_sensor_state_has_expected_members():
    assert SensorState.GENERATING.value == "generating"
    assert SensorState.DONE.value == "done"
    assert SensorState.WAITING_APPROVAL.value == "waiting_approval"
    assert SensorState.ERROR.value == "error"
    assert SensorState.UNKNOWN.value == "unknown"


def test_base_sensor_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        BaseSensor()


def test_base_sensor_subclass_must_implement_read_state():
    class IncompleteSensor(BaseSensor):
        name = "incomplete"

    with pytest.raises(TypeError):
        IncompleteSensor()


def test_base_sensor_subclass_with_full_implementation_can_be_instantiated():
    class DummySensor(BaseSensor):
        name = "dummy"

        def read_state(self):
            return SensorState.UNKNOWN

    sensor = DummySensor()
    assert sensor.name == "dummy"
    assert sensor.read_state() is SensorState.UNKNOWN
