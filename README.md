# MeshCore Connect for Home Assistant

Local custom integration using the official `meshcore` Python library. It connects
to one companion per entry, using USB serial (115200 baud) or TCP (default 5000).
BLE companions with the Connect firmware also expose the management protocol over
USB. Home Assistant must have exclusive access to the selected interface.

**Gateway companion (raw radio)** is a separate mode: Home Assistant owns the
companion identity, contacts and channels. The RAK only transports radio packets
over an authenticated service connection on **5001, 5002 or 5003**. Port **5000**
is administration, never the HA service endpoint. This is not the normal
companion protocol on another port.

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

### Independent HA Companion via RAK

1. The RAK must actually run the raw Gateway firmware, for example
   `26.09.57-gwexp2`, not `v26.09.38+mc1.17.1` Companion firmware. Updating this
   integration does not flash or configure the RAK.
2. On the gateway admin page, configure an independent service key and enable
   one of ports **5001-5003**. Release any other client on that port. There is
   exactly one client per service port. The service key is not the admin key.
3. Add the integration and choose **Gateway companion (raw radio)** (German:
   **Gateway-Companion (Rohfunk)**). Enter the host, service port, service key and
   the name of the new HA companion. Setup checks the protocol, authentication
   and a PING; it sends no radio packet and makes no gateway configuration change.
4. The HA device exposes **Companion public key** and **Announce HA companion**.
   After explicitly enabling radio transmission on the gateway, send an
   announcement to add the HA companion on your other radios. The experimental
   gateway currently resets its TX permission after a reboot. HA does not bypass
   that permission or change the fixed gateway radio profile.
5. Contacts are learned from signature-verified advertisements or added manually
   with their full public key. Select **Allowed contacts** separately, configure
   action words and enable **Send action confirmations** as with a normal
   companion. On the remote radio, send to the **HA companion**, not the old RAK
   companion identity.

Private text messages, MeshCore ACKs/path returns, signed advertisements and
configured channel reception are supported on ordinary flood/direct routes with
1-, 2- or 3-byte path hashes. Channel messages remain activity events, not private
action triggers. Scoped transport packets, room-server messages, remote CLI,
gateway administration and radio configuration are not implemented by this mode.
No node battery or airtime measurements are invented when the gateway does not
provide them. Packet counters describe the current HA service session.

Gateway `DONE` means local transmission completed, never recipient delivery.
Only a matching received MeshCore ACK confirms delivery. The gateway's fixed
airtime limits, 30-second transmit queue expiry and TX permission still apply;
rejections and expired requests are failures, not successful replies. An
interrupted transmit is not automatically replayed by the gateway transport.

Identity, local contacts, channel keys and a bounded recent-message replay cache
are stored in HA's private `.storage/meshcore_connect.gateway.<public-key>` file.
The service key is stored in the integration's HA configuration. Protect HA
backups as secrets. Neither private identity nor channel keys are sent to the
gateway or included in integration diagnostics. Back up HA before migration;
lost identity storage is an error, never a silently regenerated radio identity.
The replay cache suppresses the most recent 256 received message identities
across restarts, not unlimited historical replays. Existing automation freshness
and authorization precautions still apply.

The old version-3 gateway option only changed the companion TCP port. Such an
entry now requests reauthentication to obtain the service key and create its
actual HA identity. Existing words, allowlists and entity identifiers are retained.
Reconfiguring a working gateway entry preserves its HA radio identity and local
contacts; removing the integration deletes its private companion store. USB and
normal TCP entries are not converted. Existing contacts in the RAK are not
implicitly imported or overwritten.

Use only a trusted, isolated LAN. PSK challenge authentication does not encrypt
or authenticate the subsequent gateway stream. Do not expose these ports to the
Internet. Configure and enable the service port in the gateway web interface
before connecting HA. HA cannot unlock a disabled port or change the admin key.
Gateway firmware 26.09.60 provides a login page and an authenticated admin-password
setting; unconfigured gateways start with `admin`, while existing keys stay valid.

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

In raw-gateway mode these same controls manage the local HA companion store;
channel keys and contacts are not written to the RAK.

### Contact Learning

Under **Configure > Device contacts > Add contact**, enter the full public key,
name and device type. **Favorite** and **Allow HA actions** are independent options.
Existing contacts cannot be overwritten by this operation.

**Device contacts > Automatic learning** and the device page expose separate
switches for learning companions/room servers, learning repeaters, marking new
contacts as favorites, and permitting HA actions for newly learned contacts.
Automatic action permission is **off by default**: enabling it trusts newly
discovered senders to trigger configured HA actions. Favoriting alone grants no
permission. Changing a learning option does not modify existing permissions.

The raw-gateway companion validates signed advertisements before learning and
saves contacts in HA storage. Advertisements never replace saved favorites, and
a full contact list does not evict any contact. A normal USB/TCP companion uses
manual-add firmware mode once learning is configured; HA then imports selected
discoveries into free slots without changing telemetry or location settings.
HA must be connected for this managed learning. Existing firmware-managed
learning is left unchanged until an HA learning option is configured.

Each contact has separate **Favorite** and **Allowed** switches on the device
page. Explicit changes affect only that contact. A stale favorites dialog does
not clear favorites that were learned after the dialog was opened.

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
Receiving a word alone does not execute an action. Use a normal HA automation,
or the optional response blueprint below.

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

### Actions With a Radio Response

Since **26.09.23**, Linux and Android can execute saved HA actions directly from
the **Home Assistant** view and distinguish mesh delivery from HA execution.
The existing action buttons on supported companions send the same word messages.

