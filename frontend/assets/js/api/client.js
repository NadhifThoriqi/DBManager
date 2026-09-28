/**
 * api/client.js — Lapisan HTTP paling dasar
 * -----------------------------------------------------------------------
 * Semua modul di js/api/*.js memanggil `request()` di sini, tidak pernah
 * memanggil fetch() langsung. Ini membuat satu tempat untuk:
 *   - menyusun URL dari base URL + path
 *   - menyisipkan cookie sesi (credentials: 'include') karena backend
 *     mengautentikasi lewat cookie `access_token` (lihat /auth/signin)
 *   - menyeragamkan penanganan error (memakai format FastAPI: {detail: ...})
 */

import { getApiBaseUrl } from '../config.js';

export class ApiError extends Error {
  constructor(message, status = 0, detail = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

/**
 * Mengubah error response FastAPI menjadi pesan yang enak dibaca.
 * FastAPI mengirim validation error sebagai:
 *   { detail: [ { loc: [...], msg: "...", type: "..." }, ... ] }
 * atau error biasa sebagai:
 *   { detail: "pesan error" }
 */
function extractMessage(data, status, statusText) {
  if (data && typeof data === 'object' && 'detail' in data) {
    const { detail } = data;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          const field = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : '';
          return field ? `${field}: ${d.msg}` : d.msg;
        })
        .join(' · ');
    }
  }
  if (typeof data === 'string' && data) return data;
  return `HTTP ${status} ${statusText || ''}`.trim();
}

/**
 * @param {string} path - path relatif, contoh: "/table/list"
 * @param {object} opts
 * @param {'GET'|'POST'|'PUT'|'DELETE'} [opts.method]
 * @param {object} [opts.body] - dikirim sebagai JSON
 * @param {object} [opts.params] - query string params
 */
export async function request(path, opts = {}) {
  const { method = 'GET', body, params } = opts;

  let url = `${getApiBaseUrl()}${path}`;
  if (params && Object.keys(params).length) {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') qs.append(k, v);
    });
    const qsStr = qs.toString();
    if (qsStr) url += `?${qsStr}`;
  }

  let res;
  try {
    res = await fetch(url, {
      method,
      credentials: 'include', // wajib: backend memakai cookie `access_token`
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : {},
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch (networkErr) {
    throw new ApiError(
      `Tidak dapat terhubung ke server API di ${getApiBaseUrl()}. ` +
        `Pastikan backend berjalan dan alamat server sudah benar.`,
      0
    );
  }

  const contentType = res.headers.get('content-type') || '';
  let data = null;
  if (contentType.includes('application/json')) {
    data = await res.json().catch(() => null);
  } else {
    const text = await res.text().catch(() => '');
    data = text || null;
  }

  if (!res.ok) {
    throw new ApiError(extractMessage(data, res.status, res.statusText), res.status, data);
  }

  return data;
}

export const get = (path, params) => request(path, { method: 'GET', params });
export const post = (path, body, params) => request(path, { method: 'POST', body, params });
export const put = (path, body, params) => request(path, { method: 'PUT', body, params });
export const del = (path, body, params) => request(path, { method: 'DELETE', body, params });
