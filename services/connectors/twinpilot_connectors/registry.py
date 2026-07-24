"""Adapter registry."""

from __future__ import annotations

from typing import Any

from twinpilot_connectors.adapters.bacnet_ip import BACnetIPAdapter
from twinpilot_connectors.adapters.honeywell_niagara import HoneywellNiagaraAdapter
from twinpilot_connectors.adapters.mock import MockConnectorAdapter
from twinpilot_connectors.adapters.modbus_tcp import ModbusTCPAdapter

_REGISTRY = {
    "mock": MockConnectorAdapter,
    "bacnet_ip": BACnetIPAdapter,
    "modbus_tcp": ModbusTCPAdapter,
    "honeywell_niagara": HoneywellNiagaraAdapter,
}


def list_adapters() -> list[str]:
    return sorted(_REGISTRY.keys())


def get_adapter(adapter_type: str, config: dict[str, Any] | None = None):
    cls = _REGISTRY.get(adapter_type)
    if cls is None:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
    return cls(config or {})
