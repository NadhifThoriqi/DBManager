/**
 * views/dashboardView.js — Halaman ringkasan setelah login
 */

import { showDatabases } from '../api/database.js';
import { state } from '../state.js';
import { icon } from '../ui/icons.js';
import { engineLabel, engineDotColor } from '../ui/helpers.js';

export async function renderDashboardView(root, navigate) {
  const s = state.session;
  const engine = s?.db || 'sqlite';
  const dotColor = engineDotColor(engine);

  root.innerHTML = `
    <div class="view">
      <div class="dash-hero">
        <div class="dash-hero__intro">
          <div class="dash-hero__avatar">${icon('database', { size: 22 })}</div>
          <div>
            <h1>Selamat datang, ${s?.user || 'pengguna'} 👋</h1>
            <p>Ringkasan koneksi dan status server DBManager API kamu.</p>
          </div>
        </div>
        <button class="btn btn--primary dash-hero__cta" id="dash-go-databases">${icon('database', { size: 15 })} Kelola Database</button>
      </div>

      <div class="dash-grid">
        <div class="card">
          <div class="card__head">
            <div class="card__title">Sesi aktif<small>Kredensial dipakai backend untuk membuka koneksi</small></div>
          </div>
          <div class="session-meta">
            <div class="session-meta__item">
              <span class="session-meta__icon">${icon('key', { size: 14 })}</span>
              <div>
                <div class="session-meta__label">Username</div>
                <div class="session-meta__value mono">${s?.user || '—'}</div>
              </div>
            </div>
            <div class="session-meta__item">
              <span class="session-meta__icon">${icon('layers', { size: 14 })}</span>
              <div>
                <div class="session-meta__label">Engine login</div>
                <div class="session-meta__value"><span class="badge badge--${engine}"><span class="dot" style="background:${dotColor}"></span>${engineLabel(engine)}</span></div>
              </div>
            </div>
            <div class="session-meta__item">
              <span class="session-meta__icon">${icon('server', { size: 14 })}</span>
              <div>
                <div class="session-meta__label">Host : Port</div>
                <div class="session-meta__value mono">${s?.host || '—'}${s?.port ? `:${s.port}` : ''}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card stat-highlight" id="engine-stats" style="--stat-color:${dotColor}" data-engine-card="${engine}">
          <div class="stat-highlight__icon">${icon('database', { size: 20 })}</div>
          <div class="stat-highlight__value" data-count>${icon('loader', { size: 20, className: 'spin-icon' })}</div>
          <div class="stat-highlight__label"><span class="dot" style="background:${dotColor}"></span>database ${engineLabel(engine)} tersimpan</div>
        </div>
      </div>

      <div class="card">
        <div class="card__head">
          <div class="card__title">Mulai cepat<small>Alur kerja umum di DBManager</small></div>
        </div>
        <div class="action-grid">
          <button type="button" class="action-card" data-route="databases">
            <span class="action-card__icon">${icon('database', { size: 17 })}</span>
            <span class="action-card__body">
              <span class="action-card__title">1. Buat / pilih database</span>
              <span class="action-card__desc">Kelola database pada tab Databases</span>
            </span>
            ${icon('chevronRight', { size: 16, className: 'action-card__arrow' })}
          </button>
          <button type="button" class="action-card" data-route="tables">
            <span class="action-card__icon">${icon('table', { size: 17 })}</span>
            <span class="action-card__body">
              <span class="action-card__title">2. Buka tabel</span>
              <span class="action-card__desc">Pilih database lalu buat / pilih tabel</span>
            </span>
            ${icon('chevronRight', { size: 16, className: 'action-card__arrow' })}
          </button>
          <button type="button" class="action-card" data-route="designer">
            <span class="action-card__icon">${icon('columns', { size: 17 })}</span>
            <span class="action-card__body">
              <span class="action-card__title">3. Lihat struktur & relasi</span>
              <span class="action-card__desc">Tambah kolom atau kelola data lewat grid / Designer</span>
            </span>
            ${icon('chevronRight', { size: 16, className: 'action-card__arrow' })}
          </button>
        </div>
      </div>
    </div>
  `;

  root.querySelector('#dash-go-databases').addEventListener('click', () => navigate('databases'));
  root.querySelectorAll('[data-route]').forEach((btn) => {
    btn.addEventListener('click', () => navigate(btn.dataset.route));
  });

  // Muat statistik jumlah database untuk engine yang sedang login saja —
  // engine lain tidak diotorisasi oleh sesi ini dan akan gagal (401).
  (async () => {
    const card = root.querySelector(`[data-engine-card="${engine}"] [data-count]`);
    try {
      const res = await showDatabases(engine);
      if (card) card.textContent = res?.total ?? (res?.databases?.length || 0);
    } catch (err) {
      if (card) card.innerHTML = `<span style="font-size:13px;color:var(--text-tertiary)">n/a</span>`;
    }
  })();
}
