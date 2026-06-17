/**
 * api.js — NovDB API Layer
 * Semua komunikasi ke backend Python (FastAPI) terpusat di sini.
 * Ubah API_BASE_URL untuk mengganti endpoint backend.
 */

// ────────────────────────────────────────────────
//  KONFIGURASI
// ────────────────────────────────────────────────
const API_CONFIG = {
  BASE_URL: localStorage.getItem('novdb_api_url') || 'http://localhost:8000/1.0.0/pysql',
  TIMEOUT: parseInt(localStorage.getItem('novdb_timeout') || '10000', 10),
};

// ────────────────────────────────────────────────
//  HELPER: fetch dengan timeout + error handling
// ────────────────────────────────────────────────

/**
 * Kirim request HTTP ke API dengan timeout otomatis.
 * @param {string} endpoint  - Path relatif (e.g. "/tables")
 * @param {RequestInit} opts - Opsi fetch standar
 * @returns {Promise<any>}
 */
async function apiRequest(endpoint, opts = {}) {
  const url = `${API_CONFIG.BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_CONFIG.TIMEOUT);

  const defaultHeaders = { 'Content-Type': 'application/json' };

  try {
    const res = await fetch(url, {
      ...opts,
      signal: controller.signal,
      headers: { ...defaultHeaders, ...(opts.headers || {}) },
    });

    clearTimeout(timer);

    // Coba parse JSON
    let data;
    const contentType = res.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    if (!res.ok) {
      // Backend bisa mengirim { detail: "..." } (FastAPI style)
      const message =
        (typeof data === 'object' && data?.detail) ||
        (typeof data === 'object' && data?.message) ||
        (typeof data === 'string' && data) ||
        `HTTP ${res.status}: ${res.statusText}`;
      throw new ApiError(message, res.status, data);
    }

    return data;
  } catch (err) {
    clearTimeout(timer);

    if (err.name === 'AbortError') {
      throw new ApiError(`Request timeout setelah ${API_CONFIG.TIMEOUT}ms`, 408);
    }
    if (err instanceof ApiError) throw err;

    // Network error (backend tidak jalan, CORS, dsb.)
    throw new ApiError(
      err.message || 'Tidak dapat terhubung ke server. Pastikan backend berjalan.',
      0
    );
  }
}

/**
 * Custom error class agar UI bisa membedakan jenis error.
 */
class ApiError extends Error {
  constructor(message, statusCode = 0, raw = null) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.raw = raw;
  }
}

// ────────────────────────────────────────────────
//  PUBLIC API METHODS
// ────────────────────────────────────────────────

const API = {
  // ── Health Check ──────────────────────────────
  /**
   * Cek apakah backend aktif.
   * GET /api/health  (atau /api/tables sebagai fallback)
   */
  async healthCheck() {
    try {
      // Coba endpoint khusus health; jika tidak ada, coba tables
      const data = await apiRequest('/health');
      return { ok: true, data };
    } catch {
      // Fallback: panggil getTables; jika berhasil berarti API aktif
      try {
        await apiRequest('/tables');
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err.message };
      }
    }
  },

  // ── Tables ────────────────────────────────────
  /**
   * Ambil daftar semua tabel dari database.
   * GET /api/tables
   * Response: string[] | { tables: string[] } | { name, row_count }[]
   */
  async getTables() {
    const data = await apiRequest('/tables');
    // Normalize berbagai format response
    if (Array.isArray(data)) return data;
    if (data?.tables) return data.tables;
    return data;
  },

  /**
   * Ambil schema/struktur kolom sebuah tabel.
   * GET /api/table/{table_name}/schema
   */
  async getTableSchema(tableName) {
    return apiRequest(`/table/${encodeURIComponent(tableName)}/schema`);
  },

  // ── CRUD Data ─────────────────────────────────
  /**
   * Ambil data dari tabel dengan pagination, search, dan sort.
   * GET /api/table/{table_name}?page=1&limit=25&search=...&sort=col&order=asc
   */
  async getTableData(tableName, { page = 1, limit = 25, search = '', sort = '', order = 'asc' } = {}) {
    const params = new URLSearchParams({ page, limit });
    if (search) params.append('search', search);
    if (sort)   params.append('sort', sort);
    if (order)  params.append('order', order);

    return apiRequest(`/table/${encodeURIComponent(tableName)}?${params}`);
  },

  /**
   * Tambah baris baru ke tabel.
   * POST /api/table/{table_name}
   */
  async createData(tableName, payload) {
    return apiRequest(`/table/${encodeURIComponent(tableName)}`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Update baris berdasarkan ID.
   * PUT /api/table/{table_name}/{id}
   */
  async updateData(tableName, id, payload) {
    return apiRequest(`/table/${encodeURIComponent(tableName)}/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  /**
   * Hapus baris berdasarkan ID.
   * DELETE /api/table/{table_name}/{id}
   */
  async deleteData(tableName, id) {
    return apiRequest(`/table/${encodeURIComponent(tableName)}/${encodeURIComponent(id)}`, {
      method: 'DELETE',
    });
  },

  // ── Query Builder ─────────────────────────────
  /**
   * Eksekusi raw SQL query.
   * POST /api/query
   * Body: { query: string }
   */
  async executeQuery(query) {
    return apiRequest('/query', {
      method: 'POST',
      body: JSON.stringify({ query }),
    });
  },

  // ── Statistik ─────────────────────────────────
  /**
   * Ambil statistik overview (opsional — backend mungkin menyediakan endpoint ini).
   * GET /api/stats
   * Jika tidak tersedia, dihitung secara manual dari getTables.
   */
  async getStats() {
    try {
      return await apiRequest('/stats');
    } catch {
      // Jika endpoint /stats tidak ada, kembalikan null
      return null;
    }
  },

  // ── Config helpers ────────────────────────────
  /**
   * Update base URL dan simpan ke localStorage.
   */
  setBaseUrl(url) {
    API_CONFIG.BASE_URL = url.replace(/\/$/, ''); // hapus trailing slash
    localStorage.setItem('novdb_api_url', API_CONFIG.BASE_URL);
  },

  /**
   * Update timeout dan simpan ke localStorage.
   */
  setTimeout(ms) {
    API_CONFIG.TIMEOUT = ms;
    localStorage.setItem('novdb_timeout', String(ms));
  },

  getBaseUrl() { return API_CONFIG.BASE_URL; },
  getTimeout()  { return API_CONFIG.TIMEOUT;  },
};

// Ekspor untuk dipakai di app.js (jika menggunakan modul ES)
// export { API, ApiError };
// Untuk script biasa, API sudah tersedia sebagai global.
