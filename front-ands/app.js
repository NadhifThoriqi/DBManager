/**
 * app.js — NovDB Application Logic
 * Vanilla JS, no framework, no dependencies.
 */

/* ============================================================
   STATE
   ============================================================ */
const State = {
  currentView: 'dashboard',
  currentTable: null,
  tableColumns: [],
  tableData: [],
  page: 1,
  pageSize: parseInt(localStorage.getItem('novdb_pagesize') || '25', 10),
  totalRows: 0,
  totalPages: 1,
  search: '',
  sortCol: '',
  sortOrder: 'asc',
  tables: [],            // [{name, row_count}]
  confirmCallback: null,
  editingId: null,
};

/* ============================================================
   DOM HELPERS
   ============================================================ */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

function el(tag, cls, html = '') {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html) e.innerHTML = html;
  return e;
}

/* ============================================================
   TOAST NOTIFICATIONS
   ============================================================ */
const Toast = {
  icons: { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' },
  titles: { success: 'Berhasil', error: 'Error', warning: 'Peringatan', info: 'Info' },

  show(type = 'info', message = '', title = '') {
    const container = $('#toastContainer');
    const t = el('div', `toast toast-${type}`);
    t.innerHTML = `
      <span class="toast-icon">${this.icons[type]}</span>
      <div class="toast-content">
        <div class="toast-title">${title || this.titles[type]}</div>
        <div class="toast-msg">${message}</div>
      </div>
      <button class="toast-close" aria-label="Tutup">✕</button>`;

    container.appendChild(t);

    // Close on button
    t.querySelector('.toast-close').onclick = () => this._remove(t);

    // Auto remove
    setTimeout(() => this._remove(t), 5000);
  },

  _remove(t) {
    if (!t.parentNode) return;
    t.classList.add('removing');
    setTimeout(() => t.remove(), 260);
  },

  success(msg, title) { this.show('success', msg, title); },
  error(msg, title)   { this.show('error',   msg, title); },
  warning(msg, title) { this.show('warning', msg, title); },
  info(msg, title)    { this.show('info',    msg, title); },
};

/* ============================================================
   CONFIRM DIALOG
   ============================================================ */
function showConfirm(message, onOk, title = 'Konfirmasi Hapus') {
  $('#confirmTitle').textContent = title;
  $('#confirmMessage').textContent = message;
  $('#confirmBackdrop').classList.remove('hidden');
  State.confirmCallback = onOk;
}

function closeConfirm() {
  $('#confirmBackdrop').classList.add('hidden');
  State.confirmCallback = null;
}

/* ============================================================
   MODAL
   ============================================================ */
const Modal = {
  open(title, bodyHTML, onConfirm, confirmLabel = 'Simpan') {
    $('#modalTitle').textContent = title;
    $('#modalBody').innerHTML = bodyHTML;
    $('#modalConfirmBtn').textContent = confirmLabel;
    $('#modalConfirmBtn').onclick = onConfirm;
    $('#modalBackdrop').classList.remove('hidden');
  },
  close() {
    $('#modalBackdrop').classList.add('hidden');
    $('#modalBody').innerHTML = '';
  },
  setLoading(loading) {
    const btn = $('#modalConfirmBtn');
    if (loading) {
      btn.disabled = true;
      btn.innerHTML = '<span class="spinner"></span> Menyimpan…';
    } else {
      btn.disabled = false;
      btn.textContent = 'Simpan';
    }
  },
};

/* ============================================================
   THEME
   ============================================================ */
function initTheme() {
  const saved = localStorage.getItem('novdb_theme') || 'dark';
  applyTheme(saved);
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('novdb_theme', theme);
  $('#themeIcon').textContent = theme === 'dark' ? '◑' : '◐';
  // Settings page buttons
  $$('.theme-opt').forEach(b => {
    b.classList.toggle('active', b.dataset.themeOpt === theme);
  });
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  applyTheme(current === 'dark' ? 'light' : 'dark');
}

/* ============================================================
   VIEW NAVIGATION
   ============================================================ */
function navigateTo(view) {
  // Hide all views
  $$('.view').forEach(v => v.classList.add('hidden'));
  const target = $(`#view-${view}`);
  if (!target) return;
  target.classList.remove('hidden');

  // Update nav
  $$('.nav-item').forEach(a => {
    a.classList.toggle('active', a.dataset.view === view);
  });

  State.currentView = view;

  // Trigger view-specific load
  if (view === 'dashboard') loadDashboard();
  if (view === 'settings') loadSettingsPage();
}

/* ============================================================
   API STATUS
   ============================================================ */
async function checkApiStatus() {
  const dot = $('#statusDot');
  const txt = $('#statusText');
  dot.className = 'status-dot connecting';
  txt.textContent = 'Menghubungkan…';

  const result = await API.healthCheck();
  if (result.ok) {
    dot.className = 'status-dot online';
    txt.textContent = 'API Terhubung';
  } else {
    dot.className = 'status-dot offline';
    txt.textContent = 'API Offline';
  }
  return result.ok;
}

/* ============================================================
   DASHBOARD
   ============================================================ */
async function loadDashboard() {
  renderStatsSkeleton();
  renderTableOverviewSkeleton();

  // Load tables
  try {
    const raw = await API.getTables();
    State.tables = normalizeTables(raw);
    renderStats();
    renderTableOverviewGrid();
    renderExplorerTree();
  } catch (err) {
    renderStatsError();
    renderTableOverviewError(err.message);
  }
}

function normalizeTables(raw) {
  // Accept: string[], {name, row_count}[], {tables:[...]}
  if (!raw) return [];
  const list = Array.isArray(raw) ? raw : (raw.tables || []);
  return list.map(t => {
    if (typeof t === 'string') return { name: t, row_count: null };
    return { name: t.name || t.table_name || t, row_count: t.row_count ?? t.rows ?? null };
  });
}

function renderStatsSkeleton() {
  const grid = $('#statsGrid');
  grid.innerHTML = Array(4).fill(0).map(() => `
    <div class="stat-card skeleton-card">
      <div class="skeleton sk-label"></div>
      <div class="skeleton sk-value"></div>
    </div>`).join('');
}

function renderStats() {
  const stats = [
    { icon: '⊙', label: 'Total Database', value: '1', cls: 'c-info' },
    { icon: '⊟', label: 'Total Tables', value: State.tables.length, cls: '' },
    {
      icon: '≡',
      label: 'Total Records',
      value: State.tables.reduce((s, t) => s + (t.row_count || 0), 0),
      cls: 'c-success'
    },
    { icon: '⊕', label: 'API Status', value: 'Online', cls: 'c-success' },
  ];

  $('#statsGrid').innerHTML = stats.map(s => `
    <div class="stat-card ${s.cls}">
      <span class="stat-icon">${s.icon}</span>
      <div class="stat-value">${typeof s.value === 'number' ? s.value.toLocaleString() : s.value}</div>
      <div class="stat-label">${s.label}</div>
    </div>`).join('');
}

function renderStatsError() {
  $('#statsGrid').innerHTML = `
    <div class="stat-card c-error" style="grid-column:1/-1">
      <div class="stat-icon">⊖</div>
      <div class="stat-value" style="font-size:1rem">—</div>
      <div class="stat-label">Gagal memuat statistik</div>
    </div>`;
}

function renderTableOverviewSkeleton() {
  const grid = $('#tableOverviewGrid');
  grid.innerHTML = Array(6).fill(0).map(() => `
    <div class="skeleton" style="height:80px;border-radius:10px"></div>`).join('');
}

function renderTableOverviewGrid() {
  const grid = $('#tableOverviewGrid');
  const badge = $('#tableCountBadge');
  badge.textContent = State.tables.length;

  if (State.tables.length === 0) {
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">⊙</div><p>Tidak ada tabel ditemukan.</p></div>`;
    return;
  }

  grid.innerHTML = State.tables.map(t => `
    <div class="table-card" data-table="${esc(t.name)}" role="button" tabindex="0">
      <div class="table-card-name">⊟ ${esc(t.name)}</div>
      <div class="table-card-meta">${t.row_count !== null ? `${t.row_count.toLocaleString()} rows` : 'rows: —'}</div>
    </div>`).join('');

  grid.querySelectorAll('.table-card').forEach(card => {
    card.onclick = () => openTable(card.dataset.table);
    card.onkeydown = e => { if (e.key === 'Enter') openTable(card.dataset.table); };
  });
}

function renderTableOverviewError(msg) {
  $('#tableOverviewGrid').innerHTML = `
    <div class="error-state" style="grid-column:1/-1">
      <div class="error-icon">⊖</div>
      <strong>Gagal memuat tabel</strong>
      <p>${esc(msg)}</p>
    </div>`;
}

/* ============================================================
   EXPLORER TREE (Sidebar)
   ============================================================ */
function renderExplorerTree() {
  const tree = $('#explorerTree');

  if (State.tables.length === 0) {
    tree.innerHTML = `<div style="padding:8px 12px;font-size:0.78rem;color:var(--text-muted)">Tidak ada tabel.</div>`;
    return;
  }

  // Satu "database" (bisa dikembangkan untuk multi-db)
  const dbName = 'database';
  tree.innerHTML = `
    <div class="tree-db open" id="treeDb">
      <div class="tree-db-header" id="treeDbHeader">
        <span class="tree-db-icon">⊙</span>
        <span>${esc(dbName)}</span>
        <span class="tree-toggle">▶</span>
      </div>
      <div class="tree-tables" id="treeTables">
        ${State.tables.map(t => `
          <div class="tree-table-item ${State.currentTable === t.name ? 'active' : ''}"
               data-table="${esc(t.name)}" role="button" tabindex="0">
            <span class="tree-table-icon">⊟</span>
            <span>${esc(t.name)}</span>
          </div>`).join('')}
      </div>
    </div>`;

  // Toggle collapse
  $('#treeDbHeader').onclick = () => {
    const db = $('#treeDb');
    db.classList.toggle('open');
  };

  // Click table
  tree.querySelectorAll('.tree-table-item').forEach(item => {
    item.onclick = () => openTable(item.dataset.table);
    item.onkeydown = e => { if (e.key === 'Enter') openTable(item.dataset.table); };
  });
}

/* ============================================================
   OPEN TABLE
   ============================================================ */
function openTable(tableName) {
  State.currentTable = tableName;
  State.page = 1;
  State.search = '';
  State.sortCol = '';
  State.sortOrder = 'asc';

  // Update tree active state
  $$('.tree-table-item').forEach(i => {
    i.classList.toggle('active', i.dataset.table === tableName);
  });

  navigateTo('tables');
  loadTableData();
}

/* ============================================================
   TABLE DATA
   ============================================================ */
async function loadTableData() {
  const tableName = State.currentTable;
  if (!tableName) return;

  // Update header
  $('#tableViewTitle').textContent = tableName;
  $('#tableViewSubtitle').textContent = `Menampilkan data dari tabel "${tableName}"`;

  // Reset search input
  $('#tableSearch').value = State.search;

  renderTableSkeleton();

  try {
    const res = await API.getTableData(tableName, {
      page: State.page,
      limit: State.pageSize,
      search: State.search,
      sort: State.sortCol,
      order: State.sortOrder,
    });

    // Normalize response: { data: [], total, page, pages } atau { rows: [], count }
    let rows = [];
    let total = 0;
    let pages = 1;

    if (Array.isArray(res)) {
      rows = res;
      total = res.length;
      pages = 1;
    } else if (res?.data) {
      rows = res.data;
      total = res.total ?? res.count ?? res.data.length;
      pages = res.pages ?? res.total_pages ?? Math.ceil(total / State.pageSize);
    } else if (res?.rows) {
      rows = res.rows;
      total = res.count ?? rows.length;
      pages = Math.ceil(total / State.pageSize);
    }

    State.tableData = rows;
    State.totalRows = total;
    State.totalPages = pages;

    if (rows.length > 0) {
      State.tableColumns = Object.keys(rows[0]);
    }

    renderTable(rows);
    renderPagination();
  } catch (err) {
    $('#tableContainer').innerHTML = `
      <div class="error-state">
        <div class="error-icon">⊖</div>
        <strong>Gagal memuat data</strong>
        <p>${esc(err.message)}</p>
      </div>`;
    $('#pagination').innerHTML = '';
    Toast.error(err.message, 'Gagal memuat tabel');
  }
}

function renderTableSkeleton() {
  const rows = Array(8).fill(0).map(() => `
    <div class="sk-row">
      <div class="skeleton sk-cell narrow"></div>
      <div class="skeleton sk-cell wide"></div>
      <div class="skeleton sk-cell"></div>
      <div class="skeleton sk-cell"></div>
      <div class="skeleton sk-cell narrow"></div>
    </div>`).join('');
  $('#tableContainer').innerHTML = `<div>${rows}</div>`;
}

function renderTable(rows) {
  const container = $('#tableContainer');

  if (!rows || rows.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">⊟</div>
        <p>${State.search ? `Tidak ada hasil untuk "<strong>${esc(State.search)}</strong>"` : 'Tabel ini kosong.'}</p>
      </div>`;
    return;
  }

  const cols = State.tableColumns;

  // TH with sort
  const ths = cols.map(c => {
    const sorted = State.sortCol === c;
    const cls = sorted ? (State.sortOrder === 'asc' ? 'sorted-asc' : 'sorted-desc') : '';
    return `<th class="${cls}" data-col="${esc(c)}">${esc(c)}</th>`;
  }).join('') + '<th class="no-sort">Aksi</th>';

  // Rows
  const trs = rows.map(row => {
    const tds = cols.map(c => {
      const val = row[c];
      return `<td title="${esc(String(val ?? ''))}">${formatCell(c, val)}</td>`;
    }).join('');

    const id = row.id ?? row.ID ?? row[cols[0]];
    return `
      <tr>
        ${tds}
        <td>
          <div class="table-actions">
            <button class="btn-action btn-edit" data-id="${esc(String(id))}" data-row='${esc(JSON.stringify(row))}'>Edit</button>
            <button class="btn-action btn-delete" data-id="${esc(String(id))}">Hapus</button>
          </div>
        </td>
      </tr>`;
  }).join('');

  container.innerHTML = `
    <div class="table-scroll">
      <table>
        <thead><tr>${ths}</tr></thead>
        <tbody>${trs}</tbody>
      </table>
    </div>`;

  // Sort headers
  container.querySelectorAll('th[data-col]').forEach(th => {
    th.onclick = () => {
      if (State.sortCol === th.dataset.col) {
        State.sortOrder = State.sortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        State.sortCol = th.dataset.col;
        State.sortOrder = 'asc';
      }
      State.page = 1;
      loadTableData();
    };
  });

  // Edit / Delete
  container.querySelectorAll('.btn-edit').forEach(btn => {
    btn.onclick = () => {
      try {
        const row = JSON.parse(btn.dataset.row);
        openEditModal(row);
      } catch { Toast.error('Gagal membaca data baris.'); }
    };
  });

  container.querySelectorAll('.btn-delete').forEach(btn => {
    btn.onclick = () => {
      showConfirm(
        `Hapus baris dengan ID "${btn.dataset.id}" dari tabel "${State.currentTable}"? Tindakan ini tidak dapat dibatalkan.`,
        async () => {
          closeConfirm();
          await deleteRecord(btn.dataset.id);
        }
      );
    };
  });
}

function formatCell(col, val) {
  if (val === null || val === undefined) return `<span class="td-null">NULL</span>`;
  if (col === 'id' || col === 'ID') return `<span class="td-id">${esc(String(val))}</span>`;
  if (val === true  || val === 'true')  return `<span class="td-bool-true">true</span>`;
  if (val === false || val === 'false') return `<span class="td-bool-false">false</span>`;

  const str = String(val);

  // Highlight search term
  if (State.search && str.toLowerCase().includes(State.search.toLowerCase())) {
    const rx = new RegExp(`(${escapeRegex(State.search)})`, 'gi');
    return str.replace(rx, '<mark>$1</mark>');
  }

  return esc(str);
}

/* ── Pagination ─────────────────────────────────────────── */
function renderPagination() {
  const pg = $('#pagination');
  const total = State.totalRows;
  const pages = State.totalPages;
  const cur = State.page;

  if (pages <= 1 && total === 0) { pg.innerHTML = ''; return; }

  const start = (cur - 1) * State.pageSize + 1;
  const end   = Math.min(cur * State.pageSize, total);

  // Page buttons: show max 7 buttons
  let pageNums = [];
  if (pages <= 7) {
    pageNums = Array.from({ length: pages }, (_, i) => i + 1);
  } else {
    pageNums = [1];
    if (cur > 3) pageNums.push('…');
    for (let i = Math.max(2, cur - 1); i <= Math.min(pages - 1, cur + 1); i++) {
      pageNums.push(i);
    }
    if (cur < pages - 2) pageNums.push('…');
    pageNums.push(pages);
  }

  const btns = pageNums.map(n => {
    if (n === '…') return `<span class="page-btn" style="border:none;cursor:default">…</span>`;
    return `<button class="page-btn ${n === cur ? 'active' : ''}" data-page="${n}">${n}</button>`;
  }).join('');

  pg.innerHTML = `
    <div class="pagination-info">
      Menampilkan ${total > 0 ? start : 0}–${end} dari ${total.toLocaleString()} baris
    </div>
    <div class="pagination-controls">
      <button class="page-btn" data-page="${cur - 1}" ${cur <= 1 ? 'disabled' : ''}>‹</button>
      ${btns}
      <button class="page-btn" data-page="${cur + 1}" ${cur >= pages ? 'disabled' : ''}>›</button>
    </div>`;

  pg.querySelectorAll('.page-btn[data-page]').forEach(btn => {
    btn.onclick = () => {
      const p = parseInt(btn.dataset.page);
      if (p >= 1 && p <= pages && p !== cur) {
        State.page = p;
        loadTableData();
      }
    };
  });
}

/* ============================================================
   CRUD — Create / Edit / Delete
   ============================================================ */
function openCreateModal() {
  if (!State.currentTable) { Toast.warning('Pilih tabel terlebih dahulu.'); return; }
  State.editingId = null;

  const fields = State.tableColumns
    .filter(c => c !== 'id' && c !== 'ID')
    .map(c => buildFormField(c, ''))
    .join('');

  Modal.open(`Tambah Data — ${State.currentTable}`, fields, async () => {
    const payload = collectFormData();
    if (!validateForm()) return;
    Modal.setLoading(true);
    try {
      await API.createData(State.currentTable, payload);
      Modal.close();
      Toast.success('Data berhasil ditambahkan.');
      loadTableData();
    } catch (err) {
      Modal.setLoading(false);
      Toast.error(err.message, 'Gagal menyimpan');
    }
  });
}

function openEditModal(row) {
  const id = row.id ?? row.ID ?? Object.values(row)[0];
  State.editingId = id;

  const fields = Object.entries(row)
    .filter(([k]) => k !== 'id' && k !== 'ID')
    .map(([k, v]) => buildFormField(k, v ?? ''))
    .join('');

  Modal.open(`Edit Data — ID ${id}`, fields, async () => {
    const payload = collectFormData();
    if (!validateForm()) return;
    Modal.setLoading(true);
    try {
      await API.updateData(State.currentTable, id, payload);
      Modal.close();
      Toast.success('Data berhasil diperbarui.');
      loadTableData();
    } catch (err) {
      Modal.setLoading(false);
      Toast.error(err.message, 'Gagal memperbarui');
    }
  });
}

async function deleteRecord(id) {
  try {
    await API.deleteData(State.currentTable, id);
    Toast.success(`Data ID "${id}" berhasil dihapus.`);
    loadTableData();
  } catch (err) {
    Toast.error(err.message, 'Gagal menghapus');
  }
}

function buildFormField(name, value) {
  return `
    <div class="form-group">
      <label for="field_${esc(name)}">${esc(name)}</label>
      <input
        type="text"
        id="field_${esc(name)}"
        name="${esc(name)}"
        class="form-input"
        value="${esc(String(value))}"
        autocomplete="off"
        data-required="true"
      />
      <span class="field-error" id="err_${esc(name)}">Field ini wajib diisi.</span>
    </div>`;
}

function collectFormData() {
  const inputs = $$('#modalBody .form-input');
  const data = {};
  inputs.forEach(inp => {
    const val = inp.value.trim();
    // Try to preserve numbers/booleans
    if (val === 'true') data[inp.name] = true;
    else if (val === 'false') data[inp.name] = false;
    else if (val !== '' && !isNaN(Number(val))) data[inp.name] = Number(val);
    else data[inp.name] = val;
  });
  return data;
}

function validateForm() {
  let valid = true;
  $$('#modalBody .form-input[data-required="true"]').forEach(inp => {
    const err = $(`#err_${inp.name}`);
    if (inp.value.trim() === '') {
      inp.classList.add('error');
      if (err) err.classList.add('visible');
      valid = false;
    } else {
      inp.classList.remove('error');
      if (err) err.classList.remove('visible');
    }
  });
  return valid;
}

