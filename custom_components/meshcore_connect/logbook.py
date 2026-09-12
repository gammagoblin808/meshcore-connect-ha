"""Show every received message in the companion's HA activity view."""
from homeassistant.core import callback

from .const import DOMAIN, EVENT_RECEIVED, EVENT_RESPONSE

RESPONSE_PHASES = {
    "de": {
        "requested": "Aktionsbest\u00e4tigung angefordert",
        "executing": "Zugeh\u00f6rige Automation gestartet",
        "queued": "R\u00fcckantwort an Funkger\u00e4t \u00fcbergeben; Zustellung nicht best\u00e4tigt",
        "failed": "R\u00fcckantwort konnte nicht an Funkger\u00e4t \u00fcbergeben werden",
        "retrying": "R\u00fcckantwort erneut senden",
        "rerouted": "R\u00fcckantwort ohne gespeicherten Funkpfad versuchen",
        "delivered": "Empfang der R\u00fcckantwort vom Funkger\u00e4t des Empf\u00e4ngers best\u00e4tigt",
        "unconfirmed": "Keine Empfangsbest\u00e4tigung f\u00fcr R\u00fcckantwort; keine weiteren Sendeversuche",
    },
    "en": {
        "requested": "Action confirmation requested",
        "executing": "Related automation started",
        "queued": "Reply handed to radio; delivery not confirmed",
        "failed": "Reply could not be handed to radio",
        "retrying": "Retrying reply",
        "rerouted": "Trying reply without the saved radio path",
        "delivered": "Reply receipt confirmed by recipient radio",
        "unconfirmed": "No receipt confirmation for reply; no further attempts",
    },
    "fr": {
        "requested": "Confirmation d'action demand\u00e9e",
        "executing": "Automatisation associ\u00e9e d\u00e9marr\u00e9e",
        "queued": "R\u00e9ponse transmise \u00e0 la radio; livraison non confirm\u00e9e",
        "failed": "Impossible de transmettre la r\u00e9ponse \u00e0 la radio",
        "retrying": "Nouvelle tentative d'envoi de la r\u00e9ponse",
        "rerouted": "Tentative sans le trajet radio enregistr\u00e9",
        "delivered": "R\u00e9ception confirm\u00e9e par la radio du destinataire",
        "unconfirmed": "Aucune confirmation de r\u00e9ception; fin des tentatives",
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
                "icon": "mdi:message-alert-outline" if data.get("phase") in ("failed", "unconfirmed")
                else "mdi:message-check-outline"}

    async_describe_event(DOMAIN, EVENT_RESPONSE, describe_response)
