/**
 * config.js — Konfigurasi global aplikasi
 * -----------------------------------------------------------------------
 * Menyimpan & mengambil alamat dasar (base URL) backend DBManager API.
 * Backend didefinisikan pada openapi.json dengan server path "/thorix",
 * jadi default di bawah menganggap backend berjalan di origin yang sama
 * pada path tersebut. Ubah lewat UI (tombol "Server" di topbar) —
 * nilainya disimpan di localStorage agar tidak hilang saat reload.
 */

const STORAGE_KEY = 'dbmanager.apiBaseUrl';

// Default mengikuti server yang kamu berikan: http://127.0.0.1:2606
// (tanpa prefix path tambahan). Ubah lewat UI ("Server" di topbar/login)
// jika backend kamu berjalan di alamat lain — nilainya disimpan di
// localStorage sehingga tidak hilang saat reload.
function defaultBaseUrl() {
  return 'http://127.0.0.1:2606';
}

export function getApiBaseUrl() {
  return localStorage.getItem(STORAGE_KEY) || defaultBaseUrl();
}

export function setApiBaseUrl(url) {
  const cleaned = url.trim().replace(/\/+$/, '');
  localStorage.setItem(STORAGE_KEY, cleaned);
  return cleaned;
}

export function resetApiBaseUrl() {
  localStorage.removeItem(STORAGE_KEY);
  return defaultBaseUrl();
}
