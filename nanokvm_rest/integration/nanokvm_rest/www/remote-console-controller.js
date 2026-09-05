const MODIFIERS = {
  ControlLeft: 1, ShiftLeft: 2, AltLeft: 4, MetaLeft: 8,
  ControlRight: 16, ShiftRight: 32, AltRight: 64, MetaRight: 128
};
const SPECIAL = {
  Enter:0x28, Escape:0x29, Backspace:0x2a, Tab:0x2b, Space:0x2c, Minus:0x2d, Equal:0x2e,
  BracketLeft:0x2f, BracketRight:0x30, Backslash:0x31, Semicolon:0x33, Quote:0x34, Backquote:0x35,
  Comma:0x36, Period:0x37, Slash:0x38, CapsLock:0x39, PrintScreen:0x46, ScrollLock:0x47, Pause:0x48,
  Insert:0x49, Home:0x4a, PageUp:0x4b, Delete:0x4c, End:0x4d, PageDown:0x4e, ArrowRight:0x4f,
  ArrowLeft:0x50, ArrowDown:0x51, ArrowUp:0x52, NumLock:0x53, NumpadDivide:0x54, NumpadMultiply:0x55,
  NumpadSubtract:0x56, NumpadAdd:0x57, NumpadEnter:0x58, NumpadDecimal:0x63, IntlBackslash:0x64,
  ContextMenu:0x65
};
for (let i=1;i<=12;i++) SPECIAL[`F${i}`]=0x39+i;
for (let i=0;i<=9;i++) SPECIAL[`Numpad${i}`]=i===0?0x62:0x58+i;

function keycode(code) {
  if (/^Key[A-Z]$/.test(code)) return 0x04 + code.charCodeAt(3) - 65;
  if (/^Digit[1-9]$/.test(code)) return 0x1e + Number(code.slice(5)) - 1;
  if (code === "Digit0") return 0x27;
  return SPECIAL[code];
}

export class RemoteConsoleController {
  constructor({ hass, entryId, root, requestSession, pasteText, labels = {} }) {
    this.hass = hass;
    this.entryId = entryId;
    this.root = root;
    this.requestSession = requestSession;
    this.pasteText = pasteText;
    this.labels = labels;
    this.worker = null;
    this.canvas = null;
    this.stage = null;
    this.frame = { width: 1280, height: 720 };
    this.keyboardEnabled = true;
    this.mouseEnabled = true;
    this.pressed = new Map();
    this.modifier = 0;
    this.mouseButtons = 0;
    this.lastMouse = { x: 0x4000, y: 0x4000 };
    this.touch = null;
    this.longPressTimer = null;
    this.reconnectTimer = null;
    this.scale = localStorage.getItem("nanokvm-console-scale") || "fit";
    this._listeners = [];
  }

  async start() {
    this.stop(false);
    this.canvas = this.root.querySelector("#console-canvas");
    this.stage = this.root.querySelector("#console-stage");
    if (!this.canvas || !this.stage) return;
    this._bindUi();
    this._applyScale();
    try {
      const session = await this.requestSession();
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      const url = `${scheme}://${location.host}${session.path}`;
      const worker = new Worker(new URL("./remote-console-worker.js?v=1", import.meta.url), { type: "module" });
      this.worker = worker;
      worker.onmessage = (event) => this._workerMessage(event.data || {});
      const offscreen = this.canvas.transferControlToOffscreen();
      worker.postMessage({ type:"start", canvas:offscreen, url, protocol:session.protocol, token:session.token }, [offscreen]);
    } catch (err) {
      this._setState("error", err?.message || String(err));
    }
  }

