/**
 * MCP Autonomous Job Scout & Application System — Frontend App
 */

// Application State
const state = {
  currentView: 'jobs',
  jobs: [],
  activeJob: null,
  platforms: [],
  resumes: [],
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
  scoutRolesCount: document.getElementById('scout-roles-count'),
  inputNewScoutRole: document.getElementById('input-new-scout-role'),
  btnAddScoutRole: document.getElementById('btn-add-scout-role'),
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
  
  // Resume Matrix
  resumeFileInput: document.getElementById('resume-file-input'),
  fileChosenLabel: document.getElementById('file-chosen-label'),
  fileDropBtnLabel: document.getElementById('file-drop-btn-label'),
  resumeRoleInput: document.getElementById('resume-role-input'),
  resumeIsDefault: document.getElementById('resume-is-default'),
  btnUploadResume: document.getElementById('btn-upload-resume'),
  resumeCountBadge: document.getElementById('resume-count-badge'),
  resumesTbody: document.getElementById('resumes-tbody'),
  roleChips: document.querySelectorAll('.chip-btn'),
  
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
  modalJobSalary: document.getElementById('modal-job-salary'),
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
            <span style="font-family: var(--font-mono); font-size: 11px;">${escapeHtml(j.platform)}</span>
            ${j.salary ? `
              <span>·</span>
              <span class="badge badge-salary tabular-nums" title="Compensation Package">
                💰 ${escapeHtml(j.salary)}
              </span>
            ` : ''}
          </div>
        </div>

        <div class="job-actions">
          <a href="${escapeHtml(j.apply_url || j.url)}" target="_blank" rel="noopener noreferrer" class="button button-secondary button-sm" title="Open official job post in new browser tab">
            Open ↗
          </a>
          <button class="button button-secondary button-sm btn-inspect" data-id="${j.id}">
            Details
          </button>
          <button class="button ${isApplied ? 'button-secondary' : 'button-primary'} button-sm btn-quick-apply" data-id="${j.id}" ${isApplied ? 'disabled' : ''} title="Run autonomous agent to pre-fill application & attach resume">
            ${isApplied ? '✓ Applied' : '⚡ Auto-Apply'}
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
    let targetLink = (job.apply_url || job.url || '').trim();
    if (targetLink && !targetLink.startsWith('http')) {
      targetLink = 'https://' + targetLink;
    }
    DOM.modalJobLink.href = targetLink || '#';
    DOM.modalJobLink.setAttribute('href', targetLink || '#');

    // Salary package display
    if (job.salary) {
      DOM.modalJobSalary.style.display = 'inline-flex';
      DOM.modalJobSalary.textContent = `💰 ${job.salary}`;
    } else {
      DOM.modalJobSalary.style.display = 'none';
    }

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
  const modeText = autoSubmit ? 'Auto-Submit' : 'Pre-fill (Review Mode)';
  showToast(`Initiating stealth browser agent (${modeText})...`, 'info');

  // Disable button to prevent duplicate triggers
  const applyBtns = document.querySelectorAll(`.btn-quick-apply[data-id="${jobId}"], #btn-apply-review, #btn-apply-submit`);
  applyBtns.forEach(b => {
    b.disabled = true;
    if (b.classList.contains('btn-quick-apply')) b.textContent = '⏳ Applying...';
  });

  try {
    const res = await fetch(`/api/jobs/${jobId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_submit: autoSubmit })
    });
    let result = {};
    try {
      result = await res.json();
    } catch (_) {
      result = {};
    }

    if (res.ok) {
      if (result.status === 'APPLIED') {
        showToast(`🎉 Application auto-submitted! Screenshot saved.`, 'success');
      } else {
        showToast(`📋 Form pre-filled & resume attached! Check your opened browser window to review and submit.`, 'success');
      }
      fetchJobs();
      fetchStats();
      if (state.activeJob && state.activeJob.id === jobId) {
        closeJobModal();
      }
    } else {
      showToast(result.error || `Application agent error (${res.status})`, 'error');
      fetchJobs();
      fetchStats();
    }
  } catch (err) {
    console.error('Application error:', err);
    showToast(`Failed to connect to application agent: ${err.message || 'Server unreachable'}`, 'error');
  } finally {
    applyBtns.forEach(b => {
      b.disabled = false;
      if (b.classList.contains('btn-quick-apply')) b.textContent = '⚡ Auto-Apply';
    });
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
  
  const currentRoles = (state.preferences && state.preferences.target_roles) ? state.preferences.target_roles : [];
  appendScoutLog(`[START] Multi-platform discovery sweep launched strictly for ${currentRoles.length} target keyword(s): [${currentRoles.join(', ')}]...`);
  showToast('Live discovery sweep launched...', 'info');

  try {
    const res = await fetch('/api/scout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        roles: currentRoles,
        max_age_hours: 24 
      })
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

function renderTargetRoles(roles) {
  const targetRoles = roles || (state.preferences ? state.preferences.target_roles : []) || [];
  if (DOM.scoutRolesCount) {
    DOM.scoutRolesCount.textContent = `${targetRoles.length} keyword${targetRoles.length === 1 ? '' : 's'}`;
  }
  if (!DOM.scoutRolesDisplay) return;

  if (targetRoles.length === 0) {
    DOM.scoutRolesDisplay.innerHTML = `<span class="input-hint" style="font-size: 11px;">No target keywords configured. Add one below to restrict discovery.</span>`;
    return;
  }

  DOM.scoutRolesDisplay.innerHTML = targetRoles.map(role => `
    <span class="keyword-chip" data-role="${escapeHtml(role)}">
      <span>${escapeHtml(role)}</span>
      <button type="button" class="chip-remove-btn" data-role="${escapeHtml(role)}" title="Remove keyword">×</button>
    </span>
  `).join('');

  DOM.scoutRolesDisplay.querySelectorAll('.chip-remove-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      const roleToRemove = btn.getAttribute('data-role');
      if (roleToRemove) {
        removeTargetRoleKeyword(roleToRemove);
      }
    });
  });
}

async function addTargetRoleKeyword(role) {
  const cleanRole = (role || '').trim();
  if (!cleanRole) {
    showToast('Please enter a role keyword first', 'warning');
    return;
  }

  try {
    const res = await fetch('/api/target-roles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role: cleanRole })
    });
    const data = await res.json();
    if (res.ok && data.success) {
      if (state.preferences) {
        state.preferences.target_roles = data.target_roles;
      }
      renderTargetRoles(data.target_roles);
      if (DOM.prefsRoles) {
        DOM.prefsRoles.value = data.target_roles.join('\n');
      }
      if (DOM.inputNewScoutRole) {
        DOM.inputNewScoutRole.value = '';
      }
      if (data.added) {
        showToast(`Target keyword "${cleanRole}" added!`, 'success');
        appendScoutLog(`[CONFIG] Added target keyword: "${cleanRole}". Discovery will filter strictly by this keyword.`);
      } else {
        showToast(`Keyword "${cleanRole}" already exists.`, 'info');
      }
    } else {
      showToast(data.error || 'Failed to add keyword', 'error');
    }
  } catch (err) {
    console.error('Error adding role:', err);
    showToast('Failed to add target keyword', 'error');
  }
}

async function removeTargetRoleKeyword(role) {
  try {
    const res = await fetch(`/api/target-roles/${encodeURIComponent(role)}`, {
      method: 'DELETE'
    });
    const data = await res.json();
    if (res.ok && data.success) {
      if (state.preferences) {
        state.preferences.target_roles = data.target_roles;
      }
      renderTargetRoles(data.target_roles);
      if (DOM.prefsRoles) {
        DOM.prefsRoles.value = data.target_roles.join('\n');
      }
      showToast(`Removed keyword "${role}"`, 'info');
      appendScoutLog(`[CONFIG] Removed target keyword: "${role}".`);
    } else {
      showToast(data.error || 'Failed to remove keyword', 'error');
    }
  } catch (err) {
    console.error('Error removing role:', err);
    showToast('Failed to remove keyword', 'error');
  }
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

    // Update scout view tags & keyword manager
    renderTargetRoles(prefs.target_roles);
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
// Resume Matrix & Role Mappings
// -----------------------------------------------------------------------------
async function fetchResumes() {
  try {
    const res = await fetch('/api/resumes');
    if (!res.ok) return;
    const data = await res.json();
    state.resumes = data.resumes || [];
    renderResumes(state.resumes);
  } catch (err) {
    console.error('Failed to load resumes:', err);
  }
}

function renderResumes(resumes) {
  if (DOM.resumeCountBadge) {
    DOM.resumeCountBadge.textContent = `${resumes.length} Resume${resumes.length === 1 ? '' : 's'} Active`;
  }
  if (!DOM.resumesTbody) return;

  if (resumes.length === 0) {
    DOM.resumesTbody.innerHTML = `
      <tr>
        <td colspan="5" style="text-align: center; color: var(--color-text-subtle); padding: 24px;">
          No role-tailored resumes mapped yet. Upload a resume above to route applications automatically.
        </td>
      </tr>
    `;
    return;
  }

  DOM.resumesTbody.innerHTML = resumes.map(r => {
    const defaultBadge = r.is_default
      ? `<span class="badge badge-success" title="Used when no specific role matches">★ Default</span>`
      : `<span style="color: var(--color-text-subtle); font-size: 12px;">—</span>`;
    const readyBadge = r.exists
      ? `<span class="badge badge-success" style="font-size: 10px;">READY</span>`
      : `<span class="badge" style="color: var(--color-danger); border-color: rgba(248,113,113,0.3); font-size: 10px;">MISSING</span>`;

    return `
      <tr>
        <td>
          <span class="badge" style="color: var(--color-text); border-color: var(--color-border-strong); font-weight: 500;">
            ${escapeHtml(r.role_pattern)}
          </span>
        </td>
        <td>
          <div style="display: flex; align-items: center; gap: 8px;">
            <span class="tabular-nums" style="font-size: 13px; color: var(--color-text);">${escapeHtml(r.file_name)}</span>
            ${readyBadge}
          </div>
        </td>
        <td class="tabular-nums" style="font-size: 12px; color: var(--color-text-muted);">
          ${r.file_size_kb ? r.file_size_kb.toFixed(1) + ' KB' : '—'}
        </td>
        <td>${defaultBadge}</td>
        <td style="text-align: right;">
          <div style="display: inline-flex; gap: 6px;">
            <a href="/api/resumes/${r.id}/download" target="_blank" class="button button-secondary" style="min-height: 28px; padding: 0 10px; font-size: 12px;" title="Preview / Download file">
              Preview
            </a>
            <button type="button" class="button button-secondary btn-delete-resume" data-id="${r.id}" style="min-height: 28px; padding: 0 10px; font-size: 12px; color: var(--color-danger);" title="Delete mapping">
              Delete
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function handleResumeUpload() {
  const file = DOM.resumeFileInput && DOM.resumeFileInput.files[0];
  const role = DOM.resumeRoleInput && DOM.resumeRoleInput.value.trim();
  const isDefault = DOM.resumeIsDefault && DOM.resumeIsDefault.checked;

  if (!file) {
    showToast('Please select a PDF or DOCX resume file to upload.', 'error');
    return;
  }
  if (!role) {
    showToast('Please specify the designated role (e.g. AI Engineer, SWE, FDE).', 'error');
    return;
  }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('role', role);
  formData.append('is_default', isDefault ? 'true' : 'false');

  DOM.btnUploadResume.disabled = true;
  DOM.btnUploadResume.textContent = 'Uploading...';

  try {
    const res = await fetch('/api/resumes/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(`Resume mapped to '${role}' successfully!`, 'success');
      DOM.resumeFileInput.value = '';
      DOM.resumeRoleInput.value = '';
      if (DOM.fileChosenLabel) DOM.fileChosenLabel.textContent = 'Choose PDF / DOCX';
      if (DOM.fileDropBtnLabel) DOM.fileDropBtnLabel.classList.remove('has-file');
      if (DOM.resumeIsDefault) DOM.resumeIsDefault.checked = false;
      await fetchResumes();
    } else {
      showToast(data.error || 'Failed to upload resume.', 'error');
    }
  } catch (err) {
    showToast('Error uploading resume: ' + err.message, 'error');
  } finally {
    DOM.btnUploadResume.disabled = false;
    DOM.btnUploadResume.textContent = 'Upload & Map';
  }
}

async function handleResumeDelete(resumeId) {
  if (!confirm('Are you sure you want to remove this resume mapping?')) return;
  try {
    const res = await fetch(`/api/resumes/${resumeId}`, { method: 'DELETE' });
    if (res.ok) {
      showToast('Resume mapping removed.', 'success');
      await fetchResumes();
    } else {
      showToast('Failed to delete resume mapping.', 'error');
    }
  } catch (err) {
    showToast('Error deleting resume: ' + err.message, 'error');
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

  // Target Role Keyword Events
  if (DOM.btnAddScoutRole && DOM.inputNewScoutRole) {
    DOM.btnAddScoutRole.addEventListener('click', () => {
      addTargetRoleKeyword(DOM.inputNewScoutRole.value);
    });
    DOM.inputNewScoutRole.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        addTargetRoleKeyword(DOM.inputNewScoutRole.value);
      }
    });
  }

  // Resume Matrix Events
  if (DOM.resumeFileInput) {
    DOM.resumeFileInput.addEventListener('change', () => {
      const file = DOM.resumeFileInput.files[0];
      if (file) {
        if (DOM.fileChosenLabel) DOM.fileChosenLabel.textContent = file.name;
        if (DOM.fileDropBtnLabel) DOM.fileDropBtnLabel.classList.add('has-file');
      } else {
        if (DOM.fileChosenLabel) DOM.fileChosenLabel.textContent = 'Choose PDF / DOCX';
        if (DOM.fileDropBtnLabel) DOM.fileDropBtnLabel.classList.remove('has-file');
      }
    });
  }

  if (DOM.roleChips) {
    DOM.roleChips.forEach(chip => {
      chip.addEventListener('click', () => {
        if (DOM.resumeRoleInput) DOM.resumeRoleInput.value = chip.dataset.chip;
      });
    });
  }

  if (DOM.btnUploadResume) {
    DOM.btnUploadResume.addEventListener('click', handleResumeUpload);
  }

  if (DOM.resumesTbody) {
    DOM.resumesTbody.addEventListener('click', (e) => {
      const delBtn = e.target.closest('.btn-delete-resume');
      if (delBtn && delBtn.dataset.id) {
        handleResumeDelete(delBtn.dataset.id);
      }
    });
  }

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
    fetchResumes(),
    fetchPlatforms(),
    fetchSystemInfo()
  ]);
  console.log('MCP Web Interface initialized.');
}

window.addEventListener('DOMContentLoaded', initApp);
