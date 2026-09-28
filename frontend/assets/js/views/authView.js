/**
 * views/authView.js — Layar Sign In
 * -----------------------------------------------------------------------
 * Mengirim { user, db, host, port, password } ke /auth/signin. Backend akan
 * mengeset cookie sesi (access_token), lalu seluruh request berikutnya
 * otomatis membawa cookie itu karena api/client.js selalu memakai
 * `credentials: 'include'`.
 */

import { signIn } from '../api/auth.js';
import { ApiError } from '../api/client.js';
import { setSession } from '../state.js';
import { toastSuccess } from '../ui/toast.js';
import { icon } from '../ui/icons.js';
import { getApiBaseUrl } from '../config.js';

const DEFAULT_PORTS = { sqlite: '', mysql: '3306', postgresql: '5432' };

export function renderAuthView(root, onSuccess) {
  root.innerHTML = `
    <div class="auth-screen">
      <div class="auth-screen__side">
        <div class="auth-brand">
          <div class="auth-brand-mark">${icon('database', { size: 20 })}</div>
          <div class="auth-brand-name">DBManager<small>Database Admin Console</small></div>
        </div>

        <div class="auth-hero">
          <h1>Kelola <em>SQLite, MySQL,</em> dan <em>PostgreSQL</em> dari satu tempat.</h1>
          <p>Buat &amp; hapus database, rancang skema tabel, dan jelajahi isi data secara langsung ke server DBManager API kamu.</p>
        </div>

        <div class="engine-strip">
          <div class="engine-chip"><span class="dot" style="background:var(--engine-sqlite)"></span>sqlite</div>
          <div class="engine-chip"><span class="dot" style="background:var(--engine-mysql)"></span>mysql</div>
          <div class="engine-chip"><span class="dot" style="background:var(--engine-postgresql)"></span>postgresql</div>
        </div>
      </div>

      <div class="auth-screen__form">
        <div class="auth-card">
          <div class="auth-card__eyebrow">Selamat datang</div>
          <h2>Masuk ke server database kamu</h2>
          <p>Kredensial ini dipakai backend untuk membuka koneksi ke engine database yang dipilih.</p>

          <div id="auth-error"></div>

          <form id="auth-form">
            <div class="field">
              <label for="f-user">Username</label>
              <input type="text" id="f-user" name="user" placeholder="mis. root / admin" autocomplete="username" required>
            </div>

            <div class="field">
              <label for="f-db">Tipe database</label>
              <select id="f-db" name="db">
                <option value="sqlite">SQLite</option>
                <option value="mysql">MySQL</option>
                <option value="postgresql">PostgreSQL</option>
              </select>
            </div>

            <div class="field-row">
              <div class="field">
                <label for="f-host">Host</label>
                <input type="text" id="f-host" name="host" placeholder="localhost" value="localhost" required>
              </div>
              <div class="field">
                <label for="f-port">Port</label>
                <input type="number" id="f-port" name="port" placeholder="3306">
              </div>
            </div>

            <div class="field">
              <label for="f-password">Password</label>
              <input type="password" id="f-password" name="password" placeholder="••••••••" autocomplete="current-password">
            </div>

            <button type="submit" class="btn btn--primary btn--block mt-16" id="auth-submit">
              <span id="auth-submit-label">Sign In</span>
            </button>
          </form>

          <div class="auth-form-foot">
            <span>Server: <code class="mono">${getApiBaseUrl()}</code></span>
            <button type="button" class="link-btn" id="auth-server-btn">Ubah</button>
          </div>
        </div>
      </div>
    </div>
  `;

  const form = root.querySelector('#auth-form');
  const dbSelect = root.querySelector('#f-db');
  const portInput = root.querySelector('#f-port');
  const errorBox = root.querySelector('#auth-error');
  const submitBtn = root.querySelector('#auth-submit');
  const submitLabel = root.querySelector('#auth-submit-label');

  function applyDefaultPort() {
    portInput.value = DEFAULT_PORTS[dbSelect.value] || '';
    portInput.placeholder = dbSelect.value === 'sqlite' ? 'tidak dipakai (isi 0)' : DEFAULT_PORTS[dbSelect.value];
  }
  dbSelect.addEventListener('change', applyDefaultPort);
  applyDefaultPort();

  root.querySelector('#auth-server-btn').addEventListener('click', () => {
    import('../ui/serverSettings.js').then((m) => m.openServerSettingsModal(() => renderAuthView(root, onSuccess)));
  });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    errorBox.innerHTML = '';

    const fd = new FormData(form);
    const payload = {
      user: fd.get('user').trim(),
      db: fd.get('db'),
      host: fd.get('host').trim(),
      port: Number(fd.get('port')) || 0,
      password: fd.get('password'),
    };

    const originalLabel = 'Sign In';
    submitBtn.disabled = true;
    submitLabel.innerHTML = `<span class="spinner" style="width:13px;height:13px;border-width:2px;vertical-align:-2px"></span> Memproses…`;

    try {
      await signIn(payload);
      setSession({ user: payload.user, db: payload.db, host: payload.host, port: payload.port });
      toastSuccess(`Berhasil masuk sebagai ${payload.user}`);
      onSuccess();
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Gagal terhubung ke server.';
      errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 15 })}<span>${message}</span></div>`;
      submitBtn.disabled = false;
      submitLabel.textContent = originalLabel;
    }
  });
}
