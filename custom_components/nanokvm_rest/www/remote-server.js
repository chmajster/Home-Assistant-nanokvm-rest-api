const css = `
  :host { display:block; min-height:100%; background:var(--primary-background-color); color:var(--primary-text-color); }
  * { box-sizing:border-box; }
  .page { max-width:1180px; margin:0 auto; padding:24px; }
  .header { display:flex; gap:16px; align-items:flex-end; justify-content:space-between; margin-bottom:20px; flex-wrap:wrap; }
  h1 { font-size:28px; margin:0 0 4px; }
  .muted { color:var(--secondary-text-color); font-size:14px; }
  .selector { display:flex; gap:10px; align-items:center; flex-wrap:wrap; }
  select,input[type=text],input[type=file] { background:var(--card-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); border-radius:10px; padding:10px 12px; }
  select { min-width:260px; }
  .grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:16px; }
  .card { background:var(--card-background-color); border:1px solid var(--divider-color); border-radius:14px; padding:18px; box-shadow:var(--ha-card-box-shadow,none); }
  .wide { grid-column:1/-1; }
  .card h2 { font-size:18px; margin:0 0 14px; }
  .status-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:10px; }
  .metric { border:1px solid var(--divider-color); border-radius:10px; padding:12px; }
  .metric b { display:block; margin-top:4px; }
  .ok { color:var(--success-color,#2e7d32); }
  .bad { color:var(--error-color,#c62828); }
  .actions { display:flex; gap:8px; flex-wrap:wrap; }
  button,a.btn { border:0; border-radius:10px; padding:10px 13px; cursor:pointer; font-weight:600; text-decoration:none; background:var(--primary-color); color:var(--text-primary-color,#fff); }
  button.secondary,a.secondary { background:var(--secondary-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); }
  button.danger { background:var(--error-color,#c62828); color:#fff; }
  button:disabled { opacity:.5; cursor:not-allowed; }
  .media-row { display:grid; grid-template-columns:minmax(220px,1fr) auto; gap:10px; align-items:center; margin:10px 0; }
  .media-row select { min-width:0; width:100%; }
  .notice { margin:0 0 16px; border-radius:10px; padding:12px 14px; display:none; }
  .notice.show { display:block; }
  .notice.error { background:color-mix(in srgb,var(--error-color,#c62828) 15%,transparent); }
  .notice.success { background:color-mix(in srgb,var(--success-color,#2e7d32) 15%,transparent); }
  .update-form { display:grid; grid-template-columns:1fr 1fr auto; gap:10px; align-items:end; }
  label { display:flex; flex-direction:column; gap:6px; font-size:13px; color:var(--secondary-text-color); }
  .empty { text-align:center; padding:52px 20px; }
  @media (max-width:760px) { .page{padding:16px}.grid{grid-template-columns:1fr}.status-grid{grid-template-columns:1fr 1fr}.update-form{grid-template-columns:1fr}.wide{grid-column:auto}.media-row{grid-template-columns:1fr} }
`;