1. Update the integration and restart Home Assistant.
2. Configure the word and allow the sending contact as described above.
3. On the **MeshCore Connect device page**, under **Controls**, enable
   **Send action confirmations** (German: **Aktionsbestätigungen senden**).
   This per-gateway switch defaults to off and is retained across restarts.
4. Keep your existing automation for the word's event entity, or create a normal
   automation using that entity. No blueprint or reply action is required.
5. In the Connect app, select the gateway as the HA contact, save the matching
   **Word / message**, then press the action's play button.

The switch only controls replies. It does not enable, disable, change or repeat
your automations. Turning it off during execution suppresses the pending reply
without stopping the action; turning it back on does not acknowledge old runs.

The integration follows HA's context from an allowed private message through its
word event entity into directly triggered automations. Compatibility event
automations for `meshcore_connect_message`, `meshcore_connect_word` and SOS are
also supported. Merely listing an automation under a device's related items is
not sufficient: that particular run must have been triggered by the message.
Manual runs, unrelated triggers and rejected senders produce no radio reply.

HA's execution trace is observed locally; the integration never rewrites an
automation or executes its actions again. If multiple automations start for one
message, their results are combined and one reply is sent after all finish.
Automations skipped by their conditions or execution mode do not count as
executed. A message that starts no automation receives no execution confirmation.

The private reply goes to the **original sender**, not a fixed notification
contact. `HA OK <timestamp>: <word>` reports completed execution. `HA ERR` reports
an execution error; `HA UNKNOWN` reports a stopped or aborted action sequence,
missing execution evidence or the five-minute observation limit. Automations
continue running even after this observation limit. App status matching
checks the gateway contact, original message timestamp and exact word, so an
older response does not confirm a newer action. Replies are also ordinary
private messages readable on existing Connect firmware.

Automations created in HA's UI normally have an ID and saved traces. YAML-defined
automations also need a unique `id` and at least one stored trace. Disabled traces
or an unsupported HA trace format must never be interpreted as successful
execution. Trace-store layouts from HA 2025.3 and the newer split run buckets
are supported; automated runtime tests currently use HA 2025.3.4.

**Executed means the HA action sequence completed without a reported error.**
For confirmation that a physical device actually changed state, add an explicit
wait for that state to the sequence, with a timeout that aborts on failure.
Nonblocking calls such as `script.turn_on` and actions with `continue_on_error`
cannot by themselves provide that guarantee. See
[Home Assistant script actions](https://www.home-assistant.io/docs/scripts/).

Mesh delivery acknowledgement is not action completion. Replies are best-effort
radio messages; if none arrives, the apps show **Result unknown** after six
minutes. Failed replies never automatically repeat the action. A duplicate run
for the same registered request is rejected, and permissions are checked again
before execution. Request tracking is bounded and in memory, not a persistent
exactly-once guarantee across HA restarts. On integration shutdown observation
is stopped without cancelling your existing automations or sending false success.

The optional earlier response blueprint remains compatible, but is no longer
required. Its replies also respect the device switch; it does not receive a
second reply from the automatic observer. Do not add a blueprint automation
alongside an existing automation for the same action, as both would execute.
The blueprint calls `meshcore_connect.execute_action` with `entry_id`,
`request_id` from the word event and its `automation_entity`. The service reads
the blueprint's unrendered action sequence, preserving wait and repeat templates
until their execution. Requests expire after five minutes.
Available action variables are `meshcore_sender`, `meshcore_word`
and `meshcore_request_id`. Incoming text is only matched against configured
words; it never chooses arbitrary HA services or targets.

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

When action confirmations are enabled, Activity also records the incoming
confirmation request, the start of the correlated automation, and whether its
reply was accepted by the companion or failed. Final replies wait for a matching
MeshCore ACK and make at most three attempts using the same message timestamp.
After two unconfirmed attempts, a saved outgoing contact path is reset before
the final attempt so the encrypted private reply can use flood routing.
ACK waits follow the companion's suggested timeout, bounded to 2-30 seconds
per attempt. The companion receive loop remains available during these waits.

An accepted reply is **not** a confirmed delivery over the mesh. Activity only
reports confirmed receipt when the recipient radio's matching ACK is received;
it does not claim that the app displayed the message or that a person read it.
Missing ACKs are reported as unconfirmed, not as proof of delivery failure.
These entries distinguish a missing automation correlation from a local send
failure or a radio return-path issue. The integration never repeats an action
because its reply failed. Disabling confirmations prevents further reply attempts.
The service result `reply_queued` continues to mean local radio acceptance, not
confirmed delivery. Progress notices (`HA RUN`) are sent once without waiting
for a radio ACK, so a missing reply cannot delay execution of the action.

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

Current scope: private word event entities, device-switch-controlled automatic
execution replies, optional action execution with private radio responses, editable HA permissions and words,
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
/tmp/connect-ha-tests/bin/pip install -r home-assistant/requirements-test.txt
/tmp/connect-ha-tests/bin/python -m pytest -q home-assistant/tests
```

The `event.received` trigger requires a newer HA test environment; it is skipped
on 2025.3.4. The full suite also runs with Home Assistant 2026.9.1 and Python
3.14.2 or newer. No real locks, buttons or companion transports are used:

```sh
python3.14 -m venv /tmp/connect-ha-2026-tests
/tmp/connect-ha-2026-tests/bin/pip install -r home-assistant/requirements-test-current.txt
/tmp/connect-ha-2026-tests/bin/python -m pytest -q home-assistant/tests
```
