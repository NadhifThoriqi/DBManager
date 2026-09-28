/**
 * views/designerView.js — Halaman "Designer" (diagram relasi antar tabel)
 * -----------------------------------------------------------------------
 * Terinspirasi dari fitur "Designer" phpMyAdmin: setiap tabel digambar
 * sebagai kartu berisi daftar kolom, dan kolom yang punya `foreign_key`
 * dihubungkan dengan garis ke kolom yang dirujuk pada tabel lain.
 *
 * Sumber data: POST /table/structure (lihat js/api/table.js), dengan
 * bentuk per tabel:
 *   { table_name, columns: [ { name, type, primary_key, nullable,
 *       autoincrement, default, comment, foreign_key } ] }
 *
 * Data struktur SELALU diambil langsung dari API setiap halaman ini
 * dibuka/di-refresh — tidak ada cache di cookie (dicoba sebelumnya,
 * tapi tidak berguna karena API tetap dipanggil ulang setiap saat).
 *
 * Satu-satunya hal yang disimpan di sisi klien adalah POSISI kartu
 * hasil drag (murni preferensi tampilan, bukan data dari API), lewat
 * localStorage per database supaya diagram tidak berantakan tiap kali
 * dibuka ulang.
 *
 * Interaksi kanvas dibangun dengan Pointer Events (bukan mouse events)
 * sehingga otomatis berfungsi untuk mouse, touch (HP/tablet), dan pen
 * dengan satu set kode yang sama — termasuk pinch-to-zoom 2 jari.
 */

import { showDatabases } from '../api/database.js';
import { listTables, getTableStructure } from '../api/table.js';
import { state, setState } from '../state.js';
import { toastApiError, toastSuccess } from '../ui/toast.js';
import { icon } from '../ui/icons.js';
import { escapeHtml, engineLabel } from '../ui/helpers.js';

const CARD_WIDTH = 236;
const GRID_COL_GAP = 300;
const GRID_ROW_GAP = 240;
const ZOOM_MIN = 0.35;
const ZOOM_MAX = 2.5;
const RELATION_COLORS = ['#4fd1c5', '#f2b84b', '#a9b8ff', '#f2685c', '#6fd08c', '#7dd3fc', '#e39ff6', '#f0a35c'];
const LAYOUT_STORAGE_PREFIX = 'dbmanager.designerLayout.';

const ctx = {
  root: null,
  engine: null,
  dbName: '',
  tableNames: [],
  structures: {}, // { tableName: {table_name, columns} }
  positions: {}, // { tableName: {x, y} }
  zoom: 1,
  pan: { x: 40, y: 30 },
  dragState: null,
  panState: null,
  pinchState: null,
  wrapPointers: new Map(), // pointerId -> {x, y}, dipakai untuk pan 1 jari & pinch 2 jari
};

/* =========================================================================
   Posisi kartu — preferensi tampilan lokal (localStorage, bukan data API)
   ========================================================================= */

