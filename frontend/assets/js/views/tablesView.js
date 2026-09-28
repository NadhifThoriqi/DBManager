/**
 * views/tablesView.js — Halaman "Table Operations"
 * -----------------------------------------------------------------------
 * Mencakup seluruh endpoint grup Table Operations pada openapi.json:
 *   POST   /table/list          -> daftar tabel
 *   POST   /table/structure     -> tab "Struktur"
 *   POST   /table/content       -> tab "Data"
 *   POST   /table/create        -> modal "Buat tabel"
 *   POST   /table/column/add    -> tab "Tambah Kolom"
 *   POST   /table/insert        -> tab "Insert Row"
 *   PUT    /table/update        -> modal "Edit baris" (dari tab Data)
 *   DELETE /table/row           -> konfirmasi hapus baris (dari tab Data)
 *   DELETE /table/clear         -> tab "Danger Zone"
 *   DELETE /table/drop          -> tab "Danger Zone"
 *
 * Operasi tabel bekerja di atas koneksi engine yang sedang login
 * (state.session.db) — hanya `db_name` (nama database spesifik pada
 * engine tsb.) dan `table_name` yang perlu dipilih di halaman ini.
 *
 * File ini cukup panjang karena satu halaman menaungi banyak aksi CRUD.
 * Struktur dibagi jadi 4 bagian yang ditandai komentar besar:
 *   1) BOOTSTRAP  — render kerangka halaman, pilih database
 *   2) TABLE LIST  — memuat & memilih tabel
 *   3) WORKSPACE TABS — Data / Struktur / Insert / Tambah Kolom / Danger
 *   4) MODALS — buat tabel, edit baris, hapus baris
 */

import { showDatabases } from '../api/database.js';
import * as TableAPI from '../api/table.js';
import { state, setState } from '../state.js';
import { toastSuccess, toastApiError } from '../ui/toast.js';
import { confirmDialog, openModal, closeModal } from '../ui/modal.js';
import { icon } from '../ui/icons.js';
import {
  escapeHtml,
  formatCellValue,
  engineLabel,
  inputTypeForSqlType,
  coerceValueBySqlType,
  safeId,
} from '../ui/helpers.js';

/** Konteks lokal halaman ini — direset setiap kali view dirender ulang. */
const ctx = {
  root: null,
  navigate: null,
  engine: null,
  dbName: '',
  tables: [],
  activeTable: null,
  structure: [], // TableStructureResponse.columns
  content: null, // TableContentResponse
  limit: 25,
  activeTab: 'data', // data | structure | insert | addcolumn | danger
};

/* =========================================================================
   1) BOOTSTRAP
   ========================================================================= */

export async function renderTablesView(root, navigate) {
  ctx.root = root;
  ctx.navigate = navigate;
  ctx.engine = state.session?.db || 'sqlite';
  ctx.dbName = state.activeDbName || '';
  ctx.tables = [];
  ctx.activeTable = state.activeTable || null;
  ctx.structure = [];
  ctx.content = null;
  ctx.activeTab = 'data';

  root.innerHTML = `
    <div class="view view--wide">
      <div class="page-head">
        <div>
          <h1>Table Operations</h1>
          <p>Bekerja pada engine <span class="badge badge--${ctx.engine}">${engineLabel(ctx.engine)}</span> — koneksi sesi login kamu.</p>
        </div>
      </div>

      <div class="card">
        <div class="field-row" style="align-items:end">
          <div class="field" style="margin:0">
            <label for="db-name-select">Database</label>
            <select id="db-name-select">
              <option value="">Memuat daftar database…</option>
            </select>
          </div>
          <div class="field" style="margin:0">
            <label for="db-name-manual">Atau ketik nama database manual</label>
            <div class="input-group">
              <input type="text" id="db-name-manual" placeholder="nama_database" value="${escapeHtml(ctx.dbName)}">
              <button class="btn btn--primary" id="db-name-load">${icon('search', { size: 14 })} Muat tabel</button>
            </div>
          </div>
        </div>
      </div>

      <div class="split" id="tables-split">
        <div class="empty-state" style="grid-column:1/-1">
          ${icon('database', { size: 30 })}
          <h3>Pilih database dulu</h3>
          <p>Pilih atau ketik nama database di atas, lalu klik "Muat tabel" untuk melihat daftar tabelnya.</p>
        </div>
      </div>
    </div>
  `;

  const dbSelect = root.querySelector('#db-name-select');
  const dbManual = root.querySelector('#db-name-manual');
  const dbLoadBtn = root.querySelector('#db-name-load');

  try {
    const res = await showDatabases(ctx.engine);
    const dbs = (res?.databases || []).map((d) => (typeof d === 'string' ? d : d.name));
    dbSelect.innerHTML =
      `<option value="">— pilih dari daftar —</option>` +
      dbs.map((n) => `<option value="${escapeHtml(n)}" ${n === ctx.dbName ? 'selected' : ''}>${escapeHtml(n)}</option>`).join('');
  } catch {
    dbSelect.innerHTML = `<option value="">(gagal memuat daftar database)</option>`;
  }

  dbSelect.addEventListener('change', () => {
    if (dbSelect.value) {
      dbManual.value = dbSelect.value;
      loadDatabase(dbSelect.value);
    }
  });
  dbLoadBtn.addEventListener('click', () => loadDatabase(dbManual.value.trim()));
  dbManual.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') loadDatabase(dbManual.value.trim());
  });

  if (ctx.dbName) loadDatabase(ctx.dbName);
}

