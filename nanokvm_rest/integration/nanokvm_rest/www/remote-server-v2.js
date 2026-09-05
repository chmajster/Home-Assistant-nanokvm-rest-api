const icons = {
  dashboard: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3h8v8H3V3Zm10 0h8v5h-8V3ZM3 13h8v8H3v-8Zm10-3h8v11h-8V10Z"/></svg>',
  disc: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm0 6a4 4 0 1 1 0 8 4 4 0 0 1 0-8Zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z"/></svg>',
  wrench: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M22 6.92a6 6 0 0 1-7.46 5.82L8.27 19A3 3 0 1 1 5 15.73l6.26-6.27A6 6 0 0 1 17.08 2l-3.02 3.02.92 3.06 3.06.92L22 6.92Z"/></svg>',
  monitor: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 4h18a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2h-7v2h3v2H7v-2h3v-2H3a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Zm0 2v11h18V6H3Z"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M17.65 6.35A8 8 0 1 0 20 12h-2a6 6 0 1 1-1.76-4.24L13 11h8V3l-3.35 3.35Z"/></svg>',
  power: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 2h2v10h-2V2Zm5.66 2.93 1.41-1.41A10 10 0 1 1 5.93 3.52l1.41 1.41A8 8 0 1 0 16.66 4.93Z"/></svg>',
  restart: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4a8 8 0 1 1-7.45 5.09l1.86.72A6 6 0 1 0 8 7.08V10H2V4l2.59 2.59A7.96 7.96 0 0 1 12 4Z"/></svg>',
  keyboard: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 5h18a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Zm0 2v10h18V7H3Zm2 2h2v2H5V9Zm3 0h2v2H8V9Zm3 0h2v2h-2V9Zm3 0h2v2h-2V9Zm3 0h2v2h-2V9ZM5 13h10v2H5v-2Zm11 0h3v2h-3v-2Z"/></svg>',
  external: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3h7v7h-2V6.41l-9.29 9.3-1.42-1.42 9.3-9.29H14V3ZM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2Z"/></svg>',
  copy: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 7V3h13v13h-4v5H3V7h5Zm2 0h7v7h2V5h-9v2Zm5 2H5v10h10V9Z"/></svg>',
  server: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 3h18v7H3V3Zm2 2v3h14V5H5Zm-2 9h18v7H3v-7Zm2 2v3h14v-3H5ZM7 6h2v1H7V6Zm0 11h2v1H7v-1Z"/></svg>',
  upload: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M11 16V7.83L8.41 10.4 7 9l5-5 5 5-1.41 1.41L13 7.83V16h-2ZM5 20a2 2 0 0 1-2-2v-4h2v4h14v-4h2v4a2 2 0 0 1-2 2H5Z"/></svg>',
};

