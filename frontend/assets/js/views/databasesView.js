/**
 * views/databasesView.js — Halaman "Database Management"
 * -----------------------------------------------------------------------
 * Mencakup 3 endpoint per engine: create, show, delete.
 * SQLite: daftar berupa file .db (punya parameter `search_dir`).
 * MySQL / PostgreSQL: daftar berupa nama database di server.
 */

import { createDatabase, showDatabases, deleteDatabase } from '../api/database.js';
import { state, setState } from '../state.js';
import { toastSuccess, toastApiError } from '../ui/toast.js';
import { confirmDialog, openModal, closeModal } from '../ui/modal.js';
import { icon } from '../ui/icons.js';
import { engineLabel, engineDotColor, escapeHtml } from '../ui/helpers.js';

export async function renderDatabasesView(root, navigate) {
  // Sesi login hanya diotorisasi untuk satu engine (backend menolak engine
  // lain dengan 401) — jadi halaman ini selalu mengikuti engine sesi aktif,
  // tanpa pilihan berpindah engine.
  const engine = state.session?.db || 'sqlite';

  root.innerHTML = `
    <div class="view">
      <div class="page-head">
        <div>
          <h1>Database Management</h1>
          <p>Buat, lihat, dan hapus database pada engine <span class="badge badge--${engine}"><span class="dot" style="background:${engineDotColor(engine)}"></span>${engineLabel(engine)}</span> yang sedang login.</p>
        </div>
      </div>

      <div class="card" id="db-toolbar">
        <div class="toolbar-row">
          <div class="text-tertiary" style="font-size:12.5px">Menampilkan database di server ${engineLabel(engine)} yang sedang login.</div>
          <div class="toolbar-row__actions">
            <button class="btn" id="db-refresh">${icon('refresh', { size: 15 })} Refresh</button>
            <button class="btn btn--primary" id="db-create">${icon('plus', { size: 15 })} Database baru</button>
          </div>
        </div>
      </div>

      <div class="card" id="db-list-card">
        <div class="loading-row"><span class="spinner"></span> Memuat daftar database…</div>
      </div>
    </div>
  `;

  root.querySelector('#db-refresh').addEventListener('click', () => loadList());
  root.querySelector('#db-create').addEventListener('click', () => openCreateModal(engine, loadList));
  const searchDirInput = root.querySelector('#search-dir');
  if (searchDirInput) {
    searchDirInput.addEventListener('change', () => loadList());
  }

  async function loadList() {
    const listCard = root.querySelector('#db-list-card');
    listCard.innerHTML = `<div class="loading-row"><span class="spinner"></span> Memuat daftar database…</div>`;
    try {
      const opts = engine === 'sqlite' ? { searchDir: searchDirInput?.value || '.' } : {};
      const res = await showDatabases(engine, opts);
      renderList(listCard, engine, res, loadList, navigate);
    } catch (err) {
      listCard.innerHTML = `
        <div class="empty-state">
          ${icon('alert', { size: 30 })}
          <h3>Gagal memuat database</h3>
          <p>${escapeHtml(err.message)}</p>
        </div>`;
    }
  }

  loadList();
}

function renderList(container, engine, res, reload, navigate) {
  const dbs = res?.databases || [];
  if (!dbs.length) {
    container.innerHTML = `
      <div class="empty-state">
        ${icon('database', { size: 30 })}
        <h3>Belum ada database</h3>
        <p>Buat database ${engineLabel(engine)} pertama kamu untuk mulai bekerja dengan tabel.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="card__head">
      <div class="card__title">${engineLabel(engine)}<small>${res.total} database ditemukan</small></div>
    </div>
    <div class="list">
      ${dbs
        .map((d) => {
          const name = typeof d === 'string' ? d : d.name || JSON.stringify(d);
          const meta = typeof d === 'object' && d !== null ? d : null;
          return `
          <div class="list-row" data-db-row="${escapeHtml(name)}">
            <div class="list-row__main">
              ${icon('database', { size: 15 })}
              <div>
                <div class="list-row__name">${escapeHtml(name)}</div>
                ${meta ? `<div class="text-tertiary" style="font-size:11px">${escapeHtml(
                  Object.entries(meta)
                    .filter(([k]) => k !== 'name')
                    .map(([k, v]) => `${k}: ${v}`)
                    .join(' · ')
                )}</div>` : ''}
              </div>
            </div>
            <div class="list-row__actions">
              <button class="btn btn--sm" data-use="${escapeHtml(name)}">${icon('table', { size: 13 })} Buka tabel</button>
              <button class="btn btn--sm btn--danger btn--icon" data-delete="${escapeHtml(name)}" aria-label="Hapus database">${icon('trash', { size: 13 })}</button>
            </div>
          </div>`;
        })
        .join('')}
    </div>
  `;

  container.querySelectorAll('[data-use]').forEach((btn) => {
    btn.addEventListener('click', () => {
      setState({ activeDbName: btn.dataset.use, activeTable: null });
      navigate('tables');
    });
  });

  container.querySelectorAll('[data-delete]').forEach((btn) => {
    btn.addEventListener('click', () => openDeleteModal(engine, btn.dataset.delete, reload));
  });
}

function openCreateModal(engine, reload) {
  const needsCreds = engine !== 'sqlite';
  openModal({
    title: `Buat database ${engineLabel(engine)}`,
    subtitle: engine === 'sqlite' ? 'Akan dibuat sebagai file .db baru di server' : 'Akan dibuat di server yang sedang aktif',
    bodyHtml: `
      <div class="field">
        <label for="new-db-name">Nama database</label>
        <input type="text" id="new-db-name" placeholder="${engine === 'sqlite' ? 'toko (tanpa .db)' : 'toko_db'}" autofocus>
      </div>
      <div id="create-db-error"></div>
    `,
    footerHtml: `
      <button class="btn" data-close>Batal</button>
      <button class="btn btn--primary" id="create-db-submit">${icon('plus', { size: 14 })} Buat database</button>
    `,
    onMount: (modalEl) => {
      const input = modalEl.querySelector('#new-db-name');
      const errorBox = modalEl.querySelector('#create-db-error');
      modalEl.querySelector('#create-db-submit').addEventListener('click', async () => {
        const name = input.value.trim();
        if (!name) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}Nama database wajib diisi.</div>`;
          return;
        }
        try {
          const res = await createDatabase(engine, name);
          toastSuccess(res?.message || `Database "${name}" berhasil dibuat.`);
          closeModal();
          reload();
        } catch (err) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}${escapeHtml(err.message)}</div>`;
        }
      });
      setTimeout(() => input.focus(), 30);
    },
  });
}

async function openDeleteModal(engine, dbName, reload) {
  const ok = await confirmDialog({
    title: `Hapus database "${dbName}"?`,
    message: `Tindakan ini akan menghapus database <b>${escapeHtml(dbName)}</b> beserta seluruh isinya secara permanen dan tidak dapat dibatalkan.`,
    confirmLabel: 'Hapus permanen',
    danger: true,
    requireText: dbName,
  });
  if (!ok) return;
  try {
    const res = await deleteDatabase(engine, dbName);
    toastSuccess(res?.message || `Database "${dbName}" dihapus.`);
    reload();
  } catch (err) {
    toastApiError(err);
  }
}
