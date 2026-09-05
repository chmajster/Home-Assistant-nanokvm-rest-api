let canvas = null;
let ctx = null;
let socket = null;
let decoder = null;
let heartbeat = null;
let started = false;
let firstFrame = true;

const CHANNEL_STREAM = 0;
const CHANNEL_INPUT = 1;
const STREAM_ACK = 2;
const STREAM_RESYNC = 3;
const HEARTBEAT = 0;

self.onmessage = (event) => {
  const msg = event.data || {};
  if (msg.type === "start") start(msg);
  else if (msg.type === "input" && msg.data) sendChannel(CHANNEL_INPUT, new Uint8Array(msg.data));
  else if (msg.type === "stop") stop();
};

function start(msg) {
  stop();
  if (!msg.canvas || !msg.url) return;
  canvas = msg.canvas;
  ctx = canvas.getContext("2d", { alpha: false, desynchronized: true });
  started = true;
  firstFrame = true;
  self.postMessage({ type: "state", state: "connecting" });
  const ws = new WebSocket(msg.url, [msg.protocol || "nanokvm-console", msg.token]);
  ws.binaryType = "arraybuffer";
  socket = ws;
  ws.onopen = () => {
    if (socket !== ws) return;
    self.postMessage({ type: "state", state: "connected" });
    heartbeat = setInterval(() => sendChannel(CHANNEL_INPUT, new Uint8Array([HEARTBEAT])), 10000);
  };
  ws.onmessage = (event) => {
    if (socket !== ws || !started) return;
    if (event.data instanceof ArrayBuffer) handleFrame(event.data);
    else if (typeof event.data === "string") self.postMessage({ type: "event", data: event.data });
  };
  ws.onerror = () => self.postMessage({ type: "state", state: "error" });
  ws.onclose = () => {
    if (socket === ws) socket = null;
    clearHeartbeat();
    resetDecoder();
    if (started) self.postMessage({ type: "state", state: "closed" });
  };
}

function stop() {
  started = false;
  clearHeartbeat();
  const ws = socket;
  socket = null;
  if (ws && ws.readyState < WebSocket.CLOSING) ws.close();
  resetDecoder();
}

function clearHeartbeat() {
  if (heartbeat) clearInterval(heartbeat);
  heartbeat = null;
}

function handleFrame(buffer) {
  if (buffer.byteLength < 9 || !ctx || !canvas) return;
  const view = new DataView(buffer);
  const key = view.getUint8(0) === 1;
  const timestamp = Number(view.getBigUint64(1, true));
  const data = new Uint8Array(buffer, 9);
  if (!decoder) {
    if (!key) { requestResync(); return; }
    decoder = createDecoder();
    if (!decoder) { requestResync(); return; }
  }
  try {
    decoder.decode(new EncodedVideoChunk({ type: key ? "key" : "delta", timestamp, data }));
  } catch (_) {
    requestResync();
    resetDecoder();
  }
}

function createDecoder() {
  if (!self.VideoDecoder) {
    self.postMessage({ type: "unsupported", feature: "WebCodecs" });
    return null;
  }
  let instance = null;
  try {
    instance = new VideoDecoder({
      output: (frame) => drawFrame(instance, frame),
      error: () => {
        if (decoder === instance) {
          requestResync();
          resetDecoder();
        }
      }
    });
    instance.configure({
      codec: "avc1.42E02A",
      hardwareAcceleration: "prefer-hardware",
      optimizeForLatency: true
    });
    return instance;
  } catch (err) {
    if (instance && instance.state !== "closed") instance.close();
    self.postMessage({ type: "error", message: String(err) });
    return null;
  }
}

function drawFrame(source, frame) {
  if (source !== decoder || !canvas || !ctx) { frame.close(); return; }
  try {
    if (canvas.width !== frame.displayWidth || canvas.height !== frame.displayHeight) {
      canvas.width = frame.displayWidth;
      canvas.height = frame.displayHeight;
      self.postMessage({ type: "frame-size", width: frame.displayWidth, height: frame.displayHeight });
    }
    ctx.drawImage(frame, 0, 0, canvas.width, canvas.height);
    acknowledge(frame.timestamp || 0);
    if (firstFrame) {
      firstFrame = false;
      self.postMessage({ type: "state", state: "streaming" });
    }
  } finally {
    frame.close();
  }
}

function acknowledge(timestamp) {
  const ack = new ArrayBuffer(9);
  const view = new DataView(ack);
  view.setUint8(0, STREAM_ACK);
  view.setBigUint64(1, BigInt(Math.max(0, Math.trunc(timestamp))), true);
  sendChannel(CHANNEL_STREAM, new Uint8Array(ack));
}

function requestResync() {
  sendChannel(CHANNEL_STREAM, new Uint8Array([STREAM_RESYNC]));
}

function sendChannel(channel, payload) {
  const ws = socket;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  const out = new Uint8Array(payload.length + 1);
  out[0] = channel;
  out.set(payload, 1);
  ws.send(out);
}

function resetDecoder() {
  if (decoder && decoder.state !== "closed") {
    try { decoder.close(); } catch (_) {}
  }
  decoder = null;
}
