// Browser API fixtures are test-only; execute the production session controller.
const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs"),
  vm = require("node:vm"),
  path = require("node:path");
const source = fs.readFileSync(
  path.join(
    __dirname,
    "../nanokvm_rest/webui/static/jetkvm-console-controller.js",
  ),
  "utf8",
);
const settle = async () => {
  for (let i = 0; i < 12; i++)
    await new Promise((resolve) => setImmediate(resolve));
};

function harness(extension = "atx-power") {
  class Element {
    constructor() {
      this.handlers = new Map();
      this.dataset = {};
      this.style = {};
      this.hidden = false;
      this.textContent = "";
      this.videoWidth = 1920;
      this.videoHeight = 1080;
      this.srcObject = null;
    }
    addEventListener(type, fn) {
      if (!this.handlers.has(type)) this.handlers.set(type, new Set());
      this.handlers.get(type).add(fn);
    }
    removeEventListener(type, fn) {
      this.handlers.get(type)?.delete(fn);
    }
    emit(type, event = {}) {
      event.preventDefault ??= () => {};
      event.stopPropagation ??= () => {};
      event.target ??= this;
      for (const fn of this.handlers.get(type) || []) fn(event);
    }
    focus() {
      document.activeElement = this;
    }
    play() {
      return Promise.resolve();
    }
    getBoundingClientRect() {
      return { left: 0, top: 0, width: 1000, height: 600 };
    }
    requestPointerLock() {
      document.pointerLockElement = this;
      return Promise.resolve();
    }
    requestFullscreen() {
      document.fullscreenElement = this;
      return Promise.resolve();
    }
    count() {
      return [...this.handlers.values()].reduce((n, set) => n + set.size, 0);
    }
  }
  const nodes = new Map();
  const get = (id) => {
    if (!nodes.has(id)) nodes.set(id, new Element());
    return nodes.get(id);
  };
  const document = new Element();
  document.pointerLockElement = null;
  document.exitPointerLock = () => {
    document.pointerLockElement = null;
  };
  document.exitFullscreen = () => Promise.resolve();
  document.hidden = false;
  const window = new Element();
  const cad = get("console-cad");
  const key = get("key");
  key.dataset.consoleKey = "F2";
  const atx = get("atx");
  atx.dataset.consoleAtx = "reset";
  atx.textContent = "Reset";
  const root = {
    querySelector: (selector) => get(selector.replace(/^#/, "")),
    querySelectorAll: (selector) =>
      selector === "[data-console-key]"
        ? [key]
        : selector === "[data-console-atx]"
          ? [atx]
          : [key, cad, atx],
  };
  const timers = new Map();
  let timerId = 0;
  const later = (callback, ms) => {
    if (ms === 60) return setTimeout(callback, 0);
    const id = ++timerId;
    timers.set(id, { callback, ms });
    return id;
  };
  const records = [];
  const sockets = [];
  const peers = [];
  class Channel {
    constructor() {
      this.readyState = "connecting";
    }
    send(raw) {
      const packet = JSON.parse(raw);
      records.push(packet);
      queueMicrotask(() =>
        this.onmessage?.({
          data: JSON.stringify({
            jsonrpc: "2.0",
            id: packet.id,
            ...(packet.method === "getActiveExtension" && extension === "error"
              ? { error: { code: -32601 } }
              : {
                  result:
                    packet.method === "getActiveExtension" ? extension : null,
                }),
          }),
        }),
      );
    }
    close() {
      this.readyState = "closed";
    }
  }
  class PC {
    constructor(options) {
      this.options = options;
      this.connectionState = "new";
      this.iceConnectionState = "new";
      peers.push(this);
    }
    addTransceiver(kind, options) {
      this.transceiver = {
        kind,
        ...options,
        setCodecPreferences: (codecs) => {
          this.codecs = codecs;
        },
      };
      return this.transceiver;
    }
    createDataChannel(label, options) {
      this.dataLabel = label;
      this.dataOptions = options;
      this.channel = new Channel();
      return this.channel;
    }
    async createOffer() {
      return { type: "offer", sdp: "v=0\r\nmock-test-offer" };
    }
    async setLocalDescription(value) {
      this.localDescription = value;
      this.onicecandidate?.({
        candidate: {
          toJSON: () => ({
            candidate: "candidate:1 1 UDP 1 192.168.1.50 40000 typ host",
            sdpMid: "0",
          }),
        },
      });
    }
    async setRemoteDescription(value) {
      this.remoteDescription = value;
      this.connectionState = "connected";
      this.iceConnectionState = "connected";
      this.onconnectionstatechange?.();
      this.channel.readyState = "open";
      this.channel.onopen?.();
    }
    async addIceCandidate(candidate) {
      (this.candidates ||= []).push(candidate);
    }
    async getStats() {
      return new Map([
        [
          "in",
          {
            type: "inbound-rtp",
            kind: "video",
            framesPerSecond: 29.7,
            framesDecoded: 300,
            timestamp: 1000,
          },
        ],
        ["transport", { type: "transport", selectedCandidatePairId: "pair" }],
        ["pair", { currentRoundTripTime: 0.008 }],
      ]);
    }
    close() {
      this.connectionState = "closed";
    }
  }
  class WS {
    constructor(url, protocols) {
      this.url = url;
      this.protocols = protocols;
      this.readyState = 1;
      this.sent = [];
      sockets.push(this);
    }
    send(packet) {
      this.sent.push(packet);
    }
    receive(packet) {
      this.onmessage?.({
        data: typeof packet === "string" ? packet : JSON.stringify(packet),
      });
    }
    close() {
      this.readyState = 3;
    }
  }
  const ticket = {
    path: "/api/nanokvm_rest/console",
    protocol: "nanokvm-console",
    token: "nkv-test-one-use",
    provider: "jetkvm",
    transport: "webrtc",
  };
  const context = vm.createContext({
    document,
    window,
    location: {
      href: "https://manager.local/ingress/test/",
      host: "manager.local",
      protocol: "https:",
    },
    RTCPeerConnection: PC,
    RTCRtpReceiver: {
      getCapabilities: () => ({ codecs: [{ mimeType: "video/H264" }] }),
    },
    WebSocket: WS,
    MediaStream: class {},
    AbortController,
    URL,
    btoa: (v) => Buffer.from(v, "binary").toString("base64"),
    atob: (v) => Buffer.from(v, "base64").toString("binary"),
    setTimeout: later,
    clearTimeout: (id) => timers.delete(id),
    setInterval: later,
    clearInterval: (id) => timers.delete(id),
    confirm: () => true,
    console,
  });
  vm.runInContext(source, context);
  const controller = new context.JetKVMConsoleController({
    entryId: "jet",
    root,
    requestSession: async () => ticket,
  });
  const api = {
    controller,
    document,
    window,
    get,
    nodes,
    records,
    sockets,
    peers,
    timers,
    context,
  };
  api.connect = async () => {
    controller.start();
    await settle();
    sockets.at(-1).receive({ type: "console", state: "connected" });
    await settle();
    sockets.at(-1).receive({
      type: "answer",
      data: Buffer.from(
        JSON.stringify({ type: "answer", sdp: "v=0\r\nmock-test-answer" }),
      ).toString("base64"),
    });
    await settle();
  };
  api.fire = async (ms) => {
    const item = [...timers].find(([, timer]) => timer.ms === ms);
    assert.ok(item, `timer ${ms} exists`);
    timers.delete(item[0]);
    item[1].callback();
    await settle();
  };
  return api;
}

test("actual JetKVM envelopes, ordered rpc channel, H264 preference and LAN-only ICE", async () => {
  const h = harness();
  await h.connect();
  assert.equal(h.controller.state, "CONNECTED");
  assert.equal(h.sockets[0].protocols[1], "nkv-test-one-use");
  assert.equal(h.peers[0].dataLabel, "rpc");
  assert.equal(h.peers[0].dataOptions.ordered, true);
  assert.equal(h.peers[0].options.iceServers.length, 0);
  assert.equal(h.peers[0].codecs[0].mimeType, "video/H264");
  const messages = h.sockets[0].sent.map((s) => JSON.parse(s));
  assert.equal(messages[0].type, "offer");
  assert.equal(messages[1].type, "new-ice-candidate");
  assert.equal(
    JSON.parse(Buffer.from(messages[0].data.sd, "base64").toString()).type,
    "offer",
  );
  await h.controller.stop();
  assert.equal(h.sockets[0].readyState, 3);
  assert.equal(h.peers[0].connectionState, "closed");
});

test("keyboard modifiers, F keys, arrows, keyup and Ctrl+Alt+Del are acknowledged in order", async () => {
  const h = harness();
  await h.connect();
  const stage = h.get("console-stage");
  stage.emit("keydown", { code: "ControlLeft" });
  stage.emit("keydown", { code: "AltLeft" });
  stage.emit("keydown", { code: "Delete" });
  stage.emit("keyup", { code: "Delete" });
  stage.emit("keyup", { code: "AltLeft" });
  stage.emit("keyup", { code: "ControlLeft" });
  await settle();
  let reports = h.records.filter((r) => r.method === "keyboardReport");
  assert.ok(
    reports.some((r) => r.params.modifier === 5 && r.params.keys.includes(76)),
  );
  assert.deepEqual(reports.at(-1).params, { modifier: 0, keys: [] });
  for (const code of [
    "F1",
    "F12",
    "ArrowLeft",
    "Enter",
    "Escape",
    "Backspace",
    "MetaLeft",
  ]) {
    stage.emit("keydown", { code });
    stage.emit("keyup", { code });
  }
  h.get("console-cad").emit("click");
  await settle();
  reports = h.records.filter((r) => r.method === "keyboardReport");
  assert.deepEqual(reports.at(-2).params, { modifier: 5, keys: [76] });
  assert.deepEqual(reports.at(-1).params, { modifier: 0, keys: [] });
  await h.controller.stop();
});

test("keyboard is not globally captured and all listeners are removed on leave", async () => {
  const h = harness();
  await h.connect();
  assert.equal(h.window.handlers.get("keydown")?.size || 0, 0);
  assert.equal(h.document.handlers.get("keydown")?.size || 0, 0);
  h.get("console-stage").emit("keydown", { code: "ShiftLeft" });
  h.get("console-stage").emit("blur");
  await settle();
  assert.deepEqual(
    h.records.filter((r) => r.method === "keyboardReport").at(-1).params,
    { modifier: 0, keys: [] },
  );
  await h.controller.stop();
  assert.equal(h.window.count(), 0);
  assert.equal(h.document.count(), 0);
  for (const node of h.nodes.values()) assert.equal(node.count(), 0);
});

test("absolute mouse respects letterboxing, all buttons release, and wheel uses RPC", async () => {
  const h = harness();
  await h.connect();
  const video = h.get("console-video");
  for (const buttons of [1, 2, 4]) {
    video.emit("mousedown", { buttons, clientX: 500, clientY: 300 });
    h.window.emit("mouseup", { buttons: 0, clientX: 500, clientY: 300 });
  }
  video.emit("wheel", { deltaY: 40, deltaX: 80, deltaMode: 0 });
  await settle();
  const mouse = h.records.filter((r) => r.method === "absMouseReport");
  for (const buttons of [1, 2, 4])
    assert.ok(mouse.some((r) => r.params.buttons === buttons));
  assert.equal(mouse[0].params.x, 16384);
  assert.equal(mouse[0].params.y, 16384);
  assert.equal(mouse.at(-1).params.buttons, 0);
  assert.deepEqual(h.records.find((r) => r.method === "wheelReport").params, {
    wheelY: -1,
    wheelX: 2,
  });
  await h.controller.stop();
});

test("relative mouse requires Pointer Lock and clamps signed movement", async () => {
  const h = harness();
  await h.connect();
  h.get("console-mouse-mode").emit("change", { target: { value: "relative" } });
  await settle();
  h.get("console-video").emit("mousedown", { buttons: 1 });
  assert.equal(h.document.pointerLockElement, h.get("console-video"));
  h.get("console-video").emit("mousemove", {
    movementX: 500,
    movementY: -500,
    buttons: 0,
  });
  await settle();
  assert.ok(
    h.records.some(
      (r) =>
        r.method === "relMouseReport" &&
        r.params.dx === 127 &&
        r.params.dy === -127,
    ),
  );
  await h.controller.stop();
  assert.equal(h.document.pointerLockElement, null);
});

test("ATX is hidden without the actual extension and power command is real RPC", async () => {
  for (const extension of ["none", "error", "atx-power"]) {
    const h = harness(extension);
    await h.connect();
    assert.equal(h.get("console-atx").hidden, extension !== "atx-power");
    if (extension === "atx-power") {
      await h.controller.sendATXCommand("power-long");
      assert.deepEqual(h.records.at(-1).params, { action: "power-long" });
    }
    await h.controller.stop();
  }
});

test("measured stats populate resolution, FPS and RTT without invented defaults", async () => {
  const h = harness();
  await h.connect();
  await h.controller._stats(h.controller.generation);
  assert.match(h.get("console-metrics").textContent, /1920 × 1080/);
  assert.match(h.get("console-metrics").textContent, /29.7 FPS/);
  assert.match(h.get("console-metrics").textContent, /RTT 8.0 ms/);
  await h.controller.stop();
});

test("reconnect is bounded at 1, 2, 5, 10 seconds and re-requests backend tickets", async () => {
  const h = harness();
  h.controller.start();
  await settle();
  for (const delay of [1000, 2000, 5000, 10000]) {
    h.controller._fail(
      { code: "ice_failed", message: "network" },
      h.controller.generation,
    );
    assert.equal(h.controller.state, "RECONNECTING");
    await h.fire(delay);
  }
  h.controller._fail(
    { code: "ice_failed", message: "network" },
    h.controller.generation,
  );
  assert.equal(h.controller.state, "ERROR");
  assert.equal(h.controller.attempt, 4);
  assert.equal(h.sockets.length, 5);
  await h.controller.stop();
});

test("bad credentials, TLS and setup errors do not cause a reconnect loop", async () => {
  for (const code of [
    "invalid_password",
    "authentication_required",
    "tls_error",
    "setup_required",
  ]) {
    const h = harness();
    h.controller.start();
    await settle();
    h.sockets[0].receive({
      type: "manager-error",
      error: { code, message: "Czytelna przyczyna", detail: "Safe detail" },
    });
    await settle();
    assert.equal(h.controller.state, "ERROR");
    assert.equal(h.controller.attempt, 0);
    assert.equal(h.get("console-error").hidden, false);
    assert.match(h.get("console-error-detail").textContent, /Safe detail/);
    await h.controller.stop();
  }
});

test("a late session ticket cannot open a socket after leaving the view", async () => {
  const h = harness();
  let resolve;
  h.controller.requestSession = () =>
    new Promise((r) => {
      resolve = r;
    });
  h.controller.start();
  await settle();
  await h.controller.stop();
  resolve({ path: "/api/nanokvm_rest/console", transport: "webrtc" });
  await settle();
  assert.equal(h.sockets.length, 0);
  assert.equal(h.controller.state, "DISCONNECTED");
});
