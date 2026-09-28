/**
 * ui/helpers.js — Fungsi bantu kecil yang dipakai di banyak tempat
 */

/** Escape teks agar aman disisipkan sebagai HTML. */
export function escapeHtml(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

/** Format nilai sel tabel untuk ditampilkan (null, boolean, object, dll). */
export function formatCellValue(value) {
  if (value === null || value === undefined) {
    return { text: 'NULL', isNull: true };
  }
  if (typeof value === 'boolean') return { text: value ? 'true' : 'false', isNull: false };
  if (typeof value === 'object') return { text: JSON.stringify(value), isNull: false };
  return { text: String(value), isNull: false };
}

/** Badge warna berdasarkan engine database. */
export function engineBadgeClass(engine) {
  return `badge badge--${engine}`;
}

export function engineLabel(engine) {
  return { sqlite: 'SQLite', mysql: 'MySQL', postgresql: 'PostgreSQL' }[engine] || engine;
}

export function engineDotColor(engine) {
  return { sqlite: 'var(--engine-sqlite)', mysql: 'var(--engine-mysql)', postgresql: 'var(--engine-postgresql)' }[engine] || 'var(--text-tertiary)';
}

/** Debounce sederhana untuk input pencarian. */
export function debounce(fn, wait = 300) {
  let t;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
}

/** Menebak tipe <input> HTML paling cocok dari tipe kolom SQL. */
export function inputTypeForSqlType(sqlType = '') {
  const t = sqlType.toUpperCase();
  if (/INT|FLOAT|DOUBLE|DECIMAL|NUMERIC|REAL/.test(t)) return 'number';
  if (/BOOL/.test(t)) return 'checkbox';
  return 'text';
}

/** Konversi nilai string form ke tipe JS yang sesuai untuk dikirim ke API. */
export function coerceValueBySqlType(rawValue, sqlType = '', isCheckbox = false) {
  if (isCheckbox) return !!rawValue;
  if (rawValue === '') return null;
  const t = sqlType.toUpperCase();
  if (/INT/.test(t) && !/POINT/.test(t)) {
    const n = Number(rawValue);
    return Number.isInteger(n) ? n : rawValue;
  }
  if (/FLOAT|DOUBLE|DECIMAL|NUMERIC|REAL/.test(t)) {
    const n = Number(rawValue);
    return Number.isNaN(n) ? rawValue : n;
  }
  return rawValue;
}

export function qs(selector, root = document) {
  return root.querySelector(selector);
}

/**
 * Mengubah string apa pun (mis. nama kolom yang bisa memuat spasi atau
 * karakter spesial) menjadi id HTML yang aman dipakai di `id="..."`
 * maupun di dalam `querySelector('#...')` tanpa perlu CSS.escape.
 */
export function safeId(prefix, raw) {
  const encoded = encodeURIComponent(String(raw)).replace(/[^a-zA-Z0-9_-]/g, (c) => `_${c.charCodeAt(0)}_`);
  return `${prefix}-${encoded}`;
}

export function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  Object.entries(attrs).forEach(([k, v]) => {
    if (k === 'class') node.className = v;
    else if (k === 'html') node.innerHTML = v;
    else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v);
  });
  (Array.isArray(children) ? children : [children]).forEach((c) => {
    if (c === null || c === undefined) return;
    node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
  });
  return node;
}
