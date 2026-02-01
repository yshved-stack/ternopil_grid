"""HTTP client for toe-poweron.inneti.net (Ternopil schedule).

Discovered endpoints:
 - Streets (Hydra JSON-LD):
     /api/pw_streets?pagination=false&city.id=1032[&name=...]
 - Building group for a street (JSON):
     /api/pw-accounts/building-groups?cityId=1032&streetId=...
 - Actual graph (schedule) (Hydra JSON-LD collection):
     /api/a_gpv_g?after=...&before=...&group[]=4.1&time=<CITY><STREET>
   Requires:
     - Origin / Referer
     - x-debug-key = base64("<CITY>/<STREET>")
"""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.helpers.aiohttp_client import async_get_clientsession

try:
    from yarl import URL
except Exception:  # pragma: no cover
    URL = None  # type: ignore

_LOGGER = logging.getLogger(__name__)

BASE = "https://api-toe-poweron.inneti.net"
API = f"{BASE}/api"
ORIGIN = "https://toe-poweron.inneti.net"
REFERER = "https://toe-poweron.inneti.net/"


def _debug_key(city_id: int | str, street_id: int | str) -> str:
    raw = f"{city_id}/{street_id}".encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _build_url(path: str, params: dict[str, str]) -> str:
    """Build a URL with proper encoding (handles + in +00:00, Cyrillic, spaces, etc.)."""
    base = f"{API}/{path.lstrip('/')}"
    if URL is not None:
        return str(URL(base).with_query(params))
    # Fallback (should rarely be used in HA container)
    from urllib.parse import urlencode
    return base + "?" + urlencode(params)


async def _get_json(hass, url: str, *, accept: str) -> Any:
    session = async_get_clientsession(hass)
    headers = {
        "Accept": accept,
        "Origin": ORIGIN,
        "Referer": REFERER,
    }
    async with session.get(url, headers=headers, allow_redirects=False) as resp:
        text = await resp.text()
        if resp.status >= 400:
            raise RuntimeError(f"Upstream HTTP {resp.status}: {text[:200]}")
        try:
            return await resp.json(content_type=None)
        except Exception as err:
            raise RuntimeError(f"Upstream non-JSON response: {text[:200]}") from err


async def fetch_streets(hass, city_id: int, name_query: str | None = None) -> list[dict[str, Any]]:
    """Return a list of streets as dicts: {id:int, name:str}."""
    params: dict[str, str] = {"pagination": "false", "city.id": str(city_id)}
    if name_query:
        params["name"] = name_query

    url = _build_url("pw_streets", params)
    data = await _get_json(hass, url, accept="application/ld+json")

    members = data.get("hydra:member") or []
    streets: list[dict[str, Any]] = []
    for s in members:
        if not isinstance(s, dict):
            continue
        sid = s.get("id")
        name = s.get("name")
        if isinstance(sid, int) and isinstance(name, str):
            streets.append({"id": sid, "name": name})
    return streets


async def fetch_building_group(hass, city_id: int, street_id: int) -> str:
    """Return chergGpv group like 4.1 for a given street."""
    url = _build_url(
        "pw-accounts/building-groups",
        {"cityId": str(city_id), "streetId": str(street_id)},
    )
    data = await _get_json(hass, url, accept="application/json")
    groups = data.get("buildingGroups") or []
    if not groups:
        raise RuntimeError("No buildingGroups returned")
    grp = (groups[0] or {}).get("chergGpv")
    if not isinstance(grp, str) or not grp:
        raise RuntimeError("Invalid buildingGroups payload")
    return grp


async def fetch_building_groups(hass, city_id: int, street_id: int) -> list[str]:
    """Return list of building groups (strings). Config flow expects a list."""
    grp = await fetch_building_group(hass, city_id, street_id)
    return [grp] if grp else []


def _utc_day_start(now: datetime) -> datetime:
    return now.astimezone(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


def _format_utc(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_date_graph(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


async def fetch_schedule(
    hass,
    *,
    city_id: int,
    street_id: int,
    group: str,
) -> dict[str, Any]:
    """Fetch outage schedule with robust day-boundary windows."""
    session = async_get_clientsession(hass)
    now = datetime.now(timezone.utc)
    day0 = _utc_day_start(now)
    day2 = day0 + timedelta(days=2)
    params = {
        "after": _format_utc(day0),
        "before": _format_utc(day2),
        "group[]": group,
        "time": f"{city_id}{street_id}",
    }
    url = _build_url("a_gpv_g", params)
    headers = {
        "Accept": "application/ld+json",
        "Origin": ORIGIN,
        "Referer": REFERER,
        "x-debug-key": _debug_key(city_id, street_id),
    }

    last_empty: dict[str, Any] | None = None
    last_error: str | None = None
    for attempt in range(3):
        async with session.get(url, headers=headers, allow_redirects=False) as resp:
            text = await resp.text()
            if resp.status >= 500:
                _LOGGER.warning("Upstream HTTP %s, retrying schedule fetch", resp.status)
                last_error = f"Upstream HTTP {resp.status}: {text[:200]}"
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            if resp.status >= 400:
                raise RuntimeError(f"Upstream HTTP {resp.status}: {text[:200]}")
            try:
                data = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                raise RuntimeError(f"Upstream non-JSON response: {text[:200]}") from err

        members = data.get("hydra:member") or []
        if not members:
            _LOGGER.warning("Schedule response empty (hydra:member missing)")
            last_empty = {"raw": data, "times": {}, "date_graph": None, "empty": True}
            await asyncio.sleep(0.5 * (2**attempt))
            continue

        times: dict[str, Any] = {}
        date_graph: datetime | None = None
        for item in members:
            if not isinstance(item, dict):
                continue
            if date_graph is None:
                date_graph = _parse_date_graph(item.get("dateGraph"))
            data_json = item.get("dataJson")
            if not isinstance(data_json, dict):
                continue
            group_data = data_json.get(group)
            if isinstance(group_data, dict):
                group_times = group_data.get("times")
                if isinstance(group_times, dict):
                    times = group_times
                    break

        if not times:
            _LOGGER.warning("Schedule parsed empty times for group %s", group)
            return {"raw": data, "times": {}, "date_graph": date_graph, "empty": True}

        return {"raw": data, "times": times, "date_graph": date_graph, "empty": False}

    if last_empty is not None:
        return last_empty
    if last_error is not None:
        raise RuntimeError(last_error)
    return {"raw": {}, "times": {}, "date_graph": None, "empty": True}
