const translations = {
  de: {
    contacts: 'Kontakte', add: 'Kontakt hinzufügen', settings: 'Einstellungen', device: 'Companion',
    search: 'Name oder Public Key', name: 'Name', key: 'Public Key', kind: 'Gerätetyp',
    favorite: 'Favorit', allowed: 'HA-Aktionen erlaubt', save: 'Kontakt speichern', refresh: 'Aktualisieren',
    remove: 'Kontakt löschen', cancel: 'Abbrechen', online: 'Verbunden', offline: 'Nicht verbunden',
    empty: 'Keine Kontakte.', noMatch: 'Keine passenden Kontakte.', noDevice: 'Keine geladene MeshCore-Connect-Integration.',
    companion: 'Companion', repeater: 'Repeater', room: 'Raumserver',
    deleteWarning: 'Dieser Kontakt wird gelöscht. Seine Favoritenmarkierung und HA-Freigabe werden ebenfalls entfernt.',
    discard: 'Eingaben für den neuen Kontakt verwerfen und Companion wechseln?',
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
  },
  en: {
    contacts: 'Contacts', add: 'Add contact', settings: 'Settings', device: 'Companion', search: 'Name or public key',
    name: 'Name', key: 'Public key', kind: 'Device type', favorite: 'Favorite', allowed: 'HA actions allowed',
    save: 'Save contact', refresh: 'Refresh', remove: 'Delete contact', cancel: 'Cancel', online: 'Connected',
    offline: 'Disconnected', empty: 'No contacts.', noMatch: 'No matching contacts.', noDevice: 'No loaded MeshCore Connect integration.',
    companion: 'Companion', repeater: 'Repeater', room: 'Room server',
    deleteWarning: 'This contact will be deleted, including its favorite status and HA action permission.',
    discard: 'Discard the new contact draft and switch companions?',
    allowWarning: 'Newly learned, previously unknown contacts will be allowed to trigger HA actions. Enable?',
    saved: 'Contact saved.', deleted: 'Contact deleted.', changed: 'Saved.',
    learn_contacts: 'Learn contacts automatically', learn_repeaters: 'Learn repeaters automatically',
    learn_favorites: 'Save automatically learned contacts as favorites', learn_allowed: 'Allow HA actions for automatically learned contacts',
    action_responses: 'Send action confirmations', device_error: 'The device did not confirm the change. Check the connection and contact list.',
    invalid_contact: 'Check the input. The contact may have changed.', contact_exists: 'This public key is already saved.',
    invalid_key: 'Public key: 64 hexadecimal characters required.', invalid_contact_name: 'Name: 1 to 31 UTF-8 bytes required.',
    not_loaded: 'This integration is not loaded.', error: 'Request failed. Please check again.', menu: 'Open sidebar',
  },
  fr: {
    contacts: 'Contacts', add: 'Ajouter un contact', settings: 'Paramètres', device: 'Compagnon', search: 'Nom ou clé publique',
    name: 'Nom', key: 'Clé publique', kind: "Type d'appareil", favorite: 'Favori', allowed: 'Actions HA autorisées',
    save: 'Enregistrer le contact', refresh: 'Actualiser', remove: 'Supprimer le contact', cancel: 'Annuler', online: 'Connecté',
    offline: 'Déconnecté', empty: 'Aucun contact.', noMatch: 'Aucun contact correspondant.', noDevice: 'Aucune intégration MeshCore Connect chargée.',
    companion: 'Compagnon', repeater: 'Répéteur', room: 'Serveur de salon',
    deleteWarning: 'Ce contact sera supprimé, ainsi que son statut de favori et son autorisation pour les actions HA.',
    discard: 'Abandonner la saisie du nouveau contact et changer de compagnon ?',
    allowWarning: 'Les nouveaux contacts appris pourront déclencher des actions HA. Activer ?',
    saved: 'Contact enregistré.', deleted: 'Contact supprimé.', changed: 'Enregistré.',
    learn_contacts: 'Apprendre les contacts automatiquement', learn_repeaters: 'Apprendre les répéteurs automatiquement',
    learn_favorites: 'Enregistrer les contacts appris comme favoris', learn_allowed: 'Autoriser les actions HA pour les contacts appris',
    action_responses: "Envoyer les confirmations d'action", device_error: "L'appareil n'a pas confirmé. Vérifier la connexion et les contacts.",
    invalid_contact: 'Vérifier la saisie. Le contact peut avoir changé.', contact_exists: 'Cette clé publique est déjà enregistrée.',
    invalid_key: 'Clé publique : 64 caractères hexadécimaux requis.', invalid_contact_name: 'Nom : 1 à 31 octets UTF-8 requis.',
    not_loaded: "Cette intégration n'est pas chargée.", error: 'Échec de la demande. Vérifier à nouveau.', menu: 'Ouvrir le menu',
  },
};
const settings = ['learn_contacts', 'learn_repeaters', 'learn_favorites', 'learn_allowed', 'action_responses'];

