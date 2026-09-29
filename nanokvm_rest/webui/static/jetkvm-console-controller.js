/* Independent JetKVM local-protocol implementation. No upstream GPL code copied.
 * Reference: jetkvm/kvm 939422c8b00b423f6320db04df4adfbc6d2b3012.
 * Signaling is authenticated by HA. Video and ordered JSON-RPC HID use WebRTC.
 */
(() => {
  "use strict";
  const KEY_CODES = {
    Enter: 40,
    Escape: 41,
    Backspace: 42,
    Tab: 43,
    Space: 44,
    Minus: 45,
    Equal: 46,
    BracketLeft: 47,
    BracketRight: 48,
    Backslash: 49,
    Semicolon: 51,
    Quote: 52,
    Backquote: 53,
    Comma: 54,
    Period: 55,
    Slash: 56,
    CapsLock: 57,
    PrintScreen: 70,
    ScrollLock: 71,
    Pause: 72,
    Insert: 73,
    Home: 74,
    PageUp: 75,
    Delete: 76,
    End: 77,
    PageDown: 78,
    ArrowRight: 79,
    ArrowLeft: 80,
    ArrowDown: 81,
    ArrowUp: 82,
    NumLock: 83,
    NumpadDivide: 84,
    NumpadMultiply: 85,
    NumpadSubtract: 86,
    NumpadAdd: 87,
    NumpadEnter: 88,
    Numpad0: 98,
    NumpadDecimal: 99,
    IntlBackslash: 100,
    ContextMenu: 101,
  };
  for (let i = 0; i < 26; i++)
    KEY_CODES[`Key${String.fromCharCode(65 + i)}`] = 4 + i;
  for (let i = 1; i <= 9; i++) {
    KEY_CODES[`Digit${i}`] = 29 + i;
    KEY_CODES[`Numpad${i}`] = 88 + i;
  }
  KEY_CODES.Digit0 = 39;
  for (let i = 1; i <= 12; i++) KEY_CODES[`F${i}`] = 57 + i;
  const MODIFIERS = {
    ControlLeft: 1,
    ShiftLeft: 2,
    AltLeft: 4,
    MetaLeft: 8,
    ControlRight: 16,
    ShiftRight: 32,
    AltRight: 64,
    MetaRight: 128,
  };
  const RETRY_DELAYS = [1000, 2000, 5000, 10000];
  const NON_RETRYABLE = new Set([
    "invalid_password",
    "authentication_required",
    "setup_required",
    "not_jetkvm",
    "permission_denied",
    "forbidden_target",
    "tls_error",
    "wrong_device",
    "busy",
    "rate_limited",
    "unsupported",
  ]);
  const clamp = (v, min, max) => Math.max(min, Math.min(max, Math.round(v)));
  const envelope = (description) =>
    btoa(unescape(encodeURIComponent(JSON.stringify(description))));
  const description = (encoded) =>
    JSON.parse(decodeURIComponent(escape(atob(encoded))));
  const problem = (code, message, detail = "") =>
    Object.assign(new Error(message), { code, detail });

  class JetKVMConsoleController {
    constructor({ entryId, root, requestSession, wakeOnLAN }) {
      Object.assign(this, { entryId, root, requestSession, wakeOnLAN });
      this.stage = root.querySelector("#console-stage");
      this.video = root.querySelector("#console-video");
      this.running = false;
      this.generation = 0;
      this.attempt = 0;
      this.listeners = [];
      this.pending = new Map();
      this.serial = 0;
      this.keys = new Set();
      this.keyboardChain = Promise.resolve();
      this.mouseQueue = [];
      this.mouseSending = false;
      this.buttons = 0;
      this.lastPosition = { x: 0, y: 0 };
      this.keyboardEnabled = true;
      this.mouseEnabled = true;
      this.relative = false;
      this.scale = "fit";
      this.state = "DISCONNECTED";
    }
    _node(id) {
      return this.root.querySelector(`#${id}`);
    }
    _text(id, text) {
      const node = this._node(id);
      if (node) node.textContent = text;
    }
    _listen(target, event, callback, options) {
      if (!target) return;
      target.addEventListener(event, callback, options);
      this.listeners.push([target, event, callback, options]);
    }
    _current(g) {
      return this.running && g === this.generation;
    }
    _state(state, error) {
      this.state = state;
      const node = this._node("console-state");
      if (node) {
        node.dataset.state = state.toLowerCase();
        node.textContent = state;
      }
      this._text(
        "console-message",
        error?.message ||
          {
            CONNECTING: "Łączenie z JetKVM…",
            CONNECTED: "Kliknij obraz, aby sterować komputerem.",
            RECONNECTING: `Ponowne łączenie (${this.attempt}/${RETRY_DELAYS.length})…`,
            DISCONNECTED: "Sesja rozłączona.",
            ERROR: "Nie można połączyć się z JetKVM.",
          }[state] ||
          state,
      );
      const details = this._node("console-error");
      if (details) {
        details.hidden = !error;
        this._text(
          "console-error-detail",
          error
            ? `${error.code || "connection_error"}${error.detail ? `: ${error.detail}` : ""}`
            : "",
        );
      }
      this.root
        .querySelectorAll("[data-console-key],#console-cad,[data-console-atx]")
        .forEach((n) => {
          n.disabled = state !== "CONNECTED";
        });
      if (state !== "CONNECTED") {
        const controls = this._node("console-atx");
        if (controls) controls.hidden = true;
      }
    }
    start() {
      if (this.running) return;
      if (!this.video || !globalThis.RTCPeerConnection) {
        this._state(
          "ERROR",
          problem("unsupported", "Przeglądarka nie obsługuje WebRTC."),
        );
        return;
      }
      this.running = true;
      this.attempt = 0;
      this._bind();
      void this._connect();
    }
    async restart() {
      await this.stop();
      this.start();
    }
    async stop() {
      this.running = false;
      this.generation++;
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
      for (const [target, event, cb, opts] of this.listeners)
        target.removeEventListener(event, cb, opts);
      this.listeners = [];
      if (document.pointerLockElement === this.video)
        document.exitPointerLock?.();
      await this._dispose();
      this._state("DISCONNECTED");
    }
    async _dispose() {
      clearTimeout(this.negotiationTimer);
      clearTimeout(this.stableTimer);
      clearInterval(this.statsTimer);
      clearInterval(this.pingTimer);
      this.abort?.abort();
      this.abort = null;
      const pc = this.pc,
        ws = this.ws,
        channel = this.channel;
      this.pc = null;
      this.ws = null;
      this.channel = null;
      this.keys.clear();
      this.buttons = 0;
      this.mouseQueue = [];
      this.keyboardChain = Promise.resolve();
      if (ws) {
        ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
      }
      if (pc) {
        pc.ontrack = pc.onicecandidate = pc.onconnectionstatechange = null;
      }
      if (channel) {
        channel.onopen =
          channel.onmessage =
          channel.onerror =
          channel.onclose =
            null;
      }
      // Release keys/buttons before closing a healthy data channel. During a
      // network outage delivery is best effort; no success is reported for it.
      if (channel?.readyState === "open") {
        try {
          channel.send(
            JSON.stringify({
              jsonrpc: "2.0",
              id: ++this.serial,
              method: "keyboardReport",
              params: { modifier: 0, keys: [] },
            }),
          );
          channel.send(
            JSON.stringify({
              jsonrpc: "2.0",
              id: ++this.serial,
              method: "relMouseReport",
              params: { dx: 0, dy: 0, buttons: 0 },
            }),
          );
          await new Promise((resolve) => setTimeout(resolve, 60));
        } catch (_) {}
      }
      for (const item of this.pending.values()) {
        clearTimeout(item.timer);
        item.reject(problem("disconnected", "Sesja została rozłączona."));
      }
      this.pending.clear();
      channel?.close();
      pc?.close();
      ws?.close();
      this.video?.srcObject?.getTracks?.().forEach((t) => t.stop());
      if (this.video) this.video.srcObject = null;
    }
    async _connect() {
      const g = ++this.generation;
      await this._dispose();
      if (!this._current(g)) return;
      this._state(this.attempt ? "RECONNECTING" : "CONNECTING");
      this.abort = new AbortController();
      const timeout = setTimeout(() => this.abort?.abort(), 15000);
      try {
        const ticket = await this.requestSession(this.abort.signal);
        clearTimeout(timeout);
        if (!this._current(g)) return;
        if (ticket.transport !== "webrtc")
          throw problem(
            "protocol_error",
            "Backend zwrócił niezgodny typ sesji.",
          );
        const url = new URL(ticket.path, location.href);
        url.protocol = location.protocol === "https:" ? "wss:" : "ws:";
        if (url.host !== location.host)
          throw problem(
            "protocol_error",
            "Nieprawidłowy adres sesji Managera.",
          );
        const ws = new WebSocket(url, [ticket.protocol, ticket.token]);
        this.ws = ws;
        let messages = Promise.resolve();
        let began = false;
        ws.onmessage = (event) => {
          messages = messages
            .then(async () => {
              if (!this._current(g) || event.data === "pong") return;
              if (
                typeof event.data !== "string" ||
                event.data.length > 256 * 1024
              )
                throw problem(
                  "protocol_error",
                  "Nieprawidłowa odpowiedź sygnalizacji.",
                );
              const packet = JSON.parse(event.data);
              if (
                packet.type === "console" &&
                packet.state === "disconnected" &&
                packet.reason === "user"
              ) {
                this.running = false;
                this.generation++;
                clearTimeout(this.retryTimer);
                void this._dispose().then(() => this._state("DISCONNECTED"));
                return;
              }
              if (packet.type === "manager-error")
                throw problem(
                  packet.error?.code || "unreachable",
                  packet.error?.message || "Nie można połączyć się z JetKVM.",
                  packet.error?.detail || "",
                );
              if (
                packet.type === "console" &&
                packet.state === "connected" &&
                !began
              ) {
                began = true;
                await this._negotiate(g);
              } else if (packet.type === "answer") {
                if (!this.pc)
                  throw problem(
                    "protocol_error",
                    "Odpowiedź SDP otrzymano przed rozpoczęciem sesji.",
                  );
                const answer = description(packet.data);
                if (answer.type !== "answer")
                  throw problem(
                    "protocol_error",
                    "Nieprawidłowa odpowiedź SDP.",
                  );
                await this.pc.setRemoteDescription(answer);
                for (const candidate of this.remoteICE.splice(0))
                  await this.pc.addIceCandidate(candidate);
              } else if (packet.type === "new-ice-candidate") {
                if (this.pc?.remoteDescription)
                  await this.pc.addIceCandidate(packet.data);
                else (this.remoteICE ||= []).push(packet.data);
              } else if (packet.type === "device-metadata")
                this._text("console-version", packet.data?.deviceVersion || "");
            })
            .catch((error) => this._fail(error, g));
        };
        ws.onerror = () =>
          this._fail(
            problem(
              "signaling_error",
              "Przerwano połączenie z Managerem.",
              "WebSocket transport failed",
            ),
            g,
          );
        ws.onclose = (event) =>
          this._fail(
            problem(
              "signaling_closed",
              "Połączenie z JetKVM zostało zamknięte.",
              `WebSocket close ${event.code}`,
            ),
            g,
          );
        this.negotiationTimer = setTimeout(
          () =>
            this._fail(
              problem(
                "timeout",
                "Nie udało się zestawić obrazu WebRTC. Sprawdź połączenie LAN przeglądarki z JetKVM.",
                "WebRTC negotiation timeout",
              ),
              g,
            ),
          30000,
        );
        this.pingTimer = setInterval(() => {
          if (this.ws?.readyState === 1) this.ws.send("ping");
        }, 15000);
      } catch (error) {
        clearTimeout(timeout);
        this._fail(error, g);
      }
    }
    async _negotiate(g) {
      if (!this._current(g)) return;
      const pc = new RTCPeerConnection({
        iceServers: [],
        bundlePolicy: "max-bundle",
      });
      this.pc = pc;
      this.remoteICE = [];
      const localICE = [];
      let offered = false;
      const transceiver = pc.addTransceiver("video", { direction: "recvonly" });
      const h264 = globalThis.RTCRtpReceiver?.getCapabilities?.(
        "video",
      )?.codecs?.filter((c) => c.mimeType.toLowerCase() === "video/h264");
      if (h264?.length && transceiver.setCodecPreferences)
        transceiver.setCodecPreferences(h264);
      pc.onicecandidate = (event) => {
        if (!this._current(g) || !event.candidate) return;
        const packet = {
          type: "new-ice-candidate",
          data: event.candidate.toJSON(),
        };
        if (offered) this._signal(packet);
        else localICE.push(packet);
      };
      pc.ontrack = (event) => {
        if (!this._current(g)) return;
        this.video.srcObject =
          event.streams[0] || new MediaStream([event.track]);
        this.video
          .play()
          .catch(() =>
            this._text(
              "console-message",
              "Kliknij obraz, aby rozpocząć odtwarzanie.",
            ),
          );
      };
      pc.onconnectionstatechange = () => {
        if (!this._current(g)) return;
        this._text(
          "console-webrtc",
          `WebRTC: ${pc.connectionState} · ICE: ${pc.iceConnectionState}`,
        );
        if (pc.connectionState === "connected") this._connected(g);
        if (["failed", "disconnected", "closed"].includes(pc.connectionState))
          this._fail(
            problem(
              "ice_failed",
              "Utracono połączenie obrazu. Sprawdź sieć LAN i zaporę.",
              `WebRTC ${pc.connectionState}; ICE ${pc.iceConnectionState}`,
            ),
            g,
          );
      };
      const channel = pc.createDataChannel("rpc", { ordered: true });
      this.channel = channel;
      channel.onmessage = (event) => this._rpcMessage(event.data, g);
      channel.onopen = () => {
        this._connected(g);
        void this._probeCapabilities(g);
      };
      channel.onerror = () =>
        this._fail(
          problem(
            "control_error",
            "Kanał klawiatury i myszy został przerwany.",
          ),
          g,
        );
      channel.onclose = () =>
        this._fail(
          problem("control_closed", "Kanał sterowania został zamknięty."),
          g,
        );
      const offer = await pc.createOffer();
      if (!this._current(g)) return;
      await pc.setLocalDescription(offer);
      if (!this._current(g)) return;
      this._signal({
        type: "offer",
        data: { sd: envelope(pc.localDescription) },
      });
      offered = true;
      for (const packet of localICE) this._signal(packet);
    }
    _signal(packet) {
      if (this.ws?.readyState !== 1)
        throw problem("disconnected", "Sygnalizacja jest rozłączona.");
      this.ws.send(JSON.stringify(packet));
    }
    _connected(g) {
      if (
        !this._current(g) ||
        this.pc?.connectionState !== "connected" ||
        this.channel?.readyState !== "open"
      )
        return;
      clearTimeout(this.negotiationTimer);
      this._state("CONNECTED");
      this._signal({ type: "manager-state", state: "connected" });
      clearTimeout(this.stableTimer);
      this.stableTimer = setTimeout(() => {
        if (this._current(g)) this.attempt = 0;
      }, 30000);
      clearInterval(this.statsTimer);
      this.statsTimer = setInterval(() => void this._stats(g), 1000);
      void this._probeCapabilities(g);
    }
    _fail(error, g) {
      if (!this._current(g)) return;
      this.generation++; // Retire all callbacks from this negotiation immediately.
      if (!error?.code)
        error = problem(
          error?.name === "AbortError" ? "timeout" : "connection_error",
          "Nie można zestawić sesji JetKVM.",
          error?.name || "Connection error",
        );
      const retry =
        !NON_RETRYABLE.has(error.code) && this.attempt < RETRY_DELAYS.length;
      if (retry) {
        const delay = RETRY_DELAYS[this.attempt++];
        this._state("RECONNECTING", error);
        void this._dispose();
        this.retryTimer = setTimeout(() => {
          this.retryTimer = null;
          if (this.running) void this._connect();
        }, delay);
      } else {
        this._state("ERROR", error);
        void this._dispose();
      }
    }
    rpc(method, params = {}) {
      const channel = this.channel;
      if (channel?.readyState !== "open")
        return Promise.reject(
          problem("disconnected", "Kanał sterowania jest rozłączony."),
        );
      if (this.pending.size >= 64)
        return Promise.reject(
          problem("busy", "Kanał sterowania jest przeciążony."),
        );
      const id = ++this.serial;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          this.pending.delete(id);
          reject(
            problem(
              "timeout",
              "JetKVM nie potwierdził operacji.",
              `RPC ${method} timeout`,
            ),
          );
        }, 4000);
        this.pending.set(id, { resolve, reject, timer, method });
        try {
          channel.send(JSON.stringify({ jsonrpc: "2.0", id, method, params }));
        } catch (_) {
          clearTimeout(timer);
          this.pending.delete(id);
          reject(problem("disconnected", "Nie udało się wysłać operacji."));
        }
      });
    }
    _rpcMessage(raw, g) {
      if (
        !this._current(g) ||
        typeof raw !== "string" ||
        raw.length > 256 * 1024
      )
        return;
      let message;
      try {
        message = JSON.parse(raw);
      } catch (_) {
        return;
      }
      if (!message || typeof message !== "object") return;
      const item = this.pending.get(message.id);
      if (item) {
        clearTimeout(item.timer);
        this.pending.delete(message.id);
        if (message.error)
          item.reject(
            problem(
              "rpc_error",
              "JetKVM odrzucił operację.",
              `${item.method}: RPC code ${Number(message.error.code) || "unknown"}`,
            ),
          );
        else item.resolve(message.result);
        return;
      }
      if (message.method === "activeExtension") void this._probeCapabilities(g);
    }
    async _probeCapabilities(g) {
      if (!this._current(g) || this.channel?.readyState !== "open") return;
      try {
        const extension = await this.rpc("getActiveExtension");
        if (this._current(g)) {
          const controls = this._node("console-atx");
          if (controls)
            controls.hidden =
              extension !== "atx-power" || this.state !== "CONNECTED";
        }
      } catch (_) {
        /* Missing extension RPC means ATX stays hidden, not false success. */
      }
    }
    async _stats(g) {
      const pc = this.pc;
      if (!pc) return;
      try {
        const stats = await pc.getStats();
        if (!this._current(g)) return;
        let fps, latency;
        stats.forEach((s) => {
          if (s.type === "inbound-rtp" && s.kind === "video") {
            fps = s.framesPerSecond;
            if (
              fps === undefined &&
              this.previousFrame &&
              s.timestamp > this.previousFrame.time
            )
              fps =
                ((s.framesDecoded - this.previousFrame.frames) * 1000) /
                (s.timestamp - this.previousFrame.time);
            this.previousFrame = { time: s.timestamp, frames: s.framesDecoded };
          }
          if (s.type === "transport" && s.selectedCandidatePairId) {
            const pair = stats.get(s.selectedCandidatePairId);
            if (Number.isFinite(pair?.currentRoundTripTime))
              latency = pair.currentRoundTripTime * 1000;
          }
        });
        const width = this.video.videoWidth,
          height = this.video.videoHeight;
        this._text(
          "console-metrics",
          [
            width && height ? `${width} × ${height}` : "Oczekiwanie na obraz",
            Number.isFinite(fps) ? `${fps.toFixed(1)} FPS` : null,
            Number.isFinite(latency) ? `RTT ${latency.toFixed(1)} ms` : null,
          ]
            .filter(Boolean)
            .join(" · "),
        );
        this._scale();
      } catch (_) {
        /* Peer closed while getStats was pending. */
      }
    }
    _controlFailure(error) {
      if (this.running)
        this._text(
          "console-message",
          error.message || "Operacja sterowania nie została potwierdzona.",
        );
    }
    _keyboard() {
      const report = { modifier: 0, keys: [] };
      for (const code of this.keys) {
        if (MODIFIERS[code]) report.modifier |= MODIFIERS[code];
        else if (KEY_CODES[code] && report.keys.length < 6)
          report.keys.push(KEY_CODES[code]);
      }
      const g = this.generation;
      this.keyboardChain = this.keyboardChain
        .catch(() => {})
        .then(() => {
          if (this._current(g)) return this.rpc("keyboardReport", report);
        });
      this.keyboardChain.catch((e) => this._controlFailure(e));
      return this.keyboardChain;
    }
    sendKeyboard(code, pressed) {
      if (!MODIFIERS[code] && !KEY_CODES[code])
        return Promise.reject(
          problem("unsupported", "Nieobsługiwany klawisz."),
        );
      pressed ? this.keys.add(code) : this.keys.delete(code);
      return this._keyboard();
    }
    async _chord(codes) {
      if (this.state !== "CONNECTED") return;
      try {
        this.keys.clear();
        for (const code of codes) this.keys.add(code);
        await this._keyboard();
      } finally {
        this.keys.clear();
        await this._keyboard();
      }
    }
    _release() {
      this.keys.clear();
      if (this.channel?.readyState === "open") void this._keyboard();
      this.buttons = 0;
      this._mouseReport(
        this.relative ? { dx: 0, dy: 0 } : this.lastPosition,
        false,
      );
    }
    sendMouse(method, params) {
      return this.rpc(method, params);
    }
    _mouseReport(position, movement) {
      if (this.channel?.readyState !== "open") return;
      const item = {
        method: this.relative ? "relMouseReport" : "absMouseReport",
        params: { ...position, buttons: this.buttons },
        movement,
      };
      const last = this.mouseQueue.at(-1);
      if (movement && last?.movement && last.method === item.method) {
        if (this.relative) {
          last.params.dx = clamp(last.params.dx + position.dx, -127, 127);
          last.params.dy = clamp(last.params.dy + position.dy, -127, 127);
          last.params.buttons = this.buttons;
        } else this.mouseQueue[this.mouseQueue.length - 1] = item;
      } else if (this.mouseQueue.length < 128) this.mouseQueue.push(item);
      void this._drainMouse(this.generation);
    }
    async _drainMouse(g) {
      if (this.mouseSending) return;
      this.mouseSending = true;
      try {
        while (this._current(g) && this.mouseQueue.length) {
          const item = this.mouseQueue.shift();
          await this.sendMouse(item.method, item.params);
        }
      } catch (e) {
        if (this._current(g)) this._controlFailure(e);
      } finally {
        this.mouseSending = false;
        if (this.mouseQueue.length && this.running)
          void this._drainMouse(this.generation);
      }
    }
    _position(event) {
      if (this.relative)
        return {
          dx: clamp(event.movementX || 0, -127, 127),
          dy: clamp(event.movementY || 0, -127, 127),
        };
      const r = this.video.getBoundingClientRect();
      const ratio =
        (this.video.videoWidth || 16) / (this.video.videoHeight || 9);
      let width = r.width,
        height = width / ratio;
      if (height > r.height) {
        height = r.height;
        width = height * ratio;
      }
      if (!width || !height) return { x: 0, y: 0 };
      return {
        x: clamp(
          ((event.clientX - r.left - (r.width - width) / 2) / width) * 32767,
          0,
          32767,
        ),
        y: clamp(
          ((event.clientY - r.top - (r.height - height) / 2) / height) * 32767,
          0,
          32767,
        ),
      };
    }
    async sendATXCommand(action) {
      if (!["power-short", "power-long", "reset"].includes(action))
        throw problem("unsupported", "Nieobsługiwana akcja ATX.");
      await this.rpc("setATXPowerAction", { action });
    }
    _scale() {
      if (!this.video) return;
      this.video.style.width =
        this.scale === "fit" ? "100%" : `${this.video.videoWidth || 1280}px`;
      this.video.style.maxHeight =
        this.scale === "fit" ? "calc(100dvh - 240px)" : "none";
      this.video.style.maxWidth = this.scale === "fit" ? "100%" : "none";
    }
    _bind() {
      this.stage.tabIndex = 0;
      this._listen(this.stage, "keydown", (e) => {
        if (
          !this.keyboardEnabled ||
          this.state !== "CONNECTED" ||
          (!MODIFIERS[e.code] && !KEY_CODES[e.code])
        )
          return;
        e.preventDefault();
        e.stopPropagation();
        if (!e.repeat) void this.sendKeyboard(e.code, true);
      });
      this._listen(this.stage, "keyup", (e) => {
        if (!this.keyboardEnabled || this.state !== "CONNECTED") return;
        e.preventDefault();
        e.stopPropagation();
        void this.sendKeyboard(e.code, false);
      });
      this._listen(this.stage, "blur", () => this._release());
      this._listen(window, "blur", () => this._release());
      this._listen(document, "visibilitychange", () => {
        if (document.hidden) this._release();
      });
      this._listen(this.video, "mousedown", (e) => {
        if (!this.mouseEnabled || this.state !== "CONNECTED") return;
        e.preventDefault();
        this.stage.focus();
        void this.video.play().catch(() => {});
        if (this.relative && document.pointerLockElement !== this.video) {
          try {
            const locked = this.video.requestPointerLock?.();
            locked?.catch?.(() =>
              this._text(
                "console-message",
                "Przeglądarka odmówiła przechwycenia myszy.",
              ),
            );
          } catch (_) {}
          return;
        }
        this.buttons = e.buttons & 31;
        this.lastPosition = this._position(e);
        this._mouseReport(
          this.relative ? { dx: 0, dy: 0 } : this.lastPosition,
          false,
        );
      });
      this._listen(window, "mouseup", (e) => {
        if (!this.buttons) return;
        this.buttons = e.buttons & 31;
        this._mouseReport(
          this.relative ? { dx: 0, dy: 0 } : this._position(e),
          false,
        );
      });
      this._listen(this.video, "mousemove", (e) => {
        if (
          !this.mouseEnabled ||
          this.state !== "CONNECTED" ||
          (this.relative && document.pointerLockElement !== this.video)
        )
          return;
        this.lastPosition = this._position(e);
        this._mouseReport(this.lastPosition, true);
      });
      this._listen(
        this.video,
        "wheel",
        (e) => {
          if (!this.mouseEnabled || this.state !== "CONNECTED") return;
          e.preventDefault();
          const divisor = e.deltaMode === 0 ? 40 : 1;
          this.rpc("wheelReport", {
            wheelY: clamp(-e.deltaY / divisor, -127, 127),
            wheelX: clamp(e.deltaX / divisor, -127, 127),
          }).catch((err) => this._controlFailure(err));
        },
        { passive: false },
      );
      this._listen(this.video, "contextmenu", (e) => e.preventDefault());
      this._listen(document, "pointerlockchange", () => {
        if (document.pointerLockElement !== this.video) this._release();
      });
      this._listen(this._node("console-keyboard"), "change", (e) => {
        this.keyboardEnabled = e.target.checked;
        if (!this.keyboardEnabled) this._release();
      });
      this._listen(this._node("console-mouse"), "change", (e) => {
        this.mouseEnabled = e.target.checked;
        if (!this.mouseEnabled) this._release();
      });
      this._listen(this._node("console-mouse-mode"), "change", (e) => {
        this._release();
        this.relative = e.target.value === "relative";
        if (!this.relative && document.pointerLockElement === this.video)
          document.exitPointerLock?.();
      });
      this._listen(this._node("console-scale"), "change", (e) => {
        this.scale = e.target.value;
        this._scale();
      });
      this._listen(this._node("console-fullscreen"), "click", () => {
        const fn = document.fullscreenElement
          ? document.exitFullscreen?.bind(document)
          : this._node("console-shell")?.requestFullscreen?.bind(
              this._node("console-shell"),
            );
        Promise.resolve(fn?.()).catch(() =>
          this._text(
            "console-message",
            "Nie udało się włączyć pełnego ekranu.",
          ),
        );
      });
      this._listen(
        this._node("console-reconnect"),
        "click",
        () => void this.restart(),
      );
      this._listen(this._node("console-disconnect"), "click", () => {
        this.running = false;
        this.generation++;
        clearTimeout(this.retryTimer);
        this.retryTimer = null;
        void this._dispose().then(() => this._state("DISCONNECTED"));
      });
      this._listen(this._node("console-cad"), "click", () =>
        this._chord(["ControlLeft", "AltLeft", "Delete"]).catch((e) =>
          this._controlFailure(e),
        ),
      );
      this.root
        .querySelectorAll("[data-console-key]")
        .forEach((n) =>
          this._listen(n, "click", () =>
            this._chord([n.dataset.consoleKey]).catch((e) =>
              this._controlFailure(e),
            ),
          ),
        );
      this.root.querySelectorAll("[data-console-atx]").forEach((n) =>
        this._listen(n, "click", async () => {
          if (!confirm(`Wykonać ${n.textContent}?`)) return;
          try {
            await this.sendATXCommand(n.dataset.consoleAtx);
            this._text(
              "console-message",
              "JetKVM potwierdził wykonanie komendy ATX.",
            );
          } catch (e) {
            this._controlFailure(e);
          }
        }),
      );
      this._listen(this._node("console-wol"), "click", () =>
        this.wakeOnLAN?.().catch((e) => this._controlFailure(e)),
      );
      this._scale();
      this._state("CONNECTING");
    }
  }
  globalThis.JetKVMConsoleController = JetKVMConsoleController;
  if (typeof module !== "undefined")
    module.exports = {
      JetKVMConsoleController,
      KEY_CODES,
      MODIFIERS,
      RETRY_DELAYS,
      envelope,
      description,
    };
})();
