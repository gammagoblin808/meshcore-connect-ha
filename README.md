# MeshCore Connect for Home Assistant

Local custom integration using the official `meshcore` Python library. It connects
to one companion per entry, using USB serial (115200 baud) or TCP (default 5000).
BLE companions with the Connect firmware also expose the management protocol over
USB. Home Assistant must have exclusive access to the selected interface.

## Installation

### HACS custom repository

HACS only supports **public GitHub repositories**, not Framagit/GitLab URLs or
subdirectories of a repository. The integration is maintained in the
[MeshCore Connect source repository](https://framagit.org/tersis/meshcore-connect).
Its standalone HACS export contains `hacs.json`, this README and
`custom_components/meshcore_connect/` at the repository root.

[Open this repository in HACS](https://my.home-assistant.io/redirect/hacs_repository/?owner=gammagoblin808&repository=meshcore-connect-ha&category=integration)

Or add it manually in HACS:

1. Open **HACS > three-dot menu > Custom repositories**.
2. Enter `https://github.com/gammagoblin808/meshcore-connect-ha` and choose **Integration**.
3. Add it, find **MeshCore Connect** in HACS, and download it.
4. Restart Home Assistant.
5. Open **Settings > Devices & services > Add integration > MeshCore Connect**.

HACS manages subsequent integration downloads/updates from that GitHub repository.
Restart Home Assistant after updating. This does not update device firmware or
the Linux/Android apps. For an existing manual installation, back up the HA
configuration first; the integration domain stays `meshcore_connect` so its
existing entries do not need to be deleted.

See the official [HACS custom repository instructions](https://hacs.xyz/docs/faq/custom_repositories/)
and [supported Git providers](https://hacs.xyz/docs/faq/other_git_providers/).

### Manual fallback

Place `custom_components/meshcore_connect` in Home Assistant's configuration
directory under `custom_components`, restart Home Assistant, then add **MeshCore
Connect** under **Settings > Devices & services > Add integration**. This is not
a built-in Home Assistant integration or an add-on. English, German and French
configuration screens are included.

## Connect the Gateway

For USB, select a stable `/dev/serial/by-id/...` path on the Home Assistant host,
not a laptop path. Containers need the serial device passed through. For TCP, use
a trusted local network; MeshCore companion TCP is not an encrypted Internet API.
The gateway companion must allow the session to read messages: Connect device-PIN
authentication is not yet implemented by this integration. Existing device PINs
are never changed or bypassed.

## Configure in Home Assistant

After connecting the gateway, open **Settings > Devices & services > MeshCore
Connect > Configure**. No contact keys are required during initial connection.

- **Allowed contacts:** select names from the companion's contact list. Change
  this selection at any time without reconnecting. An empty selection blocks all
  senders; adding a device contact or favorite does not grant word permission.
- **Device contacts:** add a contact with its complete 64-character public key,
  name and device type, or select an existing contact to remove. Removal requires
  confirmation and also removes that contact from the word allowlist.
- **Device favorites:** read and change the companion's actual favorite flags.
  Other contact flags and routes are preserved. Changes affect the connected
  gateway, not the contact lists of other devices over the mesh.
- **Device channels:** add a channel to an empty slot or remove an existing
  channel after confirmation. `#hashtag` channels derive their key from the name;
  private channels require the shared 32-character hexadecimal key. Channel keys
  are sent to the device, not saved in integration options or exposed in sensor
  attributes. Occupied slots cannot be overwritten by Add channel.

Each save finishes the configuration dialog. Reopen **Configure** for another
operation. Device operations require an active gateway connection and a firmware
that permits administration. Contact/channel changes are local USB/TCP commands,
not over-the-air provisioning. Multi-contact favorite updates are individual
device writes; after an interrupted operation reopen the menu to read back the
actual state.

### Words and Permissions on the Device Page

Open the gateway's device page under **Settings > Devices & services**. Its
configuration entities include an **Allowed: contact name** switch for every
contact. Toggle it to grant or revoke permission to trigger word events. These
permissions are stored in Home Assistant, not on the remote radio devices.

Enter a word or phrase in **Add word**. A named **event entity** and an editable
**Word: name** text entity appear without restarting or reloading. Edit the text
entity to change the word; clear its value to remove it. Removed word entities
become unavailable. Renaming preserves entity identity; adding a new word after
deleting one does not reuse the old automation target. **Configure > Words** also
provides add, edit and remove forms.

Each exact private message from an allowed contact updates that word's event
entity with event type `received`, the sender's public key and sender timestamp.
Repeated messages produce new events. Matching is case-sensitive; spaces are
significant. Use the event entity as the trigger in a Home Assistant automation.
There is no action editor or automatic action execution inside the integration.

Updating from version 1.1 preserves configured words and allowed contacts, but
removes the old per-word action definitions. Recreate the desired behavior in
Home Assistant automations using the new event entities.

On a watch or display companion, enable Home Assistant in the Connect app, flag
the gateway companion as the HA contact and configure an action payload such as
`light_living_room`. Pressing that device action sends a private mesh message to
the gateway. Only an explicitly allowed contact can trigger word entities.
Unknown contacts, ambiguous prefixes, channel messages and remote command replies
cannot trigger word entities. No separate HA token needs to be stored
on the portable device.

### Radio Values and Activities

The device page shows packets sent and received, receive errors, last RSSI/SNR,
noise floor and transmit/receive airtime. Values come from the companion's local
statistics and are refreshed once per minute. Unsupported values are unavailable,
not reported as zero. Counters may reset when the companion restarts.

The device's **Activity** view records received private and channel messages,
including non-allowed or unknown senders and messages without configured words.
Channel messages include their slot number; private messages show the known
contact name or public-key prefix. Logging a message does not grant permission
to trigger word events. Only messages actually delivered by the companion's
message queue can be shown, not undecryptable radio traffic.

Message text is stored in Home Assistant's recorder/logbook history, subject to
its retention and exclusion settings. Anyone with access to that history can
read it. Duplicate received packets are suppressed.

### Favorites and Contact Queries

Each companion favorite has its own **notification entity**, named after the
contact. Open the gateway's device page to see these individual favorites, or
choose **Send a notification message** (`notify.send_message`) in the HA action
editor and select the favorite as the target. Enter the message normally; no
public key or template is needed. Messages are limited to 130 UTF-8 bytes.
The entity's timestamp records the last send attempt, not confirmed delivery.

Use the **Refresh contacts and favorites** button on the gateway device page to
read changes immediately. New favorites appear without reloading the integration.
Removed favorites become unavailable and cannot send; their entity identity is
retained so existing automations do not silently target someone else. Renaming a
contact does not change its identity. Favoriting still does not grant permission
to trigger incoming word events.

The **Favorites** sensor reports the favorite count, with names and public keys
in its `contacts` attribute. It is refreshed locally every five minutes and after
changes made through the integration. For an immediate read, use the
**MeshCore Connect: Read contacts** action in Home Assistant and enable
**Favorites only** if desired. `meshcore_connect.get_contacts` returns a
`contacts` list; it does not send radio advertisements or remote requests.

### Events and Outgoing Messages

The integration fires `meshcore_connect_message` with `entry_id`, `public_key`,
`text`, `sender_timestamp` and `sos`. An SOS (`SOS!` or `SOS! GPS: ...`) also fires
`meshcore_connect_sos`, including SOS without GPS. Message text is never evaluated
as code or interpreted as a service name. These two compatibility events remain
restricted to allowed private-message senders. Existing event automations still
work. Optional event-based automation example:

```yaml
alias: MeshCore living room light
triggers:
  - trigger: event
    event_type: meshcore_connect_message
    event_data:
      public_key: "REPLACE_WITH_COMPLETE_REMOTE_PUBLIC_KEY"
      text: "light_living_room"
actions:
  - action: light.turn_on
    target:
      entity_id: light.living_room
```

`meshcore_connect.send_message` queues an outgoing private message. Select the
integration entry, give an existing contact's complete `public_key` and `text`
(at most 130 UTF-8 bytes). Success means accepted by the companion, **not delivered**.
Never rely on this mesh integration as the only emergency alerting system.

## Power and Limits

Incoming queue notifications trigger reads; a 30-second local queue check recovers
missed notifications and disconnected links. Gateway battery voltage is read every
five minutes, as are the companion's contacts and favorites; radio statistics are
read once per minute. These are local
USB/TCP commands, not periodic over-the-air requests
to portable devices. The integration does not enable GPS or change radio settings.

Duplicate messages are suppressed with a bounded in-memory cache. The cache does
not survive a Home Assistant restart; queued messages may be delivered later.
Automations that control sensitive equipment must provide their own freshness and
safety checks. A message timestamp is supplied by the sender, not a trusted clock.

Current scope: private word event entities, editable HA permissions and words,
received-message activities, SOS events, outgoing messages, gateway battery and
radio statistics, contacts, favorites and local channel administration.
No remote firmware flashing, authorized channel-word triggers, BLE
transport, remote battery polling or device-PIN management is provided here.

API references: [MeshCore Python](https://github.com/meshcore-dev/meshcore_py/tree/v2.3.0),
[Home Assistant config entries](https://developers.home-assistant.io/docs/config_entries_index/).

## Development Tests

The automated tests use Python 3.13 and Home Assistant 2025.3.4, with mocked
companion transport and a real HA event bus. They do not replace a hardware test
or verify every subsequent Home Assistant release.

Run these commands from the root of the
[Framagit source repository](https://framagit.org/tersis/meshcore-connect),
which contains the tests. The GitHub HACS mirror contains only installation files.

```sh
python3.13 -m venv /tmp/connect-ha-tests
/tmp/connect-ha-tests/bin/pip install -r integrations/home_assistant/requirements-test.txt
/tmp/connect-ha-tests/bin/python -m pytest -q integrations/home_assistant/tests
```
