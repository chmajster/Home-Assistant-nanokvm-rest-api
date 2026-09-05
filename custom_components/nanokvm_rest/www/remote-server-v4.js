const $ = (s, root = document) => root.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>'"]/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);
const fmtBytes = (n) => {
  if (!Number.isFinite(n) || n < 0) return "—";
  const u = ["B","KiB","MiB","GiB","TiB"]; let i = 0; let v = n;
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i += 1; }
  return `${v.toFixed(i ? 1 : 0)} ${u[i]}`;
};
const fmtDate = (v, lang) => { try { return v ? new Intl.DateTimeFormat(lang, {dateStyle:"short", timeStyle:"short"}).format(new Date(v)) : "—"; } catch (_) { return v || "—"; } };

const T = {
  pl: {
    title:"Remote Server", dashboard:"Dashboard", device:"Urządzenie", updates:"Update Center", media:"Virtual Media", hid:"HID Toolbox", maintenance:"Serwis", native:"Natywny UI",
    online:"Online", offline:"Offline", host:"Host", refresh:"Odśwież", search:"Szukaj KVM...", allGroups:"Wszystkie grupy", allTags:"Wszystkie tagi", favorites:"Ulubione",
    current:"Obecna", latest:"Najnowsza", channel:"Kanał", stable:"Stable", preview:"Preview", update:"Aktualizuj", status:"Status", history:"Historia aktualizacji",
    staged:"Staged updates", stagedDesc:"Aktualizuje urządzenia kolejno. Następny KVM ruszy dopiero po potwierdzonym powrocie poprzedniego.", startStaged:"Uruchom staged update", cancel:"Anuluj", selected:"Wybrane",
    offlineUpdate:"Offline update", choosePackage:"Wybierz nanokvm_X.Y.Z.tar.gz", sha:"SHA-256 (opcjonalnie)", uploadUpdate:"Wyślij update",
    library:"Biblioteka ISO", uploadIso:"Upload ISO", chooseIso:"Wybierz plik .iso", upload:"Wyślij", downloadUrl:"Pobierz ISO z URL", startDownload:"Rozpocznij pobieranie", transfer:"Transfer", cancelDownload:"Anuluj pobieranie",
    mounted:"Zamontowany", type:"Typ", size:"Rozmiar", added:"Dodano", source:"Źródło", mountCd:"Mount CD-ROM", mountUsb:"Mount USB", unmount:"Odmontuj", deleteSelected:"Usuń wybrane", sortName:"Nazwa", sortDate:"Data", sortSize:"Rozmiar",
    hidMode:"Tryb HID", normal:"Normal", hidOnly:"HID-only", hidModeWarn:"Zmiana trybu HID powoduje restart NanoKVM.", leds:"Diody klawiatury", num:"NumLock", caps:"CapsLock", scroll:"ScrollLock", known:"Stan znany", resetHid:"Reset HID", reconnect:"Połącz ponownie klawiaturę/mysz", paste:"Wklej tekst", send:"Wyślij",
    powerOn:"Power On", power:"Power", reset:"Reset", forceOff:"Force Off", reboot:"Reboot NanoKVM", editMeta:"Metadane", group:"Grupa", tags:"Tagi (przecinki)", save:"Zapisz",
    wol:"Profile Wake-on-LAN", name:"Nazwa", mac:"MAC", add:"Dodaj", run:"Uruchom", edit:"Edytuj", del:"Usuń", events:"Historia zdarzeń", noData:"Brak danych", open:"Otwórz", working:"Przetwarzanie...", success:"Gotowe", failed:"Błąd", upToDate:"Aktualne", queued:"W kolejce", waiting:"Oczekiwanie na powrót", updating:"Aktualizacja", unknown:"Nieznany", health:"Health", confirmDanger:"Potwierdź operację krytyczną", noDevices:"Brak skonfigurowanych NanoKVM"
  },
  en: {
    title:"Remote Server", dashboard:"Dashboard", device:"Device", updates:"Update Center", media:"Virtual Media", hid:"HID Toolbox", maintenance:"Maintenance", native:"Native UI",
    online:"Online", offline:"Offline", host:"Host", refresh:"Refresh", search:"Search KVM...", allGroups:"All groups", allTags:"All tags", favorites:"Favorites",
    current:"Current", latest:"Latest", channel:"Channel", stable:"Stable", preview:"Preview", update:"Update", status:"Status", history:"Update history",
    staged:"Staged updates", stagedDesc:"Updates devices sequentially. The next KVM starts only after the previous one returns and confirms its new version.", startStaged:"Start staged update", cancel:"Cancel", selected:"Selected",
    offlineUpdate:"Offline update", choosePackage:"Choose nanokvm_X.Y.Z.tar.gz", sha:"SHA-256 (optional)", uploadUpdate:"Upload update",
    library:"ISO Library", uploadIso:"Upload ISO", chooseIso:"Choose .iso file", upload:"Upload", downloadUrl:"Download ISO from URL", startDownload:"Start download", transfer:"Transfer", cancelDownload:"Cancel download",
    mounted:"Mounted", type:"Type", size:"Size", added:"Added", source:"Source", mountCd:"Mount CD-ROM", mountUsb:"Mount USB", unmount:"Unmount", deleteSelected:"Delete selected", sortName:"Name", sortDate:"Date", sortSize:"Size",
    hidMode:"HID mode", normal:"Normal", hidOnly:"HID-only", hidModeWarn:"Changing HID mode reboots NanoKVM.", leds:"Keyboard LEDs", num:"NumLock", caps:"CapsLock", scroll:"ScrollLock", known:"Known state", resetHid:"Reset HID", reconnect:"Reconnect keyboard/mouse", paste:"Paste text", send:"Send",
    powerOn:"Power On", power:"Power", reset:"Reset", forceOff:"Force Off", reboot:"Reboot NanoKVM", editMeta:"Metadata", group:"Group", tags:"Tags (comma separated)", save:"Save",
    wol:"Wake-on-LAN profiles", name:"Name", mac:"MAC", add:"Add", run:"Run", edit:"Edit", del:"Delete", events:"Event history", noData:"No data", open:"Open", working:"Working...", success:"Done", failed:"Error", upToDate:"Up to date", queued:"Queued", waiting:"Waiting for return", updating:"Updating", unknown:"Unknown", health:"Health", confirmDanger:"Confirm critical operation", noDevices:"No configured NanoKVM devices"
  }
};

class NanoKVMRemoteServerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this._hass = null; this._devices = []; this._selected = localStorage.getItem("nanokvm-remote-selected") || "";
    this._view = localStorage.getItem("nanokvm-remote-v4-view") || "dashboard";
    this._status = null; this._updates = []; this._batch = null; this._media = null; this._hid = null; this._history = [];
    this._search = ""; this._group = ""; this._tag = ""; this._mediaSearch = ""; this._mediaSort = "name";
    this._staged = new Set(); this._mediaSelected = new Set(); this._busy = false; this._notice = ""; this._noticeError = false;
    this._wolEdit = null; this._timer = null;
  }
  set hass(value) {
    const first = !this._hass;
    this._hass = value;
    if (first) this._bootstrap();
  }
  get hass() { return this._hass; }
  connectedCallback() { if (this._hass && !this._devices.length) this._bootstrap(); }
  disconnectedCallback() { clearInterval(this._timer); this._timer = null; }
  get lang() { return (this._hass?.language || "en").toLowerCase().startsWith("pl") ? "pl" : "en"; }
  get t() { return T[this.lang]; }

  async _api(type, data = {}) { return this._hass.callWS({type, ...data}); }
  async _bootstrap() {
    await this._loadDevices();
    await Promise.all([this._loadUpdates(), this._loadHistory()]);
    if (this._selected) await this._loadSelected(false);
    this._render();
    clearInterval(this._timer);
    this._timer = setInterval(() => this._poll(), 5000);
  }
  async _poll() {
    if (!this._hass || this._busy) return;
    try {
      if (this._view === "updates") await this._loadUpdates(false);
      if (this._view === "media" && this._selected) await this._loadMedia(false);
      if (this._view === "hid" && this._selected) await this._loadHid(false);
      if (["device","maintenance"].includes(this._view) && this._selected) await this._loadStatus(false, false);
      this._render();
    } catch (_) {}
  }
  async _loadDevices(render = true) {
    try {
      const r = await this._api("nanokvm_rest/panel/list"); this._devices = r.devices || [];
      if (!this._selected || !this._devices.some(d => d.entry_id === this._selected)) this._selected = this._devices[0]?.entry_id || "";
    } catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadStatus(render = true, touch = false) {
    if (!this._selected) return;
    try { this._status = await this._api("nanokvm_rest/panel/status", {entry_id:this._selected, touch}); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadUpdates(render = true) {
    try { const r = await this._api("nanokvm_rest/panel/update/list"); this._updates = r.devices || []; this._batch = r.batch || null; }
    catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadMedia(render = true) {
    if (!this._selected) return;
    try { this._media = await this._api("nanokvm_rest/panel/media/library", {entry_id:this._selected}); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadHid(render = true) {
    if (!this._selected) return;
    try { this._hid = await this._api("nanokvm_rest/panel/hid/status", {entry_id:this._selected}); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadHistory(render = true) {
    try { const r = await this._api("nanokvm_rest/panel/history", {limit:200}); this._history = r.events || []; }
    catch (e) { this._setNotice(e.message || String(e), true); }
    if (render) this._render();
  }
  async _loadSelected(touch = true) {
    await this._loadStatus(false, touch);
    if (this._view === "media") await this._loadMedia(false);
    if (this._view === "hid") await this._loadHid(false);
  }
  _setNotice(text, error = false) { this._notice = text; this._noticeError = error; }
  _device() { return this._devices.find(d => d.entry_id === this._selected) || null; }
  _canEmbed(url) { try { const u = new URL(url); return !(location.protocol === "https:" && u.protocol === "http:"); } catch (_) { return false; } }
  _confirm(text) { return window.confirm(text); }

  async _select(id) {
    this._selected = id; localStorage.setItem("nanokvm-remote-selected", id); this._status = null; this._media = null; this._hid = null;
    if (this._view === "dashboard") this._view = "device";
    await this._loadSelected(true); this._render();
  }
  async _switchView(view) {
    this._view = view; localStorage.setItem("nanokvm-remote-v4-view", view);
    if (view === "updates") await this._loadUpdates(false);
    if (view === "media") await this._loadMedia(false);
    if (view === "hid") await this._loadHid(false);
    if (["device","maintenance","native"].includes(view)) await this._loadStatus(false, false);
    this._render();
  }
  async _action(action, extra = {}, dangerous = false) {
    if (!this._selected || this._busy) return;
    if (dangerous && !this._confirm(`${this.t.confirmDanger}: ${action}?`)) return;
    this._busy = true; this._setNotice(this.t.working); this._render();
    try {
      await this._api("nanokvm_rest/panel/action", {entry_id:this._selected, action, ...extra});
      this._setNotice(this.t.success); await Promise.all([this._loadStatus(false,false), this._loadHistory(false), this._loadDevices(false)]);
    } catch (e) { this._setNotice(e.message || String(e), true); }
    this._busy = false; this._render();
  }
  async _quick(entryId, action, dangerous = false) {
    if (dangerous && !this._confirm(`${this.t.confirmDanger}: ${action}?`)) return;
    try { await this._api("nanokvm_rest/panel/action", {entry_id:entryId, action}); this._setNotice(this.t.success); await this._loadDevices(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _toggleDeviceFavorite(id, favorite) {
    try { await this._api("nanokvm_rest/panel/metadata/update", {entry_id:id, favorite}); await this._loadDevices(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _saveMetadata() {
    const group = $("#meta-group", this.shadowRoot)?.value || "";
    const tags = ($("#meta-tags", this.shadowRoot)?.value || "").split(",").map(v=>v.trim()).filter(Boolean);
    try { await this._api("nanokvm_rest/panel/metadata/update", {entry_id:this._selected, group, tags}); await this._loadDevices(false); await this._loadStatus(false,false); this._setNotice(this.t.success); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }

  async _setChannel(entryId, channel) {
    try { await this._api("nanokvm_rest/panel/update/channel", {entry_id:entryId, channel}); this._setNotice(this.t.success); await this._loadUpdates(false); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _startUpdate(entryId) {
    if (!this._confirm(`${this.t.update}: ${this._devices.find(d=>d.entry_id===entryId)?.title || entryId}?`)) return;
    try { await this._api("nanokvm_rest/panel/update/start", {entry_id:entryId}); this._setNotice(this.t.queued); await this._loadUpdates(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _startStaged() {
    const entry_ids = [...this._staged]; if (!entry_ids.length) return;
    if (!this._confirm(`${this.t.startStaged}: ${entry_ids.length}?`)) return;
    try { await this._api("nanokvm_rest/panel/update/staged/start", {entry_ids}); this._setNotice(this.t.queued); await this._loadUpdates(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _cancelStaged() {
    try { await this._api("nanokvm_rest/panel/update/staged/cancel"); await this._loadUpdates(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._render();
  }
  async _offlineUpdate() {
    const file = $("#offline-file", this.shadowRoot)?.files?.[0]; const sha = $("#offline-sha", this.shadowRoot)?.value?.trim() || "";
    if (!file || !this._selected) return;
    if (!this._confirm(`${this.t.offlineUpdate}: ${file.name}?`)) return;
    this._busy = true; this._setNotice(this.t.working); this._render();
    const form = new FormData(); form.append("file", file);
    const headers = {Authorization:`Bearer ${this._hass.auth.accessToken}`}; if (sha) headers["X-SHA256-Checksum"] = sha;
    try { const r = await fetch(`/api/nanokvm_rest/offline-update/${encodeURIComponent(this._selected)}`, {method:"POST", headers, body:form}); const j = await r.json().catch(()=>({})); if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`); this._setNotice(this.t.success); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._busy = false; this._render();
  }

  async _mediaFavorite(path, favorite) {
    try { await this._api("nanokvm_rest/panel/media/favorite", {entry_id:this._selected, path, favorite}); await this._loadMedia(false); }
    catch (e) { this._setNotice(e.message || String(e), true); } this._render();
  }
  async _mount(path, cdrom) {
    try { await this._api("nanokvm_rest/panel/media/mount", {entry_id:this._selected, path, cdrom}); this._setNotice(this.t.success); await this._loadMedia(false); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); } this._render();
  }
  async _deleteMedia() {
    const paths = [...this._mediaSelected]; if (!paths.length || !this._confirm(`${this.t.deleteSelected}: ${paths.length}?`)) return;
    try { await this._api("nanokvm_rest/panel/media/delete_many", {entry_id:this._selected, paths}); this._mediaSelected.clear(); this._setNotice(this.t.success); await this._loadMedia(false); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); } this._render();
  }
  async _uploadIso() {
    const file = $("#iso-file", this.shadowRoot)?.files?.[0]; const sha = $("#iso-sha", this.shadowRoot)?.value?.trim() || ""; if (!file) return;
    this._busy = true; this._setNotice(`${this.t.working} ${fmtBytes(file.size)}`); this._render();
    const form = new FormData(); form.append("file", file);
    const headers = {Authorization:`Bearer ${this._hass.auth.accessToken}`}; if (sha) headers["X-SHA256-Sum"] = sha;
    try { const r = await fetch(`/api/nanokvm_rest/iso-upload/${encodeURIComponent(this._selected)}`, {method:"POST", headers, body:form}); const j = await r.json().catch(()=>({})); if (!r.ok) throw new Error(j.error || `HTTP ${r.status}`); this._setNotice(this.t.success); await this._loadMedia(false); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); }
    this._busy = false; this._render();
  }
  async _downloadIso() {
    const url = $("#iso-url", this.shadowRoot)?.value?.trim() || ""; const sha256 = $("#url-sha", this.shadowRoot)?.value?.trim() || ""; if (!url) return;
    try { await this._api("nanokvm_rest/panel/media/download/start", {entry_id:this._selected, url, sha256}); this._setNotice(this.t.queued); await this._loadMedia(false); await this._loadHistory(false); }
    catch (e) { this._setNotice(e.message || String(e), true); } this._render();
  }
  async _cancelDownload() { try { await this._api("nanokvm_rest/panel/media/download/cancel", {entry_id:this._selected}); await this._loadMedia(false); } catch(e){this._setNotice(e.message||String(e),true);} this._render(); }

  async _hidAction(action, extra = {}, dangerous = false) {
    if (dangerous && !this._confirm(this.t.hidModeWarn)) return;
    try { const r = await this._api("nanokvm_rest/panel/hid/action", {entry_id:this._selected, action, ...extra}); this._setNotice(r.reboot_expected ? this.t.hidModeWarn : this.t.success); if (!r.reboot_expected) await this._loadHid(false); await this._loadHistory(false); }
    catch(e){this._setNotice(e.message||String(e),true);} this._render();
  }
  async _paste() { const text = $("#paste-text", this.shadowRoot)?.value || ""; const language = $("#paste-lang", this.shadowRoot)?.value || "en"; if(text) await this._hidAction("paste", {text, language}); }

  async _saveWol() {
    const name = $("#wol-name", this.shadowRoot)?.value?.trim() || ""; const mac = $("#wol-mac", this.shadowRoot)?.value?.trim() || ""; if (!name || !mac) return;
    try { await this._api("nanokvm_rest/panel/wol/save", {entry_id:this._selected, name, mac, profile_id:this._wolEdit?.id || ""}); this._wolEdit=null; await this._loadStatus(false,false); this._setNotice(this.t.success); }
    catch(e){this._setNotice(e.message||String(e),true);} this._render();
  }
  async _runWol(id){ try{await this._api("nanokvm_rest/panel/wol/run",{entry_id:this._selected,profile_id:id});this._setNotice(this.t.success);await this._loadHistory(false);}catch(e){this._setNotice(e.message||String(e),true);}this._render(); }
  async _deleteWol(id){ if(!this._confirm(this.t.del+"?"))return;try{await this._api("nanokvm_rest/panel/wol/delete",{entry_id:this._selected,profile_id:id});await this._loadStatus(false,false);this._setNotice(this.t.success);}catch(e){this._setNotice(e.message||String(e),true);}this._render(); }

  _filterDevices() {
    const q=this._search.trim().toLowerCase();
    return this._devices.filter(d=>{
      const hay=[d.title,d.hostname,d.base_url,d.hardware,d.group,...(d.tags||[])].join(" ").toLowerCase();
      return (!q||hay.includes(q))&&(!this._group||d.group===this._group)&&(!this._tag||(d.tags||[]).includes(this._tag));
    });
  }
  _updateStateLabel(s){ return ({success:this.t.success,error:this.t.failed,up_to_date:this.t.upToDate,queued:this.t.queued,waiting:this.t.waiting,updating:this.t.updating})[s] || s || "idle"; }

  _renderDashboard(){
    const devices=this._filterDevices(); const groups=[...new Set(this._devices.map(d=>d.group).filter(Boolean))].sort(); const tags=[...new Set(this._devices.flatMap(d=>d.tags||[]))].sort();
    const online=this._devices.filter(d=>d.available).length, powered=this._devices.filter(d=>d.power===true).length, issues=this._devices.filter(d=>d.health?.state!=="healthy").length;
    return `<section class="view"><div class="stats"><div><b>${this._devices.length}</b><span>NanoKVM</span></div><div><b>${online}</b><span>${this.t.online}</span></div><div><b>${powered}</b><span>Host ON</span></div><div><b>${issues}</b><span>Health issues</span></div></div>
      <div class="toolbar"><input id="search" placeholder="${this.t.search}" value="${esc(this._search)}"><select id="group"><option value="">${this.t.allGroups}</option>${groups.map(g=>`<option ${g===this._group?"selected":""}>${esc(g)}</option>`).join("")}</select><select id="tag"><option value="">${this.t.allTags}</option>${tags.map(g=>`<option ${g===this._tag?"selected":""}>${esc(g)}</option>`).join("")}</select><button id="refresh-all">↻ ${this.t.refresh}</button></div>
      <div class="device-grid">${devices.map(d=>`<article class="device-card"><div class="card-head"><button class="device-link" data-select="${esc(d.entry_id)}"><span class="dot ${d.available?"on":"off"}"></span><span><b>${esc(d.hostname||d.title)}</b><small>${esc(d.group||d.hardware||d.base_url||"")}</small></span></button><button class="star ${d.favorite?"active":""}" data-fav="${esc(d.entry_id)}" data-value="${!d.favorite}">★</button></div><div class="badges"><span class="pill ${d.available?"ok":"bad"}">${d.available?this.t.online:this.t.offline}</span><span class="pill">Host ${d.power===true?"ON":d.power===false?"OFF":"—"}</span><span class="pill ${d.health?.state||""}">${this.t.health} ${d.health?.score??0}%</span></div><div class="quick"><button data-quick="power_on" data-entry="${esc(d.entry_id)}">⏻</button><button data-quick="reset_hid" data-entry="${esc(d.entry_id)}">⌨</button><button class="danger" data-quick="reset" data-entry="${esc(d.entry_id)}" data-danger="1">↻</button>${d.base_url?`<a href="${esc(d.base_url)}" target="_blank" rel="noopener">↗</a>`:""}</div>${(d.tags||[]).length?`<div class="tags">${d.tags.map(x=>`<span>${esc(x)}</span>`).join("")}</div>`:""}</article>`).join("")||`<div class="empty">${this.t.noDevices}</div>`}</div></section>`;
  }

  _renderDevice(){ const d=this._status||this._device(); if(!d)return `<div class="empty">${this.t.noData}</div>`; return `<section class="view"><div class="hero"><div><span class="eyebrow">NanoKVM</span><h2>${esc(d.hostname||d.title)}</h2><p>${esc(d.base_url||"")}</p></div><div class="hero-badges"><span class="pill ${d.available?"ok":"bad"}">${d.available?this.t.online:this.t.offline}</span><span class="pill">Host ${d.power===true?"ON":d.power===false?"OFF":"—"}</span></div></div><div class="grid2"><article class="panel"><h3>Power & KVM</h3><div class="action-grid"><button data-action="power_on">${this.t.powerOn}</button><button data-action="power_press">${this.t.power}</button><button class="danger" data-action="reset" data-danger="1">${this.t.reset}</button><button class="danger" data-action="force_off" data-danger="1">${this.t.forceOff}</button><button data-action="reset_hid">${this.t.resetHid}</button><button class="danger" data-action="reboot_nanokvm" data-danger="1">${this.t.reboot}</button></div></article><article class="panel"><h3>${this.t.editMeta}</h3><label>${this.t.group}<input id="meta-group" value="${esc(d.group||"")}"></label><label>${this.t.tags}<input id="meta-tags" value="${esc((d.tags||[]).join(", "))}"></label><button id="save-meta">${this.t.save}</button></article></div><div class="facts"><div><span>Hardware</span><b>${esc(d.hardware||"—")}</b></div><div><span>App</span><b>${esc(d.application_version||"—")}</b></div><div><span>HDMI</span><b>${d.hdmi_signal===true?"Signal":d.hdmi_signal===false?"No signal":"—"}</b></div><div><span>${this.t.health}</span><b>${d.health?.score??0}%</b></div></div></section>`; }

  _renderUpdates(){
    const batch=this._batch; const selected=this._staged.size; const updateEvents=this._history.filter(e=>String(e.event||"").includes("update")).slice(0,30);
    return `<section class="view"><div class="section-title"><div><span class="eyebrow">Fleet management</span><h2>${this.t.updates}</h2></div><button id="updates-refresh">↻ ${this.t.refresh}</button></div>${batch&&["queued","running"].includes(batch.state)?`<div class="batch"><div><b>${this.t.staged}</b><span>${esc(batch.state)} · ${(batch.index||0)+1}/${(batch.entry_ids||[]).length}</span></div><progress max="${(batch.entry_ids||[]).length}" value="${batch.index||0}"></progress><button id="cancel-staged">${this.t.cancel}</button></div>`:""}<article class="panel staged-box"><h3>${this.t.staged}</h3><p>${this.t.stagedDesc}</p><button id="start-staged" ${selected?"":"disabled"}>${this.t.startStaged} (${selected})</button></article><div class="update-grid">${this._updates.map(u=>{const r=u.runtime||{state:"idle"};return `<article class="update-card ${r.state||""}"><div class="card-head"><label class="check"><input type="checkbox" data-stage="${esc(u.entry_id)}" ${this._staged.has(u.entry_id)?"checked":""} ${!u.admin?"disabled":""}> <b>${esc(u.title)}</b></label><span class="pill ${u.available?"ok":"bad"}">${u.available?this.t.online:this.t.offline}</span></div><div class="version-pair"><div><span>${this.t.current}</span><b>${esc(u.current||"—")}</b></div><div><span>${this.t.latest}</span><b>${esc(u.latest||"—")}</b></div></div><label>${this.t.channel}<select data-channel="${esc(u.entry_id)}" ${!u.admin?"disabled":""}><option value="stable" ${u.channel==="stable"?"selected":""}>Stable</option><option value="preview" ${u.channel==="preview"?"selected":""}>Preview</option></select></label><div class="runtime"><span>${this.t.status}</span><b>${esc(this._updateStateLabel(r.state))}</b><small>${esc(r.message||u.error||"")}</small></div><button data-update="${esc(u.entry_id)}" ${!u.admin||["updating","waiting","queued"].includes(r.state)||!u.update_available?"disabled":""}>${u.update_available?this.t.update:this.t.upToDate}</button></article>`}).join("")}</div><div class="grid2"><article class="panel"><h3>${this.t.offlineUpdate}</h3><p>${esc(this._device()?.title||"")}</p><input id="offline-file" type="file" accept=".tar.gz,application/gzip"><input id="offline-sha" placeholder="${this.t.sha}"><button id="offline-update">${this.t.uploadUpdate}</button></article><article class="panel"><h3>${this.t.history}</h3>${this._renderEvents(updateEvents)}</article></div></section>`;
  }

  _mediaItems(){ let items=[...(this._media?.items||[])]; const q=this._mediaSearch.trim().toLowerCase(); if(q)items=items.filter(x=>[x.name,x.type,x.source].join(" ").toLowerCase().includes(q)); items.sort((a,b)=>{ if(this._mediaSort==="date")return String(b.added_at||"").localeCompare(String(a.added_at||"")); if(this._mediaSort==="size")return (b.size??-1)-(a.size??-1); return String(a.name).localeCompare(String(b.name)); }); return items; }
  _renderMedia(){ const m=this._media||{items:[],transfer:{}}; const tr=m.transfer||{}; const items=this._mediaItems(); const pct=parseFloat(String(tr.percentage||"").replace("%","")); return `<section class="view"><div class="section-title"><div><span class="eyebrow">Virtual Media</span><h2>${this.t.library}</h2></div><button id="media-refresh">↻ ${this.t.refresh}</button></div>${tr.status&&tr.status!=="idle"?`<div class="transfer"><div><b>${this.t.transfer}: ${esc(tr.status)}</b><span>${esc(tr.file||"")}</span></div>${Number.isFinite(pct)?`<progress max="100" value="${pct}"></progress><b>${pct}%</b>`:""}${tr.status==="in_progress"?`<button id="cancel-download">${this.t.cancelDownload}</button>`:""}</div>`:""}<div class="grid2"><article class="panel"><h3>${this.t.uploadIso}</h3><input id="iso-file" type="file" accept=".iso,application/octet-stream"><input id="iso-sha" placeholder="${this.t.sha}"><button id="upload-iso">${this.t.upload}</button></article><article class="panel"><h3>${this.t.downloadUrl}</h3><input id="iso-url" type="url" placeholder="https://example/ubuntu.iso"><input id="url-sha" placeholder="${this.t.sha}"><button id="download-iso" ${tr.status==="in_progress"?"disabled":""}>${this.t.startDownload}</button></article></div><div class="toolbar"><input id="media-search" value="${esc(this._mediaSearch)}" placeholder="${this.t.search}"><select id="media-sort"><option value="name" ${this._mediaSort==="name"?"selected":""}>${this.t.sortName}</option><option value="date" ${this._mediaSort==="date"?"selected":""}>${this.t.sortDate}</option><option value="size" ${this._mediaSort==="size"?"selected":""}>${this.t.sortSize}</option></select><button class="danger" id="delete-media" ${this._mediaSelected.size?"":"disabled"}>${this.t.deleteSelected} (${this._mediaSelected.size})</button></div><div class="media-list">${items.map(x=>`<article class="media-row ${x.mounted?"mounted":""}"><label class="check"><input type="checkbox" data-media-select="${esc(x.path)}" ${this._mediaSelected.has(x.path)?"checked":""} ${x.mounted?"disabled":""}></label><button class="star ${x.favorite?"active":""}" data-media-fav="${esc(x.path)}" data-value="${!x.favorite}">★</button><div class="media-name"><b>${esc(x.name)}</b><span>${x.mounted?`● ${this.t.mounted} · `:""}${esc(x.type)} · ${fmtBytes(x.size)} · ${fmtDate(x.added_at,this.lang)} · ${esc(x.source)}</span></div><div class="media-actions"><button data-mount-cd="${esc(x.path)}">${this.t.mountCd}</button><button data-mount-usb="${esc(x.path)}">${this.t.mountUsb}</button></div></article>`).join("")||`<div class="empty">${this.t.noData}</div>`}</div>${m.mounted?`<div class="mounted-bar"><span>${this.t.mounted}: <b>${esc(m.mounted.split("/").pop())}</b> (${m.cdrom?"CD-ROM":"USB"})</span><button id="unmount">${this.t.unmount}</button></div>`:""}</section>`; }

  _renderHid(){ const h=this._hid||{mode:"unknown",leds:{}}; const l=h.leds||{}; const led=(name,val)=>`<div class="led"><span class="led-dot ${l.known&&val?"on":""}"></span><b>${name}</b><small>${l.known?(val?"ON":"OFF"):this.t.unknown}</small></div>`; return `<section class="view"><div class="section-title"><div><span class="eyebrow">USB HID</span><h2>${this.t.hid}</h2></div><button id="hid-refresh">↻ ${this.t.refresh}</button></div><div class="grid2"><article class="panel"><h3>${this.t.hidMode}</h3><p class="warn">${this.t.hidModeWarn}</p><select id="hid-mode"><option value="normal" ${h.mode==="normal"?"selected":""}>${this.t.normal}</option><option value="hid-only" ${h.mode==="hid-only"?"selected":""}>${this.t.hidOnly}</option></select><button class="danger" id="set-hid-mode">${this.t.save}</button><div class="action-grid"><button id="hid-reset">${this.t.resetHid}</button><button id="hid-reconnect">${this.t.reconnect}</button></div></article><article class="panel"><h3>${this.t.leds}</h3><div class="leds">${led(this.t.num,l.numLock)}${led(this.t.caps,l.capsLock)}${led(this.t.scroll,l.scrollLock)}</div><small>${l.updatedAt?fmtDate(l.updatedAt,this.lang):""}</small></article></div><article class="panel"><h3>${this.t.paste}</h3><textarea id="paste-text" rows="6" placeholder="${this.t.paste}"></textarea><div class="inline"><select id="paste-lang"><option value="en">EN</option><option value="pl">PL</option></select><button id="paste-send">${this.t.send}</button></div></article></section>`; }

  _renderMaintenance(){ const d=this._status||{}; const profiles=d.wol_profiles||[]; const edit=this._wolEdit||{}; const events=this._history.filter(e=>!this._selected||e.entry_id===this._selected).slice(0,50); return `<section class="view"><div class="grid2"><article class="panel"><h3>${this.t.wol}</h3><div class="inline"><input id="wol-name" placeholder="${this.t.name}" value="${esc(edit.name||"")}"><input id="wol-mac" placeholder="AA:BB:CC:DD:EE:FF" value="${esc(edit.mac||"")}"><button id="wol-save">${edit.id?this.t.save:this.t.add}</button></div><div class="profile-list">${profiles.map(p=>`<div><span><b>${esc(p.name)}</b><small>${esc(p.mac)}</small></span><span><button data-wol-run="${esc(p.id)}">${this.t.run}</button><button data-wol-edit="${esc(p.id)}">${this.t.edit}</button><button class="danger" data-wol-del="${esc(p.id)}">${this.t.del}</button></span></div>`).join("")||this.t.noData}</div></article><article class="panel"><h3>${this.t.events}</h3>${this._renderEvents(events)}</article></div></section>`; }
  _renderEvents(events){ return events.length?`<div class="events">${events.map(e=>`<div><span class="event-dot ${e.result==="error"?"bad":"ok"}"></span><span><b>${esc(String(e.event||"").replaceAll("_"," "))}</b><small>${esc(e.actor||"system")}${e.details?.message?` · ${esc(e.details.message)}`:""}</small></span><time>${fmtDate(e.timestamp,this.lang)}</time></div>`).join("")}</div>`:`<div class="empty">${this.t.noData}</div>`; }
  _renderNative(){ const d=this._status||this._device(); if(!d?.base_url)return `<div class="empty">${this.t.noData}</div>`; return `<section class="view native"><div class="section-title"><h2>${this.t.native}</h2><a class="button" href="${esc(d.base_url)}" target="_blank" rel="noopener">${this.t.open} ↗</a></div>${this._canEmbed(d.base_url)?`<iframe src="${esc(d.base_url)}" title="NanoKVM"></iframe>`:`<div class="empty">Browser blocked HTTP content inside HTTPS Home Assistant. <a href="${esc(d.base_url)}" target="_blank">${this.t.open}</a></div>`}</section>`; }

  _renderSidebar(){ return `<aside><div class="brand"><div class="logo">K</div><div><b>${this.t.title}</b><small>NanoKVM REST</small></div></div><nav>${[["dashboard","▦",this.t.dashboard],["device","▣",this.t.device],["updates","⇧",this.t.updates],["media","◉",this.t.media],["hid","⌨",this.t.hid],["maintenance","⚙",this.t.maintenance],["native","↗",this.t.native]].map(([id,ic,l])=>`<button data-view="${id}" class="${this._view===id?"active":""}" ${id!=="dashboard"&&!this._selected?"disabled":""}><span>${ic}</span>${l}</button>`).join("")}</nav><div class="device-picker"><span>NanoKVM</span>${this._devices.map(d=>`<button data-select="${esc(d.entry_id)}" class="${d.entry_id===this._selected?"active":""}"><span class="dot ${d.available?"on":"off"}"></span><span><b>${esc(d.hostname||d.title)}</b><small>Host ${d.power===true?"ON":d.power===false?"OFF":"—"}</small></span></button>`).join("")}</div></aside>`; }
  _renderBottom(){ return `<nav class="bottom">${[["dashboard","▦"],["device","▣"],["updates","⇧"],["media","◉"],["hid","⌨"],["maintenance","⚙"]].map(([id,ic])=>`<button data-view="${id}" class="${this._view===id?"active":""}"><b>${ic}</b><span>${this.t[id]||id}</span></button>`).join("")}</nav>`; }

  _styles(){ return `<style>:host{display:block;height:100%;--gap:16px;font-family:var(--paper-font-body1_-_font-family,Inter,system-ui,sans-serif);color:var(--primary-text-color);background:var(--primary-background-color)}*{box-sizing:border-box}button,input,select,textarea{font:inherit}button,.button{border:0;border-radius:12px;padding:10px 14px;background:var(--primary-color);color:var(--text-primary-color,#fff);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center;justify-content:center;gap:8px;min-height:42px}button:disabled{opacity:.45;cursor:not-allowed}.danger{background:var(--error-color,#db4437)!important;color:#fff!important}.app{display:grid;grid-template-columns:260px 1fr;height:100vh;overflow:hidden}aside{background:var(--card-background-color);border-right:1px solid var(--divider-color);padding:18px 14px;display:flex;flex-direction:column;gap:16px;overflow:auto}.brand{display:flex;align-items:center;gap:12px;padding:4px 6px}.brand .logo{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,var(--primary-color),#00bcd4);display:grid;place-items:center;color:#fff;font-weight:900;font-size:22px}.brand b{display:block;font-size:16px}.brand small,.device-picker small{display:block;color:var(--secondary-text-color);margin-top:2px}aside nav{display:grid;gap:6px}aside nav button{background:transparent;color:var(--primary-text-color);justify-content:flex-start}aside nav button.active{background:color-mix(in srgb,var(--primary-color) 16%,transparent);color:var(--primary-color)}.device-picker{display:grid;gap:6px;margin-top:auto}.device-picker>span{font-size:12px;text-transform:uppercase;color:var(--secondary-text-color);padding:0 8px}.device-picker button{background:transparent;color:var(--primary-text-color);justify-content:flex-start;padding:9px}.device-picker button.active{background:var(--secondary-background-color)}.device-picker button>span:last-child{min-width:0;text-align:left}.device-picker b{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.dot{width:9px;height:9px;border-radius:50%;background:#8a8a8a;flex:0 0 auto}.dot.on{background:#2eaf5d;box-shadow:0 0 0 4px color-mix(in srgb,#2eaf5d 15%,transparent)}.dot.off{background:var(--error-color,#db4437)}main{overflow:auto;padding:22px 24px 90px}.view{max-width:1440px;margin:auto}.notice{position:sticky;top:0;z-index:8;margin:0 auto 14px;max-width:900px;padding:11px 16px;border-radius:12px;background:var(--success-color,#2eaf5d);color:#fff}.notice.error{background:var(--error-color,#db4437)}.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:16px}.stats>div,.facts>div{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:18px;padding:18px}.stats b{display:block;font-size:30px}.stats span,.facts span,.version-pair span,.runtime span{color:var(--secondary-text-color);font-size:12px}.toolbar{display:flex;gap:10px;margin:14px 0 18px;flex-wrap:wrap}.toolbar input{flex:1;min-width:220px}.toolbar input,.toolbar select,input,select,textarea{border:1px solid var(--divider-color);background:var(--card-background-color);color:var(--primary-text-color);border-radius:12px;padding:11px 12px;outline:none}.device-grid,.update-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px}.device-card,.update-card,.panel{background:var(--card-background-color);border:1px solid var(--divider-color);border-radius:20px;padding:16px}.card-head,.section-title,.hero,.inline,.mounted-bar,.transfer,.batch{display:flex;align-items:center;justify-content:space-between;gap:12px}.device-link{background:transparent;color:var(--primary-text-color);padding:0;justify-content:flex-start;text-align:left}.device-link>span:last-child{display:block}.device-link b{display:block;font-size:16px}.device-link small,.media-name span,.profile-list small,.runtime small{display:block;color:var(--secondary-text-color);margin-top:4px}.star{background:transparent;color:var(--secondary-text-color);font-size:22px;padding:5px}.star.active{color:#ffb300}.badges,.tags,.quick{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.pill,.tags span{padding:5px 8px;border-radius:999px;background:var(--secondary-background-color);font-size:12px}.pill.ok{background:color-mix(in srgb,#2eaf5d 18%,var(--card-background-color));color:#2eaf5d}.pill.bad,.pill.critical{color:var(--error-color)}.pill.warning{color:#e6a100}.quick button,.quick a{width:42px;height:42px;padding:0;border-radius:12px;background:var(--secondary-background-color);color:var(--primary-text-color);display:grid;place-items:center;text-decoration:none}.hero{padding:6px 2px 18px}.hero h2,.section-title h2{margin:4px 0;font-size:28px}.hero p{margin:0;color:var(--secondary-text-color)}.eyebrow{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:var(--primary-color)}.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}.panel h3{margin:0 0 12px}.panel p{color:var(--secondary-text-color)}.panel label{display:grid;gap:6px;margin:10px 0}.action-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}.facts{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.facts b{display:block;margin-top:5px}.version-pair{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0}.version-pair>div,.runtime{padding:12px;border-radius:14px;background:var(--secondary-background-color)}.version-pair b,.runtime b{display:block;margin-top:4px}.update-card label select{width:100%}.runtime{margin:12px 0}.batch,.transfer,.mounted-bar{background:color-mix(in srgb,var(--primary-color) 10%,var(--card-background-color));border:1px solid color-mix(in srgb,var(--primary-color) 30%,var(--divider-color));padding:14px 16px;border-radius:16px;margin:12px 0}.batch>div span,.transfer>div span{display:block;color:var(--secondary-text-color);margin-top:3px;max-width:420px;overflow:hidden;text-overflow:ellipsis}.batch progress,.transfer progress{flex:1}.staged-box{margin:16px 0}.media-list{display:grid;gap:9px}.media-row{display:grid;grid-template-columns:auto auto 1fr auto;align-items:center;gap:10px;background:var(--card-background-color);border:1px solid var(--divider-color);padding:12px;border-radius:16px}.media-row.mounted{border-color:var(--primary-color)}.media-actions{display:flex;gap:7px}.check{display:flex!important;align-items:center;gap:8px!important}.leds{display:grid;grid-template-columns:repeat(3,1fr);gap:9px}.led{padding:14px;border-radius:14px;background:var(--secondary-background-color);text-align:center}.led-dot{display:block;width:14px;height:14px;border-radius:50%;background:#777;margin:0 auto 9px}.led-dot.on{background:#2eaf5d;box-shadow:0 0 14px #2eaf5d}.led small{display:block;color:var(--secondary-text-color);margin-top:4px}.warn{border-left:3px solid #e6a100;padding-left:10px}.profile-list{display:grid;gap:8px;margin-top:12px}.profile-list>div{display:flex;justify-content:space-between;align-items:center;gap:10px;padding:10px;background:var(--secondary-background-color);border-radius:12px}.profile-list>div>span:last-child{display:flex;gap:6px}.events{display:grid;gap:8px;max-height:520px;overflow:auto}.events>div{display:grid;grid-template-columns:auto 1fr auto;gap:10px;align-items:center;padding:10px;border-bottom:1px solid var(--divider-color)}.events small{display:block;color:var(--secondary-text-color);margin-top:3px}.events time{font-size:11px;color:var(--secondary-text-color)}.event-dot{width:9px;height:9px;border-radius:50%;background:#2eaf5d}.event-dot.bad{background:var(--error-color)}.empty{padding:38px;text-align:center;color:var(--secondary-text-color);background:var(--card-background-color);border:1px dashed var(--divider-color);border-radius:18px}.native iframe{width:100%;height:calc(100vh - 140px);border:1px solid var(--divider-color);border-radius:18px;background:#fff}.bottom{display:none}
@media(max-width:900px){.app{grid-template-columns:1fr}aside{display:none}main{padding:14px 12px 92px}.bottom{position:fixed;display:flex;left:0;right:0;bottom:0;z-index:20;background:var(--card-background-color);border-top:1px solid var(--divider-color);padding:7px max(7px,env(safe-area-inset-right)) calc(7px + env(safe-area-inset-bottom)) max(7px,env(safe-area-inset-left));overflow-x:auto}.bottom button{min-width:74px;flex:1;background:transparent;color:var(--secondary-text-color);padding:6px 5px;display:grid;gap:2px}.bottom button.active{color:var(--primary-color)}.bottom b{font-size:19px}.bottom span{font-size:10px}.stats{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.facts{grid-template-columns:repeat(2,1fr)}.media-row{grid-template-columns:auto auto 1fr}.media-actions{grid-column:1/-1}.hero{align-items:flex-start}.hero h2,.section-title h2{font-size:23px}.update-grid,.device-grid{grid-template-columns:1fr}.batch,.transfer{align-items:flex-start;flex-direction:column}.batch progress,.transfer progress{width:100%}}
@media(max-width:430px){main{padding-left:9px;padding-right:9px}.stats{gap:8px}.stats>div{padding:13px}.stats b{font-size:24px}.action-grid{grid-template-columns:1fr}.facts{grid-template-columns:1fr 1fr}.toolbar{display:grid;grid-template-columns:1fr 1fr}.toolbar input{grid-column:1/-1;min-width:0}.media-row{grid-template-columns:auto auto 1fr}.section-title{align-items:flex-start}.inline{align-items:stretch;flex-direction:column}.leds{grid-template-columns:1fr}.profile-list>div{align-items:flex-start;flex-direction:column}}</style>`; }

  _render(){ if(!this.shadowRoot)return; const body=this._view==="dashboard"?this._renderDashboard():this._view==="device"?this._renderDevice():this._view==="updates"?this._renderUpdates():this._view==="media"?this._renderMedia():this._view==="hid"?this._renderHid():this._view==="maintenance"?this._renderMaintenance():this._renderNative(); this.shadowRoot.innerHTML=`${this._styles()}<div class="app">${this._renderSidebar()}<main>${this._notice?`<div class="notice ${this._noticeError?"error":""}">${esc(this._notice)}</div>`:""}${body}</main>${this._renderBottom()}</div>`; this._bind(); }

  _bind(){ const r=this.shadowRoot;
    r.querySelectorAll("[data-view]").forEach(el=>el.onclick=()=>this._switchView(el.dataset.view)); r.querySelectorAll("[data-select]").forEach(el=>el.onclick=()=>this._select(el.dataset.select));
    r.querySelectorAll("[data-quick]").forEach(el=>el.onclick=()=>this._quick(el.dataset.entry,el.dataset.quick,el.dataset.danger==="1")); r.querySelectorAll("[data-fav]").forEach(el=>el.onclick=()=>this._toggleDeviceFavorite(el.dataset.fav,el.dataset.value==="true"));
    const search=$("#search",r); if(search)search.oninput=e=>{this._search=e.target.value;this._render()}; const group=$("#group",r); if(group)group.onchange=e=>{this._group=e.target.value;this._render()}; const tag=$("#tag",r); if(tag)tag.onchange=e=>{this._tag=e.target.value;this._render()}; const ra=$("#refresh-all",r); if(ra)ra.onclick=()=>this._bootstrap();
    r.querySelectorAll("[data-action]").forEach(el=>el.onclick=()=>this._action(el.dataset.action,{},el.dataset.danger==="1")); const sm=$("#save-meta",r); if(sm)sm.onclick=()=>this._saveMetadata();
    r.querySelectorAll("[data-stage]").forEach(el=>el.onchange=e=>{e.target.checked?this._staged.add(e.target.dataset.stage):this._staged.delete(e.target.dataset.stage);this._render()}); r.querySelectorAll("[data-channel]").forEach(el=>el.onchange=e=>this._setChannel(e.target.dataset.channel,e.target.value)); r.querySelectorAll("[data-update]").forEach(el=>el.onclick=()=>this._startUpdate(el.dataset.update)); const ss=$("#start-staged",r); if(ss)ss.onclick=()=>this._startStaged(); const cs=$("#cancel-staged",r); if(cs)cs.onclick=()=>this._cancelStaged(); const ur=$("#updates-refresh",r);if(ur)ur.onclick=async()=>{await this._loadUpdates(false);await this._loadHistory(false);this._render()}; const ou=$("#offline-update",r);if(ou)ou.onclick=()=>this._offlineUpdate();
    const mr=$("#media-refresh",r);if(mr)mr.onclick=()=>this._loadMedia(); const ms=$("#media-search",r);if(ms)ms.oninput=e=>{this._mediaSearch=e.target.value;this._render()}; const msort=$("#media-sort",r);if(msort)msort.onchange=e=>{this._mediaSort=e.target.value;this._render()}; r.querySelectorAll("[data-media-select]").forEach(el=>el.onchange=e=>{e.target.checked?this._mediaSelected.add(e.target.dataset.mediaSelect):this._mediaSelected.delete(e.target.dataset.mediaSelect);this._render()}); r.querySelectorAll("[data-media-fav]").forEach(el=>el.onclick=()=>this._mediaFavorite(el.dataset.mediaFav,el.dataset.value==="true")); r.querySelectorAll("[data-mount-cd]").forEach(el=>el.onclick=()=>this._mount(el.dataset.mountCd,true)); r.querySelectorAll("[data-mount-usb]").forEach(el=>el.onclick=()=>this._mount(el.dataset.mountUsb,false)); const dm=$("#delete-media",r);if(dm)dm.onclick=()=>this._deleteMedia(); const ui=$("#upload-iso",r);if(ui)ui.onclick=()=>this._uploadIso(); const di=$("#download-iso",r);if(di)di.onclick=()=>this._downloadIso(); const cd=$("#cancel-download",r);if(cd)cd.onclick=()=>this._cancelDownload(); const um=$("#unmount",r);if(um)um.onclick=()=>this._action("unmount_image");
    const hr=$("#hid-refresh",r);if(hr)hr.onclick=()=>this._loadHid(); const hm=$("#set-hid-mode",r);if(hm)hm.onclick=()=>this._hidAction("set_mode",{mode:$("#hid-mode",r)?.value||"normal"},true); const hreset=$("#hid-reset",r);if(hreset)hreset.onclick=()=>this._hidAction("reset"); const hrec=$("#hid-reconnect",r);if(hrec)hrec.onclick=()=>this._hidAction("reconnect"); const ps=$("#paste-send",r);if(ps)ps.onclick=()=>this._paste();
    const ws=$("#wol-save",r);if(ws)ws.onclick=()=>this._saveWol(); r.querySelectorAll("[data-wol-run]").forEach(el=>el.onclick=()=>this._runWol(el.dataset.wolRun)); r.querySelectorAll("[data-wol-del]").forEach(el=>el.onclick=()=>this._deleteWol(el.dataset.wolDel)); r.querySelectorAll("[data-wol-edit]").forEach(el=>el.onclick=()=>{this._wolEdit=(this._status?.wol_profiles||[]).find(p=>p.id===el.dataset.wolEdit)||null;this._render()});
  }
}

if (!customElements.get("nanokvm-remote-server-panel")) customElements.define("nanokvm-remote-server-panel", NanoKVMRemoteServerPanel);
