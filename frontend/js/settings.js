import { t, setLocale, getCurrentLang, applyNavTranslations } from './i18n.js';

export function render() {
  const content = document.getElementById('app-content');
  const currentLang = getCurrentLang();

  content.innerHTML = `
    <div class="page-header">
      <h1 class="page-title">${t('settings.title')}</h1>
    </div>
    <div class="settings-grid">
      <a href="#stockid" class="settings-card">
        <div class="settings-card-icon"><i data-lucide="qr-code"></i></div>
        <div>
          <div class="settings-card-title">${t('settings.stockid_title')}</div>
          <div class="settings-card-desc">${t('settings.stockid_desc')}</div>
        </div>
        <i data-lucide="chevron-right" class="settings-card-arrow"></i>
      </a>
      <a href="#vaults" class="settings-card">
        <div class="settings-card-icon"><i data-lucide="warehouse"></i></div>
        <div>
          <div class="settings-card-title">${t('settings.vaults_title')}</div>
          <div class="settings-card-desc">${t('settings.vaults_desc')}</div>
        </div>
        <i data-lucide="chevron-right" class="settings-card-arrow"></i>
      </a>
      <a href="#units" class="settings-card">
        <div class="settings-card-icon"><i data-lucide="ruler"></i></div>
        <div>
          <div class="settings-card-title">${t('settings.units_title')}</div>
          <div class="settings-card-desc">${t('settings.units_desc')}</div>
        </div>
        <i data-lucide="chevron-right" class="settings-card-arrow"></i>
      </a>
      <a href="#categories" class="settings-card">
        <div class="settings-card-icon"><i data-lucide="tag"></i></div>
        <div>
          <div class="settings-card-title">${t('settings.categories_title')}</div>
          <div class="settings-card-desc">${t('settings.categories_desc')}</div>
        </div>
        <i data-lucide="chevron-right" class="settings-card-arrow"></i>
      </a>
      <a href="#data_transfer" class="settings-card">
        <div class="settings-card-icon"><i data-lucide="hard-drive-download"></i></div>
        <div>
          <div class="settings-card-title">${t('settings.data_transfer_title')}</div>
          <div class="settings-card-desc">${t('settings.data_transfer_desc')}</div>
        </div>
        <i data-lucide="chevron-right" class="settings-card-arrow"></i>
      </a>
    </div>

    <div class="page-header" style="margin-top:32px">
      <h2 class="page-title" style="font-size:1.1rem">${t('settings.language_title')}</h2>
    </div>
    <div class="settings-radio-group">
      <label class="settings-radio-card ${currentLang === 'de' ? 'selected' : ''}">
        <div class="settings-radio-card-header">
          <input type="radio" name="app_lang" value="de" ${currentLang === 'de' ? 'checked' : ''} />
          <div>
            <div class="settings-radio-card-title">${t('settings.lang_de')}</div>
          </div>
        </div>
      </label>
      <label class="settings-radio-card ${currentLang === 'en' ? 'selected' : ''}">
        <div class="settings-radio-card-header">
          <input type="radio" name="app_lang" value="en" ${currentLang === 'en' ? 'checked' : ''} />
          <div>
            <div class="settings-radio-card-title">${t('settings.lang_en')}</div>
          </div>
        </div>
      </label>
    </div>`;

  lucide.createIcons();

  content.querySelectorAll('input[name="app_lang"]').forEach(radio => {
    radio.addEventListener('change', () => {
      setLocale(radio.value);
      applyNavTranslations();
      window.dispatchEvent(new HashChangeEvent('hashchange'));
    });
  });
}
