/* Shared device setup, details and editing. Credentials exist only in the form
 * while submitting a test/save, never in URL, browser storage or device state. */
(() => {
  "use strict";
  const dialog = document.getElementById("device-setup-dialog");
  const form = document.getElementById("device-setup-form");
  if (!dialog || !form) return;
  const field = (id) => document.getElementById(`device-${id}`);
  const providers = {
    nanokvm: { label: "NanoKVM", username: true, staged: true },
    jetkvm: { label: "JetKVM", username: false, staged: false },
  };
  let entryId = "",
    busy = false,
    verified = false,
    reachable = false,
    unchanged = true;
  const profile = () => providers[field("provider").value];
  const notice = (text, bad = false) => {
    const n = document.getElementById("notice");
    n.textContent = text;
    n.classList.toggle("bad", bad);
    n.classList.remove("hidden");
  };
  async function manage(operation, payload = {}) {
    const abort = new AbortController();
    const timeout = setTimeout(() => abort.abort(), 40000);
    try {
      const response = await fetch("api/rpc", {
        method: "POST",
        signal: abort.signal,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-NanoKVM-Request": "1",
        },
        body: JSON.stringify({
          type: "nanokvm_rest/panel/kvm/manage",
          operation,
          payload,
        }),
      });
      const data = await response.json();
      const result = data.result;
      if (!response.ok || data.ok === false || result?.ok === false) {
        const info = result?.error || data.error;
        throw Object.assign(
          new Error(
            typeof info === "object"
              ? info.message
              : info || `HTTP ${response.status}`,
          ),
          typeof info === "object" ? info : { code: `http_${response.status}` },
        );
      }
      if (!result || result.ok !== true)
        throw new Error(
          "Nieprawidłowa odpowiedź integracji. Zaktualizuj NanoKVM REST i uruchom ponownie Home Assistant.",
        );
      return result;
    } catch (error) {
      if (error.name === "AbortError")
        throw Object.assign(
          new Error("Przekroczono czas oczekiwania na integrację."),
          { code: "timeout" },
        );
      if (error instanceof TypeError)
        throw Object.assign(
          new Error(
            "Nie można połączyć się z Managerem. Sprawdź połączenie z Home Assistant.",
          ),
          { code: "unreachable" },
        );
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }
  function showError(error) {
    field("error").hidden = false;
    field("error-message").textContent = error.message;
    field("error-detail").textContent =
      `${error.code || "connection_error"}${error.detail ? `: ${error.detail}` : ""}`;
  }
  function step(name, status, text) {
    const node = document.querySelector(`[data-setup-step="${name}"]`);
    node.className = `setup-step ${status}`;
    node.querySelector(".setup-step-text").textContent = text;
  }
  function buttons() {
    field("test-connection").disabled = busy;
    field("test-auth").disabled = busy || !reachable;
    field("create").disabled = busy || (!verified && !(entryId && unchanged));
    field("setup-close").disabled = busy;
    form.querySelectorAll("input,select").forEach((n) => {
      n.disabled = busy || (n === field("provider") && Boolean(entryId));
    });
  }
  function resetValidation() {
    verified = false;
    reachable = false;
    unchanged = false;
    field("error").hidden = true;
    field("identity").textContent = "";
    step(
      "connection",
      "pending",
      profile().staged
        ? "Sprawdź połączenie z urządzeniem."
        : "Test sprawdzi JetKVM, konfigurację i lokalne uwierzytelnienie.",
    );
    step("auth", "pending", "Wykonaj test lokalnego uwierzytelnienia.");
    step(
      "create",
      "pending",
      "Zapis będzie możliwy po poprawnym teście połączenia.",
    );
    buttons();
  }
  function applyProvider() {
    const p = profile();
    field("username-group").hidden = !p.username;
    field("fingerprint").closest(".field").hidden = p.username;
    document.querySelector('[data-setup-step="auth"]').hidden = !p.staged;
    field("test-auth").hidden = !p.staged;
    field("test-connection").textContent = p.staged
      ? "1. Test połączenia"
      : "Testuj połączenie";
    field("password-label").textContent = p.username
      ? "Hasło"
      : "Hasło lokalne (opcjonalne)";
    field("create").textContent = entryId
      ? "Zapisz zmiany"
      : "Dodaj urządzenie";
    field("setup-title").textContent = entryId
      ? `Edytuj ${p.label}`
      : "Dodaj urządzenie KVM";
    field("password-help").textContent = entryId
      ? "Pozostaw puste, aby zachować dotychczasowe hasło. Zaznacz „Usuń hasło”, gdy wyłączono ochronę na urządzeniu."
      : p.username
        ? "Dane NanoKVM są szyfrowane po stronie Home Assistant."
        : "Pozostaw puste, jeśli JetKVM pracuje w trybie bez lokalnego hasła.";
    field("clear-password-group").hidden = !entryId;
  }
  function payload() {
    const value = {
      provider: field("provider").value,
      title: field("name").value.trim(),
      host: field("url").value.trim(),
      protocol: field("protocol").value,
      port: Number(field("port").value),
      verify_ssl: !field("selfsigned").checked,
      certificate_sha256: field("fingerprint").value.trim(),
      lan_networks: field("networks").value.trim(),
    };
    if (entryId) value.entry_id = entryId;
    if (profile().username) value.username = field("username").value.trim();
    if (!entryId || field("password").value || field("clear-password").checked)
      value.password = field("clear-password").checked
        ? ""
        : field("password").value;
    return value;
  }
  function clearForm() {
    form.reset();
    entryId = "";
    verified = reachable = false;
    unchanged = true;
    busy = false;
    field("provider").disabled = false;
    field("error").hidden = true;
    field("identity").textContent = "";
    field("protocol").value = "http";
    field("port").value = "80";
    field("username").value = "admin";
    applyProvider();
    resetValidation();
  }
  function openAdd(candidate = {}) {
    clearForm();
    field("provider").value = candidate.provider || "nanokvm";
    field("url").value = candidate.host || "";
    field("name").value = candidate.title || "";
    applyProvider();
    resetValidation();
    dialog.showModal();
    field("url").focus();
  }
  async function openEdit(id) {
    try {
      const data = await manage("get", { entry_id: id });
      clearForm();
      entryId = id;
      field("provider").value = data.provider;
      field("name").value = data.title;
      field("url").value = data.host;
      field("protocol").value = data.protocol;
      field("port").value = String(data.port);
      field("username").value = data.username || "admin";
      field("selfsigned").checked = data.verify_ssl === false;
      field("fingerprint").value = data.certificate_sha256 || "";
      field("networks").value = (data.lan_networks || []).join(", ");
      applyProvider();
      resetValidation();
      unchanged = true;
      buttons();
      dialog.showModal();
    } catch (error) {
      notice(error.message, true);
    }
  }
  function change() {
    if (busy) return;
    resetValidation();
  }
  form.querySelectorAll("input,select").forEach((n) => {
    if (n !== field("name")) n.addEventListener("input", change);
  });
  field("provider").addEventListener("change", () => {
    applyProvider();
    resetValidation();
  });
  field("url").addEventListener("change", () => {
    try {
      const value = field("url").value;
      if (/^https?:\/\//i.test(value)) {
        const url = new URL(value);
        field("protocol").value = url.protocol.slice(0, -1);
        field("port").value =
          url.port || (url.protocol === "https:" ? "443" : "80");
        resetValidation();
      }
    } catch (_) {}
  });
  field("protocol").addEventListener("change", () => {
    if (["80", "443", ""].includes(field("port").value))
      field("port").value = field("protocol").value === "https" ? "443" : "80";
    resetValidation();
  });
  field("selfsigned").addEventListener("change", () => {
    field("tls-warning").hidden = !field("selfsigned").checked;
    resetValidation();
  });
  field("test-connection").addEventListener("click", async () => {
    if (!field("url").value.trim()) {
      showError(new Error("Podaj adres IP lub hostname urządzenia."));
      return;
    }
    field("error").hidden = true;
    busy = true;
    verified = false;
    buttons();
    step("connection", "working", "Łączenie z urządzeniem…");
    try {
      const value = payload();
      const operation = profile().staged ? "probe" : "test";
      const result = await manage(operation, value);
      reachable = true;
      verified = !profile().staged;
      step(
        "connection",
        "success",
        `${profile().label}: połączono z ${result.base_url || value.host}.`,
      );
      field("identity").textContent = [
        result.device_id,
        result.auth_mode,
        Number.isFinite(result.latency_ms) ? `${result.latency_ms} ms` : null,
      ]
        .filter(Boolean)
        .join(" · ");
      if (verified)
        step(
          "create",
          "pending",
          "Urządzenie wykryto i zweryfikowano. Możesz je zapisać.",
        );
    } catch (error) {
      reachable = false;
      showError(error);
      step("connection", "error", error.message);
    } finally {
      busy = false;
      buttons();
    }
  });
  field("test-auth").addEventListener("click", async () => {
    busy = true;
    verified = false;
    buttons();
    step("auth", "working", "Testowanie danych dostępowych…");
    try {
      const result = await manage("test", payload());
      verified = true;
      step("auth", "success", "Urządzenie potwierdziło dostęp.");
      field("identity").textContent = result.device_id || "";
      step("create", "pending", "Urządzenie jest gotowe do zapisania.");
    } catch (error) {
      showError(error);
      step("auth", "error", error.message);
    } finally {
      busy = false;
      buttons();
    }
  });
  field("create").addEventListener("click", async () => {
    if (!field("name").value.trim()) {
      showError(new Error("Podaj nazwę urządzenia."));
      return;
    }
    busy = true;
    buttons();
    step("create", "working", "Weryfikowanie i zapisywanie konfiguracji…");
    try {
      const value =
        entryId && unchanged
          ? { entry_id: entryId, title: field("name").value.trim() }
          : payload();
      const result = await manage("save", value);
      field("password").value = "";
      step("create", "success", `Zapisano ${result.title}.`);
      dialog.close();
      notice(`Zapisano ${result.title}.`);
      window.location.reload();
    } catch (error) {
      showError(error);
      step("create", "error", error.message);
    } finally {
      busy = false;
      buttons();
    }
  });
  document
    .getElementById("add-device")
    .addEventListener("click", () => openAdd());
  field("setup-close").addEventListener("click", () => {
    if (!busy) dialog.close();
  });
  dialog.addEventListener("cancel", (e) => {
    if (busy) e.preventDefault();
  });
  dialog.addEventListener("close", () => {
    field("password").value = "";
    field("clear-password").checked = false;
  });
  form.addEventListener("submit", (e) => e.preventDefault());

  function panel(title) {
    const d = document.createElement("dialog");
    d.className = "device-setup-dialog";
    const card = document.createElement("div");
    card.className = "device-setup-card";
    const h = document.createElement("h2");
    h.textContent = title;
    card.append(h);
    d.append(card);
    const close = document.createElement("button");
    close.type = "button";
    close.className = "btn small";
    close.textContent = "Zamknij";
    close.addEventListener("click", () => d.close());
    card.append(close);
    d.addEventListener("close", () => d.remove());
    document.body.append(d);
    return { dialog: d, card };
  }
  async function wakeOnLAN(id) {
    const mac = prompt("MAC komputera do Wake-on-LAN (np. AA:BB:CC:DD:EE:FF):");
    if (mac === null) return;
    await manage("wol", { entry_id: id, mac });
    notice("JetKVM/NanoKVM potwierdził wysłanie pakietu Wake-on-LAN.");
  }
  async function openDetails(id) {
    try {
      const data = await manage("get", { entry_id: id });
      const { dialog: d, card } = panel(data.title);
      const dl = document.createElement("dl");
      dl.className = "kvm-details";
      const fields = [
        ["Typ", providers[data.provider]?.label],
        ["Adres", data.base_url],
        ["Status", data.available ? "ONLINE" : "OFFLINE"],
        ["Model", data.hardware],
        ["Device ID", data.device_id || data.device_key],
        ["Firmware", data.firmware_version || data.application_version],
        ["MAC", data.mac],
        ["Uptime", data.uptime],
        ["Tryb uwierzytelnienia", data.auth_mode],
        ["Ostatnio widziany", data.last_seen_at],
        [
          "Latency HTTP",
          Number.isFinite(data.last_latency_ms)
            ? `${data.last_latency_ms} ms`
            : undefined,
        ],
      ];
      for (const [label, value] of fields) {
        if (value === undefined || value === null || value === "") continue;
        const dt = document.createElement("dt"),
          dd = document.createElement("dd");
        dt.textContent = label;
        dd.textContent = String(value);
        dl.append(dt, dd);
      }
      card.append(dl);
      const output = document.createElement("p");
      output.setAttribute("role", "status");
      card.append(output);
      if (data.last_error) {
        const details = document.createElement("details"),
          summary = document.createElement("summary"),
          pre = document.createElement("pre");
        summary.textContent = data.last_error.message || "Szczegóły błędu";
        pre.textContent = `${data.last_error.code || ""}: ${data.last_error.detail || ""}`;
        details.append(summary, pre);
        card.append(details);
      }
      const actions = document.createElement("div");
      actions.className = "actions";
      card.append(actions);
      const button = (text, fn, danger = false) => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = `btn ${danger ? "danger" : ""}`;
        b.textContent = text;
        b.onclick = async () => {
          b.disabled = true;
          try {
            await fn();
          } catch (error) {
            output.textContent = error.message;
          } finally {
            b.disabled = false;
          }
        };
        actions.append(b);
      };
      button("Testuj połączenie", async () => {
        const result = await manage("test", { entry_id: id });
        output.textContent = `Połączono · ${result.latency_ms} ms`;
      });
      button("Edytuj", () => {
        d.close();
        return openEdit(id);
      });
      button("Rozłącz sesje", async () => {
        const result = await manage("disconnect", { entry_id: id });
        output.textContent = `Zamknięte sesje: ${result.closed_sessions}`;
      });
      if (data.capabilities?.wol) button("Wake-on-LAN", () => wakeOnLAN(id));
      button(
        "Usuń",
        async () => {
          if (!confirm(`Usunąć ${data.title} z Managera?`)) return;
          await manage("delete", { entry_id: id });
          d.close();
          window.location.reload();
        },
        true,
      );
      d.showModal();
    } catch (error) {
      notice(error.message, true);
    }
  }
  document
    .getElementById("scan-devices")
    ?.addEventListener("click", async (event) => {
      event.target.disabled = true;
      try {
        const result = await manage("discover");
        const { dialog: d, card } = panel("Wykryte urządzenia LAN");
        const explanation = document.createElement("p");
        explanation.textContent =
          result.note || "Odczytano tablicę sąsiadów i sprawdzono lokalne API.";
        card.append(explanation);
        for (const device of result.devices || []) {
          const row = document.createElement("div");
          row.className = "actions";
          const label = document.createElement("span");
          label.textContent = `${device.host} · ${providers[device.provider]?.label}`;
          const add = document.createElement("button");
          add.className = "btn";
          add.textContent = "Dodaj";
          add.onclick = () => {
            d.close();
            openAdd(device);
          };
          row.append(label, add);
          card.append(row);
        }
        if (!result.devices?.length) {
          const empty = document.createElement("p");
          empty.textContent =
            "Brak potwierdzonych urządzeń w tablicy sąsiadów. Odczytaj adres z routera i dodaj urządzenie ręcznie.";
          card.append(empty);
        }
        d.showModal();
      } catch (error) {
        notice(error.message, true);
      } finally {
        event.target.disabled = false;
      }
    });
  window.KVMDeviceManager = {
    openDetails,
    openEdit,
    openAdd,
    wakeOnLAN,
    manage,
  };
})();
