// Native NanoKVM regression: execute the production controller, not a replacement.
const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs"),
  vm = require("node:vm"),
  path = require("node:path");
const source = fs.readFileSync(
  path.join(
    __dirname,
    "../nanokvm_rest/webui/static/remote-console-controller.js",
  ),
  "utf8",
);
function harness(request) {
  const nodes = new Map(),
    workers = [],
    timers = new Map();
  let next = 0;
  class Element {
    constructor(id) {
      this.id = id;
      this.dataset = {};
      this.style = {};
      this.handlers = new Map();
    }
    addEventListener(t, f) {
      if (!this.handlers.has(t)) this.handlers.set(t, new Set());
      this.handlers.get(t).add(f);
    }
    removeEventListener(t, f) {
      this.handlers.get(t)?.delete(f);
    }
    cloneNode() {
      const copy = new Element(this.id);
      copy.dataset = { ...this.dataset };
      return copy;
    }
    replaceWith(copy) {
      nodes.set(this.id, copy);
    }
    transferControlToOffscreen() {
      if (this.transferred) throw Error("Canvas already transferred");
      this.transferred = true;
      return {};
    }
    getBoundingClientRect() {
      return { left: 0, top: 0, width: 1000, height: 600 };
    }
    focus() {}
  }
  const get = (id) => {
    if (!nodes.has(id)) nodes.set(id, new Element(id));
    return nodes.get(id);
  };
  const root = {
    querySelector: (s) => get(s.slice(1)),
    querySelectorAll: () => [],
  };
  const window = new Element("window");
  window.location = { href: "http://manager.local/" };
  const document = new Element("document");
  document.currentScript = {
    src: "http://manager.local/static/remote-console-controller.js",
  };
  class Worker {
    constructor() {
      this.messages = [];
      workers.push(this);
    }
    postMessage(data) {
      this.messages.push(data);
    }
    terminate() {
      this.stopped = true;
    }
  }
  const context = vm.createContext({
    window,
    document,
    URL,
    Worker,
    localStorage: { getItem: () => null, setItem() {} },
    location: { host: "manager.local", protocol: "http:" },
    setTimeout: (fn, ms) => {
      const id = ++next;
      timers.set(id, { fn, ms });
      return id;
    },
    clearTimeout: (id) => timers.delete(id),
    console,
  });
  vm.runInContext(source, context);
  const controller = new window.RemoteConsoleController({
    entryId: "nano-1",
    root,
    requestSession:
      request ||
      (() =>
        Promise.resolve({
          path: "/api/nanokvm_rest/console",
          protocol: "nanokvm-console",
          token: "nkv-fixture",
        })),
  });
  return { controller, nodes, workers, timers, context };
}
const event = (code) => ({
  code,
  preventDefault() {},
  stopPropagation() {},
  isComposing: false,
  repeat: false,
});
test("native keyboard modifiers, Ctrl+Alt+Delete and mouse HID reports stay binary", async () => {
  const h = harness();
  await h.controller.start();
  h.controller._combo(["ControlLeft", "AltLeft", "Delete"]);
  const reports = h.workers[0].messages
    .filter((x) => x.type === "input")
    .map((x) => Array.from(new Uint8Array(x.data)));
  assert.ok(reports.some((x) => x[0] === 1 && x[1] === 5 && x[3] === 0x4c));
  assert.equal(reports.at(-1)[1], 0);
  h.controller._keyDown(event("F12"));
  h.controller._keyUp(event("F12"));
  h.controller.mouseButtons = 2;
  h.controller._mouseReport(-1);
  const mouse = Array.from(new Uint8Array(h.workers[0].messages.at(-1).data));
  assert.equal(mouse[0], 2);
  assert.equal(mouse[1], 2);
  assert.equal(mouse[6], 255);
  h.controller.stop();
  assert.equal(h.controller._listeners.length, 0);
  assert.ok(h.workers[0].stopped);
});
test("NanoKVM reconnect replaces transferred canvas and stops after four attempts", async () => {
  const h = harness();
  await h.controller.start();
  const original = h.nodes.get("console-canvas");
  await h.controller.restart();
  assert.notEqual(h.nodes.get("console-canvas"), original);
  assert.equal(h.workers.length, 2);
  const delays = [];
  for (let i = 0; i < 4; i++) {
    h.controller._workerMessage({ type: "state", state: "closed" });
    const id = h.controller.reconnectTimer;
    const timer = h.timers.get(id);
    delays.push(timer.ms);
    h.timers.delete(id);
    timer.fn();
    await new Promise(setImmediate);
  }
  assert.deepEqual(delays, [1000, 2000, 5000, 10000]);
  h.controller._workerMessage({ type: "state", state: "closed" });
  assert.equal(h.controller.manualStop, true);
  assert.equal(h.controller.reconnectTimer, null);
});
test("explicit backend disconnect does not restart NanoKVM", async () => {
  const h = harness();
  await h.controller.start();
  h.controller._handleUpstreamEvent(
    JSON.stringify({ type: "console", state: "disconnected", reason: "user" }),
  );
  assert.equal(h.controller.worker, null);
  assert.equal(h.controller.manualStop, true);
  assert.equal(h.controller.reconnectTimer, null);
});
test("leaving the panel while a NanoKVM ticket is pending cannot create a worker", async () => {
  let resolve;
  const h = harness(
    () =>
      new Promise((r) => {
        resolve = r;
      }),
  );
  const pending = h.controller.start();
  h.controller.stop();
  resolve({ path: "/api/nanokvm_rest/console", token: "nkv-fixture" });
  await pending;
  assert.equal(h.workers.length, 0);
});
