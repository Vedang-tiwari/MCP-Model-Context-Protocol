/**
 * MCP Autonomous Job Scout & Application System — Frontend App
 */

// Application State
const state = {
  currentView: 'jobs',
  jobs: [],
  activeJob: null,
  platforms: [],
  profile: null,
  preferences: null,
  stats: null,
  filters: {
    search: '',
    platform: '',
    score: '',
    status: ''
  }
};

// DOM Elements
const DOM = {
  tabs: document.querySelectorAll('.nav-tab'),
  views: document.querySelectorAll('.view-section'),
  jobsList: document.getElementById('jobs-list'),
  badgeTotalJobs: document.getElementById('badge-total-jobs'),
  badgeTotalPlatforms: document.getElementById('badge-total-platforms'),
  
  // Stats
  statTotalDiscovered: document.getElementById('stat-total-discovered'),
  statHighMatch: document.getElementById('stat-high-match'),
  statTotalApplied: document.getElementById('stat-total-applied'),
  statActivePlatforms: document.getElementById('stat-active-platforms'),
  
  // Filters
  filterSearch: document.getElementById('filter-search'),
  filterPlatform: document.getElementById('filter-platform'),
  filterScore: document.getElementById('filter-score'),
  filterStatus: document.getElementById('filter-status'),
  btnResetFilters: document.getElementById('btn-reset-filters'),
  
  // Scout
  btnQuickScout: document.getElementById('btn-quick-scout'),
  btnRunScoutFull: document.getElementById('btn-run-scout-full'),
  scoutRolesDisplay: document.getElementById('scout-roles-display'),
  scoutThresholdDisplay: document.getElementById('scout-threshold-display'),
  scoutAutoapplyBadge: document.getElementById('scout-autoapply-badge'),
  scoutProviderList: document.getElementById('scout-provider-list'),
  scoutConsole: document.getElementById('scout-console'),
  
  // Vault
  btnSaveProfile: document.getElementById('btn-save-profile'),
  profName: document.getElementById('prof-name'),
  profEmail: document.getElementById('prof-email'),
  profPhone: document.getElementById('prof-phone'),
  profCity: document.getElementById('prof-city'),
  profLinkedin: document.getElementById('prof-linkedin'),
  profGithub: document.getElementById('prof-github'),
  profSummary: document.getElementById('prof-summary'),
  profExperience: document.getElementById('prof-experience'),
  profNotice: document.getElementById('prof-notice'),
  profSalaryUsd: document.getElementById('prof-salary-usd'),
  profSalaryInr: document.getElementById('prof-salary-inr'),
  profWorkauth: document.getElementById('prof-workauth'),
  profResumePath: document.getElementById('prof-resume-path'),
  prefsRoles: document.getElementById('prefs-roles'),
  prefsThreshold: document.getElementById('prefs-threshold'),
  thresholdVal: document.getElementById('threshold-val'),
  prefsAutoapply: document.getElementById('prefs-autoapply'),
  prefsRemoteonly: document.getElementById('prefs-remoteonly'),
  
  // Platforms
  platformsGrid: document.getElementById('platforms-grid'),
  btnOpenAddPlatform: document.getElementById('btn-open-add-platform'),
  addPlatformModal: document.getElementById('add-platform-modal'),
  btnCloseAddPlatform: document.getElementById('btn-close-add-platform'),
  btnCancelAddPlatform: document.getElementById('btn-cancel-add-platform'),
  btnSubmitAddPlatform: document.getElementById('btn-submit-add-platform'),
  newPlatformName: document.getElementById('new-platform-name'),
  newPlatformDisplay: document.getElementById('new-platform-display'),
  newPlatformType: document.getElementById('new-platform-type'),
  newPlatformUrl: document.getElementById('new-platform-url'),
  
  // System
  sysLlmProvider: document.getElementById('sys-llm-provider'),
  sysLlmModel: document.getElementById('sys-llm-model'),
  sysDbPath: document.getElementById('sys-db-path'),
  sysDbSize: document.getElementById('sys-db-size'),
  
  // Job Modal
  jobModal: document.getElementById('job-modal'),
  btnCloseModal: document.getElementById('btn-close-modal'),
  modalJobTitle: document.getElementById('modal-job-title'),
  modalJobCompany: document.getElementById('modal-job-company'),
  modalJobLocation: document.getElementById('modal-job-location'),
  modalJobPlatform: document.getElementById('modal-job-platform'),
  modalJobScore: document.getElementById('modal-job-score'),
  modalJobReasons: document.getElementById('modal-job-reasons'),
  modalJobDesc: document.getElementById('modal-job-desc'),
  modalJobLink: document.getElementById('modal-job-link'),
  btnReEvaluate: document.getElementById('btn-re-evaluate'),
  btnApplyReview: document.getElementById('btn-apply-review'),
  btnApplySubmit: document.getElementById('btn-apply-submit'),
  
  // Toast
  toastContainer: document.getElementById('toast-container')
};

