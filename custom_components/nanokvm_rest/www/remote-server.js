const css = `
  :host {
    display:block;
    min-height:100%;
    background:var(--primary-background-color);
    color:var(--primary-text-color);
    font-family:var(--paper-font-body1_-_font-family,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif);
  }
  * { box-sizing:border-box; }
  button,input,select { font:inherit; }
  button { cursor:pointer; }
  button:disabled { cursor:not-allowed; opacity:.48; }
  a { color:inherit; }

  .shell { min-height:100vh; display:grid; grid-template-columns:280px minmax(0,1fr); }
  .rail {
    border-right:1px solid var(--divider-color);
    background:var(--sidebar-background-color,var(--card-background-color));
    padding:18px 14px;
    position:sticky;
    top:0;
    height:100vh;
    overflow:auto;
  }
  .brand { display:flex; align-items:center; gap:12px; padding:4px 6px 16px; }
  .brand-icon {
    width:42px; height:42px; border-radius:12px; display:grid; place-items:center;
    background:color-mix(in srgb,var(--primary-color) 16%,transparent);
    color:var(--primary-color); font-size:22px; font-weight:800;
  }
  .brand h1 { margin:0; font-size:20px; line-height:1.15; }
  .muted { color:var(--secondary-text-color); }
  .tiny { font-size:12px; }
  .rail-summary { display:grid; grid-template-columns:repeat(3,1fr); gap:7px; margin:4px 0 14px; }
  .rail-stat {
    border:1px solid var(--divider-color); border-radius:10px; padding:9px 7px;
    text-align:center; background:var(--primary-background-color);
  }
  .rail-stat b { display:block; font-size:16px; }
  .device-list { display:flex; flex-direction:column; gap:7px; }
  .device-item {
    width:100%; text-align:left; border:1px solid transparent; border-radius:12px;
    padding:11px; background:transparent; color:var(--primary-text-color);
    display:grid; grid-template-columns:10px minmax(0,1fr) auto; gap:9px; align-items:center;
  }
  .device-item:hover { background:var(--secondary-background-color); }
  .device-item.active {
    background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color));
    border-color:color-mix(in srgb,var(--primary-color) 38%,var(--divider-color));
  }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--disabled-color,#777); }
  .dot.online { background:var(--success-color,#2e7d32); }
  .dot.offline { background:var(--error-color,#c62828); }
  .device-name { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-weight:650; }
  .device-meta { font-size:11px; color:var(--secondary-text-color); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .power-pill { font-size:10px; border-radius:999px; padding:3px 6px; background:var(--secondary-background-color); }
  .rail-actions { display:flex; gap:7px; margin-top:14px; }

  .main { min-width:0; padding:22px; }
  .topbar {
    display:flex; justify-content:space-between; align-items:flex-start; gap:16px;
    margin:0 auto 16px; max-width:1320px;
  }
  .title-wrap h2 { margin:0 0 4px; font-size:25px; }
  .top-actions { display:flex; gap:8px; flex-wrap:wrap; justify-content:flex-end; }
  .btn, button.btn {
    border:0; border-radius:10px; padding:9px 12px; min-height:38px;
    background:var(--primary-color); color:var(--text-primary-color,#fff); font-weight:650;
    text-decoration:none; display:inline-flex; align-items:center; justify-content:center; gap:6px;
  }
  .btn.secondary { background:var(--secondary-background-color); color:var(--primary-text-color); border:1px solid var(--divider-color); }
  .btn.danger { background:var(--error-color,#c62828); color:#fff; }
  .btn.warning { background:var(--warning-color,#ef6c00); color:#fff; }

  .notice {
    display:none; max-width:1320px; margin:0 auto 14px; padding:11px 13px; border-radius:10px;
    border:1px solid var(--divider-color); background:var(--card-background-color);
  }
  .notice.show { display:block; }
  .notice.error { border-color:color-mix(in srgb,var(--error-color,#c62828) 50%,var(--divider-color)); background:color-mix(in srgb,var(--error-color,#c62828) 10%,var(--card-background-color)); }
  .notice.success { border-color:color-mix(in srgb,var(--success-color,#2e7d32) 50%,var(--divider-color)); background:color-mix(in srgb,var(--success-color,#2e7d32) 10%,var(--card-background-color)); }

  .tabs { max-width:1320px; margin:0 auto 14px; display:flex; gap:6px; overflow:auto; padding-bottom:2px; }
  .tab {
    border:1px solid var(--divider-color); background:var(--card-background-color); color:var(--primary-text-color);
    border-radius:999px; padding:8px 12px; white-space:nowrap;
  }
  .tab.active { background:var(--primary-color); color:var(--text-primary-color,#fff); border-color:var(--primary-color); }

  .content { max-width:1320px; margin:0 auto; }
  .grid { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:14px; }
  .card {
    grid-column:span 6; background:var(--card-background-color); border:1px solid var(--divider-color);
    border-radius:14px; padding:16px; box-shadow:var(--ha-card-box-shadow,none); min-width:0;
  }
  .card.full { grid-column:1/-1; }
  .card.third { grid-column:span 4; }
  .card h3 { margin:0 0 12px; font-size:17px; }
  .card-head { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:12px; }
  .card-head h3 { margin:0; }
  .metrics { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:9px; }
  .metric { border:1px solid var(--divider-color); border-radius:11px; padding:11px; min-width:0; }
  .metric span { display:block; color:var(--secondary-text-color); font-size:12px; margin-bottom:4px; }
  .metric b { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ok { color:var(--success-color,#2e7d32); }
  .bad { color:var(--error-color,#c62828); }
  .warn { color:var(--warning-color,#ef6c00); }
  .actions { display:flex; flex-wrap:wrap; gap:8px; }
  .section-text { color:var(--secondary-text-color); margin:0 0 12px; line-height:1.45; }

  .media-list { display:flex; flex-direction:column; gap:8px; }
  .media-item {
    border:1px solid var(--divider-color); border-radius:11px; padding:10px 11px;
    display:grid; grid-template-columns:minmax(0,1fr) auto; gap:10px; align-items:center;
  }
  .media-name { min-width:0; }
  .media-name b { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .media-name span { display:block; margin-top:2px; color:var(--secondary-text-color); font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .mounted { border-color:color-mix(in srgb,var(--primary-color) 45%,var(--divider-color)); background:color-mix(in srgb,var(--primary-color) 7%,var(--card-background-color)); }
  .media-actions { display:flex; flex-wrap:wrap; gap:6px; justify-content:flex-end; }
  .compact { padding:7px 9px !important; min-height:32px !important; font-size:12px; }

  .form-grid { display:grid; grid-template-columns:1fr 1fr auto; gap:10px; align-items:end; }
  label { display:flex; flex-direction:column; gap:5px; font-size:12px; color:var(--secondary-text-color); min-width:0; }
  input[type=text],input[type=file],select {
    width:100%; min-width:0; background:var(--primary-background-color); color:var(--primary-text-color);
    border:1px solid var(--divider-color); border-radius:9px; padding:9px 10px;
  }
  .native-wrap { min-height:460px; }
  .native-toolbar { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:12px; }
  iframe { width:100%; min-height:650px; border:1px solid var(--divider-color); border-radius:12px; background:#111; }
  .url { font-family:ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
  .empty { text-align:center; padding:54px 18px; }
  .busy-line { height:3px; background:transparent; overflow:hidden; position:sticky; top:0; z-index:5; }
  .busy-line.active::after { content:""; display:block; height:100%; width:35%; background:var(--primary-color); animation:slide 1s linear infinite; }
  @keyframes slide { from { transform:translateX(-110%); } to { transform:translateX(320%); } }

  @media (max-width:980px) {
    .shell { grid-template-columns:220px minmax(0,1fr); }
    .rail { padding:14px 10px; }
    .main { padding:16px; }
    .card,.card.third { grid-column:1/-1; }
    .metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .form-grid { grid-template-columns:1fr; }
  }
  @media (max-width:700px) {
    .shell { display:block; }
    .rail { position:static; height:auto; border-right:0; border-bottom:1px solid var(--divider-color); }
    .device-list { flex-direction:row; overflow:auto; padding-bottom:2px; }
    .device-item { min-width:210px; }
    .rail-summary,.rail-actions { display:none; }
    .main { padding:12px; }
    .topbar { align-items:stretch; flex-direction:column; }
    .top-actions { justify-content:flex-start; }
    .metrics { grid-template-columns:1fr 1fr; }
    .media-item { grid-template-columns:1fr; }
    .media-actions { justify-content:flex-start; }
  }
`;

