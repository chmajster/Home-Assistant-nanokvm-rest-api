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
  let setupId = '';

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
    connectionButton.disabled = busy || authOk;
    authButton.disabled = busy || !connectionOk || authOk;
    createButton.disabled = busy || !authOk;
    closeButton.disabled = busy;
  }

  async function jsonPost(url, payload) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-NanoKVM-Request': '1',
      },
      body: JSON.stringify(payload || {}),
    });
    const data = await response.json().catch(() => ({ok: false, error: `HTTP ${response.status}`}));
    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function globalNotice(message, bad = false) {
    const notice = document.getElementById('notice');
    if (!notice) return;
    notice.textContent = message;
    notice.classList.toggle('bad', bad);
    notice.classList.remove('hidden');
    window.setTimeout(() => notice.classList.add('hidden'), 6000);
  }

  function cancelSetup(id = setupId) {
    if (!id) return;
    if (id === setupId) setupId = '';
    void jsonPost('api/device/setup/cancel', {setup_id: id}).catch(() => {});
  }

  function unlockFields() {
    usernameInput.disabled = false;
    passwordInput.disabled = false;
    urlInput.disabled = false;
    verifyInput.disabled = false;
  }

  function resetAuth({keepFlow = true} = {}) {
    if (!keepFlow) cancelSetup();
    authOk = false;
    identity.textContent = '';
    setStep(
      'auth',
      'pending',
      connectionOk
        ? 'Połączenie działa. Teraz sprawdź login i hasło.'
        : 'Najpierw wykonaj test połączenia, potem sprawdź login i hasło.',
    );
    setStep('create', 'pending', 'Urządzenie zostanie dodane dopiero po poprawnej autentykacji.');
    setBusy(busy);
  }

  function resetConnection({cancel = true} = {}) {
    if (cancel) cancelSetup();
    connectionOk = false;
    authOk = false;
    identity.textContent = '';
    unlockFields();
    setStep('connection', 'pending', 'Sprawdzimy, czy host odpowiada po HTTP lub HTTPS. Dane logowania nie są wysyłane.');
    setStep('auth', 'pending', 'Najpierw wykonaj test połączenia, potem sprawdź login i hasło.');
    setStep('create', 'pending', 'Urządzenie zostanie dodane dopiero po poprawnej autentykacji.');
    setBusy(busy);
  }

  function resetForm() {
    cancelSetup();
    form.reset();
    unlockFields();
    usernameInput.value = 'admin';
    verifyInput.checked = true;
    passwordInput.value = '';
    setupId = '';
    busy = false;
    resetConnection({cancel: false});
  }

  openButton.addEventListener('click', () => {
    resetForm();
    dialog.showModal();
    window.setTimeout(() => urlInput.focus(), 0);
  });

  closeButton.addEventListener('click', () => {
    if (!busy) {
      cancelSetup();
      dialog.close();
    }
  });

  dialog.addEventListener('close', () => {
    cancelSetup();
    passwordInput.value = '';
    unlockFields();
  });

  dialog.addEventListener('cancel', (event) => {
    if (busy) {
      event.preventDefault();
      return;
    }
    cancelSetup();
  });

  urlInput.addEventListener('input', () => resetConnection());
  verifyInput.addEventListener('change', () => resetConnection());

  usernameInput.addEventListener('input', () => {
    if (authOk) {
      resetConnection();
      return;
    }
    resetAuth({keepFlow: true});
  });

  passwordInput.addEventListener('input', () => {
    if (authOk) {
      resetConnection();
      return;
    }
    resetAuth({keepFlow: true});
  });

  connectionButton.addEventListener('click', async () => {
    const baseUrl = urlInput.value.trim();
    if (!baseUrl) {
      setStep('connection', 'error', 'Podaj adres IP, nazwę hosta albo pełny URL NanoKVM.');
      urlInput.focus();
      return;
    }

    cancelSetup();
    connectionOk = false;
    authOk = false;
    identity.textContent = '';
    setStep('connection', 'working', 'Testuję połączenie z urządzeniem…');
    setStep('auth', 'pending', 'Oczekiwanie na poprawny test połączenia.');
    setStep('create', 'pending', 'Urządzenie zostanie dodane dopiero po poprawnej autentykacji.');
    setBusy(true);
    try {
      const result = await jsonPost('api/device/setup/connection', {
        base_url: baseUrl,
        verify_ssl: verifyInput.checked,
      });
      setupId = result.setup_id || '';
      if (result.base_url) urlInput.value = result.base_url;
      connectionOk = Boolean(setupId);
      if (!connectionOk) throw new Error('Home Assistant nie zwrócił sesji konfiguracji.');
      setStep('connection', 'success', `Połączenie działa: ${result.base_url || baseUrl}.`);
      setStep('auth', 'pending', 'Połączenie działa. Teraz sprawdź login i hasło.');
    } catch (error) {
      setupId = '';
      setStep('connection', 'error', `Test połączenia nieudany: ${error.message}`);
    } finally {
      setBusy(false);
    }
  });

  authButton.addEventListener('click', async () => {
    if (!connectionOk || !setupId) return;
    if (!usernameInput.value.trim() || !passwordInput.value) {
      setStep('auth', 'error', 'Podaj nazwę użytkownika i hasło.');
      return;
    }

    authOk = false;
    setStep('auth', 'working', 'Loguję się do NanoKVM i odczytuję identyfikator urządzenia…');
    setBusy(true);
    try {
      const result = await jsonPost('api/device/setup/authentication', {
        setup_id: setupId,
        username: usernameInput.value.trim(),
        password: passwordInput.value,
      });
      identity.textContent = result.title
        ? `Wykryto: ${result.title}${result.device_key ? ` · ${result.device_key}` : ''}`
        : '';
      if (result.base_url) urlInput.value = result.base_url;
      authOk = true;
      passwordInput.value = '';
      usernameInput.disabled = true;
      passwordInput.disabled = true;
      urlInput.disabled = true;
      verifyInput.disabled = true;
      setStep('auth', 'success', 'Autentykacja poprawna. NanoKVM zaakceptował login i hasło.');
      setStep('create', 'pending', 'Urządzenie jest zweryfikowane i gotowe do dodania do Home Assistant.');
    } catch (error) {
      if (error.status === 409) {
        setupId = '';
        connectionOk = false;
      }
      setStep('auth', 'error', `Test autentykacji nieudany: ${error.message}`);
      setStep(
        'create',
        'pending',
        error.status === 409
          ? 'To urządzenie nie może zostać dodane ponownie.'
          : 'Popraw dane logowania i ponów test autentykacji.',
      );
    } finally {
      setBusy(false);
    }
  });

  createButton.addEventListener('click', async () => {
    if (!authOk || !setupId) return;
    setStep('create', 'working', 'Dodaję zweryfikowane urządzenie przez config flow Home Assistant…');
    setBusy(true);
    try {
      const result = await jsonPost('api/device/setup/create', {setup_id: setupId});
      setupId = '';
      setStep('create', 'success', `Dodano urządzenie ${result.title || 'NanoKVM'}.`);
      globalNotice(`Dodano urządzenie ${result.title || 'NanoKVM'}.`);
      window.setTimeout(() => {
        dialog.close();
        window.location.reload();
      }, 700);
    } catch (error) {
      setStep('create', 'error', `Nie udało się dodać urządzenia: ${error.message}`);
      globalNotice(error.message, true);
      setBusy(false);
    }
  });
})();
