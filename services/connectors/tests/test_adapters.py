from twinpilot_connectors import get_adapter, list_adapters
from twinpilot_connectors.base import WriteRequest


def test_registry_lists_all_adapters():
    names = list_adapters()
    assert "mock" in names
    assert "bacnet_ip" in names
    assert "modbus_tcp" in names
    assert "honeywell_niagara" in names


def test_mock_discover_and_write_ack():
    adapter = get_adapter("mock", {})
    points = adapter.discover_points()
    assert len(points) >= 10
    writable = next(p for p in points if p["writable"])
    result = adapter.write(
        WriteRequest(external_point_id=writable["external_point_id"], value=25.0, deadband=0.1)
    )
    assert result.success
    assert result.acked
    assert result.readback_value == 25.0


def test_bacnet_and_modbus_poll():
    bacnet = get_adapter("bacnet_ip", {"device_id": 42})
    modbus = get_adapter("modbus_tcp", {"unit_id": 2})
    assert bacnet.health()["provider"] == "bacnet_ip"
    assert modbus.health()["provider"] == "modbus_tcp"
    assert len(bacnet.poll_telemetry()) >= 1
    assert len(modbus.poll_telemetry()) >= 1


def test_honeywell_certified_flag():
    hw = get_adapter("honeywell_niagara", {"station": "Demo"})
    health = hw.health()
    assert health["certified_adapter"] is True
    assert health["vendor"] == "honeywell"