/* =========================================================================
   2) TABLE LIST
   ========================================================================= */

async function loadDatabase(dbName) {
  if (!dbName) {
    toastApiError({ message: 'Nama database tidak boleh kosong.' });
    return;
  }
  ctx.dbName = dbName;
  ctx.activeTable = null;
  setState({ activeDbName: dbName, activeTable: null });

  const splitEl = ctx.root.querySelector('#tables-split');
  splitEl.innerHTML = `<div class="loading-row" style="grid-column:1/-1"><span class="spinner"></span> Memuat daftar tabel…</div>`;

  try {
    const res = await TableAPI.listTables(dbName);
    ctx.tables = res?.tables || [];
    renderSplit();
  } catch (err) {
    splitEl.innerHTML = `
      <div class="empty-state" style="grid-column:1/-1">
        ${icon('alert', { size: 30 })}
        <h3>Gagal memuat tabel</h3>
        <p>${escapeHtml(err.message)}</p>
      </div>`;
  }
}

function renderSplit() {
  const splitEl = ctx.root.querySelector('#tables-split');
  splitEl.innerHTML = `
    <div class="split__side">
      <div class="card" style="padding:14px">
        <div class="card__head" style="margin-bottom:10px">
          <div class="card__title" style="font-size:13px">Tabel<small>${ctx.tables.length} ditemukan</small></div>
          <button class="btn btn--sm btn--icon" id="new-table-btn" aria-label="Buat tabel baru">${icon('plus', { size: 14 })}</button>
        </div>
        <div class="picker" id="table-picker">
          ${
            ctx.tables.length
              ? ctx.tables
                  .map(
                    (t) =>
                      `<button type="button" class="picker-item ${t === ctx.activeTable ? 'active' : ''}" data-table="${escapeHtml(t)}">${icon('table', { size: 13 })}<span style="flex:1;text-align:left;overflow:hidden;text-overflow:ellipsis">${escapeHtml(t)}</span></button>`
                  )
                  .join('')
              : `<p class="text-tertiary" style="font-size:12.5px;padding:8px 4px">Belum ada tabel pada database ini.</p>`
          }
        </div>
      </div>
    </div>
    <div id="table-workspace">
      <div class="empty-state">
        ${icon('table', { size: 30 })}
        <h3>Pilih tabel</h3>
        <p>Pilih tabel di panel kiri untuk melihat data, struktur, dan aksi lainnya — atau buat tabel baru.</p>
      </div>
    </div>
  `;

  splitEl.querySelector('#new-table-btn').addEventListener('click', openCreateTableModal);
  splitEl.querySelectorAll('[data-table]').forEach((btn) => {
    btn.addEventListener('click', () => selectTable(btn.dataset.table));
  });

  if (ctx.activeTable && ctx.tables.includes(ctx.activeTable)) {
    selectTable(ctx.activeTable);
  }
}

