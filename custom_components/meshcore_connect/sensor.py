from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import UnitOfElectricPotential
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_MODE, MODE_GATEWAY_COMPANION
from .entity import CompanionEntity

METRICS = {
    "sent": (None, SensorStateClass.TOTAL_INCREASING),
    "recv": (None, SensorStateClass.TOTAL_INCREASING),
    "recv_errors": (None, SensorStateClass.TOTAL_INCREASING),
    "last_rssi": ("dBm", SensorStateClass.MEASUREMENT),
    "last_snr": ("dB", SensorStateClass.MEASUREMENT),
    "noise_floor": ("dBm", SensorStateClass.MEASUREMENT),
    "tx_air_secs": ("s", SensorStateClass.TOTAL_INCREASING),
    "rx_air_secs": ("s", SensorStateClass.TOTAL_INCREASING),
}


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([Favorites(entry.runtime_data, entry)])
    if entry.data.get(CONF_MODE) == MODE_GATEWAY_COMPANION:
        async_add_entities([CompanionPublicKey(entry.runtime_data, entry)])
    else:
        async_add_entities([BatteryVoltage(entry.runtime_data, entry)])
    async_add_entities([RadioMetric(entry.runtime_data, entry, key) for key in METRICS])


class CompanionPublicKey(CompanionEntity, SensorEntity):
    _attr_translation_key = "companion_public_key"
    _attr_icon = "mdi:identifier"

    def __init__(self, hub, entry):
        super().__init__(hub, entry, "companion_public_key")

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("companion_public_key")


class RadioMetric(CompanionEntity, SensorEntity):
    _attr_icon = "mdi:radio-tower"

    def __init__(self, hub, entry, key):
        super().__init__(hub, entry, key)
        self.key = key
        self._attr_translation_key = key
        self._attr_native_unit_of_measurement, self._attr_state_class = METRICS[key]

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(self.key)

    @property
    def available(self):
        return super().available and self.native_value is not None


class BatteryVoltage(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "battery_voltage"
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_battery_voltage"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)

    @property
    def native_value(self):
        return self.coordinator.data.get("voltage")


class Favorites(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "favorites"
    _attr_icon = "mdi:star"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.unique_id}_favorites"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.unique_id)}, name=entry.title)

    @property
    def native_value(self):
        return len(self.extra_state_attributes["contacts"])

    @property
    def extra_state_attributes(self):
        return {"contacts": [c for c in self.coordinator.data.get("contacts", []) if c["favorite"]]}
