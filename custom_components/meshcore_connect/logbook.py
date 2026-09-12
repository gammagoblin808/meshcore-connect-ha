"""Show every received message in the companion's HA activity view."""
from homeassistant.core import callback

from .const import DOMAIN, EVENT_RECEIVED, EVENT_RESPONSE

RESPONSE_PHASES = {
    "de": {
        "requested": "Aktionsbest\u00e4tigung angefordert",
        "executing": "Zugeh\u00f6rige Automation gestartet",
        "queued": "R\u00fcckantwort an Funkger\u00e4t \u00fcbergeben; Zustellung nicht best\u00e4tigt",
        "failed": "R\u00fcckantwort konnte nicht an Funkger\u00e4t \u00fcbergeben werden",
    },
    "en": {
        "requested": "Action confirmation requested",
        "executing": "Related automation started",
        "queued": "Reply handed to radio; delivery not confirmed",
        "failed": "Reply could not be handed to radio",
    },
    "fr": {
        "requested": "Confirmation d'action demand\u00e9e",
        "executing": "Automatisation associ\u00e9e d\u00e9marr\u00e9e",
        "queued": "R\u00e9ponse transmise \u00e0 la radio; livraison non confirm\u00e9e",
        "failed": "Impossible de transmettre la r\u00e9ponse \u00e0 la radio",
    },
}


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

    @callback
    def describe_response(event):
        data = event.data
        phases = RESPONSE_PHASES.get(hass.config.language, RESPONSE_PHASES["en"])
        phase = phases.get(data.get("phase"), data.get("phase", ""))
        status = f' (HA {data["status"]})' if data.get("status") else ""
        return {"name": data.get("name", "MeshCore Connect"),
                "message": f'{phase}{status}: {data.get("recipient", "")} / {data.get("text", "")}',
                "device_id": data.get("device_id"),
                "icon": "mdi:message-alert-outline" if data.get("phase") == "failed"
                else "mdi:message-check-outline"}

    async_describe_event(DOMAIN, EVENT_RESPONSE, describe_response)