async function selectTable(tableName) {
  ctx.activeTable = tableName;
  ctx.activeTab = 'data';
  setState({ activeTable: tableName });

  ctx.root.querySelectorAll('#table-picker [data-table]').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.table === tableName);
  });

  const workspace = ctx.root.querySelector('#table-workspace');
  workspace.innerHTML = `<div class="loading-row"><span class="spinner"></span> Memuat "${escapeHtml(tableName)}"…</div>`;

  try {
    const [structureRes, contentRes] = await Promise.all([
      TableAPI.getTableStructure(ctx.dbName, tableName),
      TableAPI.getTableContent(ctx.dbName, tableName, ctx.limit),
    ]);
    ctx.structure = structureRes?.columns || [];
    ctx.content = contentRes;
    renderWorkspace();
  } catch (err) {
    workspace.innerHTML = `
      <div class="empty-state">
        ${icon('alert', { size: 30 })}
        <h3>Gagal memuat tabel</h3>
        <p>${escapeHtml(err.message)}</p>
      </div>`;
  }
}

/* =========================================================================
   3) WORKSPACE TABS
   ========================================================================= */

const TABS = [
  { id: 'data', label: 'Data', icon: 'eye' },
  { id: 'structure', label: 'Struktur', icon: 'columns' },
  { id: 'insert', label: 'Insert Row', icon: 'plus' },
  { id: 'addcolumn', label: 'Tambah Kolom', icon: 'layers' },
  { id: 'danger', label: 'Danger Zone', icon: 'alert' },
];

function renderWorkspace() {
  const workspace = ctx.root.querySelector('#table-workspace');
  workspace.innerHTML = `
    <div class="card" style="padding:0">
      <div class="card__head" style="padding:16px 18px 0;margin-bottom:0">
        <div class="card__title">${icon('table', { size: 15 })} <span class="mono">${escapeHtml(ctx.activeTable)}</span><small>Database: ${escapeHtml(ctx.dbName)}</small></div>
        <button class="btn btn--sm" id="table-refresh">${icon('refresh', { size: 13 })} Refresh</button>
      </div>
      <div class="tabs" style="padding:0 18px;margin-top:12px">
        ${TABS.map(
          (t) => `<button type="button" class="tab ${t.id === ctx.activeTab ? 'active' : ''}" data-tab="${t.id}">${icon(t.icon, { size: 14 })}${t.label}</button>`
        ).join('')}
      </div>
      <div id="tab-content" style="padding:18px"></div>
    </div>
  `;

  workspace.querySelector('#table-refresh').addEventListener('click', () => selectTable(ctx.activeTable));
  workspace.querySelectorAll('[data-tab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      ctx.activeTab = btn.dataset.tab;
      workspace.querySelectorAll('[data-tab]').forEach((b) => b.classList.toggle('active', b === btn));
      renderTabContent();
    });
  });

  renderTabContent();
}

function renderTabContent() {
  const container = ctx.root.querySelector('#tab-content');
  if (!container) return;
  const renderers = {
    data: renderDataTab,
    structure: renderStructureTab,
    insert: renderInsertTab,
    addcolumn: renderAddColumnTab,
    danger: renderDangerTab,
  };
  renderers[ctx.activeTab](container);
}

/* ---- Tab: Data (browse rows, edit/delete per baris) -------------------- */

function primaryKeyColumns() {
  const pk = ctx.structure.filter((c) => {
    const flags = ['primary_key', 'pk', 'is_primary', 'primaryKey'];
    return flags.some((f) => c[f] === true || c[f] === 1);
  });
  if (pk.length) return pk.map((c) => c.name).filter(Boolean);
  const idCol = ctx.structure.find((c) => (c.name || '').toLowerCase() === 'id');
  return idCol ? [idCol.name] : [];
}

