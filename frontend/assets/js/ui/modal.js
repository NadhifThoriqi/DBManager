/**
 * ui/modal.js — Dialog modal generik
 * -----------------------------------------------------------------------
 * openModal({title, subtitle, bodyHtml, wide, onMount, footerButtons})
 *   -> mengembalikan { overlay, close } sehingga caller (views/*) bisa
 *      menutup modal secara manual (misal setelah submit form sukses).
 *
 * confirmDialog({...}) -> Promise<boolean>, dipakai untuk konfirmasi
 *      aksi destruktif (hapus database, drop table, dll).
 */

let activeOverlay = null;

export function closeModal() {
  if (activeOverlay) {
    activeOverlay.remove();
    activeOverlay = null;
    document.removeEventListener('keydown', handleEsc);
  }
}

function handleEsc(e) {
  if (e.key === 'Escape') closeModal();
}

export function openModal({ title, subtitle = '', bodyHtml = '', wide = false, footerHtml = '', onMount } = {}) {
  closeModal();

  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal ${wide ? 'modal--wide' : ''}" role="dialog" aria-modal="true">
      <div class="modal__head">
        <div class="modal__title">${title}${subtitle ? `<small>${subtitle}</small>` : ''}</div>
        <button class="modal__close" aria-label="Tutup" data-close>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>
      <div class="modal__body">${bodyHtml}</div>
      ${footerHtml ? `<div class="modal__foot">${footerHtml}</div>` : ''}
    </div>
  `;

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay || e.target.closest('[data-close]')) closeModal();
  });
  document.addEventListener('keydown', handleEsc);

  document.body.appendChild(overlay);
  activeOverlay = overlay;

  const modalEl = overlay.querySelector('.modal');
  if (onMount) onMount(modalEl, overlay);

  return { overlay, modalEl, close: closeModal };
}

/**
 * Dialog konfirmasi berbasis Promise.
 * @param {{title:string, message:string, confirmLabel?:string, danger?:boolean, requireText?:string}} opts
 *   requireText: jika diisi, tombol konfirmasi baru aktif setelah user
 *   mengetik teks tersebut persis (dipakai untuk drop table / hapus database).
 * @returns {Promise<boolean>}
 */
export function confirmDialog({ title, message, confirmLabel = 'Konfirmasi', danger = false, requireText = '' }) {
  return new Promise((resolve) => {
    const needsTyping = !!requireText;
    const bodyHtml = `
      <div class="danger-box">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 9v4M12 17h.01M10.3 3.86 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.86a2 2 0 0 0-3.4 0Z"/></svg>
        <div>${message}</div>
      </div>
      ${
        needsTyping
          ? `<div class="field mt-16">
               <label>Ketik <code class="mono">${requireText}</code> untuk melanjutkan</label>
               <input type="text" id="confirm-typed" autocomplete="off" placeholder="${requireText}">
             </div>`
          : ''
      }
    `;
    const footerHtml = `
      <button class="btn" data-close>Batal</button>
      <button class="btn ${danger ? 'btn--danger-solid' : 'btn--primary'}" id="confirm-ok" ${needsTyping ? 'disabled' : ''}>${confirmLabel}</button>
    `;

    const { close } = openModal({
      title,
      bodyHtml,
      footerHtml,
      onMount: (modalEl) => {
        const okBtn = modalEl.querySelector('#confirm-ok');
        if (needsTyping) {
          const input = modalEl.querySelector('#confirm-typed');
          input.addEventListener('input', () => {
            okBtn.disabled = input.value !== requireText;
          });
          setTimeout(() => input.focus(), 30);
        }
        okBtn.addEventListener('click', () => {
          resolve(true);
          close();
        });
      },
    });

    // Jika ditutup lewat overlay/close/esc tanpa klik OK -> resolve(false)
    const overlay = document.querySelector('.modal-overlay');
    overlay.addEventListener(
      'click',
      (e) => {
        if (e.target === overlay || e.target.closest('[data-close]')) resolve(false);
      },
      { once: true }
    );
    document.addEventListener(
      'keydown',
      function onKey(e) {
        if (e.key === 'Escape') {
          resolve(false);
          document.removeEventListener('keydown', onKey);
        }
      },
      { once: true }
    );
  });
}
