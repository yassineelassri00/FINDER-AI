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
    const todayStr = new Date().toLocaleDateString();
    const todayCount = STATE.history.filter(h => h.fullDate === new Date().toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' })).length;
    if (DOM.usageCount) DOM.usageCount.textContent = `${Math.min(todayCount, 3)}/3`;
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
      const ext = f.nom_fichier ? f.nom_fichier.split('.').pop().toUpperCase() : 'FILE';
      return `
        <div class="file-chip" data-id="${f.id}">
          <svg viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><polyline points="13 2 13 9 20 9"/></svg>
          <span>${escapeHTML(f.nom_fichier)}</span>
          <span class="chip-ext">${ext}</span>
          <button type="button" class="file-chip-remove" data-id="${f.id}" title="Supprimer">✕</button>
        </div>
      `;
    }).join('');

    if (DOM.contextFilesSummary) {
      DOM.contextFilesSummary.innerHTML = STATE.contextFiles.map(f => `• ${escapeHTML(f.nom_fichier)} (${f.taille || '2 KB'})`).join('<br>');
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

  // File attach button -> open file dialog
  if (DOM.attachButton && DOM.fileInput) {
    DOM.attachButton.addEventListener('click', () => DOM.fileInput.click());
    DOM.fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      
      const chip = document.createElement('div');
      chip.className = 'attachment-chip';
      chip.innerHTML = `
        <svg viewBox="0 0 24 24"><path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/></svg>
        <span>${escapeHTML(file.name)}</span>
        <button type="button" class="remove-chip">✕</button>
      `;
      chip.querySelector('.remove-chip').addEventListener('click', () => chip.remove());
      DOM.composerAttachArea.appendChild(chip);
      showToast(`Fichier "${file.name}" prêt pour l'analyse`);
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
      filterTools();
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
      filterTools();
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
    }
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
        filterTools();
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
        filterTools();
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
    DOM.openReviewModalBtn.addEventListener('click', () => DOM.reviewDialog.showModal());
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

  // Copy result text
  if (DOM.copyResultButton) {
    DOM.copyResultButton.addEventListener('click', () => {
      const title = DOM.resultPanelTitle ? DOM.resultPanelTitle.textContent : '';
      const desc = DOM.resultDescription ? DOM.resultDescription.textContent : '';
      const text = `${title}\n\n${desc}`;
      navigator.clipboard.writeText(text).then(() => showToast('Synthèse copiée dans le presse-papier !'));
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
      filterTools();
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
  initVoiceRecognition();
  filterTools();
  initDynamicGreeting();

  console.log('⚡ FINDER-AI v13 Workspace Initialisé.');
});
