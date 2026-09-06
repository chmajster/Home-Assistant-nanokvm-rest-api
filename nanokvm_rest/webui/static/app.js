(() => {
  const state = { view: 'overview', devices: [], operations: {}, updates: {}, selected: '' };
  const content = document.getElementById('content');
  const notice = document.getElementById('notice');
  const title = document.getElementById('page-title');
  const subtitle = document.getElementById('page-subtitle');

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const yes = (v) => v === true ? 'Tak' : v === false ? 'Nie' : '—';
  const n = (v, suffix='') => (v === null || v === undefined || v === '') ? '—' : `${v}${suffix}`;
  const healthBadge = (h={}) => `<span class="badge ${h.state === 'healthy' ? 'good' : h.state === 'warning' ? 'warn' : 'bad'}">Health ${esc(h.score ?? '—')}</span>`;
  const statusBadge = (online) => `<span class="badge ${online ? 'good' : 'bad'}">${online ? 'Online' : 'Offline'}</span>`;

  function showNotice(message, bad=false) {
    notice.textContent = message;
    notice.classList.toggle('bad', bad);
    notice.classList.remove('hidden');
    clearTimeout(showNotice.t);
    showNotice.t = setTimeout(() => notice.classList.add('hidden'), 6000);
  }

  async function jsonFetch(url, options={}) {
    const headers = {'Accept':'application/json', ...(options.headers||{})};
    if (options.method && options.method !== 'GET') {
      headers['Content-Type'] = 'application/json';
      headers['X-NanoKVM-Request'] = '1';
    }
    const r = await fetch(url, {...options, headers});
    const data = await r.json().catch(() => ({ok:false,error:`HTTP ${r.status}`}));
    if (!r.ok || data.ok === false) throw new Error(data.error || `HTTP ${r.status}`);
    return data;
  }

  async function rpc(type, payload={}) {
    const data = await jsonFetch('api/rpc', {method:'POST', body:JSON.stringify({type, ...payload})});
    return data.result;
  }

  async function load(show=true) {
    if (show) content.innerHTML = '<div class="loading">Ładowanie danych z Home Assistant…</div>';
    try {
      const data = await jsonFetch('api/bootstrap');
      state.devices = data.devices?.devices || [];
      state.operations = data.operations || {};
      state.updates = data.updates || {};
      if (!state.selected && state.devices[0]) state.selected = state.devices[0].entry_id;
      render();
    } catch (e) {
      content.innerHTML = `<div class="card"><h2>Nie udało się połączyć z integracją</h2><p>${esc(e.message)}</p><p>Sprawdź, czy NanoKVM REST jest zainstalowane, skonfigurowane i Home Assistant został zrestartowany po aktualizacji.</p></div>`;
      showNotice(e.message, true);
    }
  }

  function summary() {
    const devices = state.devices;
    const ops = state.operations.summary || {};
    const updateDevices = state.updates.devices || [];
    return {
      total: devices.length,
      online: devices.filter(d => d.available).length,
      powered: devices.filter(d => d.power === true).length,
      alerts: (ops.critical || 0) + (ops.warning || 0),
      updates: updateDevices.filter(d => d.update_available).length,
      maintenance: ops.maintenance || 0,
    };
  }

  function deviceCard(d) {
    return `<article class="card device-card">
      <div class="device-head"><div><h3>${esc(d.hostname || d.title)}</h3><div class="muted">${esc(d.base_url || '')}</div></div>${statusBadge(d.available)}</div>
      <div class="actions">${healthBadge(d.health)}${d.favorite ? '<span class="badge warn">★ Favorite</span>' : ''}${d.group ? `<span class="badge">${esc(d.group)}</span>` : ''}</div>
      <div class="facts">
        <div class="fact"><span>Host</span><strong>${d.power === true ? 'ON' : d.power === false ? 'OFF' : '—'}</strong></div>
        <div class="fact"><span>HDMI</span><strong>${yes(d.hdmi_signal)}</strong></div>
        <div class="fact"><span>Hardware</span><strong>${esc(d.hardware || '—')}</strong></div>
        <div class="fact"><span>App</span><strong>${esc(d.application_version || '—')}</strong></div>
      </div>
      <div class="actions">
        <button class="btn small" data-action="power_on" data-entry="${esc(d.entry_id)}">Power On</button>
        <button class="btn small" data-action="power_press" data-entry="${esc(d.entry_id)}">Power</button>
        <button class="btn small danger" data-action="reset" data-entry="${esc(d.entry_id)}">Reset</button>
        ${d.admin ? `<button class="btn small" data-action="reset_hid" data-entry="${esc(d.entry_id)}">HID Reset</button>` : ''}
      </div>
    </article>`;
  }

  function renderOverview() {
    const s = summary();
    return `<div class="grid">
      <div class="card metric"><span class="muted">NanoKVM</span><strong>${s.total}</strong></div>
      <div class="card metric"><span class="muted">Online</span><strong>${s.online}/${s.total}</strong></div>
      <div class="card metric"><span class="muted">Aktywne hosty</span><strong>${s.powered}</strong></div>
      <div class="card metric"><span class="muted">Alerty</span><strong>${s.alerts}</strong></div>
    </div>
    <div class="section-title"><h2>Flota NanoKVM</h2><span class="muted">Update dostępny: ${s.updates} · Maintenance: ${s.maintenance}</span></div>
    <div class="device-grid">${state.devices.map(deviceCard).join('') || '<div class="card">Brak skonfigurowanych urządzeń.</div>'}</div>`;
  }

  function renderDevices() {
    return `<div class="device-grid">${state.devices.map(deviceCard).join('')}</div>`;
  }

  function renderOperations() {
    const devices = state.operations.devices || [];
    return `<div class="device-grid">${devices.map(d => `<article class="card device-card">
      <div class="device-head"><div><h3>${esc(d.title)}</h3><span class="muted">${n(d.latency_ms,' ms')}</span></div>${healthBadge(d.health)}</div>
      <div class="facts">
        <div class="fact"><span>Availability 24h</span><strong>${n(d.availability_24h,'%')}</strong></div>
        <div class="fact"><span>Availability 7d</span><strong>${n(d.availability_7d,'%')}</strong></div>
        <div class="fact"><span>Latency avg</span><strong>${n(d.latency_avg_24h,' ms')}</strong></div>
        <div class="fact"><span>Maintenance</span><strong>${(d.maintenance||{}).enabled ? 'ON' : 'OFF'}</strong></div>
      </div>
      <div class="actions">
        <button class="btn small" data-recovery="diagnose" data-entry="${esc(d.entry_id)}">Diagnostics</button>
        <button class="btn small" data-recovery="safe_recovery" data-entry="${esc(d.entry_id)}">Safe Recovery</button>
        <button class="btn small" data-maintenance="${(d.maintenance||{}).enabled ? 'off' : 'on'}" data-entry="${esc(d.entry_id)}">${(d.maintenance||{}).enabled ? 'Wyłącz maintenance' : 'Maintenance 2h'}</button>
      </div>
    </article>`).join('') || '<div class="card">Brak danych Operations.</div>'}</div>`;
  }

  function renderAlerts() {
    const alerts = state.operations.alerts || [];
    return `<div class="alert-list">${alerts.map(a => `<div class="card alert-row">
      <span class="badge ${a.severity === 'critical' ? 'bad' : a.severity === 'warning' ? 'warn' : ''}">${esc(a.severity)}</span>
      <div><strong>${esc(a.title)}</strong><div class="muted">${esc(a.message)}</div></div>
      ${a.acknowledged ? '<span class="badge">Potwierdzony</span>' : `<button class="btn small" data-ack="${esc(a.id)}" data-entry="${esc(a.entry_id)}">Potwierdź</button>`}
    </div>`).join('') || '<div class="card">Brak aktywnych alertów.</div>'}</div>`;
  }

  function renderUpdates() {
    const devices = state.updates.devices || [];
    return `<div class="table-wrap"><table><thead><tr><th>Urządzenie</th><th>Current</th><th>Latest</th><th>Channel</th><th>Status</th><th>Akcje</th></tr></thead><tbody>
      ${devices.map(d => `<tr><td>${esc(d.title)}</td><td>${esc(d.current||'—')}</td><td>${esc(d.latest||'—')}</td><td><select data-channel-entry="${esc(d.entry_id)}"><option value="stable" ${d.channel==='stable'?'selected':''}>Stable</option><option value="preview" ${d.channel==='preview'?'selected':''}>Preview</option></select></td><td>${d.error ? `<span class="badge bad">${esc(d.error)}</span>` : d.update_available ? '<span class="badge warn">Update available</span>' : `<span class="badge">${esc(d.runtime?.state || 'idle')}</span>`}</td><td><button class="btn small primary" data-update="${esc(d.entry_id)}" ${!d.admin?'disabled':''}>Update</button></td></tr>`).join('')}
    </tbody></table></div>`;
  }

  function deviceSelect() {
    return `<select id="device-select">${state.devices.map(d => `<option value="${esc(d.entry_id)}" ${d.entry_id===state.selected?'selected':''}>${esc(d.hostname||d.title)}</option>`).join('')}</select>`;
  }

  async function renderMedia() {
    content.innerHTML = `<div class="toolbar"><div class="field"><label>NanoKVM</label>${deviceSelect()}</div><button class="btn" id="media-load">Odśwież bibliotekę</button></div><div id="media-body" class="section-title"><span class="muted">Ładowanie…</span></div>`;
    bindDeviceSelect();
    document.getElementById('media-load')?.addEventListener('click', renderMedia);
    try {
      const media = await rpc('nanokvm_rest/panel/media/library', {entry_id:state.selected});
      const items = media.items || [];
      document.getElementById('media-body').outerHTML = `<div id="media-body"><div class="section-title"><h2>Virtual Media</h2><span class="muted">Mounted: ${esc(media.mounted||'—')}</span></div>
        <div class="card"><div class="toolbar"><div class="field"><label>ISO URL</label><input id="iso-url" placeholder="https://…/image.iso"></div><div class="field"><label>SHA-256 (opcjonalnie)</label><input id="iso-sha"></div><button class="btn" id="iso-download">Pobierz na NanoKVM</button></div></div>
        <div class="table-wrap" style="margin-top:14px"><table><thead><tr><th>Obraz</th><th>Typ</th><th>Źródło</th><th>Mounted</th><th>Akcje</th></tr></thead><tbody>${items.map(i => `<tr><td>${esc(i.name||i.path)}</td><td>${esc(i.type||'—')}</td><td>${esc(i.source||'device')}</td><td>${i.mounted?'Tak':'Nie'}</td><td class="actions"><button class="btn small" data-mount="cd" data-path="${esc(i.path)}">CD-ROM</button><button class="btn small" data-mount="usb" data-path="${esc(i.path)}">USB</button></td></tr>`).join('')}</tbody></table></div>
        <div class="actions" style="margin-top:12px"><button class="btn" id="unmount">Unmount</button></div></div>`;
      bindMediaActions();
    } catch(e) { showNotice(e.message,true); }
  }

  async function renderHid() {
    content.innerHTML = `<div class="toolbar"><div class="field"><label>NanoKVM</label>${deviceSelect()}</div><button class="btn" id="hid-load">Odśwież</button></div><div id="hid-body" class="loading">Ładowanie…</div>`;
    bindDeviceSelect();
    document.getElementById('hid-load')?.addEventListener('click', renderHid);
    try {
      const hid = await rpc('nanokvm_rest/panel/hid/status', {entry_id:state.selected});
      document.getElementById('hid-body').outerHTML = `<div id="hid-body" class="grid two" style="margin-top:14px"><div class="card"><h2>HID</h2><div class="facts"><div class="fact"><span>Mode</span><strong>${esc(hid.mode||'—')}</strong></div><div class="fact"><span>CapsLock</span><strong>${yes(hid.leds?.caps_lock)}</strong></div><div class="fact"><span>NumLock</span><strong>${yes(hid.leds?.num_lock)}</strong></div><div class="fact"><span>ScrollLock</span><strong>${yes(hid.leds?.scroll_lock)}</strong></div></div><div class="actions" style="margin-top:12px"><button class="btn" data-hid="reset">Reset HID</button><button class="btn" data-hid="reconnect">Reconnect</button></div></div><div class="card"><h2>Paste text</h2><div class="field"><label>Tekst</label><textarea id="paste-text" rows="6"></textarea></div><div class="actions" style="margin-top:12px"><button class="btn primary" data-hid="paste">Wyślij</button></div></div></div>`;
      bindHidActions();
    } catch(e) { showNotice(e.message,true); }
  }

  const viewMeta = {
    overview:['Dashboard','Centrum zdalnego zarządzania NanoKVM'], devices:['Urządzenia','Sterowanie hostami i stan urządzeń'], operations:['Operations','Monitoring, health i recovery'], alerts:['Alert Center','Problemy wymagające uwagi'], updates:['Update Center','Aktualizacje aplikacji NanoKVM'], media:['Virtual Media','Biblioteka ISO/IMG i montowanie'], hid:['HID Toolbox','Klawiatura, mysz i reset HID']
  };

  function render() {
    const meta = viewMeta[state.view] || viewMeta.overview;
    title.textContent = meta[0]; subtitle.textContent = meta[1];
    document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === state.view));
    if (state.view === 'overview') content.innerHTML = renderOverview();
    else if (state.view === 'devices') content.innerHTML = renderDevices();
    else if (state.view === 'operations') content.innerHTML = renderOperations();
    else if (state.view === 'alerts') content.innerHTML = renderAlerts();
    else if (state.view === 'updates') content.innerHTML = renderUpdates();
    else if (state.view === 'media') { renderMedia(); return; }
    else if (state.view === 'hid') { renderHid(); return; }
    bindActions();
  }

  function bindDeviceSelect() {
    const select = document.getElementById('device-select');
    if (select) select.addEventListener('change', () => {state.selected=select.value; render();});
  }

  function bindActions() {
    document.querySelectorAll('[data-action]').forEach(btn => btn.addEventListener('click', async () => {
      const destructive = ['reset','force_off','reboot_nanokvm'].includes(btn.dataset.action);
      if (destructive && !confirm(`Wykonać ${btn.dataset.action}?`)) return;
      try { await rpc('nanokvm_rest/panel/action',{entry_id:btn.dataset.entry,action:btn.dataset.action}); showNotice('Akcja wykonana.'); await load(false); } catch(e){showNotice(e.message,true);}
    }));
    document.querySelectorAll('[data-recovery]').forEach(btn => btn.addEventListener('click', async () => {
      try { await rpc('nanokvm_rest/panel/ops/recovery/action',{entry_id:btn.dataset.entry,action:btn.dataset.recovery}); showNotice('Recovery zakończony.'); await load(false);} catch(e){showNotice(e.message,true);}
    }));
    document.querySelectorAll('[data-maintenance]').forEach(btn => btn.addEventListener('click', async () => {
      const enabled = btn.dataset.maintenance === 'on';
      try { await rpc('nanokvm_rest/panel/ops/maintenance/set',{entry_id:btn.dataset.entry,enabled,minutes:enabled?120:0,note:'NanoKVM Manager'}); showNotice('Maintenance zaktualizowany.'); await load(false);} catch(e){showNotice(e.message,true);}
    }));
    document.querySelectorAll('[data-ack]').forEach(btn => btn.addEventListener('click', async () => {
      try { await rpc('nanokvm_rest/panel/ops/alert/ack',{entry_id:btn.dataset.entry,alert_id:btn.dataset.ack}); await load(false);} catch(e){showNotice(e.message,true);}
    }));
    document.querySelectorAll('[data-update]').forEach(btn => btn.addEventListener('click', async () => {
      if (!confirm('Uruchomić aktualizację NanoKVM? Urządzenie może chwilowo stracić połączenie.')) return;
      try { await rpc('nanokvm_rest/panel/update/start',{entry_id:btn.dataset.update}); showNotice('Aktualizacja została zakolejkowana.'); setTimeout(()=>load(false),1200);} catch(e){showNotice(e.message,true);}
    }));
    document.querySelectorAll('[data-channel-entry]').forEach(sel => sel.addEventListener('change', async () => {
      try { await rpc('nanokvm_rest/panel/update/channel',{entry_id:sel.dataset.channelEntry,channel:sel.value}); showNotice('Kanał aktualizacji zmieniony.'); await load(false);} catch(e){showNotice(e.message,true);}
    }));
  }

  function bindMediaActions() {
    document.getElementById('iso-download')?.addEventListener('click', async () => {
      const url=document.getElementById('iso-url').value.trim(), sha256=document.getElementById('iso-sha').value.trim();
      if(!url){showNotice('Podaj URL ISO.',true);return;}
      try{await rpc('nanokvm_rest/panel/media/download/start',{entry_id:state.selected,url,sha256});showNotice('Pobieranie ISO uruchomione.');setTimeout(renderMedia,1000);}catch(e){showNotice(e.message,true);}
    });
    document.querySelectorAll('[data-mount]').forEach(btn=>btn.addEventListener('click',async()=>{try{await rpc('nanokvm_rest/panel/media/mount',{entry_id:state.selected,path:btn.dataset.path,cdrom:btn.dataset.mount==='cd'});showNotice('Obraz zamontowany.');await renderMedia();}catch(e){showNotice(e.message,true);}}));
    document.getElementById('unmount')?.addEventListener('click',async()=>{try{await rpc('nanokvm_rest/panel/action',{entry_id:state.selected,action:'unmount_image'});showNotice('Obraz odmontowany.');await renderMedia();}catch(e){showNotice(e.message,true);}});
  }

  function bindHidActions() {
    document.querySelectorAll('[data-hid]').forEach(btn=>btn.addEventListener('click',async()=>{const action=btn.dataset.hid;const payload={entry_id:state.selected,action};if(action==='paste'){payload.text=document.getElementById('paste-text').value;payload.language='pl';if(!payload.text){showNotice('Wpisz tekst.',true);return;}}try{await rpc('nanokvm_rest/panel/hid/action',payload);showNotice('Akcja HID wykonana.');if(action!=='paste')await renderHid();}catch(e){showNotice(e.message,true);}}));
  }

  document.querySelectorAll('[data-view]').forEach(btn => btn.addEventListener('click', () => { state.view=btn.dataset.view; render(); }));
  document.getElementById('refresh').addEventListener('click', () => load(true));
  document.getElementById('open-live').addEventListener('click', () => { if (window.top) window.top.location.href='/nanokvm-remote-server'; });
  load(true);
  setInterval(() => { if (!['media','hid'].includes(state.view)) load(false); }, 30000);
})();