function getStoredLayout(dbName) {
  try {
    const raw = localStorage.getItem(LAYOUT_STORAGE_PREFIX + dbName);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveStoredLayout(dbName, positions) {
  try {
    localStorage.setItem(LAYOUT_STORAGE_PREFIX + dbName, JSON.stringify(positions));
  } catch {
    /* localStorage penuh/diblokir — abaikan, layout cukup tidak tersimpan */
  }
}

/* =========================================================================
   BOOTSTRAP — pilih database
   ========================================================================= */

export async function renderDesignerView(root) {
  ctx.root = root;
  ctx.engine = state.session?.db || 'sqlite';
  ctx.dbName = state.activeDbName || '';
  ctx.tableNames = [];
  ctx.structures = {};
  ctx.positions = {};
  ctx.zoom = 1;
  ctx.pan = { x: 40, y: 30 };

  root.innerHTML = `
    <div class="view view--wide">
      <div class="page-head">
        <div>
          <h1>Designer</h1>
          <p>Diagram relasi antar tabel pada engine <span class="badge badge--${ctx.engine}">${engineLabel(ctx.engine)}</span>, dibangun dari <code class="mono">/table/structure</code>.</p>
        </div>
      </div>

      <div class="card">
        <div class="field-row" style="align-items:end">
          <div class="field" style="margin:0">
            <label for="des-db-select">Database</label>
            <select id="des-db-select">
              <option value="">Memuat daftar database…</option>
            </select>
          </div>
          <div class="field" style="margin:0">
            <label for="des-db-manual">Atau ketik nama database manual</label>
            <div class="input-group">
              <input type="text" id="des-db-manual" placeholder="nama_database" value="${escapeHtml(ctx.dbName)}">
              <button class="btn btn--primary" id="des-db-load">${icon('search', { size: 14 })} Buka diagram</button>
            </div>
          </div>
        </div>
      </div>

      <div id="designer-area">
        <div class="empty-state">
          ${icon('layers', { size: 30 })}
          <h3>Pilih database dulu</h3>
          <p>Pilih atau ketik nama database di atas untuk melihat diagram relasi antar tabelnya.</p>
        </div>
      </div>
    </div>
  `;

  const dbSelect = root.querySelector('#des-db-select');
  const dbManual = root.querySelector('#des-db-manual');
  const dbLoadBtn = root.querySelector('#des-db-load');

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
   MUAT DATA — selalu langsung dari API (tanpa cache)
   ========================================================================= */

async function loadDatabase(dbName) {
  if (!dbName) {
    toastApiError({ message: 'Nama database tidak boleh kosong.' });
    return;
  }
  ctx.dbName = dbName;
  setState({ activeDbName: dbName });
  ctx.positions = getStoredLayout(dbName);

  const area = ctx.root.querySelector('#designer-area');
  area.innerHTML = `<div class="loading-row"><span class="spinner"></span><span> Memuat struktur tabel dari server…</span></div>`;

  try {
    const listRes = await listTables(dbName);
    const tableNames = listRes?.tables || [];

    const structures = {};
    for (let i = 0; i < tableNames.length; i += 1) {
      const t = tableNames[i];
      const label = ctx.root.querySelector('#designer-area .loading-row span:last-child');
      if (label) label.textContent = ` Memuat struktur tabel… (${i + 1}/${tableNames.length})`;
      try {
        structures[t] = await getTableStructure(dbName, t);
      } catch {
        structures[t] = null;
      }
    }

    ctx.tableNames = tableNames;
    ctx.structures = structures;

    // Buang posisi tersimpan untuk tabel yang sudah tidak ada lagi
    Object.keys(ctx.positions).forEach((t) => {
      if (!tableNames.includes(t)) delete ctx.positions[t];
    });
    autoLayoutMissing();
    saveStoredLayout(dbName, ctx.positions);
    renderCanvas(`${tableNames.length} tabel · dimuat ${new Date().toLocaleTimeString('id-ID')}`);
  } catch (err) {
    area.innerHTML = `
      <div class="empty-state">
        ${icon('alert', { size: 30 })}
        <h3>Gagal memuat struktur database</h3>
        <p>${escapeHtml(err.message)}</p>
      </div>`;
  }
}

/** Memberi posisi grid default ke tabel yang belum punya posisi tersimpan. */
function autoLayoutMissing() {
  const cols = Math.max(1, Math.ceil(Math.sqrt(ctx.tableNames.length)));
  let i = 0;
  ctx.tableNames.forEach((t) => {
    if (ctx.positions[t]) return;
    const col = i % cols;
    const row = Math.floor(i / cols);
    ctx.positions[t] = { x: 40 + col * GRID_COL_GAP, y: 40 + row * GRID_ROW_GAP };
    i += 1;
  });
}

function resetLayout() {
  ctx.positions = {};
  autoLayoutMissing();
  saveStoredLayout(ctx.dbName, ctx.positions);
  renderCanvas();
  toastSuccess('Tata letak diagram diatur ulang.');
}

/* =========================================================================
   RENDER KANVAS
   ========================================================================= */

function renderCanvas(statusText = '') {
  const area = ctx.root.querySelector('#designer-area');

  if (!ctx.tableNames.length) {
    area.innerHTML = `
      <div class="empty-state">
        ${icon('inbox', { size: 30 })}
        <h3>Belum ada tabel</h3>
        <p>Database "${escapeHtml(ctx.dbName)}" belum punya tabel untuk digambarkan.</p>
      </div>`;
    return;
  }

  area.innerHTML = `
    <div class="designer-toolbar">
      <div class="designer-status">
        ${icon('database', { size: 13 })}
        <span class="mono">${escapeHtml(ctx.dbName)}</span>
        <span id="designer-status-text">${escapeHtml(statusText)}</span>
      </div>
      <div class="designer-toolbar__right">
        <div class="designer-legend">
          <span>${icon('key', { size: 12 })} Primary key</span>
          <span><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="${RELATION_COLORS[0]}" stroke-width="2.5"><path d="M4 12h16"/></svg> Relasi (foreign key)</span>
        </div>
        <div class="zoom-group">
          <button type="button" id="zoom-out" aria-label="Perkecil">${icon('minus', { size: 13 })}</button>
          <span class="zoom-group__value" id="zoom-value">100%</span>
          <button type="button" id="zoom-in" aria-label="Perbesar">${icon('plus', { size: 13 })}</button>
          <button type="button" id="zoom-reset" aria-label="Reset zoom">${icon('refresh', { size: 13 })}</button>
        </div>
        <button class="btn btn--sm" id="auto-layout-btn">${icon('layers', { size: 13 })} Atur ulang</button>
        <button class="btn btn--sm btn--primary" id="designer-refresh">${icon('refresh', { size: 13 })} Refresh</button>
      </div>
    </div>

    <div class="designer-canvas-wrap mt-12" id="canvas-wrap">
      <div class="designer-canvas" id="canvas">
        <svg class="designer-svg" id="canvas-svg" width="1" height="1"></svg>
        ${ctx.tableNames.map((t) => renderTableCard(t)).join('')}
      </div>
    </div>

    <p class="text-tertiary" style="font-size:11.5px;margin-top:4px">
      Geser kartu untuk memindah posisi · seret area kosong untuk pan · scroll / pinch 2 jari untuk zoom.
    </p>
  `;

  bindToolbar();
  bindCardDrag();
  bindCanvasPanAndZoom();
  applyTransform();
  scheduleRedraw();
}

function renderTableCard(tableName) {
  const structure = ctx.structures[tableName];
  const columns = structure?.columns || [];
  const pos = ctx.positions[tableName] || { x: 0, y: 0 };

  return `
    <div class="er-table" data-table="${escapeHtml(tableName)}" style="left:${pos.x}px; top:${pos.y}px; width:${CARD_WIDTH}px">
      <div class="er-table__head" data-drag-handle>
        ${icon('table', { size: 13 })}<span>${escapeHtml(tableName)}</span>
      </div>
      <div class="er-table__rows">
        ${
          columns.length
            ? columns.map((col) => renderColumnRow(col)).join('')
            : `<div class="er-row"><span class="er-row__name text-tertiary">(tidak ada kolom)</span></div>`
        }
      </div>
    </div>
  `;
}

function renderColumnRow(col) {
  const isPk = col.primary_key === 'Y' || col.primary_key === true;
  const isFk = !!col.foreign_key;
  const name = col.name || '';
  return `
    <div class="er-row ${isPk ? 'is-pk' : ''} ${isFk ? 'is-fk' : ''}" data-col="${escapeHtml(name)}">
      <span class="er-row__icon ${isFk ? 'er-row__icon--fk' : ''}">${isPk ? icon('key', { size: 12 }) : isFk ? icon('layers', { size: 11 }) : ''}</span>
      <span class="er-row__name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
      <span class="er-row__type">${escapeHtml(col.type || '')}</span>
      ${col.nullable === false ? '<span class="er-row__nn">NN</span>' : ''}
    </div>
  `;
}

/* =========================================================================
   GARIS RELASI (FOREIGN KEY)
   ========================================================================= */

function collectRelations() {
  const relations = [];
  ctx.tableNames.forEach((tableName) => {
    const columns = ctx.structures[tableName]?.columns || [];
    columns.forEach((col) => {
      if (col.foreign_key && col.foreign_key.referred_table) {
        relations.push({
          sourceTable: tableName,
          sourceCol: col.name,
          targetTable: col.foreign_key.referred_table,
          targetCol: col.foreign_key.referred_column,
        });
      }
    });
  });
  return relations;
}

function localPointFromClient(canvasEl, clientX, clientY) {
  const rect = canvasEl.getBoundingClientRect();
  return {
    x: (clientX - rect.left) / ctx.zoom,
    y: (clientY - rect.top) / ctx.zoom,
  };
}

let rafHandle = null;
function scheduleRedraw() {
  if (rafHandle) cancelAnimationFrame(rafHandle);
  rafHandle = requestAnimationFrame(redrawConnectors);
}

function redrawConnectors() {
  const canvasEl = ctx.root.querySelector('#canvas');
  const svg = ctx.root.querySelector('#canvas-svg');
  if (!canvasEl || !svg) return;

  const relations = collectRelations();
  let maxX = 0;
  let maxY = 0;
  const paths = [];

  relations.forEach((rel, i) => {
    const sourceRow = canvasEl.querySelector(`[data-table="${cssAttrEscape(rel.sourceTable)}"] [data-col="${cssAttrEscape(rel.sourceCol)}"]`);
    const targetRow = canvasEl.querySelector(`[data-table="${cssAttrEscape(rel.targetTable)}"] [data-col="${cssAttrEscape(rel.targetCol)}"]`);
    if (!sourceRow || !targetRow) return;

    const s = sourceRow.getBoundingClientRect();
    const t = targetRow.getBoundingClientRect();
    const sourceCenterX = s.left + s.width / 2;
    const targetCenterX = t.left + t.width / 2;

    let sx, tx;
    if (targetCenterX >= sourceCenterX) {
      sx = s.right;
      tx = t.left;
    } else {
      sx = s.left;
      tx = t.right;
    }
    const sy = s.top + s.height / 2;
    const ty = t.top + t.height / 2;

    const p1 = localPointFromClient(canvasEl, sx, sy);
    const p2 = localPointFromClient(canvasEl, tx, ty);
    maxX = Math.max(maxX, p1.x, p2.x);
    maxY = Math.max(maxY, p1.y, p2.y);

    const dx = Math.max(Math.abs(p2.x - p1.x) * 0.4, 40);
    const dir = p2.x >= p1.x ? 1 : -1;
    const c1x = p1.x + dir * dx;
    const c2x = p2.x - dir * dx;
    const color = RELATION_COLORS[i % RELATION_COLORS.length];

    paths.push(`
      <path d="M ${p1.x},${p1.y} C ${c1x},${p1.y} ${c2x},${p2.y} ${p2.x},${p2.y}"
            fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" opacity="0.9" />
      <circle cx="${p1.x}" cy="${p1.y}" r="3.5" fill="${color}" />
      <circle cx="${p2.x}" cy="${p2.y}" r="3.5" fill="${color}" />
    `);
  });

  svg.setAttribute('width', String(Math.max(maxX + 260, 800)));
  svg.setAttribute('height', String(Math.max(maxY + 200, 600)));
  svg.innerHTML = paths.join('');
}

function cssAttrEscape(value) {
  return String(value).replace(/["\\]/g, '\\$&');
}

/* =========================================================================
   DRAG KARTU TABEL — Pointer Events (mouse + touch + pen)
   ========================================================================= */

function bindCardDrag() {
  const canvasEl = ctx.root.querySelector('#canvas');
  canvasEl.querySelectorAll('.er-table').forEach((card) => {
    const handle = card.querySelector('[data-drag-handle]');
    handle.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const tableName = card.dataset.table;
      ctx.dragState = {
        pointerId: e.pointerId,
        tableName,
        card,
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPos: { ...ctx.positions[tableName] },
      };
      card.classList.add('dragging');
      document.addEventListener('pointermove', onDragMove);
      document.addEventListener('pointerup', onDragEnd);
      document.addEventListener('pointercancel', onDragEnd);
    });
  });
}

function onDragMove(e) {
  const ds = ctx.dragState;
  if (!ds || e.pointerId !== ds.pointerId) return;
  const dx = (e.clientX - ds.startMouseX) / ctx.zoom;
  const dy = (e.clientY - ds.startMouseY) / ctx.zoom;
  const newPos = { x: Math.round(ds.startPos.x + dx), y: Math.round(ds.startPos.y + dy) };
  ctx.positions[ds.tableName] = newPos;
  ds.card.style.left = `${newPos.x}px`;
  ds.card.style.top = `${newPos.y}px`;
  scheduleRedraw();
}

function onDragEnd(e) {
  if (ctx.dragState && (!e || e.pointerId === ctx.dragState.pointerId)) {
    ctx.dragState.card.classList.remove('dragging');
    saveStoredLayout(ctx.dbName, ctx.positions);
    ctx.dragState = null;
  }
  document.removeEventListener('pointermove', onDragMove);
  document.removeEventListener('pointerup', onDragEnd);
  document.removeEventListener('pointercancel', onDragEnd);
}

/* =========================================================================
   PAN & ZOOM KANVAS — mouse drag, scroll wheel, dan pinch 2 jari di touch
   ========================================================================= */

function applyTransform() {
  const canvasEl = ctx.root.querySelector('#canvas');
  if (!canvasEl) return;
  canvasEl.style.transform = `translate(${ctx.pan.x}px, ${ctx.pan.y}px) scale(${ctx.zoom})`;
  const label = ctx.root.querySelector('#zoom-value');
  if (label) label.textContent = `${Math.round(ctx.zoom * 100)}%`;
}

function distanceBetween(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}
function midpointOf(a, b) {
  return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
}

function bindCanvasPanAndZoom() {
  const wrap = ctx.root.querySelector('#canvas-wrap');
  const canvasEl = ctx.root.querySelector('#canvas');
  ctx.wrapPointers.clear();
  ctx.panState = null;
  ctx.pinchState = null;

  wrap.addEventListener('pointerdown', (e) => {
    if (e.target.closest('.er-table')) return; // biarkan drag kartu bekerja sendiri
    ctx.wrapPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (ctx.wrapPointers.size === 1) {
      ctx.panState = {
        pointerId: e.pointerId,
        startMouseX: e.clientX,
        startMouseY: e.clientY,
        startPan: { ...ctx.pan },
      };
      wrap.classList.add('panning');
    } else if (ctx.wrapPointers.size === 2) {
      // Dua jari menyentuh -> beralih ke mode pinch-zoom, batalkan pan 1 jari
      ctx.panState = null;
      wrap.classList.remove('panning');
      const pts = Array.from(ctx.wrapPointers.values());
      const mid = midpointOf(pts[0], pts[1]);
      ctx.pinchState = {
        startDist: distanceBetween(pts[0], pts[1]),
        startZoom: ctx.zoom,
        midLocal: localPointFromClient(canvasEl, mid.x, mid.y),
      };
    }
  });

  wrap.addEventListener('pointermove', (e) => {
    if (!ctx.wrapPointers.has(e.pointerId)) return;
    ctx.wrapPointers.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (ctx.pinchState && ctx.wrapPointers.size >= 2) {
      const pts = Array.from(ctx.wrapPointers.values()).slice(0, 2);
      const dist = distanceBetween(pts[0], pts[1]);
      const newZoom = clamp(ctx.pinchState.startZoom * (dist / ctx.pinchState.startDist), ZOOM_MIN, ZOOM_MAX);
      const mid = midpointOf(pts[0], pts[1]);
      const wrapRect = wrap.getBoundingClientRect();
      const screenX = mid.x - wrapRect.left;
      const screenY = mid.y - wrapRect.top;
      ctx.pan = { x: screenX - ctx.pinchState.midLocal.x * newZoom, y: screenY - ctx.pinchState.midLocal.y * newZoom };
      ctx.zoom = newZoom;
      applyTransform();
      scheduleRedraw();
    } else if (ctx.panState && e.pointerId === ctx.panState.pointerId) {
      ctx.pan = {
        x: ctx.panState.startPan.x + (e.clientX - ctx.panState.startMouseX),
        y: ctx.panState.startPan.y + (e.clientY - ctx.panState.startMouseY),
      };
      applyTransform();
      scheduleRedraw();
    }
  });

  const endWrapPointer = (e) => {
    ctx.wrapPointers.delete(e.pointerId);
    if (ctx.wrapPointers.size < 2) ctx.pinchState = null;
    if (ctx.panState && e.pointerId === ctx.panState.pointerId) {
      ctx.panState = null;
    }
    if (ctx.wrapPointers.size === 0) {
      wrap.classList.remove('panning');
    }
  };
  wrap.addEventListener('pointerup', endWrapPointer);
  wrap.addEventListener('pointercancel', endWrapPointer);

  // Zoom dengan scroll wheel (desktop) — tetap dipertahankan berdampingan dengan pinch (touch)
  wrap.addEventListener(
    'wheel',
    (e) => {
      e.preventDefault();
      const wrapRect = wrap.getBoundingClientRect();
      const cursorLocal = localPointFromClient(canvasEl, e.clientX, e.clientY);
      const factor = e.deltaY < 0 ? 1.12 : 1 / 1.12;
      const newZoom = clamp(ctx.zoom * factor, ZOOM_MIN, ZOOM_MAX);

      const screenX = e.clientX - wrapRect.left;
      const screenY = e.clientY - wrapRect.top;
      ctx.pan = { x: screenX - cursorLocal.x * newZoom, y: screenY - cursorLocal.y * newZoom };
      ctx.zoom = newZoom;
      applyTransform();
      scheduleRedraw();
    },
    { passive: false }
  );
}

function clamp(v, min, max) {
  return Math.min(Math.max(v, min), max);
}

/* =========================================================================
   TOOLBAR
   ========================================================================= */

function bindToolbar() {
  ctx.root.querySelector('#designer-refresh').addEventListener('click', () => loadDatabase(ctx.dbName));
  ctx.root.querySelector('#auto-layout-btn').addEventListener('click', resetLayout);
  ctx.root.querySelector('#zoom-in').addEventListener('click', () => zoomBy(1.2));
  ctx.root.querySelector('#zoom-out').addEventListener('click', () => zoomBy(1 / 1.2));
  ctx.root.querySelector('#zoom-reset').addEventListener('click', () => {
    ctx.zoom = 1;
    ctx.pan = { x: 40, y: 30 };
    applyTransform();
    scheduleRedraw();
  });
}

function zoomBy(factor) {
  ctx.zoom = clamp(ctx.zoom * factor, ZOOM_MIN, ZOOM_MAX);
  applyTransform();
  scheduleRedraw();
}