// -----------------------------------------------------------------------------
// Toast Notifications
// -----------------------------------------------------------------------------
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  
  let icon = 'ℹ';
  if (type === 'success') icon = '✓';
  if (type === 'error') icon = '✕';
  if (type === 'warning') icon = '⚠';
  
  toast.innerHTML = `<span style="color: ${type === 'success' ? 'var(--color-success)' : (type === 'error' ? 'var(--color-danger)' : 'var(--color-text)')}; font-weight: bold;">${icon}</span> <span>${message}</span>`;
  DOM.toastContainer.appendChild(toast);
  
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    toast.style.transition = 'all 150ms ease';
    setTimeout(() => toast.remove(), 150);
  }, 4000);
}

// -----------------------------------------------------------------------------
// Navigation & Views
// -----------------------------------------------------------------------------
function switchView(viewName) {
  state.currentView = viewName;
  
  DOM.tabs.forEach(tab => {
    if (tab.dataset.view === viewName) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  DOM.views.forEach(view => {
    if (view.id === `view-${viewName}`) {
      view.classList.add('active');
    } else {
      view.classList.remove('active');
    }
  });
}

// -----------------------------------------------------------------------------
// Data Fetching: Stats
// -----------------------------------------------------------------------------
async function fetchStats() {
  try {
    const res = await fetch('/api/stats');
    if (!res.ok) return;
    const data = await res.json();
    state.stats = data;

    DOM.statTotalDiscovered.textContent = data.total_discovered || 0;
    DOM.statHighMatch.textContent = data.high_match_count || 0;
    DOM.statTotalApplied.textContent = data.total_applied || 0;
    DOM.badgeTotalJobs.textContent = data.total_discovered || 0;

    if (DOM.scoutThresholdDisplay) {
      DOM.scoutThresholdDisplay.textContent = `${data.threshold_percent}% Match Score`;
      DOM.scoutAutoapplyBadge.textContent = data.auto_apply_enabled ? 'AUTO-PILOT ACTIVE' : 'REVIEW MODE';
      DOM.scoutAutoapplyBadge.className = `badge ${data.auto_apply_enabled ? 'badge-success' : ''}`;
    }
  } catch (err) {
    console.error('Failed to fetch stats:', err);
  }
}

// -----------------------------------------------------------------------------
// Data Fetching: Jobs
// -----------------------------------------------------------------------------
async function fetchJobs() {
  try {
    const params = new URLSearchParams();
    if (state.filters.search) params.append('q', state.filters.search);
    if (state.filters.platform) params.append('platform', state.filters.platform);
    if (state.filters.score) params.append('min_score', state.filters.score);
    if (state.filters.status) params.append('status', state.filters.status);

    const res = await fetch(`/api/jobs?${params.toString()}`);
    if (!res.ok) return;
    const data = await res.json();
    state.jobs = data.jobs || [];

    renderJobsList(state.jobs);
  } catch (err) {
    console.error('Failed to fetch jobs:', err);
    DOM.jobsList.innerHTML = `<div style="padding: 40px; text-align: center; color: var(--color-danger);">Failed to load jobs. Check backend connection.</div>`;
  }
}

function renderJobsList(jobs) {
  if (!jobs || jobs.length === 0) {
    DOM.jobsList.innerHTML = `
      <div style="padding: 48px 24px; text-align: center; color: var(--color-text-subtle);">
        <div style="font-size: 16px; margin-bottom: 8px; color: var(--color-text-muted);">No postings match current filters.</div>
        <div style="font-size: 13px;">Try clearing filters or run a live discovery sweep across all platforms.</div>
      </div>
    `;
    return;
  }

  DOM.jobsList.innerHTML = jobs.map(j => {
    let scoreClass = 'score-low';
    if (j.match_score >= 70) scoreClass = 'score-high';
    else if (j.match_score >= 40) scoreClass = 'score-mid';

    const isApplied = j.status === 'APPLIED';
    const statusBadgeClass = isApplied ? 'badge-success' : '';

    return `
      <div class="job-row" data-job-id="${j.id}">
        <div>
          <span class="score-pill ${scoreClass}">
            ${j.match_score !== null ? `${j.match_score}%` : '—'}
          </span>
        </div>

        <div class="job-primary">
          <div class="job-title-line">
            <span class="job-title" title="${escapeHtml(j.title)}">${escapeHtml(j.title)}</span>
            <span class="badge ${statusBadgeClass}">${j.status}</span>
            ${j.is_easy_apply ? '<span class="badge" title="1-Click Easy Apply">⚡ Fast</span>' : ''}
          </div>
          <div class="job-meta-line">
            <span class="job-company">${escapeHtml(j.company)}</span>
            <span>·</span>
            <span>${escapeHtml(j.location || 'Remote')}</span>
            <span>·</span>
            <span style="font-family: var(--font-mono); font-size: 11px;">${j.platform}</span>
          </div>
        </div>

        <div class="job-actions">
          <button class="button button-secondary button-sm btn-inspect" data-id="${j.id}">
            Details
          </button>
          <button class="button ${isApplied ? 'button-secondary' : 'button-primary'} button-sm btn-quick-apply" data-id="${j.id}" ${isApplied ? 'disabled' : ''}>
            ${isApplied ? 'Applied' : 'Apply'}
          </button>
        </div>
      </div>
    `;
  }).join('');

  // Attach event handlers
  DOM.jobsList.querySelectorAll('.btn-inspect').forEach(btn => {
    btn.addEventListener('click', () => openJobModal(btn.dataset.id));
  });

  DOM.jobsList.querySelectorAll('.btn-quick-apply').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      triggerApply(btn.dataset.id, false);
    });
  });
}

