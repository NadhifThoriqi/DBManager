/**
 * ui/toast.js — Notifikasi kecil di pojok kanan bawah
 */

const ICONS = {
  success:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6 9 17l-5-5"/></svg>',
  error:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>',
  info:
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>',
};

function getStack() {
  let stack = document.getElementById('toast-stack');
  if (!stack) {
    stack = document.createElement('div');
    stack.id = 'toast-stack';
    stack.className = 'toast-stack';
    document.body.appendChild(stack);
  }
  return stack;
}

export function toast(message, type = 'info', duration = 4200) {
  const stack = getStack();
  const node = document.createElement('div');
  node.className = `toast toast--${type}`;
  node.innerHTML = `
    ${ICONS[type] || ICONS.info}
    <div class="toast__msg">${message}</div>
    <button class="toast__close" aria-label="Tutup">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6 6 18M6 6l12 12"/></svg>
    </button>
  `;
  const remove = () => node.remove();
  node.querySelector('.toast__close').addEventListener('click', remove);
  stack.appendChild(node);
  if (duration) setTimeout(remove, duration);
  return remove;
}

export const toastSuccess = (msg) => toast(msg, 'success');
export const toastError = (msg) => toast(msg, 'error', 6000);
export const toastInfo = (msg) => toast(msg, 'info');

/** Menerjemahkan ApiError menjadi toast error otomatis. */
export function toastApiError(err, fallback = 'Terjadi kesalahan yang tidak diketahui.') {
  toastError(err?.message || fallback);
}