function renderDataTab(container) {
  const rows = ctx.content?.rows || [];
  const columnNames = rows.length ? Object.keys(rows[0]) : ctx.structure.map((c) => c.name).filter(Boolean);

  container.innerHTML = `
    <div class="flex-between mt-4" style="margin-bottom:12px">
      <div class="flex gap-8" style="align-items:center">
        <label class="text-secondary" style="font-size:12.5px;font-weight:700">Limit</label>
        <select id="content-limit" style="width:90px">
          ${[10, 25, 50, 100, 250, 1000].map((n) => `<option value="${n}" ${n === ctx.limit ? 'selected' : ''}>${n}</option>`).join('')}
        </select>
      </div>
      <span class="pill-count">${rows.length} baris ditampilkan</span>
    </div>
    <div id="data-grid-holder"></div>
  `;

  container.querySelector('#content-limit').addEventListener('change', async (e) => {
    ctx.limit = Number(e.target.value);
    const holder = container.querySelector('#data-grid-holder');
    holder.innerHTML = `<div class="loading-row"><span class="spinner"></span> Memuat data…</div>`;
    try {
      ctx.content = await TableAPI.getTableContent(ctx.dbName, ctx.activeTable, ctx.limit);
      renderDataTab(container);
    } catch (err) {
      toastApiError(err);
    }
  });

  const holder = container.querySelector('#data-grid-holder');

  if (!rows.length) {
    holder.innerHTML = `
      <div class="empty-state">
        ${icon('inbox', { size: 28 })}
        <h3>Tabel kosong</h3>
        <p>Belum ada baris data. Gunakan tab "Insert Row" untuk menambahkan data pertama.</p>
      </div>`;
    return;
  }

  holder.innerHTML = `
    <div class="table-scroll">
      <table class="data-grid">
        <thead>
          <tr>
            ${columnNames.map((c) => `<th>${escapeHtml(c)}</th>`).join('')}
            <th>Aksi</th>
          </tr>
        </thead>
        <tbody>
          ${rows
            .map((row, i) => {
              const cells = columnNames
                .map((c) => {
                  const { text, isNull } = formatCellValue(row[c]);
                  return `<td class="${isNull ? 'cell-null' : ''}" title="${escapeHtml(text)}">${escapeHtml(text)}</td>`;
                })
                .join('');
              return `
              <tr data-row-index="${i}">
                ${cells}
                <td class="actions-cell">
                  <div class="row-actions">
                    <button class="btn btn--sm btn--icon" data-edit-row="${i}" aria-label="Edit baris">${icon('edit', { size: 13 })}</button>
                    <button class="btn btn--sm btn--icon btn--danger" data-delete-row="${i}" aria-label="Hapus baris">${icon('trash', { size: 13 })}</button>
                  </div>
                </td>
              </tr>`;
            })
            .join('')}
        </tbody>
      </table>
    </div>
  `;

  holder.querySelectorAll('[data-edit-row]').forEach((btn) => {
    btn.addEventListener('click', () => openEditRowModal(rows[Number(btn.dataset.editRow)]));
  });
  holder.querySelectorAll('[data-delete-row]').forEach((btn) => {
    btn.addEventListener('click', () => openDeleteRowModal(rows[Number(btn.dataset.deleteRow)]));
  });
}

/* ---- Tab: Struktur ------------------------------------------------------ */

