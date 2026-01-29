from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import ATTRIBUTION, DOMAIN


@dataclass(frozen=True, kw_only=True)
class TGDSensorDescription(SensorEntityDescription):
    key: str


DESC_NEXT_CHANGE = TGDSensorDescription(
    key="next_change",
    name="Next change",
    icon="mdi:clock-outline",
    device_class="timestamp",
)

DESC_COUNTDOWN = TGDSensorDescription(
    key="countdown",
    name="Countdown",
    icon="mdi:timer-outline",
)

DESC_OFF_TODAY = TGDSensorDescription(
    key="off_today",
    name="OFF today",
    icon="mdi:calendar-today",
)

DESC_OFF_TOMORROW = TGDSensorDescription(
    key="off_tomorrow",
    name="OFF tomorrow",
    icon="mdi:calendar",
)


def _local_date_from_ts(ts: float):
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).date()


def _hhmm(ts: float):
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).strftime("%H:%M")


class TernopilGridSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, entry, coordinator, description: TGDSensorDescription):
        self.entry = entry
        self.coordinator = coordinator
        self.entity_description = description

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_attribution = ATTRIBUTION

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Ternopil Grid Schedule",
            manufacturer="Community",
            model="Outage schedule",
        )

    @property
    def available(self):
        return self.coordinator.last_update_success

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class TernopilNextChange(TernopilGridSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, DESC_NEXT_CHANGE)

    @property
    def native_value(self):
        now = dt_util.utcnow().timestamp()
        future = [s["start"] for s in (self.coordinator.data or []) if s["start"] > now]
        if not future:
            return None
        return dt_util.utc_from_timestamp(min(future))


class TernopilCountdown(TernopilGridSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, DESC_COUNTDOWN)

    @property
    def native_value(self):
        nxt = TernopilNextChange(self.entry, self.coordinator).native_value
        if not nxt:
            return "--"
        diff = int(nxt.timestamp() - dt_util.utcnow().timestamp())
        if diff < 0:
            return "--"
        h = diff // 3600
        m = (diff % 3600) // 60
        return f"{h}h {m}m"


class TernopilOffToday(TernopilGridSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, DESC_OFF_TODAY)

    @property
    def native_value(self):
        return "ready"

    @property
    def extra_state_attributes(self):
        today = dt_util.as_local(dt_util.utcnow()).date()
        blocks = []
        for s in (self.coordinator.data or []):
            if s["color"] in ("red", "yellow") and _local_date_from_ts(s["start"]) == today:
                blocks.append(f"{_hhmm(s['start'])}-{_hhmm(s['end'])}")
        return {"blocks": blocks}


class TernopilOffTomorrow(TernopilGridSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, DESC_OFF_TOMORROW)

    @property
    def native_value(self):
        return "ready"

    @property
    def extra_state_attributes(self):
        tomorrow = dt_util.as_local(dt_util.utcnow()).date() + timedelta(days=1)
        blocks = []
        for s in (self.coordinator.data or []):
            if s["color"] in ("red", "yellow") and _local_date_from_ts(s["start"]) == tomorrow:
                blocks.append(f"{_hhmm(s['start'])}-{_hhmm(s['end'])}")
        return {"blocks": blocks}


async def async_setup_entry(hass, entry, async_add_entities):
    schedule = hass.data[DOMAIN][entry.entry_id]["schedule"]
    async_add_entities(
        [
            TernopilNextChange(entry, schedule),
            TernopilCountdown(entry, schedule),
            TernopilOffToday(entry, schedule),
            TernopilOffTomorrow(entry, schedule),
        ],
        True,
    )
