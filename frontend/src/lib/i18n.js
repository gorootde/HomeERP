import { writable, derived, get } from 'svelte/store';

const de = {
  common: {
    cancel: 'Abbrechen', save: 'Speichern', create: 'Erstellen', edit: 'Bearbeiten',
    delete: 'Löschen', add: 'Hinzufügen', done: 'Fertig', close: 'Schließen', default: 'Standard',
    empty_dash: '—', confirm_title: 'Bestätigen', confirm_delete: 'Wirklich löschen?',
    confirm_cancel: 'Abbrechen', unit_placeholder: 'Einheit wählen…', no_category: 'Keine Kategorie',
    tags_label: 'Tags', tag_input_placeholder: 'Tag eingeben…', tag_add: 'Hinzufügen',
    error_load_page: 'Seite konnte nicht geladen werden', camera_unavailable: 'Kamera nicht verfügbar',
    scanner_unavailable: 'Scanner nicht verfügbar', optional: 'optional'
  },
  nav: {
    dashboard: 'Dashboard', products: 'Produkte', stock: 'Lager', scanner: 'Scanner',
    inventory: 'Inventur', settings: 'Einstellungen', apidocs: 'API Docs',
    more: 'Mehr', home: 'Home', scan: 'Scan'
  },
  dashboard: {
    title: 'Dashboard', products_in_stock: 'Produkte im Lager', total_stock: 'Gesamtbestand',
    storage_locations: 'Lagerorte', critical: 'Kritisch', low: 'Gering', cat_suffix: '',
    section_by_category: 'Nach Kategorie', section_all_products: 'Alle Produkte',
    col_product: 'Produkt', col_vendor: 'Hersteller', col_size: 'Größe',
    col_total_qty: 'Gesamt', col_by_vault: 'Nach Lagerort', empty: 'Kein Bestand vorhanden',
    status_ok: 'OK', status_low: 'Gering', status_critical: 'Kritisch', status_none: 'Kein Mindestbestand'
  },
  products: {
    title: 'Produkte', btn_add: 'Produkt hinzufügen', search_placeholder: 'Suche nach Name oder Hersteller…',
    col_product: 'Produkt', col_size: 'Größe', col_eans: 'EAN-Codes', col_tags: 'Tags', empty: 'Keine Produkte',
    btn_edit: 'Bearbeiten', btn_eans: 'EAN-Codes', confirm_delete: 'Produkt wirklich löschen?',
    toast_deleted: 'Produkt gelöscht', toast_updated: 'Produkt gespeichert', toast_created: 'Produkt erstellt',
    modal_edit: 'Produkt bearbeiten', modal_add: 'Neues Produkt',
    label_vendor: 'Hersteller', label_size: 'Standardmenge pro Stück', label_unit: 'Bestandseinheit', label_entry_unit: 'Erfassen Einheit', label_entry_unit_hint: 'Standard-Einheit beim Erfassen von Beständen', label_category: 'Kategorie',
    label_name: 'Name', placeholder_vendor: 'Hersteller', placeholder_size: 'z.B. 160',
    placeholder_name: 'Produktname', label_photo: 'Foto', photo_placeholder: 'Kein Foto',
    btn_remove_photo: 'Foto entfernen', toast_photo_removed: 'Foto entfernt',
    ean_modal_title: 'EAN-Codes verwalten', ean_modal_hint: 'Scanne oder gib EAN-Codes ein',
    ean_placeholder: 'EAN-Code', ean_btn_stop: 'Scanner stoppen', ean_btn_done: 'Fertig',
    ean_toast_removed: 'EAN entfernt', ean_toast_added: 'EAN hinzugefügt',
    off_loading: 'Lade Produktinfos…', off_found: 'Produkt gefunden',
    off_replace_q: 'Produktdaten ersetzen?', off_use_q: 'Gefundene Daten verwenden?',
    off_btn_replace: 'Ersetzen', off_btn_use: 'Verwenden', off_btn_dismiss: 'Verwerfen',
    off_saving: 'Speichere…', off_saved: 'Gespeichert', off_toast_saved: 'Foto gespeichert',
    off_banner_label: 'OpenFoodFacts', off_banner_hint: 'Produktdaten aus OpenFoodFacts',
    puc_label: 'Einheitenkonvertierungen', puc_empty: 'Keine Konvertierungen',
    puc_name_placeholder: 'z.B. Flasche', puc_toast_removed: 'Konvertierung entfernt',
    puc_err_name: 'Name erforderlich', puc_err_factor: 'Faktor ungültig', puc_err_unit: 'Einheit wählen',
    puc_toast_added: 'Konvertierung hinzugefügt'
  },
  vaults: {
    title: 'Lagerorte', btn_add: 'Lagerort hinzufügen', col_id: 'ID', col_description: 'Beschreibung',
    col_tags: 'Tags', empty: 'Keine Lagerorte', confirm_delete: 'Lagerort wirklich löschen?',
    toast_deleted: 'Lagerort gelöscht', modal_edit: 'Lagerort bearbeiten', modal_add: 'Neuer Lagerort',
    label_desc: 'Beschreibung', placeholder_desc: 'z.B. Keller', toast_updated: 'Lagerort gespeichert',
    toast_created: 'Lagerort erstellt'
  },
  stock: {
    title: 'Lagerbestand', btn_add: 'Eintrag hinzufügen', filter_all_vaults: 'Alle Lagerorte',
    filter_all_products: 'Alle Produkte', filter_expiry_all: 'Alle MHDs', filter_expiry_7d: 'Nächste 7 Tage',
    filter_expiry_30d: 'Nächste 30 Tage', filter_expiry_6m: 'Nächste 6 Monate',
    col_product: 'Produkt', col_vault: 'Lagerort', col_qty: 'Menge', col_bbd: 'MHD',
    col_comment: 'Kommentar', col_stockids: 'Stock IDs', empty: 'Kein Bestand',
    empty_filter: 'Keine Treffer für diesen Filter', confirm_delete: 'Eintrag wirklich löschen?',
    toast_deleted: 'Eintrag gelöscht', toast_updated: 'Eintrag gespeichert', toast_added: 'Eintrag hinzugefügt',
    modal_edit: 'Eintrag bearbeiten', modal_add: 'Neuer Eintrag', label_product: 'Produkt',
    label_vault: 'Lagerort', label_qty: 'Menge', label_bbd: 'MHD', label_comment: 'Kommentar',
    select_product: 'Produkt wählen…', select_vault: 'Lagerort wählen…', placeholder_comment: 'Kommentar',
    stockid_modal_title: 'Stock IDs verwalten', stockid_modal_hint: 'Scanne oder gib Stock IDs ein',
    stockid_placeholder: 'Stock ID', stockid_btn_scan: 'Scannen', stockid_btn_add: 'Hinzufügen',
    stockid_btn_stop: 'Scanner stoppen', stockid_btn_done: 'Fertig',
    stockid_toast_removed: 'Stock ID entfernt', stockid_toast_added: 'Stock ID hinzugefügt'
  },
  units: {
    title: 'Einheiten', btn_add: 'Einheit hinzufügen', col_id: 'ID', col_name: 'Name',
    col_abbr: 'Kürzel', col_conversions: 'Konvertierungen', empty: 'Keine Einheiten',
    conv_count_singular: 'Konvertierung', conv_count_plural: 'Konvertierungen', btn_edit: 'Bearbeiten',
    confirm_delete: 'Einheit wirklich löschen?', toast_deleted: 'Einheit gelöscht',
    conv_empty: 'Keine Konvertierungen', conv_col_factor: 'Faktor', conv_col_target: 'Zieleinheit',
    modal_edit: 'Einheit bearbeiten', modal_add: 'Neue Einheit', label_name: 'Name',
    placeholder_name: 'z.B. Kilogramm', label_abbr: 'Kürzel', placeholder_abbr: 'z.B. kg',
    label_conversions: 'Konvertierungen', conv_placeholder_factor: 'Faktor', conv_btn_add: 'Hinzufügen',
    conv_preview: '1 {from} = {factor} {to}', conv_no_other_units: 'Keine anderen Einheiten',
    toast_conv_deleted: 'Konvertierung entfernt', toast_conv_err_factor: 'Ungültiger Faktor',
    toast_conv_saved: 'Konvertierung gespeichert', toast_saved: 'Einheit gespeichert',
    toast_created: 'Einheit erstellt'
  },
  categories: {
    title: 'Kategorien', btn_add: 'Kategorie hinzufügen', col_name: 'Name', col_min_stock: 'Mindestbestand',
    empty: 'Keine Kategorien', btn_edit: 'Bearbeiten', confirm_delete: 'Kategorie wirklich löschen?',
    toast_deleted: 'Kategorie gelöscht', modal_edit: 'Kategorie bearbeiten', modal_add: 'Neue Kategorie',
    label_name: 'Name', placeholder_name: 'z.B. Getränke', label_min_qty: 'Mindestmenge',
    placeholder_min_qty: '0', label_unit: 'Einheit', toast_saved: 'Kategorie gespeichert',
    toast_created: 'Kategorie erstellt'
  },
  inventory: {
    title: 'Inventur', step_select_heading: 'Lagerort auswählen', label_vault: 'Lagerort',
    select_vault: 'Lagerort wählen…', btn_start: 'Inventur starten', counting_title: 'Zählen',
    tally_scans: 'Scans', tally_products: 'Produkte', tally_expected: 'Erwartet',
    feedback_initial: 'Bereit zum Scannen', btn_start_scanner: 'Scanner starten',
    btn_stop_scanner: 'Scanner stoppen', btn_finish: 'Abschließen', btn_cancel: 'Abbrechen',
    feedback_stopped: 'Scanner gestoppt', feedback_scanning: 'Scanne…',
    feedback_camera_unavailable: 'Kamera nicht verfügbar', feedback_camera_fallback: 'Kamera-Fallback aktiv',
    feedback_scanned: 'Gescannt: {name}', feedback_unknown_ean: 'Unbekannte EAN: {ean}',
    result_title: 'Ergebnis', col_product: 'Produkt', col_expected: 'Erwartet', col_scanned: 'Gescannt',
    col_diff: 'Diff', col_status: 'Status', empty: 'Kein Ergebnis', btn_update_db: 'In DB speichern',
    btn_apply_all: 'Alle übernehmen', btn_new: 'Neue Inventur', status_ok: 'OK',
    status_missing: 'Fehlend', status_extra: 'Überschuss', status_unexpected: 'Unbekannt',
    unknown_eans_prefix: 'Unbekannte EANs: ', toast_applied: 'Gespeichert', toast_updated: 'Aktualisiert'
  },
  scanner: {
    title: 'Scanner', status_starting: 'Starte…', status_active: 'Aktiv', status_searching: 'Suche…',
    err_lib_not_loaded: 'Scanner-Bibliothek nicht geladen', err_camera_api: 'Kamera-API nicht verfügbar',
    err_camera_denied: 'Kamera-Zugriff verweigert', err_camera_unavailable: 'Kamera nicht verfügbar',
    stockid_badge: 'Stock ID', stockid_found: 'Stock ID gefunden',
    label_location: 'Lagerort', label_stock: 'Bestand', label_bbd: 'MHD',
    btn_consume: 'Verbrauchen', btn_adjust: 'Anpassen', btn_continue: 'Weiter scannen',
    toast_consumed_deleted: 'Verbraucht & gelöscht', toast_consumed: 'Verbraucht ({qty})',
    stockid_not_found: 'Stock ID nicht gefunden', stockid_not_found_hint: 'Kein Eintrag für diese ID',
    adjust_modal_title: 'Menge anpassen', label_new_qty: 'Neue Menge', err_invalid_qty: 'Ungültige Menge',
    toast_qty_updated: 'Menge aktualisiert', ean_found: 'Produkt gefunden',
    ean_unknown_status: 'Unbekanntes Produkt', ean_unknown_heading: 'Unbekannte EAN',
    ean_unknown_hint: 'EAN nicht in der Datenbank',
    btn_new_product: 'Neues Produkt', new_product_modal: 'Neues Produkt erstellen',
    label_name: 'Name', placeholder_name: 'Produktname', label_vendor: 'Hersteller',
    placeholder_vendor: 'Hersteller', label_size: 'Standardmenge pro Stück', placeholder_size: 'z.B. 160',
    label_unit: 'Einheit', unit_placeholder: 'Einheit wählen…', label_category: 'Kategorie',
    label_ean: 'EAN', placeholder_ean: 'EAN-Code', ean_hint: 'EAN wird automatisch zugeordnet',
    btn_create_product: 'Produkt erstellen', toast_product_created: 'Produkt erstellt',
    stock_entry_modal: 'Lagereintrag hinzufügen', label_vault: 'Lagerort', select_vault: 'Lagerort wählen…',
    label_qty: 'Menge', label_bbd_form: 'MHD', label_comment: 'Kommentar',
    placeholder_comment: 'Kommentar', btn_add_entry: 'Eintrag hinzufügen',
    toast_entry_created: 'Eintrag erstellt', off_banner_label: 'OpenFoodFacts', off_banner_hint: 'Daten aus OpenFoodFacts',
    hint_ean_title: 'EAN / Barcode', hint_ean_desc: 'Sucht das zugehörige Produkt und öffnet den Dialog für einen neuen Bestandseintrag. Unbekannte Codes können direkt als neues Produkt angelegt werden.',
    hint_stockid_title: 'Stock ID ({prefix}…)', hint_stockid_desc: 'Öffnet den Bestandseintrag direkt — Menge entnehmen oder anpassen.'
  },
  settings: {
    title: 'Einstellungen', stockid_title: 'Stock ID', stockid_desc: 'Konfiguriere die Stock ID-Generierung',
    vaults_title: 'Lagerorte', vaults_desc: 'Verwalte deine Lagerorte',
    units_title: 'Einheiten', units_desc: 'Verwalte Maßeinheiten',
    categories_title: 'Kategorien', categories_desc: 'Verwalte Produktkategorien',
    data_transfer_title: 'Datentransfer', data_transfer_desc: 'Importiere oder exportiere Daten',
    language_title: 'Sprache', language_desc: 'Wähle deine bevorzugte Sprache',
    lang_de: 'Deutsch', lang_en: 'English'
  },
  data_transfer: {
    title: 'Datentransfer', export_title: 'Export', export_desc: 'Exportiere Daten als ZIP',
    select_all: 'Alle auswählen', btn_export: 'Exportieren', exporting: 'Exportiere…',
    toast_nothing_selected: 'Nichts ausgewählt', toast_exported: 'Export erfolgreich',
    import_title: 'Import', import_desc: 'Importiere Daten aus ZIP', import_drop_label: 'ZIP-Datei auswählen',
    btn_preview: 'Vorschau', btn_import: 'Importieren', loading_preview: 'Lade Vorschau…',
    importing: 'Importiere…', col_model: 'Tabelle', col_rows: 'Zeilen', col_imported: 'Importiert',
    col_total: 'Gesamt', col_status: 'Status', status_known: 'Bekannt', status_unknown: 'Unbekannt',
    status_ok: 'OK', status_error: 'Fehler', status_skipped: 'Übersprungen',
    toast_import_done: 'Import abgeschlossen', toast_import_with_errors: 'Import mit Fehlern',
    images_label: 'Produktbilder', export_images_hint: 'Bilder werden im ZIP enthalten'
  },
  stockid: {
    title: 'Stock ID Konfiguration', mode_manual_title: 'Manuell', mode_manual_desc: 'IDs manuell eingeben oder scannen',
    mode_auto_title: 'Automatisch', mode_auto_desc: 'IDs automatisch generieren',
    label_prefix: 'Präfix', placeholder_prefix: 'z.B. S-', hint_prefix: 'Präfix für Stock IDs',
    label_counter: 'Zähler', hint_next_id: 'Nächste ID: {id}', label_pad: 'Auffüllen auf',
    hint_pad: 'Stellen mit führenden Nullen', mode_extern_title: 'Extern (Webhook)',
    mode_extern_desc: 'IDs via Webhook generieren', label_webhook: 'Webhook-URL', hint_webhook: 'URL zum Aufrufen',
    placeholders_title: 'Platzhalter', ph_quantity: '{quantity} – Menge', ph_product_id: '{product_id} – Produkt-ID',
    ph_vault_id: '{vault_id} – Lagerort-ID', ph_bbd: '{bbd} – MHD', ph_comment: '{comment} – Kommentar',
    btn_save: 'Speichern', toast_saved: 'Einstellungen gespeichert'
  }
};