function renderStructureTab(container) {
  if (!ctx.structure.length) {
    container.innerHTML = `
      <div class="empty-state">
        ${icon('columns', { size: 28 })}
        <h3>Tidak ada informasi kolom</h3>
        <p>Backend tidak mengembalikan data struktur untuk tabel ini.</p>
      </div>`;
    return;
  }
  const keys = Array.from(ctx.structure.reduce((set, c) => { Object.keys(c).forEach((k) => set.add(k)); return set; }, new Set()));

  container.innerHTML = `
    <div class="table-scroll">
      <table class="data-grid structure-table">
        <thead>
          <tr>${keys.map((k) => `<th>${escapeHtml(k)}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${ctx.structure
            .map(
              (col) =>
                `<tr>${keys
                  .map((k) => {
                    const v = col[k];
                    const { text, isNull } = formatCellValue(v);
                    return `<td class="${isNull ? 'cell-null' : ''}">${escapeHtml(text)}</td>`;
                  })
                  .join('')}</tr>`
            )
            .join('')}
        </tbody>
      </table>
    </div>
  `;
}

/* ---- Tab: Insert Row ----------------------------------------------------- */

function renderInsertTab(container) {
  if (!ctx.structure.length) {
    container.innerHTML = `
      <div class="empty-state">
        ${icon('plus', { size: 28 })}
        <h3>Struktur kolom tidak tersedia</h3>
        <p>Tidak bisa membuat form otomatis tanpa data struktur tabel.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <p class="text-secondary" style="font-size:12.5px;margin-bottom:14px">Isi nilai untuk baris baru. Kosongkan field yang ingin diisi NULL / default.</p>
    <form id="insert-form">
      ${ctx.structure
        .map((col) => {
          const name = col.name || '';
          const type = col.type || '';
          const kind = inputTypeForSqlType(type);
          if (kind === 'checkbox') {
            return `
              <div class="field">
                <label>${escapeHtml(name)} <span class="text-tertiary">(${escapeHtml(type)})</span></label>
                <div class="checkbox-row"><input type="checkbox" id="${safeId('ins', name)}" name="${escapeHtml(name)}"><span class="text-secondary" style="font-size:12.5px">true / false</span></div>
              </div>`;
          }
          return `
            <div class="field">
              <label for="${safeId('ins', name)}">${escapeHtml(name)} <span class="text-tertiary">(${escapeHtml(type)})</span></label>
              <input type="${kind}" id="${safeId('ins', name)}" name="${escapeHtml(name)}" placeholder="${escapeHtml(type)}">
            </div>`;
        })
        .join('')}
      <div id="insert-error"></div>
      <button type="submit" class="btn btn--primary mt-16">${icon('plus', { size: 14 })} Insert baris</button>
    </form>
  `;

  container.querySelector('#insert-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const data = {};
    ctx.structure.forEach((col) => {
      const name = col.name || '';
      if (!name) return;
      const kind = inputTypeForSqlType(col.type || '');
      const input = container.querySelector('#' + safeId('ins', name));
      if (kind === 'checkbox') {
        data[name] = input.checked;
      } else {
        const raw = input.value;
        if (raw !== '') data[name] = coerceValueBySqlType(raw, col.type || '');
      }
    });

    const errorBox = container.querySelector('#insert-error');
    try {
      const res = await TableAPI.insertRow(ctx.dbName, ctx.activeTable, data);
      toastSuccess(res?.message || 'Baris berhasil ditambahkan.');
      const form = container.querySelector('#insert-form');
      form.reset();
      ctx.content = await TableAPI.getTableContent(ctx.dbName, ctx.activeTable, ctx.limit);
    } catch (err) {
      errorBox.innerHTML = `<div class="form-error mt-8">${icon('alert', { size: 14 })}${escapeHtml(err.message)}</div>`;
    }
  });
}

/* ---- Tab: Tambah Kolom ---------------------------------------------------- */

function renderAddColumnTab(container) {
  container.innerHTML = `
    <p class="text-secondary" style="font-size:12.5px;margin-bottom:14px">Menambah kolom baru ke tabel yang sudah ada (ALTER TABLE). Tipe kolom ditulis sebagai tipe SQL mentah.</p>
    <form id="addcol-form">
      <div class="field-row">
        <div class="field" style="margin:0">
          <label for="addcol-name">Nama kolom</label>
          <input type="text" id="addcol-name" placeholder="mis. deskripsi" required>
        </div>
        <div class="field" style="margin:0">
          <label for="addcol-type">Tipe SQL</label>
          <input type="text" id="addcol-type" placeholder="mis. VARCHAR(255)" required>
        </div>
      </div>
      <div id="addcol-error"></div>
      <button type="submit" class="btn btn--primary mt-16">${icon('layers', { size: 14 })} Tambah kolom</button>
    </form>
  `;

  container.querySelector('#addcol-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = container.querySelector('#addcol-name').value.trim();
    const type = container.querySelector('#addcol-type').value.trim();
    const errorBox = container.querySelector('#addcol-error');
    try {
      const res = await TableAPI.addColumn(ctx.dbName, ctx.activeTable, name, type);
      toastSuccess(res?.message || `Kolom "${name}" ditambahkan.`);
      const structureRes = await TableAPI.getTableStructure(ctx.dbName, ctx.activeTable);
      ctx.structure = structureRes?.columns || [];
      container.querySelector('#addcol-form').reset();
    } catch (err) {
      errorBox.innerHTML = `<div class="form-error mt-8">${icon('alert', { size: 14 })}${escapeHtml(err.message)}</div>`;
    }
  });
}

/* ---- Tab: Danger Zone (clear / drop table) --------------------------------- */

function renderDangerTab(container) {
  container.innerHTML = `
    <div class="list">
      <div class="list-row" style="align-items:center">
        <div class="list-row__main">
          <div>
            <div style="font-weight:700;font-size:13px">Kosongkan seluruh data</div>
            <div class="text-secondary" style="font-size:12px">Menghapus semua baris, struktur tabel tetap ada.</div>
          </div>
        </div>
        <button class="btn btn--danger" id="clear-table-btn">${icon('trash', { size: 14 })} Clear table</button>
      </div>
      <div class="list-row" style="align-items:center">
        <div class="list-row__main">
          <div>
            <div style="font-weight:700;font-size:13px">Hapus tabel secara permanen</div>
            <div class="text-secondary" style="font-size:12px">Struktur dan seluruh data hilang. Tidak dapat dibatalkan.</div>
          </div>
        </div>
        <button class="btn btn--danger-solid" id="drop-table-btn">${icon('trash', { size: 14 })} Drop table</button>
      </div>
    </div>
  `;

  container.querySelector('#clear-table-btn').addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: `Kosongkan "${ctx.activeTable}"?`,
      message: `Semua baris pada tabel <b>${escapeHtml(ctx.activeTable)}</b> akan dihapus. Struktur kolom tidak berubah.`,
      confirmLabel: 'Ya, kosongkan',
      danger: true,
    });
    if (!ok) return;
    try {
      const res = await TableAPI.clearTable(ctx.dbName, ctx.activeTable);
      toastSuccess(res?.message || 'Tabel dikosongkan.');
      ctx.content = await TableAPI.getTableContent(ctx.dbName, ctx.activeTable, ctx.limit);
      if (ctx.activeTab === 'data') renderTabContent();
    } catch (err) {
      toastApiError(err);
    }
  });

  container.querySelector('#drop-table-btn').addEventListener('click', async () => {
    const ok = await confirmDialog({
      title: `Hapus tabel "${ctx.activeTable}" secara permanen?`,
      message: `Tabel <b>${escapeHtml(ctx.activeTable)}</b> beserta seluruh datanya akan hilang selamanya.`,
      confirmLabel: 'Hapus permanen',
      danger: true,
      requireText: ctx.activeTable,
    });
    if (!ok) return;
    try {
      const res = await TableAPI.dropTable(ctx.dbName, ctx.activeTable);
      toastSuccess(res?.message || 'Tabel dihapus.');
      const listRes = await TableAPI.listTables(ctx.dbName);
      ctx.tables = listRes?.tables || [];
      ctx.activeTable = null;
      setState({ activeTable: null });
      renderSplit();
    } catch (err) {
      toastApiError(err);
    }
  });
}

/* =========================================================================
   4) MODALS
   ========================================================================= */

/** Modal: buat tabel baru dengan definisi kolom dinamis. */
function openCreateTableModal() {
  let rowCount = 0;
  const makeColumnRow = (name = '', type = '', index = '') => {
    rowCount += 1;
    const id = rowCount;
    return `
      <div class="key-value-row" data-col-row="${id}">
        <input type="text" placeholder="nama_kolom" value="${escapeHtml(name)}" data-col-name>
        <input type="text" placeholder="tipe SQL, mis. VARCHAR(100)" value="${escapeHtml(type)}" data-col-type>
        <select data-col-index>
          ${TableAPI.INDEX_TYPES.map((v) => `<option value="${v}" ${v === index ? 'selected' : ''}>${v || '(tidak ada)'}</option>`).join('')}
        </select>
      </div>`;
  };

  openModal({
    title: 'Buat tabel baru',
    subtitle: `Database: ${ctx.dbName} — kolom bernama "id" otomatis jadi Primary Key`,
    wide: true,
    bodyHtml: `
      <div class="field">
        <label for="new-table-name">Nama tabel</label>
        <input type="text" id="new-table-name" placeholder="mis. produk">
      </div>
      <div class="field">
        <label>Kolom</label>
        <div id="col-rows">${makeColumnRow('id', 'INTEGER', 'primary')}${makeColumnRow('nama', 'VARCHAR(100)')}</div>
        <button type="button" class="link-btn mt-8" id="add-col-row">+ Tambah baris kolom</button>
      </div>
      <div id="create-table-error"></div>
    `,
    footerHtml: `
      <button class="btn" data-close>Batal</button>
      <button class="btn btn--primary" id="create-table-submit">${icon('plus', { size: 14 })} Buat tabel</button>
    `,
    onMount: (modalEl) => {
      modalEl.querySelector('#add-col-row').addEventListener('click', () => {
        modalEl.querySelector('#col-rows').insertAdjacentHTML('beforeend', makeColumnRow());
      });

      modalEl.querySelector('#create-table-submit').addEventListener('click', async () => {
        const tableName = modalEl.querySelector('#new-table-name').value.trim();
        const errorBox = modalEl.querySelector('#create-table-error');
        const columnsDef = {};
        modalEl.querySelectorAll('[data-col-row]').forEach((row) => {
          const name = row.querySelector('[data-col-name]').value.trim();
          const type = row.querySelector('[data-col-type]').value.trim();
          const index = row.querySelector('[data-col-index]').value;
          if (name && type) columnsDef[name] = { type, index };
        });

        if (!tableName || !Object.keys(columnsDef).length) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}Nama tabel dan minimal satu kolom wajib diisi.</div>`;
          return;
        }

        try {
          const res = await TableAPI.createTable(ctx.dbName, tableName, columnsDef);
          toastSuccess(res?.message || `Tabel "${tableName}" berhasil dibuat.`);
          closeModal();
          const listRes = await TableAPI.listTables(ctx.dbName);
          ctx.tables = listRes?.tables || [];
          ctx.activeTable = tableName;
          setState({ activeTable: tableName });
          renderSplit();
        } catch (err) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}${escapeHtml(err.message)}</div>`;
        }
      });
    },
  });
}

/** Membangun condition_str + condition_params dari sebuah baris data,
 *  memakai kolom primary key jika terdeteksi, atau seluruh kolom jika tidak. */
function buildConditionFromRow(row) {
  const pkCols = primaryKeyColumns();
  const cols = pkCols.length ? pkCols : Object.keys(row);
  const conditionParams = {};
  const parts = cols.map((c, i) => {
    const paramName = `p${i}_${c}`.replace(/[^a-zA-Z0-9_]/g, '_');
    conditionParams[paramName] = row[c];
    return `${c} = :${paramName}`;
  });
  return { conditionStr: parts.join(' AND '), conditionParams, usedAllColumns: !pkCols.length };
}

/** Modal: edit baris (PUT /table/update). */
function openEditRowModal(row) {
  const { conditionStr, conditionParams, usedAllColumns } = buildConditionFromRow(row);
  const columns = ctx.structure.length ? ctx.structure : Object.keys(row).map((name) => ({ name, type: '' }));

  openModal({
    title: `Edit baris`,
    subtitle: `Tabel: ${ctx.activeTable}`,
    wide: true,
    bodyHtml: `
      ${
        usedAllColumns
          ? `<div class="form-error" style="margin-bottom:14px">${icon('alert', { size: 14 })}Tidak ada kolom primary key terdeteksi — kondisi WHERE memakai semua kolom asli baris ini. Periksa kembali sebelum menyimpan.</div>`
          : ''
      }
      <form id="edit-row-form">
        ${columns
          .map((col) => {
            const name = col.name || '';
            if (!name) return '';
            const type = col.type || '';
            const kind = inputTypeForSqlType(type);
            const currentValue = row[name];
            if (kind === 'checkbox') {
              return `
                <div class="field">
                  <label>${escapeHtml(name)} <span class="text-tertiary">(${escapeHtml(type)})</span></label>
                  <div class="checkbox-row"><input type="checkbox" id="${safeId('edit', name)}" ${currentValue ? 'checked' : ''}><span class="text-secondary" style="font-size:12.5px">true / false</span></div>
                </div>`;
            }
            const displayValue = currentValue === null || currentValue === undefined ? '' : currentValue;
            return `
              <div class="field">
                <label for="${safeId('edit', name)}">${escapeHtml(name)} <span class="text-tertiary">(${escapeHtml(type)})</span></label>
                <input type="${kind === 'number' ? 'text' : kind}" id="${safeId('edit', name)}" value="${escapeHtml(displayValue)}">
              </div>`;
          })
          .join('')}
      </form>
      <div class="divider mt-16"></div>
      <div class="field">
        <label>Kondisi WHERE (bisa diedit)</label>
        <input type="text" id="edit-condition-str" value="${escapeHtml(conditionStr)}">
        <span class="hint">Gunakan placeholder <code>:nama</code>, cocokkan dengan parameter di bawah.</span>
      </div>
      <div class="field">
        <label>Parameter kondisi (JSON)</label>
        <textarea id="edit-condition-params" rows="3">${escapeHtml(JSON.stringify(conditionParams, null, 2))}</textarea>
      </div>
      <div id="edit-row-error"></div>
    `,
    footerHtml: `
      <button class="btn" data-close>Batal</button>
      <button class="btn btn--primary" id="edit-row-submit">${icon('check', { size: 14 })} Simpan perubahan</button>
    `,
    onMount: (modalEl) => {
      modalEl.querySelector('#edit-row-submit').addEventListener('click', async () => {
        const errorBox = modalEl.querySelector('#edit-row-error');
        const updateValues = {};
        columns.forEach((col) => {
          const name = col.name || '';
          if (!name) return;
          const kind = inputTypeForSqlType(col.type || '');
          const input = modalEl.querySelector('#' + safeId('edit', name));
          if (kind === 'checkbox') {
            updateValues[name] = input.checked;
          } else {
            updateValues[name] = coerceValueBySqlType(input.value, col.type || '');
          }
        });

        const conditionStrVal = modalEl.querySelector('#edit-condition-str').value.trim();
        let conditionParamsVal;
        try {
          conditionParamsVal = JSON.parse(modalEl.querySelector('#edit-condition-params').value || '{}');
        } catch {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}Parameter kondisi harus berupa JSON yang valid.</div>`;
          return;
        }

        if (!conditionStrVal) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}Kondisi WHERE tidak boleh kosong (mencegah update seluruh tabel).</div>`;
          return;
        }

        try {
          const res = await TableAPI.updateRow(ctx.dbName, ctx.activeTable, updateValues, conditionStrVal, conditionParamsVal);
          toastSuccess(res?.message || 'Baris berhasil diperbarui.');
          closeModal();
          ctx.content = await TableAPI.getTableContent(ctx.dbName, ctx.activeTable, ctx.limit);
          if (ctx.activeTab === 'data') renderTabContent();
        } catch (err) {
          errorBox.innerHTML = `<div class="form-error">${icon('alert', { size: 14 })}${escapeHtml(err.message)}</div>`;
        }
      });
    },
  });
}

/** Modal konfirmasi: hapus satu baris (DELETE /table/row). */
async function openDeleteRowModal(row) {
  const { conditionStr, conditionParams } = buildConditionFromRow(row);
  const preview = escapeHtml(JSON.stringify(row));

  const ok = await confirmDialog({
    title: 'Hapus baris ini?',
    message: `Baris dengan data <code class="mono" style="font-size:11.5px">${preview.length > 140 ? preview.slice(0, 140) + '…' : preview}</code> akan dihapus permanen dari tabel <b>${escapeHtml(ctx.activeTable)}</b>.`,
    confirmLabel: 'Hapus baris',
    danger: true,
  });
  if (!ok) return;

  try {
    const res = await TableAPI.deleteRow(ctx.dbName, ctx.activeTable, conditionStr, conditionParams);
    toastSuccess(res?.message || 'Baris berhasil dihapus.');
    ctx.content = await TableAPI.getTableContent(ctx.dbName, ctx.activeTable, ctx.limit);
    if (ctx.activeTab === 'data') renderTabContent();
  } catch (err) {
    toastApiError(err);
  }
}