/* ============================================================
   QUERY BUILDER
   ============================================================ */
async function executeQuery() {
  const textarea = $('#queryTextarea');
  const query = textarea.value.trim();
  if (!query) { Toast.warning('Tulis query SQL terlebih dahulu.'); return; }

  const btn = $('#executeQueryBtn');
  const label = $('#executeLabel');
  btn.disabled = true;
  label.innerHTML = '<span class="spinner"></span> Running…';

  const wrap = $('#queryResultWrap');
  wrap.innerHTML = `<div class="empty-state"><span class="spinner"></span></div>`;

  const t0 = performance.now();
  try {
    const res = await API.executeQuery(query);
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);

    // Normalize: { rows: [], columns: [], affected_rows: N }
    let rows = res?.rows ?? res?.data ?? (Array.isArray(res) ? res : null);
    const affected = res?.affected_rows ?? res?.rowCount ?? null;

    if (rows && rows.length > 0) {
      renderQueryResult(rows, elapsed, res);
    } else if (affected !== null) {
      wrap.innerHTML = `
        <div class="query-result-header">
          <span>Query berhasil dijalankan</span>
          <span class="query-time">${elapsed}s</span>
        </div>
        <div class="empty-state">
          <div class="empty-icon">✓</div>
          <p>${affected} baris terpengaruh.</p>
        </div>`;
      Toast.success(`${affected} baris terpengaruh — ${elapsed}s`);
    } else {
      wrap.innerHTML = `
        <div class="query-result-header"><span>Hasil</span><span class="query-time">${elapsed}s</span></div>
        <div class="empty-state"><div class="empty-icon">⊙</div><p>Query berhasil. Tidak ada baris dikembalikan.</p></div>`;
      Toast.success(`Query berhasil — ${elapsed}s`);
    }
  } catch (err) {
    const elapsed = ((performance.now() - t0) / 1000).toFixed(3);
    wrap.innerHTML = `
      <div class="query-result-header" style="border-left:3px solid var(--error)">
        <span style="color:var(--error)">Error</span>
        <span class="query-time">${elapsed}s</span>
      </div>
      <div class="query-error"><strong>ERROR:</strong> ${esc(err.message)}</div>`;
    Toast.error(err.message, 'Query gagal');
  } finally {
    btn.disabled = false;
    label.textContent = '⊳ Execute';
  }
}

