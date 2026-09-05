import "./remote-server-v4.js?v=4";
import { RemoteConsoleController } from "./remote-console-controller.js?v=1";

const BasePanel = customElements.get("nanokvm-remote-server-panel");

class NanoKVMRemoteServerPanelV5 extends BasePanel {
  constructor(){super();this._consoleController=null;}
  get t(){
    const base=super.t;
    return {...base,...(this.lang==="pl"?{
      console:"Konsola",liveConsole:"Remote Console / Live KVM",consoleDesc:"Obraz i sterowanie hostem bezpośrednio w Home Assistant.",fullscreen:"Pełny ekran",landscape:"Landscape",scale:"Skala",keyboard:"Klawiatura",mouse:"Mysz",reconnectConsole:"Połącz ponownie",consolePaste:"Wyślij tekst",rotateHint:"Obróć telefon poziomo",consoleFocus:"Kliknij obraz, aby przejąć klawiaturę",streaming:"Streaming"
    }:{
      console:"Console",liveConsole:"Remote Console / Live KVM",consoleDesc:"Live host video and controls directly inside Home Assistant.",fullscreen:"Fullscreen",landscape:"Landscape",scale:"Scale",keyboard:"Keyboard",mouse:"Mouse",reconnectConsole:"Reconnect",consolePaste:"Send text",rotateHint:"Rotate the phone to landscape",consoleFocus:"Click the image to capture keyboard input",streaming:"Streaming"
    })};
  }
  disconnectedCallback(){this._stopConsole();super.disconnectedCallback();}
  async _poll(){if(this._view==="console")return;return super._poll();}
  async _switchView(view){if(this._view==="console"&&view!=="console")this._stopConsole();await super._switchView(view);}
  async _select(id){const consoleOpen=this._view==="console";if(consoleOpen)this._stopConsole();await super._select(id);}
  _renderNative(){if(this._view==="console")return this._renderConsole();return super._renderNative();}
  _renderSidebar(){
    const html=super._renderSidebar();
    const button=`<button data-view="console" class="${this._view==="console"?"active":""}" ${!this._selected?"disabled":""}><span>▣</span>${this.t.console}</button>`;
    return html.replace('<button data-view="native"',`${button}<button data-view="native"`);
  }
  _renderBottom(){
    const html=super._renderBottom();
    const button=`<button data-view="console" class="${this._view==="console"?"active":""}" ${!this._selected?"disabled":""}><b>▣</b><span>${this.t.console}</span></button>`;
    return html.replace('<button data-view="maintenance"',`${button}<button data-view="maintenance"`);
  }
  _styles(){return super._styles().replace("</style>",`${this._consoleStyles()}</style>`);}
  _consoleStyles(){return `
.console-view{max-width:1800px}.console-head{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;margin-bottom:12px}.console-head h2{margin:4px 0}.console-head p{margin:0;color:var(--secondary-text-color)}.console-toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:10px 0 12px}.console-toolbar label{display:flex;align-items:center;gap:6px;padding:8px 10px;border:1px solid var(--divider-color);border-radius:12px;background:var(--card-background-color)}.console-toolbar select{padding:7px 9px}.console-state{padding:7px 10px;border-radius:999px;background:var(--secondary-background-color);font-size:12px;text-transform:capitalize}.console-state[data-state="streaming"]{color:#2eaf5d}.console-state[data-state="error"]{color:var(--error-color)}.console-shell{background:#080b10;border-radius:20px;border:1px solid var(--divider-color);overflow:hidden;min-height:480px;display:grid;grid-template-rows:minmax(0,1fr) auto}.console-stage{position:relative;overflow:auto;min-height:420px;display:grid;place-items:center;outline:none;background:radial-gradient(circle at 50% 30%,#1a2230,#050608 65%)}.console-stage:focus{box-shadow:inset 0 0 0 2px var(--primary-color)}.console-video-wrap{min-width:100%;min-height:100%;display:grid;place-items:center;overflow:auto;padding:8px}.console-video-wrap canvas{display:block;background:#000;touch-action:none;user-select:none;-webkit-user-select:none}.console-hint{position:absolute;left:12px;bottom:12px;background:rgba(0,0,0,.62);color:#fff;padding:7px 10px;border-radius:10px;font-size:12px;pointer-events:none}.console-controls{padding:12px;background:#10151d;color:#fff;display:grid;gap:10px}.console-keys{display:flex;flex-wrap:wrap;gap:7px}.console-keys button{background:#242d39;color:#fff;min-width:54px}.console-keys .danger-key{background:#7d2d2d}.console-paste{display:flex;gap:8px}.console-paste input{flex:1;background:#171d25;color:#fff;border-color:#343d49}.console-shell:fullscreen{border-radius:0;width:100vw;height:100vh;grid-template-rows:minmax(0,1fr) auto}.console-shell:fullscreen .console-stage{min-height:0}.console-shell:fullscreen canvas{max-height:calc(100vh - 82px)!important}@media(max-width:900px){.console-head{align-items:flex-start}.console-shell{min-height:calc(100dvh - 185px);border-radius:14px}.console-stage{min-height:calc(100dvh - 295px)}.console-toolbar{position:sticky;top:0;z-index:4;background:var(--primary-background-color);padding:6px 0}.console-toolbar button,.console-toolbar label{min-height:44px}.console-controls{padding-bottom:calc(12px + env(safe-area-inset-bottom))}.console-paste{flex-direction:column}.console-paste button{width:100%}}@media(max-width:900px) and (orientation:landscape){main{padding:5px 6px 74px}.console-head{display:none}.console-toolbar{margin:0 0 5px;padding:3px 0}.console-shell{min-height:calc(100dvh - 82px);height:calc(100dvh - 82px)}.console-stage{min-height:0}.console-controls{position:absolute;left:8px;right:8px;bottom:8px;border-radius:14px;background:rgba(10,14,20,.88);backdrop-filter:blur(8px);padding:7px}.console-paste{display:none}.console-hint{display:none}.bottom{opacity:.88}}`}
  _renderConsole(){
    const d=this._status||this._device(); if(!d)return `<div class="empty">${this.t.noData}</div>`;
    return `<section class="view console-view"><div class="console-head"><div><span class="eyebrow">Live KVM</span><h2>${this.t.liveConsole}</h2><p>${this.t.consoleDesc} · ${esc(d.hostname||d.title)}</p></div><span id="console-state" class="console-state" data-state="idle">idle</span></div><div class="console-toolbar"><label><input id="console-keyboard" type="checkbox" checked> ${this.t.keyboard}</label><label><input id="console-mouse" type="checkbox" checked> ${this.t.mouse}</label><label>${this.t.scale}<select id="console-scale"><option value="fit">Fit</option><option value="1">100%</option><option value="1.25">125%</option><option value="1.5">150%</option><option value="2">200%</option></select></label><button id="console-fullscreen">⛶ ${this.t.fullscreen}</button><button id="console-landscape">↻ ${this.t.landscape}</button><button id="console-reconnect">↺ ${this.t.reconnectConsole}</button><span id="console-leds" class="console-state">NUM ○ CAPS ○ SCR ○</span></div><div id="console-shell" class="console-shell"><div id="console-stage" class="console-stage"><div class="console-video-wrap"><canvas id="console-canvas" width="1280" height="720"></canvas></div><div class="console-hint">${this.t.consoleFocus}</div></div><div class="console-controls"><div class="console-keys"><button data-console-key="Escape">Esc</button><button data-console-key="F2">F2</button><button data-console-key="F8">F8</button><button data-console-key="F12">F12</button><button data-console-key="Enter">Enter</button><button data-console-key="Delete">Del</button><button id="console-cad" class="danger-key">Ctrl+Alt+Del</button></div><div class="console-paste"><input id="console-paste" placeholder="${this.t.paste}"><button id="console-paste-send">${this.t.consolePaste}</button></div></div></div></section>`;
  }
  _stopConsole(){if(this._consoleController){this._consoleController.stop();this._consoleController=null;}}
  async _startConsole(){
    if(this._view!=="console"||!this._selected)return;
    this._stopConsole();
    this._consoleController=new RemoteConsoleController({
      hass:this._hass,entryId:this._selected,root:this.shadowRoot,labels:{rotateHint:this.t.rotateHint},
      requestSession:()=>this._api("nanokvm_rest/panel/console/session",{entry_id:this._selected}),
      pasteText:(text)=>this._api("nanokvm_rest/panel/hid/action",{entry_id:this._selected,action:"paste",text,language:this.lang})
    });
    await this._consoleController.start();
  }
  _bind(){super._bind();if(this._view==="console")queueMicrotask(()=>this._startConsole());}
}

if(!customElements.get("nanokvm-remote-server-panel-v5"))customElements.define("nanokvm-remote-server-panel-v5",NanoKVMRemoteServerPanelV5);