const css = `
  :host {
    --nk-radius: 22px;
    --nk-radius-sm: 15px;
    --nk-gap: 16px;
    display:block;
    min-height:100%;
    color:var(--primary-text-color);
    background:
      radial-gradient(circle at 15% -10%, color-mix(in srgb,var(--primary-color) 12%,transparent), transparent 34rem),
      var(--primary-background-color);
    font-family:var(--paper-font-body1_-_font-family,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif);
  }
  * { box-sizing:border-box; }
  button,input { font:inherit; }
  button { cursor:pointer; }
  button:disabled { opacity:.46; cursor:not-allowed; }
  a { color:inherit; }
  svg { width:20px; height:20px; fill:currentColor; flex:none; }

  .shell { min-height:100vh; display:grid; grid-template-columns:300px minmax(0,1fr); }
  .sidebar {
    position:sticky; top:0; height:100vh; overflow:auto; padding:18px;
    border-right:1px solid color-mix(in srgb,var(--divider-color) 72%,transparent);
    background:color-mix(in srgb,var(--card-background-color) 88%,transparent);
    backdrop-filter:blur(18px);
  }
  .brand { display:flex; align-items:center; gap:12px; margin-bottom:18px; }
  .brand-mark {
    width:46px; height:46px; border-radius:16px; display:grid; place-items:center;
    color:var(--primary-color); background:color-mix(in srgb,var(--primary-color) 13%,var(--card-background-color));
    box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--primary-color) 18%,transparent);
  }
  .brand-mark svg { width:25px; height:25px; }
  .brand h1 { margin:0; font-size:19px; letter-spacing:-.02em; }
  .muted { color:var(--secondary-text-color); }
  .tiny { font-size:12px; }

  .summary { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-bottom:16px; }
  .summary-card { padding:10px 8px; border-radius:14px; text-align:center; background:var(--primary-background-color); border:1px solid var(--divider-color); }
  .summary-card b { display:block; font-size:18px; line-height:1.15; }
  .summary-card span { display:block; margin-top:3px; font-size:10px; color:var(--secondary-text-color); }

  .device-list { display:flex; flex-direction:column; gap:8px; }
  .device-card {
    width:100%; border:1px solid transparent; border-radius:17px; padding:12px;
    display:grid; grid-template-columns:12px minmax(0,1fr) auto; gap:10px; align-items:center;
    color:var(--primary-text-color); background:transparent; text-align:left; transition:.18s ease;
  }
  .device-card:hover { transform:translateY(-1px); background:var(--secondary-background-color); }
  .device-card.active {
    border-color:color-mix(in srgb,var(--primary-color) 35%,var(--divider-color));
    background:color-mix(in srgb,var(--primary-color) 10%,var(--card-background-color));
    box-shadow:0 8px 28px color-mix(in srgb,var(--primary-color) 8%,transparent);
  }
  .status-dot { width:10px; height:10px; border-radius:50%; background:var(--disabled-color,#777); box-shadow:0 0 0 4px color-mix(in srgb,var(--disabled-color,#777) 13%,transparent); }
  .status-dot.online { background:var(--success-color,#2e7d32); box-shadow:0 0 0 4px color-mix(in srgb,var(--success-color,#2e7d32) 13%,transparent); }
  .status-dot.offline { background:var(--error-color,#c62828); box-shadow:0 0 0 4px color-mix(in srgb,var(--error-color,#c62828) 13%,transparent); }
  .device-name { display:block; font-weight:720; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .device-meta { display:block; margin-top:2px; font-size:11px; color:var(--secondary-text-color); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .power-badge { min-width:42px; padding:5px 8px; text-align:center; border-radius:999px; font-size:10px; font-weight:800; background:var(--secondary-background-color); }
  .power-badge.on { color:var(--success-color,#2e7d32); background:color-mix(in srgb,var(--success-color,#2e7d32) 12%,var(--card-background-color)); }

  .sidebar-footer { display:flex; gap:8px; margin-top:16px; }
  .main { min-width:0; padding:24px; }
  .main-inner { max-width:1280px; margin:0 auto; }
  .topbar { display:flex; justify-content:space-between; gap:18px; align-items:center; margin-bottom:16px; }
  .headline { min-width:0; }
  .headline-row { display:flex; gap:10px; align-items:center; }
  .headline h2 { margin:0; font-size:28px; letter-spacing:-.035em; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .headline .address { margin-top:4px; font-size:12px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .availability-pill { display:inline-flex; align-items:center; gap:7px; padding:7px 10px; border-radius:999px; font-size:12px; font-weight:750; background:var(--secondary-background-color); }
  .availability-pill.online { color:var(--success-color,#2e7d32); background:color-mix(in srgb,var(--success-color,#2e7d32) 10%,var(--card-background-color)); }
  .availability-pill.offline { color:var(--error-color,#c62828); background:color-mix(in srgb,var(--error-color,#c62828) 10%,var(--card-background-color)); }
  .top-actions { display:flex; gap:8px; align-items:center; }

  .btn {
    min-height:44px; padding:10px 14px; border:0; border-radius:14px; display:inline-flex; gap:8px; align-items:center; justify-content:center;
    text-decoration:none; font-weight:720; background:var(--primary-color); color:var(--text-primary-color,#fff); transition:.16s ease;
  }
  .btn:hover:not(:disabled) { transform:translateY(-1px); filter:brightness(1.03); }
  .btn.secondary { color:var(--primary-text-color); background:var(--card-background-color); box-shadow:inset 0 0 0 1px var(--divider-color); }
  .btn.danger { background:var(--error-color,#c62828); color:#fff; }
  .btn.warning { background:var(--warning-color,#ef6c00); color:#fff; }
  .btn.ghost { color:var(--primary-text-color); background:transparent; box-shadow:inset 0 0 0 1px var(--divider-color); }
  .btn.icon-only { width:44px; padding:0; }
  .btn.compact { min-height:38px; padding:8px 10px; border-radius:12px; font-size:12px; }

  .desktop-tabs { display:flex; gap:8px; margin-bottom:16px; padding:5px; width:max-content; max-width:100%; overflow:auto; border-radius:16px; background:color-mix(in srgb,var(--card-background-color) 82%,transparent); border:1px solid var(--divider-color); }
  .tab { min-height:40px; border:0; border-radius:12px; padding:8px 13px; color:var(--secondary-text-color); background:transparent; display:flex; align-items:center; gap:8px; white-space:nowrap; font-weight:680; }
  .tab svg { width:18px; height:18px; }
  .tab.active { color:var(--primary-color); background:color-mix(in srgb,var(--primary-color) 11%,var(--card-background-color)); }

  .notice { display:none; margin-bottom:14px; padding:13px 15px; border-radius:15px; border:1px solid var(--divider-color); background:var(--card-background-color); }
  .notice.show { display:block; }
  .notice.error { border-color:color-mix(in srgb,var(--error-color,#c62828) 42%,var(--divider-color)); background:color-mix(in srgb,var(--error-color,#c62828) 8%,var(--card-background-color)); }
  .notice.success { border-color:color-mix(in srgb,var(--success-color,#2e7d32) 42%,var(--divider-color)); background:color-mix(in srgb,var(--success-color,#2e7d32) 8%,var(--card-background-color)); }

  .grid { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:var(--nk-gap); }
  .card { grid-column:span 6; min-width:0; padding:18px; border-radius:var(--nk-radius); background:var(--card-background-color); border:1px solid color-mix(in srgb,var(--divider-color) 78%,transparent); box-shadow:0 12px 36px rgba(0,0,0,.05); }
  .card.full { grid-column:1/-1; }
  .card h3 { margin:0; font-size:17px; letter-spacing:-.015em; }
  .card-head { display:flex; gap:12px; align-items:center; justify-content:space-between; margin-bottom:14px; }
  .section-text { margin:7px 0 14px; color:var(--secondary-text-color); line-height:1.5; }

  .hero { position:relative; overflow:hidden; padding:22px; }
  .hero::after { content:""; position:absolute; width:240px; height:240px; border-radius:50%; right:-90px; top:-130px; background:color-mix(in srgb,var(--primary-color) 10%,transparent); pointer-events:none; }
  .hero-top { display:flex; justify-content:space-between; gap:12px; align-items:flex-start; margin-bottom:18px; position:relative; z-index:1; }
  .hero-device { display:flex; align-items:center; gap:12px; min-width:0; }
  .hero-icon { width:48px; height:48px; border-radius:16px; display:grid; place-items:center; color:var(--primary-color); background:color-mix(in srgb,var(--primary-color) 12%,var(--card-background-color)); }
  .hero-title b { display:block; font-size:18px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .hero-title span { display:block; margin-top:3px; font-size:12px; color:var(--secondary-text-color); }
  .metrics { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; position:relative; z-index:1; }
  .metric { min-width:0; padding:13px; border-radius:15px; background:var(--primary-background-color); border:1px solid var(--divider-color); }
  .metric span { display:block; margin-bottom:5px; font-size:11px; color:var(--secondary-text-color); }
  .metric b { display:block; font-size:14px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .ok { color:var(--success-color,#2e7d32); }
  .bad { color:var(--error-color,#c62828); }

  .action-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }
  .action-btn { min-height:58px; padding:12px; border:1px solid var(--divider-color); border-radius:15px; background:var(--primary-background-color); color:var(--primary-text-color); display:flex; align-items:center; gap:10px; text-align:left; font-weight:720; }
  .action-btn svg { width:22px; height:22px; color:var(--primary-color); }
  .action-btn.danger svg,.action-btn.danger { color:var(--error-color,#c62828); }
  .action-btn.warning svg,.action-btn.warning { color:var(--warning-color,#ef6c00); }

  .media-list { display:flex; flex-direction:column; gap:10px; }
  .media-item { display:grid; grid-template-columns:minmax(0,1fr) auto; gap:12px; align-items:center; padding:13px; border:1px solid var(--divider-color); border-radius:16px; background:var(--primary-background-color); }
  .media-item.mounted { border-color:color-mix(in srgb,var(--primary-color) 38%,var(--divider-color)); background:color-mix(in srgb,var(--primary-color) 6%,var(--card-background-color)); }
  .media-name { min-width:0; }
  .media-name b { display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .media-name span { display:block; margin-top:3px; color:var(--secondary-text-color); font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .media-actions { display:flex; gap:7px; flex-wrap:wrap; justify-content:flex-end; }

  .form-grid { display:grid; grid-template-columns:1fr 1fr auto; gap:10px; align-items:end; }
  label { display:flex; flex-direction:column; gap:6px; min-width:0; color:var(--secondary-text-color); font-size:12px; }
  input[type=text],input[type=file] { width:100%; min-width:0; min-height:44px; padding:10px 12px; border:1px solid var(--divider-color); border-radius:13px; color:var(--primary-text-color); background:var(--primary-background-color); }
  .url { font-family:ui-monospace,SFMono-Regular,Consolas,monospace; overflow-wrap:anywhere; }
  .empty { padding:54px 18px; text-align:center; }
  .native-toolbar { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:14px; }
  iframe { width:100%; min-height:650px; border:1px solid var(--divider-color); border-radius:18px; background:#111; }

  .mobile-device-strip,.mobile-nav { display:none; }
  .busy-line { position:fixed; top:0; left:0; right:0; height:3px; z-index:100; overflow:hidden; pointer-events:none; }
  .busy-line.active::after { content:""; display:block; width:35%; height:100%; background:var(--primary-color); animation:nk-slide 1s linear infinite; }
  @keyframes nk-slide { from{transform:translateX(-110%)} to{transform:translateX(320%)} }

  @media (max-width:1050px) {
    .shell { grid-template-columns:240px minmax(0,1fr); }
    .sidebar { padding:14px 12px; }
    .main { padding:18px; }
    .metrics { grid-template-columns:repeat(2,minmax(0,1fr)); }
    .form-grid { grid-template-columns:1fr; }
  }

  @media (max-width:760px) {
    :host { --nk-gap:12px; }
    .shell { display:block; min-height:100dvh; }
    .sidebar { display:none; }
    .main { padding:0 12px calc(92px + env(safe-area-inset-bottom)); }
    .main-inner { max-width:none; }
    .topbar { position:sticky; top:0; z-index:20; margin:0 -12px 10px; padding:12px 12px 10px; background:color-mix(in srgb,var(--primary-background-color) 88%,transparent); backdrop-filter:blur(18px); border-bottom:1px solid color-mix(in srgb,var(--divider-color) 65%,transparent); }
    .headline h2 { font-size:21px; }
    .headline .address { max-width:70vw; }
    .top-actions .integrations-link { display:none; }
    .top-actions .btn { min-height:42px; }
    .availability-pill { display:none; }

    .mobile-device-strip { display:flex; gap:9px; overflow:auto; margin:0 -12px 12px; padding:2px 12px 8px; scroll-snap-type:x proximity; scrollbar-width:none; }
    .mobile-device-strip::-webkit-scrollbar { display:none; }
    .mobile-device { flex:0 0 min(78vw,280px); scroll-snap-align:start; border:1px solid var(--divider-color); border-radius:18px; padding:12px; color:var(--primary-text-color); background:var(--card-background-color); display:grid; grid-template-columns:10px minmax(0,1fr) auto; gap:10px; align-items:center; text-align:left; box-shadow:0 8px 22px rgba(0,0,0,.04); }
    .mobile-device.active { border-color:color-mix(in srgb,var(--primary-color) 40%,var(--divider-color)); background:color-mix(in srgb,var(--primary-color) 8%,var(--card-background-color)); }

    .desktop-tabs { display:none; }
    .mobile-nav { position:fixed; left:10px; right:10px; bottom:max(10px,env(safe-area-inset-bottom)); z-index:50; display:grid; grid-template-columns:repeat(4,1fr); gap:4px; padding:6px; border:1px solid color-mix(in srgb,var(--divider-color) 75%,transparent); border-radius:20px; background:color-mix(in srgb,var(--card-background-color) 92%,transparent); backdrop-filter:blur(20px); box-shadow:0 14px 38px rgba(0,0,0,.18); }
    .mobile-nav button { min-width:0; min-height:58px; border:0; border-radius:15px; color:var(--secondary-text-color); background:transparent; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:4px; font-size:10px; font-weight:720; }
    .mobile-nav button svg { width:21px; height:21px; }
    .mobile-nav button.active { color:var(--primary-color); background:color-mix(in srgb,var(--primary-color) 11%,var(--card-background-color)); }

    .grid { display:block; }
    .card { margin-bottom:12px; padding:15px; border-radius:19px; box-shadow:none; }
    .hero { padding:16px; }
    .hero-top { margin-bottom:14px; }
    .hero-icon { width:44px; height:44px; border-radius:14px; }
    .metrics { grid-template-columns:1fr 1fr; gap:8px; }
    .metric { padding:11px; border-radius:13px; }
    .metric b { font-size:13px; }
    .action-grid { grid-template-columns:1fr 1fr; gap:8px; }
    .action-btn { min-height:64px; padding:11px; border-radius:14px; flex-direction:column; justify-content:center; text-align:center; gap:6px; font-size:12px; }
    .action-btn svg { width:23px; height:23px; }
    .media-item { grid-template-columns:1fr; padding:12px; }
    .media-actions { display:grid; grid-template-columns:1fr 1fr; justify-content:stretch; }
    .media-actions .btn { width:100%; min-height:44px; }
    .media-actions .danger:last-child:nth-child(3) { grid-column:1/-1; }
    .form-grid .btn { width:100%; min-height:48px; }
    .native-toolbar { display:grid; grid-template-columns:1fr 1fr; }
    .native-toolbar .btn { width:100%; }
    iframe { min-height:62dvh; border-radius:14px; }
    .notice { border-radius:14px; }
  }

  @media (max-width:390px) {
    .metrics,.action-grid { grid-template-columns:1fr; }
    .action-btn { flex-direction:row; justify-content:flex-start; text-align:left; }
    .mobile-nav button { font-size:9px; }
  }
`;

