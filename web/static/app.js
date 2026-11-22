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
  btnBatchApplySubmit: document.getElementById('btn-batch-apply-submit'),
  btnBatchApplyReview: document.getElementById('btn-batch-apply-review'),
  batchApplyCount: document.getElementById('batch-apply-count'),
  batchProgressCard: document.getElementById('batch-progress-card'),
  batchProgressTitle: document.getElementById('batch-progress-title'),
  batchProgressStats: document.getElementById('batch-progress-stats'),
  batchProgressBar: document.getElementById('batch-progress-bar'),
  batchProgressDetail: document.getElementById('batch-progress-detail'),
  batchProgressCounts: document.getElementById('batch-progress-counts'),
  
  // Scout
  btnQuickScout: document.getElementById('btn-quick-scout'),
  btnRunScoutFull: document.getElementById('btn-run-scout-full'),
  scoutRolesDisplay: document.getElementById('scout-roles-display'),
  scoutRolesCount: document.getElementById('scout-roles-count'),
  inputNewScoutRole: document.getElementById('input-new-scout-role'),
  btnAddScoutRole: document.getElementById('btn-add-scout-role'),
  scoutThresholdDisplay: document.getElementById('scout-threshold-display'),
  scoutAutoapplyBadge: document.getElementById('scout-autoapply-badge'),
  scoutTargetPlatform: document.getElementById('scout-target-platform'),
  scoutPlatformBadge: document.getElementById('scout-platform-badge'),
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
  btnTailorResume: document.getElementById('btn-tailor-resume'),

  // Tailor Modal
  tailorModal: document.getElementById('tailor-modal'),
  btnCloseTailorModal: document.getElementById('btn-close-tailor-modal'),
  tailorModalTitle: document.getElementById('tailor-modal-title'),
  tailorModalSub: document.getElementById('tailor-modal-sub'),
  tailorAuditBadge: document.getElementById('tailor-audit-badge'),
  tailorMatchedSkills: document.getElementById('tailor-matched-skills'),
  tailorDomainFocus: document.getElementById('tailor-domain-focus'),
  tailorSummaryBox: document.getElementById('tailor-summary-box'),
  tailorSkillsList: document.getElementById('tailor-skills-list'),
  tailorExpList: document.getElementById('tailor-exp-list'),
  tailorCoverLetterBox: document.getElementById('tailor-cover-letter-box'),
  btnCopyAtsText: document.getElementById('btn-copy-ats-text'),
  btnCopyCoverLetter: document.getElementById('btn-copy-cover-letter'),
  btnDownloadTailoredPdf: document.getElementById('btn-download-tailored-pdf'),
  btnApplyWithTailored: document.getElementById('btn-apply-with-tailored'),
  
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
  const unapplied = (jobs || []).filter(j => j.status !== 'APPLIED');
  if (DOM.batchApplyCount) {
    DOM.batchApplyCount.textContent = unapplied.length;
  }
  if (DOM.btnBatchApplySubmit) {
    DOM.btnBatchApplySubmit.disabled = unapplied.length === 0;
  }
  if (DOM.btnBatchApplyReview) {
    DOM.btnBatchApplyReview.disabled = unapplied.length === 0;
  }

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
          <button class="button button-secondary button-sm btn-quick-tailor" data-id="${j.id}" title="Run Resume Tailor Agent for this specific job">
            📄 Tailor
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

  DOM.jobsList.querySelectorAll('.btn-quick-tailor').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      triggerTailorResume(btn.dataset.id);
    });
  });

  DOM.jobsList.querySelectorAll('.btn-quick-apply').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      triggerApply(btn.dataset.id, true);
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
// Apply & Evaluate Actions (with Live Progress Polling)
// -----------------------------------------------------------------------------
async function triggerApply(jobId, autoSubmit = true) {
  const modeText = autoSubmit ? 'Auto-Submit' : 'Pre-fill (Review Mode)';
  showToast(`Initiating stealth browser agent (${modeText})...`, 'info');

  const applyBtns = document.querySelectorAll(`.btn-quick-apply[data-id="${jobId}"], #btn-apply-review, #btn-apply-submit`);
  applyBtns.forEach(b => {
    b.disabled = true;
    if (b.classList.contains('btn-quick-apply')) b.textContent = '⏳ Starting...';
  });

  try {
    const res = await fetch(`/api/jobs/${jobId}/apply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ auto_submit: autoSubmit, async: true })
    });
    let initData = {};
    try {
      initData = await res.json();
    } catch (_) {
      initData = {};
    }

    if (!res.ok) {
      showToast(initData.error || `Application agent error (${res.status})`, 'error');
      applyBtns.forEach(b => {
        b.disabled = false;
        if (b.classList.contains('btn-quick-apply')) b.textContent = '⚡ Auto-Apply';
      });
      return;
    }

    // Live status polling loop
    let polls = 0;
    const maxPolls = 80; // ~2 minutes max
    const pollInterval = setInterval(async () => {
      polls++;
      try {
        const sRes = await fetch(`/api/jobs/${jobId}/apply-status`);
        if (!sRes.ok) return;
        const sData = await sRes.json();

        // Update button label with current stage
        if (sData.stage && sData.is_active) {
          applyBtns.forEach(b => {
            if (b.classList.contains('btn-quick-apply')) {
              b.textContent = `⏳ ${sData.stage.length > 20 ? sData.stage.slice(0, 18) + '...' : sData.stage}`;
            }
          });
        }

        // Check if finished
        const terminalStatuses = ['APPLIED', 'SUBMITTED', 'MANUAL_REVIEW', 'READY_FOR_REVIEW', 'FAILED', 'NEEDS_HUMAN'];
        const isDone = !sData.is_active || terminalStatuses.includes(sData.status) || polls >= maxPolls;

        if (isDone) {
          clearInterval(pollInterval);
          applyBtns.forEach(b => {
            b.disabled = false;
            if (b.classList.contains('btn-quick-apply')) {
              b.textContent = (sData.status === 'APPLIED' || sData.status === 'SUBMITTED') ? '✓ Applied' : '⚡ Auto-Apply';
            }
          });

          if (sData.status === 'APPLIED' || sData.status === 'SUBMITTED') {
            showToast(`🎉 Application auto-submitted! Proof screenshot captured.`, 'success');
          } else if (sData.status === 'MANUAL_REVIEW' || sData.status === 'READY_FOR_REVIEW' || sData.status === 'NEEDS_HUMAN') {
            if (sData.notes && (sData.notes.includes('pre-filled') || sData.notes.includes('fields filled'))) {
              showToast(`📋 Form pre-filled & resume attached! Review and submit in the opened browser tab.`, 'success');
            } else if (sData.notes && sData.notes.includes('CAPTCHA')) {
              showToast(`⚠️ CAPTCHA encountered. Please solve it in the opened browser window.`, 'warning');
            } else if (sData.notes && (sData.notes.includes('LinkedIn') || sData.notes.includes('login') || sData.notes.includes('sign-in'))) {
              showToast(`⚠️ ${sData.notes}`, 'warning');
            } else {
              showToast(`📋 ${sData.notes || 'Job opened in browser. Ready for inspection.'}`, 'info');
            }
          } else if (sData.status === 'FAILED') {
            showToast(sData.notes || 'Application attempt failed. Check opened browser tab to complete.', 'warning');
          } else {
            showToast(`Application finished with status: ${sData.status}`, 'info');
          }

          fetchJobs();
          fetchStats();
          if (state.activeJob && state.activeJob.id === jobId) {
            closeJobModal();
          }
        }
      } catch (pollErr) {
        console.warn('Status poll error:', pollErr);
      }
    }, 1500);

  } catch (err) {
    console.error('Application error:', err);
    showToast(`Failed to connect to application agent: ${err.message || 'Server unreachable'}`, 'error');
    applyBtns.forEach(b => {
      b.disabled = false;
      if (b.classList.contains('btn-quick-apply')) b.textContent = '⚡ Auto-Apply';
    });
  }
}

async function triggerBatchApply(autoSubmit = true) {
  const modeText = autoSubmit ? 'Auto-Submit' : 'Pre-fill (Review Mode)';
  const eligibleJobs = (state.jobs || []).filter(j => j.status !== 'APPLIED' && j.status !== 'SUBMITTED');
  if (eligibleJobs.length === 0) {
    showToast('No eligible unapplied jobs found matching current filters', 'warning');
    return;
  }

  const jobIds = eligibleJobs.map(j => j.id);
  const count = jobIds.length;

  showToast(`⚡ Autonomous Batch Apply initiated for ${count} jobs (${modeText})...`, 'info');

  if (DOM.batchProgressCard) {
    DOM.batchProgressCard.style.display = 'block';
    DOM.batchProgressTitle.textContent = `Applying to ${count} jobs simultaneously (${modeText})...`;
    DOM.batchProgressStats.textContent = `0 / ${count} Completed`;
    DOM.batchProgressBar.style.width = '10%';
    DOM.batchProgressDetail.textContent = `Spawning parallel stealth browser tabs and matching resumes...`;
    DOM.batchProgressCounts.textContent = `0 Applied | 0 Review | 0 Failed`;
  }

  if (DOM.btnBatchApplySubmit) {
    DOM.btnBatchApplySubmit.disabled = true;
    DOM.btnBatchApplySubmit.textContent = `⏳ Applying (${count})...`;
  }
  if (DOM.btnBatchApplyReview) DOM.btnBatchApplyReview.disabled = true;

  document.querySelectorAll('.btn-quick-apply').forEach(b => {
    b.disabled = true;
  });

  try {
    const res = await fetch('/api/jobs/batch-apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        job_ids: jobIds,
        auto_submit: autoSubmit,
        max_concurrency: 3,
        async: true
      })
    });

    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }

    if (!res.ok) {
      showToast(data.error || 'Batch application failed to start', 'error');
      if (DOM.batchProgressCard) DOM.batchProgressCard.style.display = 'none';
      return;
    }

    // Poll live batch progress
    const batchInterval = setInterval(async () => {
      try {
        const bRes = await fetch('/api/jobs/batch-status');
        if (!bRes.ok) return;
        const bState = await bRes.json();

        const total = bState.total || count;
        const completed = bState.completed || 0;
        const pct = total > 0 ? Math.min(100, Math.round((completed / total) * 100)) : 10;

        if (DOM.batchProgressBar) DOM.batchProgressBar.style.width = `${Math.max(10, pct)}%`;
        if (DOM.batchProgressStats) DOM.batchProgressStats.textContent = `${completed} / ${total} Completed`;
        if (DOM.batchProgressCounts) {
          DOM.batchProgressCounts.textContent = `${bState.applied || 0} Applied | ${bState.manual_review || 0} Review | ${bState.failed || 0} Failed`;
        }
        if (bState.current_job && DOM.batchProgressDetail) {
          DOM.batchProgressDetail.textContent = `Active: ${bState.current_job}`;
        }

        if (!bState.running && completed >= total) {
          clearInterval(batchInterval);
          if (DOM.batchProgressBar) DOM.batchProgressBar.style.width = '100%';
          if (DOM.batchProgressDetail) {
            DOM.batchProgressDetail.textContent = `Autonomous sweep finished! Proof screenshots captured.`;
          }

          showToast(`🎉 Batch complete: ${bState.applied || 0} applications submitted, ${bState.manual_review || 0} ready for review!`, 'success');
          fetchJobs();
          fetchStats();

          if (DOM.btnBatchApplySubmit) {
            DOM.btnBatchApplySubmit.disabled = false;
            DOM.btnBatchApplySubmit.innerHTML = `⚡ Auto-Apply Filtered (<span id="batch-apply-count">${DOM.batchApplyCount ? DOM.batchApplyCount.textContent : '0'}</span>)`;
          }
          if (DOM.btnBatchApplyReview) DOM.btnBatchApplyReview.disabled = false;

          setTimeout(() => {
            if (DOM.batchProgressCard) DOM.batchProgressCard.style.display = 'none';
          }, 6000);
        }
      } catch (bErr) {
        console.warn('Batch status poll error:', bErr);
      }
    }, 1500);

  } catch (err) {
    console.error('Batch apply error:', err);
    showToast(`Failed to connect to application agent: ${err.message || 'Server error'}`, 'error');
    if (DOM.batchProgressCard) DOM.batchProgressCard.style.display = 'none';
    if (DOM.btnBatchApplySubmit) {
      DOM.btnBatchApplySubmit.disabled = false;
      DOM.btnBatchApplySubmit.innerHTML = `⚡ Auto-Apply Filtered (<span id="batch-apply-count">${DOM.batchApplyCount ? DOM.batchApplyCount.textContent : '0'}</span>)`;
    }
    if (DOM.btnBatchApplyReview) DOM.btnBatchApplyReview.disabled = false;
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
// Resume Tailor Agent UI Functions
// -----------------------------------------------------------------------------
let activeTailoredArtifacts = null;
let activeTailoredJobId = null;

async function triggerTailorResume(jobId) {
  if (!jobId && state.activeJob) jobId = state.activeJob.id;
  if (!jobId) return;

  const job = (state.jobs || []).find(j => j.id === jobId) || state.activeJob;
  const roleTitle = job ? job.title : 'Target Role';
  const company = job ? job.company : 'Company';

  showToast(`📄 Resume Tailor Agent analyzing requirements for "${roleTitle}"...`, 'info');

  if (DOM.btnTailorResume) {
    DOM.btnTailorResume.disabled = true;
    DOM.btnTailorResume.textContent = '⏳ Tailoring...';
  }

  try {
    const res = await fetch(`/api/jobs/${jobId}/tailor`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ generate_pdf: true })
    });
    const data = await res.json();

    if (!res.ok || !data.success) {
      showToast(data.error || 'Failed to tailor resume', 'error');
      return;
    }

    const art = data.artifacts;
    openTailorModalWithData(art, jobId);
    showToast(`✅ Resume tailored & verified with 0 hallucinations!`, 'success');
    fetchJobs(); // Update job status in background if changed to TAILORED
  } catch (err) {
    console.error('Tailoring error:', err);
    showToast(`Tailor Agent error: ${err.message}`, 'error');
  } finally {
    if (DOM.btnTailorResume) {
      DOM.btnTailorResume.disabled = false;
      DOM.btnTailorResume.textContent = '📄 Tailor Resume';
    }
  }
}

function openTailorModalWithData(art, jobId) {
  activeTailoredArtifacts = art;
  activeTailoredJobId = jobId;

  if (DOM.tailorModalTitle) {
    DOM.tailorModalTitle.textContent = `Tailored Resume: ${art.role_title}`;
  }
  if (DOM.tailorModalSub) {
    DOM.tailorModalSub.textContent = `${art.company} · Generated specifically for this role`;
  }

  // Matched Skills & Focus
  const analysis = art.match_analysis || {};
  if (DOM.tailorMatchedSkills) {
    const matched = (analysis.matched_strong_skills || []).concat(analysis.matched_familiar_skills || []);
    DOM.tailorMatchedSkills.textContent = matched.length > 0 ? matched.join(', ') : 'Aligned with core experience';
  }
  if (DOM.tailorDomainFocus) {
    DOM.tailorDomainFocus.textContent = `${analysis.domain || 'Software Engineering'} · ${analysis.seniority || 'Mid'} Level`;
  }

  // Summary
  if (DOM.tailorSummaryBox) {
    DOM.tailorSummaryBox.textContent = art.summary || 'Summary generated.';
  }

  // Categorized Skills
  if (DOM.tailorSkillsList) {
    DOM.tailorSkillsList.innerHTML = '';
    const skills = art.ordered_skills || {};
    for (const [cat, items] of Object.entries(skills)) {
      const line = document.createElement('div');
      line.innerHTML = `<span style="font-weight: 600; color: var(--color-text);">${escapeHtml(cat)}:</span> <span style="color: var(--color-text-subtle);">${escapeHtml(items.join(', '))}</span>`;
      DOM.tailorSkillsList.appendChild(line);
    }
  }

  // Experience Bullets
  if (DOM.tailorExpList) {
    DOM.tailorExpList.innerHTML = '';
    const exps = art.tailored_experience || [];
    exps.forEach(exp => {
      const item = document.createElement('div');
      item.style.padding = '8px 12px';
      item.style.background = 'var(--color-surface-inset)';
      item.style.borderRadius = 'var(--radius-sm)';
      const bulletsHtml = (exp.bullets || []).map(b => `<li style="margin-bottom: 2px;">${escapeHtml(b)}</li>`).join('');
      item.innerHTML = `
        <div style="display: flex; justify-content: space-between; font-weight: 600; color: var(--color-text);">
          <span>${escapeHtml(exp.title)} — ${escapeHtml(exp.company)}</span>
          <span style="font-size: 11px; color: var(--color-text-subtle);">${escapeHtml(exp.dates || '')}</span>
        </div>
        <ul style="margin: 4px 0 0 16px; padding: 0; color: var(--color-text-subtle);">
          ${bulletsHtml}
        </ul>
      `;
      DOM.tailorExpList.appendChild(item);
    });
  }

  // Cover Letter
  if (DOM.tailorCoverLetterBox) {
    DOM.tailorCoverLetterBox.textContent = art.cover_letter || 'Cover letter generated.';
  }

  // PDF Download Button
  if (DOM.btnDownloadTailoredPdf) {
    if (art.pdf_filename) {
      DOM.btnDownloadTailoredPdf.style.display = 'inline-flex';
      DOM.btnDownloadTailoredPdf.href = `/api/artifacts/${art.pdf_filename}`;
      DOM.btnDownloadTailoredPdf.download = art.pdf_filename;
    } else {
      DOM.btnDownloadTailoredPdf.style.display = 'none';
    }
  }

  if (DOM.tailorModal) {
    DOM.tailorModal.classList.add('open');
  }
}

function closeTailorModal() {
  if (DOM.tailorModal) {
    DOM.tailorModal.classList.remove('open');
  }
  activeTailoredArtifacts = null;
  activeTailoredJobId = null;
}

// -----------------------------------------------------------------------------
// Live Discovery Scout
// -----------------------------------------------------------------------------
function getPlatformDisplayName(key) {
  if (!key || typeof key !== 'string' || key.toLowerCase() === 'all' || key.toLowerCase() === 'all platforms') {
    return 'All Platforms';
  }
  if (DOM.filterPlatform) {
    try {
      const opt = DOM.filterPlatform.querySelector(`option[value="${key}"]`);
      if (opt) {
        const txt = opt.textContent.split('(')[0].trim();
        return txt.length > 0 ? txt : opt.textContent.trim();
      }
    } catch (_) {}
  }
  return key.charAt(0).toUpperCase() + key.slice(1);
}

function updateScoutButtonLabel() {
  const currentPlatform = state.filters.platform || (DOM.scoutTargetPlatform ? DOM.scoutTargetPlatform.value : '');
  const disp = getPlatformDisplayName(currentPlatform);

  if (DOM.btnQuickScout) {
    const lbl = DOM.btnQuickScout.querySelector('span:last-child');
    if (lbl) {
      lbl.textContent = currentPlatform ? `Run Discovery Sweep (${disp})` : 'Run Discovery Sweep';
    }
  }

  if (DOM.btnRunScoutFull) {
    const lbl = DOM.btnRunScoutFull.querySelector('span');
    if (lbl) {
      lbl.textContent = currentPlatform ? `Trigger Live Sweep (${disp})` : 'Trigger Live Sweep';
    }
  }

  if (DOM.scoutPlatformBadge) {
    DOM.scoutPlatformBadge.textContent = currentPlatform ? disp.toUpperCase() : 'ALL PLATFORMS';
    DOM.scoutPlatformBadge.className = `badge ${currentPlatform ? 'badge-success' : ''}`;
  }
}

async function triggerLiveScout(explicitPlatform = null) {
  if (DOM.btnQuickScout) DOM.btnQuickScout.disabled = true;
  if (DOM.btnRunScoutFull) DOM.btnRunScoutFull.disabled = true;

  // Resolve targeted platform: explicit parameter, state filter, or scout view dropdown
  let selectedPlatform = (typeof explicitPlatform === 'string' && explicitPlatform.trim()) ? explicitPlatform.trim() : null;
  if (!selectedPlatform) {
    const filterVal = (DOM.filterPlatform && DOM.filterPlatform.value) ? DOM.filterPlatform.value.trim() : '';
    const scoutVal = (DOM.scoutTargetPlatform && DOM.scoutTargetPlatform.value) ? DOM.scoutTargetPlatform.value.trim() : '';
    const stateVal = (typeof state.filters.platform === 'string') ? state.filters.platform.trim() : '';
    selectedPlatform = filterVal || scoutVal || stateVal || null;
  }
  if (selectedPlatform && (selectedPlatform.toLowerCase() === 'all' || selectedPlatform.toLowerCase() === 'all platforms')) {
    selectedPlatform = null;
  }

  const platformName = selectedPlatform ? getPlatformDisplayName(selectedPlatform) : 'All Platforms';

  if (DOM.btnQuickScout) {
    const lbl = DOM.btnQuickScout.querySelector('span:last-child');
    if (lbl) lbl.textContent = selectedPlatform ? `Scouting ${platformName}...` : 'Scouting...';
  }
  if (DOM.btnRunScoutFull) {
    const lbl = DOM.btnRunScoutFull.querySelector('span');
    if (lbl) lbl.textContent = selectedPlatform ? `Scouting ${platformName}...` : 'Scouting...';
  }

  const currentRoles = (state.preferences && state.preferences.target_roles) ? state.preferences.target_roles : [];
  const logPrefix = selectedPlatform ? `[TARGETED: ${platformName.toUpperCase()}]` : '[MULTI-PLATFORM]';
  appendScoutLog(`${logPrefix} Discovery sweep launched for ${currentRoles.length} target keyword(s)...`);
  showToast(`🔍 Discovering recent related jobs on ${platformName}...`, 'info');

  try {
    const payload = {
      roles: currentRoles,
      max_age_hours: 24
    };
    if (selectedPlatform) {
      payload.platform = selectedPlatform;
    }

    const res = await fetch('/api/scout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    let data = {};
    try {
      data = await res.json();
    } catch (_) {
      data = {};
    }

    if (res.ok && data.success) {
      const s = data.summary || {};
      const newJobs = s.new_unique_jobs ?? 0;
      const totalFetched = s.total_fetched ?? 0;
      const qualified = s.qualified_matches ?? 0;
      const thresh = s.threshold ?? 70;

      appendScoutLog(`[COMPLETE] Discovered ${newJobs} new unique jobs from ${totalFetched} listings parsed on ${platformName}.`);
      appendScoutLog(`[MATCHES] ${qualified} qualified listings matched profile threshold (≥${thresh}%).`);

      showToast(`🎉 Sweep complete for ${platformName}: ${newJobs} new jobs discovered! Displaying all recent related jobs.`, 'success');

      // If a specific platform was swept, lock filter to that platform and display results
      if (selectedPlatform) {
        state.filters.platform = selectedPlatform;
        if (DOM.filterPlatform) DOM.filterPlatform.value = selectedPlatform;
        if (DOM.scoutTargetPlatform) DOM.scoutTargetPlatform.value = selectedPlatform;
      }
      updateScoutButtonLabel();
      switchView('jobs');

      await fetchStats();
      await fetchJobs();
    } else {
      const errMsg = (data && data.error) ? data.error : 'Discovery sweep encountered issues';
      appendScoutLog(`[ERROR] Discovery sweep failed on ${platformName}: ${errMsg}`);
      showToast(`Scout sweep failed: ${errMsg}`, 'error');
    }
  } catch (err) {
    appendScoutLog(`[ERROR] Connection failed: ${err.message}`);
    showToast(`Failed to trigger scout: ${err.message}`, 'error');
  } finally {
    if (DOM.btnQuickScout) DOM.btnQuickScout.disabled = false;
    if (DOM.btnRunScoutFull) DOM.btnRunScoutFull.disabled = false;
    updateScoutButtonLabel();
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
    updatePlatformDropdowns(state.platforms);
  } catch (err) {
    console.error('Failed to load platforms:', err);
  }
}

function updatePlatformDropdowns(platforms) {
  if (DOM.scoutTargetPlatform) {
    const curVal = DOM.scoutTargetPlatform.value;
    const optionsHtml = `<option value="">All Enabled Platforms (30+)</option>` +
      platforms.map(p => `<option value="${escapeHtml(p.name)}">${escapeHtml(p.display_name)}</option>`).join('');
    DOM.scoutTargetPlatform.innerHTML = optionsHtml;
    if (curVal) DOM.scoutTargetPlatform.value = curVal;
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
      <div style="display: flex; align-items: center; gap: 8px;">
        <span class="badge ${p.enabled ? 'badge-success' : ''}">${p.enabled ? 'ACTIVE' : 'OFFLINE'}</span>
        <button class="button button-secondary button-sm btn-sweep-provider" data-platform="${escapeHtml(p.name)}" style="padding: 2px 8px; font-size: 11px;" title="Trigger discovery sweep for ${escapeHtml(p.display_name)}">
          ▶ Sweep
        </button>
      </div>
    </div>
  `).join('');

  DOM.scoutProviderList.querySelectorAll('.btn-sweep-provider').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerLiveScout(btn.dataset.platform);
    });
  });
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
    if (DOM.scoutTargetPlatform) DOM.scoutTargetPlatform.value = DOM.filterPlatform.value;
    updateScoutButtonLabel();
    fetchJobs();
  });

  if (DOM.scoutTargetPlatform) {
    DOM.scoutTargetPlatform.addEventListener('change', () => {
      state.filters.platform = DOM.scoutTargetPlatform.value;
      if (DOM.filterPlatform) DOM.filterPlatform.value = DOM.scoutTargetPlatform.value;
      updateScoutButtonLabel();
    });
  }

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
    if (DOM.scoutTargetPlatform) DOM.scoutTargetPlatform.value = '';
    DOM.filterScore.value = '';
    DOM.filterStatus.value = '';
    state.filters = { search: '', platform: '', score: '', status: '' };
    updateScoutButtonLabel();
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
  if (DOM.btnQuickScout) {
    DOM.btnQuickScout.addEventListener('click', () => triggerLiveScout());
  }
  if (DOM.btnRunScoutFull) {
    DOM.btnRunScoutFull.addEventListener('click', () => triggerLiveScout());
  }

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

  // Batch Application Master Triggers
  if (DOM.btnBatchApplySubmit) {
    DOM.btnBatchApplySubmit.addEventListener('click', () => triggerBatchApply(true));
  }
  if (DOM.btnBatchApplyReview) {
    DOM.btnBatchApplyReview.addEventListener('click', () => triggerBatchApply(false));
  }

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
  if (DOM.btnTailorResume) {
    DOM.btnTailorResume.addEventListener('click', () => {
      if (state.activeJob) triggerTailorResume(state.activeJob.id);
    });
  }

  // Tailor Modal Actions
  if (DOM.btnCloseTailorModal) {
    DOM.btnCloseTailorModal.addEventListener('click', closeTailorModal);
  }
  if (DOM.tailorModal) {
    DOM.tailorModal.addEventListener('click', (e) => {
      if (e.target === DOM.tailorModal) closeTailorModal();
    });
  }
  if (DOM.btnCopyAtsText) {
    DOM.btnCopyAtsText.addEventListener('click', () => {
      if (activeTailoredArtifacts && activeTailoredArtifacts.ats_text) {
        navigator.clipboard.writeText(activeTailoredArtifacts.ats_text);
        showToast('📋 ATS Resume Plain Text copied to clipboard!', 'success');
      }
    });
  }
  if (DOM.btnCopyCoverLetter) {
    DOM.btnCopyCoverLetter.addEventListener('click', () => {
      if (activeTailoredArtifacts && activeTailoredArtifacts.cover_letter) {
        navigator.clipboard.writeText(activeTailoredArtifacts.cover_letter);
        showToast('✉️ Tailored Cover Letter copied to clipboard!', 'success');
      }
    });
  }
  if (DOM.btnApplyWithTailored) {
    DOM.btnApplyWithTailored.addEventListener('click', () => {
      if (activeTailoredJobId) {
        closeTailorModal();
        closeJobModal();
        triggerApply(activeTailoredJobId, true);
      }
    });
  }

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
      closeTailorModal();
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
