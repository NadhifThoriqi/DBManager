/**
 * ui/serverSettings.js — Modal untuk mengubah alamat server API
 */

import { getApiBaseUrl, setApiBaseUrl, resetApiBaseUrl } from '../config.js';
import { openModal, closeModal } from './modal.js';
import { toastSuccess } from './toast.js';
import { icon } from './icons.js';

export function openServerSettingsModal(onSaved) {
  openModal({
    title: 'Alamat server API',
    subtitle: 'Sesuai path "servers" pada openapi.json backend kamu',
    bodyHtml: `
      <div class="field">
        <label for="server-url">Base URL</label>
        <input type="text" id="server-url" value="${getApiBaseUrl()}" placeholder="http://localhost:8000/thorix">
        <span class="hint">Contoh: http://localhost:8000/thorix — cocokkan dengan tempat backend FastAPI kamu berjalan.</span>
      </div>
    `,
    footerHtml: `
      <button class="btn" id="server-reset">Reset ke default</button>
      <button class="btn btn--primary" id="server-save">${icon('check', { size: 14 })} Simpan</button>
    `,
    onMount: (modalEl) => {
      modalEl.querySelector('#server-save').addEventListener('click', () => {
        const val = modalEl.querySelector('#server-url').value.trim();
        if (!val) return;
        setApiBaseUrl(val);
        toastSuccess('Alamat server disimpan.');
        closeModal();
        if (onSaved) onSaved();
      });
      modalEl.querySelector('#server-reset').addEventListener('click', () => {
        const url = resetApiBaseUrl();
        modalEl.querySelector('#server-url').value = url;
      });
    },
  });
}