// -----------------------------------------------------------------------------
// Job Detail Modal
// -----------------------------------------------------------------------------
async function openJobModal(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}`);
    if (!res.ok) {
      showToast('Could not load job details', 'error');
      return;
    }
    const job = await res.json();
    state.activeJob = job;

    DOM.modalJobTitle.textContent = job.title;
    DOM.modalJobCompany.textContent = job.company;
    DOM.modalJobLocation.textContent = job.location || 'Remote';
    DOM.modalJobPlatform.textContent = job.platform;
    DOM.modalJobLink.href = job.apply_url || job.url;

    // Score & styling
    DOM.modalJobScore.textContent = `${job.match_score !== null ? job.match_score : 0}%`;
    DOM.modalJobScore.className = `score-pill ${job.match_score >= 70 ? 'score-high' : (job.match_score >= 40 ? 'score-mid' : 'score-low')}`;

    // Reasons
    if (job.match_reasons && job.match_reasons.length > 0) {
      DOM.modalJobReasons.innerHTML = job.match_reasons.map(r => `
        <li class="criteria-item">${escapeHtml(r)}</li>
      `).join('');
    } else {
      DOM.modalJobReasons.innerHTML = `<li class="criteria-item">Click 'Re-Evaluate Fit' to compute detailed alignment criteria.</li>`;
    }

    // Description
    DOM.modalJobDesc.textContent = job.description || 'No detailed description snippet available for this job.';

    DOM.jobModal.classList.add('open');
  } catch (err) {
    showToast('Failed to fetch job record', 'error');
  }
}

function closeJobModal() {
  DOM.jobModal.classList.remove('open');
  state.activeJob = null;
}

// -----------------------------------------------------------------------------
// Apply & Evaluate Actions
// -----------------------------------------------------------------------------
async function triggerApply(jobId, autoSubmit = false) {
  showToast(`Initiating stealth browser for job ${jobId}...`, 'info');
  try {
    const res = await fetch(`/api/jobs/${jobId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_submit: autoSubmit })
    });
    const result = await res.json();
    if (res.ok) {
      showToast(`Status: ${result.status}. ${result.notes}`, result.status === 'APPLIED' ? 'success' : 'warning');
      fetchJobs();
      fetchStats();
      if (state.activeJob && state.activeJob.id === jobId) {
        closeJobModal();
      }
    } else {
      showToast(result.error || 'Application failed', 'error');
    }
  } catch (err) {
    showToast('Failed to connect to application agent', 'error');
  }
}

