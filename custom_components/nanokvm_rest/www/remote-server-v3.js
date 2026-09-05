import { css } from "./remote-server-v3.css.js";
import { translations } from "./remote-server-v3-i18n.js";

const svg = (body) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${body}</svg>`;
const icons = {
  server: svg('<rect x="3" y="4" width="18" height="6" rx="2"/><rect x="3" y="14" width="18" height="6" rx="2"/><path d="M7 7h.01M7 17h.01M11 7h7M11 17h7"/>'),
  dashboard: svg('<rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/>'),
  device: svg('<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>'),
  media: svg('<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="2"/><path d="M12 3v7M21 12h-7"/>'),
  tools: svg('<path d="M14.7 6.3a4 4 0 0 0-5-5L12 3.6 9.6 6 7.3 3.7a4 4 0 0 0 5 5l-7.9 7.9a2 2 0 1 0 2.8 2.8z"/>'),
  external: svg('<path d="M14 3h7v7M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>'),
  search: svg('<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>'),
  star: svg('<path d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2-5.6-3-5.6 3 1.1-6.2L3 9.6l6.2-.9z"/>'),
  refresh: svg('<path d="M20 11a8 8 0 0 0-14.8-4M4 4v5h5M4 13a8 8 0 0 0 14.8 4M20 20v-5h-5"/>'),
  settings: svg('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1z"/>'),
  power: svg('<path d="M12 2v10"/><path d="M7.1 5.7a8 8 0 1 0 9.8 0"/>'),
  reset: svg('<path d="M4 4v6h6"/><path d="M5.1 15a8 8 0 1 0 .5-7.5L4 10"/>'),
  keyboard: svg('<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M6 14h12"/>'),
  edit: svg('<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/>'),
  activity: svg('<path d="M3 12h4l2-7 4 14 2-7h6"/>'),
  check: svg('<path d="m5 12 4 4L19 6"/>'),
  alert: svg('<path d="M12 3 2.8 20h18.4z"/><path d="M12 9v4M12 17h.01"/>'),
  wifi: svg('<path d="M5 12.5a10 10 0 0 1 14 0M8.5 16a5 5 0 0 1 7 0M12 20h.01"/>'),
  plus: svg('<path d="M12 5v14M5 12h14"/>'),
  trash: svg('<path d="M3 6h18M8 6V4h8v2M6 6l1 15h10l1-15M10 10v7M14 10v7"/>'),
  copy: svg('<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>'),
  upload: svg('<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v5h16v-5"/>'),
  tag: svg('<path d="M20 13 11 22l-9-9V4h9z"/><circle cx="7" cy="9" r="1"/>'),
};
const icon = (name) => icons[name] || icons.server;

class NanoKVMRemoteServerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._hass = null;
    this._devices = [];
    this._groups = [];
    this._tags = [];
    this._history = [];
    this._status = null;
    this._selected = localStorage.getItem("nanokvm-remote-selected") || "";
    this._view = localStorage.getItem("nanokvm-remote-view-v3") || "dashboard";
    this._search = "";
    this._group = "";
    this._tag = "";
    this._favoritesOnly = false;
    this._busy = false;
    this._notice = null;
    this._modal = null;
    this._embedNative = false;
    this._pollTimer = null;
    this._tick = 0;
    this._pendingUpdate = null;
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
  disconnectedCallback() { this._stopPolling(); }

  get t() {
    const lang = (this._hass?.language || "en").toLowerCase().startsWith("pl") ? "pl" : "en";
    return translations[lang];
  }

  async _bootstrap() {
    await this._loadDevices(false);
    await this._loadHistory(true);
    if (this._selected && this._view !== "dashboard") await this._loadStatus(false, false);
    this._startPolling();
  }

  _startPolling() {
    this._stopPolling();
    this._pollTimer = window.setInterval(async () => {
      if (document.hidden || this._busy) return;
      this._tick += 1;
      await this._loadDevices(true);
      if (this._selected && this._view !== "dashboard") await this._loadStatus(false, true);
      if (this._tick % 4 === 0) await this._loadHistory(true);
    }, 15000);
  }
  _stopPolling() {
    if (this._pollTimer) window.clearInterval(this._pollTimer);
    this._pollTimer = null;
  }

  async _loadDevices(silent = false) {
    if (!this._hass) return;
    if (!silent) { this._busy = true; this._render(); }
    try {
      const result = await this._hass.callWS({ type: "nanokvm_rest/panel/list" });
      this._devices = result.devices || [];
      this._groups = result.groups || [];
      this._tags = result.tags || [];
      if (!this._devices.some((item) => item.entry_id === this._selected)) {
        this._selected = this._devices[0]?.entry_id || "";
      }
      if (this._selected) localStorage.setItem("nanokvm-remote-selected", this._selected);
    } catch (err) {
      if (!silent) this._setNotice(this._errorText(err), true);
    } finally {
      if (!silent) this._busy = false;
      this._render();
    }
  }

  async _loadStatus(touch = false, silent = false) {
    if (!this._selected || !this._hass) return;
    if (!silent) { this._busy = true; this._render(); }
    try {
      const status = await this._hass.callWS({
        type: "nanokvm_rest/panel/status",
        entry_id: this._selected,
        touch,
      });
      this._status = status;
      this._devices = this._devices.map((item) => item.entry_id === status.entry_id ? { ...item, ...status, media: undefined, wol_profiles: undefined } : item);
      if (!silent) this._notice = null;
    } catch (err) {
      if (!silent) this._setNotice(this._errorText(err), true);
      if (this._status) this._status = { ...this._status, available: false };
    } finally {
      if (!silent) this._busy = false;
      this._render();
    }
  }

  async _loadHistory(silent = false) {
    try {
      const result = await this._hass.callWS({ type: "nanokvm_rest/panel/history", limit: 120 });
      this._history = result.events || [];
      if (!silent) this._render();
    } catch (err) {
      if (!silent) { this._setNotice(this._errorText(err), true); this._render(); }
    }
  }

  async _select(entryId, view = "device") {
    if (!entryId || this._busy) return;
    const changed = entryId !== this._selected;
    this._selected = entryId;
    this._view = view;
    this._embedNative = false;
    if (changed) this._status = null;
    localStorage.setItem("nanokvm-remote-selected", entryId);
    localStorage.setItem("nanokvm-remote-view-v3", view);
    await this._loadStatus(true, false);
  }

  async _setView(view) {
    this._view = view;
    localStorage.setItem("nanokvm-remote-view-v3", view);
    if (view !== "dashboard" && this._selected && (!this._status || this._status.entry_id !== this._selected)) {
      await this._loadStatus(true, false);
      return;
    }
    this._render();
  }

  async _action(entryId, action, extra = {}, silentSuccess = false) {
    if (!entryId || this._busy) return;
    this._busy = true;
    this._setNotice(this.t.working, false);
    this._render();
    try {
      await this._hass.callWS({ type: "nanokvm_rest/panel/action", entry_id: entryId, action, ...extra });
      if (!silentSuccess) this._setNotice(this.t.success, false, true);
      await this._loadDevices(true);
      if (entryId === this._selected && action !== "reboot_nanokvm") await this._loadStatus(false, true);
      await this._loadHistory(true);
    } catch (err) {
      this._setNotice(this._errorText(err), true);
    } finally {
      this._busy = false;
      this._render();
    }
  }

  async _toggleFavorite(entryId) {
    const device = this._devices.find((item) => item.entry_id === entryId);
    if (!device || this._busy) return;
    try {
      const meta = await this._hass.callWS({
        type: "nanokvm_rest/panel/metadata/update",
        entry_id: entryId,
        favorite: !device.favorite,
      });
      this._devices = this._devices.map((item) => item.entry_id === entryId ? { ...item, ...meta } : item);
      if (this._status?.entry_id === entryId) this._status = { ...this._status, ...meta };
      await this._loadHistory(true);
      this._render();
    } catch (err) { this._setNotice(this._errorText(err), true); this._render(); }
  }

  async _saveMetadata() {
    const entryId = this._modal?.entry_id;
    if (!entryId) return;
    const favorite = !!this.shadowRoot.querySelector("#meta-favorite")?.checked;
    const group = this.shadowRoot.querySelector("#meta-group")?.value?.trim() || "";
    const tags = (this.shadowRoot.querySelector("#meta-tags")?.value || "").split(",").map((item) => item.trim()).filter(Boolean);
    this._modal = null;
    this._busy = true;
    this._render();
    try {
      await this._hass.callWS({ type: "nanokvm_rest/panel/metadata/update", entry_id: entryId, favorite, group, tags });
      await this._loadDevices(true);
      if (entryId === this._selected) await this._loadStatus(false, true);
      await this._loadHistory(true);
      this._setNotice(this.t.success, false, true);
    } catch (err) { this._setNotice(this._errorText(err), true); }
    this._busy = false;
    this._render();
  }

  async _saveWol() {
    if (!this._selected) return;
    const name = this.shadowRoot.querySelector("#wol-name")?.value?.trim() || "";
    const mac = this.shadowRoot.querySelector("#wol-mac")?.value?.trim() || "";
    const profileId = this._modal?.profile?.id || "";
    this._modal = null;
    this._busy = true;
    this._render();
    try {
      await this._hass.callWS({ type: "nanokvm_rest/panel/wol/save", entry_id: this._selected, name, mac, profile_id: profileId });
      await this._loadStatus(false, true);
      await this._loadHistory(true);
      this._setNotice(this.t.success, false, true);
    } catch (err) { this._setNotice(this._errorText(err), true); }
    this._busy = false;
    this._render();
  }

  async _runWol(profileId) {
    if (!this._selected || this._busy) return;
    this._busy = true; this._setNotice(this.t.working, false); this._render();
    try {
      await this._hass.callWS({ type: "nanokvm_rest/panel/wol/run", entry_id: this._selected, profile_id: profileId });
      await this._loadHistory(true);
      this._setNotice(this.t.success, false, true);
    } catch (err) { this._setNotice(this._errorText(err), true); }
    this._busy = false; this._render();
  }

  async _deleteWol(profileId) {
    if (!this._selected) return;
    this._busy = true; this._render();
    try {
      await this._hass.callWS({ type: "nanokvm_rest/panel/wol/delete", entry_id: this._selected, profile_id: profileId });
      await this._loadStatus(false, true);
      await this._loadHistory(true);
      this._setNotice(this.t.success, false, true);
    } catch (err) { this._setNotice(this._errorText(err), true); }
    this._busy = false; this._render();
  }

  _prepareOfflineUpdate() {
    const file = this.shadowRoot.querySelector("#update-file")?.files?.[0];
    if (!file || !this._selected || this._busy) return;
    const checksum = this.shadowRoot.querySelector("#checksum")?.value?.trim() || "";
    this._pendingUpdate = { file, checksum };
    this._openConfirm("offline_update", this.t.confirmUpdateTitle, this.t.confirmUpdateText, true, {});
  }

  async _performOfflineUpdate() {
    const pending = this._pendingUpdate;
    this._pendingUpdate = null;
    if (!pending || !this._selected) return;
    this._busy = true;
    this._setNotice(`${this.t.working} (${this._formatBytes(pending.file.size)})`, false);
    this._render();
    const form = new FormData();
    form.append("file", pending.file);
    const headers = { Authorization: `Bearer ${this._hass.auth.accessToken}` };
    if (pending.checksum) headers["X-SHA256-Checksum"] = pending.checksum;
    try {
      const response = await fetch(`/api/nanokvm_rest/offline-update/${encodeURIComponent(this._selected)}`, { method: "POST", headers, body: form });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `HTTP ${response.status}`);
      this._setNotice(this.t.updateAccepted, false, true);
      await this._loadHistory(true);
    } catch (err) { this._setNotice(this._errorText(err), true); }
    this._busy = false; this._render();
  }

  async _copyAddress() {
    const url = this._status?.base_url || this._selectedDevice()?.base_url;
    if (!url) return;
    try { await navigator.clipboard.writeText(url); this._setNotice(this.t.copied, false, true); }
    catch (err) { this._setNotice(this._errorText(err), true); }
    this._render();
  }

  _openMetadata(entryId) {
    const device = this._devices.find((item) => item.entry_id === entryId);
    if (!device) return;
    this._modal = { kind: "metadata", entry_id: entryId, device };
    this._render();
  }

  _openWol(profile = null) { this._modal = { kind: "wol", profile }; this._render(); }
  _openConfirm(kind, title, text, danger, payload) {
    this._modal = { kind: "confirm", confirmKind: kind, title, text, danger, payload };
    this._render();
  }

  async _confirmModal() {
    const modal = this._modal;
    if (!modal || modal.kind !== "confirm") return;
    this._modal = null;
    const p = modal.payload || {};
    if (modal.confirmKind === "action") await this._action(p.entry_id, p.action, p.extra || {});
    else if (modal.confirmKind === "delete_wol") await this._deleteWol(p.profile_id);
    else if (modal.confirmKind === "offline_update") await this._performOfflineUpdate();
  }

  _setNotice(text, error = false, success = false) { this._notice = { text, error, success }; }
  _errorText(err) { return err?.message || err?.error?.message || String(err); }
  _escape(value) { return String(value ?? "").replace(/[&<>'"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[c]); }
  _basename(value) { const bits = String(value || "").split("/"); return bits[bits.length - 1] || value; }
  _selectedDevice() { return this._devices.find((item) => item.entry_id === this._selected) || null; }
  _bool(value) { return value === true ? this.t.on : value === false ? this.t.off : this.t.unknown; }
  _formatBytes(bytes) { if (!Number.isFinite(bytes) || bytes < 1) return "0 B"; const units = ["B", "KiB", "MiB", "GiB"]; const i = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1); return `${(bytes / Math.pow(1024, i)).toFixed(i ? 1 : 0)} ${units[i]}`; }
  _canEmbed(baseUrl) { try { const url = new URL(baseUrl); return !(window.location.protocol === "https:" && url.protocol === "http:"); } catch (_) { return false; } }
  _healthLabel(health) { return health?.state === "healthy" ? this.t.healthy : health?.state === "warning" ? this.t.warning : this.t.critical; }
  _eventLabel(event) { return this.t[`event_${event}`] || event.replaceAll("_", " "); }
  _time(value) { try { return new Intl.DateTimeFormat(this._hass?.language || undefined, { dateStyle: "short", timeStyle: "short" }).format(new Date(value)); } catch (_) { return value || ""; } }

  _matches(device) {
    const query = this._search.trim().toLowerCase();
    const haystack = [device.title, device.hostname, device.base_url, device.hardware, device.group, ...(device.tags || [])].join(" ").toLowerCase();
    if (query && !haystack.includes(query)) return false;
    if (this._group && device.group !== this._group) return false;
    if (this._tag && !(device.tags || []).includes(this._tag)) return false;
    if (this._favoritesOnly && !device.favorite) return false;
    return true;
  }

  _filterDom() {
    let visible = 0;
    this.shadowRoot.querySelectorAll("[data-filter-entry]").forEach((el) => {
      const device = this._devices.find((item) => item.entry_id === el.dataset.filterEntry);
      const show = !!device && this._matches(device);
      el.hidden = !show;
      if (show && el.classList.contains("device-card")) visible += 1;
    });
    const noResults = this.shadowRoot.querySelector("#no-results");
    if (noResults) noResults.hidden = visible > 0 || this._devices.length === 0;
  }

  _summary() {
    return {
      total: this._devices.length,
      online: this._devices.filter((d) => d.available === true).length,
      powered: this._devices.filter((d) => d.power === true).length,
      issues: this._devices.filter((d) => d.health?.state !== "healthy").length,
    };
  }

  _renderSidebar() {
    const s = this._summary();
    const groupOptions = [`<option value="">${this.t.allGroups}</option>`, ...this._groups.map((g) => `<option value="${this._escape(g)}" ${g === this._group ? "selected" : ""}>${this._escape(g)}</option>`)].join("");
    const rows = this._devices.map((d) => `<button class="device-row ${d.entry_id === this._selected && this._view !== "dashboard" ? "active" : ""}" data-select="${this._escape(d.entry_id)}" data-filter-entry="${this._escape(d.entry_id)}">
      <span class="status-dot ${d.available ? "online" : "offline"}"></span><span class="row-copy"><span class="row-name">${this._escape(d.hostname || d.title)}</span><span class="row-meta">${this._escape(d.group || d.hardware || d.base_url || "")}</span></span><span class="row-end">${d.favorite ? `<span class="mini-star">★</span>` : ""}<span class="mini-pill">${d.power === true ? "ON" : d.power === false ? "OFF" : "—"}</span></span>
    </button>`).join("");
    return `<aside class="sidebar"><div class="brand"><div class="brand-mark">${icon("server")}</div><div><h1>${this.t.appTitle}</h1><p>${this.t.subtitle}</p></div></div>
      <div class="side-tools"><div class="search-wrap">${icon("search")}<input class="search" id="global-search" type="search" value="${this._escape(this._search)}" placeholder="${this._escape(this.t.search)}"></div><div class="side-filters"><select class="select" id="group-filter">${groupOptions}</select><button class="icon-btn ${this._favoritesOnly ? "active" : ""}" id="favorite-filter" title="${this._escape(this.t.favoritesOnly)}">${icon("star")}</button></div></div>
      <div class="side-summary"><div class="summary-mini"><b>${s.total}</b><span>${this.t.all}</span></div><div class="summary-mini"><b>${s.online}</b><span>${this.t.online}</span></div><div class="summary-mini"><b>${s.powered}</b><span>${this.t.hostsOn}</span></div></div>
      <div class="device-list">${rows || `<div class="empty tiny">${this.t.noDevices}</div>`}</div>
      <div class="sidebar-footer"><button class="btn secondary small" id="side-refresh">${icon("refresh")}${this.t.refresh}</button><a class="btn secondary small" href="/config/integrations/integration/nanokvm_rest">${icon("settings")}${this.t.integrations}</a></div></aside>`;
  }

  _renderMobilePicker() {
    const cards = this._devices.map((d) => `<button class="mobile-device ${d.entry_id === this._selected && this._view !== "dashboard" ? "active" : ""}" data-select="${this._escape(d.entry_id)}"><b>${this._escape(d.hostname || d.title)}</b><span>${d.available ? this.t.online : this.t.offline} · ${d.power === true ? "Host ON" : d.power === false ? "Host OFF" : this.t.unknown}${d.favorite ? " · ★" : ""}</span></button>`).join("");
    return `<div class="mobile-device-picker"><div class="mobile-picker-label">${this.t.devices}</div><div class="mobile-device-scroll">${cards}</div></div>`;
  }

  _renderTabs() {
    const tabs = [["dashboard","dashboard",this.t.dashboard],["device","device",this.t.device],["media","media",this.t.media],["maintenance","tools",this.t.maintenance],["native","external",this.t.native]];
    return `<div class="tabs">${tabs.map(([id,ic,label]) => `<button class="tab ${this._view === id ? "active" : ""}" data-view="${id}">${icon(ic)}${label}</button>`).join("")}</div>`;
  }

  _renderBottomNav() {
    const tabs = [["dashboard","dashboard",this.t.dashboard],["device","device",this.t.device],["media","media",this.t.media],["maintenance","tools",this.t.maintenance],["native","external",this.t.native]];
    return `<nav class="bottom-nav">${tabs.map(([id,ic,label]) => `<button class="bottom-item ${this._view === id ? "active" : ""}" data-view="${id}" ${id !== "dashboard" && !this._selected ? "disabled" : ""}>${icon(ic)}<span>${label}</span></button>`).join("")}</nav>`;
  }

  _renderDeviceCard(d) {
    const health = d.health || { score: 0, state: "critical", issues: [] };
    const badges = [`<span class="badge ${d.available ? "ok" : "bad"}">${d.available ? this.t.online : this.t.offline}</span>`, `<span class="badge ${health.state === "healthy" ? "ok" : health.state === "warning" ? "warn" : "bad"}">${this._healthLabel(health)}</span>`];
    if (d.group) badges.push(`<span class="badge primary">${this._escape(d.group)}</span>`);
    const tags = (d.tags || []).map((tag) => `<span class="tag">${this._escape(tag)}</span>`).join("");
    return `<article class="device-card" data-filter-entry="${this._escape(d.entry_id)}"><div class="device-card-head"><div class="device-avatar">${icon("server")}</div><div class="device-title"><button data-select="${this._escape(d.entry_id)}">${this._escape(d.hostname || d.title)}</button><div class="device-sub">${this._escape(d.base_url || d.hardware || "")}</div></div><div><button class="favorite-btn ${d.favorite ? "on" : ""}" data-favorite="${this._escape(d.entry_id)}" title="${this.t.favorite}">${icon("star")}</button><button class="favorite-btn" data-meta="${this._escape(d.entry_id)}" title="${this.t.manageMeta}">${icon("edit")}</button></div></div>
      <div class="card-badges">${badges.join("")}</div><div class="health-row"><div class="health-meter ${health.state}"><span style="width:${Math.max(0, Math.min(100, health.score || 0))}%"></span></div><span class="health-score">${health.score ?? 0}%</span></div>
      <div class="quick-actions"><button class="quick" data-quick-action="power_on" data-entry="${this._escape(d.entry_id)}" title="${this.t.powerOn}" ${!d.available || d.power === true ? "disabled" : ""}>${icon("power")}</button><button class="quick danger" data-risk-action="reset" data-entry="${this._escape(d.entry_id)}" title="${this.t.resetHost}" ${!d.available ? "disabled" : ""}>${icon("reset")}</button><button class="quick" data-quick-action="reset_hid" data-entry="${this._escape(d.entry_id)}" title="${this.t.hidReset}" ${!d.available || !d.admin ? "disabled" : ""}>${icon("keyboard")}</button>${d.base_url ? `<a class="quick" href="${this._escape(d.base_url)}" target="_blank" rel="noopener noreferrer" title="${this.t.openUi}">${icon("external")}</a>` : `<button class="quick" disabled>${icon("external")}</button>`}</div>
      ${tags ? `<div class="card-tags">${tags}</div>` : ""}</article>`;
  }

  _renderHistory(limit = 15, entryId = "") {
    const events = this._history.filter((e) => !entryId || e.entry_id === entryId).slice(0, limit);
    if (!events.length) return `<div class="empty">${this.t.noEvents}</div>`;
    return `<div class="history-list">${events.map((e) => { const d = this._devices.find((item) => item.entry_id === e.entry_id); const detail = e.details?.profile || e.details?.image || e.details?.filename || e.details?.message || ""; return `<div class="history-item"><div class="event-icon ${e.result === "error" ? "error" : ""}">${icon(e.result === "error" ? "alert" : "activity")}</div><div><div class="event-title">${this._escape(this._eventLabel(e.event))}${e.result === "error" ? ` · ${this.t.failed}` : ""}</div><div class="event-meta">${this._escape(d?.hostname || d?.title || e.entry_id)} · ${this._escape(e.actor || this.t.system)}${detail ? ` · ${this._escape(detail)}` : ""}</div></div><div class="event-time">${this._escape(this._time(e.timestamp))}</div></div>`; }).join("")}</div>`;
  }

  _renderDashboard() {
    const s = this._summary();
    const favorite = this._devices.filter((d) => d.favorite).slice(0, 8);
    const recent = this._devices.filter((d) => d.last_used && !d.favorite).sort((a,b) => String(b.last_used).localeCompare(String(a.last_used))).slice(0, 8);
    const groupOptions = [`<option value="">${this.t.allGroups}</option>`, ...this._groups.map((g) => `<option value="${this._escape(g)}" ${g === this._group ? "selected" : ""}>${this._escape(g)}</option>`)].join("");
    const tagOptions = [`<option value="">${this.t.allTags}</option>`, ...this._tags.map((tag) => `<option value="${this._escape(tag)}" ${tag === this._tag ? "selected" : ""}>${this._escape(tag)}</option>`)].join("");
    const strip = (title, items) => items.length ? `<div class="strip"><div class="strip-title">${title}</div><div class="strip-scroll">${items.map((d) => `<button class="strip-card" data-select="${this._escape(d.entry_id)}"><b>${d.favorite ? "★ " : ""}${this._escape(d.hostname || d.title)}</b><span>${d.available ? this.t.online : this.t.offline} · ${this._healthLabel(d.health)}</span></button>`).join("")}</div></div>` : "";
    return `<div class="hero-stats"><div class="hero-stat"><span>${this.t.all}</span><b>${s.total}</b><div class="stat-note">NanoKVM</div></div><div class="hero-stat"><span>${this.t.online}</span><b class="ok">${s.online}</b><div class="stat-note">${s.total ? Math.round(s.online/s.total*100) : 0}%</div></div><div class="hero-stat"><span>${this.t.hostsOn}</span><b>${s.powered}</b><div class="stat-note">Power</div></div><div class="hero-stat"><span>${this.t.warnings}</span><b class="${s.issues ? "warn" : "ok"}">${s.issues}</b><div class="stat-note">Health</div></div></div>
      <div class="dashboard-tools"><div class="search-wrap">${icon("search")}<input class="search" id="dashboard-search" type="search" value="${this._escape(this._search)}" placeholder="${this._escape(this.t.search)}"></div><select class="select" id="dashboard-group">${groupOptions}</select><select class="select tag-filter" id="dashboard-tag">${tagOptions}</select><button class="btn secondary ${this._favoritesOnly ? "active" : ""}" id="dashboard-favorite">${icon("star")}${this.t.favorites}</button></div>
      <div class="mobile-strips">${strip(this.t.favorites, favorite)}${strip(this.t.recent, recent)}</div>
      <div class="section-head"><div><h3>${this.t.devices}</h3><p>${this.t.quickActions}</p></div></div><div class="device-grid">${this._devices.map((d) => this._renderDeviceCard(d)).join("")}</div><div class="empty" id="no-results" hidden>${this.t.noResults}</div>
      <div style="height:18px"></div><div class="section-head"><div><h3>${this.t.eventHistory}</h3><p>${this.t.eventHistoryText}</p></div></div><section class="card full">${this._renderHistory(18)}</section>`;
  }

  _renderOverview() {
    const s = this._status; if (!s) return `<div class="empty">${this.t.working}</div>`;
    const h = s.health || { score:0,state:"critical",issues:[] };
    const issues = (h.issues || []).map((issue) => issue === "kvm_offline" ? this.t.healthKvmOffline : issue === "hdmi_no_signal" ? this.t.healthHdmi : issue === "hardware_unknown" ? this.t.healthHardware : issue === "version_unknown" ? this.t.healthVersion : issue).map((x) => `<span class="badge warn">${this._escape(x)}</span>`).join("");
    return `<div class="grid"><section class="card full"><div class="card-head"><h3>${this.t.overview}</h3><span class="badge ${h.state === "healthy" ? "ok" : h.state === "warning" ? "warn" : "bad"}">${this._healthLabel(h)} · ${h.score}%</span></div><div class="metrics"><div class="metric"><span>${this.t.availability}</span><b class="${s.available ? "ok" : "bad"}">${s.available ? this.t.online : this.t.offline}</b></div><div class="metric"><span>${this.t.hostPower}</span><b>${this._bool(s.power)}</b></div><div class="metric"><span>${this.t.hdmi}</span><b>${this._bool(s.hdmi_signal)}</b></div><div class="metric"><span>${this.t.hardware}</span><b>${this._escape(s.hardware || this.t.unknown)}</b></div><div class="metric"><span>${this.t.appVersion}</span><b>${this._escape(s.application_version || this.t.unknown)}</b></div><div class="metric"><span>${this.t.address}</span><b class="url">${this._escape(s.base_url || this.t.unknown)}</b></div></div>${issues ? `<div class="card-tags" style="margin-top:10px">${issues}</div>` : ""}</section>
      <section class="card"><h3>${this.t.hostControls}</h3><div class="touch-actions"><button class="touch-action" data-action="power_on" ${this._busy || s.power === true ? "disabled" : ""}>${icon("power")}<span><b>${this.t.powerOn}</b><span>Power ON</span></span></button><button class="touch-action" data-action="power_press" ${this._busy ? "disabled" : ""}>${icon("power")}<span><b>${this.t.powerPress}</b><span>Short press</span></span></button><button class="touch-action warning" data-risk-action="reset" data-entry="${this._escape(s.entry_id)}" ${this._busy ? "disabled" : ""}>${icon("reset")}<span><b>${this.t.resetHost}</b><span>RESET</span></span></button><button class="touch-action danger" data-risk-action="force_off" data-entry="${this._escape(s.entry_id)}" ${this._busy || s.power !== true ? "disabled" : ""}>${icon("power")}<span><b>${this.t.forceOff}</b><span>Long press</span></span></button></div></section>
      <section class="card"><h3>${this.t.kvmControls}</h3>${s.admin ? `<div class="touch-actions"><button class="touch-action" data-action="reset_hid">${icon("keyboard")}<span><b>${this.t.hidReset}</b><span>Keyboard / mouse</span></span></button><button class="touch-action warning" data-risk-action="reboot_nanokvm" data-entry="${this._escape(s.entry_id)}">${icon("reset")}<span><b>${this.t.rebootKvm}</b><span>NanoKVM</span></span></button><button class="touch-action" data-meta="${this._escape(s.entry_id)}">${icon("tag")}<span><b>${this.t.manageMeta}</b><span>${this._escape(s.group || "—")}</span></span></button>${s.base_url ? `<a class="touch-action" href="${this._escape(s.base_url)}" target="_blank" rel="noopener noreferrer">${icon("external")}<span><b>${this.t.openUi}</b><span>Web UI</span></span></a>` : ""}</div>` : `<p class="section-text">${this.t.adminRequired}</p>`}</section>
      <section class="card full"><div class="card-head"><h3>${this.t.eventHistory}</h3></div>${this._renderHistory(12, s.entry_id)}</section></div>`;
  }

  _renderMedia() {
    const s = this._status; if (!s) return `<div class="empty">${this.t.working}</div>`;
    if (!s.admin) return `<section class="card full"><h3>${this.t.media}</h3><p class="section-text">${this.t.adminRequired}</p></section>`;
    const media = s.media || { files:[], mounted:"", cdrom:false };
    const mounted = media.mounted ? `<section class="card full"><div class="card-head"><h3>${this.t.mountedImage}</h3><span class="badge primary">${media.cdrom ? this.t.cdrom : this.t.disk}</span></div><div class="media-item mounted"><div class="media-name"><b>${this._escape(this._basename(media.mounted))}</b><span>${this._escape(media.mounted)}</span></div><div class="media-actions"><button class="btn secondary small" data-action="set_cdrom" data-cdrom="${media.cdrom ? "false" : "true"}">${this.t.changeMode}</button><button class="btn danger small" data-action="unmount_image">${this.t.unmount}</button></div></div></section>` : "";
    const rows = (media.files || []).map((file) => `<div class="media-item ${file === media.mounted ? "mounted" : ""}"><div class="media-name"><b>${this._escape(this._basename(file))}</b><span>${this._escape(file)}</span></div><div class="media-actions"><button class="btn small" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="true">${this.t.mountCdrom}</button><button class="btn secondary small" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="false">${this.t.mountDisk}</button><button class="btn danger small" data-delete-image="${this._escape(file)}" ${file === media.mounted ? "disabled" : ""}>${this.t.delete}</button></div></div>`).join("");
    return `<div class="grid">${mounted}<section class="card full"><div class="card-head"><h3>${this.t.availableImages}</h3><span class="badge">${media.files?.length || 0}</span></div><div class="media-list">${rows || `<div class="empty">${this.t.noImages}</div>`}</div></section></div>`;
  }

  _renderMaintenance() {
    const s = this._status; if (!s) return `<div class="empty">${this.t.working}</div>`;
    const profiles = s.wol_profiles || [];
    const profileRows = profiles.map((p) => `<div class="profile-item"><div class="profile-copy"><b>${this._escape(p.name)}</b><span>${this._escape(p.mac)}</span></div><div class="profile-actions"><button class="btn small" data-run-wol="${this._escape(p.id)}">${icon("wifi")}${this.t.wake}</button><button class="btn secondary small" data-edit-wol="${this._escape(p.id)}">${this.t.edit}</button><button class="btn danger small" data-delete-wol="${this._escape(p.id)}">${this.t.delete}</button></div></div>`).join("");
    return `<div class="grid"><section class="card"><div class="card-head"><h3>${this.t.wolProfiles}</h3><button class="btn small" id="add-wol">${icon("plus")}${this.t.addProfile}</button></div><p class="section-text">${this.t.wolProfilesText}</p><div class="profile-list">${profileRows || `<div class="empty">${this.t.noProfiles}</div>`}</div></section>
      <section class="card"><h3>${this.t.kvmControls}</h3>${s.admin ? `<div class="touch-actions"><button class="touch-action" data-action="reset_hid">${icon("keyboard")}<span><b>${this.t.hidReset}</b><span>HID</span></span></button><button class="touch-action warning" data-risk-action="reboot_nanokvm" data-entry="${this._escape(s.entry_id)}">${icon("reset")}<span><b>${this.t.rebootKvm}</b><span>Device</span></span></button><button class="touch-action" id="copy-address">${icon("copy")}<span><b>${this.t.copyAddress}</b><span>${this._escape(s.base_url || "")}</span></span></button></div>` : `<p class="section-text">${this.t.adminRequired}</p>`}</section>
      <section class="card full"><h3>${this.t.offlineUpdate}</h3><p class="section-text">${this.t.updateText}</p>${s.admin ? `<div class="form-grid"><label>${this.t.package}<input id="update-file" type="file" accept=".tar.gz,application/gzip"></label><label>${this.t.checksum}<input id="checksum" type="text" maxlength="64" placeholder="0123456789abcdef…"></label><button class="btn" id="offline-update">${icon("upload")}${this.t.upload}</button></div>` : `<p class="section-text">${this.t.adminRequired}</p>`}</section>
      <section class="card full"><div class="card-head"><h3>${this.t.eventHistory}</h3></div>${this._renderHistory(30, s.entry_id)}</section></div>`;
  }

  _renderNative() {
    const s = this._status; if (!s) return `<div class="empty">${this.t.working}</div>`;
    const baseUrl = s.base_url || ""; const canEmbed = this._canEmbed(baseUrl);
    return `<section class="card full"><h3>${this.t.nativeTitle}</h3><p class="section-text">${this.t.nativeText}</p><div class="native-toolbar">${baseUrl ? `<a class="btn" href="${this._escape(baseUrl)}" target="_blank" rel="noopener noreferrer">${icon("external")}${this.t.openUi}</a>` : ""}<button class="btn secondary" id="toggle-embed" ${!baseUrl || !canEmbed ? "disabled" : ""}>${this._embedNative ? this.t.hideEmbed : this.t.embed}</button><button class="btn secondary" id="copy-address" ${!baseUrl ? "disabled" : ""}>${icon("copy")}${this.t.copyAddress}</button></div>${!canEmbed && baseUrl ? `<div class="notice show error">${icon("alert")}${this.t.mixedContent}</div>` : ""}${this._embedNative && canEmbed ? `<iframe src="${this._escape(baseUrl)}" referrerpolicy="no-referrer" allow="fullscreen; clipboard-read; clipboard-write"></iframe>` : ""}</section>`;
  }

  _renderModal() {
    const m = this._modal; if (!m) return "";
    if (m.kind === "metadata") {
      const d = m.device;
      return `<div class="modal-backdrop" id="modal-backdrop"><div class="modal"><div class="modal-head"><h3>${this.t.manageMeta}</h3><button class="icon-btn" id="modal-close">×</button></div><div class="modal-body"><div class="modal-fields"><label>${this.t.group}<input id="meta-group" type="text" maxlength="64" value="${this._escape(d.group || "")}" placeholder="Production / Lab / Rack 1"></label><label>${this.t.tags}<input id="meta-tags" type="text" value="${this._escape((d.tags || []).join(", "))}" placeholder="PROD, PVE, RACK-01"></label><label class="check-row"><input id="meta-favorite" type="checkbox" ${d.favorite ? "checked" : ""}>${this.t.favorite}</label></div></div><div class="modal-footer"><button class="btn secondary" id="modal-close-2">${this.t.cancel}</button><button class="btn" id="meta-save">${this.t.save}</button></div></div></div>`;
    }
    if (m.kind === "wol") {
      const p = m.profile || {};
      return `<div class="modal-backdrop"><div class="modal"><div class="modal-head"><h3>${p.id ? this.t.editProfile : this.t.addProfile}</h3><button class="icon-btn" id="modal-close">×</button></div><div class="modal-body"><div class="modal-fields"><label>${this.t.profileName}<input id="wol-name" type="text" maxlength="64" value="${this._escape(p.name || "")}" placeholder="Proxmox 01"></label><label>${this.t.mac}<input id="wol-mac" type="text" maxlength="17" value="${this._escape(p.mac || "")}" placeholder="AA:BB:CC:DD:EE:FF"></label></div></div><div class="modal-footer"><button class="btn secondary" id="modal-close-2">${this.t.cancel}</button><button class="btn" id="wol-save">${this.t.save}</button></div></div></div>`;
    }
    if (m.kind === "confirm") return `<div class="modal-backdrop"><div class="modal"><div class="modal-body"><div class="confirm-symbol ${m.danger ? "danger" : ""}">${icon("alert")}</div><h4>${this._escape(m.title)}</h4><p>${this._escape(m.text)}</p></div><div class="modal-footer"><button class="btn secondary" id="modal-close">${this.t.cancel}</button><button class="btn ${m.danger ? "danger" : "warning"}" id="modal-confirm">${m.danger ? this.t.delete : this.t.save}</button></div></div></div>`;
    return "";
  }

  _render() {
    if (!this.shadowRoot) return;
    const selected = this._selectedDevice();
    const title = this._view === "dashboard" ? this.t.dashboard : (this._status?.hostname || selected?.hostname || selected?.title || this.t.appTitle);
    const sub = this._view === "dashboard" ? this.t.subtitle : (this._status?.base_url || selected?.base_url || this.t.subtitle);
    const noticeClass = this._notice ? `notice show ${this._notice.error ? "error" : this._notice.success ? "success" : ""}` : "notice";
    let body = this._renderDashboard();
    if (this._view === "device") body = this._selected ? this._renderOverview() : `<div class="empty">${this.t.noDevices}</div>`;
    else if (this._view === "media") body = this._selected ? this._renderMedia() : `<div class="empty">${this.t.noDevices}</div>`;
    else if (this._view === "maintenance") body = this._selected ? this._renderMaintenance() : `<div class="empty">${this.t.noDevices}</div>`;
    else if (this._view === "native") body = this._selected ? this._renderNative() : `<div class="empty">${this.t.noDevices}</div>`;
    this.shadowRoot.innerHTML = `<style>${css}</style><div class="busy-line ${this._busy ? "active" : ""}"></div><div class="shell">${this._renderSidebar()}<main class="main"><div class="topbar"><div class="title"><h2>${this._escape(title)}</h2><p>${this._escape(sub)}</p></div><div class="top-actions"><button class="btn secondary square" id="refresh" title="${this.t.refresh}">${icon("refresh")}</button><a class="btn secondary" href="/config/integrations/integration/nanokvm_rest">${icon("settings")}${this.t.integrations}</a></div></div><div class="${noticeClass}">${this._notice ? icon(this._notice.error ? "alert" : "check") : ""}${this._escape(this._notice?.text || "")}</div>${this._renderMobilePicker()}${this._renderTabs()}<div class="content">${body}</div></main></div>${this._renderBottomNav()}${this._renderModal()}`;
    this._bindEvents();
    this._filterDom();
  }

  _bindEvents() {
    const root = this.shadowRoot;
    root.querySelectorAll("[data-select]").forEach((el) => el.addEventListener("click", () => this._select(el.dataset.select)));
    root.querySelectorAll("[data-view]").forEach((el) => el.addEventListener("click", () => this._setView(el.dataset.view)));
    root.querySelectorAll("[data-favorite]").forEach((el) => el.addEventListener("click", (ev) => { ev.stopPropagation(); this._toggleFavorite(el.dataset.favorite); }));
    root.querySelectorAll("[data-meta]").forEach((el) => el.addEventListener("click", (ev) => { ev.stopPropagation(); this._openMetadata(el.dataset.meta); }));
    root.querySelectorAll("[data-quick-action]").forEach((el) => el.addEventListener("click", () => this._action(el.dataset.entry, el.dataset.quickAction)));
    root.querySelectorAll("[data-risk-action]").forEach((el) => el.addEventListener("click", () => {
      const action = el.dataset.riskAction; const entry = el.dataset.entry || this._selected;
      const title = action === "reset" ? this.t.confirmResetTitle : action === "force_off" ? this.t.confirmForceTitle : this.t.confirmRebootTitle;
      const text = action === "reset" ? this.t.confirmResetText : action === "force_off" ? this.t.confirmForceText : this.t.confirmRebootText;
      this._openConfirm("action", title, text, action === "force_off", { entry_id: entry, action });
    }));
    root.querySelectorAll("[data-action]").forEach((el) => el.addEventListener("click", () => {
      const extra = {}; if (el.dataset.image) extra.image = el.dataset.image; if (el.dataset.cdrom !== undefined) extra.cdrom = el.dataset.cdrom === "true";
      this._action(this._selected, el.dataset.action, extra);
    }));
    root.querySelectorAll("[data-delete-image]").forEach((el) => el.addEventListener("click", () => this._openConfirm("action", this.t.confirmDeleteTitle, this.t.confirmDeleteText, true, { entry_id: this._selected, action: "delete_image", extra: { image: el.dataset.deleteImage } })));
    root.querySelectorAll("[data-run-wol]").forEach((el) => el.addEventListener("click", () => this._runWol(el.dataset.runWol)));
    root.querySelectorAll("[data-edit-wol]").forEach((el) => el.addEventListener("click", () => this._openWol((this._status?.wol_profiles || []).find((p) => p.id === el.dataset.editWol) || null)));
    root.querySelectorAll("[data-delete-wol]").forEach((el) => el.addEventListener("click", () => this._openConfirm("delete_wol", this.t.confirmDeleteProfileTitle, this.t.confirmDeleteProfileText, true, { profile_id: el.dataset.deleteWol })));
    root.querySelector("#refresh")?.addEventListener("click", async () => { await this._loadDevices(false); if (this._selected && this._view !== "dashboard") await this._loadStatus(false, false); await this._loadHistory(true); });
    root.querySelector("#side-refresh")?.addEventListener("click", () => this._loadDevices(false));
    root.querySelector("#add-wol")?.addEventListener("click", () => this._openWol());
    root.querySelector("#offline-update")?.addEventListener("click", () => this._prepareOfflineUpdate());
    root.querySelectorAll("#copy-address").forEach((el) => el.addEventListener("click", () => this._copyAddress()));
    root.querySelector("#toggle-embed")?.addEventListener("click", () => { this._embedNative = !this._embedNative; this._render(); });
    root.querySelector("#meta-save")?.addEventListener("click", () => this._saveMetadata());
    root.querySelector("#wol-save")?.addEventListener("click", () => this._saveWol());
    root.querySelector("#modal-confirm")?.addEventListener("click", () => this._confirmModal());
    root.querySelectorAll("#modal-close,#modal-close-2").forEach((el) => el.addEventListener("click", () => { this._modal = null; this._pendingUpdate = this._modal?.confirmKind === "offline_update" ? null : this._pendingUpdate; this._render(); }));
    const bindSearch = (selector) => root.querySelector(selector)?.addEventListener("input", (ev) => { this._search = ev.target.value; const other = selector === "#global-search" ? root.querySelector("#dashboard-search") : root.querySelector("#global-search"); if (other) other.value = this._search; this._filterDom(); });
    bindSearch("#global-search"); bindSearch("#dashboard-search");
    const groupHandler = (ev) => { this._group = ev.target.value; const other = ev.target.id === "group-filter" ? root.querySelector("#dashboard-group") : root.querySelector("#group-filter"); if (other) other.value = this._group; this._filterDom(); };
    root.querySelector("#group-filter")?.addEventListener("change", groupHandler); root.querySelector("#dashboard-group")?.addEventListener("change", groupHandler);
    root.querySelector("#dashboard-tag")?.addEventListener("change", (ev) => { this._tag = ev.target.value; this._filterDom(); });
    const fav = () => { this._favoritesOnly = !this._favoritesOnly; this._render(); };
    root.querySelector("#favorite-filter")?.addEventListener("click", fav); root.querySelector("#dashboard-favorite")?.addEventListener("click", fav);
  }
}

if (!customElements.get("nanokvm-remote-server-panel")) customElements.define("nanokvm-remote-server-panel", NanoKVMRemoteServerPanel);
