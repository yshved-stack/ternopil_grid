from __future__ import annotations

from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ATTRIBUTION


def _local_date_from_ts(ts: float):
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).date()


def _hhmm(ts: float):
    return dt_util.as_local(dt_util.utc_from_timestamp(ts)).strftime("%H:%M")


class _BaseSensor(SensorEntity):
    def __init__(self, entry, coordinator, name, icon, suggested_object_id: str):
        self.entry = entry
        self.coordinator = coordinator
        self._attr_name = name
        self._attr_icon = icon
        self._attr_attribution = ATTRIBUTION
        self._attr_unique_id = f"{entry.entry_id}_{suggested_object_id}"
        self._attr_suggested_object_id = suggested_object_id

    @property
    def available(self):
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, self.entry.entry_id)},
            name="Ternopil Grid Schedule",
            manufacturer="Community",
            model="Outage schedule",
        )

    async def async_added_to_hass(self):
        self.async_on_remove(self.coordinator.async_add_listener(self.async_write_ha_state))


class TernopilNextChange(_BaseSensor):
    _attr_device_class = "timestamp"

    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, "Next change", "mdi:clock-outline", "ternopil_grid_next_change")

    @property
    def native_value(self):
        now = dt_util.utcnow().timestamp()
        future = [s["start"] for s in (self.coordinator.data or []) if s["start"] > now]
        if not future:
            return None
        ts = min(future)
        return dt_util.utc_from_timestamp(ts)


class TernopilCountdown(_BaseSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, "Countdown", "mdi:timer-outline", "ternopil_grid_countdown")

    @property
    def native_value(self):
        nxt_dt = TernopilNextChange(self.entry, self.coordinator).native_value
        if not nxt_dt:
            return "--"
        diff = int(nxt_dt.timestamp() - dt_util.utcnow().timestamp())
        if diff < 0:
            return "--"
        h = diff // 3600
        m = (diff % 3600) // 60
        return f"{h}h {m}m"


class TernopilOffToday(_BaseSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, "OFF today", "mdi:calendar-today", "ternopil_grid_off_today")

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


class TernopilOffTomorrow(_BaseSensor):
    def __init__(self, entry, schedule):
        super().__init__(entry, schedule, "OFF tomorrow", "mdi:calendar", "ternopil_grid_off_tomorrow")

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
