/**
 * state.js — Penyimpanan state aplikasi (sangat sederhana, tanpa framework)
 * -----------------------------------------------------------------------
 * Bukan Redux/Vuex — hanya sebuah objek + fungsi subscribe/notify.
 * Views membaca `state.xxx` langsung dan memanggil `setState({...})`
 * untuk mengubahnya; setiap perubahan memicu semua subscriber (biasanya
 * cuma app.js yang re-render area yang relevan).
 */

const SESSION_KEY = 'dbmanager.session';

function loadSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export const state = {
  // Sesi login (tidak menyimpan password). null = belum login.
  session: loadSession(), // { user, db, host, port }

  // Navigasi
  route: 'dashboard', // 'dashboard' | 'databases' | 'tables'

  // Konteks kerja saat ini
  activeDbName: null, // database yang dipilih untuk operasi tabel
  activeTable: null, // nama tabel yang dipilih

  // Cache ringan supaya tidak fetch berulang saat pindah tab
  databases: { sqlite: null, mysql: null, postgresql: null }, // null = belum dimuat
};

const listeners = new Set();

export function subscribe(fn) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function setState(patch) {
  Object.assign(state, patch);
  listeners.forEach((fn) => fn(state));
}

export function setSession(session) {
  if (session) {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } else {
    localStorage.removeItem(SESSION_KEY);
  }
  setState({ session });
}

export function isAuthenticated() {
  return !!state.session;
}
