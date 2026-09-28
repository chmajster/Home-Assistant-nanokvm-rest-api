// Execute the real Manager script with a minimal DOM/HTTP harness, without npm dependencies.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {test} = require('node:test');
const source = fs.readFileSync(path.join(__dirname, '../nanokvm_rest/webui/static/app.js'), 'utf8');

async function manager(responses) {
  const elements = new Map();
  class Element {
    constructor() {
      this.innerHTML = ''; this.textContent = ''; this.dataset = {}; this.handlers = {};
      this.classList = {toggle() {}, add() {}, remove() {}};
    }
    setAttribute() {}
    before(element) { elements.set(element.id, element); }
    addEventListener(name, callback) { this.handlers[name] = callback; }
  }
  const getElement = id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  };
  const devicesButton = new Element();
  devicesButton.dataset.view = 'devices';
  const document = {
    getElementById: getElement,
    createElement: () => new Element(),
    querySelectorAll: selector => selector === '[data-view]' ? [devicesButton] : [],
  };
  let requestCount = 0;
  const context = vm.createContext({
    document,
    fetch: async url => {
      assert.equal(url, 'api/bootstrap');
      const payload = responses[Math.min(requestCount++, responses.length - 1)];
      return {ok: payload.ok !== false, status: payload.ok === false ? 502 : 200, json: async () => payload};
    },
    setTimeout() { return 1; }, clearTimeout() {}, setInterval() { return 1; },
    window: {top: null}, console,
  });
  vm.runInContext(source, context);
  const settle = () => new Promise(resolve => setImmediate(resolve));
  await settle();
  return {elements, devicesButton, settle, getElement};
}
const response = (devices, warnings = []) => ({ok: true, devices: {devices}, operations: {}, updates: {}, warnings});

test('saved but unloaded NanoKVM is visible and power controls are disabled', async () => {
  const ui = await manager([response([{entry_id: 'id1', title: 'Saved NanoKVM', loaded: false}])]);
  const html = ui.getElement('content').innerHTML;
  assert.match(html, /Saved NanoKVM/);
  assert.match(html, /Konfiguracja zapisana/);
  assert.match(html, /data-action="power_on"[^>]*disabled/);
  assert.match(html, /data-action="reset"[^>]*disabled/);
  assert.doesNotMatch(html, /Brak skonfigurowanych/);
});

test('fallback inventory remains visible with persistent escaped diagnostics', async () => {
  const ui = await manager([response([{entry_id: 'id1', title: '<img src=x>', loaded: true, backend_available: false}], ['Restart <script>evil()</script>'])]);
  const html = ui.getElement('content').innerHTML;
  assert.match(html, /&lt;img src=x&gt;/);
  assert.match(html, /Brak danych z integracji/);
  assert.match(html, /data-action="power_on"[^>]*disabled/);
  const diagnostics = ui.getElement('integration-diagnostics').innerHTML;
  assert.match(diagnostics, /&lt;script&gt;/);
  assert.doesNotMatch(diagnostics, /<script>/);
  ui.devicesButton.handlers.click();
  assert.equal(ui.getElement('integration-diagnostics').innerHTML, diagnostics);
  assert.match(ui.getElement('content').innerHTML, /&lt;img src=x&gt;/);
});

test('empty devices tab has an explanation instead of a blank grid', async () => {
  const ui = await manager([response([])]);
  ui.devicesButton.handlers.click();
  assert.match(ui.getElement('content').innerHTML, /Brak skonfigurowanych urządzeń/);
  assert.match(ui.getElement('content').innerHTML, /Dodaj NanoKVM/);
});

test('transport failure is not shown as zero configured devices', async () => {
  const ui = await manager([{ok: false, error: 'HA unavailable'}]);
  assert.match(ui.getElement('content').innerHTML, /HA unavailable/);
  assert.doesNotMatch(ui.getElement('content').innerHTML, /Brak skonfigurowanych/);
});

test('malformed bootstrap response is an error, not an empty inventory', async () => {
  const ui = await manager([{ok: true, devices: {}}]);
  assert.match(ui.getElement('content').innerHTML, /Nieprawidłowa lista urządzeń/);
});

test('refresh discovers newly saved devices and clears resolved warnings', async () => {
  const ui = await manager([response([], ['Backend unavailable']), response([{entry_id: 'new', title: 'New NanoKVM', loaded: true, available: true}])]);
  assert.match(ui.getElement('integration-diagnostics').innerHTML, /Backend unavailable/);
  await ui.getElement('refresh').handlers.click();
  await ui.settle();
  assert.match(ui.getElement('content').innerHTML, /New NanoKVM/);
  assert.match(ui.getElement('content').innerHTML, /Online/);
  assert.equal(ui.getElement('integration-diagnostics').innerHTML, '');
  assert.doesNotMatch(ui.getElement('content').innerHTML, /data-action="power_on"[^>]*disabled/);
});
