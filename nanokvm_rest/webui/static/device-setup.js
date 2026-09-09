(() => {
  const dialog = document.getElementById('device-setup-dialog');
  const openButton = document.getElementById('add-device');
  const closeButton = document.getElementById('device-setup-close');
  const form = document.getElementById('device-setup-form');
  const urlInput = document.getElementById('device-url');
  const verifyInput = document.getElementById('device-verify-ssl');
  const usernameInput = document.getElementById('device-username');
  const passwordInput = document.getElementById('device-password');
  const connectionButton = document.getElementById('device-test-connection');
  const authButton = document.getElementById('device-test-auth');
  const createButton = document.getElementById('device-create');
  const identity = document.getElementById('device-identity');

  if (!dialog || !openButton || !form) return;

  let connectionOk = false;
  let authOk = false;
  let busy = false;

  const step = (name) => document.querySelector(`[data-setup-step="${name}"]`);

  function setStep(name, state, text) {
    const node = step(name);
    if (!node) return;
    node.classList.remove('pending', 'working', 'success', 'error');
    node.classList.add(state);
    const textNode = node.querySelector('.setup-step-text');
    if (textNode) textNode.textContent = text;
  }

  function setBusy(value) {
    busy = value;
    connectionButton.disabled = busy;
    authButton.disabled = busy || !connectionOk;
    createButton.disabled = busy || !authOk;
    closeButton.disabled = busy;
  }

  function resetAuth() {
    authOk = false;
    setStep('auth', 'pending', 'Najpierw wykonaj test połączenia, potem sprawdź login i hasło.');
    setStep('create', 'pending', 'Urządzenie zostanie dodane dopiero po poprawnej autentykacji.');
    identity.textContent = '';
    authButton.disabled = busy || !connectionOk;
    createButton.disabled = true;
  }

  function resetConnection() {
    connectionOk = false;
    setStep('connection', 'pending', 'Sprawdzimy, czy host odpowiada po HTTP lub HTTPS. Dane logowania nie są wysyłane.');
    resetAuth();
  }

  function resetForm() {
    form.reset();
    usernameInput.value = 'admin';
    verifyInput.checked = true;
    passwordInput.value = '';
    resetConnection();
    setBusy(false);
  }

  function credentialsPayload() {
    return {
      base_url: urlInput.value.trim(),
      verify_ssl: verifyInput.checked,
      username: usernameInput.value.trim(),
      password: passwordInput.value,
    };
  }

  async function rpc(type, payload) {
    const response = await fetch('api/rpc', {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-NanoKVM-Request': '1',
      },
      body: JSON.stringify({type, ...payload}),
    });
    const data = await response.json().catch(() => ({ok: false, error: `HTTP ${response.status}`}));
    if (!response.ok || data.ok === false) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data.result || {};
  }

  function globalNotice(message, bad = false) {
    const notice = document.getElementById('notice');
    if (!notice) return;
    notice.textContent = message;
    notice.classList.toggle('bad', bad);
    notice.classList.remove('hidden');
    window.setTimeout(() => notice.classList.add('hidden'), 6000);
  }

  openButton.addEventListener('click', () => {
    resetForm();
    dialog.showModal();
    window.setTimeout(() => urlInput.focus(), 0);
  });

  closeButton.addEventListener('click', () => {
    if (!busy) dialog.close();
  });

  dialog.addEventListener('close', () => {
    passwordInput.value = '';
  });

  dialog.addEventListener('cancel', (event) => {
    if (busy) event.preventDefault();
  });

  urlInput.addEventListener('input', resetConnection);
  verifyInput.addEventListener('change', resetConnection);
  usernameInput.addEventListener('input', resetAuth);
  passwordInput.addEventListener('input', resetAuth);

  connectionButton.addEventListener('click', async () => {
    const baseUrl = urlInput.value.trim();
    if (!baseUrl) {
      setStep('connection', 'error', 'Podaj adres IP, nazwę hosta albo pełny URL NanoKVM.');
      urlInput.focus();
      return;
    }

    resetConnection();
    setStep('connection', 'working', 'Testuję połączenie z urządzeniem…');
    setBusy(true);
    try {
      const result = await rpc('nanokvm_rest/panel/device/test_connection', {
        base_url: baseUrl,
        verify_ssl: verifyInput.checked,
      });
      if (result.base_url) urlInput.value = result.base_url;
      connectionOk = true;
      setStep(
        'connection',
        'success',
        `Połączenie działa: ${result.base_url || baseUrl} · HTTP ${result.http_status ?? 'OK'}.`,
      );
      setStep('auth', 'pending', 'Połączenie działa. Teraz sprawdź login i hasło.');
    } catch (error) {
      setStep('connection', 'error', `Test połączenia nieudany: ${error.message}`);
    } finally {
      setBusy(false);
    }
  });

  authButton.addEventListener('click', async () => {
    if (!connectionOk) return;
    if (!usernameInput.value.trim() || !passwordInput.value) {
      setStep('auth', 'error', 'Podaj nazwę użytkownika i hasło.');
      return;
    }

    authOk = false;
    createButton.disabled = true;
    setStep('auth', 'working', 'Loguję się do NanoKVM i odczytuję identyfikator urządzenia…');
    setBusy(true);
    try {
      const result = await rpc('nanokvm_rest/panel/device/test_authentication', credentialsPayload());
      if (result.base_url) urlInput.value = result.base_url;
      identity.textContent = result.title
        ? `Wykryto: ${result.title}${result.device_key ? ` · ${result.device_key}` : ''}`
        : '';

      if (result.already_configured) {
        setStep('auth', 'success', 'Autentykacja poprawna, ale to urządzenie jest już skonfigurowane w Home Assistant.');
        setStep('create', 'error', 'Nie można dodać tego samego urządzenia drugi raz.');
        authOk = false;
      } else {
        authOk = true;
        setStep('auth', 'success', 'Autentykacja poprawna. NanoKVM zaakceptował login i hasło.');
        setStep('create', 'pending', 'Urządzenie jest gotowe do dodania do Home Assistant.');
      }
    } catch (error) {
      setStep('auth', 'error', `Test autentykacji nieudany: ${error.message}`);
      setStep('create', 'pending', 'Popraw dane logowania i ponów test autentykacji.');
    } finally {
      setBusy(false);
    }
  });

  createButton.addEventListener('click', async () => {
    if (!authOk) return;
    setStep('create', 'working', 'Dodaję urządzenie przez config flow Home Assistant…');
    setBusy(true);
    try {
      const result = await rpc('nanokvm_rest/panel/device/create', credentialsPayload());
      setStep('create', 'success', `Dodano urządzenie ${result.title || 'NanoKVM'}.`);
      passwordInput.value = '';
      globalNotice(`Dodano urządzenie ${result.title || 'NanoKVM'}.`);
      window.setTimeout(() => {
        dialog.close();
        document.getElementById('refresh')?.click();
      }, 700);
    } catch (error) {
      setStep('create', 'error', `Nie udało się dodać urządzenia: ${error.message}`);
      globalNotice(error.message, true);
    } finally {
      setBusy(false);
    }
  });
})();
