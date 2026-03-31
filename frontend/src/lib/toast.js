import { writable } from 'svelte/store';

export const toasts = writable([]);

let nextId = 0;

export function showToast(message, type = 'info', duration = 3000) {
  const id = ++nextId;
  toasts.update((t) => [...t, { id, message, type }]);
  setTimeout(() => {
    toasts.update((t) => t.filter((x) => x.id !== id));
  }, duration);
}

export function dismissToast(id) {
  toasts.update((t) => t.filter((x) => x.id !== id));
}
