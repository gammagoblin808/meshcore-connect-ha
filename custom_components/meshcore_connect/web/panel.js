const translations = {
  de: {
    contacts: 'Kontakte', add: 'Kontakt hinzufügen', settings: 'Einstellungen', device: 'Companion',
    search: 'Name oder Public Key', name: 'Name', key: 'Public Key', kind: 'Gerätetyp',
    favorite: 'Favorit', allowed: 'HA-Aktionen erlaubt', save: 'Kontakt speichern', refresh: 'Aktualisieren',
    remove: 'Kontakt löschen', cancel: 'Abbrechen', online: 'Verbunden', offline: 'Nicht verbunden',
    empty: 'Keine Kontakte.', noMatch: 'Keine passenden Kontakte.', noDevice: 'Keine geladene MeshCore-Connect-Integration.',
    companion: 'Companion', repeater: 'Repeater', room: 'Raumserver',
    deleteWarning: 'Dieser Kontakt wird gelöscht. Seine Favoritenmarkierung und HA-Freigabe werden ebenfalls entfernt.',
    discard: 'Ungespeicherte Eingaben verwerfen?',
    allowWarning: 'Neu gelernte, auch bisher unbekannte Kontakte dürfen damit HA-Aktionen auslösen. Einschalten?',
    saved: 'Kontakt gespeichert.', deleted: 'Kontakt gelöscht.', changed: 'Gespeichert.',
    learn_contacts: 'Kontakte automatisch lernen', learn_repeaters: 'Repeater automatisch lernen',
    learn_favorites: 'Automatisch gelernte Kontakte als Favoriten speichern',
    learn_allowed: 'Automatisch gelernte Kontakte für HA-Aktionen erlauben', action_responses: 'Aktionsbestätigungen senden',
    device_error: 'Das Gerät hat die Änderung nicht bestätigt. Verbindung und Kontaktliste prüfen.',
    invalid_contact: 'Eingaben prüfen. Der Kontakt könnte zwischenzeitlich geändert worden sein.',
    contact_exists: 'Dieser Public Key ist bereits gespeichert.', invalid_key: 'Public Key: 64 Hexadezimalzeichen erforderlich.',
    invalid_contact_name: 'Name: 1 bis 31 UTF-8-Bytes erforderlich.', not_loaded: 'Diese Integration ist nicht geladen.',
    error: 'Anfrage fehlgeschlagen. Bitte erneut prüfen.', menu: 'Seitenleiste öffnen',
    commands: 'Befehle', command: 'Nachrichteninhalt', commandSave: 'Befehl speichern', edit: 'Bearbeiten',
    commandRemove: 'Befehl löschen', commandDeleteWarning: 'Befehl löschen? Verknüpfte Automationen erhalten dafür keine Ereignisse mehr.',
    noCommands: 'Keine Befehle.', invalid_word: 'Befehl muss eindeutig sein: 1 bis 130 UTF-8-Bytes, ohne Zeilenumbrüche.',
    stale_word: 'Der Befehl wurde inzwischen geändert. Liste aktualisieren und erneut auswählen.',
    feed: 'Nachrichten', noMessages: 'Noch keine Nachrichten empfangen.', direct: 'Direkt', channel: 'Kanal',
    live: 'Live', feedError: 'Live-Verbindung unterbrochen', unknown: 'Unbekannt',
  },
  en: {
    contacts: 'Contacts', add: 'Add contact', settings: 'Settings', device: 'Companion', search: 'Name or public key',
    name: 'Name', key: 'Public key', kind: 'Device type', favorite: 'Favorite', allowed: 'HA actions allowed',
    save: 'Save contact', refresh: 'Refresh', remove: 'Delete contact', cancel: 'Cancel', online: 'Connected',
    offline: 'Disconnected', empty: 'No contacts.', noMatch: 'No matching contacts.', noDevice: 'No loaded MeshCore Connect integration.',
    companion: 'Companion', repeater: 'Repeater', room: 'Room server',
    deleteWarning: 'This contact will be deleted, including its favorite status and HA action permission.',
    discard: 'Discard unsaved changes?',
    allowWarning: 'Newly learned, previously unknown contacts will be allowed to trigger HA actions. Enable?',
    saved: 'Contact saved.', deleted: 'Contact deleted.', changed: 'Saved.',
    learn_contacts: 'Learn contacts automatically', learn_repeaters: 'Learn repeaters automatically',
    learn_favorites: 'Save automatically learned contacts as favorites', learn_allowed: 'Allow HA actions for automatically learned contacts',
    action_responses: 'Send action confirmations', device_error: 'The device did not confirm the change. Check the connection and contact list.',
    invalid_contact: 'Check the input. The contact may have changed.', contact_exists: 'This public key is already saved.',
    invalid_key: 'Public key: 64 hexadecimal characters required.', invalid_contact_name: 'Name: 1 to 31 UTF-8 bytes required.',
    not_loaded: 'This integration is not loaded.', error: 'Request failed. Please check again.', menu: 'Open sidebar',
    commands: 'Commands', command: 'Message content', commandSave: 'Save command', edit: 'Edit',
    commandRemove: 'Delete command', commandDeleteWarning: 'Delete command? Linked automations will no longer receive its events.',
    noCommands: 'No commands.', invalid_word: 'Command must be unique: 1 to 130 UTF-8 bytes, without line breaks.',
    stale_word: 'The command has changed. Refresh and select it again.',
    feed: 'Messages', noMessages: 'No messages received yet.', direct: 'Direct', channel: 'Channel',
    live: 'Live', feedError: 'Live connection interrupted', unknown: 'Unknown',
  },
  fr: {
    contacts: 'Contacts', add: 'Ajouter un contact', settings: 'Paramètres', device: 'Compagnon', search: 'Nom ou clé publique',
    name: 'Nom', key: 'Clé publique', kind: "Type d'appareil", favorite: 'Favori', allowed: 'Actions HA autorisées',
    save: 'Enregistrer le contact', refresh: 'Actualiser', remove: 'Supprimer le contact', cancel: 'Annuler', online: 'Connecté',
    offline: 'Déconnecté', empty: 'Aucun contact.', noMatch: 'Aucun contact correspondant.', noDevice: 'Aucune intégration MeshCore Connect chargée.',
    companion: 'Compagnon', repeater: 'Répéteur', room: 'Serveur de salon',
    deleteWarning: 'Ce contact sera supprimé, ainsi que son statut de favori et son autorisation pour les actions HA.',
    discard: 'Abandonner les modifications non enregistrées ?',
    allowWarning: 'Les nouveaux contacts appris pourront déclencher des actions HA. Activer ?',
    saved: 'Contact enregistré.', deleted: 'Contact supprimé.', changed: 'Enregistré.',
    learn_contacts: 'Apprendre les contacts automatiquement', learn_repeaters: 'Apprendre les répéteurs automatiquement',
    learn_favorites: 'Enregistrer les contacts appris comme favoris', learn_allowed: 'Autoriser les actions HA pour les contacts appris',
    action_responses: "Envoyer les confirmations d'action", device_error: "L'appareil n'a pas confirmé. Vérifier la connexion et les contacts.",
    invalid_contact: 'Vérifier la saisie. Le contact peut avoir changé.', contact_exists: 'Cette clé publique est déjà enregistrée.',
    invalid_key: 'Clé publique : 64 caractères hexadécimaux requis.', invalid_contact_name: 'Nom : 1 à 31 octets UTF-8 requis.',
    not_loaded: "Cette intégration n'est pas chargée.", error: 'Échec de la demande. Vérifier à nouveau.', menu: 'Ouvrir le menu',
    commands: 'Commandes', command: 'Contenu du message', commandSave: 'Enregistrer la commande', edit: 'Modifier',
    commandRemove: 'Supprimer la commande', commandDeleteWarning: 'Supprimer la commande ? Les automatisations liées ne recevront plus ses événements.',
    noCommands: 'Aucune commande.', invalid_word: 'Commande unique : 1 à 130 octets UTF-8, sans saut de ligne.',
    stale_word: 'La commande a changé. Actualiser et la sélectionner à nouveau.',
    feed: 'Messages', noMessages: 'Aucun message reçu.', direct: 'Direct', channel: 'Canal',
    live: 'En direct', feedError: 'Connexion en direct interrompue', unknown: 'Inconnu',
  },
};
const settings = ['learn_contacts', 'learn_repeaters', 'learn_favorites', 'learn_allowed', 'action_responses'];

