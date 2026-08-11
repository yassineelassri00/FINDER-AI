/**
 * FINDER AI — script.js v14
 * Architecture Frontend Professionnelle & Dynamique
 */

document.addEventListener('DOMContentLoaded', () => {
  'use strict';

  /* ──────────────────────────────────────────────────
     1. STATE MANAGEMENT
  ────────────────────────────────────────────────── */
  const STATE = {
    history: [],
    historyIndex: -1,
    activeToolId: null,
    attachedFiles: [],
    contextFiles: [],
    isRecording: false,
    recognition: null,
    activeCategory: 'all',
    activeTag: 'all',
    modelMode: 'Extra', // Extra (Gemini/Deep) vs Standard
    isSidebarCollapsed: false,
    isPanelOpen: true,
    activePanelTab: 'analyse',
    activeSettingsTab: 'compte',
    currentPage: 1,
    pageSize: 8,
    sessionKeywords: [],
    sessionResults: {},
    activeSessionKeyword: null,
    activeTool: null,
    quota: { used: 0, limit: 3, est_abonne_plus: false, limit_reached: false },
    numPages: 1,
    totalTools: 0,
    semanticActive: false,
    settings: {
      resultStyle: 'balanced',
      preferredLanguage: 'fr',
      defaultPricing: 'all',
      sourceMode: 'hybrid',
      maxResults: 8,
      includeWeb: true,
      sourceTransparency: true,
      ajaxMode: 'on_submit',
      watchFrequency: 'on_demand',
      goals: [],
      researchSources: [],
      technologyStack: [],
      professionalContext: '',
      ui: {
        theme: 'dark',
        viewMode: 'list',
        density: 'comfortable',
        fontSize: 'normal',
        motion: 'off',
      },
    },
  };

  /* ──────────────────────────────────────────────────
     2. DOM ELEMENTS CACHE
  ────────────────────────────────────────────────── */
  const DOM = {
    // Shell
    appFrame: document.getElementById('appFrame'),
    appLayout: document.getElementById('appLayout'),
    sidebar: document.querySelector('.sidebar'),
    workspace: document.querySelector('.workspace'),
    resultPanel: document.getElementById('resultPanel'),
    resizeHandle: document.getElementById('resizeHandle'),
    toast: document.getElementById('toast'),

    // Sidebar & Navigation
    menuButton: document.getElementById('menuButton'),
    sidebarToggleButton: document.getElementById('sidebarToggleButton'),
    newSearchButton: document.getElementById('newSearchButton'),
    historyBackButton: document.getElementById('historyBackButton'),
    historyForwardButton: document.getElementById('historyForwardButton'),
    projectsButton: document.getElementById('projectsButton'),
    toolsButton: document.getElementById('toolsButton'),
    proposeToolButton: document.getElementById('proposeToolButton'),
    sidebarRecentList: document.getElementById('sidebarRecentList'),
    manageRecentsButton: document.getElementById('manageRecentsButton'),
    upgradeButton: document.getElementById('upgradeButton'),
    usageCount: document.getElementById('usageCount'),
    openSettingsSidebarBtn: document.getElementById('openSettingsSidebarBtn'),
    profileMenuBtn: document.getElementById('profileMenuBtn'),
    profileMiniModal: document.getElementById('profileMiniModal'),
    pmmSettingsBtn: document.getElementById('pmm-settings-btn'),

    // Topbar
    topSearchButton: document.getElementById('topSearchButton'),
    splitViewButton: document.getElementById('splitViewButton'),
    pinProjectButton: document.getElementById('pinProjectButton'),
    projectActionsButton: document.getElementById('projectActionsButton'),
    projectActionMenu: document.getElementById('projectActionMenu'),

    // Composer & Search
    searchForm: document.getElementById('searchForm'),
    searchInput: document.getElementById('searchInput'),
    sendButton: document.getElementById('sendButton'),
    attachButton: document.getElementById('attachButton'),
    fileInput: document.getElementById('fileInput'),
    composerAttachArea: document.getElementById('composerAttachArea'),
    voiceButton: document.getElementById('voiceButton'),
    voiceIcon: document.getElementById('voiceIcon'),
    modelButton: document.getElementById('modelButton'),
    modelLabel: document.getElementById('modelLabel'),
    quickSuggestions: document.getElementById('quickSuggestions'),

    // Context Files
    contextFilesChips: document.getElementById('contextFilesChips'),
    contextFilesEmpty: document.getElementById('contextFilesEmpty'),
    contextAddBtn: document.getElementById('contextAddBtn'),
    contextFilesSummary: document.getElementById('contextFilesSummary'),

    // Recents & Catalog
    recentList: document.getElementById('recentList'),
    openPanelButton: document.getElementById('openPanelButton'),
    categoryPills: document.getElementById('categoryPills'),
    tagPills: document.getElementById('tagPills'),
    toolsList: document.getElementById('toolsList'),
    toolsCountLabel: document.getElementById('toolsCountLabel'),
    paginationBar: document.getElementById('paginationBar'),
    prevPageBtn: document.getElementById('prevPageBtn'),
    nextPageBtn: document.getElementById('nextPageBtn'),
    paginationInfo: document.getElementById('paginationInfo'),
    semanticBadge: document.getElementById('semanticBadge'),

    // Result Panel
    panelStatusLabel: document.getElementById('panelStatusLabel'),
    panelTabs: document.querySelectorAll('.panel-tab'),
    panelPanes: document.querySelectorAll('.panel-pane'),
    toggleFavoriBtn: document.getElementById('toggleFavoriBtn'),
    copyResultButton: document.getElementById('copyResultButton'),
    downloadResultButton: document.getElementById('downloadResultButton'),
    closePanelButton: document.getElementById('closePanelButton'),
    resultQuery: document.getElementById('resultQuery'),
    resultDate: document.getElementById('resultDate'),
    resultLogo: document.getElementById('resultLogo'),
    resultPanelTitle: document.getElementById('resultPanelTitle'),
    resultDescription: document.getElementById('resultDescription'),
    resultPrice: document.getElementById('resultPrice'),
    researchResultCount: document.getElementById('researchResultCount'),
    resultCategory: document.getElementById('resultCategory'),
    resultLink: document.getElementById('resultLink'),
    reasonList: document.getElementById('reasonList'),
    researchResults: document.getElementById('researchResults'),
    reviewsList: document.getElementById('reviewsList'),
    resultRatingBadge: document.getElementById('resultRatingBadge'),
    openReviewModalBtn: document.getElementById('openReviewModalBtn'),
    downloadPdfCta: document.getElementById('downloadPdfCta'),

    // Dialogs
    projectsLibrary: document.getElementById('projectsLibrary'),
    closeProjectsBtn: document.getElementById('closeProjectsBtn'),
    projectsGrid: document.getElementById('projectsGrid'),
    newProjectBtn: document.getElementById('newProjectBtn'),
    newProjectForm: document.getElementById('newProjectForm'),
    newProjectName: document.getElementById('newProjectName'),
    newProjectDescription: document.getElementById('newProjectDescription'),
    createProjectBtn: document.getElementById('createProjectBtn'),
    projectCreateStatus: document.getElementById('projectCreateStatus'),

    settingsDialog: document.getElementById('settingsDialog'),
    closeSettingsBtn: document.getElementById('closeSettingsBtn'),
    settingsTabs: document.querySelectorAll('.settings-tab'),
    settingsPanes: document.querySelectorAll('.settings-pane'),
    settingsProfileForm: document.getElementById('settingsProfileForm'),
    settingsSaveStatus: document.getElementById('settingsSaveStatus'),
    clearHistoryBtn: document.getElementById('clearHistoryBtn'),
    exportDataBtn: document.getElementById('exportDataBtn'),
    historyCount: document.getElementById('historyCount'),
    maxResultsRange: document.getElementById('maxResultsRange'),
    resultsCountLabel: document.getElementById('resultsCountLabel'),
    saveSearchPrefsBtn: document.getElementById('saveSearchPrefsBtn'),
    searchPrefsSaveStatus: document.getElementById('searchPrefsSaveStatus'),
    prefResultStyle: document.getElementById('prefResultStyle'),
    prefDefaultPricing: document.getElementById('prefDefaultPricing'),
    prefCategoriesPills: document.getElementById('prefCategoriesPills'),
    sourceModeSegmented: document.getElementById('sourceModeSegmented'),
    includeWebToggle: document.getElementById('includeWebToggle'),
    sourceTransparencyToggle: document.getElementById('sourceTransparencyToggle'),
    researchSourcesPills: document.getElementById('researchSourcesPills'),
    techStackPills: document.getElementById('techStackPills'),
    watchFrequencySelect: document.getElementById('watchFrequencySelect'),
    geminiKeyInput: document.getElementById('geminiKeyInput'),
    geminiKeyToggle: document.getElementById('geminiKeyToggle'),
    upgradeCodeInSettings: document.getElementById('upgradeCodeInSettings'),
    activateCodeInSettings: document.getElementById('activateCodeInSettings'),
    upgradeStatusSettings: document.getElementById('upgradeStatusSettings'),

    upgradeDialog: document.getElementById('upgradeDialog'),
    upgradeCloseButton: document.getElementById('upgradeCloseButton'),
    upgradeCodeInput: document.getElementById('upgradeCodeInput'),
    upgradeActivateButton: document.getElementById('upgradeActivateButton'),
    upgradeStatus: document.getElementById('upgradeStatus'),

    reviewDialog: document.getElementById('reviewDialog'),
    reviewForm: document.getElementById('reviewForm'),
    reviewCloseBtn: document.getElementById('reviewCloseBtn'),
    starRatingSelect: document.getElementById('starRatingSelect'),
    reviewNoteInput: document.getElementById('reviewNoteInput'),
    reviewCommentInput: document.getElementById('reviewCommentInput'),
    submitReviewBtn: document.getElementById('submitReviewBtn'),
    reviewFormStatus: document.getElementById('reviewFormStatus'),

    proposeToolDialog: document.getElementById('proposeToolDialog'),
    proposeToolForm: document.getElementById('proposeToolForm'),
    proposeToolCloseBtn: document.getElementById('proposeToolCloseBtn'),
  };

  /* ──────────────────────────────────────────────────
     3. UTILITY FUNCTIONS
  ────────────────────────────────────────────────── */
  function showToast(message, duration = 3000) {
    if (!DOM.toast) return;
    DOM.toast.textContent = message;
    DOM.toast.classList.add('is-visible');
    setTimeout(() => DOM.toast.classList.remove('is-visible'), duration);
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }
  const csrftoken = getCookie('csrftoken');

  /* ──────────────────────────────────────────────────
     4. HISTORY MANAGEMENT (localStorage)
  ────────────────────────────────────────────────── */
  function loadHistory() {
    try {
      const stored = localStorage.getItem('finder_ai_history');
      STATE.history = stored ? JSON.parse(stored) : [];
      STATE.historyIndex = STATE.history.length - 1;
    } catch (e) {
      STATE.history = [];
      STATE.historyIndex = -1;
    }
    renderHistoryUI();
    updateHistoryButtons();
  }

  function saveHistory(query, resultData) {
    const entry = {
      id: Date.now(),
      query: query,
      date: new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' }),
      fullDate: new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' }),
      data: resultData
    };
    STATE.history.unshift(entry);
    if (STATE.history.length > 30) STATE.history.pop();
    try {
      localStorage.setItem('finder_ai_history', JSON.stringify(STATE.history));
    } catch (e) {}
    STATE.historyIndex = 0;
    renderHistoryUI();
    updateHistoryButtons();
    updateUsageCounter();
  }

  function updateUsageCounter() {
    // Compteur serveur réel (ResearchJob) — le comptage localStorage est abandonné.
    if (!DOM.usageCount) return;
    if (STATE.quota.est_abonne_plus) {
      DOM.usageCount.textContent = '∞';
      return;
    }
    const limit = STATE.quota.limit || 3;
    const used = typeof STATE.quota.used === 'number' ? STATE.quota.used : 0;
    DOM.usageCount.textContent = `${Math.min(used, limit)}/${limit}`;
  }

  async function loadQuota() {
    try {
      const res = await fetch('/api/quota/');
      if (!res.ok) throw new Error('quota unavailable');
      const data = await res.json();
      if (data.ok) STATE.quota = { ...STATE.quota, ...data };
    } catch (e) {
      // Réseau/API indisponible : affichage neutre 0/3 par défaut.
      STATE.quota = { used: 0, limit: 3, est_abonne_plus: false, limit_reached: false };
    }
    updateUsageCounter();
  }

  function quotaEstDepasse() {
    return !STATE.quota.est_abonne_plus && STATE.quota.used >= (STATE.quota.limit || 3);
  }

  function proposerActivationPlus() {
    if (DOM.upgradeDialog) DOM.upgradeDialog.showModal();
  }

  function updateHistoryButtons() {
    if (DOM.historyBackButton) DOM.historyBackButton.disabled = STATE.historyIndex >= STATE.history.length - 1;
    if (DOM.historyForwardButton) DOM.historyForwardButton.disabled = STATE.historyIndex <= 0;
  }

  function renderHistoryUI() {
    // Sidebar list
    if (DOM.sidebarRecentList) {
      if (STATE.history.length === 0) {
        DOM.sidebarRecentList.innerHTML = '<p style="font-size:12px;color:var(--text-muted);padding:8px;">Aucune recherche récente</p>';
      } else {
        DOM.sidebarRecentList.innerHTML = STATE.history.slice(0, 8).map((item, idx) => `
          <button type="button" class="sidebar-recent" data-idx="${idx}">
            <svg viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg>
            <span>${escapeHTML(item.query)}</span>
          </button>
        `).join('');
      }
    }

    // Central recents list
    if (DOM.recentList) {
      if (STATE.history.length === 0) {
        DOM.recentList.innerHTML = '<p class="result-empty">Vos recherches récentes apparaîtront ici.</p>';
      } else {
        DOM.recentList.innerHTML = STATE.history.slice(0, 4).map((item, idx) => `
          <button type="button" class="central-recent" data-idx="${idx}">
            <div class="recent-message-icon">
              <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            </div>
            <div>
              <strong>${escapeHTML(item.query)}</strong>
              <small>${item.fullDate} à ${item.date}</small>
            </div>
            <svg class="recent-chevron" viewBox="0 0 24 24"><path d="m9 18 6-6-6-6"/></svg>
          </button>
        `).join('');
      }
    }

    if (DOM.historyCount) {
      DOM.historyCount.textContent = `${STATE.history.length} recherches enregistrées localement`;
    }
  }

  function escapeHTML(str) {
    return String(str).replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  }

  function getSelectedPillValues(container) {
    if (!container) return [];
    return Array.from(container.querySelectorAll('.antigravity-pill.is-selected'))
      .map(btn => btn.dataset.val)
      .filter(Boolean);
  }

  function getSegmentedValue(container, fallback) {
    const active = container ? container.querySelector('.segmented-btn.is-active') : null;
    return active ? active.dataset.val : fallback;
  }

  function setSegmentedValue(container, value) {
    if (!container || !value) return;
    container.querySelectorAll('.segmented-btn').forEach(btn => {
      btn.classList.toggle('is-active', btn.dataset.val === value);
    });
  }

  function readSettingsFromControls() {
    const form = DOM.settingsProfileForm;
    const formData = form ? new FormData(form) : new FormData();
    const maxResults = DOM.maxResultsRange ? parseInt(DOM.maxResultsRange.value, 10) : STATE.pageSize;

    STATE.settings = {
      ...STATE.settings,
      resultStyle: DOM.prefResultStyle ? DOM.prefResultStyle.value : STATE.settings.resultStyle,
      preferredLanguage: formData.get('preferred_language') || STATE.settings.preferredLanguage,
      defaultPricing: DOM.prefDefaultPricing ? DOM.prefDefaultPricing.value : STATE.settings.defaultPricing,
      sourceMode: getSegmentedValue(DOM.sourceModeSegmented, STATE.settings.sourceMode),
      maxResults: Number.isFinite(maxResults) ? maxResults : STATE.settings.maxResults,
      includeWeb: DOM.includeWebToggle ? DOM.includeWebToggle.checked : STATE.settings.includeWeb,
      sourceTransparency: DOM.sourceTransparencyToggle ? DOM.sourceTransparencyToggle.checked : STATE.settings.sourceTransparency,
      ajaxMode: getSegmentedValue(document.getElementById('prefAjaxModeSegmented'), STATE.settings.ajaxMode),
      watchFrequency: DOM.watchFrequencySelect ? DOM.watchFrequencySelect.value : STATE.settings.watchFrequency,
      goals: getSelectedPillValues(DOM.prefCategoriesPills),
      researchSources: getSelectedPillValues(DOM.researchSourcesPills),
      technologyStack: getSelectedPillValues(DOM.techStackPills),
      professionalContext: String(formData.get('professional_context') || '').trim(),
      ui: {
        theme: getSegmentedValue(document.getElementById('themeSegmented'), STATE.settings.ui.theme),
        viewMode: getSegmentedValue(document.getElementById('viewModeSegmented'), STATE.settings.ui.viewMode),
        density: getSegmentedValue(document.getElementById('densitySegmented'), STATE.settings.ui.density),
        fontSize: getSegmentedValue(document.getElementById('fontSizeSegmented'), STATE.settings.ui.fontSize),
        motion: getSegmentedValue(document.getElementById('motionSegmented'), STATE.settings.ui.motion),
      },
    };

    STATE.pageSize = STATE.settings.maxResults;
    if (DOM.resultsCountLabel) DOM.resultsCountLabel.textContent = String(STATE.pageSize);
  }

  function persistLocalSettings() {
    try {
      localStorage.setItem('finder_ai_settings', JSON.stringify(STATE.settings));
    } catch (e) {}
  }

  function loadLocalSettings() {
    try {
      const stored = localStorage.getItem('finder_ai_settings');
      if (stored) {
        STATE.settings = { ...STATE.settings, ...JSON.parse(stored) };
        STATE.settings.ui = { theme: 'dark', viewMode: 'list', density: 'comfortable', fontSize: 'normal', motion: 'off', ...(STATE.settings.ui || {}) };
        STATE.pageSize = Number.isFinite(parseInt(STATE.settings.maxResults, 10)) ? parseInt(STATE.settings.maxResults, 10) : STATE.pageSize;
      }
    } catch (e) {}
  }

  function applyUiPreferences() {
    const ui = STATE.settings.ui || {};
    document.body.classList.toggle('theme-oled', ui.theme === 'oled');
    document.body.classList.toggle('reduce-motion', ui.motion === 'on');
    document.body.classList.toggle('font-size-large', ui.fontSize === 'large');
    document.body.classList.toggle('font-size-xlarge', ui.fontSize === 'xlarge');
    if (DOM.appFrame) DOM.appFrame.classList.toggle('is-compact-density', ui.density === 'compact');
    if (DOM.toolsList) {
      DOM.toolsList.classList.remove('grid-view', 'list-view');
      DOM.toolsList.classList.add(`${ui.viewMode || 'list'}-view`);
    }
  }

  function syncControlsFromSettings() {
    if (DOM.prefResultStyle) DOM.prefResultStyle.value = STATE.settings.resultStyle;
    if (DOM.prefDefaultPricing) DOM.prefDefaultPricing.value = STATE.settings.defaultPricing;
    if (DOM.maxResultsRange) DOM.maxResultsRange.value = STATE.pageSize;
    if (DOM.resultsCountLabel) DOM.resultsCountLabel.textContent = String(STATE.pageSize);
    if (DOM.includeWebToggle) DOM.includeWebToggle.checked = STATE.settings.includeWeb;
    if (DOM.sourceTransparencyToggle) DOM.sourceTransparencyToggle.checked = STATE.settings.sourceTransparency;
    if (DOM.watchFrequencySelect) DOM.watchFrequencySelect.value = STATE.settings.watchFrequency;
    setSegmentedValue(DOM.sourceModeSegmented, STATE.settings.sourceMode);
    setSegmentedValue(document.getElementById('themeSegmented'), STATE.settings.ui.theme);
    setSegmentedValue(document.getElementById('viewModeSegmented'), STATE.settings.ui.viewMode);
    setSegmentedValue(document.getElementById('densitySegmented'), STATE.settings.ui.density);
    setSegmentedValue(document.getElementById('fontSizeSegmented'), STATE.settings.ui.fontSize);
    setSegmentedValue(document.getElementById('motionSegmented'), STATE.settings.ui.motion);
  }

  async function saveProfileSettings() {
    if (!DOM.settingsProfileForm) return;
    const formData = new FormData(DOM.settingsProfileForm);
    const payload = {
      section: 'profil',
      full_name: formData.get('full_name') || '',
      organization: formData.get('organization') || '',
      job_role: formData.get('job_role') || '',
      preferred_language: formData.get('preferred_language') || 'fr',
      professional_context: formData.get('professional_context') || '',
    };

    const res = await fetch('/api/settings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || 'Profil non sauvegardé.');
    return data;
  }

  async function savePreferenceSettings() {
    readSettingsFromControls();
    persistLocalSettings();
    const payload = {
      section: 'preferences',
      result_style: STATE.settings.resultStyle,
      preferred_language: STATE.settings.preferredLanguage,
      budget_preference: STATE.settings.defaultPricing,
      watch_frequency: STATE.settings.watchFrequency,
      gemini_api_key: DOM.geminiKeyInput ? DOM.geminiKeyInput.value : '',
      goals: STATE.settings.goals,
      research_sources: STATE.settings.researchSources,
      technology_stack: STATE.settings.technologyStack,
      search_preferences: {
        max_results: STATE.pageSize,
        source_mode: STATE.settings.sourceMode,
        include_web: STATE.settings.includeWeb,
        source_transparency: STATE.settings.sourceTransparency,
        ajax_mode: STATE.settings.ajaxMode,
      },
      ui_preferences: STATE.settings.ui,
    };

    const res = await fetch('/api/settings/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || 'Préférences non sauvegardées.');
    return data;
  }

  /* ──────────────────────────────────────────────────
     5. PANEL & SIDEBAR TOGGLES
────────────────────────────────────────────────── */
  function toggleSidebar() {
    STATE.isSidebarCollapsed = !STATE.isSidebarCollapsed;
    DOM.appFrame.classList.toggle('is-sidebar-collapsed', STATE.isSidebarCollapsed);
    if (DOM.menuButton) DOM.menuButton.setAttribute('aria-pressed', STATE.isSidebarCollapsed);
  }

  function togglePanel(forceOpen = null) {
    if (forceOpen !== null) STATE.isPanelOpen = forceOpen;
    else STATE.isPanelOpen = !STATE.isPanelOpen;

    DOM.resultPanel.classList.toggle('is-closed', !STATE.isPanelOpen);
    if (DOM.splitViewButton) DOM.splitViewButton.setAttribute('aria-pressed', !STATE.isPanelOpen);

    // Adjust grid
    if (!STATE.isPanelOpen) {
      DOM.appLayout.style.gridTemplateColumns = STATE.isSidebarCollapsed
        ? 'var(--sidebar-w-col) 1fr 0px 0px'
        : 'var(--sidebar-w) 1fr 0px 0px';
    } else {
      DOM.appLayout.style.gridTemplateColumns = STATE.isSidebarCollapsed
        ? 'var(--sidebar-w-col) 1fr 5px var(--panel-w)'
        : 'var(--sidebar-w) 1fr 5px var(--panel-w)';
    }
  }

  function switchPanelTab(tabName) {
    STATE.activePanelTab = tabName;
    DOM.panelTabs.forEach(t => {
      const active = t.dataset.panel === tabName;
      t.classList.toggle('is-active', active);
      t.setAttribute('aria-selected', active);
    });
    DOM.panelPanes.forEach(p => {
      p.classList.toggle('is-active', p.id === `pane${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`);
    });
  }

  async function executeSearch(query) {
    if (!query || !query.trim()) return;
    const cleanQuery = query.trim();

    // Quota journalier : refuse proprement quand la limite gratuite est atteinte.
    if (quotaEstDepasse()) {
      if (DOM.resultDescription) DOM.resultDescription.textContent = 'Limite de recherches gratuites atteinte pour aujourd\'hui.';
      if (DOM.researchResults) DOM.researchResults.innerHTML = '<p class="result-empty is-error">Activez le Plan Finder Plus pour continuer à rechercher sans limite.</p>';
      showToast('Limite quotidienne atteinte — activez Finder Plus', 4000);
      proposerActivationPlus();
      return;
    }

    readSettingsFromControls();
    persistLocalSettings();

    // 1. Add to session history
    if (!STATE.sessionKeywords.includes(cleanQuery)) {
      STATE.sessionKeywords.push(cleanQuery);
    }
    STATE.activeSessionKeyword = cleanQuery;

    // Visual feedback
    DOM.sendButton.disabled = true;
    DOM.sendButton.classList.add('is-sending');
    if (DOM.panelStatusLabel) DOM.panelStatusLabel.textContent = 'ANALYSE EN COURS…';

    // Show panel if closed
    togglePanel(true);

    // Toggle Empty State / Content View
    const emptyState = document.getElementById('unifiedEmptyState');
    const resultContent = document.getElementById('unifiedResultContent');
    if (emptyState) emptyState.style.display = 'none';
    if (resultContent) resultContent.style.display = 'block';

    // Update keyword tabs and session chips
    renderKeywordTabs();
    renderSessionChips();

    // Render loading state in panel
    if (DOM.resultPanelTitle) DOM.resultPanelTitle.textContent = cleanQuery;
    if (DOM.resultDescription) DOM.resultDescription.textContent = 'Analyse sémantique et recherche des meilleures solutions IA...';
    if (DOM.reasonList) DOM.reasonList.innerHTML = '<li><span class="rp-reason-num">...</span>Analyse du besoin technique en cours...</li>';
    if (DOM.researchResults) {
      DOM.researchResults.innerHTML = `
        <div class="research-loading">
          <span></span>
          <div>
            <strong>Fouille du catalogue &amp; Web</strong>
            <small>Extraction des outils les plus pertinents pour votre cas d'usage…</small>
          </div>
        </div>
      `;
    }

    try {
      const response = await fetch('/api/recherche/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken,
        },
        body: JSON.stringify({
          q: cleanQuery,
          inclure_web: STATE.settings.includeWeb,
          model_mode: STATE.modelMode,
          max_results: STATE.pageSize,
          result_style: STATE.settings.resultStyle,
          preferred_language: STATE.settings.preferredLanguage,
          default_pricing: STATE.settings.defaultPricing,
          budget_preference: STATE.settings.defaultPricing,
          source_mode: STATE.settings.sourceMode,
          source_transparency: STATE.settings.sourceTransparency,
          goals: STATE.settings.goals,
          research_sources: STATE.settings.researchSources,
          technology_stack: STATE.settings.technologyStack,
          professional_context: STATE.settings.professionalContext
        })
      });

      if (!response.ok) throw new Error(`Erreur serveur (${response.status})`);
      const data = await response.json();

      // Cache the result
      STATE.sessionResults[cleanQuery] = data;

      // Render search results
      renderSearchResults(cleanQuery, data);
      renderKeywordTabs();
      renderSessionChips();
      saveHistory(cleanQuery, data);
      loadQuota(); // Re-synchronise le compteur avec le serveur
      showToast('Analyse terminée !');

    } catch (err) {
      console.error('Search error:', err);
      if (DOM.resultDescription) DOM.resultDescription.textContent = `Erreur : ${err.message}`;
      if (DOM.researchResults) DOM.researchResults.innerHTML = `<p class="result-empty is-error">Erreur lors de la recherche. Veuillez réessayer.</p>`;
      showToast('Erreur lors de la recherche');
    } finally {
      DOM.sendButton.disabled = false;
      DOM.sendButton.classList.remove('is-sending');
      if (DOM.panelStatusLabel) DOM.panelStatusLabel.textContent = 'ANALYSE VÉRIFIÉE';
    }
  }

  /* ──────────────────────────────────────────────────
     SESSION HISTORY & KEYWORD TABS UI
  ────────────────────────────────────────────────── */
  function renderSessionChips() {
    const chipsContainer = document.getElementById('sessionKeywordChips');
    const emptyLabel = document.getElementById('sessionHistoryEmpty');
    
    if (!chipsContainer) return;
    
    if (STATE.sessionKeywords.length === 0) {
      chipsContainer.innerHTML = '';
      if (emptyLabel) emptyLabel.style.display = 'inline';
      return;
    }
    
    if (emptyLabel) emptyLabel.style.display = 'none';
    
    chipsContainer.innerHTML = STATE.sessionKeywords.map((kw, index) => {
      const activeClass = kw === STATE.activeSessionKeyword ? 'is-active' : '';
      return `
        <span class="session-chip ${activeClass}" data-keyword="${escapeHTML(kw)}">
          <span>${escapeHTML(kw)}</span>
          <span class="session-chip-remove" data-index="${index}">&times;</span>
        </span>
      `;
    }).join('');

    // Click events
    chipsContainer.querySelectorAll('.session-chip').forEach(chip => {
      chip.addEventListener('click', (e) => {
        if (e.target.classList.contains('session-chip-remove')) return;
        const kw = chip.dataset.keyword;
        switchKeywordTab(kw);
      });
    });

    chipsContainer.querySelectorAll('.session-chip-remove').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const index = parseInt(btn.dataset.index, 10);
        removeSessionKeyword(index);
      });
    });
  }

  function renderKeywordTabs() {
    const tabsContainer = document.getElementById('keywordTabsList');
    if (!tabsContainer) return;

    if (STATE.sessionKeywords.length === 0) {
      tabsContainer.innerHTML = '';
      if (DOM.unifiedEmptyState) DOM.unifiedEmptyState.style.display = 'flex';
      if (DOM.unifiedResultContent) DOM.unifiedResultContent.style.display = 'none';
      return;
    }

    if (DOM.unifiedEmptyState) DOM.unifiedEmptyState.style.display = 'none';
    if (DOM.unifiedResultContent) DOM.unifiedResultContent.style.display = 'block';

    tabsContainer.innerHTML = STATE.sessionKeywords.map((kw, index) => {
      const activeClass = kw === STATE.activeSessionKeyword ? 'is-active' : '';
      return `
        <button type="button" class="keyword-tab ${activeClass}" role="tab" data-keyword="${escapeHTML(kw)}">
          <span>🔍 ${escapeHTML(kw)}</span>
          <span class="keyword-tab-close" data-index="${index}">&times;</span>
        </button>
      `;
    }).join('');

    // Scroll active tab into view
    const activeTabEl = tabsContainer.querySelector('.keyword-tab.is-active');
    if (activeTabEl) {
      activeTabEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
    }

    // Click event
    tabsContainer.querySelectorAll('.keyword-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        if (e.target.classList.contains('keyword-tab-close')) return;
        const kw = tab.dataset.keyword;
        switchKeywordTab(kw);
      });
    });

    tabsContainer.querySelectorAll('.keyword-tab-close').forEach(btn => {
      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const index = parseInt(btn.dataset.index, 10);
        removeSessionKeyword(index);
      });
    });
  }

  function switchKeywordTab(kw) {
    if (!kw) return;
    STATE.activeSessionKeyword = kw;
    renderKeywordTabs();
    renderSessionChips();

    const data = STATE.sessionResults[kw];
    if (data) {
      renderSearchResults(kw, data);
    } else {
      executeSearch(kw);
    }
  }

  function removeSessionKeyword(index) {
    const kw = STATE.sessionKeywords[index];
    if (!kw) return;

    STATE.sessionKeywords.splice(index, 1);
    delete STATE.sessionResults[kw];

    if (STATE.activeSessionKeyword === kw) {
      if (STATE.sessionKeywords.length > 0) {
        STATE.activeSessionKeyword = STATE.sessionKeywords[STATE.sessionKeywords.length - 1];
        switchKeywordTab(STATE.activeSessionKeyword);
      } else {
        STATE.activeSessionKeyword = null;
        renderKeywordTabs();
        renderSessionChips();
      }
    } else {
      renderKeywordTabs();
      renderSessionChips();
    }
  }

  function clearSession() {
    STATE.sessionKeywords = [];
    STATE.sessionResults = {};
    STATE.activeSessionKeyword = null;
    renderKeywordTabs();
    renderSessionChips();
    showToast('Discussion réinitialisée');
  }

  /* ──────────────────────────────────────────────────
     DYNAMIC PROFESSIONAL GREETING
  ────────────────────────────────────────────────── */
  function initDynamicGreeting() {
    const greetings = [
      "À vous la parole,",
      "Que souhaitez-vous explorer aujourd'hui,",
      "Prêt pour une nouvelle recherche,",
      "Quelle est votre prochaine idée,",
      "Comment puis-je vous guider,",
      "À votre écoute,"
    ];
    const prefixEl = document.getElementById('dynamicGreetingPrefix');
    if (prefixEl) {
      const randomIndex = Math.floor(Math.random() * greetings.length);
      prefixEl.textContent = greetings[randomIndex];
    }
  }

  /* ──────────────────────────────────────────────────
     6. SEARCH EXECUTION & API INTEGRATION
  ────────────────────────────────────────────────── */


  function renderSearchResults(query, data) {
    if (DOM.resultQuery) DOM.resultQuery.textContent = 'RECOMMANDATION';
    if (DOM.resultDate) DOM.resultDate.textContent = 'À l\'instant';
    if (DOM.resultPanelTitle) DOM.resultPanelTitle.textContent = data.meilleur_outil ? data.meilleur_outil.nom : query;
    if (DOM.resultDescription) DOM.resultDescription.textContent = data.synthese || 'Synthèse générée avec succès.';
    if (DOM.resultPrice) DOM.resultPrice.textContent = data.meilleur_outil ? data.meilleur_outil.type_tarification : 'Libre';
    if (DOM.researchResultCount) DOM.researchResultCount.textContent = (data.resultats || []).length;
    if (DOM.resultCategory) DOM.resultCategory.textContent = data.meilleur_outil ? (data.meilleur_outil.categorie || 'IA') : 'IA Generative';
    
    if (DOM.resultLink && data.meilleur_outil && data.meilleur_outil.url_site) {
      DOM.resultLink.href = data.meilleur_outil.url_site;
      DOM.resultLink.style.display = 'flex';
    }

    // Outil actif : nécessaire pour les favoris et les avis
    STATE.activeTool = data.meilleur_outil || null;
    STATE.activeToolId = data.meilleur_outil ? data.meilleur_outil.id : null;
    renderFavoriState();
    renderReviews(data.meilleur_outil ? (data.meilleur_outil.avis || []) : []);
    if (DOM.resultRatingBadge && data.meilleur_outil) {
      DOM.resultRatingBadge.textContent = `${(data.meilleur_outil.score || 0)}/5`;
    }

    // Reasons
    if (DOM.reasonList && data.points_cles) {
      DOM.reasonList.innerHTML = data.points_cles.map((pt, i) => `
        <li><span class="rp-reason-num">0${i+1}</span>${escapeHTML(pt)}</li>
      `).join('');
    }

    // Sources cards
    if (DOM.researchResults) {
      const results = data.resultats || [];
      if (results.length === 0) {
        DOM.researchResults.innerHTML = '<p class="result-empty">Aucun outil correspondant trouvé dans le catalogue.</p>';
      } else {
        DOM.researchResults.innerHTML = results.map((res, i) => `
          <div class="research-card">
            <div class="research-card-head">
              <span class="research-rank">#0${i+1}</span>
              <h4>${escapeHTML(res.nom)}</h4>
              <span class="research-score">${Math.round((res.score_pertinence || 0.9) * 100)}%</span>
            </div>
            <p>${escapeHTML(res.description)}</p>
            <div class="research-source-list">
              <span class="research-source">${escapeHTML(res.type_tarification || 'Freemium')}</span>
              <span class="research-source">${escapeHTML(res.type_integration || 'API / Web')}</span>
            </div>
          </div>
        `).join('');
      }
    }
  }

  /* ──────────────────────────────────────────────────
     6b. FAVORIS & AVIS
  ────────────────────────────────────────────────── */
  function renderFavoriState() {
    if (!DOM.toggleFavoriBtn) return;
    const isFav = !!(STATE.activeTool && STATE.activeTool.is_favori);
    DOM.toggleFavoriBtn.setAttribute('aria-pressed', isFav ? 'true' : 'false');
    DOM.toggleFavoriBtn.classList.toggle('is-favori', isFav);
    const svg = DOM.toggleFavoriBtn.querySelector('svg');
    if (svg) svg.setAttribute('fill', isFav ? 'currentColor' : 'none');
    DOM.toggleFavoriBtn.title = isFav ? 'Retirer des favoris' : 'Ajouter aux favoris';
  }

  async function toggleFavori() {
    if (!STATE.activeToolId) {
      showToast('Sélectionnez un outil avant d\'ajouter un favori.');
      return;
    }
    const wasFav = !!(STATE.activeTool && STATE.activeTool.is_favori);
    // Optimisme : bascule immédiate pour un retour visuel instantané.
    if (STATE.activeTool) STATE.activeTool.is_favori = !wasFav;
    renderFavoriState();
    try {
      const res = await fetch(`/api/outils/${STATE.activeToolId}/favoris/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken }
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Erreur favori');
      if (STATE.activeTool) STATE.activeTool.is_favori = data.is_favori;
      renderFavoriState();
      showToast(data.message || (data.is_favori ? 'Ajouté aux favoris' : 'Retiré des favoris'));
    } catch (err) {
      if (STATE.activeTool) STATE.activeTool.is_favori = wasFav;
      renderFavoriState();
      showToast('Impossible de mettre à jour le favori');
    }
  }

  function renderReviews(reviews) {
    if (!DOM.reviewsList) return;
    const list = Array.isArray(reviews) ? reviews : [];
    if (list.length === 0) {
      DOM.reviewsList.innerHTML = '<p class="result-empty">Aucun avis pour le moment.</p>';
      return;
    }
    DOM.reviewsList.innerHTML = list.map(r => `
      <div class="review-item">
        <div class="review-item-head">
          <strong>${escapeHTML(r.auteur || 'Utilisateur')}</strong>
          <span class="review-stars" aria-label="${r.note || 0} étoiles">${'★'.repeat(Math.min(r.note || 0, 5))}${'☆'.repeat(5 - Math.min(r.note || 0, 5))}</span>
        </div>
        <span class="review-date">${escapeHTML(r.date_creation || '')}</span>
        <p>${escapeHTML(r.commentaire || '')}</p>
      </div>
    `).join('');
  }

  /* ──────────────────────────────────────────────────
     6c. PROJETS PERSONNALISÉS (/api/projets/)
  ────────────────────────────────────────────────── */
  async function loadProjects() {
    try {
      const res = await fetch('/api/projets/');
      if (!res.ok) return;
      const data = await res.json();
      renderProjectsGrid(data.projets || []);
    } catch (e) {
      console.warn('Could not load projects:', e);
    }
  }

  function renderProjectsGrid(projets) {
    if (!DOM.projectsGrid) return;
    // Conserve la carte "Nouveau projet" et retire les cartes précédentes.
    DOM.projectsGrid.querySelectorAll('.project-card:not(.new-project-card), .projects-empty').forEach(el => el.remove());

    if (!projets.length) {
      const empty = document.createElement('p');
      empty.className = 'projects-empty';
      empty.textContent = 'Aucun projet pour le moment. Créez-en un pour regrouper vos recherches.';
      DOM.projectsGrid.appendChild(empty);
      return;
    }

    projets.forEach(p => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'project-card';
      card.dataset.id = p.id;
      card.title = 'Ouvrir ce projet';
      card.innerHTML = `
        <div class="project-icon">
          <svg viewBox="0 0 24 24"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
        </div>
        <strong>${escapeHTML(p.nom)}</strong>
        <small>${escapeHTML(p.description || '')}</small>
        <span class="project-meta">${p.outils_count || 0} outil${(p.outils_count || 0) > 1 ? 's' : ''} · ${escapeHTML(p.date_creation || '')}</span>
      `;
      DOM.projectsGrid.appendChild(card);
    });
  }

  async function createProject(nom, description) {
    const res = await fetch('/api/projets/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
      body: JSON.stringify({ nom, description })
    });
    const data = await res.json();
    if (!res.ok || !data.ok) throw new Error(data.error || 'Impossible de créer le projet.');
    return data;
  }

  /* ──────────────────────────────────────────────────
     6d. PAGINATION CATALOGUE (/api/outils/)
  ────────────────────────────────────────────────── */
  async function loadToolsPage(page) {
    readSettingsFromControls();
    const params = new URLSearchParams();
    params.set('page', String(page || 1));
    params.set('page_size', String(STATE.pageSize || 8));
    if (STATE.activeCategory && STATE.activeCategory !== 'all') params.set('categorie', STATE.activeCategory);
    if (STATE.activeTag && STATE.activeTag !== 'all') params.set('tags[]', STATE.activeTag);
    if (STATE.settings.defaultPricing && STATE.settings.defaultPricing !== 'all') params.set('tarification', STATE.settings.defaultPricing);

    try {
      const res = await fetch(`/api/outils/?${params.toString()}`);
      if (!res.ok) throw new Error('Erreur catalogue');
      const data = await res.json();
      STATE.currentPage = data.current_page || 1;
      STATE.numPages = data.num_pages || 1;
      STATE.totalTools = data.total || 0;
      STATE.semanticActive = !!data.semantic_active;
      renderToolsList(data.outils || []);
      renderPagination();
    } catch (err) {
      if (DOM.toolsList) DOM.toolsList.innerHTML = '<p class="no-tools">Impossible de charger le catalogue.</p>';
    }
  }

  function renderToolsList(outils) {
    if (!DOM.toolsList) return;
    if (!outils.length) {
      DOM.toolsList.innerHTML = '<p class="no-tools">Aucune référence ne correspond à ces filtres.</p>';
    } else {
      DOM.toolsList.innerHTML = outils.map(o => `
        <button type="button" class="tool-result"
          data-name="${escapeHTML(o.nom)}"
          data-description="${escapeHTML(o.description)}"
          data-category="${escapeHTML(o.categorie ? o.categorie.nom : 'Outil IA')}"
          data-price="${escapeHTML(o.type_tarification)}"
          data-url="${escapeHTML(o.url_site)}"
          data-id="${o.id}"
          data-is-favori="${o.is_favori ? 'true' : 'false'}">
          <span class="tool-letter">${escapeHTML(String(o.nom).slice(0, 1).toUpperCase())}</span>
          <span>
            <strong>${escapeHTML(o.nom)}</strong>
            <small>${escapeHTML(o.categorie ? o.categorie.nom : 'Outil IA')} · ${escapeHTML(o.type_tarification)}</small>
          </span>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>
        </button>
      `).join('');
    }

    if (DOM.toolsCountLabel) {
      DOM.toolsCountLabel.textContent = `${STATE.totalTools} référence${STATE.totalTools > 1 ? 's' : ''}`;
    }
    if (DOM.semanticBadge) {
      DOM.semanticBadge.hidden = !STATE.semanticActive;
    }
  }

  function renderPagination() {
    if (!DOM.paginationBar) return;
    DOM.paginationBar.hidden = STATE.numPages <= 1;
    if (DOM.prevPageBtn) DOM.prevPageBtn.disabled = STATE.currentPage <= 1;
    if (DOM.nextPageBtn) DOM.nextPageBtn.disabled = STATE.currentPage >= STATE.numPages;
    if (DOM.paginationInfo) {
      DOM.paginationInfo.textContent = `Page ${STATE.currentPage} sur ${STATE.numPages || 1} — ${STATE.totalTools} outil${STATE.totalTools > 1 ? 's' : ''}`;
    }
  }

  /* ──────────────────────────────────────────────────
     6e. EXPORT PDF (blob généré côté client)
  ────────────────────────────────────────────────── */
  function generateReportPDF() {
    const query = STATE.activeSessionKeyword || (STATE.activeTool ? STATE.activeTool.nom : 'Rapport');
    const synthese = DOM.resultDescription ? DOM.resultDescription.textContent : '';
    const cached = STATE.sessionResults[query];
    const points = cached && Array.isArray(cached.points_cles) ? cached.points_cles : [];
    const results = cached && Array.isArray(cached.resultats) ? cached.resultats : [];
    const date = new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' });

    const lines = [];
    lines.push('FINDER AI - RAPPORT D\'ANALYSE');
    lines.push('Date : ' + date);
    lines.push('Requete : ' + query);
    lines.push('');
    lines.push('SYNTHESE');
    lines.push(synthese || 'Aucune synthese disponible.');
    lines.push('');
    lines.push('POINTS CLES');
    (points.length ? points : ['Aucun point cle.']).forEach(p => lines.push('- ' + p));
    lines.push('');
    lines.push('REFERENCES RECOMMANDEES');
    if (results.length === 0) {
      lines.push('Aucune reference.');
    } else {
      results.forEach((r, i) => {
        lines.push((i + 1) + '. ' + r.nom + ' (' + (r.type_tarification || 'Freemium') + ')');
        if (r.description) lines.push('   ' + r.description);
      });
    }

    const pdfBytes = buildMinimalPdf(lines.join('\n'));
    const blob = new Blob([pdfBytes], { type: 'application/pdf' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `finder_ai_rapport_${Date.now()}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    setTimeout(() => URL.revokeObjectURL(url), 5000);
    showToast('Rapport PDF généré');
  }

  function buildMinimalPdf(text) {
    // Génère un PDF 1.4 minimal et valide (une page, texte ASCII).
    // On force l'ASCII (0x20-0x7E) pour que la longueur du flux soit exacte.
    const esc = (s) => String(s).replace(/[^\x20-\x7E]/g, ' ').replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');

    const lines = String(text).split('\n');
    const lineHeight = 14;
    const margin = 50;
    const maxChars = 82;
    const maxLines = Math.floor((792 - 2 * margin) / lineHeight);
    const wrapped = [];
    lines.forEach(line => {
      if (line.length === 0) { wrapped.push(''); return; }
      let current = line;
      while (current.length > maxChars) {
        wrapped.push(current.slice(0, maxChars));
        current = current.slice(maxChars);
      }
      wrapped.push(current);
    });
    const shown = wrapped.slice(0, maxLines);

    const textObj = shown.map((line, i) => {
      const y = 792 - margin - i * lineHeight;
      return `BT /F1 11 Tf 50 ${y} Td (${esc(line)}) Tj ET`;
    }).join('\n');

    const chunks = ['%PDF-1.4\n'];
    const objects = [
      '<< /Type /Catalog /Pages 2 0 R >>',
      '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
      '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
      '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
      `<< /Length ${textObj.length} >>\nstream\n${textObj}\nendstream`,
    ];

    let offset = chunks[0].length;
    const xref = [0];
    objects.forEach((obj, idx) => {
      xref.push(offset);
      chunks.push(`${idx + 1} 0 obj\n${obj}\nendobj\n`);
      offset += chunks[chunks.length - 1].length;
    });
    const xrefOffset = offset;
    chunks.push(`xref\n0 ${objects.length + 1}\n`);
    chunks.push('0000000000 65535 f \n');
    xref.slice(1).forEach(off => chunks.push(String(off).padStart(10, '0') + ' 00000 n \n'));
    chunks.push(`trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`);

    const data = chunks.join('');
    const bytes = new Uint8Array(data.length);
    for (let i = 0; i < data.length; i++) {
      const c = data.charCodeAt(i);
      bytes[i] = c < 128 ? c : 32;
    }
    return bytes;
  }

  /* ──────────────────────────────────────────────────
     7. CONTEXT FILES MANAGEMENT (/api/fichiers/)
  ────────────────────────────────────────────────── */
  async function loadContextFiles() {
    try {
      const res = await fetch('/api/fichiers/');
      if (!res.ok) return;
      const data = await res.json();
      STATE.contextFiles = data.fichiers || data || [];
      renderContextFilesUI();
    } catch (e) {
      console.warn('Could not load context files:', e);
    }
  }

  function renderContextFilesUI() {
    if (!DOM.contextFilesChips) return;
    if (!STATE.contextFiles || STATE.contextFiles.length === 0) {
      DOM.contextFilesChips.innerHTML = '<span class="context-files-empty">Aucun fichier de contexte actif</span>';
      if (DOM.contextFilesSummary) DOM.contextFilesSummary.textContent = 'Aucun fichier chargé.';
      return;
    }

    DOM.contextFilesChips.innerHTML = STATE.contextFiles.map(f => {
      const nomFichier = f.nom || f.nom_fichier || 'fichier';
      const ext = nomFichier.split('.').pop().toUpperCase();
      return `
        <div class="file-chip" data-id="${f.id}">
          <svg viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
          <span>${escapeHTML(nomFichier)}</span>
          <span class="chip-ext">${ext}</span>
          <button type="button" class="file-chip-remove" data-id="${f.id}" title="Supprimer">✕</button>
        </div>
      `;
    }).join('');

    if (DOM.contextFilesSummary) {
      DOM.contextFilesSummary.innerHTML = STATE.contextFiles.map(f => {
        const nomFichier = f.nom || f.nom_fichier || 'fichier';
        const taille = f.taille ? `${(f.taille / 1024).toFixed(1)} Ko` : '—';
        return `• ${escapeHTML(nomFichier)} (${taille})`;
      }).join('<br>');
    }
  }

  async function uploadContextFile(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('fichier', file);
    try {
      const res = await fetch('/api/fichiers/upload/', {
        method: 'POST',
        headers: { 'X-CSRFToken': csrftoken },
        body: formData
      });
      const data = await res.json();
      if (!res.ok || !data.ok) throw new Error(data.error || 'Upload impossible');
      showToast(data.message || 'Fichier ajouté au contexte');
      loadContextFiles();
    } catch (err) {
      showToast(err.message || 'Erreur lors de l\'upload', 4000);
    }
  }

  async function deleteContextFile(id) {
    try {
      const res = await fetch(`/api/fichiers/${id}/`, {
        method: 'DELETE',
        headers: { 'X-CSRFToken': csrftoken }
      });
      if (res.ok) {
        STATE.contextFiles = STATE.contextFiles.filter(f => f.id !== id);
        renderContextFilesUI();
        showToast('Fichier retiré du contexte');
      }
    } catch (e) {
      showToast('Erreur suppression fichier');
    }
  }

  /* ──────────────────────────────────────────────────
     8. VOICE INPUT (Web Speech API)
  ────────────────────────────────────────────────── */
  function initVoiceRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      if (DOM.voiceButton) DOM.voiceButton.title = 'Saisie vocale non supportée par ce navigateur';
      return;
    }

    STATE.recognition = new SpeechRecognition();
    STATE.recognition.lang = 'fr-FR';
    STATE.recognition.interimResults = false;

    STATE.recognition.onstart = () => {
      STATE.isRecording = true;
      if (DOM.voiceButton) DOM.voiceButton.classList.add('is-recording');
      showToast('Écoute en cours… Parlez !');
    };

    STATE.recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      if (DOM.searchInput) {
        DOM.searchInput.value = transcript;
        DOM.searchInput.dispatchEvent(new Event('input'));
      }
    };

    STATE.recognition.onerror = () => {
      STATE.isRecording = false;
      if (DOM.voiceButton) DOM.voiceButton.classList.remove('is-recording');
      showToast('Erreur reconnaissance vocale');
    };

    STATE.recognition.onend = () => {
      STATE.isRecording = false;
      if (DOM.voiceButton) DOM.voiceButton.classList.remove('is-recording');
    };
  }

  function toggleVoice() {
    if (!STATE.recognition) {
      showToast('La saisie vocale n\'est pas supportée sur ce navigateur.');
      return;
    }
    if (STATE.isRecording) {
      STATE.recognition.stop();
    } else {
      STATE.recognition.start();
    }
  }

  /* ──────────────────────────────────────────────────
     9. CATALOGUE FILTERING & PAGINATION
  ────────────────────────────────────────────────── */
  function filterTools() {
    readSettingsFromControls();
    const items = Array.from(DOM.toolsList.querySelectorAll('.tool-result'));
    let visibleCount = 0;
    let displayedCount = 0;

    items.forEach(item => {
      const catMatch = STATE.activeCategory === 'all' || item.dataset.category.toLowerCase().includes(STATE.activeCategory);
      const tagMatch = STATE.activeTag === 'all' || item.dataset.search.includes(STATE.activeTag);
      const priceMatch = !STATE.settings.defaultPricing || STATE.settings.defaultPricing === 'all' || item.dataset.price.toLowerCase().includes(STATE.settings.defaultPricing.toLowerCase());

      if (catMatch && tagMatch && priceMatch) {
        visibleCount++;
      }

      if (catMatch && tagMatch && priceMatch && displayedCount < STATE.pageSize) {
        item.style.display = 'flex';
        displayedCount++;
      } else {
        item.style.display = 'none';
      }
    });

    if (DOM.toolsCountLabel) {
      DOM.toolsCountLabel.textContent = `${displayedCount}/${visibleCount} référence${visibleCount > 1 ? 's' : ''}`;
    }
  }

  /* ──────────────────────────────────────────────────
     10. CODE ACTIVATION (Finder Plus)
  ────────────────────────────────────────────────── */
  async function activatePlusCode(code, statusEl) {
    if (!code || !code.trim()) {
      if (statusEl) { statusEl.textContent = 'Veuillez entrer un code.'; statusEl.className = 'upgrade-status is-error'; }
      return;
    }
    statusEl.textContent = 'Vérification du code...';
    statusEl.className = 'upgrade-status';

    try {
      const res = await fetch('/api/activer-plus/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrftoken
        },
        body: JSON.stringify({ code: code.trim() })
      });

      const data = await res.json();
      if (res.ok && data.ok) {
        statusEl.textContent = '🎉 ' + (data.message || 'Plan Finder Plus activé avec succès !');
        statusEl.className = 'upgrade-status is-success';
        showToast('Finder Plus activé !');
        setTimeout(() => {
          if (DOM.upgradeDialog) DOM.upgradeDialog.close();
        }, 1500);
      } else {
        statusEl.textContent = data.error || 'Code invalide ou expiré.';
        statusEl.className = 'upgrade-status is-error';
      }
    } catch (e) {
      statusEl.textContent = 'Erreur lors de la validation.';
      statusEl.className = 'upgrade-status is-error';
    }
  }

  /* ──────────────────────────────────────────────────
     11. EVENT LISTENERS
  ────────────────────────────────────────────────── */

  // Sidebar toggle
  if (DOM.menuButton) DOM.menuButton.addEventListener('click', toggleSidebar);
  if (DOM.sidebarToggleButton) DOM.sidebarToggleButton.addEventListener('click', toggleSidebar);

  // Split View toggle
  if (DOM.splitViewButton) DOM.splitViewButton.addEventListener('click', () => togglePanel());
  if (DOM.closePanelButton) DOM.closePanelButton.addEventListener('click', () => togglePanel(false));
  if (DOM.openPanelButton) DOM.openPanelButton.addEventListener('click', () => togglePanel(true));

  // Panel Tabs
  DOM.panelTabs.forEach(tab => {
    tab.addEventListener('click', () => switchPanelTab(tab.dataset.panel));
  });

  // Composer Textarea Auto-Resize & Submit on Enter
  if (DOM.searchInput) {
    DOM.searchInput.addEventListener('input', () => {
      DOM.searchInput.style.height = 'auto';
      DOM.searchInput.style.height = Math.min(DOM.searchInput.scrollHeight, 220) + 'px';
    });

    DOM.searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        DOM.searchForm.dispatchEvent(new Event('submit'));
      }
    });
  }

  // Search Form Submit
  if (DOM.searchForm) {
    DOM.searchForm.addEventListener('submit', (e) => {
      e.preventDefault();
      executeSearch(DOM.searchInput.value);
    });
  }

  // Quick suggestions
  if (DOM.quickSuggestions) {
    DOM.quickSuggestions.addEventListener('click', (e) => {
      const pill = e.target.closest('.suggestion-pill');
      if (pill && pill.dataset.query) {
        DOM.searchInput.value = pill.dataset.query;
        executeSearch(pill.dataset.query);
      }
    });
  }

  // Fichiers de contexte : joindre / téléverser + suppression
  if (DOM.attachButton && DOM.fileInput) {
    DOM.attachButton.addEventListener('click', () => DOM.fileInput.click());
  }
  if (DOM.contextAddBtn && DOM.fileInput) {
    DOM.contextAddBtn.addEventListener('click', () => DOM.fileInput.click());
  }
  if (DOM.fileInput) {
    DOM.fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      uploadContextFile(file);
      DOM.fileInput.value = '';
    });
  }
  if (DOM.contextFilesChips) {
    DOM.contextFilesChips.addEventListener('click', (e) => {
      const btn = e.target.closest('.file-chip-remove');
      if (btn) deleteContextFile(btn.dataset.id);
    });
  }

  // Voice recognition button
  if (DOM.voiceButton) DOM.voiceButton.addEventListener('click', toggleVoice);

  // Model Mode switch button
  if (DOM.modelButton) {
    DOM.modelButton.addEventListener('click', () => {
      STATE.modelMode = STATE.modelMode === 'Extra' ? 'Standard' : 'Extra';
      if (DOM.modelLabel) DOM.modelLabel.textContent = STATE.modelMode;
      showToast(`Mode d'analyse : Finder AI ${STATE.modelMode}`);
    });
  }

  // History buttons back / forward
  if (DOM.historyBackButton) {
    DOM.historyBackButton.addEventListener('click', () => {
      if (STATE.historyIndex < STATE.history.length - 1) {
        STATE.historyIndex++;
        const item = STATE.history[STATE.historyIndex];
        if (item) {
          DOM.searchInput.value = item.query;
          renderSearchResults(item.query, item.data);
          togglePanel(true);
        }
        updateHistoryButtons();
      }
    });
  }
  if (DOM.historyForwardButton) {
    DOM.historyForwardButton.addEventListener('click', () => {
      if (STATE.historyIndex > 0) {
        STATE.historyIndex--;
        const item = STATE.history[STATE.historyIndex];
        if (item) {
          DOM.searchInput.value = item.query;
          renderSearchResults(item.query, item.data);
          togglePanel(true);
        }
        updateHistoryButtons();
      }
    });
  }

  // New Search button (Ctrl+K)
  if (DOM.newSearchButton) {
    DOM.newSearchButton.addEventListener('click', () => {
      DOM.searchInput.value = '';
      DOM.searchInput.focus();
    });
  }
  if (DOM.topSearchButton) {
    DOM.topSearchButton.addEventListener('click', () => {
      DOM.searchInput.focus();
    });
  }

  // Recents clicks (sidebar & central)
  document.addEventListener('click', (e) => {
    const recBtn = e.target.closest('.sidebar-recent, .central-recent');
    if (recBtn && recBtn.dataset.idx !== undefined) {
      const item = STATE.history[parseInt(recBtn.dataset.idx, 10)];
      if (item) {
        DOM.searchInput.value = item.query;
        renderSearchResults(item.query, item.data);
        togglePanel(true);
      }
    }
  });

  // Category Pills
  if (DOM.categoryPills) {
    DOM.categoryPills.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-pill');
      if (!btn) return;
      DOM.categoryPills.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      STATE.activeCategory = btn.dataset.cat;
      loadToolsPage(1);
    });
  }

  // Tag Pills
  if (DOM.tagPills) {
    DOM.tagPills.addEventListener('click', (e) => {
      const btn = e.target.closest('.filter-pill');
      if (!btn) return;
      DOM.tagPills.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      STATE.activeTag = btn.dataset.tag;
      loadToolsPage(1);
    });
  }

  // Tool click from catalog -> display details in panel
  if (DOM.toolsList) {
    DOM.toolsList.addEventListener('click', (e) => {
      const toolBtn = e.target.closest('.tool-result');
      if (!toolBtn) return;
      
      DOM.toolsList.querySelectorAll('.tool-result').forEach(b => b.classList.remove('is-active'));
      toolBtn.classList.add('is-active');

      const name = toolBtn.dataset.name;
      const desc = toolBtn.dataset.description;
      const cat = toolBtn.dataset.category;
      const price = toolBtn.dataset.price;
      const url = toolBtn.dataset.url;

      // Outil actif : utilisé par les favoris et les avis
      const id = toolBtn.dataset.id ? parseInt(toolBtn.dataset.id, 10) : null;
      STATE.activeToolId = id;
      STATE.activeTool = id ? {
        id,
        nom: name,
        description: desc,
        type_tarification: price,
        categorie: cat,
        url_site: url,
        is_favori: toolBtn.dataset.isFavori === 'true',
        avis: [],
      } : null;
      renderFavoriState();
      renderReviews([]);

      if (DOM.resultPanelTitle) DOM.resultPanelTitle.textContent = name;
      if (DOM.resultDescription) DOM.resultDescription.textContent = desc;
      if (DOM.resultPrice) DOM.resultPrice.textContent = price;
      if (DOM.resultCategory) DOM.resultCategory.textContent = cat;
      if (DOM.resultLink && url) {
        DOM.resultLink.href = url;
        DOM.resultLink.style.display = 'flex';
      }

      togglePanel(true);
    });
  }

  // Profile Mini-modal toggle
  if (DOM.profileMenuBtn && DOM.profileMiniModal) {
    DOM.profileMenuBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      const hidden = DOM.profileMiniModal.hasAttribute('hidden');
      if (hidden) DOM.profileMiniModal.removeAttribute('hidden');
      else DOM.profileMiniModal.setAttribute('hidden', '');
    });

    document.addEventListener('click', (e) => {
      if (!DOM.profileMiniModal.contains(e.target) && !DOM.profileMenuBtn.contains(e.target)) {
        DOM.profileMiniModal.setAttribute('hidden', '');
      }
    });
  }

  // Open Settings Dialog — défaut : onglet "compte"
  function openSettings(tab = 'compte') {
    if (DOM.profileMiniModal) DOM.profileMiniModal.setAttribute('hidden', '');
    if (DOM.settingsDialog) {
      DOM.settingsDialog.showModal();
      switchSettingsTab(tab);
      loadSensitiveSettings();
    }
  }

  // La clé Gemini n'est jamais injectée dans le HTML : elle est récupérée
  // exclusivement via l'API JSON lors de l'ouverture des paramètres.
  async function loadSensitiveSettings() {
    try {
      const res = await fetch('/api/settings/', { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      if (!res.ok) return;
      const data = await res.json();
      if (data.ok && DOM.geminiKeyInput) {
        DOM.geminiKeyInput.value = data.gemini_api_key || '';
      }
    } catch (e) {}
  }

  function switchSettingsTab(tabName) {
    STATE.activeSettingsTab = tabName;
    DOM.settingsTabs.forEach(t => {
      t.classList.toggle('is-active', t.dataset.settingsTab === tabName);
    });
    DOM.settingsPanes.forEach(p => {
      p.classList.toggle('is-active', p.id === `pane-${tabName}`);
    });
  }

  if (DOM.openSettingsSidebarBtn) DOM.openSettingsSidebarBtn.addEventListener('click', () => openSettings());
  if (DOM.pmmSettingsBtn) DOM.pmmSettingsBtn.addEventListener('click', () => openSettings());
  if (DOM.closeSettingsBtn) DOM.closeSettingsBtn.addEventListener('click', () => DOM.settingsDialog.close());

  DOM.settingsTabs.forEach(tab => {
    tab.addEventListener('click', () => switchSettingsTab(tab.dataset.settingsTab));
  });

  /* ──────────────────────────────────────────────────
     Composants interactifs des paramètres
  ────────────────────────────────────────────────── */

  // Helper : active un seul bouton dans un groupe segmenté
  function initSegmented(containerId, onChange) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.addEventListener('click', (e) => {
      const btn = e.target.closest('.segmented-btn');
      if (!btn) return;
      el.querySelectorAll('.segmented-btn').forEach(b => b.classList.remove('is-active'));
      btn.classList.add('is-active');
      if (onChange) onChange(btn.dataset.val);
    });
  }

  // Helper : toggle pills (multi-sélection)
  function initPills(containerId) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.addEventListener('click', (e) => {
      const pill = e.target.closest('.antigravity-pill');
      if (!pill) return;
      pill.classList.toggle('is-selected');
    });
  }

  // 1. Thème OLED
  initSegmented('themeSegmented', (val) => {
    STATE.settings.ui.theme = val;
    applyUiPreferences();
    persistLocalSettings();
    showToast(val === 'oled' ? 'Thème OLED activé' : 'Thème bleu nuit activé');
  });

  // 2. Mode d'affichage Grille / Liste
  initSegmented('viewModeSegmented', (val) => {
    STATE.settings.ui.viewMode = val;
    applyUiPreferences();
    persistLocalSettings();
    showToast(val === 'grid' ? 'Vue en grille activée' : 'Vue en liste activée');
  });

  // 3. Densité de l'interface
  initSegmented('densitySegmented', (val) => {
    STATE.settings.ui.density = val;
    applyUiPreferences();
    persistLocalSettings();
    showToast(val === 'compact' ? 'Interface compacte activée' : 'Interface confortable activée');
  });

  // 4. Taille de police
  initSegmented('fontSizeSegmented', (val) => {
    STATE.settings.ui.fontSize = val;
    applyUiPreferences();
    persistLocalSettings();
    showToast('Taille de police mise à jour');
  });

  // 5. Réduction des animations (AJAX)
  initSegmented('motionSegmented', (val) => {
    STATE.settings.ui.motion = val;
    applyUiPreferences();
    persistLocalSettings();
    showToast(val === 'on' ? 'Animations réduites activées' : 'Animations standard restaurées');
  });

  // 6. Mode AJAX de rechargement
  initSegmented('prefAjaxModeSegmented', (val) => {
    STATE.settings.ajaxMode = val;
    persistLocalSettings();
    showToast(val === 'instant' ? 'Rechargement instantané actif' : 'Rechargement après validation actif');
  });

  initSegmented('sourceModeSegmented', (val) => {
    STATE.settings.sourceMode = val;
    STATE.settings.includeWeb = val !== 'catalog';
    if (DOM.includeWebToggle) DOM.includeWebToggle.checked = STATE.settings.includeWeb;
    persistLocalSettings();
    showToast(`Mode de recherche : ${val}`);
  });

  // 7. Pills de catégories préférées (multi-sélection)
  initPills('prefCategoriesPills');
  initPills('researchSourcesPills');
  initPills('techStackPills');

  if (DOM.settingsProfileForm) {
    DOM.settingsProfileForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (DOM.settingsSaveStatus) DOM.settingsSaveStatus.textContent = 'Sauvegarde...';
      try {
        await saveProfileSettings();
        readSettingsFromControls();
        persistLocalSettings();
        if (DOM.settingsSaveStatus) DOM.settingsSaveStatus.textContent = 'Profil sauvegardé.';
        showToast('Profil de recommandation mis à jour');
      } catch (err) {
        if (DOM.settingsSaveStatus) DOM.settingsSaveStatus.textContent = err.message;
        showToast('Impossible de sauvegarder le profil');
      }
    });
  }

  if (DOM.saveSearchPrefsBtn) {
    DOM.saveSearchPrefsBtn.addEventListener('click', async () => {
      if (DOM.searchPrefsSaveStatus) DOM.searchPrefsSaveStatus.textContent = 'Application...';
      try {
        await savePreferenceSettings();
        applyUiPreferences();
        loadToolsPage(1);
        if (DOM.searchPrefsSaveStatus) DOM.searchPrefsSaveStatus.textContent = 'Préférences appliquées.';
        showToast('Préférences de recherche actives');
      } catch (err) {
        if (DOM.searchPrefsSaveStatus) DOM.searchPrefsSaveStatus.textContent = err.message;
        showToast('Impossible de sauvegarder les préférences');
      }
    });
  }

  [DOM.prefResultStyle, DOM.prefDefaultPricing, DOM.includeWebToggle, DOM.sourceTransparencyToggle, DOM.watchFrequencySelect]
    .filter(Boolean)
    .forEach(control => {
      control.addEventListener('change', () => {
        readSettingsFromControls();
        persistLocalSettings();
        loadToolsPage(1);
      });
    });

  if (DOM.geminiKeyToggle && DOM.geminiKeyInput) {
    DOM.geminiKeyToggle.addEventListener('click', () => {
      DOM.geminiKeyInput.type = DOM.geminiKeyInput.type === 'password' ? 'text' : 'password';
    });
  }

  // Projects Dialog
  if (DOM.projectsButton && DOM.projectsLibrary) {
    DOM.projectsButton.addEventListener('click', () => DOM.projectsLibrary.showModal());
  }
  if (DOM.closeProjectsBtn) DOM.closeProjectsBtn.addEventListener('click', () => DOM.projectsLibrary.close());

  // Propose Tool Dialog
  if (DOM.proposeToolButton && DOM.proposeToolDialog) {
    DOM.proposeToolButton.addEventListener('click', () => DOM.proposeToolDialog.showModal());
  }
  if (DOM.proposeToolCloseBtn) DOM.proposeToolCloseBtn.addEventListener('click', () => DOM.proposeToolDialog.close());
  if (DOM.proposeToolForm) {
    DOM.proposeToolForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const submitBtn = document.getElementById('submitProposeBtn');
      const formData = new FormData(DOM.proposeToolForm);
      const payload = {
        nom: formData.get('nom') || '',
        description: formData.get('description') || '',
        url_site: formData.get('url_site') || '',
        type_tarification: formData.get('type_tarification') || 'Freemium',
        type_integration: formData.get('type_integration') || 'Web / API',
        categorie_id: formData.get('categorie_id') || null,
      };
      if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = 'Soumission…'; }
      try {
        const res = await fetch('/api/outils/proposer/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrftoken
          },
          body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.ok) {
          showToast(data.message || 'Proposition soumise pour validation.');
          DOM.proposeToolForm.reset();
          DOM.proposeToolDialog.close();
        } else {
          showToast(data.error || 'Impossible de soumettre la proposition.', 4000);
        }
      } catch (err) {
        showToast('Erreur lors de la soumission.', 4000);
      } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = 'Soumettre pour validation'; }
      }
    });
  }

  // Upgrade Dialog
  if (DOM.upgradeButton && DOM.upgradeDialog) {
    DOM.upgradeButton.addEventListener('click', () => DOM.upgradeDialog.showModal());
  }
  if (DOM.upgradeCloseButton) DOM.upgradeCloseButton.addEventListener('click', () => DOM.upgradeDialog.close());

  if (DOM.upgradeActivateButton) {
    DOM.upgradeActivateButton.addEventListener('click', () => {
      activatePlusCode(DOM.upgradeCodeInput.value, DOM.upgradeStatus);
    });
  }
  if (DOM.activateCodeInSettings) {
    DOM.activateCodeInSettings.addEventListener('click', () => {
      activatePlusCode(DOM.upgradeCodeInSettings.value, DOM.upgradeStatusSettings);
    });
  }

  // Review Modal
  if (DOM.openReviewModalBtn && DOM.reviewDialog) {
    DOM.openReviewModalBtn.addEventListener('click', () => {
      if (!STATE.activeToolId) {
        showToast('Sélectionnez d\'abord un outil dans le catalogue.');
        return;
      }
      DOM.reviewDialog.showModal();
      if (DOM.reviewFormStatus) { DOM.reviewFormStatus.textContent = ''; DOM.reviewFormStatus.className = 'dialog-status'; }
    });
  }
  if (DOM.reviewCloseBtn) DOM.reviewCloseBtn.addEventListener('click', () => DOM.reviewDialog.close());

  // Star Rating Selector
  if (DOM.starRatingSelect) {
    DOM.starRatingSelect.addEventListener('click', (e) => {
      const star = e.target.closest('span');
      if (!star) return;
      const note = parseInt(star.dataset.star, 10);
      DOM.reviewNoteInput.value = note;
      DOM.starRatingSelect.querySelectorAll('span').forEach((s, idx) => {
        s.classList.toggle('is-selected', idx < note);
      });
    });
  }

  // Publication d'un avis -> /api/outils/<id>/avis/
  if (DOM.reviewForm) {
    DOM.reviewForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!STATE.activeToolId) {
        if (DOM.reviewFormStatus) DOM.reviewFormStatus.textContent = 'Sélectionnez d\'abord un outil.';
        return;
      }
      const note = DOM.reviewNoteInput ? parseInt(DOM.reviewNoteInput.value, 10) : 5;
      const commentaire = DOM.reviewCommentInput ? DOM.reviewCommentInput.value.trim() : '';
      if (!commentaire) {
        if (DOM.reviewFormStatus) DOM.reviewFormStatus.textContent = 'Veuillez saisir un commentaire.';
        return;
      }
      if (DOM.reviewFormStatus) { DOM.reviewFormStatus.textContent = 'Publication de votre avis...'; DOM.reviewFormStatus.className = 'dialog-status'; }
      if (DOM.submitReviewBtn) { DOM.submitReviewBtn.disabled = true; DOM.submitReviewBtn.textContent = 'Publication…'; }
      try {
        const res = await fetch(`/api/outils/${STATE.activeToolId}/avis/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrftoken },
          body: JSON.stringify({ note, commentaire })
        });
        const data = await res.json();
        if (!res.ok || !data.ok) throw new Error(data.error || 'Impossible de publier l\'avis');

        if (DOM.reviewFormStatus) {
          DOM.reviewFormStatus.textContent = data.message || 'Votre avis a été publié.';
          DOM.reviewFormStatus.classList.add('is-success');
        }
        // Met à jour la liste des avis affichée dans le panneau
        if (STATE.activeTool) {
          const avis = Array.isArray(STATE.activeTool.avis) ? STATE.activeTool.avis.slice() : [];
          avis.unshift(data.new_avis);
          STATE.activeTool.avis = avis;
          STATE.activeTool.score = data.score;
          if (DOM.resultRatingBadge) DOM.resultRatingBadge.textContent = `${data.score}/5`;
          renderReviews(avis);
        }
        DOM.reviewForm.reset();
        if (DOM.starRatingSelect) {
          DOM.starRatingSelect.querySelectorAll('span').forEach((s, idx) => s.classList.toggle('is-selected', idx < 5));
        }
        setTimeout(() => DOM.reviewDialog.close(), 1200);
      } catch (err) {
        if (DOM.reviewFormStatus) {
          DOM.reviewFormStatus.textContent = err.message;
          DOM.reviewFormStatus.classList.add('is-error');
        }
      } finally {
        if (DOM.submitReviewBtn) { DOM.submitReviewBtn.disabled = false; DOM.submitReviewBtn.textContent = 'Publier l\'avis'; }
      }
    });
  }

  // Copy result text
  if (DOM.copyResultButton) {
    DOM.copyResultButton.addEventListener('click', () => {
      const title = DOM.resultPanelTitle ? DOM.resultPanelTitle.textContent : '';
      const desc = DOM.resultDescription ? DOM.resultDescription.textContent : '';
      const text = `${title}\n\n${desc}`;
      navigator.clipboard.writeText(text).then(() => showToast('Synthèse copiée dans le presse-papier !'));
    });
  }

  // Favoris : toggle via l'API
  if (DOM.toggleFavoriBtn) {
    DOM.toggleFavoriBtn.addEventListener('click', toggleFavori);
  }

  // Export PDF (blob réel généré côté client)
  if (DOM.downloadPdfCta) DOM.downloadPdfCta.addEventListener('click', generateReportPDF);
  if (DOM.downloadResultButton) DOM.downloadResultButton.addEventListener('click', generateReportPDF);

  // Projets : création
  if (DOM.newProjectForm) {
    DOM.newProjectForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const nom = (DOM.newProjectName ? DOM.newProjectName.value : '').trim();
      const description = DOM.newProjectDescription ? DOM.newProjectDescription.value.trim() : '';
      if (!nom) {
        if (DOM.projectCreateStatus) DOM.projectCreateStatus.textContent = 'Le nom du projet est requis.';
        return;
      }
      if (DOM.projectCreateStatus) DOM.projectCreateStatus.textContent = 'Création...';
      if (DOM.createProjectBtn) DOM.createProjectBtn.disabled = true;
      try {
        await createProject(nom, description);
        if (DOM.projectCreateStatus) DOM.projectCreateStatus.textContent = 'Projet créé.';
        DOM.newProjectForm.reset();
        loadProjects();
      } catch (err) {
        if (DOM.projectCreateStatus) DOM.projectCreateStatus.textContent = err.message;
      } finally {
        if (DOM.createProjectBtn) DOM.createProjectBtn.disabled = false;
      }
    });
  }
  if (DOM.newProjectBtn) {
    DOM.newProjectBtn.addEventListener('click', () => {
      if (DOM.newProjectName) DOM.newProjectName.focus();
    });
  }

  // Pagination réelle via /api/outils/
  if (DOM.prevPageBtn) {
    DOM.prevPageBtn.addEventListener('click', () => {
      if (STATE.currentPage > 1) loadToolsPage(STATE.currentPage - 1);
    });
  }
  if (DOM.nextPageBtn) {
    DOM.nextPageBtn.addEventListener('click', () => {
      if (STATE.currentPage < STATE.numPages) loadToolsPage(STATE.currentPage + 1);
    });
  }

  // Explorateur : affiche/masque le catalogue paginé
  if (DOM.toolsButton) {
    DOM.toolsButton.addEventListener('click', () => {
      const contentArea = document.querySelector('.content-area');
      if (!contentArea) return;
      const currentlyHidden = !contentArea.style.display || contentArea.style.display === 'none';
      contentArea.style.display = currentlyHidden ? 'block' : 'none';
      if (currentlyHidden) loadToolsPage(STATE.currentPage || 1);
    });
  }

  // Épingler un projet (localStorage)
  if (DOM.pinProjectButton) {
    DOM.pinProjectButton.addEventListener('click', () => {
      const isPinned = DOM.pinProjectButton.getAttribute('aria-pressed') === 'true';
      const next = !isPinned;
      DOM.pinProjectButton.setAttribute('aria-pressed', next ? 'true' : 'false');
      DOM.pinProjectButton.classList.toggle('is-active', next);
      try {
        if (next) localStorage.setItem('finder_ai_pinned_project', STATE.activeToolId ? String(STATE.activeToolId) : 'workspace');
        else localStorage.removeItem('finder_ai_pinned_project');
      } catch (e) {}
      showToast(next ? 'Projet épinglé dans l\'espace de travail' : 'Projet détaché');
    });
  }

  // Menu d'actions du projet (nouvelle recherche / copier le lien)
  if (DOM.projectActionsButton && DOM.projectActionMenu) {
    DOM.projectActionsButton.addEventListener('click', (e) => {
      e.stopPropagation();
      if (DOM.projectActionMenu.hasAttribute('hidden')) DOM.projectActionMenu.removeAttribute('hidden');
      else DOM.projectActionMenu.setAttribute('hidden', '');
    });
    document.addEventListener('click', (e) => {
      if (!DOM.projectActionMenu.contains(e.target) && !DOM.projectActionsButton.contains(e.target)) {
        DOM.projectActionMenu.setAttribute('hidden', '');
      }
    });
    const actionNewSearch = document.getElementById('actionNewSearchButton');
    if (actionNewSearch) actionNewSearch.addEventListener('click', () => {
      DOM.projectActionMenu.setAttribute('hidden', '');
      if (DOM.searchInput) DOM.searchInput.focus();
    });
    const actionCopy = document.getElementById('actionCopyProjectButton');
    if (actionCopy) actionCopy.addEventListener('click', () => {
      DOM.projectActionMenu.setAttribute('hidden', '');
      navigator.clipboard.writeText(window.location.href)
        .then(() => showToast('Lien copié dans le presse-papier'))
        .catch(() => showToast('Impossible de copier le lien'));
    });
  }

  // Keyboard Shortcuts (Ctrl+K, Ctrl+B, Escape)
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      DOM.searchInput.focus();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      toggleSidebar();
    }
  });

  // Range slider label
  if (DOM.maxResultsRange && DOM.resultsCountLabel) {
    DOM.maxResultsRange.addEventListener('input', (e) => {
      DOM.resultsCountLabel.textContent = e.target.value;
      STATE.pageSize = parseInt(e.target.value, 10);
      STATE.settings.maxResults = STATE.pageSize;
      persistLocalSettings();
      loadToolsPage(1);
    });
  }

  // Export Data JSON
  if (DOM.exportDataBtn) {
    DOM.exportDataBtn.addEventListener('click', () => {
      const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify({
        history: STATE.history,
        contextFiles: STATE.contextFiles,
        exportDate: new Date().toISOString()
      }, null, 2));
      const downloadAnchor = document.createElement('a');
      downloadAnchor.setAttribute("href", dataStr);
      downloadAnchor.setAttribute("download", `finder_ai_backup_${Date.now()}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
      showToast('Données exportées au format JSON');
    });
  }

  // Clear History
  if (DOM.clearHistoryBtn) {
    DOM.clearHistoryBtn.addEventListener('click', () => {
      if (confirm('Voulez-vous vraiment effacer tout votre historique ?')) {
        STATE.history = [];
        localStorage.removeItem('finder_ai_history');
        renderHistoryUI();
        showToast('Historique effacé');
      }
    });
  }

  // Clear Session Keywords
  const clearSessionKeywordsBtn = document.getElementById('clearSessionKeywordsBtn');
  if (clearSessionKeywordsBtn) {
    clearSessionKeywordsBtn.addEventListener('click', clearSession);
  }

  /* ──────────────────────────────────────────────────
     12. INITIALIZATION
  ────────────────────────────────────────────────── */
  readSettingsFromControls();
  loadLocalSettings();
  syncControlsFromSettings();
  applyUiPreferences();
  loadHistory();
  loadContextFiles();
  loadQuota();
  loadProjects();
  loadToolsPage(1);
  initVoiceRecognition();
  initDynamicGreeting();

  console.log('⚡ FINDER-AI v13 Workspace Initialisé.');
});