async function reEvaluateActiveJob() {
  if (!state.activeJob) return;
  const jobId = state.activeJob.id;
  try {
    const res = await fetch(`/api/jobs/${jobId}/evaluate`, { method: 'POST' });
    const data = await res.json();
    if (res.ok) {
      showToast(`Match Score Updated: ${data.match_score}%`, 'success');
      state.activeJob.match_score = data.match_score;
      state.activeJob.match_reasons = data.match_reasons;
      openJobModal(jobId);
      fetchJobs();
      fetchStats();
    }
  } catch (err) {
    showToast('Evaluation failed', 'error');
  }
}

// -----------------------------------------------------------------------------
// Live Discovery Scout
// -----------------------------------------------------------------------------
async function triggerLiveScout() {
  DOM.btnQuickScout.disabled = true;
  DOM.btnRunScoutFull.disabled = true;
  DOM.btnQuickScout.querySelector('span:last-child').textContent = 'Scouting...';
  
  appendScoutLog('[START] Triggering multi-platform discovery sweep across all enabled sources...');
  showToast('Live discovery sweep launched...', 'info');

  try {
    const res = await fetch('/api/scout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ max_age_hours: 24 })
    });
    const data = await res.json();

    if (res.ok && data.success) {
      const s = data.summary;
      appendScoutLog(`[COMPLETE] Discovered ${s.new_unique_jobs} new unique jobs from ${s.total_fetched} total parsed listings.`);
      appendScoutLog(`[MATCHES] ${s.qualified_matches} qualified listings matched your profile threshold (≥${s.threshold}%).`);
      showToast(`Sweep complete: ${s.new_unique_jobs} new jobs added to database!`, 'success');
      fetchStats();
      fetchJobs();
    } else {
      appendScoutLog(`[ERROR] Discovery sweep encountered issues.`);
      showToast('Scout sweep failed', 'error');
    }
  } catch (err) {
    appendScoutLog(`[ERROR] Connection failed: ${err.message}`);
    showToast('Failed to trigger scout', 'error');
  } finally {
    DOM.btnQuickScout.disabled = false;
    DOM.btnRunScoutFull.disabled = false;
    DOM.btnQuickScout.querySelector('span:last-child').textContent = 'Run Discovery Sweep';
  }
}

function appendScoutLog(msg) {
  const time = new Date().toLocaleTimeString();
  DOM.scoutConsole.textContent += `\n[${time}] ${msg}`;
  DOM.scoutConsole.scrollTop = DOM.scoutConsole.scrollHeight;
}