class MeshCoreConnectPanel extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode: 'open'}); this.entries = []; this.entryId = ''; this.busy = false; this.sequence = 0;
    this.view = 'contacts';
  }
  set hass(value) {
    this._hass = value;
    if (!this.ready) { this.mount(); if (this.isConnected) this.start(); }
  }
  connectedCallback() { if (this.ready) this.start(); }
  disconnectedCallback() {
    clearInterval(this.timer); this.timer = null; this.sequence++; this.busy = false;
    this.streamGeneration = (this.streamGeneration || 0) + 1;
    if (this.unsubscribe) { this.unsubscribe(); this.unsubscribe = null; }
    this.subscribing = false;
  }
  start() {
    if (this.timer) return;
    this.request();
    this.subscribe();
    this.timer = setInterval(() => {
      if (!document.hidden && !this.busy && !this.$('delete-dialog').open) { this.request(); this.subscribe(); }
    }, 15000);
  }
  async subscribe() {
    if (this.unsubscribe || this.subscribing || !this._hass.connection) return;
    this.subscribing = true;
    const generation = this.streamGeneration || 0;
    try {
      const unsubscribe = await this._hass.connection.subscribeMessage(message => {
        if (!this.isConnected || generation !== (this.streamGeneration || 0)) return;
        if (this.busy) this.pendingMessages = this.mergeMessages(this.pendingMessages, [message]);
        const entry = this.entries.find(e => e.entry_id === message.entry_id);
        if (entry) entry.messages = this.mergeMessages(entry.messages, [message]);
        this.renderMessages();
      }, {type: 'meshcore_connect/panel_messages'});
      if (!this.isConnected || generation !== (this.streamGeneration || 0)) { unsubscribe(); return; }
      this.unsubscribe = unsubscribe; this.$('feed-status').textContent = this.t.live;
    } catch (_) {
      if (this.isConnected && generation === (this.streamGeneration || 0)) this.$('feed-status').textContent = this.t.feedError;
    } finally { if (generation === (this.streamGeneration || 0)) this.subscribing = false; }
  }
  mergeMessages(first = [], second = []) {
    return [...new Map([...first, ...second].map(message => [message.id, message])).values()]
      .sort((a, b) => a.received_at - b.received_at).slice(-100);
  }
  $(id) { return this.shadowRoot.getElementById(id); }
  get selected() { return this.entries.find(entry => entry.entry_id === this.entryId); }
  icon(name) { const icon = document.createElement('ha-icon'); icon.setAttribute('icon', 'mdi:' + name); return icon; }
  node(tag, text, className) {
    const node = document.createElement(tag); if (text !== undefined) node.textContent = text;
    if (className) node.className = className; return node;
  }
  notice(text, error = false) { this.$('notice').textContent = text; this.$('notice').classList.toggle('error', error); }
  mount() {
    this.t = translations[(this._hass.locale?.language || this._hass.language || 'de').split('-')[0]] || translations.en;
    const t = this.t;
    this.shadowRoot.innerHTML = `
      <style>
        :host{display:block;min-height:100%;background:var(--primary-background-color,#202124);color:var(--primary-text-color,#f0f2f3);font:14px/1.5 var(--paper-font-body1_-_font-family,system-ui,sans-serif);letter-spacing:0}
        *{box-sizing:border-box;letter-spacing:0}header{display:flex;align-items:center;gap:12px;padding:14px 20px;border-bottom:1px solid var(--divider-color,#444)}header img{width:36px;height:36px}h1{font-size:22px;margin:0}h2{font-size:18px;margin:0}main{max-width:1240px;margin:auto;padding:20px}button,input,select{font:inherit;color:inherit}button{min-height:44px;cursor:pointer;padding:8px 12px;border:1px solid var(--divider-color,#555);background:var(--secondary-background-color,#303236);border-radius:4px;display:inline-flex;align-items:center;justify-content:center;gap:8px}button:disabled{opacity:.45;cursor:default}button:hover:not(:disabled){filter:brightness(1.12)}.primary{background:var(--primary-color,#70d6bb);color:var(--text-primary-color,#132b23);border-color:transparent}.danger{color:var(--error-color,#ffb4ab)}ha-icon{width:22px;height:22px;flex-shrink:0}button.icon{width:44px;padding:8px}input:not([type=checkbox]),select{min-height:44px;width:100%;padding:9px;border:1px solid var(--divider-color,#555);border-radius:4px;background:var(--primary-background-color,#202124)}input[type=checkbox]{width:20px;height:20px;accent-color:var(--primary-color,#70d6bb);flex-shrink:0}label{display:grid;gap:5px}label.check{display:flex;align-items:center;gap:10px;min-height:44px}fieldset{padding:0;margin:0;border:0;min-width:0}fieldset:disabled{opacity:.65}form{display:grid;gap:14px}.toolbar{display:flex;align-items:end;gap:12px;flex-wrap:wrap}.toolbar label{width:300px;max-width:100%}.status{margin:auto 0}.grid{display:grid;grid-template-columns:minmax(0,1.65fr) minmax(300px,1fr);gap:20px;align-items:start}.side{display:grid;gap:20px}ha-card{display:block;background:var(--ha-card-background,var(--card-background-color,#292a2d));border:1px solid var(--divider-color,#45474c);border-radius:8px;box-shadow:none;overflow:hidden}.card-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 18px;border-bottom:1px solid var(--divider-color,#45474c)}.body{padding:18px}.body>label{margin-bottom:12px}.muted{color:var(--secondary-text-color,#b4bac1)}#notice{min-height:24px;margin:12px 0;overflow-wrap:anywhere}.error{color:var(--error-color,#ffb4ab)}.contact{padding:16px 18px;border-top:1px solid var(--divider-color,#45474c)}.contact:first-child{border-top:0}.contact-head{display:flex;align-items:center;gap:10px}.contact-head strong{font-size:16px;overflow-wrap:anywhere;min-width:0;flex:1}.contact-head .kind{font-size:12px;color:var(--secondary-text-color,#b4bac1)}code{display:block;font:12px/1.6 monospace;overflow-wrap:anywhere;margin:8px 0;color:var(--secondary-text-color,#b4bac1)}.contact-flags{display:flex;gap:16px;flex-wrap:wrap}.empty{padding:18px;margin:0}#count{font-size:14px;color:var(--secondary-text-color,#b4bac1)}#search{margin:0}#settings-form label{border-bottom:1px solid var(--divider-color,#45474c);padding:8px 0}#settings-form label:last-child{border:0}dialog{max-width:460px;width:calc(100% - 32px);color:inherit;background:var(--card-background-color,#292a2d);border:1px solid var(--divider-color,#555);border-radius:8px;padding:24px}dialog::backdrop{background:#0009}.dialog-actions{display:flex;justify-content:end;gap:10px;margin-top:20px}:focus-visible{outline:2px solid var(--primary-color,#70d6bb);outline-offset:3px}[hidden]{display:none!important}@media(max-width:800px){main{padding:14px}.grid{grid-template-columns:minmax(0,1fr)}header{padding:12px}.toolbar label{flex:1}.contact-head{flex-wrap:wrap}.contact-head strong{flex-basis:55%}h1{font-size:20px}}
      </style>
      <style>
        .activity{display:grid;gap:20px;grid-template-columns:minmax(0,1fr)}.grid.settings-view{grid-template-columns:minmax(0,1fr)}
        nav{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px;border-bottom:1px solid var(--divider-color,#45474c);margin:16px 0}
        nav button{background:none;border:0;border-radius:0;border-bottom:3px solid transparent;flex:1}
        nav button[aria-selected=true]{border-color:var(--primary-color,#70d6bb);color:var(--primary-color,#70d6bb)}
        .word{display:flex;align-items:center;gap:8px;padding:10px 18px;border-bottom:1px solid var(--divider-color,#45474c)}
        .word span{flex:1;min-width:0;overflow-wrap:anywhere;white-space:pre-wrap}
        #messages{max-height:520px;overflow:auto}.message{padding:12px 18px;border-bottom:1px solid var(--divider-color,#45474c)}
        .message-head{display:flex;gap:8px;flex-wrap:wrap;font-size:12px}.message-head strong{overflow-wrap:anywhere}
        .message p{white-space:pre-wrap;overflow-wrap:anywhere;margin:6px 0 0}.form-actions{display:flex;gap:8px;flex-wrap:wrap}
        #feed-status{font-size:12px;overflow-wrap:anywhere}#word-form button{max-width:100%}
        @media(max-width:800px){.activity{grid-template-columns:minmax(0,1fr)}nav{grid-template-columns:repeat(2,minmax(0,1fr))}}
      </style>
      <header><button id="menu" class="icon" title="${t.menu}" aria-label="${t.menu}"><ha-icon icon="mdi:menu"></ha-icon></button><img src="/meshcore_connect_panel/logo.png" alt=""><h1>MeshCore Connect</h1></header>
      <main><div class="toolbar"><label>${t.device}<select id="device"></select></label><span id="status" class="status muted"></span><button id="refresh" title="${t.refresh}" aria-label="${t.refresh}" class="icon"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
      <nav id="views" role="tablist" aria-label="MeshCore Connect"></nav>
      <p id="notice" role="status" aria-live="polite"></p><p id="no-device" hidden>${t.noDevice}</p>
      <div id="cards" class="grid">
        <ha-card id="contacts-card"><div class="card-head"><h2>${t.contacts}</h2><span id="count"></span></div><div class="body"><label>${t.search}<input id="search" type="search" autocomplete="off"></label></div><div id="contacts"></div></ha-card>
        <div class="side"><ha-card id="add-card"><div class="card-head"><h2>${t.add}</h2></div><div class="body"><fieldset id="add-fields"><form id="add-form">
          <label>${t.name}<input name="name" maxlength="31" required autocomplete="off"></label>
          <label>${t.key}<input name="public_key" maxlength="64" minlength="64" pattern="[a-fA-F0-9]{64}" required spellcheck="false" autocomplete="off"></label>
          <label>${t.kind}<select name="kind"><option value="1">${t.companion}</option><option value="2">${t.repeater}</option><option value="3">${t.room}</option></select></label>
          <label class="check"><input name="favorite" type="checkbox">${t.favorite}</label><label class="check"><input name="allowed" type="checkbox">${t.allowed}</label>
          <button class="primary" type="submit"><ha-icon icon="mdi:account-plus"></ha-icon>${t.save}</button>
        </form></fieldset></div></ha-card>
        <ha-card id="settings-card"><div class="card-head"><h2>${t.settings}</h2></div><div class="body"><fieldset id="settings-fields"><div id="settings-form"></div></fieldset></div></ha-card></div>
      </div>
      <div id="activity" class="activity">
        <ha-card id="commands-card"><div class="card-head"><h2>${t.commands}</h2></div><div id="words"></div>
          <div class="body"><fieldset id="word-fields"><form id="word-form">
            <label>${t.command}<input id="word-text" maxlength="130" required autocomplete="off"></label>
            <div class="form-actions"><button type="submit" class="primary"><ha-icon icon="mdi:content-save"></ha-icon>${t.commandSave}</button>
            <button type="button" id="word-cancel" hidden>${t.cancel}</button></div>
          </form></fieldset></div></ha-card>
        <ha-card id="messages-card"><div class="card-head"><h2>${t.feed}</h2><span id="feed-status" class="muted"></span></div><div id="messages" role="log" aria-live="polite" aria-relevant="additions"></div></ha-card>
      </div></main>
      <dialog id="delete-dialog" aria-labelledby="delete-title"><h2 id="delete-title">${t.remove}</h2><p><strong id="delete-name"></strong></p><code id="delete-key"></code><p>${t.deleteWarning}</p><div class="dialog-actions"><button id="delete-cancel">${t.cancel}</button><button id="delete-confirm" class="danger"><ha-icon icon="mdi:delete"></ha-icon>${t.remove}</button></div></dialog>`;
    this.ready = true;
    for (const [view, icon] of [['contacts', 'account-multiple'], ['commands', 'message-flash'], ['messages', 'message-text'], ['settings', 'cog']]) {
      const tab = this.node('button'); tab.id = 'tab-' + view; tab.dataset.view = view;
      tab.setAttribute('role', 'tab'); tab.setAttribute('aria-controls', view + '-card');
      tab.append(this.icon(icon), this.node('span', view === 'messages' ? t.feed : t[view]));
      tab.onclick = () => { this.view = view; this.renderViews(); };
      tab.onkeydown = event => {
        const tabs = [...this.$('views').children], index = tabs.indexOf(tab);
        const target = event.key === 'ArrowRight' ? (index + 1) % tabs.length :
          event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length :
          event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
        if (target !== null) { event.preventDefault(); tabs[target].click(); tabs[target].focus(); }
      };
      this.$('views').append(tab);
      this.$(view + '-card').setAttribute('role', 'tabpanel');
      this.$(view + '-card').setAttribute('aria-labelledby', tab.id);
    }
    this.renderViews();
    this.$('menu').onclick = () => this.dispatchEvent(new Event('hass-toggle-menu', {bubbles: true, composed: true}));
    this.$('refresh').onclick = () => this.request('refresh');
    this.$('search').oninput = () => this.renderContacts();
    this.$('device').onchange = () => {
      const form = this.$('add-form');
      const dirty = form.elements.name.value || form.elements.public_key.value || form.elements.favorite.checked || form.elements.allowed.checked || form.elements.kind.value !== '1' || this.$('word-text').value;
      if (dirty && !window.confirm(t.discard)) { this.$('device').value = this.entryId; return; }
      this.entryId = this.$('device').value; form.reset(); this.resetWord(); this.$('search').value = ''; this.notice(''); this.render();
    };
    this.$('word-cancel').onclick = () => this.resetWord();
    this.$('word-form').onsubmit = async event => {
      event.preventDefault();
      if (await this.request('word_save', {slot: this.wordSlot || null, original: this.wordOriginal ?? null,
        text: this.$('word-text').value})) this.resetWord();
    };
    this.$('add-form').onsubmit = async event => {
      event.preventDefault(); const form = event.currentTarget;
      if (await this.request('add', {name: form.elements.name.value, public_key: form.elements.public_key.value,
        kind: Number(form.elements.kind.value), favorite: form.elements.favorite.checked, allowed: form.elements.allowed.checked})) {
        form.reset(); this.notice(t.saved);
      }
    };
    for (const key of settings) {
      const label = this.node('label', undefined, 'check'), input = document.createElement('input');
      input.type = 'checkbox'; input.dataset.setting = key;
      input.onchange = () => {
        const enabled = input.checked;
        input.checked = !!this.selected?.settings[key];
        if (key === 'learn_allowed' && enabled && !window.confirm(t.allowWarning)) return;
        this.request('settings', {key, enabled});
      };
      label.append(input, document.createTextNode(t[key])); this.$('settings-form').append(label);
    }
    this.$('delete-cancel').onclick = () => this.$('delete-dialog').close();
    this.$('delete-confirm').onclick = async () => {
      const key = this.deleteKey; this.$('delete-dialog').close();
      if (await this.request('remove', {public_key: key, confirm: true})) this.notice(t.deleted);
    };
  }
  async request(action = 'state', values = {}) {
    if (this.busy || !this._hass) return false;
    const sequence = ++this.sequence;
    this.pendingMessages = [];
    this.busy = true; this.controls();
    try {
      const result = await this._hass.callWS({type: 'meshcore_connect/panel', action, entry_id: this.entryId, values});
      if (sequence !== this.sequence || !this.isConnected) return false;
      this.entries = result.entries.map(entry => ({...entry,
        messages: this.mergeMessages(entry.messages, this.pendingMessages.filter(message => message.entry_id === entry.entry_id))}));
      if (!this.selected) this.entryId = this.entries[0]?.entry_id || '';
      this.render();
      if (action !== 'state') this.notice(this.t.changed);
      return true;
    } catch (error) {
      if (sequence === this.sequence) this.notice(this.t[error.code] || this.t.error, true);
      return false;
    } finally {
      if (sequence === this.sequence) { this.busy = false; this.controls(); }
    }
  }
  controls() {
    const entry = this.selected;
    this.$('device').disabled = this.busy || !this.entries.length;
    this.$('refresh').disabled = this.busy || !entry?.connected;
    this.$('add-fields').disabled = this.busy || !entry?.connected;
    this.$('settings-fields').disabled = this.busy || !entry;
    this.$('word-fields').disabled = this.busy || !entry;
    this.shadowRoot.querySelectorAll('.word button').forEach(el => { el.disabled = this.busy || !entry; });
    this.shadowRoot.querySelectorAll('.contact button,.contact input').forEach(el => { el.disabled = this.busy || !entry?.connected; });
  }
  render() {
    const entry = this.selected;
    this.$('device').replaceChildren(...this.entries.map(e => new Option(e.name, e.entry_id)));
    this.$('device').value = this.entryId;
    this.$('no-device').hidden = !!entry;
    this.renderViews();
    this.$('status').textContent = entry ? this.t[entry.connected ? 'online' : 'offline'] : '';
    this.shadowRoot.querySelectorAll('[data-setting]').forEach(input => { input.checked = !!entry?.settings[input.dataset.setting]; });
    this.renderContacts(); this.renderWords(); this.renderMessages(); this.controls();
  }
  renderViews() {
    const present = !!this.selected;
    this.$('views').hidden = !present;
    this.$('cards').hidden = !present || !['contacts', 'settings'].includes(this.view);
    this.$('activity').hidden = !present || !['commands', 'messages'].includes(this.view);
    this.$('cards').classList.toggle('settings-view', this.view === 'settings');
    this.$('add-card').hidden = this.view !== 'contacts';
    for (const tab of this.$('views').children) {
      const active = tab.dataset.view === this.view;
      tab.setAttribute('aria-selected', String(active)); tab.tabIndex = active ? 0 : -1;
      this.$(tab.dataset.view + '-card').hidden = !active;
    }
  }
  resetWord() {
    this.wordSlot = null; this.wordOriginal = null; this.$('word-form').reset(); this.$('word-cancel').hidden = true;
  }
  renderWords() {
    const t = this.t, words = Object.entries(this.selected?.words || {});
    this.$('words').replaceChildren(...words.map(([slot, text]) => {
      const row = this.node('div', undefined, 'word'); row.append(this.node('span', text));
      for (const [icon, label, action] of [
        ['pencil', t.edit, () => {
          if (this.$('word-text').value && !window.confirm(t.discard)) return;
          this.wordSlot = slot; this.wordOriginal = text; this.$('word-text').value = text;
          this.$('word-cancel').hidden = false; this.$('word-text').focus();
        }],
        ['delete', t.commandRemove, async () => {
          if (!window.confirm(t.commandDeleteWarning + '\n\n' + text)) return;
          if (await this.request('word_remove', {slot, original: text, confirm: true}) && this.wordSlot === slot) this.resetWord();
        }],
      ]) {
        const button = this.node('button', undefined, 'icon' + (icon === 'delete' ? ' danger' : ''));
        button.title = label; button.setAttribute('aria-label', label + ': ' + text);
        button.append(this.icon(icon)); button.onclick = action; row.append(button);
      }
      return row;
    }));
    if (!words.length) this.$('words').append(this.node('p', t.noCommands, 'empty muted'));
  }
  renderMessages() {
    const t = this.t, messages = [...(this.selected?.messages || [])].reverse();
    const signature = this.entryId + ':' + messages.map(m => m.id).join(',');
    if (this.messageSignature === signature) return;
    this.messageSignature = signature;
    this.$('messages').replaceChildren(...messages.map(message => {
      const row = this.node('div', undefined, 'message'), head = this.node('div', undefined, 'message-head muted');
      const timestamp = new Date(message.received_at * 1000);
      const time = this.node('time', timestamp.toLocaleString(this._hass.locale?.language || this._hass.language));
      time.dateTime = timestamp.toISOString();
      head.append(time, this.node('strong', message.sender || t.unknown),
        this.node('span', message.kind === 'channel' ? t.channel + ' ' + message.channel_idx : t.direct));
      row.append(head, this.node('p', message.text)); return row;
    }));
    if (!messages.length) this.$('messages').append(this.node('p', t.noMessages, 'empty muted'));
  }
  renderContacts() {
    const t = this.t, entry = this.selected, all = entry?.contacts || [], query = this.$('search').value.toLocaleLowerCase().trim();
    const contacts = all.filter(c => c.name.toLocaleLowerCase().includes(query) || c.public_key.includes(query))
      .sort((a, b) => a.name.localeCompare(b.name));
    this.$('count').textContent = query ? contacts.length + ' / ' + all.length : String(all.length);
    this.$('contacts').replaceChildren(...contacts.map(contact => {
      const row = this.node('div', undefined, 'contact'), head = this.node('div', undefined, 'contact-head');
      head.append(this.node('strong', contact.name), this.node('span', ({1: t.companion, 2: t.repeater, 3: t.room})[contact.type] || '', 'kind'));
      const remove = this.node('button', undefined, 'icon danger'); remove.title = t.remove; remove.setAttribute('aria-label', t.remove + ': ' + contact.name);
      remove.append(this.icon('delete'));
      remove.onclick = () => {
        this.deleteKey = contact.public_key; this.$('delete-name').textContent = contact.name; this.$('delete-key').textContent = contact.public_key;
        this.$('delete-dialog').showModal(); this.$('delete-cancel').focus();
      };
      head.append(remove); row.append(head, this.node('code', contact.public_key));
      const flags = this.node('div', undefined, 'contact-flags');
      for (const key of ['favorite', 'allowed']) {
        const label = this.node('label', undefined, 'check'), input = document.createElement('input');
        input.type = 'checkbox'; input.checked = contact[key]; input.setAttribute('aria-label', t[key] + ': ' + contact.name);
        input.onchange = () => { const enabled = input.checked; input.checked = contact[key]; this.request(key, {public_key: contact.public_key, enabled}); };
        label.append(input, document.createTextNode(t[key])); flags.append(label);
      }
      row.append(flags); return row;
    }));
    if (!contacts.length) this.$('contacts').append(this.node('p', all.length ? t.noMatch : t.empty, 'empty muted'));
    this.controls();
  }
}
if (!customElements.get('meshcore-connect-panel')) customElements.define('meshcore-connect-panel', MeshCoreConnectPanel);