const translations = {
  pl: {
    subtitle:"Panel administracyjny NanoKVM", all:"Wszystkie", online:"Online", hostsOn:"Host ON",
    noDevices:"Brak skonfigurowanych NanoKVM. Dodaj integrację NanoKVM REST w Ustawieniach.", refresh:"Odśwież", integrations:"Integracje",
    overview:"Przegląd", media:"Virtual Media", maintenance:"Serwis", native:"Natywny UI", availability:"Dostępność", hostPower:"Zasilanie hosta", hdmi:"HDMI", hardware:"Hardware", appVersion:"Wersja aplikacji", address:"Adres",
    on:"Włączony", off:"Wyłączony", yes:"Tak", no:"Nie", unknown:"Brak danych", powerControls:"Sterowanie hostem", powerText:"Sterowanie fizycznymi liniami Power/Reset przez wybrany NanoKVM.",
    powerOn:"Włącz host", powerPress:"Power", reset:"Reset hosta", forceOff:"Wymuś OFF", kvmControls:"Sterowanie NanoKVM", hidReset:"Reset HID", rebootKvm:"Restart NanoKVM", openNative:"Otwórz NanoKVM",
    mountedImage:"Zamontowany obraz", cdrom:"CD-ROM", disk:"USB disk", unmount:"Odłącz", changeToCdrom:"Ustaw CD-ROM", changeToDisk:"Ustaw USB disk", availableImages:"Dostępne obrazy ISO / IMG", mountCdrom:"Montuj CD-ROM", mountDisk:"Montuj disk", delete:"Usuń", noImages:"NanoKVM nie zwrócił żadnych obrazów ISO/IMG.",
    adminRequired:"Ta funkcja wymaga konta administratora NanoKVM.", offlineUpdate:"Offline update", updateText:"Wgraj lokalny pakiet nanokvm_X.Y.Z.tar.gz bez internetowego serwera aktualizacji.", package:"Pakiet aktualizacji", checksum:"SHA-256 (opcjonalnie)", upload:"Wyślij i zaktualizuj",
    nativeTitle:"Natywny interfejs NanoKVM", nativeText:"Możesz osadzić oryginalny interfejs wybranego NanoKVM. Przy HTTPS Home Assistant → HTTP NanoKVM użyj nowej karty.", embed:"Pokaż w panelu", hideEmbed:"Ukryj UI", copyAddress:"Kopiuj adres", copied:"Adres skopiowany.", mixedContent:"Przeglądarka zablokuje HTTP wewnątrz Home Assistant działającego po HTTPS. Otwórz NanoKVM w nowej karcie.",
    working:"Wykonywanie operacji…", uploaded:"Pakiet został przekazany do NanoKVM. Urządzenie może się teraz restartować.",
    confirmReset:"Zresetować host przez linię RESET?", confirmForce:"Wymusić wyłączenie hosta długim naciśnięciem POWER?", confirmReboot:"Zrestartować samo urządzenie NanoKVM?", confirmDelete:"Usunąć wybrany obraz z pamięci NanoKVM?", confirmUpdate:"Rozpocząć offline update wybranego NanoKVM?",
  },
  en: {
    subtitle:"NanoKVM administration panel", all:"All", online:"Online", hostsOn:"Hosts ON",
    noDevices:"No NanoKVM devices are configured. Add NanoKVM REST in Settings.", refresh:"Refresh", integrations:"Integrations",
    overview:"Overview", media:"Virtual Media", maintenance:"Maintenance", native:"Native UI", availability:"Availability", hostPower:"Host power", hdmi:"HDMI", hardware:"Hardware", appVersion:"Application version", address:"Address",
    on:"On", off:"Off", yes:"Yes", no:"No", unknown:"Unknown", powerControls:"Host controls", powerText:"Control physical Power/Reset lines through the selected NanoKVM.",
    powerOn:"Power on host", powerPress:"Power", reset:"Reset host", forceOff:"Force OFF", kvmControls:"NanoKVM controls", hidReset:"Reset HID", rebootKvm:"Reboot NanoKVM", openNative:"Open NanoKVM",
    mountedImage:"Mounted image", cdrom:"CD-ROM", disk:"USB disk", unmount:"Unmount", changeToCdrom:"Set CD-ROM", changeToDisk:"Set USB disk", availableImages:"Available ISO / IMG images", mountCdrom:"Mount CD-ROM", mountDisk:"Mount disk", delete:"Delete", noImages:"NanoKVM did not return any ISO/IMG images.",
    adminRequired:"This function requires a NanoKVM administrator account.", offlineUpdate:"Offline update", updateText:"Upload a local nanokvm_X.Y.Z.tar.gz package without using the online update server.", package:"Update package", checksum:"SHA-256 (optional)", upload:"Upload and update",
    nativeTitle:"Native NanoKVM interface", nativeText:"Embed the original UI of the selected NanoKVM. For HTTPS Home Assistant → HTTP NanoKVM use a new browser tab.", embed:"Show in panel", hideEmbed:"Hide UI", copyAddress:"Copy address", copied:"Address copied.", mixedContent:"The browser will block HTTP content inside Home Assistant served over HTTPS. Open NanoKVM in a new tab.",
    working:"Operation in progress…", uploaded:"The package was accepted by NanoKVM. The device may now restart.",
    confirmReset:"Reset the host through the RESET line?", confirmForce:"Force the host off with a long POWER press?", confirmReboot:"Reboot the NanoKVM device itself?", confirmDelete:"Delete the selected image from NanoKVM storage?", confirmUpdate:"Start an offline update on the selected NanoKVM?",
  },
};

class NanoKVMRemoteServerPanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({mode:"open"});
    this._hass=null; this._devices=[]; this._status=null;
    this._selected=localStorage.getItem("nanokvm-remote-selected")||"";
    this._view=localStorage.getItem("nanokvm-remote-view")||"overview";
    this._notice=null; this._busy=false; this._embedNative=false; this._pollTimer=null; this._listTick=0;
  }
  set hass(value){const first=!this._hass;this._hass=value;if(first)this._bootstrap();}
  set panel(_){} set route(_){} set narrow(_){}
  connectedCallback(){if(this._hass&&!this._pollTimer)this._startPolling();}
  disconnectedCallback(){this._stopPolling();}
  get t(){const lang=(this._hass?.language||"en").toLowerCase().startsWith("pl")?"pl":"en";return translations[lang];}
  async _bootstrap(){await this._loadDevices();this._startPolling();}
  _startPolling(){this._stopPolling();this._pollTimer=window.setInterval(async()=>{if(document.hidden||this._busy||!this._selected)return;this._listTick+=1;if(this._listTick>=4){this._listTick=0;await this._loadDevices(true);}else await this._loadStatus(false,true);},15000);}
  _stopPolling(){if(this._pollTimer)window.clearInterval(this._pollTimer);this._pollTimer=null;}
  async _loadDevices(silent=false){if(!this._hass)return;if(!silent){this._busy=true;this._render();}try{const data=await this._hass.callWS({type:"nanokvm_rest/panel/list"});this._devices=data.devices||[];if(!this._devices.some(i=>i.entry_id===this._selected))this._selected=this._devices[0]?.entry_id||"";if(this._selected)localStorage.setItem("nanokvm-remote-selected",this._selected);if(this._selected)await this._loadStatus(false,silent);else this._status=null;}catch(err){this._setNotice(this._errorText(err),true);}finally{this._busy=false;this._render();}}
  async _loadStatus(renderFirst=true,silent=false){if(!this._selected||!this._hass){this._status=null;this._render();return;}if(renderFirst){this._busy=true;this._render();}try{const result=await this._hass.callWS({type:"nanokvm_rest/panel/status",entry_id:this._selected});this._status=result;this._devices=this._devices.map(i=>i.entry_id===this._selected?{...i,...result}:i);if(!silent)this._notice=null;}catch(err){if(!silent)this._setNotice(this._errorText(err),true);if(this._status)this._status={...this._status,available:false};this._devices=this._devices.map(i=>i.entry_id===this._selected?{...i,available:false}:i);}finally{this._busy=false;this._render();}}
  async _select(entryId){if(!entryId||entryId===this._selected||this._busy)return;this._selected=entryId;this._status=null;this._embedNative=false;localStorage.setItem("nanokvm-remote-selected",entryId);await this._loadStatus(true);}
  _setView(view){this._view=view;localStorage.setItem("nanokvm-remote-view",view);this._render();}
  async _action(action,extra={},confirmation=""){if(!this._selected||this._busy)return;if(confirmation&&!window.confirm(confirmation))return;this._busy=true;this._setNotice(this.t.working);this._render();try{await this._hass.callWS({type:"nanokvm_rest/panel/action",entry_id:this._selected,action,...extra});this._notice=null;await this._loadStatus(false);}catch(err){this._setNotice(this._errorText(err),true);}finally{this._busy=false;this._render();}}
  async _offlineUpdate(){const file=this.shadowRoot.querySelector("#update-file")?.files?.[0];const checksum=this.shadowRoot.querySelector("#checksum")?.value?.trim()||"";if(!file||!this._selected||this._busy)return;if(!window.confirm(this.t.confirmUpdate))return;this._busy=true;this._setNotice(`${this.t.working} (${this._formatBytes(file.size)})`);this._render();const form=new FormData();form.append("file",file);const headers={Authorization:`Bearer ${this._hass.auth.accessToken}`};if(checksum)headers["X-SHA256-Checksum"]=checksum;try{const response=await fetch(`/api/nanokvm_rest/offline-update/${encodeURIComponent(this._selected)}`,{method:"POST",headers,body:form});const result=await response.json().catch(()=>({}));if(!response.ok)throw new Error(result.error||`HTTP ${response.status}`);this._setNotice(this.t.uploaded,false,true);}catch(err){this._setNotice(this._errorText(err),true);}finally{this._busy=false;this._render();}}
  async _copyAddress(){const url=this._status?.base_url||this._selectedDevice()?.base_url;if(!url)return;try{await navigator.clipboard.writeText(url);this._setNotice(this.t.copied,false,true);}catch(err){this._setNotice(this._errorText(err),true);}this._render();}
  _selectedDevice(){return this._devices.find(i=>i.entry_id===this._selected)||null;}
  _setNotice(text,error=false,success=false){this._notice={text,error,success};}
  _errorText(err){return err?.message||err?.error?.message||String(err);}
  _escape(value){return String(value??"").replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[c]);}
  _basename(value){const bits=String(value||"").split("/");return bits[bits.length-1]||value;}
  _bool(value,yes=this.t.yes,no=this.t.no){return value===true?yes:value===false?no:this.t.unknown;}
  _formatBytes(bytes){if(!Number.isFinite(bytes)||bytes<1)return"0 B";const units=["B","KiB","MiB","GiB"];const i=Math.min(Math.floor(Math.log(bytes)/Math.log(1024)),units.length-1);return`${(bytes/Math.pow(1024,i)).toFixed(i?1:0)} ${units[i]}`;}
  _canEmbed(baseUrl){try{const url=new URL(baseUrl);return!(window.location.protocol==="https:"&&url.protocol==="http:");}catch(_){return false;}}
  _summary(){return{total:this._devices.length,online:this._devices.filter(d=>d.available===true).length,powered:this._devices.filter(d=>d.power===true).length};}
  _deviceButton(item,mobile=false){const active=item.entry_id===this._selected;const state=item.available===true?"online":item.available===false?"offline":"";const power=item.power===true?"ON":item.power===false?"OFF":"—";return`<button class="${mobile?"mobile-device":"device-card"} ${active?"active":""}" data-device="${this._escape(item.entry_id)}" ${this._busy?"disabled":""}><span class="status-dot ${state}"></span><span><span class="device-name">${this._escape(item.hostname||item.title||"NanoKVM")}</span><span class="device-meta">${this._escape(item.hardware||item.base_url||"")}</span></span><span class="power-badge ${item.power===true?"on":""}">${power}</span></button>`;}
  _renderSidebar(){const t=this.t,s=this._summary(),devices=this._devices.map(i=>this._deviceButton(i)).join("");return`<aside class="sidebar"><div class="brand"><div class="brand-mark">${icons.server}</div><div><h1>Remote Server</h1><div class="muted tiny">${t.subtitle}</div></div></div><div class="summary"><div class="summary-card"><b>${s.total}</b><span>${t.all}</span></div><div class="summary-card"><b>${s.online}</b><span>${t.online}</span></div><div class="summary-card"><b>${s.powered}</b><span>${t.hostsOn}</span></div></div><div class="device-list">${devices||`<div class="muted tiny">${t.noDevices}</div>`}</div><div class="sidebar-footer"><button class="btn secondary compact" id="rail-refresh">${icons.refresh}${t.refresh}</button><a class="btn secondary compact" href="/config/integrations/integration/nanokvm_rest">${t.integrations}</a></div></aside>`;}
  _renderMobileDevices(){return`<div class="mobile-device-strip">${this._devices.map(i=>this._deviceButton(i,true)).join("")}</div>`;}
  _renderOverview(status,selected){const t=this.t;return`<div class="grid"><section class="card full hero"><div class="hero-top"><div class="hero-device"><div class="hero-icon">${icons.server}</div><div class="hero-title"><b>${this._escape(status.hostname||selected?.title||"NanoKVM")}</b><span>${this._escape(status.hardware||t.unknown)}</span></div></div><span class="availability-pill ${status.available?"online":"offline"}"><span class="status-dot ${status.available?"online":"offline"}"></span>${status.available?t.online:t.off}</span></div><div class="metrics"><div class="metric"><span>${t.availability}</span><b class="${status.available?"ok":"bad"}">${status.available?t.online:t.off}</b></div><div class="metric"><span>${t.hostPower}</span><b>${this._bool(status.power,t.on,t.off)}</b></div><div class="metric"><span>${t.hdmi}</span><b>${this._bool(status.hdmi_signal,t.on,t.off)}</b></div><div class="metric"><span>${t.appVersion}</span><b>${this._escape(status.application_version||t.unknown)}</b></div></div></section><section class="card"><div class="card-head"><h3>${t.powerControls}</h3>${icons.power}</div><p class="section-text">${t.powerText}</p><div class="action-grid"><button class="action-btn" data-action="power_on" ${this._busy||status.power===true?"disabled":""}>${icons.power}<span>${t.powerOn}</span></button><button class="action-btn" data-action="power_press" ${this._busy?"disabled":""}>${icons.power}<span>${t.powerPress}</span></button><button class="action-btn warning" data-action="reset" data-confirm="reset" ${this._busy?"disabled":""}>${icons.restart}<span>${t.reset}</span></button><button class="action-btn danger" data-action="force_off" data-confirm="force" ${this._busy||status.power!==true?"disabled":""}>${icons.power}<span>${t.forceOff}</span></button></div></section><section class="card"><div class="card-head"><h3>${t.kvmControls}</h3>${icons.keyboard}</div>${status.admin?`<div class="action-grid"><button class="action-btn" data-action="reset_hid" ${this._busy?"disabled":""}>${icons.keyboard}<span>${t.hidReset}</span></button><button class="action-btn warning" data-action="reboot_nanokvm" data-confirm="reboot" ${this._busy?"disabled":""}>${icons.restart}<span>${t.rebootKvm}</span></button><a class="action-btn" href="${this._escape(status.base_url||selected?.base_url||"#")}" target="_blank" rel="noopener noreferrer">${icons.external}<span>${t.openNative}</span></a></div>`:`<p class="section-text">${t.adminRequired}</p>`}</section></div>`;}
  _renderMedia(status){const t=this.t,media=status.media||{files:[],mounted:"",cdrom:false};if(!status.admin)return`<section class="card full"><h3>${t.media}</h3><p class="section-text">${t.adminRequired}</p></section>`;const mounted=media.mounted?`<section class="card full"><div class="card-head"><h3>${t.mountedImage}</h3><span class="availability-pill online">${media.cdrom?t.cdrom:t.disk}</span></div><div class="media-item mounted"><div class="media-name"><b>${this._escape(this._basename(media.mounted))}</b><span>${this._escape(media.mounted)}</span></div><div class="media-actions"><button class="btn secondary compact" data-action="set_cdrom" data-cdrom="${media.cdrom?"false":"true"}">${media.cdrom?t.changeToDisk:t.changeToCdrom}</button><button class="btn danger compact" data-action="unmount_image">${t.unmount}</button></div></div></section>`:"";const rows=(media.files||[]).map(file=>`<div class="media-item ${file===media.mounted?"mounted":""}"><div class="media-name"><b>${this._escape(this._basename(file))}</b><span>${this._escape(file)}</span></div><div class="media-actions"><button class="btn compact" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="true">${t.mountCdrom}</button><button class="btn secondary compact" data-action="mount_image" data-image="${this._escape(file)}" data-cdrom="false">${t.mountDisk}</button><button class="btn danger compact" data-action="delete_image" data-image="${this._escape(file)}" data-confirm="delete" ${file===media.mounted?"disabled":""}>${t.delete}</button></div></div>`).join("");return`<div class="grid">${mounted}<section class="card full"><div class="card-head"><h3>${t.availableImages}</h3>${icons.disc}</div><div class="media-list">${rows||`<div class="empty muted">${t.noImages}</div>`}</div></section></div>`;}
  _renderMaintenance(status,selected){const t=this.t,baseUrl=status.base_url||selected?.base_url||"";return`<div class="grid"><section class="card"><div class="card-head"><h3>${t.kvmControls}</h3>${icons.wrench}</div>${status.admin?`<div class="action-grid"><button class="action-btn" data-action="reset_hid">${icons.keyboard}<span>${t.hidReset}</span></button><button class="action-btn warning" data-action="reboot_nanokvm" data-confirm="reboot">${icons.restart}<span>${t.rebootKvm}</span></button><button class="action-btn" id="copy-address">${icons.copy}<span>${t.copyAddress}</span></button></div>`:`<p class="section-text">${t.adminRequired}</p>`}</section><section class="card"><div class="card-head"><h3>${t.address}</h3>${icons.external}</div><p class="section-text url">${this._escape(baseUrl||t.unknown)}</p>${baseUrl?`<a class="btn secondary" href="${this._escape(baseUrl)}" target="_blank" rel="noopener noreferrer">${icons.external}${t.openNative}</a>`:""}</section><section class="card full"><div class="card-head"><h3>${t.offlineUpdate}</h3>${icons.upload}</div><p class="section-text">${t.updateText}</p>${status.admin?`<div class="form-grid"><label>${t.package}<input id="update-file" type="file" accept=".tar.gz,application/gzip"></label><label>${t.checksum}<input id="checksum" type="text" maxlength="64" placeholder="0123456789abcdef…"></label><button class="btn" id="offline-update">${icons.upload}${t.upload}</button></div>`:`<p class="section-text">${t.adminRequired}</p>`}</section></div>`;}
  _renderNative(status,selected){const t=this.t,baseUrl=status.base_url||selected?.base_url||"",canEmbed=this._canEmbed(baseUrl);return`<section class="card full"><div class="card-head"><h3>${t.nativeTitle}</h3>${icons.monitor}</div><p class="section-text">${t.nativeText}</p><div class="native-toolbar">${baseUrl?`<a class="btn" href="${this._escape(baseUrl)}" target="_blank" rel="noopener noreferrer">${icons.external}${t.openNative}</a>`:""}<button class="btn secondary" id="toggle-embed" ${!baseUrl||!canEmbed?"disabled":""}>${icons.monitor}${this._embedNative?t.hideEmbed:t.embed}</button><button class="btn secondary" id="copy-address" ${!baseUrl?"disabled":""}>${icons.copy}${t.copyAddress}</button></div>${!canEmbed&&baseUrl?`<div class="notice show error">${t.mixedContent}</div>`:""}${this._embedNative&&canEmbed?`<iframe src="${this._escape(baseUrl)}" referrerpolicy="no-referrer" allow="fullscreen; clipboard-read; clipboard-write"></iframe>`:""}</section>`;}
  _tabs(mobile=false){const t=this.t;const data=[["overview",t.overview,icons.dashboard],["media",t.media,icons.disc],["maintenance",t.maintenance,icons.wrench],["native",t.native,icons.monitor]];return data.map(([id,label,icon])=>`<button class="${mobile?"":"tab "}${this._view===id?"active":""}" data-view="${id}">${icon}<span>${label}</span></button>`).join("");}
  _render(){if(!this.shadowRoot)return;const t=this.t,selected=this._selectedDevice(),status=this._status;const noticeClass=this._notice?`notice show ${this._notice.error?"error":this._notice.success?"success":""}`:"notice";let body=`<section class="card full empty">${t.noDevices}</section>`;if(this._devices.length&&!status)body=`<section class="card full empty">${t.working}</section>`;if(status){if(this._view==="media")body=this._renderMedia(status);else if(this._view==="maintenance")body=this._renderMaintenance(status,selected);else if(this._view==="native")body=this._renderNative(status,selected);else body=this._renderOverview(status,selected);}this.shadowRoot.innerHTML=`<style>${css}</style><div class="busy-line ${this._busy?"active":""}"></div><div class="shell">${this._renderSidebar()}<main class="main"><div class="main-inner"><div class="topbar"><div class="headline"><div class="headline-row"><h2>${this._escape(status?.hostname||selected?.hostname||selected?.title||"Remote Server")}</h2>${status?`<span class="availability-pill ${status.available?"online":"offline"}"><span class="status-dot ${status.available?"online":"offline"}"></span>${status.available?t.online:t.off}</span>`:""}</div><div class="address muted">${this._escape(status?.base_url||selected?.base_url||t.subtitle)}</div></div><div class="top-actions"><button class="btn secondary icon-only" id="refresh" title="${t.refresh}" ${this._busy?"disabled":""}>${icons.refresh}</button><a class="btn secondary integrations-link" href="/config/integrations/integration/nanokvm_rest">${t.integrations}</a></div></div>${this._renderMobileDevices()}<div class="${noticeClass}">${this._escape(this._notice?.text||"")}</div><div class="desktop-tabs">${this._tabs(false)}</div>${body}</div></main></div><nav class="mobile-nav">${this._tabs(true)}</nav>`;this._bindEvents();}
  _bindEvents(){this.shadowRoot.querySelectorAll("[data-device]").forEach(el=>el.addEventListener("click",()=>this._select(el.dataset.device)));this.shadowRoot.querySelectorAll("[data-view]").forEach(el=>el.addEventListener("click",()=>this._setView(el.dataset.view)));this.shadowRoot.querySelectorAll("[data-action]").forEach(el=>el.addEventListener("click",()=>{const action=el.dataset.action,extra={};if(el.dataset.image)extra.image=el.dataset.image;if(el.dataset.cdrom!==undefined)extra.cdrom=el.dataset.cdrom==="true";const key=el.dataset.confirm;const confirmation=key==="reset"?this.t.confirmReset:key==="force"?this.t.confirmForce:key==="reboot"?this.t.confirmReboot:key==="delete"?this.t.confirmDelete:"";this._action(action,extra,confirmation);}));this.shadowRoot.querySelector("#refresh")?.addEventListener("click",()=>this._loadDevices());this.shadowRoot.querySelector("#rail-refresh")?.addEventListener("click",()=>this._loadDevices());this.shadowRoot.querySelector("#offline-update")?.addEventListener("click",()=>this._offlineUpdate());this.shadowRoot.querySelectorAll("#copy-address").forEach(el=>el.addEventListener("click",()=>this._copyAddress()));this.shadowRoot.querySelector("#toggle-embed")?.addEventListener("click",()=>{this._embedNative=!this._embedNative;this._render();});}
}

if(!customElements.get("nanokvm-remote-server-panel"))customElements.define("nanokvm-remote-server-panel",NanoKVMRemoteServerPanel);
