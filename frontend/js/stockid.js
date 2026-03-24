import { getSettings, putSetting } from './api.js';
import { showToast } from './app.js';
import { t } from './i18n.js';

export async function render() {
  const content = document.getElementById('app-content');

  const settings = await getSettings();
  const get = (key) => settings.find(s => s.key === key)?.value ?? '';

  const mode       = get('stock_id_mode');
  const prefix     = get('stock_id_prefix');
  const counter    = get('stock_id_counter');
  const padLength  = get('stock_id_pad_length');
  const webhookUrl = get('stock_id_webhook_url');

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('stockid.title')}</h1>
    </div>

    <div class="settings-radio-group">

      <label class="settings-radio-card ${mode === 'manual' ? 'selected' : ''}">
        <div class="settings-radio-card-header">
          <input type="radio" name="stock_id_mode" value="manual" ${mode === 'manual' ? 'checked' : ''} />
          <div>
            <div class="settings-radio-card-title">${t('stockid.mode_manual_title')}</div>
            <div class="settings-radio-card-desc">${t('stockid.mode_manual_desc')}</div>
          </div>
        </div>
      </label>

      <label class="settings-radio-card ${mode === 'generated' ? 'selected' : ''}">
        <div class="settings-radio-card-header">
          <input type="radio" name="stock_id_mode" value="generated" ${mode === 'generated' ? 'checked' : ''} />
          <div>
            <div class="settings-radio-card-title">${t('stockid.mode_auto_title')}</div>
            <div class="settings-radio-card-desc">${t('stockid.mode_auto_desc')}</div>
          </div>
        </div>
        <div class="settings-radio-card-body ${mode !== 'generated' ? 'hidden' : ''}" id="generated-options">
          <div class="form-row">
            <div class="form-field">
              <label for="si-prefix">${t('stockid.label_prefix')}</label>
              <input id="si-prefix" type="text" placeholder="${t('stockid.placeholder_prefix')}" maxlength="32" value="${prefix}" />
              <span class="form-hint">${t('stockid.hint_prefix')}</span>
            </div>
            <div class="form-field">
              <label for="si-counter">${t('stockid.label_counter')}</label>
              <div class="spinner-row">
                <button type="button" class="btn btn-ghost btn-sm" id="si-dec"><i data-lucide="minus"></i></button>
                <input id="si-counter" type="number" min="0" step="1" value="${counter}" />
                <button type="button" class="btn btn-ghost btn-sm" id="si-inc"><i data-lucide="plus"></i></button>
              </div>
              <span class="form-hint">${t('stockid.hint_next_id')} <strong id="si-preview"></strong></span>
            </div>
          </div>
          <div class="form-field" style="margin-top:12px">
            <label for="si-pad">${t('stockid.label_pad')}</label>
            <div class="spinner-row">
              <button type="button" class="btn btn-ghost btn-sm" id="si-pad-dec"><i data-lucide="minus"></i></button>
              <input id="si-pad" type="number" min="0" step="1" value="${padLength}" />
              <button type="button" class="btn btn-ghost btn-sm" id="si-pad-inc"><i data-lucide="plus"></i></button>
            </div>
            <span class="form-hint">${t('stockid.hint_pad')} <strong id="si-pad-preview"></strong></span>
          </div>
        </div>
      </label>

      <label class="settings-radio-card ${mode === 'extern' ? 'selected' : ''}">
        <div class="settings-radio-card-header">
          <input type="radio" name="stock_id_mode" value="extern" ${mode === 'extern' ? 'checked' : ''} />
          <div>
            <div class="settings-radio-card-title">${t('stockid.mode_extern_title')}</div>
            <div class="settings-radio-card-desc">${t('stockid.mode_extern_desc')}</div>
          </div>
        </div>
        <div class="settings-radio-card-body ${mode !== 'extern' ? 'hidden' : ''}" id="extern-options">
          <div class="form-field">
            <label for="si-webhook">${t('stockid.label_webhook')}</label>
            <input id="si-webhook" type="url" placeholder="https://example.com/generate-id?qty={quantity}"
              value="${webhookUrl}" />
            <span class="form-hint">${t('stockid.hint_webhook')}</span>
          </div>
          <div class="webhook-placeholder-table">
            <div class="webhook-placeholder-table-title">${t('stockid.placeholders_title')}</div>
            <table>
              <tbody>
                <tr><td><code>{quantity}</code></td><td>${t('stockid.ph_quantity')}</td></tr>
                <tr><td><code>{product_id}</code></td><td>${t('stockid.ph_product_id')}</td></tr>
                <tr><td><code>{vault_id}</code></td><td>${t('stockid.ph_vault_id')}</td></tr>
                <tr><td><code>{best_before_date}</code></td><td>${t('stockid.ph_bbd')}</td></tr>
                <tr><td><code>{comment}</code></td><td>${t('stockid.ph_comment')}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </label>

    </div>

    <div class="form-actions" style="margin-top:24px">
      <button class="btn btn-primary" id="btn-save-stockid">
        <i data-lucide="save"></i> ${t('stockid.btn_save')}
      </button>
    </div>`;

  lucide.createIcons();

  // ── Interactivity ──────────────────────────────────────────────────────────

  const radios     = content.querySelectorAll('input[name="stock_id_mode"]');
  const cards      = content.querySelectorAll('.settings-radio-card');
  const genOptions = content.querySelector('#generated-options');
  const extOptions = content.querySelector('#extern-options');
  const prefixIn   = content.querySelector('#si-prefix');
  const counterIn  = content.querySelector('#si-counter');
  const padIn      = content.querySelector('#si-pad');
  const webhookIn  = content.querySelector('#si-webhook');
  const preview    = content.querySelector('#si-preview');
  const padPreview = content.querySelector('#si-pad-preview');

  const updatePreview = () => {
    const next   = Number(counterIn.value) + 1;
    const pad    = Math.max(0, Number(padIn.value));
    const numStr = pad > 0 ? String(next).padStart(pad, '0') : String(next);
    if (preview)    preview.textContent    = `${prefixIn.value}${numStr}`;
    if (padPreview) padPreview.textContent = pad > 0
      ? `${prefixIn.value}${numStr}`
      : '—';
  };

  radios.forEach(radio => {
    radio.addEventListener('change', () => {
      cards.forEach(c => c.classList.toggle('selected', c.querySelector('input').value === radio.value));
      genOptions.classList.toggle('hidden', radio.value !== 'generated');
      extOptions.classList.toggle('hidden', radio.value !== 'extern');
    });
  });

  content.querySelector('#si-dec').addEventListener('click', () => {
    counterIn.value = Math.max(0, Number(counterIn.value) - 1);
    updatePreview();
  });
  content.querySelector('#si-inc').addEventListener('click', () => {
    counterIn.value = Number(counterIn.value) + 1;
    updatePreview();
  });
  content.querySelector('#si-pad-dec').addEventListener('click', () => {
    padIn.value = Math.max(0, Number(padIn.value) - 1);
    updatePreview();
  });
  content.querySelector('#si-pad-inc').addEventListener('click', () => {
    padIn.value = Number(padIn.value) + 1;
    updatePreview();
  });
  prefixIn.addEventListener('input', updatePreview);
  counterIn.addEventListener('input', updatePreview);
  padIn.addEventListener('input', updatePreview);

  updatePreview();

  content.querySelector('#btn-save-stockid').addEventListener('click', async () => {
    const selectedMode = content.querySelector('input[name="stock_id_mode"]:checked').value;
    try {
      await putSetting('stock_id_mode',        selectedMode);
      await putSetting('stock_id_prefix',      prefixIn.value.trim());
      await putSetting('stock_id_counter',     String(Math.max(0, Number(counterIn.value))));
      await putSetting('stock_id_pad_length',  String(Math.max(0, Number(padIn.value))));
      await putSetting('stock_id_webhook_url', webhookIn.value.trim());
      showToast(t('stockid.toast_saved'));
    } catch (err) {
      showToast(err.message, 'error');
    }
  });
}