const en = {
  common: {
    cancel: 'Cancel', save: 'Save', create: 'Create', edit: 'Edit', delete: 'Delete', add: 'Add',
    done: 'Done', close: 'Close', default: 'Default', empty_dash: '—', confirm_title: 'Confirm',
    confirm_delete: 'Really delete?', confirm_cancel: 'Cancel', unit_placeholder: 'Choose unit…',
    no_category: 'No category', tags_label: 'Tags', tag_input_placeholder: 'Enter tag…', tag_add: 'Add',
    error_load_page: 'Could not load page', camera_unavailable: 'Camera not available',
    scanner_unavailable: 'Scanner not available', optional: 'optional'
  },
  nav: {
    dashboard: 'Dashboard', products: 'Products', stock: 'Stock', scanner: 'Scanner',
    inventory: 'Inventory', settings: 'Settings', apidocs: 'API Docs', more: 'More', home: 'Home', scan: 'Scan'
  },
  dashboard: {
    title: 'Dashboard', products_in_stock: 'Products in Stock', total_stock: 'Total Stock',
    storage_locations: 'Storage Locations', critical: 'Critical', low: 'Low', cat_suffix: '',
    section_by_category: 'By Category', section_all_products: 'All Products',
    col_product: 'Product', col_vendor: 'Vendor', col_size: 'Size',
    col_total_qty: 'Total', col_by_vault: 'By Vault', empty: 'No stock entries',
    status_ok: 'OK', status_low: 'Low', status_critical: 'Critical', status_none: 'No minimum stock'
  },
  products: {
    title: 'Products', btn_add: 'Add Product', search_placeholder: 'Search by name or vendor…',
    col_product: 'Product', col_size: 'Size', col_eans: 'EAN Codes', col_tags: 'Tags', empty: 'No products',
    btn_edit: 'Edit', btn_eans: 'EAN Codes', confirm_delete: 'Really delete product?',
    toast_deleted: 'Product deleted', toast_updated: 'Product saved', toast_created: 'Product created',
    modal_edit: 'Edit Product', modal_add: 'New Product',
    label_vendor: 'Vendor', label_size: 'Default Qty per Piece', label_unit: 'Stock Unit', label_entry_unit: 'Entry Unit', label_entry_unit_hint: 'Default unit when adding stock entries', label_category: 'Category',
    label_name: 'Name', placeholder_vendor: 'Vendor', placeholder_size: 'e.g. 160',
    placeholder_name: 'Product name', label_photo: 'Photo', photo_placeholder: 'No photo',
    btn_remove_photo: 'Remove photo', toast_photo_removed: 'Photo removed',
    ean_modal_title: 'Manage EAN Codes', ean_modal_hint: 'Scan or enter EAN codes',
    ean_placeholder: 'EAN code', ean_btn_stop: 'Stop scanner', ean_btn_done: 'Done',
    ean_toast_removed: 'EAN removed', ean_toast_added: 'EAN added',
    off_loading: 'Loading product info…', off_found: 'Product found',
    off_replace_q: 'Replace product data?', off_use_q: 'Use found data?',
    off_btn_replace: 'Replace', off_btn_use: 'Use', off_btn_dismiss: 'Dismiss',
    off_saving: 'Saving…', off_saved: 'Saved', off_toast_saved: 'Photo saved',
    off_banner_label: 'OpenFoodFacts', off_banner_hint: 'Product data from OpenFoodFacts',
    puc_label: 'Unit Conversions', puc_empty: 'No conversions',
    puc_name_placeholder: 'e.g. Bottle', puc_toast_removed: 'Conversion removed',
    puc_err_name: 'Name required', puc_err_factor: 'Invalid factor', puc_err_unit: 'Choose unit',
    puc_toast_added: 'Conversion added'
  },
  vaults: {
    title: 'Vaults', btn_add: 'Add Vault', col_id: 'ID', col_description: 'Description',
    col_tags: 'Tags', empty: 'No vaults', confirm_delete: 'Really delete vault?',
    toast_deleted: 'Vault deleted', modal_edit: 'Edit Vault', modal_add: 'New Vault',
    label_desc: 'Description', placeholder_desc: 'e.g. Basement', toast_updated: 'Vault saved',
    toast_created: 'Vault created'
  },
  stock: {
    title: 'Stock', btn_add: 'Add Entry', filter_all_vaults: 'All Vaults',
    filter_all_products: 'All Products', filter_expiry_all: 'All dates', filter_expiry_7d: 'Next 7 days',
    filter_expiry_30d: 'Next 30 days', filter_expiry_6m: 'Next 6 months',
    col_product: 'Product', col_vault: 'Vault', col_qty: 'Qty', col_bbd: 'Best Before',
    col_comment: 'Comment', col_stockids: 'Stock IDs', empty: 'No stock entries',
    empty_filter: 'No entries match this filter', confirm_delete: 'Really delete entry?',
    toast_deleted: 'Entry deleted', toast_updated: 'Entry saved', toast_added: 'Entry added',
    modal_edit: 'Edit Entry', modal_add: 'New Entry', label_product: 'Product',
    label_vault: 'Vault', label_qty: 'Quantity', label_bbd: 'Best Before', label_comment: 'Comment',
    select_product: 'Choose product…', select_vault: 'Choose vault…', placeholder_comment: 'Comment',
    stockid_modal_title: 'Manage Stock IDs', stockid_modal_hint: 'Scan or enter Stock IDs',
    stockid_placeholder: 'Stock ID', stockid_btn_scan: 'Scan', stockid_btn_add: 'Add',
    stockid_btn_stop: 'Stop scanner', stockid_btn_done: 'Done',
    stockid_toast_removed: 'Stock ID removed', stockid_toast_added: 'Stock ID added'
  },
  units: {
    title: 'Units', btn_add: 'Add Unit', col_id: 'ID', col_name: 'Name',
    col_abbr: 'Abbr', col_conversions: 'Conversions', empty: 'No units',
    conv_count_singular: 'conversion', conv_count_plural: 'conversions', btn_edit: 'Edit',
    confirm_delete: 'Really delete unit?', toast_deleted: 'Unit deleted',
    conv_empty: 'No conversions', conv_col_factor: 'Factor', conv_col_target: 'Target Unit',
    modal_edit: 'Edit Unit', modal_add: 'New Unit', label_name: 'Name',
    placeholder_name: 'e.g. Kilogram', label_abbr: 'Abbreviation', placeholder_abbr: 'e.g. kg',
    label_conversions: 'Conversions', conv_placeholder_factor: 'Factor', conv_btn_add: 'Add',
    conv_preview: '1 {from} = {factor} {to}', conv_no_other_units: 'No other units',
    toast_conv_deleted: 'Conversion removed', toast_conv_err_factor: 'Invalid factor',
    toast_conv_saved: 'Conversion saved', toast_saved: 'Unit saved', toast_created: 'Unit created'
  },
  categories: {
    title: 'Categories', btn_add: 'Add Category', col_name: 'Name', col_min_stock: 'Min Stock',
    empty: 'No categories', btn_edit: 'Edit', confirm_delete: 'Really delete category?',
    toast_deleted: 'Category deleted', modal_edit: 'Edit Category', modal_add: 'New Category',
    label_name: 'Name', placeholder_name: 'e.g. Beverages', label_min_qty: 'Min Quantity',
    placeholder_min_qty: '0', label_unit: 'Unit', toast_saved: 'Category saved', toast_created: 'Category created'
  },
  inventory: {
    title: 'Inventory', step_select_heading: 'Select Vault', label_vault: 'Vault',
    select_vault: 'Choose vault…', btn_start: 'Start Inventory', counting_title: 'Counting',
    tally_scans: 'Scans', tally_products: 'Products', tally_expected: 'Expected',
    feedback_initial: 'Ready to scan', btn_start_scanner: 'Start Scanner',
    btn_stop_scanner: 'Stop Scanner', btn_finish: 'Finish', btn_cancel: 'Cancel',
    feedback_stopped: 'Scanner stopped', feedback_scanning: 'Scanning…',
    feedback_camera_unavailable: 'Camera not available', feedback_camera_fallback: 'Camera fallback active',
    feedback_scanned: 'Scanned: {name}', feedback_unknown_ean: 'Unknown EAN: {ean}',
    result_title: 'Result', col_product: 'Product', col_expected: 'Expected', col_scanned: 'Scanned',
    col_diff: 'Diff', col_status: 'Status', empty: 'No results', btn_update_db: 'Save to DB',
    btn_apply_all: 'Apply All', btn_new: 'New Inventory', status_ok: 'OK',
    status_missing: 'Missing', status_extra: 'Extra', status_unexpected: 'Unknown',
    unknown_eans_prefix: 'Unknown EANs: ', toast_applied: 'Saved', toast_updated: 'Updated'
  },
  scanner: {
    title: 'Scanner', status_starting: 'Starting…', status_active: 'Active', status_searching: 'Searching…',
    err_lib_not_loaded: 'Scanner library not loaded', err_camera_api: 'Camera API not available',
    err_camera_denied: 'Camera access denied', err_camera_unavailable: 'Camera not available',
    stockid_badge: 'Stock ID', stockid_found: 'Stock ID found',
    label_location: 'Location', label_stock: 'Stock', label_bbd: 'Best Before',
    btn_consume: 'Consume', btn_adjust: 'Adjust', btn_continue: 'Continue Scanning',
    toast_consumed_deleted: 'Consumed & deleted', toast_consumed: 'Consumed ({qty})',
    stockid_not_found: 'Stock ID not found', stockid_not_found_hint: 'No entry for this ID',
    adjust_modal_title: 'Adjust Quantity', label_new_qty: 'New Quantity', err_invalid_qty: 'Invalid quantity',
    toast_qty_updated: 'Quantity updated', ean_found: 'Product found',
    ean_unknown_status: 'Unknown product', ean_unknown_heading: 'Unknown EAN',
    ean_unknown_hint: 'EAN not in database', btn_new_product: 'New Product',
    new_product_modal: 'Create New Product', label_name: 'Name', placeholder_name: 'Product name',
    label_vendor: 'Vendor', placeholder_vendor: 'Vendor', label_size: 'Default Qty per Piece', placeholder_size: 'e.g. 160',
    label_unit: 'Unit', unit_placeholder: 'Choose unit…', label_category: 'Category',
    label_ean: 'EAN', placeholder_ean: 'EAN code', ean_hint: 'EAN will be assigned automatically',
    btn_create_product: 'Create Product', toast_product_created: 'Product created',
    stock_entry_modal: 'Add Stock Entry', label_vault: 'Vault', select_vault: 'Choose vault…',
    label_qty: 'Quantity', label_bbd_form: 'Best Before', label_comment: 'Comment',
    placeholder_comment: 'Comment', btn_add_entry: 'Add Entry', toast_entry_created: 'Entry created',
    off_banner_label: 'OpenFoodFacts', off_banner_hint: 'Data from OpenFoodFacts',
    hint_ean_title: 'EAN / Barcode', hint_ean_desc: 'Looks up the matching product and opens the stock entry dialog. Unknown codes can be created as a new product on the spot.',
    hint_stockid_title: 'Stock ID ({prefix}…)', hint_stockid_desc: 'Opens the stock entry directly — take out or adjust the quantity.'
  },
  settings: {
    title: 'Settings', stockid_title: 'Stock ID', stockid_desc: 'Configure Stock ID generation',
    vaults_title: 'Vaults', vaults_desc: 'Manage your storage locations',
    units_title: 'Units', units_desc: 'Manage units of measure',
    categories_title: 'Categories', categories_desc: 'Manage product categories',
    data_transfer_title: 'Data Transfer', data_transfer_desc: 'Import or export data',
    language_title: 'Language', language_desc: 'Choose your preferred language',
    lang_de: 'Deutsch', lang_en: 'English'
  },
  data_transfer: {
    title: 'Data Transfer', export_title: 'Export', export_desc: 'Export data as ZIP',
    select_all: 'Select all', btn_export: 'Export', exporting: 'Exporting…',
    toast_nothing_selected: 'Nothing selected', toast_exported: 'Export successful',
    import_title: 'Import', import_desc: 'Import data from ZIP', import_drop_label: 'Choose ZIP file',
    btn_preview: 'Preview', btn_import: 'Import', loading_preview: 'Loading preview…',
    importing: 'Importing…', col_model: 'Table', col_rows: 'Rows', col_imported: 'Imported',
    col_total: 'Total', col_status: 'Status', status_known: 'Known', status_unknown: 'Unknown',
    status_ok: 'OK', status_error: 'Error', status_skipped: 'Skipped',
    toast_import_done: 'Import complete', toast_import_with_errors: 'Import with errors',
    images_label: 'Product Images', export_images_hint: 'Images will be included in ZIP'
  },
  stockid: {
    title: 'Stock ID Configuration', mode_manual_title: 'Manual', mode_manual_desc: 'Enter or scan IDs manually',
    mode_auto_title: 'Auto-generated', mode_auto_desc: 'Generate IDs automatically',
    label_prefix: 'Prefix', placeholder_prefix: 'e.g. S-', hint_prefix: 'Prefix for Stock IDs',
    label_counter: 'Counter', hint_next_id: 'Next ID: {id}', label_pad: 'Pad to',
    hint_pad: 'Digits with leading zeros', mode_extern_title: 'External (Webhook)',
    mode_extern_desc: 'Generate IDs via webhook', label_webhook: 'Webhook URL', hint_webhook: 'URL to call',
    placeholders_title: 'Placeholders', ph_quantity: '{quantity} – Quantity', ph_product_id: '{product_id} – Product ID',
    ph_vault_id: '{vault_id} – Vault ID', ph_bbd: '{bbd} – Best Before', ph_comment: '{comment} – Comment',
    btn_save: 'Save', toast_saved: 'Settings saved'
  }
};

const locales = { de, en };

function loadLang() {
  if (typeof localStorage !== 'undefined') {
    return localStorage.getItem('lang') || 'de';
  }
  return 'de';
}

export const locale = writable(loadLang());

locale.subscribe((lang) => {
  if (typeof localStorage !== 'undefined') {
    localStorage.setItem('lang', lang);
  }
});

export const translations = derived(locale, ($locale) => locales[$locale] || locales.de);

export function t(key, params = {}) {
  const parts = key.split('.');
  let val = get(translations);
  for (const p of parts) {
    if (val == null) return key;
    val = val[p];
  }
  if (val == null) return key;
  let str = String(val);
  for (const [k, v] of Object.entries(params)) {
    str = str.replaceAll(`{${k}}`, v);
  }
  return str;
}

export function setLocale(lang) {
  locale.set(lang);
}