const translations = {
  pl: {
    subtitle: "Webowy panel administracyjny wielu NanoKVM",
    all: "Wszystkie",
    online: "Online",
    hostsOn: "Host ON",
    noDevices: "Brak skonfigurowanych NanoKVM. Dodaj integrację NanoKVM REST w Ustawieniach.",
    refresh: "Odśwież",
    integrations: "Integracje",
    overview: "Przegląd",
    media: "Virtual Media",
    maintenance: "Serwis",
    native: "Natywny UI",
    availability: "Dostępność",
    hostPower: "Zasilanie hosta",
    hdmi: "HDMI",
    hardware: "Hardware",
    appVersion: "Wersja aplikacji",
    address: "Adres",
    on: "Włączony",
    off: "Wyłączony",
    yes: "Tak",
    no: "Nie",
    unknown: "Brak danych",
    powerControls: "Sterowanie hostem",
    powerText: "Sterowanie fizycznymi liniami Power/Reset przez wybrany NanoKVM.",
    powerOn: "Włącz host",
    powerPress: "Power",
    reset: "Reset hosta",
    forceOff: "Wymuś OFF",
    kvmControls: "Sterowanie NanoKVM",
    hidReset: "Reset HID",
    rebootKvm: "Restart NanoKVM",
    openNative: "Otwórz NanoKVM",
    mountedImage: "Zamontowany obraz",
    mode: "Tryb",
    cdrom: "CD-ROM",
    disk: "USB disk",
    unmount: "Odłącz",
    changeToCdrom: "Ustaw CD-ROM",
    changeToDisk: "Ustaw USB disk",
    availableImages: "Dostępne obrazy ISO / IMG",
    mountCdrom: "Montuj CD-ROM",
    mountDisk: "Montuj disk",
    delete: "Usuń",
    noImages: "NanoKVM nie zwrócił żadnych obrazów ISO/IMG.",
    adminRequired: "Ta funkcja wymaga konta administratora NanoKVM.",
    offlineUpdate: "Offline update",
    updateText: "Wgraj lokalny pakiet nanokvm_X.Y.Z.tar.gz bez korzystania z internetowego serwera aktualizacji.",
    package: "Pakiet aktualizacji",
    checksum: "SHA-256 (opcjonalnie)",
    upload: "Wyślij i zaktualizuj",
    nativeTitle: "Natywny interfejs NanoKVM",
    nativeText: "Panel poniżej próbuje osadzić oryginalny interfejs wybranego NanoKVM. Jeżeli urządzenie blokuje iframe albo Home Assistant działa po HTTPS, a KVM po HTTP, użyj przycisku otwierającego UI w nowej karcie.",
    embed: "Pokaż w panelu",
    hideEmbed: "Ukryj osadzony UI",
    copyAddress: "Kopiuj adres",
    copied: "Adres skopiowany.",
    mixedContent: "Przeglądarka zablokuje osadzanie HTTP wewnątrz Home Assistant działającego po HTTPS. Otwórz NanoKVM w nowej karcie.",
    working: "Wykonywanie operacji…",
    uploaded: "Pakiet został przekazany do NanoKVM. Urządzenie może się teraz restartować.",
    confirmReset: "Zresetować host przez linię RESET?",
    confirmForce: "Wymusić wyłączenie hosta długim naciśnięciem POWER?",
    confirmReboot: "Zrestartować samo urządzenie NanoKVM?",
    confirmDelete: "Usunąć wybrany obraz z pamięci NanoKVM?",
    confirmUpdate: "Rozpocząć offline update wybranego NanoKVM?",
  },
  en: {
    subtitle: "Web administration panel for multiple NanoKVM devices",
    all: "All",
    online: "Online",
    hostsOn: "Hosts ON",
    noDevices: "No NanoKVM devices are configured. Add NanoKVM REST in Settings.",
    refresh: "Refresh",
    integrations: "Integrations",
    overview: "Overview",
    media: "Virtual Media",
    maintenance: "Maintenance",
    native: "Native UI",
    availability: "Availability",
    hostPower: "Host power",
    hdmi: "HDMI",
    hardware: "Hardware",
    appVersion: "Application version",
    address: "Address",
    on: "On",
    off: "Off",
    yes: "Yes",
    no: "No",
    unknown: "Unknown",
    powerControls: "Host controls",
    powerText: "Control physical Power/Reset lines through the selected NanoKVM.",
    powerOn: "Power on host",
    powerPress: "Power",
    reset: "Reset host",
    forceOff: "Force OFF",
    kvmControls: "NanoKVM controls",
    hidReset: "Reset HID",
    rebootKvm: "Reboot NanoKVM",
    openNative: "Open NanoKVM",
    mountedImage: "Mounted image",
    mode: "Mode",
    cdrom: "CD-ROM",
    disk: "USB disk",
    unmount: "Unmount",
    changeToCdrom: "Set CD-ROM",
    changeToDisk: "Set USB disk",
    availableImages: "Available ISO / IMG images",
    mountCdrom: "Mount CD-ROM",
    mountDisk: "Mount disk",
    delete: "Delete",
    noImages: "NanoKVM did not return any ISO/IMG images.",
    adminRequired: "This function requires a NanoKVM administrator account.",
    offlineUpdate: "Offline update",
    updateText: "Upload a local nanokvm_X.Y.Z.tar.gz package without using the online update server.",
    package: "Update package",
    checksum: "SHA-256 (optional)",
    upload: "Upload and update",
    nativeTitle: "Native NanoKVM interface",
    nativeText: "The panel below can embed the original UI of the selected NanoKVM. If the device blocks iframes, or Home Assistant uses HTTPS while the KVM uses HTTP, open the UI in a new tab instead.",
    embed: "Show in panel",
    hideEmbed: "Hide embedded UI",
    copyAddress: "Copy address",
    copied: "Address copied.",
    mixedContent: "The browser will block HTTP content inside Home Assistant served over HTTPS. Open NanoKVM in a new tab.",
    working: "Operation in progress…",
    uploaded: "The package was accepted by NanoKVM. The device may now restart.",
    confirmReset: "Reset the host through the RESET line?",
    confirmForce: "Force the host off with a long POWER press?",
    confirmReboot: "Reboot the NanoKVM device itself?",
    confirmDelete: "Delete the selected image from NanoKVM storage?",
    confirmUpdate: "Start an offline update on the selected NanoKVM?",
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
    this._view = localStorage.getItem("nanokvm-remote-view") || "overview";
    this._notice = null;
    this._busy = false;
    this._embedNative = false;
    this._pollTimer = null;
    this._listTick = 0;
  }

  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first) this._bootstrap();
  }

  set panel(_) {}
  set route(_) {}
  set narrow(_) {}

  connectedCallback() {
    if (this._hass && !this._pollTimer) this._startPolling();
  }

  disconnectedCallback() {
    this._stopPolling();
  }

  get t() {
    const lang = (this._hass?.language || "en").toLowerCase().startsWith("pl") ? "pl" : "en";
    return translations[lang];
  }

  async _bootstrap() {
    await this._loadDevices();
    this._startPolling();
  }

  _startPolling() {
    this._stopPolling();
    this._pollTimer = window.setInterval(async () => {
      if (document.hidden || this._busy || !this._selected) return;
      this._listTick += 1;
      if (this._listTick >= 4) {
        this._listTick = 0;
        await this._loadDevices(true);
      } else {
        await this._loadStatus(false, true);
      }
    }, 15000);
  }

  _stopPolling() {
    if (this._pollTimer) window.clearInterval(this._pollTimer);
    this._pollTimer = null;
  }

  async _loadDevices(silent = false) {
    if (!this._hass) return;
    if (!silent) {
      this._busy = true;
      this._render();
    }
    try {
      const data = await this._hass.callWS({ type: "nanokvm_rest/panel/list" });
      this._devices = data.devices || [];
      if (!this._devices.some((item) => item.entry_id === this._selected)) {
        this._selected = this._devices[0]?.entry_id || "";
      }
      if (this._selected) localStorage.setItem("nanokvm-remote-selected", this._selected);
      if (this._selected) await this._loadStatus(false, silent);
      else this._status = null;
    } catch (err) {
      this._setNotice(this._errorText(err), true);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _loadStatus(renderFirst = true, silent = false) {
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
      const result = await this._hass.callWS({
        type: "nanokvm_rest/panel/status",
        entry_id: this._selected,
      });
      this._status = result;
      this._devices = this._devices.map((item) => item.entry_id === this._selected ? { ...item, ...result } : item);
      if (!silent) this._notice = null;
    } catch (err) {
      if (!silent) this._setNotice(this._errorText(err), true);
      if (this._status) this._status = { ...this._status, available: false };
      this._devices = this._devices.map((item) => item.entry_id === this._selected ? { ...item, available: false } : item);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _select(entryId) {
    if (!entryId || entryId === this._selected || this._busy) return;
    this._selected = entryId;
    this._status = null;
    this._embedNative = false;
    localStorage.setItem("nanokvm-remote-selected", entryId);
    await this._loadStatus(true);
  }

  _setView(view) {
    this._view = view;
    localStorage.setItem("nanokvm-remote-view", view);
    this._render();
  }

  async _action(action, extra = {}, confirmation = "") {
    if (!this._selected || this._busy) return;
    if (confirmation && !window.confirm(confirmation)) return;
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
      this._setNotice(this._errorText(err), true);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _offlineUpdate() {
    const file = this.shadowRoot.querySelector("#update-file")?.files?.[0];
    const checksum = this.shadowRoot.querySelector("#checksum")?.value?.trim() || "";
    if (!file || !this._selected || this._busy) return;
    if (!window.confirm(this.t.confirmUpdate)) return;

    this._busy = true;
    this._setNotice(`${this.t.working} (${this._formatBytes(file.size)})`, false);
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

  async _copyAddress() {
    const url = this._status?.base_url || this._selectedDevice()?.base_url;
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      this._setNotice(this.t.copied, false, true);
    } catch (err) {
      this._setNotice(this._errorText(err), true);
    }
    this._render();
  }

  _selectedDevice() {
    return this._devices.find((item) => item.entry_id === this._selected) || null;
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

  _bool(value, yes = this.t.yes, no = this.t.no) {
    return value === true ? yes : value === false ? no : this.t.unknown;
  }

  _formatBytes(bytes) {
    if (!Number.isFinite(bytes) || bytes < 1) return "0 B";
    const units = ["B", "KiB", "MiB", "GiB"];
    const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
    return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`;
  }

  _canEmbed(baseUrl) {
    try {
      const url = new URL(baseUrl);
      return !(window.location.protocol === "https:" && url.protocol === "http:");
    } catch (_) {
      return false;
    }
  }

  _summary() {
    return {
      total: this._devices.length,
      online: this._devices.filter((d) => d.available === true).length,
      powered: this._devices.filter((d) => d.power === true).length,
    };
  }

  _renderRail() {
    const t = this.t;
    const summary = this._summary();
    const devices = this._devices.map((item) => {
      const active = item.entry_id === this._selected;
      const stateClass = item.available === true ? "online" : item.available === false ? "offline" : "";
      const power = item.power === true ? "ON" : item.power === false ? "OFF" : "—";
      return `<button class="device-item ${active ? "active" : ""}" data-device="${this._escape(item.entry_id)}" ${this._busy ? "disabled" : ""}>
        <span class="dot ${stateClass}"></span>
        <span><span class="device-name">${this._escape(item.hostname || item.title || "NanoKVM")}</span><span class="device-meta">${this._escape(item.hardware || item.base_url || "")}</span></span>
        <span class="power-pill">${power}</span>
      </button>`;
    }).join("");

    return `<aside class="rail">
      <div class="brand"><div class="brand-icon">K</div><div><h1>Remote Server</h1><div class="muted tiny">${t.subtitle}</div></div></div>
      <div class="rail-summary">
        <div class="rail-stat"><b>${summary.total}</b><span class="tiny muted">${t.all}</span></div>
        <div class="rail-stat"><b>${summary.online}</b><span class="tiny muted">${t.online}</span></div>
        <div class="rail-stat"><b>${summary.powered}</b><span class="tiny muted">${t.hostsOn}</span></div>
      </div>
      <div class="device-list">${devices || `<div class="muted tiny">${t.noDevices}</div>`}</div>
      <div class="rail-actions">
        <button class="btn secondary compact" id="rail-refresh" ${this._busy ? "disabled" : ""}>${t.refresh}</button>
        <a class="btn secondary compact" href="/config/integrations/integration/nanokvm_rest">${t.integrations}</a>
      </div>
    </aside>`;
  }

  _renderOverview(status, selected) {
    const t = this.t;
    return `<div class="grid">
      <section class="card full">
        <div class="card-head"><h3>${t.overview}</h3><span class="${status.available ? "ok" : "bad"}">${status.available ? t.online : t.off}</span></div>
        <div class="metrics">
          <div class="metric"><span>${t.availability}</span><b class="${status.available ? "ok" : "bad"}">${status.available ? t.online : t.off}</b></div>
          <div class="metric"><span>${t.hostPower}</span><b>${this._bool(status.power, t.on, t.off)}</b></div>
          <div class="metric"><span>${t.hdmi}</span><b>${this._bool(status.hdmi_signal, t.on, t.off)}</b></div>
          <div class="metric"><span>${t.hardware}</span><b>${this._escape(status.hardware || t.unknown)}</b></div>
          <div class="metric"><span>${t.appVersion}</span><b>${this._escape(status.application_version || t.unknown)}</b></div>
          <div class="metric"><span>${t.address}</span><b class="url">${this._escape(status.base_url || selected?.base_url || t.unknown)}</b></div>
        </div>
      </section>

      <section class="card">
        <h3>${t.powerControls}</h3>
        <p class="section-text">${t.powerText}</p>
        <div class="actions">
          <button class="btn" data-action="power_on" ${this._busy || status.power === true ? "disabled" : ""}>${t.powerOn}</button>
          <button class="btn secondary" data-action="power_press" ${this._busy ? "disabled" : ""}>${t.powerPress}</button>
          <button class="btn warning" data-action="reset" data-confirm="reset" ${this._busy ? "disabled" : ""}>${t.reset}</button>
          <button class="btn danger" data-action="force_off" data-confirm="force" ${this._busy || status.power !== true ? "disabled" : ""}>${t.forceOff}</button>
        </div>
      </section>

      <section class="card">
        <h3>${t.kvmControls}</h3>
        ${status.admin ? `<div class="actions">
          <button class="btn" data-action="reset_hid" ${this._busy ? "disabled" : ""}>${t.hidReset}</button>
          <button class="btn warning" data-action="reboot_nanokvm" data-confirm="reboot" ${this._busy ? "disabled" : ""}>${t.rebootKvm}</button>
          <a class="btn secondary" href="${this._escape(status.base_url || selected?.base_url || "#")}" target="_blank" rel="noopener noreferrer">${t.openNative}</a>
        </div>` : `<p class="section-text">${t.adminRequired}</p>`}
      </section>
    </div>`;
  }

  _renderMedia(status) {
    const t = this.t;
    const media = status.media || { files: [], mounted: "", cdrom: false };
    if (!status.admin) return `<section class="card full"><h3>${t.media}</h3><p class="section-text">${t.adminRequired}</p></section>`;

    const mounted = media.mounted ? `<section class="card full mounted"><div class="card-head"><h3>${t.mountedImage}</h3><b>${media.cdrom ? t.cdrom : t.disk}</b></div>
      <div class="media-item mounted"><div class="media-name"><b>${this._escape(this._basename(media.mounted))}</b><span>${this._escape(media.mounted)}</span></div>
      <div class="media-actions">
        <button class="btn secondary compact" data-action="set_cdrom" data-cdrom="${media.cdrom ? "false" : "true"}" ${this._busy ? "disabled" : ""}>${media.cdrom ? t.changeToDisk : t.changeToCdrom}</button>
        <button class="btn danger compact" data-action="unmount_image" ${this._busy ? "disabled" : ""}>${t.unmount}</button>
      </div></div></section>` : "";

    const rows = (media.files || []).map((file) => `<div class="media-item ${file === media.mounted ? "mounted" : ""}">
      <div class="media-name"><b>${this._escape(this._basename(file))}</b><span>${this._escape(file)}</span></div>
      <div class="media-actions">
        <button class="btn compact" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="true" ${this._busy ? "disabled" : ""}>${t.mountCdrom}</button>
        <button class="btn secondary compact" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="false" ${this._busy ? "disabled" : ""}>${t.mountDisk}</button>
        <button class="btn danger compact" data-action="delete_image" data-image="${this._escape(file)}" data-confirm="delete" ${this._busy || file === media.mounted ? "disabled" : ""}>${t.delete}</button>
      </div>
    </div>`).join("");

    return `<div class="grid">${mounted}<section class="card full"><h3>${t.availableImages}</h3><div class="media-list">${rows || `<div class="empty muted">${t.noImages}</div>`}</div></section></div>`;
  }

  _renderMaintenance(status, selected) {
    const t = this.t;
    const baseUrl = status.base_url || selected?.base_url || "";
    return `<div class="grid">
      <section class="card">
        <h3>${t.kvmControls}</h3>
        ${status.admin ? `<div class="actions">
          <button class="btn" data-action="reset_hid" ${this._busy ? "disabled" : ""}>${t.hidReset}</button>
          <button class="btn warning" data-action="reboot_nanokvm" data-confirm="reboot" ${this._busy ? "disabled" : ""}>${t.rebootKvm}</button>
          <button class="btn secondary" id="copy-address" ${!baseUrl ? "disabled" : ""}>${t.copyAddress}</button>
        </div>` : `<p class="section-text">${t.adminRequired}</p>`}
      </section>
      <section class="card">
        <h3>${t.address}</h3><p class="section-text url">${this._escape(baseUrl || t.unknown)}</p>
        ${baseUrl ? `<a class="btn secondary" href="${this._escape(baseUrl)}" target="_blank" rel="noopener noreferrer">${t.openNative}</a>` : ""}
      </section>
      <section class="card full">
        <h3>${t.offlineUpdate}</h3><p class="section-text">${t.updateText}</p>
        ${status.admin ? `<div class="form-grid">
          <label>${t.package}<input id="update-file" type="file" accept=".tar.gz,application/gzip" ${this._busy ? "disabled" : ""}></label>
          <label>${t.checksum}<input id="checksum" type="text" maxlength="64" placeholder="0123456789abcdef…" ${this._busy ? "disabled" : ""}></label>
          <button class="btn" id="offline-update" ${this._busy ? "disabled" : ""}>${t.upload}</button>
        </div>` : `<p class="section-text">${t.adminRequired}</p>`}
      </section>
    </div>`;
  }

  _renderNative(status, selected) {
    const t = this.t;
    const baseUrl = status.base_url || selected?.base_url || "";
    const canEmbed = this._canEmbed(baseUrl);
    return `<section class="card full native-wrap">
      <h3>${t.nativeTitle}</h3><p class="section-text">${t.nativeText}</p>
      <div class="native-toolbar">
        ${baseUrl ? `<a class="btn" href="${this._escape(baseUrl)}" target="_blank" rel="noopener noreferrer">${t.openNative}</a>` : ""}
        <button class="btn secondary" id="toggle-embed" ${!baseUrl || !canEmbed ? "disabled" : ""}>${this._embedNative ? t.hideEmbed : t.embed}</button>
        <button class="btn secondary" id="copy-address" ${!baseUrl ? "disabled" : ""}>${t.copyAddress}</button>
      </div>
      ${!canEmbed && baseUrl ? `<div class="notice show error">${t.mixedContent}</div>` : ""}
      ${this._embedNative && canEmbed ? `<iframe src="${this._escape(baseUrl)}" referrerpolicy="no-referrer" allow="fullscreen; clipboard-read; clipboard-write"></iframe>` : ""}
    </section>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    const t = this.t;
    const selected = this._selectedDevice();
    const status = this._status;
    const noticeClass = this._notice ? `notice show ${this._notice.error ? "error" : this._notice.success ? "success" : ""}` : "notice";
    const tabs = [
      ["overview", t.overview],
      ["media", t.media],
      ["maintenance", t.maintenance],
      ["native", t.native],
    ].map(([id, label]) => `<button class="tab ${this._view === id ? "active" : ""}" data-view="${id}">${label}</button>`).join("");

    let body = `<section class="card full empty">${t.noDevices}</section>`;
    if (this._devices.length && !status) body = `<section class="card full empty">${t.working}</section>`;
    if (status) {
      if (this._view === "media") body = this._renderMedia(status);
      else if (this._view === "maintenance") body = this._renderMaintenance(status, selected);
      else if (this._view === "native") body = this._renderNative(status, selected);
      else body = this._renderOverview(status, selected);
    }

    this.shadowRoot.innerHTML = `<style>${css}</style><div class="busy-line ${this._busy ? "active" : ""}"></div><div class="shell">
      ${this._renderRail()}
      <main class="main">
        <div class="topbar"><div class="title-wrap"><h2>${this._escape(status?.hostname || selected?.hostname || selected?.title || "Remote Server")}</h2><div class="muted">${this._escape(status?.base_url || selected?.base_url || t.subtitle)}</div></div>
          <div class="top-actions"><button class="btn secondary" id="refresh" ${this._busy ? "disabled" : ""}>${t.refresh}</button><a class="btn secondary" href="/config/integrations/integration/nanokvm_rest">${t.integrations}</a></div></div>
        <div class="${noticeClass}">${this._escape(this._notice?.text || "")}</div>
        <div class="tabs">${tabs}</div>
        <div class="content">${body}</div>
      </main>
    </div>`;
    this._bindEvents();
  }

  _bindEvents() {
    this.shadowRoot.querySelectorAll("[data-device]").forEach((el) => el.addEventListener("click", () => this._select(el.dataset.device)));
    this.shadowRoot.querySelectorAll("[data-view]").forEach((el) => el.addEventListener("click", () => this._setView(el.dataset.view)));
    this.shadowRoot.querySelectorAll("[data-action]").forEach((el) => el.addEventListener("click", () => {
      const action = el.dataset.action;
      const extra = {};
      if (el.dataset.image) extra.image = el.dataset.image;
      if (el.dataset.cdrom !== undefined) extra.cdrom = el.dataset.cdrom === "true";
      const key = el.dataset.confirm;
      const confirmation = key === "reset" ? this.t.confirmReset : key === "force" ? this.t.confirmForce : key === "reboot" ? this.t.confirmReboot : key === "delete" ? this.t.confirmDelete : "";
      this._action(action, extra, confirmation);
    }));
    this.shadowRoot.querySelector("#refresh")?.addEventListener("click", () => this._loadDevices());
    this.shadowRoot.querySelector("#rail-refresh")?.addEventListener("click", () => this._loadDevices());
    this.shadowRoot.querySelector("#offline-update")?.addEventListener("click", () => this._offlineUpdate());
    this.shadowRoot.querySelector("#copy-address")?.addEventListener("click", () => this._copyAddress());
    this.shadowRoot.querySelector("#toggle-embed")?.addEventListener("click", () => { this._embedNative = !this._embedNative; this._render(); });
  }
}

if (!customElements.get("nanokvm-remote-server-panel")) {
  customElements.define("nanokvm-remote-server-panel", NanoKVMRemoteServerPanel);
}
