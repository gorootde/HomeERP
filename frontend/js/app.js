import { t, applyNavTranslations } from './i18n.js';
import * as dashboard from './dashboard.js';
import * as products   from './products.js';
import * as vaults     from './vaults.js';
import * as stockPage  from './stock.js';
import * as scanner    from './scanner.js';
import * as inventory  from './inventory.js';
import * as units      from './units.js';
import * as categories from './categories.js';
import * as settings      from './settings.js';
import * as stockid       from './stockid.js';
import * as dataTransfer  from './data_transfer.js';

const apidocs = {
  render() {
    const content = document.getElementById('app-content');
    content.innerHTML = `<iframe src="/docs" class="apidocs-frame" title="API Documentation"></iframe>`;
  }
};

const ROUTES = {
  dashboard:  dashboard,
  products:   products,
  vaults:     vaults,
  stock:      stockPage,
  scanner:    scanner,
  inventory:  inventory,
  units:      units,
  categories: categories,
  settings:      settings,
  stockid:       stockid,
  data_transfer: dataTransfer,
  apidocs:       apidocs,
};

window.AppState = {
  cleanup: null,
};

// ── Router ───────────────────────────────────────────────────────────────────
async function router() {
  if (window.AppState.cleanup) {
    try { await window.AppState.cleanup(); } catch (_) {}
    window.AppState.cleanup = null;
  }

  const hash   = location.hash.replace('#', '') || 'dashboard';
  const module = ROUTES[hash] ?? ROUTES.dashboard;

  const content = document.getElementById('app-content');
  content.innerHTML = '<div class="page-loading"><i data-lucide="loader-circle" class="spin"></i></div>';
  lucide.createIcons();

  setActiveNav(hash);

  if (typeof module.cleanup === 'function') {
    window.AppState.cleanup = module.cleanup.bind(module);
  }

  try {
    await module.render();
  } catch (err) {
    content.innerHTML = `
      <div class="empty-state">
        <i data-lucide="circle-alert"></i>
        <p>${t('common.error_load_page', { msg: escHtml(err.message) })}</p>
      </div>`;
  }
  lucide.createIcons();
}

function setActiveNav(page) {
  document.querySelectorAll('.nav-link, .tab-item').forEach(el => {
    el.classList.toggle('active', el.dataset.page === page);
  });
  const moreBtn = document.getElementById('btn-more-nav');
  if (moreBtn) moreBtn.classList.toggle('active', MORE_PAGES.has(page));
}

// Pages shown in the "more" sheet (not in primary bottom nav)
const MORE_PAGES = new Set(['inventory', 'settings', 'apidocs']);

function openMoreMenu() {
  document.getElementById('more-menu').classList.add('open');
  document.getElementById('more-menu-backdrop').classList.add('open');
}

function closeMoreMenu() {
  document.getElementById('more-menu').classList.remove('open');
  document.getElementById('more-menu-backdrop').classList.remove('open');
}

window.addEventListener('hashchange', router);
document.addEventListener('DOMContentLoaded', () => {
  applyNavTranslations();
  router();

  // More-menu toggle
  document.getElementById('btn-more-nav').addEventListener('click', () => {
    const isOpen = document.getElementById('more-menu').classList.contains('open');
    isOpen ? closeMoreMenu() : openMoreMenu();
  });

  document.getElementById('more-menu-backdrop').addEventListener('click', closeMoreMenu);

  // Close sheet when a link inside it is tapped
  document.querySelectorAll('[data-more]').forEach(link => {
    link.addEventListener('click', closeMoreMenu);
  });

  fetch('/openapi.json')
    .then(r => r.json())
    .then(data => {
      const el = document.getElementById('sidebar-version');
      if (el && data.info?.version) el.textContent = `v${data.info.version}`;
    })
    .catch(() => {});
});

// ── Modal helper ─────────────────────────────────────────────────────────────
export function openModal(titleHtml, bodyHtml, { wide = false } = {}) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `
    <div class="modal${wide ? ' modal-wide' : ''}">
      <div class="modal-header">
        <span class="modal-title">${titleHtml}</span>
        <button class="modal-close" aria-label="Close"><i data-lucide="x"></i></button>
      </div>
      <div class="modal-body">${bodyHtml}</div>
    </div>`;
  document.body.appendChild(overlay);
  lucide.createIcons();

  const close = () => overlay.remove();
  overlay.querySelector('.modal-close').addEventListener('click', close);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  return { overlay, close };
}

export function openConfirm(message, onConfirm) {
  const { overlay, close } = openModal(
    t('common.confirm_title'),
    `<div class="confirm-body">
       <i data-lucide="triangle-alert"></i>
       <p>${escHtml(message)}</p>
       <div class="confirm-actions">
         <button class="btn btn-ghost" id="confirm-cancel">${t('common.confirm_cancel')}</button>
         <button class="btn btn-danger" id="confirm-ok">${t('common.confirm_delete')}</button>
       </div>
     </div>`
  );
  lucide.createIcons();
  overlay.querySelector('#confirm-cancel').addEventListener('click', close);
  overlay.querySelector('#confirm-ok').addEventListener('click', () => {
    close();
    onConfirm();
  });
}