function renderQueryResult(rows, elapsed, meta) {
  const cols = Object.keys(rows[0]);
  const ths = cols.map(c => `<th>${esc(c)}</th>`).join('');
  const trs = rows.map(row =>
    `<tr>${cols.map(c => `<td>${formatCell(c, row[c])}</td>`).join('')}</tr>`
  ).join('');

  const affectedNote = (meta?.affected_rows != null)
    ? ` — ${meta.affected_rows} baris terpengaruh` : '';

  $('#queryResultWrap').innerHTML = `
    <div class="query-result-header">
      <span>${rows.length.toLocaleString()} baris${affectedNote}</span>
      <span class="query-time">${elapsed}s</span>
    </div>
    <div class="query-result-body">
      <table><thead><tr>${ths}</tr></thead><tbody>${trs}</tbody></table>
    </div>`;
}

/* ── Line numbers for textarea ────────────────────────────── */
function updateLineNumbers() {
  const textarea = $('#queryTextarea');
  const lines = textarea.value.split('\n').length;
  $('#queryLineNumbers').textContent = Array.from({ length: lines }, (_, i) => i + 1).join('\n');
}

/* ============================================================
   SETTINGS PAGE
   ============================================================ */
function loadSettingsPage() {
  $('#settingApiUrl').value = API.getBaseUrl();
  $('#settingTimeout').value = API.getTimeout();
  $('#settingPageSize').value = State.pageSize;
  $$('.theme-opt').forEach(b => {
    b.classList.toggle('active', b.dataset.themeOpt === (localStorage.getItem('novdb_theme') || 'dark'));
  });
}