// -----------------------------------------------------------------------------
// Candidate Vault: Profile & Preferences
// -----------------------------------------------------------------------------
async function fetchProfile() {
  try {
    const res = await fetch('/api/profile');
    if (!res.ok) return;
    const data = await res.json();
    state.profile = data.profile;
    state.preferences = data.preferences;

    // Populate inputs
    const p = data.profile.personal_info || {};
    DOM.profName.value = p.full_name || '';
    DOM.profEmail.value = p.email || '';
    DOM.profPhone.value = p.phone || '';
    DOM.profCity.value = `${p.current_city || ''}, ${p.country || ''}`.replace(/^, |, $/g, '');
    DOM.profLinkedin.value = p.linkedin_url || '';
    DOM.profGithub.value = p.github_url || '';
    DOM.profSummary.value = data.profile.summary || '';

    const std = data.profile.standard_answers || {};
    DOM.profExperience.value = std.years_of_experience || 3;
    DOM.profNotice.value = std.notice_period_days || 15;
    DOM.profSalaryUsd.value = std.expected_salary_usd || 120000;
    DOM.profSalaryInr.value = std.expected_salary_inr || 2000000;
    DOM.profWorkauth.value = std.work_authorization || '';
    DOM.profResumePath.value = data.profile.resume_file_path || 'config/resume.pdf';

    const prefs = data.preferences || {};
    DOM.prefsRoles.value = (prefs.target_roles || []).join('\n');
    DOM.prefsThreshold.value = prefs.match_threshold_percent || 70;
    DOM.thresholdVal.textContent = DOM.prefsThreshold.value;
    DOM.prefsAutoapply.checked = Boolean(prefs.auto_apply);
    DOM.prefsRemoteonly.checked = Boolean(prefs.remote_only);

    // Update scout view tags
    if (DOM.scoutRolesDisplay) {
      DOM.scoutRolesDisplay.innerHTML = (prefs.target_roles || []).map(r => `
        <span class="badge">${escapeHtml(r)}</span>
      `).join('');
    }
  } catch (err) {
    console.error('Failed to load profile:', err);
  }
}

async function saveProfile() {
  try {
    const roles = DOM.prefsRoles.value
      .split('\n')
      .map(r => r.trim())
      .filter(Boolean);

    const cityCountry = DOM.profCity.value.split(',');
    const currentCity = cityCountry[0] ? cityCountry[0].trim() : '';
    const country = cityCountry[1] ? cityCountry[1].trim() : '';

    const updatedProfile = {
      ...state.profile,
      personal_info: {
        ...(state.profile ? state.profile.personal_info : {}),
        full_name: DOM.profName.value.trim(),
        email: DOM.profEmail.value.trim(),
        phone: DOM.profPhone.value.trim(),
        current_city: currentCity,
        country: country,
        linkedin_url: DOM.profLinkedin.value.trim(),
        github_url: DOM.profGithub.value.trim()
      },
      summary: DOM.profSummary.value.trim(),
      standard_answers: {
        ...(state.profile ? state.profile.standard_answers : {}),
        years_of_experience: parseInt(DOM.profExperience.value) || 3,
        notice_period_days: parseInt(DOM.profNotice.value) || 15,
        expected_salary_usd: parseInt(DOM.profSalaryUsd.value) || 120000,
        expected_salary_inr: parseInt(DOM.profSalaryInr.value) || 2000000,
        work_authorization: DOM.profWorkauth.value.trim()
      },
      resume_file_path: DOM.profResumePath.value.trim()
    };

    const updatedPrefs = {
      ...(state.preferences || {}),
      target_roles: roles,
      match_threshold_percent: parseInt(DOM.prefsThreshold.value) || 70,
      auto_apply: DOM.prefsAutoapply.checked,
      remote_only: DOM.prefsRemoteonly.checked
    };

    const res = await fetch('/api/profile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        profile: updatedProfile,
        preferences: updatedPrefs
      })
    });

    if (res.ok) {
      showToast('Profile & preferences saved successfully!', 'success');
      fetchProfile();
      fetchStats();
    } else {
      showToast('Failed to save profile changes', 'error');
    }
  } catch (err) {
    showToast('Error saving profile', 'error');
  }
}

// -----------------------------------------------------------------------------
// Platforms Registry
// -----------------------------------------------------------------------------
async function fetchPlatforms() {
  try {
    const res = await fetch('/api/platforms');
    if (!res.ok) return;
    const data = await res.json();
    state.platforms = data.platforms || [];

    DOM.badgeTotalPlatforms.textContent = state.platforms.length;
    DOM.statActivePlatforms.textContent = state.platforms.filter(p => p.enabled).length;

    renderPlatforms(state.platforms);
    renderScoutProviders(state.platforms);
  } catch (err) {
    console.error('Failed to load platforms:', err);
  }
}