// ── Toast helper ─────────────────────────────────────────────────────────────
export function showToast(message, type = 'success') {
  const icon = type === 'success' ? 'circle-check' : type === 'error' ? 'circle-x' : 'info';
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<i data-lucide="${icon}"></i><span>${escHtml(message)}</span>`;
  container.appendChild(toast);
  lucide.createIcons({ nodes: [toast] });
  requestAnimationFrame(() => { requestAnimationFrame(() => toast.classList.add('show')); });
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 350);
  }, 3200);
}

// ── Utilities ─────────────────────────────────────────────────────────────────
export function escHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function fmtQty(n) {
  return Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/\.?0+$/, '');
}

export function fmtDate(d) {
  if (!d) return '—';
  return new Date(d + 'T00:00:00').toLocaleDateString(undefined, { dateStyle: 'medium' });
}

export function fmtFactor(n) {
  return parseFloat(n.toPrecision(10)).toString();
}

// ── Shared unit / tag helpers ──────────────────────────────────────────────────

/**
 * Builds <option> elements for a unit <select>.
 * @param {Array}  units       - array of unit objects { id, name, abbreviation }
 * @param {number} selectedId  - currently selected unit id (or null)
 * @param {object} [opts]
 * @param {string} [opts.placeholder='Einheit wählen…']
 * @param {boolean}[opts.nullable=false]  - if true the placeholder is selectable (not disabled)
 */
export function buildUnitOptions(units, selectedId, { placeholder = null, nullable = false } = {}) {
  placeholder = placeholder ?? t('common.unit_placeholder');
  const first = nullable
    ? `<option value=""${!selectedId ? ' selected' : ''}>${escHtml(placeholder)}</option>`
    : `<option value="" disabled${!selectedId ? ' selected' : ''}>${escHtml(placeholder)}</option>`;
  return first + units.map(u =>
    `<option value="${u.id}"${u.id === selectedId ? ' selected' : ''}>${escHtml(u.name)} (${escHtml(u.abbreviation)})</option>`
  ).join('');
}

export function renderTagChips(tags) {
  if (!tags || tags.length === 0) return '<span class="text-muted text-sm">—</span>';
  return tags.map(t => `<span class="item-tag">${escHtml(t.name)}</span>`).join('');
}

export function buildTagList(tags) {
  return (tags || []).map(t => `
    <span class="item-tag item-tag--removable" data-tag-name="${escHtml(t.name)}">
      ${escHtml(t.name)}
      <button type="button" title="Remove" data-remove-tag="${escHtml(t.name)}">
        <i data-lucide="x"></i>
      </button>
    </span>`).join('');
}

export function buildTagsSection(tags) {
  return `
    <div class="form-field">
      <label>${t('common.tags_label')}</label>
      <div class="tag-manager">
        <div class="tag-manager-list" id="tag-list">${buildTagList(tags)}</div>
        <div class="ean-add-row">
          <input id="tag-input" type="text" placeholder="${t('common.tag_input_placeholder')}" list="tag-suggestions" autocomplete="off" />
          <datalist id="tag-suggestions"></datalist>
          <button type="button" class="btn btn-ghost btn-sm" id="btn-add-tag">
            <i data-lucide="plus"></i> ${t('common.tag_add')}
          </button>
        </div>
      </div>
    </div>`;
}

/**
 * Wires up add/remove tag interactions inside a modal overlay.
 * @param {Element}  overlay       - modal overlay element
 * @param {Array}    initialTags   - current tags on the entity
 * @param {number}   entityId      - id of the entity being edited
 * @param {Function} addFn         - (entityId, name) => Promise<tag>
 * @param {Function} removeFn      - (entityId, name) => Promise<void>
 * @param {Array}    allTags       - mutable global tag list for datalist suggestions
 */
export function attachTagListeners(overlay, initialTags, entityId, addFn, removeFn, allTags) {
  const tagList  = overlay.querySelector('#tag-list');
  const tagInput = overlay.querySelector('#tag-input');
  const datalist = overlay.querySelector('#tag-suggestions');
  if (!tagList || !tagInput) return;

  let tags = [...(initialTags || [])];

  if (datalist && allTags) {
    datalist.innerHTML = allTags.map(t => `<option value="${escHtml(t.name)}">`).join('');
  }

  const refreshList = () => {
    tagList.innerHTML = buildTagList(tags);
    lucide.createIcons({ nodes: [tagList] });
    attachRemoveListeners();
  };

  const attachRemoveListeners = () => {
    tagList.querySelectorAll('[data-remove-tag]').forEach(btn => {
      btn.addEventListener('click', async () => {
        const name = btn.dataset.removeTag;
        try {
          await removeFn(entityId, name);
          tags = tags.filter(t => t.name !== name);
          refreshList();
        } catch (err) {
          showToast(err.message, 'error');
        }
      });
    });
  };
  attachRemoveListeners();

  const addTagHandler = async () => {
    const name = tagInput.value.trim();
    if (!name) return;
    if (tags.find(t => t.name === name)) { tagInput.value = ''; return; }
    try {
      const newTag = await addFn(entityId, name);
      tags.push(newTag);
      tagInput.value = '';
      refreshList();
      if (datalist && allTags && !allTags.find(t => t.name === name)) {
        allTags.push(newTag);
        datalist.innerHTML = allTags.map(t => `<option value="${escHtml(t.name)}">`).join('');
      }
    } catch (err) {
      showToast(err.message, 'error');
    }
  };

  overlay.querySelector('#btn-add-tag').addEventListener('click', addTagHandler);
  tagInput.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); addTagHandler(); } });
}
