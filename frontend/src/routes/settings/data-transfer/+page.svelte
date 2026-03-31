<script>
  import { onMount } from 'svelte';
  import { t } from '$lib/i18n.js';
  import { showToast } from '$lib/toast.js';
  import { getExportModels, previewImport, applyImport } from '$lib/api.js';
  import { ChevronLeft, Download, Upload } from 'lucide-svelte';

  let models = $state([]);
  let selectedModels = $state([]);
  let includeImages = $state(true);
  let exporting = $state(false);

  let importFile = $state(null);
  let importPreview = $state(null);
  let importId = $state(null);
  let loadingPreview = $state(false);
  let importing = $state(false);

  onMount(async () => {
    models = await getExportModels();
  });

  function toggleModel(name) {
    if (selectedModels.includes(name)) {
      selectedModels = selectedModels.filter(m => m !== name);
    } else {
      selectedModels = [...selectedModels, name];
    }
  }

  function selectAll() {
    selectedModels = models.map(m => m.name || m);
  }

  async function doExport() {
    if (selectedModels.length === 0) { showToast(t('data_transfer.toast_nothing_selected'), 'error'); return; }
    exporting = true;
    try {
      const tables = includeImages ? [...selectedModels, 'images'] : selectedModels;
      const res = await fetch('/api/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tables })
      });
      if (!res.ok) throw new Error(await res.text());
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `homeerp-export-${new Date().toISOString().slice(0, 10)}.zip`;
      a.click();
      URL.revokeObjectURL(url);
      showToast(t('data_transfer.toast_exported'), 'success');
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      exporting = false;
    }
  }

  async function handleImportFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    importFile = file;
    importPreview = null;
    importId = null;
    loadingPreview = true;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const preview = await previewImport(fd);
      importPreview = preview.tables || [];
      importId = preview.import_id;
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      loadingPreview = false;
    }
  }

  async function doImport() {
    if (!importId) return;
    importing = true;
    try {
      await applyImport(importId);
      showToast(t('data_transfer.toast_import_done'), 'success');
      importPreview = null;
      importId = null;
      importFile = null;
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      importing = false;
    }
  }

  const statusColors = {
    ok: 'text-green-600', error: 'text-red-600', skipped: 'text-gray-400',
    known: 'text-blue-600', unknown: 'text-amber-600'
  };
</script>

<div class="px-4 md:px-6 py-5 max-w-2xl">
  <div class="flex items-center gap-3 mb-5">
    <a href="/settings" class="p-1.5 rounded-lg hover:bg-gray-100 text-gray-500"><ChevronLeft size={20} /></a>
    <h1 class="text-xl font-bold text-gray-900">{t('data_transfer.title')}</h1>
  </div>

  <!-- Export -->
  <div class="bg-white rounded-xl border border-gray-200 p-5 mb-4">
    <div class="flex items-center gap-2 mb-1">
      <Download size={18} class="text-gray-600" />
      <h2 class="text-sm font-semibold text-gray-900">{t('data_transfer.export_title')}</h2>
    </div>
    <p class="text-xs text-gray-500 mb-4">{t('data_transfer.export_desc')}</p>

    <div class="flex justify-between items-center mb-2">
      <p class="text-xs font-medium text-gray-700">Tables</p>
      <button onclick={selectAll} class="text-xs text-blue-600 hover:underline">{t('data_transfer.select_all')}</button>
    </div>
    <div class="grid grid-cols-2 gap-1.5 mb-3">
      {#each models as model}
        {@const name = model.name || model}
        <label class="flex items-center gap-2 text-sm cursor-pointer hover:text-gray-900">
          <input type="checkbox" checked={selectedModels.includes(name)} onchange={() => toggleModel(name)}
            class="rounded border-gray-300" />
          <span class="text-gray-700">{name}</span>
        </label>
      {/each}
    </div>
    <label class="flex items-center gap-2 text-sm mb-3 cursor-pointer">
      <input type="checkbox" bind:checked={includeImages} class="rounded border-gray-300" />
      <span class="text-gray-700">{t('data_transfer.images_label')}</span>
    </label>
    <button onclick={doExport} disabled={exporting}
      class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
      <Download size={16} />
      {exporting ? t('data_transfer.exporting') : t('data_transfer.btn_export')}
    </button>
  </div>

  <!-- Import -->
  <div class="bg-white rounded-xl border border-gray-200 p-5">
    <div class="flex items-center gap-2 mb-1">
      <Upload size={18} class="text-gray-600" />
      <h2 class="text-sm font-semibold text-gray-900">{t('data_transfer.import_title')}</h2>
    </div>
    <p class="text-xs text-gray-500 mb-4">{t('data_transfer.import_desc')}</p>

    <input type="file" accept=".zip" onchange={handleImportFile}
      class="text-sm text-gray-600 file:mr-3 file:px-3 file:py-1.5 file:text-sm file:font-medium file:bg-gray-100 file:border file:border-gray-300 file:rounded-lg file:cursor-pointer" />

    {#if loadingPreview}
      <p class="text-sm text-gray-500 mt-3">{t('data_transfer.loading_preview')}</p>
    {/if}

    {#if importPreview}
      <div class="mt-4 bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-gray-200 bg-gray-50">
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('data_transfer.col_model')}</th>
                <th class="text-right px-4 py-2.5 text-xs font-semibold text-gray-500">{t('data_transfer.col_rows')}</th>
                <th class="text-left px-4 py-2.5 text-xs font-semibold text-gray-500">{t('data_transfer.col_status')}</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              {#each importPreview as row}
                <tr>
                  <td class="px-4 py-2.5 font-medium text-gray-900">{row.model}</td>
                  <td class="px-4 py-2.5 text-right text-gray-600">{row.rows ?? row.count ?? '—'}</td>
                  <td class="px-4 py-2.5">
                    <span class={`text-xs font-medium ${statusColors[row.status] || 'text-gray-500'}`}>
                      {t(`data_transfer.status_${row.status}`) || row.status}
                    </span>
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      </div>
      <button onclick={doImport} disabled={importing}
        class="mt-3 flex items-center gap-2 px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50">
        <Upload size={16} />
        {importing ? t('data_transfer.importing') : t('data_transfer.btn_import')}
      </button>
    {/if}
  </div>
</div>