  stop(clearReconnect = true) {
    if (clearReconnect && this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = null;
    this._releaseKeyboard();
    if (this.worker) {
      try { this.worker.postMessage({type:"stop"}); } catch (_) {}
      this.worker.terminate();
    }
    this.worker = null;
    this._listeners.forEach(([target,type,fn,opts]) => target.removeEventListener(type,fn,opts));
    this._listeners = [];
    if (this.longPressTimer) clearTimeout(this.longPressTimer);
    this.longPressTimer = null;
  }

  async restart() {
    this.stop(false);
    await this.start();
  }

  _listen(target, type, fn, opts) {
    target.addEventListener(type, fn, opts);
    this._listeners.push([target,type,fn,opts]);
  }

  _bindUi() {
    const stage = this.stage;
    const canvas = this.canvas;
    stage.tabIndex = 0;
    this._listen(stage,"keydown",e=>this._keyDown(e));
    this._listen(stage,"keyup",e=>this._keyUp(e));
    this._listen(stage,"blur",()=>this._releaseKeyboard());
    this._listen(canvas,"mousedown",e=>this._mouseDown(e));
    this._listen(window,"mouseup",e=>this._mouseUp(e));
    this._listen(canvas,"mousemove",e=>this._mouseMove(e));
    this._listen(canvas,"wheel",e=>this._wheel(e),{passive:false});
    this._listen(canvas,"contextmenu",e=>e.preventDefault());
    this._listen(canvas,"touchstart",e=>this._touchStart(e),{passive:false});
    this._listen(canvas,"touchmove",e=>this._touchMove(e),{passive:false});
    this._listen(canvas,"touchend",e=>this._touchEnd(e),{passive:false});
    this._listen(canvas,"touchcancel",e=>this._touchCancel(e),{passive:false});
    this._listen(document,"visibilitychange",()=>{ if(document.hidden)this._releaseKeyboard(); });

    const kb=this.root.querySelector("#console-keyboard"); if(kb)kb.onchange=e=>{this.keyboardEnabled=e.target.checked;if(!this.keyboardEnabled)this._releaseKeyboard();};
    const ms=this.root.querySelector("#console-mouse"); if(ms)ms.onchange=e=>{this.mouseEnabled=e.target.checked;};
    const scale=this.root.querySelector("#console-scale"); if(scale){scale.value=this.scale;scale.onchange=e=>{this.scale=e.target.value;localStorage.setItem("nanokvm-console-scale",this.scale);this._applyScale();};}
    const fs=this.root.querySelector("#console-fullscreen"); if(fs)fs.onclick=()=>this.fullscreen();
    const landscape=this.root.querySelector("#console-landscape"); if(landscape)landscape.onclick=()=>this.landscape();
    const reconnect=this.root.querySelector("#console-reconnect"); if(reconnect)reconnect.onclick=()=>this.restart();
    this.root.querySelectorAll("[data-console-key]").forEach(el=>el.onclick=()=>this._tapKey(el.dataset.consoleKey));
    const cad=this.root.querySelector("#console-cad"); if(cad)cad.onclick=()=>this._combo(["ControlLeft","AltLeft","Delete"]);
    const send=this.root.querySelector("#console-paste-send"); if(send)send.onclick=async()=>{const text=this.root.querySelector("#console-paste")?.value||"";if(text&&this.pasteText)await this.pasteText(text);};
  }

  _workerMessage(msg) {
    if (msg.type === "frame-size") { this.frame={width:msg.width||1280,height:msg.height||720}; this._applyScale(); return; }
    if (msg.type === "state") {
      this._setState(msg.state);
      if (msg.state === "closed" && !this.reconnectTimer) this.reconnectTimer=setTimeout(()=>this.restart(),1500);
      return;
    }
    if (msg.type === "unsupported") this._setState("error", `${msg.feature} unavailable`);
    if (msg.type === "error") this._setState("error", msg.message || "Console error");
    if (msg.type === "event") this._handleUpstreamEvent(msg.data);
  }

  _handleUpstreamEvent(raw) {
    try {
      const event=JSON.parse(raw);
      const data=typeof event.data==="string"?JSON.parse(event.data):event.data;
      if(data && ("numLock" in data || "capsLock" in data || "scrollLock" in data)){
        const el=this.root.querySelector("#console-leds");
        if(el)el.textContent=`NUM ${data.numLock?"●":"○"}  CAPS ${data.capsLock?"●":"○"}  SCR ${data.scrollLock?"●":"○"}`;
      }
    } catch (_) {}
  }

  _setState(state, detail="") {
    const el=this.root.querySelector("#console-state");
    if(el){el.dataset.state=state;el.textContent=detail?`${state}: ${detail}`:state;}
  }

  _send(payload) {
    if(!this.worker)return;
    const copy=new Uint8Array(payload);
    this.worker.postMessage({type:"input",data:copy.buffer},[copy.buffer]);
  }

  _keyboardReport() {
    const report=new Uint8Array(9); report[0]=1; report[1]=this.modifier;
    let i=3; for(const value of this.pressed.values()){if(i>=9)break;report[i++]=value;}
    this._send(report);
  }

  _keyDown(event) {
    if(!this.keyboardEnabled||event.isComposing)return;
    const code=event.code; const mod=MODIFIERS[code]; const key=keycode(code);
    if(mod===undefined&&key===undefined)return;
    event.preventDefault();event.stopPropagation();
    if(event.repeat)return;
    if(mod!==undefined)this.modifier|=mod; else if(this.pressed.size<6)this.pressed.set(code,key);
    this._keyboardReport();
  }

  _keyUp(event) {
    if(!this.keyboardEnabled)return;
    const code=event.code; const mod=MODIFIERS[code]; const key=keycode(code);
    if(mod===undefined&&key===undefined)return;
    event.preventDefault();event.stopPropagation();
    if(mod!==undefined)this.modifier&=~mod; else this.pressed.delete(code);
    this._keyboardReport();
  }

  _releaseKeyboard() { if(!this.worker){this.modifier=0;this.pressed.clear();return;} this.modifier=0;this.pressed.clear();this._keyboardReport(); }
  _tapKey(code){ const fake={code,isComposing:false,repeat:false,preventDefault(){},stopPropagation(){}};this._keyDown(fake);this._keyUp(fake); }
  _combo(codes){ const fake=c=>({code:c,isComposing:false,repeat:false,preventDefault(){},stopPropagation(){}});codes.forEach(c=>this._keyDown(fake(c)));[...codes].reverse().forEach(c=>this._keyUp(fake(c))); }

  _coords(clientX, clientY) {
    const rect=this.canvas.getBoundingClientRect(); if(!rect.width||!rect.height)return null;
    const x=Math.max(0,Math.min(1,(clientX-rect.left)/rect.width));
    const y=Math.max(0,Math.min(1,(clientY-rect.top)/rect.height));
    return {x:Math.floor(0x7fff*x)+1,y:Math.floor(0x7fff*y)+1};
  }

  _mouseReport(wheel=0) {
    const r=new Uint8Array(7);r[0]=2;r[1]=this.mouseButtons;r[2]=this.lastMouse.x&255;r[3]=(this.lastMouse.x>>8)&255;r[4]=this.lastMouse.y&255;r[5]=(this.lastMouse.y>>8)&255;r[6]=wheel&255;this._send(r);
  }
  _buttonBit(button){return button===0?1:button===2?2:button===1?4:button===3?8:button===4?16:0;}
  _moveTo(x,y){const p=this._coords(x,y);if(!p)return false;this.lastMouse=p;this._mouseReport();return true;}
  _mouseDown(e){if(!this.mouseEnabled)return;e.preventDefault();this.stage.focus({preventScroll:true});if(!this._moveTo(e.clientX,e.clientY))return;this.mouseButtons|=this._buttonBit(e.button);this._mouseReport();}
  _mouseUp(e){if(!this.mouseEnabled)return;const bit=this._buttonBit(e.button);if(!(this.mouseButtons&bit))return;e.preventDefault();this.mouseButtons&=~bit;this._mouseReport();}
  _mouseMove(e){if(!this.mouseEnabled)return;this._moveTo(e.clientX,e.clientY);}
  _wheel(e){if(!this.mouseEnabled)return;e.preventDefault();if(this._moveTo(e.clientX,e.clientY))this._mouseReport(e.deltaY>0?1:-1);}

  _touchStart(e){if(!this.mouseEnabled||!e.touches.length)return;e.preventDefault();this.stage.focus({preventScroll:true});const t=e.touches[0];this._moveTo(t.clientX,t.clientY);this.touch={x:t.clientX,y:t.clientY,lastY:t.clientY,moved:false,long:false,multi:e.touches.length>1};if(e.touches.length===1)this.longPressTimer=setTimeout(()=>{if(!this.touch||this.touch.moved)return;this.touch.long=true;this.mouseButtons|=2;this._mouseReport();if(navigator.vibrate)navigator.vibrate(40);},700);}
  _touchMove(e){if(!this.mouseEnabled||!this.touch||!e.touches.length)return;e.preventDefault();const t=e.touches[0];if(e.touches.length>1){this.touch.multi=true;if(this.longPressTimer)clearTimeout(this.longPressTimer);const dy=t.clientY-this.touch.lastY;if(Math.abs(dy)>6){this._mouseReport(dy>0?1:-1);this.touch.lastY=t.clientY;}return;}if(Math.hypot(t.clientX-this.touch.x,t.clientY-this.touch.y)>8){this.touch.moved=true;if(this.longPressTimer)clearTimeout(this.longPressTimer);}this._moveTo(t.clientX,t.clientY);}
  _touchEnd(e){if(!this.touch)return;e.preventDefault();if(this.longPressTimer)clearTimeout(this.longPressTimer);if(this.touch.long){this.mouseButtons&=~2;this._mouseReport();}else if(!this.touch.moved&&!this.touch.multi){this.mouseButtons|=1;this._mouseReport();this.mouseButtons&=~1;this._mouseReport();}this.touch=null;}
  _touchCancel(e){if(e)e.preventDefault();if(this.longPressTimer)clearTimeout(this.longPressTimer);this.mouseButtons=0;this._mouseReport();this.touch=null;}

  _applyScale() {
    if(!this.canvas)return;
    const mode=this.scale;
    this.canvas.style.maxWidth="none";this.canvas.style.maxHeight="none";
    if(mode==="fit") { this.canvas.style.width="100%"; this.canvas.style.height="auto"; this.canvas.style.maxHeight="calc(100vh - 250px)"; this.canvas.style.objectFit="contain"; }
    else { const factor=Math.max(.5,Math.min(3,Number(mode)||1));this.canvas.style.width=`${Math.round(this.frame.width*factor)}px`;this.canvas.style.height=`${Math.round(this.frame.height*factor)}px`;this.canvas.style.objectFit="fill"; }
  }

  async fullscreen() { const shell=this.root.querySelector("#console-shell");if(!shell)return;try{if(document.fullscreenElement)await document.exitFullscreen();else await shell.requestFullscreen();}catch(err){this._setState("error",err?.message||String(err));} }
  async landscape() { const shell=this.root.querySelector("#console-shell");try{if(!document.fullscreenElement&&shell)await shell.requestFullscreen();if(screen.orientation?.lock)await screen.orientation.lock("landscape");}catch(_){this._setState("connected",this.labels.rotateHint||"Rotate device to landscape");} }
}
