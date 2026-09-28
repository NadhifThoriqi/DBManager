/**
 * app.js — Entry point aplikasi
 * -----------------------------------------------------------------------
 * Tanggung jawab file ini hanya dua:
 *   1. Menampilkan layar Auth jika belum login, atau App Shell jika sudah.
 *   2. Merender sidebar/topbar App Shell + routing antar view
 *      (dashboard / databases / tables) tanpa reload halaman.
 *
 * Semua logika bisnis per-halaman ada di js/views/*.js.
 */

import { state, setState, isAuthenticated, setSession } from './state.js';
import { renderAuthView } from './views/authView.js';
import { renderDashboardView } from './views/dashboardView.js';
import { renderDatabasesView } from './views/databasesView.js';
import { renderTablesView } from './views/tablesView.js';
import { renderDesignerView } from './views/designerView.js';
import { logOut } from './api/auth.js';
import { toastSuccess, toastApiError } from './ui/toast.js';
import { openServerSettingsModal } from './ui/serverSettings.js';
import { icon } from './ui/icons.js';
import { engineLabel } from './ui/helpers.js';

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
  { id: 'databases', label: 'Databases', icon: 'database' },
  { id: 'tables', label: 'Tables', icon: 'table' },
  { id: 'designer', label: 'Designer', icon: 'layers' },
];

const PAGE_META = {
  dashboard: { title: 'Dashboard' },
  databases: { title: 'Database Management' },
  tables: { title: 'Table Operations' },
  designer: { title: 'Designer' },
};

const appRoot = document.getElementById('app');

function boot() {
  if (isAuthenticated()) {
    renderShell();
  } else {
    renderAuthView(appRoot, () => renderShell());
  }
}

function navigate(route) {
  setState({ route });
  renderShell();
}

function renderShell() {
  appRoot.innerHTML = `
    <div class="shell">
      <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="sidebar__brand">
          <div class="sidebar__brand-mark">${icon('database', { size: 15 })}</div>
          <div class="sidebar__brand-name">DBManager<small>Admin Console</small></div>
        </div>
        <nav class="nav">
          <div class="nav__group-label">Menu</div>
          ${NAV_ITEMS.map(
            (item) =>
              `<button type="button" class="nav__item ${item.id === state.route ? 'active' : ''}" data-route="${item.id}">${icon(item.icon, { size: 16 })}${item.label}</button>`
          ).join('')}
        </nav>
        <div class="sidebar__footer">
          <div class="session-card">
            <div class="session-card__row">
              <span class="session-card__dot"></span>
              <span class="session-card__user">${state.session?.user || '—'}</span>
            </div>
            <div class="session-card__row">
              ${icon('server', { size: 13 })}
              <span>${engineLabel(state.session?.db)} · ${state.session?.host || '-'}</span>
            </div>
          </div>
        </div>
      </aside>

      <header class="topbar">
        <button type="button" class="topbar__hamburger" id="sidebar-toggle" aria-label="Buka menu">${icon('menu', { size: 20 })}</button>
        <div class="topbar__crumb">
          <b>${PAGE_META[state.route]?.title || ''}</b>
          ${state.activeDbName ? `<span class="sep">/</span><span class="trunc mono">${state.activeDbName}</span>` : ''}
          ${state.activeTable && state.route === 'tables' ? `<span class="sep">/</span><span class="trunc mono">${state.activeTable}</span>` : ''}
        </div>
        <div class="topbar__right">
          <button class="btn btn--sm btn--ghost" id="topbar-settings">${icon('settings', { size: 14 })} Server</button>
          <button class="btn btn--sm" id="topbar-logout">${icon('logout', { size: 14 })} Keluar</button>
        </div>
      </header>

      <main class="main">
        <div id="view-root"></div>
      </main>
    </div>
  `;

  const sidebar = appRoot.querySelector('#sidebar');
  const backdrop = appRoot.querySelector('#sidebar-backdrop');

  const openDrawer = () => {
    sidebar.classList.add('is-open');
    backdrop.classList.add('is-open');
  };
  const closeDrawer = () => {
    sidebar.classList.remove('is-open');
    backdrop.classList.remove('is-open');
  };

  appRoot.querySelector('#sidebar-toggle').addEventListener('click', openDrawer);
  backdrop.addEventListener('click', closeDrawer);

  appRoot.querySelectorAll('[data-route]').forEach((btn) => {
    btn.addEventListener('click', () => {
      closeDrawer();
      navigate(btn.dataset.route);
    });
  });
  appRoot.querySelector('#topbar-settings').addEventListener('click', () => openServerSettingsModal());
  appRoot.querySelector('#topbar-logout').addEventListener('click', handleLogout);

  const viewRoot = document.getElementById('view-root');
  if (state.route === 'databases') renderDatabasesView(viewRoot, navigate);
  else if (state.route === 'tables') renderTablesView(viewRoot, navigate);
  else if (state.route === 'designer') renderDesignerView(viewRoot, navigate);
  else renderDashboardView(viewRoot, navigate);
}

async function handleLogout() {
  try {
    await logOut();
  } catch (err) {
    // Tetap lanjutkan logout di sisi client meski request gagal (mis. sudah expired)
  }
  setSession(null);
  setState({ route: 'dashboard', activeDbName: null, activeTable: null });
  toastSuccess('Kamu telah keluar.');
  boot();
}

boot();
