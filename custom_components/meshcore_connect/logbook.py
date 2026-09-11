"""Show every received message in the companion's HA activity view."""
from homeassistant.core import callback

from .const import DOMAIN, EVENT_RECEIVED


@callback
def async_describe_events(hass, async_describe_event):
    @callback
    def describe(event):
        data = event.data
        source = f'#{data.get("channel_idx")}' if data.get("kind") == "channel" else data.get("sender", "")
        return {"name": data.get("name", "MeshCore Connect"),
                "message": f'{source}: {data.get("text", "")}',
                "icon": "mdi:message-text"}

    async_describe_event(DOMAIN, EVENT_RECEIVED, describe)