/* ============================================================
   SEARCH (global & table)
   ============================================================ */
let searchDebounce;
function handleGlobalSearch(query) {
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    // Filter tree items
    const q = query.toLowerCase();
    $$('.tree-table-item').forEach(item => {
      const match = item.textContent.toLowerCase().includes(q);
      item.style.display = (!q || match) ? '' : 'none';
    });
  }, 200);
}

let tableSearchDebounce;
function handleTableSearch(query) {
  clearTimeout(tableSearchDebounce);
  tableSearchDebounce = setTimeout(() => {
    State.search = query;
    State.page = 1;
    loadTableData();
  }, 350);
}

/* ============================================================
   UTILITIES
   ============================================================ */
function esc(str) {
  if (typeof str !== 'string') str = String(str ?? '');
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function setRefreshRotating(on) {
  const btn = $('#refreshAll');
  btn.classList.toggle('rotate', on);
}

/* ============================================================
   INIT — Wire up all event listeners
   ============================================================ */
function init() {
  initTheme();

  // ── Theme toggle ────────────────────────────────────────
  $('#themeToggle').onclick = toggleTheme;

  // ── Nav items ───────────────────────────────────────────
  $$('.nav-item').forEach(a => {
    a.onclick = e => {
      e.preventDefault();
      navigateTo(a.dataset.view);
      // Close sidebar on mobile
      if (window.innerWidth <= 900) closeSidebar();
    };
  });

  // ── Sidebar mobile toggle ───────────────────────────────
  $('#hamburger').onclick = openSidebar;
  $('#sidebarClose').onclick = closeSidebar;
  $('#overlay').onclick = closeSidebar;

  // ── Global search ────────────────────────────────────────
  $('#globalSearch').addEventListener('input', e => handleGlobalSearch(e.target.value));

  // ── Refresh all ──────────────────────────────────────────
  $('#refreshAll').onclick = async () => {
    setRefreshRotating(true);
    await loadDashboard();
    if (State.currentTable) await loadTableData();
    await checkApiStatus();
    setRefreshRotating(false);
    Toast.info('Data berhasil diperbarui.');
  };

  // ── Refresh tables (sidebar) ─────────────────────────────
  $('#refreshTables').onclick = async () => {
    const btn = $('#refreshTables');
    btn.classList.add('rotate');
    const raw = await API.getTables().catch(() => []);
    State.tables = normalizeTables(raw);
    renderExplorerTree();
    renderTableOverviewGrid();
    btn.classList.remove('rotate');
  };

  // ── User menu ────────────────────────────────────────────
  $('#userMenu').onclick = e => {
    e.stopPropagation();
    $('#userDropdown').classList.toggle('open');
  };
  document.addEventListener('click', () => $('#userDropdown').classList.remove('open'));

  document.querySelectorAll('[data-view]').forEach(el => {
    if (!el.classList.contains('nav-item')) {
      el.addEventListener('click', e => {
        e.preventDefault();
        const view = el.dataset.view;
        if (view) navigateTo(view);
      });
    }
  });

  // ── Table view buttons ───────────────────────────────────
  $('#addRecordBtn').onclick = openCreateModal;
  $('#refreshTableBtn').onclick = () => loadTableData();
  $('#tableSearch').addEventListener('input', e => handleTableSearch(e.target.value));

  // ── Modal ────────────────────────────────────────────────
  $('#modalClose').onclick = Modal.close;
  $('#modalCancelBtn').onclick = Modal.close;
  $('#modalBackdrop').onclick = e => { if (e.target === $('#modalBackdrop')) Modal.close(); };

  // ── Confirm dialog ───────────────────────────────────────
  $('#confirmClose').onclick = closeConfirm;
  $('#confirmCancelBtn').onclick = closeConfirm;
  $('#confirmOkBtn').onclick = () => { if (State.confirmCallback) State.confirmCallback(); };
  $('#confirmBackdrop').onclick = e => { if (e.target === $('#confirmBackdrop')) closeConfirm(); };

  // ── Query builder ─────────────────────────────────────────
  $('#executeQueryBtn').onclick = executeQuery;
  $('#clearQueryBtn').onclick = () => {
    $('#queryTextarea').value = '';
    $('#queryResultWrap').innerHTML = `
      <div class="empty-state"><div class="empty-icon">⊳</div><p>Tulis query dan klik Execute untuk melihat hasil.</p></div>`;
    updateLineNumbers();
  };

  const qt = $('#queryTextarea');
  qt.addEventListener('input', updateLineNumbers);
  qt.addEventListener('keydown', e => {
    // Tab key → insert spaces
    if (e.key === 'Tab') {
      e.preventDefault();
      const start = qt.selectionStart;
      const end   = qt.selectionEnd;
      qt.value = qt.value.substring(0, start) + '  ' + qt.value.substring(end);
      qt.selectionStart = qt.selectionEnd = start + 2;
      updateLineNumbers();
    }
    // Ctrl/Cmd+Enter → execute
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      executeQuery();
    }
  });

  // ── Settings ──────────────────────────────────────────────
  $('#saveSettingsBtn').onclick = () => {
    const url = $('#settingApiUrl').value.trim();
    const timeout = parseInt($('#settingTimeout').value, 10);
    const pageSize = parseInt($('#settingPageSize').value, 10);

    if (!url) { Toast.warning('URL tidak boleh kosong.'); return; }
    if (!timeout || timeout < 1000) { Toast.warning('Timeout minimal 1000ms.'); return; }

    API.setBaseUrl(url);
    API.setTimeout(timeout);
    State.pageSize = pageSize;
    localStorage.setItem('novdb_pagesize', pageSize);

    Toast.success('Pengaturan disimpan. Memuat ulang koneksi…');
    setTimeout(() => { checkApiStatus(); loadDashboard(); }, 400);
  };

  $('#testConnectionBtn').onclick = async () => {
    const btn = $('#testConnectionBtn');
    btn.disabled = true;
    btn.textContent = '⊳ Menguji…';
    const result = await checkApiStatus();
    btn.disabled = false;
    btn.textContent = 'Test Koneksi';
    if (result) Toast.success('Koneksi berhasil!');
    else Toast.error('Tidak dapat terhubung ke API.');
  };

  $$('.theme-opt').forEach(btn => {
    btn.onclick = () => applyTheme(btn.dataset.themeOpt);
  });

  // ── Initial load ──────────────────────────────────────────
  checkApiStatus();
  navigateTo('dashboard');
}

function openSidebar() {
  $('#sidebar').classList.add('open');
  $('#overlay').classList.add('visible');
  document.body.style.overflow = 'hidden';
}

function closeSidebar() {
  $('#sidebar').classList.remove('open');
  $('#overlay').classList.remove('visible');
  document.body.style.overflow = '';
}

// Bootstrap
document.addEventListener('DOMContentLoaded', init);