function renderPlatforms(platforms) {
  DOM.platformsGrid.innerHTML = platforms.map(p => `
    <div class="platform-card">
      <div class="platform-card-header">
        <div>
          <div class="platform-card-title">${escapeHtml(p.display_name)}</div>
          <div style="font-family: var(--font-mono); font-size: 11px; color: var(--color-text-subtle);">
            ${p.name} · ${p.type}
          </div>
        </div>
        <label class="switch">
          <input type="checkbox" class="platform-toggle" data-name="${p.name}" ${p.enabled ? 'checked' : ''}>
          <span class="slider"></span>
        </label>
      </div>

      <div style="font-size: 12px; color: var(--color-text-muted);">
        ${p.url_template ? `<div class="code-box" style="font-size: 11px; padding: 6px;">${escapeHtml(p.url_template)}</div>` : 'Built-in crawler with direct API'}
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; font-size: 11px; color: var(--color-text-subtle);">
        <span>Source: ${p.source}</span>
        <span class="status-dot ${p.enabled ? 'active' : ''}" style="background: ${p.enabled ? 'var(--color-success)' : 'var(--color-border-strong)'};"></span>
      </div>
    </div>
  `).join('');

  DOM.platformsGrid.querySelectorAll('.platform-toggle').forEach(input => {
    input.addEventListener('change', async () => {
      const name = input.dataset.name;
      const enabled = input.checked;
      try {
        const res = await fetch(`/api/platforms/${name}/toggle`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ enabled })
        });
        if (res.ok) {
          showToast(`Platform '${name}' ${enabled ? 'enabled' : 'disabled'}`, 'info');
          fetchPlatforms();
        }
      } catch (err) {
        showToast('Toggle failed', 'error');
        input.checked = !enabled;
      }
    });
  });
}

function renderScoutProviders(platforms) {
  if (!DOM.scoutProviderList) return;
  DOM.scoutProviderList.innerHTML = platforms.map(p => `
    <div style="display: flex; align-items: center; justify-content: space-between; padding: 8px 12px; background: var(--color-surface-inset); border: 1px solid var(--color-border); border-radius: var(--radius-sm); font-size: 12px;">
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="status-dot" style="background: ${p.enabled ? 'var(--color-success)' : 'var(--color-text-subtle)'};"></span>
        <span style="font-weight: 500;">${escapeHtml(p.display_name)}</span>
        <span style="font-family: var(--font-mono); font-size: 11px; color: var(--color-text-subtle);">(${p.type})</span>
      </div>
      <span class="badge ${p.enabled ? 'badge-success' : ''}">${p.enabled ? 'ACTIVE' : 'OFFLINE'}</span>
    </div>
  `).join('');
}

async function addCustomPlatform() {
  const name = DOM.newPlatformName.value.trim().toLowerCase();
  const display = DOM.newPlatformDisplay.value.trim();
  const type = DOM.newPlatformType.value;
  const url = DOM.newPlatformUrl.value.trim();

  if (!name || !url) {
    showToast('Platform slug and URL are required', 'warning');
    return;
  }

  try {
    const res = await fetch('/api/platforms', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name,
        display_name: display || name.toUpperCase(),
        platform_type: type,
        url_template: url
      })
    });

    if (res.ok) {
      showToast(`Added platform '${name}'!`, 'success');
      DOM.addPlatformModal.classList.remove('open');
      DOM.newPlatformName.value = '';
      DOM.newPlatformDisplay.value = '';
      DOM.newPlatformUrl.value = '';
      fetchPlatforms();
    } else {
      const err = await res.json();
      showToast(err.error || 'Failed to add platform', 'error');
    }
  } catch (err) {
    showToast('Network error adding platform', 'error');
  }
}

// -----------------------------------------------------------------------------
// System Info Fetch
// -----------------------------------------------------------------------------
async function fetchSystemInfo() {
  try {
    const res = await fetch('/api/system');
    if (!res.ok) return;
    const data = await res.json();

    DOM.sysLlmProvider.textContent = data.llm_provider.toUpperCase();
    DOM.sysLlmModel.textContent = data.llm_model;
    DOM.sysDbPath.textContent = data.database_path;
    DOM.sysDbSize.textContent = `${data.database_size_kb} KB`;
  } catch (err) {
    console.error('Failed to load system info:', err);
  }
}