class MeshCoreConnectPanel extends HTMLElement {
  constructor() {
    super(); this.attachShadow({mode: 'open'}); this.entries = []; this.entryId = ''; this.busy = false; this.sequence = 0;
  }
  set hass(value) {
    this._hass = value;
    if (!this.ready) { this.mount(); if (this.isConnected) this.start(); }
  }
  connectedCallback() { if (this.ready) this.start(); }
  disconnectedCallback() { clearInterval(this.timer); this.timer = null; this.sequence++; this.busy = false; }
  start() {
    if (this.timer) return;
    this.request();
    this.timer = setInterval(() => {
      if (!document.hidden && !this.busy && !this.$('delete-dialog').open) this.request();
    }, 15000);
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
      <header><button id="menu" class="icon" title="${t.menu}" aria-label="${t.menu}"><ha-icon icon="mdi:menu"></ha-icon></button><img src="/meshcore_connect_panel/logo.png" alt=""><h1>MeshCore Connect</h1></header>
      <main><div class="toolbar"><label>${t.device}<select id="device"></select></label><span id="status" class="status muted"></span><button id="refresh" title="${t.refresh}" aria-label="${t.refresh}" class="icon"><ha-icon icon="mdi:refresh"></ha-icon></button></div>
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
      </div></main>
      <dialog id="delete-dialog" aria-labelledby="delete-title"><h2 id="delete-title">${t.remove}</h2><p><strong id="delete-name"></strong></p><code id="delete-key"></code><p>${t.deleteWarning}</p><div class="dialog-actions"><button id="delete-cancel">${t.cancel}</button><button id="delete-confirm" class="danger"><ha-icon icon="mdi:delete"></ha-icon>${t.remove}</button></div></dialog>`;
    this.ready = true;
    this.$('menu').onclick = () => this.dispatchEvent(new Event('hass-toggle-menu', {bubbles: true, composed: true}));
    this.$('refresh').onclick = () => this.request('refresh');
    this.$('search').oninput = () => this.renderContacts();
    this.$('device').onchange = () => {
      const form = this.$('add-form');
      const dirty = form.elements.name.value || form.elements.public_key.value || form.elements.favorite.checked || form.elements.allowed.checked || form.elements.kind.value !== '1';
      if (dirty && !window.confirm(t.discard)) { this.$('device').value = this.entryId; return; }
      this.entryId = this.$('device').value; form.reset(); this.$('search').value = ''; this.notice(''); this.render();
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
    this.busy = true; this.controls();
    try {
      const result = await this._hass.callWS({type: 'meshcore_connect/panel', action, entry_id: this.entryId, values});
      if (sequence !== this.sequence || !this.isConnected) return false;
      this.entries = result.entries;
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
    this.shadowRoot.querySelectorAll('.contact button,.contact input').forEach(el => { el.disabled = this.busy || !entry?.connected; });
  }
  render() {
    const entry = this.selected;
    this.$('device').replaceChildren(...this.entries.map(e => new Option(e.name, e.entry_id)));
    this.$('device').value = this.entryId;
    this.$('no-device').hidden = !!entry; this.$('cards').hidden = !entry;
    this.$('status').textContent = entry ? this.t[entry.connected ? 'online' : 'offline'] : '';
    this.shadowRoot.querySelectorAll('[data-setting]').forEach(input => { input.checked = !!entry?.settings[input.dataset.setting]; });
    this.renderContacts(); this.controls();
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