const translations = {
  pl: {
    subtitle: "Centralny panel zarządzania wieloma NanoKVM",
    device: "NanoKVM",
    manage: "Zarządzaj KVM",
    noDevices: "Brak skonfigurowanych NanoKVM.",
    status: "Status",
    available: "Dostępność",
    power: "Zasilanie hosta",
    hdmi: "Sygnał HDMI",
    online: "Online",
    offline: "Offline",
    on: "Włączony",
    off: "Wyłączony",
    unknown: "Brak danych",
    controls: "Sterowanie hostem",
    powerOn: "Włącz",
    powerPress: "Power",
    reset: "Reset",
    forceOff: "Wymuś wyłączenie",
    kvm: "NanoKVM / HID",
    hidReset: "Reset HID",
    rebootKvm: "Restart NanoKVM",
    openUi: "Otwórz panel NanoKVM",
    media: "Virtual Media / ISO",
    mounted: "Zamontowany obraz",
    mode: "Tryb",
    images: "Dostępne obrazy",
    mountCdrom: "Montuj jako CD-ROM",
    mountDisk: "Montuj jako USB disk",
    unmount: "Odłącz",
    delete: "Usuń obraz",
    changeMode: "Zmień tryb",
    cdrom: "CD-ROM (read-only)",
    disk: "USB disk",
    none: "Brak",
    offlineUpdate: "Offline update",
    package: "Pakiet nanokvm_X.Y.Z.tar.gz",
    checksum: "SHA-256 (opcjonalnie)",
    upload: "Wyślij i zaktualizuj",
    refresh: "Odśwież",
    adminRequired: "Ta funkcja wymaga konta administratora NanoKVM.",
    working: "Wykonywanie operacji...",
    uploaded: "Pakiet został przekazany do NanoKVM. Urządzenie może się teraz restartować.",
  },
  en: {
    subtitle: "Central management panel for multiple NanoKVM devices",
    device: "NanoKVM",
    manage: "Manage KVM devices",
    noDevices: "No NanoKVM devices are configured.",
    status: "Status",
    available: "Availability",
    power: "Host power",
    hdmi: "HDMI signal",
    online: "Online",
    offline: "Offline",
    on: "On",
    off: "Off",
    unknown: "Unknown",
    controls: "Host controls",
    powerOn: "Power on",
    powerPress: "Power",
    reset: "Reset",
    forceOff: "Force off",
    kvm: "NanoKVM / HID",
    hidReset: "Reset HID",
    rebootKvm: "Reboot NanoKVM",
    openUi: "Open NanoKVM UI",
    media: "Virtual Media / ISO",
    mounted: "Mounted image",
    mode: "Mode",
    images: "Available images",
    mountCdrom: "Mount as CD-ROM",
    mountDisk: "Mount as USB disk",
    unmount: "Unmount",
    delete: "Delete image",
    changeMode: "Change mode",
    cdrom: "CD-ROM (read-only)",
    disk: "USB disk",
    none: "None",
    offlineUpdate: "Offline update",
    package: "Package nanokvm_X.Y.Z.tar.gz",
    checksum: "SHA-256 (optional)",
    upload: "Upload and update",
    refresh: "Refresh",
    adminRequired: "This function requires a NanoKVM administrator account.",
    working: "Operation in progress...",
    uploaded: "The package was accepted by NanoKVM. The device may now restart.",
  },
};

class NanoKVMRemoteServerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._devices = [];
    this._status = null;
    this._selected = localStorage.getItem("nanokvm-remote-selected") || "";
    this._notice = null;
    this._busy = false;
  }

  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first) this._load();
  }

  set panel(_) {}
  set route(_) {}
  set narrow(_) {}

  get t() {
    const lang = (this._hass?.language || "en").toLowerCase().startsWith("pl") ? "pl" : "en";
    return translations[lang];
  }

  async _load() {
    if (!this._hass) return;
    try {
      const data = await this._hass.callWS({ type: "nanokvm_rest/panel/list" });
      this._devices = data.devices || [];
      if (!this._devices.some((item) => item.entry_id === this._selected)) {
        this._selected = this._devices[0]?.entry_id || "";
      }
      if (this._selected) localStorage.setItem("nanokvm-remote-selected", this._selected);
      await this._loadStatus(false);
    } catch (err) {
      this._setNotice(this._errorText(err), true);
      this._render();
    }
  }

  async _loadStatus(renderFirst = true) {
    if (!this._selected || !this._hass) {
      this._status = null;
      this._render();
      return;
    }
    if (renderFirst) {
      this._busy = true;
      this._render();
    }
    try {
      this._status = await this._hass.callWS({
        type: "nanokvm_rest/panel/status",
        entry_id: this._selected,
      });
    } catch (err) {
      this._setNotice(this._errorText(err), true);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _action(action, extra = {}) {
    if (!this._selected || this._busy) return;
    this._busy = true;
    this._setNotice(this.t.working, false);
    this._render();
    try {
      await this._hass.callWS({
        type: "nanokvm_rest/panel/action",
        entry_id: this._selected,
        action,
        ...extra,
      });
      this._notice = null;
      await this._loadStatus(false);
    } catch (err) {
      this._busy = false;
      this._setNotice(this._errorText(err), true);
      this._render();
    }
  }

  async _offlineUpdate() {
    const file = this.shadowRoot.querySelector("#update-file")?.files?.[0];
    const checksum = this.shadowRoot.querySelector("#checksum")?.value?.trim() || "";
    if (!file || !this._selected || this._busy) return;
    this._busy = true;
    this._setNotice(this.t.working, false);
    this._render();
    const form = new FormData();
    form.append("file", file);
    const headers = { Authorization: `Bearer ${this._hass.auth.accessToken}` };
    if (checksum) headers["X-SHA256-Checksum"] = checksum;
    try {
      const response = await fetch(`/api/nanokvm_rest/offline-update/${encodeURIComponent(this._selected)}`, {
        method: "POST",
        headers,
        body: form,
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      this._setNotice(this.t.uploaded, false, true);
    } catch (err) {
      this._setNotice(this._errorText(err), true);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  _setNotice(text, error = false, success = false) {
    this._notice = { text, error, success };
  }

  _errorText(err) {
    return err?.message || err?.error?.message || String(err);
  }

  _escape(value) {
    return String(value ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]);
  }

  _basename(value) {
    const bits = String(value || "").split("/");
    return bits[bits.length - 1] || value;
  }

  _bool(value, yes, no) {
    return value === true ? yes : value === false ? no : this.t.unknown;
  }

  _render() {
    const t = this.t;
    const selectedDevice = this._devices.find((item) => item.entry_id === this._selected);
    const status = this._status;
    const media = status?.media || { files: [], mounted: "", cdrom: false };
    const options = this._devices.map((item) => `<option value="${this._escape(item.entry_id)}" ${item.entry_id === this._selected ? "selected" : ""}>${this._escape(item.title)}${item.available === false ? " — offline" : ""}</option>`).join("");
    const imageOptions = media.files.map((file) => `<option value="${this._escape(file)}">${this._escape(this._basename(file))}</option>`).join("");
    const noticeClass = this._notice ? `notice show ${this._notice.error ? "error" : this._notice.success ? "success" : ""}` : "notice";

    this.shadowRoot.innerHTML = `<style>${css}</style><div class="page">
      <div class="header">
        <div><h1>Remote Server</h1><div class="muted">${t.subtitle}</div></div>
        <div class="selector">
          <select id="device-select" ${this._busy ? "disabled" : ""}>${options}</select>
          <button class="secondary" id="refresh" ${!this._selected || this._busy ? "disabled" : ""}>${t.refresh}</button>
          <a class="btn secondary" href="/config/integrations/integration/nanokvm_rest">${t.manage}</a>
        </div>
      </div>
      <div class="${noticeClass}">${this._escape(this._notice?.text || "")}</div>
      ${!this._devices.length ? `<div class="card empty">${t.noDevices}</div>` : !status ? `<div class="card empty">${this._busy ? t.working : t.offline}</div>` : `
      <div class="grid">
        <section class="card wide"><h2>${t.status}</h2><div class="status-grid">
          <div class="metric">${t.device}<b>${this._escape(status.hostname || selectedDevice?.title || "NanoKVM")}</b></div>
          <div class="metric">${t.available}<b class="${status.available ? "ok" : "bad"}">${status.available ? t.online : t.offline}</b></div>
          <div class="metric">${t.power}<b>${this._bool(status.power, t.on, t.off)}</b></div>
          <div class="metric">${t.hdmi}<b>${this._bool(status.hdmi_signal, t.on, t.off)}</b></div>
          <div class="metric">Hardware<b>${this._escape(status.hardware || t.unknown)}</b></div>
          <div class="metric">NanoKVM app<b>${this._escape(status.application_version || t.unknown)}</b></div>
        </div></section>

        <section class="card"><h2>${t.controls}</h2><div class="actions">
          <button data-action="power_on" ${this._busy ? "disabled" : ""}>${t.powerOn}</button>
          <button data-action="power_press" class="secondary" ${this._busy ? "disabled" : ""}>${t.powerPress}</button>
          <button data-action="reset" class="secondary" ${this._busy ? "disabled" : ""}>${t.reset}</button>
          <button data-action="force_off" class="danger" ${this._busy ? "disabled" : ""}>${t.forceOff}</button>
        </div></section>

        <section class="card"><h2>${t.kvm}</h2>
          ${status.admin ? `<div class="actions"><button data-action="reset_hid" ${this._busy ? "disabled" : ""}>${t.hidReset}</button><button data-action="reboot_nanokvm" class="danger" ${this._busy ? "disabled" : ""}>${t.rebootKvm}</button><a class="btn secondary" href="${this._escape(status.base_url)}" target="_blank" rel="noreferrer">${t.openUi}</a></div>` : `<div class="muted">${t.adminRequired}</div>`}
        </section>

        <section class="card wide"><h2>${t.media}</h2>
          ${status.admin ? `<div class="status-grid"><div class="metric">${t.mounted}<b>${this._escape(media.mounted ? this._basename(media.mounted) : t.none)}</b></div><div class="metric">${t.mode}<b>${media.mounted ? (media.cdrom ? t.cdrom : t.disk) : t.none}</b></div><div class="metric">${t.images}<b>${media.files.length}</b></div></div>
          <div class="media-row"><select id="image-select" ${!media.files.length || this._busy ? "disabled" : ""}>${imageOptions}</select><div class="actions"><button id="mount-cdrom" ${!media.files.length || this._busy ? "disabled" : ""}>${t.mountCdrom}</button><button id="mount-disk" class="secondary" ${!media.files.length || this._busy ? "disabled" : ""}>${t.mountDisk}</button></div></div>
          <div class="actions"><button data-action="unmount_image" class="secondary" ${!media.mounted || this._busy ? "disabled" : ""}>${t.unmount}</button><button id="toggle-mode" class="secondary" ${!media.mounted || this._busy ? "disabled" : ""}>${t.changeMode}</button><button id="delete-image" class="danger" ${!media.files.length || this._busy ? "disabled" : ""}>${t.delete}</button></div>` : `<div class="muted">${t.adminRequired}</div>`}
        </section>

        <section class="card wide"><h2>${t.offlineUpdate}</h2>
          ${status.admin ? `<div class="update-form"><label>${t.package}<input id="update-file" type="file" accept=".tar.gz" ${this._busy ? "disabled" : ""}></label><label>${t.checksum}<input id="checksum" type="text" maxlength="64" placeholder="SHA-256" ${this._busy ? "disabled" : ""}></label><button id="offline-update" ${this._busy ? "disabled" : ""}>${t.upload}</button></div>` : `<div class="muted">${t.adminRequired}</div>`}
        </section>
      </div>`}
    </div>`;

    this.shadowRoot.querySelector("#device-select")?.addEventListener("change", async (event) => {
      this._selected = event.target.value;
      localStorage.setItem("nanokvm-remote-selected", this._selected);
      this._status = null;
      await this._loadStatus();
    });
    this.shadowRoot.querySelector("#refresh")?.addEventListener("click", () => this._loadStatus());
    this.shadowRoot.querySelectorAll("[data-action]").forEach((button) => button.addEventListener("click", () => this._action(button.dataset.action)));
    this.shadowRoot.querySelector("#mount-cdrom")?.addEventListener("click", () => this._mount(true));
    this.shadowRoot.querySelector("#mount-disk")?.addEventListener("click", () => this._mount(false));
    this.shadowRoot.querySelector("#toggle-mode")?.addEventListener("click", () => this._action("set_cdrom", { cdrom: !media.cdrom }));
    this.shadowRoot.querySelector("#delete-image")?.addEventListener("click", () => {
      const image = this.shadowRoot.querySelector("#image-select")?.value;
      if (image) this._action("delete_image", { image });
    });
    this.shadowRoot.querySelector("#offline-update")?.addEventListener("click", () => this._offlineUpdate());
  }

  _mount(cdrom) {
    const image = this.shadowRoot.querySelector("#image-select")?.value;
    if (image) this._action("mount_image", { image, cdrom });
  }
}

if (!customElements.get("nanokvm-remote-server-panel")) {
  customElements.define("nanokvm-remote-server-panel", NanoKVMRemoteServerPanel);
}