// -----------------------------------------------------------------------------
// Event Listeners Initialization
// -----------------------------------------------------------------------------
function initEventListeners() {
  // Navigation Tabs
  DOM.tabs.forEach(tab => {
    tab.addEventListener('click', () => switchView(tab.dataset.view));
  });

  // Filter Toolbar
  let searchTimeout = null;
  DOM.filterSearch.addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      state.filters.search = DOM.filterSearch.value.trim();
      fetchJobs();
    }, 250);
  });

  DOM.filterPlatform.addEventListener('change', () => {
    state.filters.platform = DOM.filterPlatform.value;
    fetchJobs();
  });

  DOM.filterScore.addEventListener('change', () => {
    state.filters.score = DOM.filterScore.value;
    fetchJobs();
  });

  DOM.filterStatus.addEventListener('change', () => {
    state.filters.status = DOM.filterStatus.value;
    fetchJobs();
  });

  DOM.btnResetFilters.addEventListener('click', () => {
    DOM.filterSearch.value = '';
    DOM.filterPlatform.value = '';
    DOM.filterScore.value = '';
    DOM.filterStatus.value = '';
    state.filters = { search: '', platform: '', score: '', status: '' };
    fetchJobs();
  });

  // Quick Stat Cards Click to Filter
  document.querySelectorAll('.stat-card[data-filter-status]').forEach(card => {
    card.addEventListener('click', () => {
      switchView('jobs');
      DOM.filterStatus.value = card.dataset.filterStatus;
      state.filters.status = card.dataset.filterStatus;
      fetchJobs();
    });
  });

  document.querySelectorAll('.stat-card[data-filter-min-score]').forEach(card => {
    card.addEventListener('click', () => {
      switchView('jobs');
      DOM.filterScore.value = card.dataset.filterMinScore;
      state.filters.score = card.dataset.filterMinScore;
      fetchJobs();
    });
  });

  document.querySelectorAll('.stat-card[data-nav]').forEach(card => {
    card.addEventListener('click', () => switchView(card.dataset.nav));
  });

  // Scout Triggers
  DOM.btnQuickScout.addEventListener('click', triggerLiveScout);
  DOM.btnRunScoutFull.addEventListener('click', triggerLiveScout);

  // Profile Save
  DOM.btnSaveProfile.addEventListener('click', saveProfile);
  DOM.prefsThreshold.addEventListener('input', () => {
    DOM.thresholdVal.textContent = DOM.prefsThreshold.value;
  });

  // Job Modal
  DOM.btnCloseModal.addEventListener('click', closeJobModal);
  DOM.jobModal.addEventListener('click', (e) => {
    if (e.target === DOM.jobModal) closeJobModal();
  });
  DOM.btnReEvaluate.addEventListener('click', reEvaluateActiveJob);
  DOM.btnApplyReview.addEventListener('click', () => {
    if (state.activeJob) triggerApply(state.activeJob.id, false);
  });
  DOM.btnApplySubmit.addEventListener('click', () => {
    if (state.activeJob) triggerApply(state.activeJob.id, true);
  });

  // Add Platform Modal
  DOM.btnOpenAddPlatform.addEventListener('click', () => {
    DOM.addPlatformModal.classList.add('open');
  });
  DOM.btnCloseAddPlatform.addEventListener('click', () => {
    DOM.addPlatformModal.classList.remove('open');
  });
  DOM.btnCancelAddPlatform.addEventListener('click', () => {
    DOM.addPlatformModal.classList.remove('open');
  });
  DOM.addPlatformModal.addEventListener('click', (e) => {
    if (e.target === DOM.addPlatformModal) DOM.addPlatformModal.classList.remove('open');
  });
  DOM.btnSubmitAddPlatform.addEventListener('click', addCustomPlatform);

  // Global Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      closeJobModal();
      DOM.addPlatformModal.classList.remove('open');
    }
  });
}

// Utility: Escape HTML
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// -----------------------------------------------------------------------------
// App Initialization
// -----------------------------------------------------------------------------
async function initApp() {
  initEventListeners();
  await Promise.all([
    fetchStats(),
    fetchJobs(),
    fetchProfile(),
    fetchPlatforms(),
    fetchSystemInfo()
  ]);
  console.log('MCP Web Interface initialized.');
}

window.addEventListener('DOMContentLoaded', initApp);
