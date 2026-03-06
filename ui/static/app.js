(function () {
  const metaEl = document.getElementById("meta");
  const repoNameEl = document.getElementById("repo-name");
  const repoPrivateBadgeEl = document.getElementById("repo-private-badge");
  const repoSelectEl = document.getElementById("repo-select");
  const addRepoBtnEl = document.getElementById("add-repo-btn");
  const aiSettingsBtnEl = document.getElementById("ai-settings-btn");
  const repoListModePillEl = document.getElementById("repo-list-mode-pill");
  const treeStatusEl = document.getElementById("tree-status");
  const treeEl = document.getElementById("tree");
  const fileViewEl = document.getElementById("file-view");
  const symbolViewEl = document.getElementById("symbol-view");
  const searchInputEl = document.getElementById("symbol-search-input");
  const searchResultsEl = document.getElementById("symbol-search-results");
  const tabDetailsEl = document.getElementById("tab-details");
  const tabImpactEl = document.getElementById("tab-impact");
  const tabGraphEl = document.getElementById("tab-graph");
  const tabArchitectureEl = document.getElementById("tab-architecture");
  const graphControlsEl = document.getElementById("graph-controls");
  const impactControlsEl = document.getElementById("impact-controls");
  const impactDepthEl = document.getElementById("impact-depth");
  const impactMaxNodesEl = document.getElementById("impact-max-nodes");
  const impactViewEl = document.getElementById("impact-view");
  const graphViewEl = document.getElementById("graph-view");
  const architectureViewEl = document.getElementById("architecture-view");
  const graphModeEl = document.getElementById("graph-mode");
  const graphDepthEl = document.getElementById("graph-depth");
  const graphHideBuiltinsEl = document.getElementById("graph-hide-builtins");
  const graphHideExternalEl = document.getElementById("graph-hide-external");
  const graphSearchEl = document.getElementById("graph-search");
  const recentSymbolsEl = document.getElementById("recent-symbols");
  const recentFilesEl = document.getElementById("recent-files");
  const recentSymbolsWrapEl = document.getElementById("recent-symbols-wrap");
  const recentFilesWrapEl = document.getElementById("recent-files-wrap");
  const repoListContentEl = document.getElementById("repo-list-content");
  const addRepoInlineEl = document.getElementById("add-repo-inline");
  const repoInlineCloseEl = document.getElementById("repo-inline-close");
  const repoTabLocalEl = document.getElementById("repo-tab-local");
  const repoTabGithubEl = document.getElementById("repo-tab-github");
  const repoFormLocalEl = document.getElementById("repo-form-local");
  const repoFormGithubEl = document.getElementById("repo-form-github");
  const localRepoPathEl = document.getElementById("local-repo-path");
  const localDisplayNameEl = document.getElementById("local-display-name");
  const ghRepoUrlEl = document.getElementById("gh-repo-url");
  const ghRefEl = document.getElementById("gh-ref");
  const ghModeEl = document.getElementById("gh-mode");
  const ghTokenEl = document.getElementById("gh-token");
  const ghPrivateModeEl = document.getElementById("gh-private-mode");
  const privateModeIndicatorEl = document.getElementById("private-mode-indicator");
  const repoModalErrorEl = document.getElementById("repo-modal-error");
  const repoAddBtnEl = document.getElementById("repo-add-btn");
  const repoCancelBtnEl = document.getElementById("repo-cancel-btn");
  const toastEl = document.getElementById("toast");
  const privacySummaryEl = document.getElementById("privacy-summary");
  const privacyRepoListModeEl = document.getElementById("privacy-repo-list-mode");
  const privacyExpiringEl = document.getElementById("privacy-expiring");
  const privacyPrivateBannerEl = document.getElementById("privacy-private-banner");
  const privacyResultEl = document.getElementById("privacy-result");
  const privacyConfirmEl = document.getElementById("privacy-confirm");
  const repoRetentionSelectEl = document.getElementById("repo-retention-select");
  const repoRetentionSaveBtnEl = document.getElementById("repo-retention-save-btn");
  const cleanupDryBtnEl = document.getElementById("cleanup-dry-btn");
  const cleanupNowBtnEl = document.getElementById("cleanup-now-btn");
  const deleteRepoCacheBtnEl = document.getElementById("delete-repo-cache-btn");
  const deleteAllCachesBtnEl = document.getElementById("delete-all-caches-btn");
  const autoCleanOnRemoveEl = document.getElementById("auto-clean-on-remove");
  const autoCleanNoteEl = document.getElementById("auto-clean-note");
  const confirmModalEl = document.getElementById("confirm-modal");
  const confirmTitleEl = document.getElementById("confirm-title");
  const confirmMessageEl = document.getElementById("confirm-message");
  const confirmYesEl = document.getElementById("confirm-yes");
  const confirmNoEl = document.getElementById("confirm-no");
  const aiSettingsModalEl = document.getElementById("ai-settings-modal");
  const aiSettingsKeyEl = null;
  const aiSettingsRememberReposEl = document.getElementById("ai-settings-remember-repos");
  const aiSettingsClearReposEl = document.getElementById("ai-settings-clear-repos");
  const aiSettingsCancelEl = document.getElementById("ai-settings-cancel");
  const aiSettingsStatusEl = document.getElementById("ai-settings-status");

  const fileCache = new Map();
  const symbolCache = new Map();
  const symbolAiSummaryCache = new Map();
  let repoDir = "";
  let repoName = "";
  let activeSymbolFqn = "";
  let activeFilePath = "";
  let searchTimer = null;
  let currentSearchResults = [];
  let workspaceRepos = [];
  let activeRepoHash = "";
  let recentSymbols = [];
  let recentFiles = [];
  let lastSymbol = "";
  let activeTab = "details";
  let graphDataCache = new Map();
  let impactDataCache = new Map();
  let architectureCache = null;
  let repoSummary = null;
  let repoSummaryUpdatedAt = "";
  let repoSummaryStatus = "idle"; // idle|loading|ready|missing|error
  let repoSummaryError = "";
  let aiEnabled = false;
  let aiProvider = "";
  let aiModel = "";
  let aiStatusMessage = "AI is optional. Configure a provider and key to enable summaries and explanations.";
  let riskRadar = null;
  let riskRadarUpdatedAt = "";
  let riskRadarStatus = "idle"; // idle|loading|ready|missing|error
  let riskRadarError = "";
  let dataPrivacyCache = null;
  let repoRegistry = [];
  let rememberRepos = false;
  let autoCleanOnRemove = false;

  function withRepo(path) {
    return new URL(path, window.location.origin).toString();
  }

  async function fetchJson(path, options) {
    const res = await fetch(withRepo(path), options);
    const data = await res.json();
    if (!res.ok || data.ok === false) throw data;
    return data;
  }

  function esc(v) {
    return String(v ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;",
    })[ch]);
  }

  function redactSecrets(v) {
    let value = String(v || "");
    value = value.replace(/\bgh[pousr]_[A-Za-z0-9_]{8,}\b/g, (m) => `${m.slice(0, 4)}************`);
    value = value.replace(/\bBearer\s+[^\s]+/gi, "Bearer ********");
    value = value.replace(/\bBasic\s+[^\s]+/gi, "Basic ********");
    value = value.replace(/(https?:\/\/)([^/\s:@]+):([^@\s/]+)@/gi, "$1***:***@");
    value = value.replace(/\b(token|api[_-]?key|password)\s*[:=]\s*[^\s'"`]+/gi, "$1=[REDACTED]");
    return value;
  }

  function formatBytes(v) {
    const n = Number(v || 0);
    if (!Number.isFinite(n) || n <= 0) return "0 B";
    if (n < 1024) return `${Math.round(n)} B`;
    if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
    if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
    return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
  }

  function stripMarkdown(text) {
    return String(text || "")
      .replace(/```/g, "")
      .replace(/[*#`]/g, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function _summaryFromMarkdown(content) {
    const lines = String(content || "").split("\n").map((x) => x.trim()).filter(Boolean);
    const oneLiner = lines.length ? lines[0].replace(/^\-\s*/, "") : "";
    const bullets = lines.slice(1, 8).map((x) => x.replace(/^\-\s*/, "")).filter(Boolean);
    return {
      one_liner: oneLiner,
      bullets,
      notes: [],
    };
  }

  function relPath(p) {
    const path = String(p || "").replace(/\\/g, "/");
    const root = String(repoDir || "").replace(/\\/g, "/");
    if (root && path.toLowerCase().startsWith(root.toLowerCase() + "/")) {
      return path.slice(root.length + 1);
    }
    return path;
  }

  function normalizeTree(raw) {
    if (!raw) return null;
    if (raw.tree) return raw.tree;
    if (raw.name && raw.type) return raw;
    if (Array.isArray(raw)) return { name: "repo", type: "directory", path: "", children: raw };
    if (raw.root) return raw.root;
    return { name: "repo", type: "directory", path: "", children: [] };
  }

  function parseSymbolParts(fqn) {
    const parts = String(fqn || "").split(".");
    const symbol = parts[parts.length - 1] || "";
    const prev = parts[parts.length - 2] || "";
    const className = prev && prev[0] === prev[0].toUpperCase() ? prev : "";
    const display = className ? `${className}.${symbol}` : symbol;
    return { className, symbol, display };
  }

  function currentRepoEntry() {
    return (repoRegistry || []).find((r) => String(r.repo_hash) === String(activeRepoHash)) || null;
  }

  function selectedRepoEntry() {
    const fromWorkspace = (workspaceRepos || []).find((r) => String(r.repo_hash) === String(activeRepoHash));
    if (fromWorkspace) return fromWorkspace;
    return currentRepoEntry();
  }

  function syncRepoHeader(fallbackName) {
    const entry = selectedRepoEntry();
    const displayName = String((entry && entry.name) || fallbackName || "").trim();
    repoName = displayName;
    if (repoNameEl) {
      repoNameEl.textContent = displayName || "No repo selected";
    }
    if (repoPrivateBadgeEl) {
      const privateMode = !!(entry && entry.private_mode);
      repoPrivateBadgeEl.classList.toggle("hidden", !privateMode);
    }
  }

  function analyzeCommandForRepo(repo) {
    const r = repo || currentRepoEntry();
    if (!r) return "python cli.py api analyze --path <repo>";
    if (String(r.source || "filesystem") === "github" && r.repo_url) {
      const ref = r.ref || "main";
      const mode = r.mode || "zip";
      return `python cli.py api analyze --github ${r.repo_url} --ref ${ref} --mode ${mode}`;
    }
    return `python cli.py api analyze --path ${r.repo_path || "<repo>"}`;
  }

  function updateAiModeUi() {
  }

  function updateRepoListModeUi() {
    const label = rememberRepos ? "Remembering Repos" : "Session Mode";
    if (repoListModePillEl) repoListModePillEl.textContent = label;
    if (privacyRepoListModeEl) {
      privacyRepoListModeEl.textContent = rememberRepos
        ? "Repository list: Remembered on this machine"
        : "Repository list: Session-only";
    }
  }

  async function loadAiStatus() {
    aiEnabled = false;
    aiProvider = "";
    aiModel = "";
    aiStatusMessage = "CodeMap runs fully without AI. Deterministic summaries are always available.";
    updateAiModeUi();
  }

  async function loadRegistryMode() {
    try {
      const data = await fetchJson("/api/registry");
      rememberRepos = !!data.remember_repos;
    } catch (_e) {
      rememberRepos = false;
    }
    updateRepoListModeUi();
    if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = !!rememberRepos;
  }


  function setAiSettingsStatus(message, isError) {
    if (!aiSettingsStatusEl) return;
    aiSettingsStatusEl.textContent = redactSecrets(String(message || ""));
    aiSettingsStatusEl.classList.toggle("error", !!isError);
  }

  function closeAiSettingsModal() {
    if (!aiSettingsModalEl) return;
    aiSettingsModalEl.classList.add("hidden");
    if (aiSettingsKeyEl) aiSettingsKeyEl.value = "";
    setAiSettingsStatus("", false);
    document.body.classList.remove("modal-open");
  }

  async function openAiSettingsModal() {
    if (!aiSettingsModalEl) return;
    aiSettingsModalEl.classList.remove("hidden");
    document.body.classList.add("modal-open");
    if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = !!rememberRepos;
    if (aiSettingsKeyEl) aiSettingsKeyEl.value = "";
    setAiSettingsStatus("Loading settings...", false);
    try {
      await loadRegistryMode();
      if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = !!rememberRepos;
      setAiSettingsStatus("CodeMap runs fully without AI. Deterministic summaries are always available.", false);
    } catch (e) {
      setAiSettingsStatus(redactSecrets((e && (e.message || e.error)) || "Failed to load settings."), true);
    }
  }




  async function setRememberRepos(value) {
    const remember = !!value;
    try {
      await fetchJson("/api/registry/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ remember_repos: remember }),
      });
      rememberRepos = remember;
      updateRepoListModeUi();
      if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = remember;
      if (!remember) {
        workspaceRepos = [];
        repoRegistry = [];
        activeRepoHash = "";
        renderWorkspaceSelect();
        renderRepoRegistry();
        clearWorkspaceView("No repositories added yet. Add a local path or GitHub repo to begin.");
        await loadDataPrivacy();
        showToast("Session Mode enabled. Repo list will reset when you close.", "success");
      } else {
        await loadWorkspace();
        await refreshForActiveRepo();
      }
    } catch (e) {
      showToast(redactSecrets((e && (e.message || e.error)) || "Failed to update registry mode"), "error");
      if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = !!rememberRepos;
    }
  }

  async function clearRepositoryList() {
    const sessionOnly = !rememberRepos;
    await openConfirmModal({
      title: "Clear repository list",
      message: sessionOnly
        ? "This will clear the in-memory session repo list only."
        : "This will clear remembered repositories. Cache files are not deleted.",
      confirmText: "Yes",
      cancelText: "Cancel",
      actionType: "clear_repo_list",
      payload: { session_only: sessionOnly },
      onConfirm: async () => {
        await fetchJson("/api/registry/repos/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_only: sessionOnly }),
        });
        workspaceRepos = [];
        repoRegistry = [];
        activeRepoHash = "";
        renderWorkspaceSelect();
        renderRepoRegistry();
        clearWorkspaceView("No repositories added yet. Add a local path or GitHub repo to begin.");
        await loadDataPrivacy();
        showToast("Repository list cleared", "success");
      },
    });
  }

  function analysisErrorMessage(errPayload) {
    const payload = (errPayload && errPayload.analyze_result) ? errPayload.analyze_result : (errPayload || {});
    const code = String(payload.error || (errPayload && errPayload.error) || "");
    if (code === "GITHUB_AUTH_REQUIRED") {
      return "Private repo detected. Please provide a GitHub token and run analysis again.";
    }
    return redactSecrets(String(payload.message || payload.error || (errPayload && errPayload.message) || (errPayload && errPayload.error) || "Analyze failed"));
  }

  function renderMissingAnalysisCta(msg) {
    const repo = currentRepoEntry();
    const cmd = analyzeCommandForRepo();
    const isGithub = String((repo && repo.source) || "filesystem") === "github";
    return `
      <div class="missing-analysis-cta">
        <div class="symbol-name">Analysis not found</div>
        <div>No analysis data found for this repo. Click "Run Analysis Now" or run:</div>
        <div class="impact-command analysis-cli-command">${esc(cmd)}</div>
        ${isGithub ? `
          <label class="path">GitHub token (optional for private repos)
            <input class="missing-analysis-token" type="password" placeholder="Used for this run only" />
          </label>
        ` : ""}
        <div class="repo-row-actions">
          <button class="repo-btn small run-analysis-now-btn" type="button">Run Analysis Now</button>
          <button class="repo-btn small copy-analysis-cli-btn" type="button">Copy CLI command</button>
        </div>
        <div class="analysis-run-status path hidden"></div>
        <div class="analysis-run-error hidden"></div>
        <div class="path">${esc(msg || "After it finishes, refresh this page.")}</div>
      </div>
    `;
  }

  function clearWorkspaceView(message) {
    fileCache.clear();
    symbolCache.clear();
    symbolAiSummaryCache.clear();
    activeFilePath = "";
    activeSymbolFqn = "";
    closeSearchDropdown();
    treeEl.innerHTML = "";
    treeStatusEl.textContent = "";
    fileViewEl.classList.add("muted");
    symbolViewEl.classList.add("muted");
    impactViewEl.classList.add("muted");
    graphViewEl.classList.add("muted");
    architectureViewEl.classList.add("muted");
    fileViewEl.textContent = message || "Select a file from the tree.";
    symbolViewEl.textContent = "Select a symbol to view summary and usages.";
    impactViewEl.textContent = "Select a symbol to view impact.";
    graphViewEl.textContent = "Select a symbol to view graph.";
    architectureViewEl.textContent = "Select a repository to view architecture insights.";
    recentSymbols = [];
    recentFiles = [];
    lastSymbol = "";
    architectureCache = null;
    repoSummary = null;
    repoSummaryUpdatedAt = "";
    repoSummaryStatus = "idle";
    repoSummaryError = "";
    riskRadar = null;
    riskRadarUpdatedAt = "";
    riskRadarStatus = "idle";
    riskRadarError = "";
    renderRecents();
  }

  function setMissingAnalysisCtaState(state) {
    const loading = !!(state && state.loading);
    const status = String((state && state.status) || "").trim();
    const error = String((state && state.error) || "").trim();

    document.querySelectorAll(".run-analysis-now-btn").forEach((btn) => {
      btn.disabled = loading;
      btn.classList.toggle("is-loading", loading);
      btn.textContent = loading ? "Analyzing..." : "Run Analysis Now";
    });
    document.querySelectorAll(".copy-analysis-cli-btn").forEach((btn) => {
      btn.disabled = loading;
    });
    document.querySelectorAll(".analysis-run-status").forEach((el) => {
      el.textContent = status;
      el.classList.toggle("hidden", !status);
    });
    document.querySelectorAll(".analysis-run-error").forEach((el) => {
      el.textContent = error;
      el.classList.toggle("hidden", !error);
    });
  }

  function bindRunAnalysisNowButton() {
    document.querySelectorAll(".run-analysis-now-btn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", async () => {
        if (!activeRepoHash) return;
        const container = btn.closest(".missing-analysis-cta");
        const tokenInput = container ? container.querySelector(".missing-analysis-token") : null;
        const token = tokenInput ? String(tokenInput.value || "").trim() : "";
        setMissingAnalysisCtaState({ loading: true, status: "Analyzing..." });
        const activeRepo = currentRepoEntry();
        const result = await analyzeRepoByHash(activeRepoHash, {
          token,
          showErrors: false,
          privateModeHint: !!(activeRepo && activeRepo.private_mode),
        });
        if (tokenInput) tokenInput.value = "";
        if (ghTokenEl) ghTokenEl.value = "";
        updatePrivateModeIndicator();
        if (!result || !result.ok) {
          const err = analysisErrorMessage(result ? result.error : {});
          setMissingAnalysisCtaState({ loading: false, status: "", error: err });
          showToast(err, "error");
          return;
        }
        showToast("Analysis completed.", "success");
        setMissingAnalysisCtaState({ loading: false, status: "", error: "" });
      });
    });

    document.querySelectorAll(".copy-analysis-cli-btn").forEach((btn) => {
      if (btn.dataset.bound === "1") return;
      btn.dataset.bound = "1";
      btn.addEventListener("click", async () => {
        const container = btn.closest(".missing-analysis-cta");
        const cmdEl = container ? container.querySelector(".analysis-cli-command") : null;
        const command = String((cmdEl && cmdEl.textContent) || analyzeCommandForRepo()).trim();
        if (!command) return;
        try {
          await navigator.clipboard.writeText(command);
          showToast("CLI command copied.", "success");
        } catch (_e) {
          showToast("Failed to copy command.", "error");
        }
      });
    });
  }

  function showMissingAnalysisState(message) {
    const cta = renderMissingAnalysisCta(message);
    fileViewEl.classList.remove("muted");
    symbolViewEl.classList.remove("muted");
    impactViewEl.classList.remove("muted");
    graphViewEl.classList.remove("muted");
    fileViewEl.innerHTML = cta;
    symbolViewEl.innerHTML = cta;
    impactViewEl.innerHTML = cta;
    graphViewEl.innerHTML = cta;
    bindRunAnalysisNowButton();
  }

  function graphParams() {
    return {
      mode: String(graphModeEl && graphModeEl.value ? graphModeEl.value : "symbol"),
      depth: Number(graphDepthEl && graphDepthEl.value ? graphDepthEl.value : 1),
      hideBuiltins: !!(graphHideBuiltinsEl && graphHideBuiltinsEl.checked),
      hideExternal: !!(graphHideExternalEl && graphHideExternalEl.checked),
      search: String(graphSearchEl && graphSearchEl.value ? graphSearchEl.value : "").trim().toLowerCase(),
    };
  }

  function setActiveTab(tab) {
    activeTab = tab === "graph" || tab === "architecture" || tab === "impact" ? tab : "details";
    const isImpact = activeTab === "impact";
    const isGraph = activeTab === "graph";
    const isArchitecture = activeTab === "architecture";
    if (tabDetailsEl) tabDetailsEl.classList.toggle("active", activeTab === "details");
    if (tabImpactEl) tabImpactEl.classList.toggle("active", isImpact);
    if (tabGraphEl) tabGraphEl.classList.toggle("active", isGraph);
    if (tabArchitectureEl) tabArchitectureEl.classList.toggle("active", isArchitecture);
    if (symbolViewEl) symbolViewEl.classList.toggle("hidden", activeTab !== "details");
    if (impactViewEl) impactViewEl.classList.toggle("hidden", !isImpact);
    if (graphViewEl) graphViewEl.classList.toggle("hidden", !isGraph);
    if (architectureViewEl) architectureViewEl.classList.toggle("hidden", !isArchitecture);
    if (graphControlsEl) graphControlsEl.classList.toggle("hidden", !isGraph);
    if (impactControlsEl) impactControlsEl.classList.toggle("hidden", !isImpact);
    if (isGraph) {
      loadGraph();
    }
    if (isImpact) {
      loadImpact();
    }
    if (isArchitecture) {
      loadArchitecture();
    }
  }

  function shortLabel(fqn) {
    const parts = String(fqn || "").split(".");
    if (parts.length >= 2) return `${parts[parts.length - 2]}.${parts[parts.length - 1]}`;
    return parts[parts.length - 1] || fqn;
  }

  function basename(path) {
    return String(path || "").replace(/\\/g, "/").split("/").pop() || "";
  }

  function renderSymbolList(rows, symbolsMap, emptyText) {
    if (!rows.length) return `<div class="muted">${esc(emptyText)}</div>`;
    return rows.slice(0, 25).map((entry) => {
      const fqn = typeof entry === "string" ? entry : entry.fqn;
      const info = symbolsMap[fqn] || {};
      const location = info.location || {};
      return `<button class="arch-row" data-fqn="${esc(fqn)}">
        <span class="arch-name">${esc(shortLabel(fqn))}</span>
        <span class="path">in:${esc(info.fan_in ?? 0)} out:${esc(info.fan_out ?? 0)} ${esc(basename(location.file || ""))}</span>
      </button>`;
    }).join("");
  }

  function repoSummarySection() {
    const cmd = `python cli.py api repo_summary --repo ${repoName || "<repo>"}`;
    const controls = `
      <div class="repo-row-actions">
        <button id='repo-summary-view' class='repo-refresh-btn' type='button'>View summary</button>
        <button id='repo-summary-regen' class='repo-refresh-btn' type='button'>Regenerate summary</button>
      </div>
    `;
    if (repoSummaryStatus === "loading") {
      return `<div class="card"><div class="section-title">Repo Summary</div>${controls}<div class="path">Loading summary...</div></div>`;
    }
    if (repoSummaryStatus === "disabled") {
      return `<div class="card arch-missing"><div class="section-title">Repo Summary</div>${controls}<div>Summary unavailable.</div></div>`;
    }
    if (repoSummaryStatus === "missing") {
      return `<div class="card arch-missing"><div class="section-title">Repo Summary</div>${controls}<div>No cached summary for current analysis. Click Regenerate.</div><div class="path">${esc(cmd)}</div></div>`;
    }
    if (repoSummaryStatus === "stale") {
      return `<div class="card arch-missing"><div class="section-title">Repo Summary</div>${controls}<div><span class="repo-badge expiring">Outdated (repo changed)</span></div><div class="path">No cached summary for current analysis. Click Regenerate.</div></div>`;
    }
    if (repoSummaryStatus === "error") {
      return `<div class="card arch-missing"><div class="section-title">Repo Summary</div>${controls}<div>${esc(repoSummaryError || "Failed to load repo summary.")}</div><div class="path">Run analyze, then: ${esc(cmd)}</div></div>`;
    }
    if (repoSummaryStatus !== "ready" || !repoSummary) {
      return `<div class="card"><div class="section-title">Repo Summary</div>${controls}<div class="path">Summary is idle. View cached or regenerate.</div></div>`;
    }

    const payload = repoSummary || {};
    const summary = payload.summary || {};
    const bullets = Array.isArray(summary.bullets) ? summary.bullets.slice(0, 7) : [];
    const notes = Array.isArray(summary.notes) ? summary.notes.slice(0, 5) : [];
    return `
      <div class="card">
        <div class="section-title">Repo Summary</div>
        ${controls}
        <div class="arch-one-liner">${esc(summary.one_liner || "")}</div>
        ${bullets.length ? `<ul class="arch-bullets">${bullets.map((b) => `<li>${esc(b)}</li>`).join("")}</ul>` : "<div class='muted'>No bullets available.</div>"}
        ${notes.length ? `<div class="section-title">Notes</div><ul class="arch-bullets">${notes.map((n) => `<li>${esc(n)}</li>`).join("")}</ul>` : ""}
        <div class="path">source: deterministic | cached: ${esc(String(payload.cached))} | updated: ${esc(payload.cached_at || payload.generated_at || repoSummaryUpdatedAt || "unknown")}</div>
      </div>
    `;
  }

  async function loadRepoSummary(force, generate) {
    const shouldGenerate = !!generate;
    if (!force && !activeRepoHash) {
      repoSummaryStatus = "missing";
      repoSummary = null;
      return;
    }
    repoSummaryStatus = "loading";
    repoSummaryError = "";
    try {
      if (!shouldGenerate) {
        const state = await fetchJson(`/api/repo_summary?repo=${encodeURIComponent(repoDir || "")}`);
        if (state.exists && state.repo_summary) {
          const cachedSummary = state.repo_summary || {};
          repoSummary = {
            provider: String(cachedSummary.provider || ""),
            model: String(cachedSummary.model || ""),
            cached: true,
            generated_at: String(cachedSummary.generated_at || ""),
            summary: _summaryFromMarkdown(String(cachedSummary.content_markdown || "")),
          };
          repoSummaryUpdatedAt = String(cachedSummary.generated_at || "");
          repoSummaryStatus = "ready";
          return;
        }
        if (state.outdated) {
          repoSummary = null;
          repoSummaryUpdatedAt = "";
          repoSummaryStatus = "stale";
          return;
        }
        repoSummary = null;
        repoSummaryUpdatedAt = "";
        repoSummaryStatus = "missing";
        return;
      }

      const data = await fetchJson(`/api/repo_summary/generate?force=${force ? "1" : "0"}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_hash: activeRepoHash || "", repo: repoDir || "", force: !!force }),
      });
      const generated = data.repo_summary || {};
      repoSummary = {
        provider: String(generated.provider || ""),
        model: String(generated.model || ""),
        cached: !!data.cached,
        generated_at: String(generated.generated_at || ""),
        summary: _summaryFromMarkdown(String(generated.content_markdown || "")),
      };
      repoSummaryUpdatedAt = String(generated.generated_at || "");
      repoSummaryStatus = "ready";
      showToast(data.cached ? "Using cached summary" : "Summary generated", "success");
    } catch (e) {
      repoSummary = null;
      repoSummaryUpdatedAt = "";
      if (e && e.error === "MISSING_ANALYSIS") {
        repoSummaryStatus = "missing";
        repoSummaryError = "";
      } else if (e && e.error === "AI_DISABLED") {
        repoSummaryStatus = "disabled";
      } else {
        repoSummaryStatus = "error";
        repoSummaryError = redactSecrets((e && (e.message || e.error)) || "Repo summary load failed");
      }
    }
  }

  function riskPillClass(risk) {
    const v = String(risk || "").toLowerCase();
    if (v === "high") return "risk-pill high";
    if (v === "medium") return "risk-pill medium";
    return "risk-pill low";
  }

  function riskRadarSection() {
    const cmd = `python cli.py api risk_radar --repo ${repoName || "<repo>"}`;
    if (riskRadarStatus === "loading") {
      return `<div class="card"><div class="section-title">Risk Radar</div><div class="path">Loading risk radar...</div></div>`;
    }
    if (riskRadarStatus === "missing") {
      return `<div class="card arch-missing"><div class="section-title">Risk Radar</div><div>Risk radar not generated yet.</div><div class="path">${esc(cmd)}</div></div>`;
    }
    if (riskRadarStatus === "error") {
      return `<div class="card arch-missing"><div class="section-title">Risk Radar</div><div>${esc(riskRadarError || "Failed to load risk radar.")}</div><div class="path">Run analyze, then: ${esc(cmd)}</div></div>`;
    }
    if (riskRadarStatus !== "ready" || !riskRadar) {
      return `<div class="card"><div class="section-title">Risk Radar</div><div class="path">No risk data loaded.</div></div>`;
    }

    const payload = riskRadar || {};
    const hotspots = Array.isArray(payload.hotspots) ? payload.hotspots.slice(0, 5) : [];
    const riskyFiles = Array.isArray(payload.risky_files) ? payload.risky_files.slice(0, 5) : [];
    const refactors = Array.isArray(payload.refactor_targets) ? payload.refactor_targets.slice(0, 6) : [];

    const hotspotsHtml = hotspots.length
      ? hotspots.map((h) => `
        <button class="arch-row risk-hotspot-row" data-fqn="${esc(h.fqn)}">
          <span class="arch-name">${esc(shortLabel(h.fqn))}</span>
          <span class="${riskPillClass(h.risk)}">${esc(h.risk)}</span>
          <span class="path">score:${esc(h.score)} in:${esc(h.fan_in)} out:${esc(h.fan_out)}</span>
          ${Array.isArray(h.reasons) && h.reasons.length ? `<span class="path">${esc(h.reasons[0])}</span>` : ""}
        </button>
      `).join("")
      : "<div class='muted'>No hotspots detected.</div>";

    const filesHtml = riskyFiles.length
      ? riskyFiles.map((f) => `
        <div class="risk-file-row">
          <span class="arch-name">${esc(basename(f.file || ""))}</span>
          <span class="${riskPillClass(f.risk)}">${esc(f.risk)}</span>
          <span class="path">score:${esc(f.score)} edges:${esc(f.edges)}</span>
        </div>
      `).join("")
      : "<div class='muted'>No risky files detected.</div>";

    const refactorHtml = refactors.length
      ? refactors.map((r) => `
        <div class="risk-target">
          <div class="arch-name">${esc(r.title || "")}</div>
          <div class="path">${esc(r.why || "")}</div>
          ${(Array.isArray(r.targets) && r.targets.length) ? `<div class="path">targets: ${esc(r.targets.join(", "))}</div>` : ""}
        </div>
      `).join("")
      : "<div class='muted'>No refactor targets suggested.</div>";

    return `
      <div class="card">
        <div class="section-title">Risk Radar</div>
        <div class="path">updated: ${esc(riskRadarUpdatedAt || "unknown")}</div>
        <div class="divider"></div>
        <div class="section-title">Top Hotspots</div>
        ${hotspotsHtml}
        <div class="divider"></div>
        <div class="section-title">Top Risky Files</div>
        ${filesHtml}
        <div class="divider"></div>
        <div class="section-title">Refactor Targets</div>
        ${refactorHtml}
      </div>
    `;
  }

  async function loadRiskRadar(force) {
    if (!force && riskRadarStatus === "ready" && riskRadar) return;
    riskRadarStatus = "loading";
    riskRadarError = "";
    try {
      const data = await fetchJson("/api/risk_radar");
      riskRadar = data.risk_radar || null;
      riskRadarUpdatedAt = data.updated_at || "";
      riskRadarStatus = "ready";
    } catch (e) {
      riskRadar = null;
      riskRadarUpdatedAt = "";
      if (e && e.error === "MISSING_RISK_RADAR") {
        riskRadarStatus = "missing";
        riskRadarError = "";
      } else {
        riskRadarStatus = "error";
        riskRadarError = redactSecrets((e && (e.message || e.error)) || "Risk radar load failed");
      }
    }
  }

  async function loadArchitecture() {
    if (!architectureViewEl) return;
    architectureViewEl.classList.remove("muted");
    architectureViewEl.innerHTML = "<div class='card'>Loading architecture insights...</div>";
    try {
      if (!architectureCache) architectureCache = await fetchJson("/api/architecture");
      await loadRepoSummary(false, false);
      await loadRiskRadar(false);
      const arch = architectureCache.architecture_metrics || {};
      const dep = architectureCache.dependency_cycles || {};
      const repo = arch.repo || {};
      const symbolsMap = arch.symbols || {};

      const orchestrators = (repo.orchestrators && repo.orchestrators.length ? repo.orchestrators : (repo.top_fan_out || []).map((x) => x.fqn || x)).filter(Boolean);
      const critical = (repo.critical_symbols && repo.critical_symbols.length ? repo.critical_symbols : (repo.top_fan_in || []).map((x) => x.fqn || x)).filter(Boolean);
      const dead = (repo.dead_symbols || []).filter(Boolean);
      const cycles = dep.cycles || [];

      architectureViewEl.innerHTML = `
        ${repoSummarySection()}
        ${riskRadarSection()}
        <div class="arch-grid">
          <div class="kpi-card"><div class="kpi-label">Orchestrators</div><div class="kpi-value">${orchestrators.length}</div></div>
          <div class="kpi-card"><div class="kpi-label">Critical APIs</div><div class="kpi-value">${critical.length}</div></div>
          <div class="kpi-card"><div class="kpi-label">Dead Symbols</div><div class="kpi-value">${dead.length}</div></div>
          <div class="kpi-card"><div class="kpi-label">Dependency Cycles</div><div class="kpi-value">${dep.cycle_count || 0}</div></div>
        </div>
        <div class="card">
          <div class="section-title">Top Orchestrators</div>
          ${renderSymbolList(orchestrators, symbolsMap, "No orchestrators detected.")}
        </div>
        <div class="card">
          <div class="section-title">Top Critical Symbols</div>
          ${renderSymbolList(critical, symbolsMap, "No critical symbols detected.")}
        </div>
        <div class="card">
          <div class="section-title">Dead Symbols</div>
          ${renderSymbolList(dead, symbolsMap, "No dead symbols detected.")}
        </div>
        <div class="card">
          <div class="section-title">Dependency Cycles</div>
          ${dep.cycle_count ? cycles.slice(0, 50).map((c, i) => `<div class="cycle-row"><span>${esc(c.join(" -> "))}</span><button class="copy-cycle" data-cycle="${esc(c.join(" -> "))}">Copy</button></div>`).join("") : "<div class='ok-cycle'>No cycles detected OK</div>"}
        </div>
      `;

      const viewBtn = architectureViewEl.querySelector("#repo-summary-view");
      if (viewBtn) {
        viewBtn.addEventListener("click", async () => {
          await loadRepoSummary(false, false);
          await loadArchitecture();
        });
      }
      const regenBtn = architectureViewEl.querySelector("#repo-summary-regen");
      if (regenBtn) {
        regenBtn.addEventListener("click", async () => {
          const forceEl = architectureViewEl.querySelector("#repo-summary-force");
          const force = !!(forceEl && forceEl.checked);
          await loadRepoSummary(force, true);
          await loadArchitecture();
        });
      }
      architectureViewEl.querySelectorAll(".arch-row").forEach((el) => {
        el.addEventListener("click", async () => {
          const fqn = el.getAttribute("data-fqn");
          if (!fqn) return;
          setActiveTab("details");
          await loadSymbol(fqn);
        });
      });
      architectureViewEl.querySelectorAll(".copy-cycle[data-cycle]").forEach((el) => {
        el.addEventListener("click", async () => {
          const text = el.getAttribute("data-cycle") || "";
          try {
            await navigator.clipboard.writeText(text);
            el.textContent = "Copied";
            window.setTimeout(() => { el.textContent = "Copy"; }, 800);
          } catch (_e) {
            // noop
          }
        });
      });
    } catch (e) {
      const errCode = String((e && e.error) || "");
      if (errCode === "MISSING_ARCHITECTURE_CACHE" || errCode === "CACHE_NOT_FOUND") {
        architectureViewEl.classList.remove("muted");
        architectureViewEl.innerHTML = renderMissingAnalysisCta("Run Analyze first to unlock architecture insights.");
        bindRunAnalysisNowButton();
        return;
      }
      architectureViewEl.classList.remove("muted");
      architectureViewEl.innerHTML = `
        <div class="card arch-missing">
          <div class="section-title">Architecture Insights Unavailable</div>
          <div>${esc((e && (e.message || e.error)) || "Missing architecture cache artifacts.")}</div>
          <div class="path">Run: python cli.py api analyze --path &lt;repo&gt;</div>
        </div>
      `;
    }
  }

  function renderGraphData(data) {
    const p = graphParams();
    const nodes = (data.nodes || []).slice();
    const edges = (data.edges || []).slice();
    const byId = new Map(nodes.map((n) => [n.id, n]));
    const center = data.center || activeSymbolFqn;
    const mode = data.mode || "symbol";
    const seedNodes = new Set(data.seed_nodes || []);

    const matches = new Set(
      !p.search
        ? []
        : nodes.filter((n) => n.id.toLowerCase().includes(p.search) || String(n.label || "").toLowerCase().includes(p.search)).map((n) => n.id)
    );

    const incoming = [];
    const outgoing = [];
    const internal = [];
    for (const e of edges) {
      if (mode === "file") {
        const fromSeed = seedNodes.has(e.from);
        const toSeed = seedNodes.has(e.to);
        if (toSeed && !fromSeed) incoming.push(e);
        else if (fromSeed && !toSeed) outgoing.push(e);
        else if (fromSeed && toSeed) internal.push(e);
      } else {
        if (e.to === center) incoming.push(e);
        if (e.from === center) outgoing.push(e);
      }
    }

    function nodePill(nodeId) {
      const n = byId.get(nodeId) || { id: nodeId, label: nodeId, kind: "external", clickable: false };
      const cls = `graph-node kind-${n.kind} ${matches.has(nodeId) ? "graph-match" : ""} ${n.clickable ? "graph-clickable" : ""}`;
      const subtitle = n.subtitle ? `<div class="path">${esc(n.subtitle)}</div>` : "";
      return `<div class="${cls}" data-node-id="${esc(nodeId)}">
        <div>${esc(n.label || nodeId)}</div>
        ${subtitle}
      </div>`;
    }

    graphViewEl.classList.remove("muted");
    graphViewEl.innerHTML = `
      <div class="card graph-card">
        <div class="graph-legend">
          <span class="legend-item"><span class="dot local"></span>Local</span>
          <span class="legend-item"><span class="dot builtin"></span>Builtins</span>
          <span class="legend-item"><span class="dot external"></span>External</span>
        </div>
        <div class="section-title">${mode === "file" ? "Center File" : "Center"}</div>
        ${mode === "file" ? `<div class="path">${esc(center)}</div>` : nodePill(center)}
        ${mode === "file" ? `<div class="path">Seed symbols: ${seedNodes.size}</div>` : ""}
        <div class="divider"></div>
        <div class="section-title">Incoming Callers (${incoming.length})</div>
        ${incoming.length ? incoming.slice(0, 200).map((e) => `<div class="graph-edge-row">${nodePill(e.from)} <span class="edge-arrow">-></span> <span class="path">${esc(e.count)}x</span></div>`).join("") : "<div class='muted'>No incoming callers in current depth/filter.</div>"}
        <div class="divider"></div>
        <div class="section-title">Outgoing Callees (${outgoing.length})</div>
        ${outgoing.length ? outgoing.slice(0, 200).map((e) => `<div class="graph-edge-row">${nodePill(e.to)} <span class="path">${esc(e.count)}x</span></div>`).join("") : "<div class='muted'>No outgoing callees in current depth/filter.</div>"}
        ${mode === "file" ? `<div class="divider"></div><div class="section-title">Internal File Edges (${internal.length})</div>${internal.length ? internal.slice(0, 200).map((e) => `<div class="graph-edge-row">${nodePill(e.from)} <span class="edge-arrow">-></span> ${nodePill(e.to)} <span class="path">${esc(e.count)}x</span></div>`).join("") : "<div class='muted'>No internal edges in current depth/filter.</div>"}` : ""}
        <div class="divider"></div>
        <div class="section-title">Subgraph Stats</div>
        <div class="path">Nodes: ${nodes.length} | Edges: ${edges.length} | Depth: ${data.depth}</div>
      </div>
    `;

    graphViewEl.querySelectorAll(".graph-node.graph-clickable").forEach((el) => {
      el.addEventListener("click", () => {
        const next = el.getAttribute("data-node-id");
        if (next) loadSymbol(next);
      });
    });
  }

  function renderImpactList(nodes, emptyText) {
    if (!nodes || !nodes.length) return `<div class="muted">${esc(emptyText)}</div>`;
    return nodes.slice(0, 200).map((n) => {
      const isLocal = !String(n.fqn || "").startsWith("builtins.") && !String(n.fqn || "").startsWith("external::");
      if (isLocal) {
        return `
          <button class="arch-row impact-node-row" data-fqn="${esc(n.fqn)}">
            <span class="arch-name">${esc(shortLabel(n.fqn))}</span>
            <span class="impact-distance">d${esc(n.distance)}</span>
            <span class="path">in:${esc(n.fan_in)} out:${esc(n.fan_out)} ${esc(n.file ? relPath(n.file) : "")}:${esc(n.line)}</span>
          </button>
        `;
      }
      return `
        <div class="risk-file-row">
          <span class="arch-name">${esc(shortLabel(n.fqn))}</span>
          <span class="impact-distance">d${esc(n.distance)}</span>
          <span class="path">in:${esc(n.fan_in)} out:${esc(n.fan_out)} ${esc(n.file ? relPath(n.file) : "")}:${esc(n.line)}</span>
        </div>
      `;
    }).join("");
  }

  function renderImpactedFiles(items) {
    if (!items || !items.length) return "<div class='muted'>No impacted files.</div>";
    return items.slice(0, 15).map((x) => `
      <div class="impact-file-row">
        <span class="path">${esc(relPath(x.file || ""))}</span>
        <span class="impact-distance">${esc(x.count)}</span>
      </div>
    `).join("");
  }

  async function loadImpact(fqn) {
    if (!impactViewEl) return;
    const anchor = fqn || activeSymbolFqn;
    if (!anchor) {
      impactViewEl.classList.add("muted");
      impactViewEl.textContent = "Select a symbol to view impact.";
      return;
    }
    const depth = Number(impactDepthEl && impactDepthEl.value ? impactDepthEl.value : 2);
    const maxNodes = Number(impactMaxNodesEl && impactMaxNodesEl.value ? impactMaxNodesEl.value : 200);
    const key = `${anchor}|${depth}|${maxNodes}`;
    impactViewEl.classList.remove("muted");
    impactViewEl.innerHTML = "<div class='card'>Loading impact...</div>";
    try {
      let data = impactDataCache.get(key);
      if (!data) {
        data = await fetchJson(`/api/impact?target=${encodeURIComponent(anchor)}&depth=${depth}&max_nodes=${maxNodes}`);
        impactDataCache.set(key, data);
      }
      const up = data.upstream || { nodes: [], truncated: false };
      const down = data.downstream || { nodes: [], truncated: false };
      const files = data.impacted_files || { upstream: [], downstream: [] };
      const truncated = !!(up.truncated || down.truncated);
      const upstreamBadge = up.truncated ? " <span class='impact-section-badge'>TRUNCATED</span>" : "";
      const downstreamBadge = down.truncated ? " <span class='impact-section-badge'>TRUNCATED</span>" : "";

      impactViewEl.innerHTML = `
        <div class="card impact-card">
          <div class="section-title">Impact</div>
          <div class="path">Target: ${esc(anchor)} | depth: ${esc(data.depth)} | max_nodes: ${esc(data.max_nodes)}</div>
          ${truncated ? `<div class='impact-truncated-banner'>Warning: Results truncated (max_nodes=${esc(data.max_nodes)}). Displaying partial results.</div>` : ""}
          <div class="divider"></div>
          <div class="section-title">Upstream${upstreamBadge}</div>
          ${renderImpactList(up.nodes || [], "No upstream dependents in selected depth.")}
          <div class="divider"></div>
          <div class="section-title">Downstream${downstreamBadge}</div>
          ${renderImpactList(down.nodes || [], "No downstream dependencies in selected depth.")}
          <div class="divider"></div>
          <div class="section-title">Impacted Files (Upstream)</div>
          ${renderImpactedFiles(files.upstream || [])}
          <div class="divider"></div>
          <div class="section-title">Impacted Files (Downstream)</div>
          ${renderImpactedFiles(files.downstream || [])}
        </div>
      `;

      impactViewEl.querySelectorAll(".impact-node-row").forEach((el) => {
        el.addEventListener("click", async () => {
          const next = el.getAttribute("data-fqn");
          if (!next) return;
          setActiveTab("details");
          await loadSymbol(next);
        });
      });
    } catch (e) {
      const errCode = String((e && e.error) || "");
      if (errCode === "MISSING_ANALYSIS" || errCode === "CACHE_NOT_FOUND") {
        impactViewEl.classList.remove("muted");
        impactViewEl.innerHTML = renderMissingAnalysisCta("After it finishes, impact will load automatically.");
        bindRunAnalysisNowButton();
        return;
      }
      impactViewEl.classList.add("muted");
      impactViewEl.textContent = redactSecrets((e && (e.error || e.message)) || "Impact unavailable.");
    }
  }

  async function loadGraph(fqn) {
    if (!graphViewEl) return;
    const p = graphParams();
    const graphMode = p.mode === "file" ? "file" : "symbol";
    const anchor = graphMode === "file" ? activeFilePath : (fqn || activeSymbolFqn);
    if (!anchor) {
      graphViewEl.classList.add("muted");
      graphViewEl.textContent = graphMode === "file"
        ? "Select a file to view file graph."
        : "Select a symbol to view graph.";
      return;
    }
    const key = `${graphMode}|${anchor}|${p.depth}|${p.hideBuiltins}|${p.hideExternal}`;
    graphViewEl.classList.remove("muted");
    graphViewEl.innerHTML = "<div class='card'>Loading graph...</div>";
    try {
      let data = graphDataCache.get(key);
      if (!data) {
        const targetParam = graphMode === "file"
          ? `file=${encodeURIComponent(anchor)}`
          : `fqn=${encodeURIComponent(anchor)}`;
        data = await fetchJson(`/api/graph?${targetParam}&depth=${p.depth}&hide_builtins=${p.hideBuiltins ? "true" : "false"}&hide_external=${p.hideExternal ? "true" : "false"}`);
        graphDataCache.set(key, data);
      }
      renderGraphData(data);
    } catch (e) {
      const errCode = String((e && e.error) || "");
      if (errCode === "MISSING_ANALYSIS" || errCode === "CACHE_NOT_FOUND") {
        graphViewEl.classList.remove("muted");
        graphViewEl.innerHTML = renderMissingAnalysisCta("After it finishes, graph will load automatically.");
        bindRunAnalysisNowButton();
        return;
      }
      graphViewEl.classList.add("muted");
      graphViewEl.textContent = redactSecrets((e && (e.error || e.message)) || "Graph unavailable.");
    }
  }

  function renderRecentSymbols() {
    if (!recentSymbolsEl || !recentSymbolsWrapEl) return;
    const items = recentSymbols.slice(0, 8);
    if (!items.length) {
      recentSymbolsWrapEl.classList.add("hidden");
      recentSymbolsEl.className = "content muted";
      recentSymbolsEl.textContent = "";
      return;
    }
    recentSymbolsWrapEl.classList.remove("hidden");
    recentSymbolsEl.className = "content";
    recentSymbolsEl.innerHTML = items
      .map((fqn) => {
        const p = parseSymbolParts(fqn);
        return `<div><span class="symbol-link recent-link" data-fqn="${esc(fqn)}">${esc(p.display)}</span> <span class="path">${esc(fqn)}</span></div>`;
      })
      .join("");
    recentSymbolsEl.querySelectorAll(".recent-link").forEach((el) => {
      el.addEventListener("click", () => loadSymbol(el.getAttribute("data-fqn")));
    });
  }

  function renderRecentFiles() {
    if (!recentFilesEl || !recentFilesWrapEl) return;
    const items = recentFiles.slice(0, 8);
    if (!items.length) {
      recentFilesWrapEl.classList.add("hidden");
      recentFilesEl.className = "content muted";
      recentFilesEl.textContent = "";
      return;
    }
    recentFilesWrapEl.classList.remove("hidden");
    recentFilesEl.className = "content";
    recentFilesEl.innerHTML = items
      .map((file) => `<div><span class="symbol-link recent-file-link" data-file="${esc(file)}">${esc(file)}</span></div>`)
      .join("");
    recentFilesEl.querySelectorAll(".recent-file-link").forEach((el) => {
      el.addEventListener("click", () => loadFile(el.getAttribute("data-file")));
    });
  }

  function renderRecents() {
    renderRecentSymbols();
    renderRecentFiles();
  }

  async function loadUiState() {
    try {
      const data = await fetchJson("/api/ui_state");
      const state = data.state || {};
      recentSymbols = Array.isArray(state.recent_symbols) ? state.recent_symbols : [];
      recentFiles = Array.isArray(state.recent_files) ? state.recent_files : [];
      lastSymbol = String(state.last_symbol || "");
      renderRecents();
      return true;
    } catch (_e) {
      recentSymbols = [];
      recentFiles = [];
      lastSymbol = "";
      renderRecents();
      return false;
    }
  }

  async function updateUiState(payload) {
    try {
      await fetchJson("/api/ui_state/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload || {}),
      });
      await loadUiState();
    } catch (_e) {
      // Keep UI responsive even if persistence fails.
    }
  }

  function renderWorkspaceSelect() {
    if (!repoSelectEl) return;
    const placeholder = !activeRepoHash
      ? '<option value="" selected>Select repo...</option>'
      : "";
    repoSelectEl.innerHTML = placeholder + workspaceRepos
      .map((r) => `<option value="${esc(r.repo_hash)}" ${r.repo_hash === activeRepoHash ? "selected" : ""}>${esc(r.name)}</option>`)
      .join("");
    syncRepoHeader();
  }

  async function loadWorkspace() {
    try {
      const reg = await fetchJson("/api/registry");
      rememberRepos = !!reg.remember_repos;
      if (aiSettingsRememberReposEl) aiSettingsRememberReposEl.checked = !!rememberRepos;
      updateRepoListModeUi();
    } catch (_e) {
      rememberRepos = false;
      updateRepoListModeUi();
    }
    const ws = await fetchJson("/api/workspace");
    workspaceRepos = ws.repos || [];
    activeRepoHash = ws.active_repo_hash || "";
    if (!rememberRepos) {
      workspaceRepos = [];
      activeRepoHash = "";
    }
    renderWorkspaceSelect();
    syncRepoHeader();
    await loadRepoRegistry();
    await loadDataPrivacy();
  }

  async function selectWorkspace(repoHash) {
    if (!repoHash) return;
    try {
      await fetchJson("/api/workspace/select", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_hash: repoHash }),
      });
    } catch (_e) {
      const candidate = (repoRegistry || []).find((r) => String(r.repo_hash) === String(repoHash));
      if (candidate && candidate.repo_path) {
        await fetchJson("/api/workspace/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: candidate.repo_path }),
        });
        await fetchJson("/api/workspace/select", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_hash: repoHash }),
        });
      } else {
        throw _e;
      }
    }
    activeRepoHash = repoHash;
    syncRepoHeader();
    await refreshForActiveRepo();
  }

  async function addWorkspaceRepo() {
    if (!addRepoInlineEl) return;
    if (addRepoInlineEl.classList.contains("hidden")) {
      openRepoPanel("local");
      return;
    }
    closeRepoPanel(false);
  }

  function repoBadge(repo) {
    if (!repo) return "";
    if (!repo.has_analysis) return `<span class="repo-badge not-analyzed">Not analyzed</span>`;
    const daysLeft = Number(repo && repo.retention ? repo.retention.days_left : NaN);
    if (Number.isFinite(daysLeft) && daysLeft <= 3 && daysLeft >= 0) {
      return `<span class="repo-badge expiring">Expiring in ${Math.ceil(daysLeft)}d</span>`;
    }
    return `<span class="repo-badge analyzed">Analyzed</span>`;
  }

  function sourceLabel(repo) {
    if (!repo) return "filesystem";
    if (String(repo.source || "") === "github") return `github ${repo.mode || "zip"}`;
    return "filesystem";
  }

  function repoPolicyValue(repo) {
    const r = (repo && repo.retention) || {};
    const mode = String(r.mode || "ttl");
    const ttl = Number(r.ttl_days || 30);
    if (mode === "pinned" || ttl <= 0) return "never";
    if (ttl <= 1) return "24h";
    if (ttl <= 7) return "7d";
    if (ttl <= 14) return "14d";
    if (ttl <= 30) return "30d";
    return "90d";
  }

  function isExpiringSoon(repo) {
    const daysLeft = Number(repo && repo.retention ? repo.retention.days_left : NaN);
    return Number.isFinite(daysLeft) && daysLeft >= 0 && daysLeft < 2;
  }

  function renderRepoRegistry() {
    if (!repoListContentEl) return;
    const rows = Array.isArray(repoRegistry) ? repoRegistry : [];
    if (!rows.length) {
      repoListContentEl.innerHTML = "<div class='muted'>No repositories added yet. Add a local path or GitHub repo to begin.</div>";
      return;
    }
    repoListContentEl.innerHTML = rows.map((r) => `
      <div class="repo-row" data-repo-hash="${esc(r.repo_hash)}">
        <div class="repo-row-header">
          <div class="repo-row-name">${esc(r.name || r.repo_hash)} ${r.private_mode ? "<span class='repo-badge private'>PRIVATE MODE</span>" : ""}</div>
          <div class="repo-row-actions">
            ${repoBadge(r)}
            ${isExpiringSoon(r) ? "<span class='expires-chip'>Expires soon</span>" : ""}
          </div>
        </div>
        <div class="path">${esc(r.source === "github" ? (r.repo_url || r.repo_path || "") : (r.repo_path || ""))}</div>
        <div class="path">Source: ${esc(sourceLabel(r))}</div>
        <div class="path">Cache size: ${esc(formatBytes(r.size_bytes || 0))} | Last analyzed: ${esc(r.last_updated || "unknown")}</div>
        <div class="path">${esc(r.cache_dir || "")}</div>
        ${r.source === "github" ? `<div class="path">Workspace: ${esc(r.repo_path || "")}</div>` : ""}
        <div class="repo-row-actions">
          <select class="repo-policy-select" data-repo-hash="${esc(r.repo_hash)}">
            <option value="1d" ${repoPolicyValue(r) === "24h" ? "selected" : ""}>Delete after 1 day</option>
            <option value="7d" ${repoPolicyValue(r) === "7d" ? "selected" : ""}>Delete after 7 days</option>
            <option value="14d" ${repoPolicyValue(r) === "14d" ? "selected" : ""}>Delete after 14 days</option>
            <option value="30d" ${repoPolicyValue(r) === "30d" ? "selected" : ""}>Delete after 30 days</option>
            <option value="90d" ${repoPolicyValue(r) === "90d" ? "selected" : ""}>Delete after 90 days</option>
            <option value="never" ${repoPolicyValue(r) === "never" ? "selected" : ""}>Never auto-delete</option>
          </select>
          <button class="repo-btn small repo-policy-save-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Set Auto-Delete Policy</button>
        </div>
        <div class="repo-row-actions">
          <button class="repo-btn small repo-open-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Open</button>
          <button class="repo-btn small repo-analyze-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">${r.has_analysis ? "Re-analyze" : "Analyze"}</button>
          <button class="repo-btn small danger repo-clear-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Delete analysis data</button>
          ${isExpiringSoon(r) ? `<button class="repo-btn small danger repo-delete-now-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Delete now</button>` : ""}
          <button class="repo-btn small danger repo-delete-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Delete Repo Completely</button>
          <button class="repo-btn small repo-remove-btn" type="button" data-repo-hash="${esc(r.repo_hash)}">Remove Repo from list</button>
        </div>
      </div>
    `).join("");

    repoListContentEl.querySelectorAll(".repo-open-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await selectWorkspace(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-analyze-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await analyzeRepoByHash(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-clear-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await clearRepoByHash(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-delete-now-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await clearRepoByHash(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-delete-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await deleteRepoByHash(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-remove-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        await removeRepoFromList(repoHash);
      });
    });
    repoListContentEl.querySelectorAll(".repo-policy-save-btn").forEach((el) => {
      el.addEventListener("click", async () => {
        const repoHash = el.getAttribute("data-repo-hash");
        if (!repoHash) return;
        const select = repoListContentEl.querySelector(`.repo-policy-select[data-repo-hash="${CSS.escape(repoHash)}"]`);
        const policy = select ? String(select.value || "30d") : "30d";
        await setRepoPolicy(repoHash, policy);
      });
    });
  }

  async function loadRepoRegistry() {
    try {
      const data = await fetchJson("/api/repo_registry");
      repoRegistry = Array.isArray(data.repos) ? data.repos : [];
      renderRepoRegistry();
    } catch (_e) {
      repoRegistry = [];
      if (repoListContentEl) repoListContentEl.innerHTML = "<div class='muted'>Failed to load repo registry.</div>";
    }
  }

  async function maybeApplyPrivateDefaultRetention(repoHash, shouldApply) {
    if (!repoHash || !shouldApply) return;
    try {
      await fetchJson("/api/cache/retention", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_hash: repoHash, days: 7 }),
      });
    } catch (_e) {
      // Best-effort; analysis result should not fail if retention update fails.
    }
  }

  async function analyzeRepoByHash(repoHash, options) {
    if (!repoHash) return { ok: false, error: { message: "INVALID_REPO_HASH" } };
    const opts = options || {};
    const token = String(opts.token || "").trim();
    const showErrors = opts.showErrors !== false;
    const repoBefore = (repoRegistry || []).find((r) => String(r.repo_hash) === String(repoHash));
    const shouldApplyPrivateDefault = !!(
      opts.privateModeHint
      || token
      || (repoBefore && repoBefore.private_mode && !repoBefore.has_analysis)
    );
    try {
      const data = await fetchJson("/api/repo_analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_hash: repoHash, token, private_mode: !!opts.privateModeHint }),
      });
      await maybeApplyPrivateDefaultRetention(repoHash, shouldApplyPrivateDefault);
      await loadWorkspace();
      if (repoHash) {
        await selectWorkspace(repoHash);
      }
      return { ok: true, data };
    } catch (e) {
      const message = analysisErrorMessage(e || {});
      if (showErrors) {
        window.alert(message);
      }
      return { ok: false, error: e, message };
    }
  }

  async function clearRepoByHash(repoHash) {
    if (!repoHash) return;
    await openConfirmModal({
      title: "Delete analysis data",
      message: `This will remove cache artifacts for ${repoHash}.`,
      confirmText: "Yes",
      cancelText: "Cancel",
      actionType: "delete_analysis",
      payload: { repo_hash: repoHash },
      onConfirm: async () => {
        await fetchJson("/api/cache/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_hash: repoHash, dry_run: false }),
        });
        await loadRepoRegistry();
        await loadDataPrivacy();
        if (String(activeRepoHash) === String(repoHash)) {
          await refreshForActiveRepo();
        }
      },
    });
  }

  async function deleteRepoByHash(repoHash) {
    if (!repoHash) return;
    await openConfirmModal({
      title: "Delete repo completely",
      message: "This will permanently remove analysis data and cloned/downloaded source.",
      confirmText: "Yes",
      cancelText: "Cancel",
      actionType: "delete_repo_completely",
      payload: { repo_hash: repoHash },
      onConfirm: async () => {
        await fetchJson("/api/cache/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_hash: repoHash, dry_run: false }),
        });
        await loadWorkspace();
        await refreshForActiveRepo();
        await loadDataPrivacy();
      },
    });
  }

  async function removeRepoFromList(repoHash) {
    if (!repoHash) return;
    const msg = autoCleanOnRemove
      ? `Remove repo ${repoHash} from UI list and delete its local cache?`
      : `Remove repo ${repoHash} from UI list only?`;
    await openConfirmModal({
      title: "Remove repo from list",
      message: msg,
      confirmText: "Yes",
      cancelText: "Cancel",
      actionType: "remove_repo_from_list",
      payload: { repo_hash: repoHash, auto_clean: !!autoCleanOnRemove },
      onConfirm: async () => {
        await fetchJson("/api/registry/repos/remove", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_hash: repoHash }),
        });
        if (autoCleanOnRemove) {
          await fetchJson("/api/cache/clear", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ repo_hash: repoHash, dry_run: false }),
          });
        }
        await loadWorkspace();
        await refreshForActiveRepo();
      },
    });
  }

  async function setRepoPolicy(repoHash, policyValue) {
    let days = 30;
    if (policyValue === "never") days = 0;
    if (policyValue === "24h" || policyValue === "1d") days = 1;
    if (policyValue === "7d") days = 7;
    if (policyValue === "14d") days = 14;
    try {
      if (policyValue === "90d") days = 90;
      await fetchJson("/api/cache/retention", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_hash: repoHash, days }),
      });
      await loadRepoRegistry();
      await loadDataPrivacy();
    } catch (e) {
      window.alert(redactSecrets((e && (e.message || e.error)) || "Policy update failed"));
    }
  }

  async function loadDataPrivacy() {
    if (!privacySummaryEl) return;
    privacySummaryEl.textContent = "Loading data retention...";
    privacyExpiringEl.innerHTML = "";
    if (privacyConfirmEl) {
      privacyConfirmEl.classList.add("hidden");
      privacyConfirmEl.innerHTML = "";
    }
    try {
      const data = await fetchJson("/api/cache/list");
      dataPrivacyCache = data;
      const caches = Array.isArray(data.caches) ? data.caches : [];
      const totalSize = caches.reduce((acc, c) => acc + Number(c.size_bytes || 0), 0);
      const activeRepo = currentRepoEntry();
      const activeCache = activeRepo ? caches.find((c) => String(c.repo_hash) === String(activeRepo.repo_hash)) : null;
      const retentionMode = String(activeCache && activeCache.retention ? activeCache.retention.mode : "ttl");
      const ttlDays = Number(activeCache && activeCache.retention ? activeCache.retention.ttl_days : 14);
      const retentionLabel = (retentionMode === "pinned" || ttlDays <= 0) ? "Never" : `${Math.max(1, Math.floor(ttlDays))} days`;
      const lastAnalyzed = String((activeCache && activeCache.last_updated) || "never");
      const autoDeleteOn = !((retentionMode === "pinned") || ttlDays <= 0);
      privacySummaryEl.textContent = `Stored locally in .codemap_cache | Retention: ${retentionLabel} | Last analyzed: ${lastAnalyzed} | Auto-delete policy: ${autoDeleteOn ? "ON" : "OFF"}`;
      if (privacyResultEl) {
        privacyResultEl.textContent = `Repos cached: ${caches.length} | Total size: ${formatBytes(totalSize)}`;
      }

      if (activeRepo && repoRetentionSelectEl) {
        const ttl = Number(activeCache && activeCache.retention ? activeCache.retention.ttl_days : 14);
        if (!Number.isFinite(ttl) || ttl <= 0) repoRetentionSelectEl.value = "0";
        else if (ttl <= 1) repoRetentionSelectEl.value = "1";
        else if (ttl <= 7) repoRetentionSelectEl.value = "7";
        else if (ttl <= 14) repoRetentionSelectEl.value = "14";
        else if (ttl <= 30) repoRetentionSelectEl.value = "30";
        else repoRetentionSelectEl.value = "90";
      }

      const activePrivate = !!(activeRepo && activeRepo.private_mode);
      if (privacyPrivateBannerEl) {
        privacyPrivateBannerEl.classList.toggle("hidden", !activePrivate);
      }

      const expiring = caches.filter((c) => {
        const days = Number(c && c.retention ? c.retention.days_left : NaN);
        return c && c.retention && c.retention.mode !== "pinned" && Number.isFinite(days) && days <= 3;
      });
      if (expiring.length) {
        privacyExpiringEl.innerHTML = expiring
          .slice(0, 5)
          .map((x) => {
            const target = String(x.repo_path || x.repo_hash || "repo");
            const days = Number(x.retention ? x.retention.days_left : NaN);
            const label = Number.isFinite(days) ? `${Math.max(0, days).toFixed(1)} days` : "soon";
            return `<div class="privacy-warning">This repo cache will be auto-deleted in ${esc(label)}: ${esc(target)}</div>`;
          })
          .join("");
      } else {
        privacyExpiringEl.innerHTML = "<div class='muted'>No caches near expiration.</div>";
      }
    } catch (e) {
      const msg = redactSecrets((e && (e.message || e.error)) || "Failed to load data privacy status");
      privacySummaryEl.textContent = msg;
      privacyExpiringEl.innerHTML = "";
    }
  }

  function showPrivacyConfirm(message, onConfirm) {
    if (!privacyConfirmEl) return;
    privacyConfirmEl.classList.remove("hidden");
    privacyConfirmEl.innerHTML = `
      <div class="privacy-warning">${esc(message)}</div>
      <div class="repo-row-actions">
        <button id="privacy-confirm-yes" class="repo-btn danger" type="button">Confirm</button>
        <button id="privacy-confirm-no" class="repo-btn" type="button">Cancel</button>
      </div>
    `;
    const yesBtn = document.getElementById("privacy-confirm-yes");
    const noBtn = document.getElementById("privacy-confirm-no");
    if (yesBtn) {
      yesBtn.addEventListener("click", async () => {
        privacyConfirmEl.classList.add("hidden");
        privacyConfirmEl.innerHTML = "";
        await onConfirm();
      });
    }
    if (noBtn) {
      noBtn.addEventListener("click", () => {
        privacyConfirmEl.classList.add("hidden");
        privacyConfirmEl.innerHTML = "";
      });
    }
  }

  async function setActiveRepoRetention() {
    const repo = currentRepoEntry();
    if (!repo) {
      if (privacyResultEl) privacyResultEl.textContent = "No active repo selected.";
      return;
    }
    const days = Number(repoRetentionSelectEl && repoRetentionSelectEl.value ? repoRetentionSelectEl.value : 14);
    if (!Number.isFinite(days) || days < 0) {
      if (privacyResultEl) privacyResultEl.textContent = "Select a valid retention value.";
      return;
    }
    try {
      const data = await fetchJson("/api/cache/retention", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          repo_hash: repo.repo_hash,
          days: Math.floor(days),
        }),
      });
      if (privacyResultEl) {
        const ttl = Number(data.days);
        privacyResultEl.textContent = `Retention updated: ${repo.name || repo.repo_hash} -> ${ttl === 0 ? "Never" : `${ttl} days`}`;
      }
      await loadDataPrivacy();
      await loadRepoRegistry();
    } catch (e) {
      if (privacyResultEl) privacyResultEl.textContent = redactSecrets((e && (e.message || e.error)) || "Retention update failed.");
    }
  }

  async function runRetentionCleanup(dryRun, confirmAfterPreview) {
    try {
      const data = await fetchJson("/api/cache/sweep", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          dry_run: !!dryRun,
        }),
      });
      if (!dryRun) {
        if (privacyResultEl) {
          privacyResultEl.textContent = `Cleanup executed: removed ${(data.caches_removed || []).length} caches, freed ~${formatBytes(data.freed_bytes_estimate || 0)}.`;
        }
        await loadDataPrivacy();
        await loadWorkspace();
        return;
      }
      const count = (data.would_delete || []).length;
      if (privacyResultEl) {
        privacyResultEl.textContent = `Dry run: ${count} path(s) would be deleted, freed ~${formatBytes(data.freed_bytes_estimate || 0)}.`;
      }
      if (confirmAfterPreview) {
        showPrivacyConfirm(`Proceed with cleanup of ${count} path(s)?`, async () => {
          await runRetentionCleanup(false, false);
        });
      }
      await loadDataPrivacy();
    } catch (e) {
      if (privacyResultEl) privacyResultEl.textContent = redactSecrets((e && (e.message || e.error)) || "Cleanup failed.");
    }
  }

  async function deleteAllCaches() {
    showPrivacyConfirm("Delete ALL caches and related workspaces?", async () => {
      try {
        const data = await fetchJson("/api/cache/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ all: true, dry_run: false }),
        });
        if (privacyResultEl) {
          privacyResultEl.textContent = `Deleted all caches. Freed ~${formatBytes(data.freed_bytes_estimate || 0)}.`;
        }
        await loadWorkspace();
        await refreshForActiveRepo();
        await loadDataPrivacy();
      } catch (e) {
        if (privacyResultEl) privacyResultEl.textContent = redactSecrets((e && (e.message || e.error)) || "Delete all failed.");
      }
    });
  }

  async function deleteActiveRepoCache() {
    if (!activeRepoHash) {
      if (privacyResultEl) privacyResultEl.textContent = "No active repo selected.";
      return;
    }
    showPrivacyConfirm(`Delete cached data for repo ${activeRepoHash}?`, async () => {
      try {
        const data = await fetchJson("/api/cache/clear", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_hash: activeRepoHash, dry_run: false }),
        });
        if (privacyResultEl) {
          privacyResultEl.textContent = `Deleted cache for ${data.repo_hash}. Freed~${formatBytes(data.freed_bytes_estimate || 0)}`;
        }
        fileCache.clear();
        symbolCache.clear();
        await loadWorkspace();
        await refreshForActiveRepo();
        await loadDataPrivacy();
      } catch (e) {
        if (privacyResultEl) privacyResultEl.textContent = redactSecrets((e && (e.message || e.error)) || "Delete failed.");
      }
    });
  }

  function renderTreeNode(node, parentEl) {
    const li = document.createElement("li");
    const label = document.createElement("span");
    label.className = `tree-item ${node.type === "file" ? "file" : "dir"}`;
    label.textContent = node.type === "file" ? node.name : `${node.name}/`;
    if (node.type === "file") {
      label.setAttribute("data-file-path", node.path || "");
    }
    li.appendChild(label);
    parentEl.appendChild(li);

    if (node.type === "file") {
      label.addEventListener("click", () => loadFile(node.path));
      return;
    }
    const children = node.children || [];
    if (!children.length) return;

    const ul = document.createElement("ul");
    li.appendChild(ul);
    children.forEach((child) => renderTreeNode(child, ul));
  }

  async function loadMeta() {
    try {
      const meta = await fetchJson("/api/meta");
      repoDir = meta.repo_dir || "";
      const fallbackName = String(repoDir || "").replace(/\\/g, "/").split("/").filter(Boolean).pop() || "";
      syncRepoHeader(fallbackName);
      const counts = meta.counts || {};
      metaEl.textContent = `${meta.repo_hash} | symbols ${counts.symbols || 0} | calls ${counts.resolved_calls || 0}`;
      return true;
    } catch (e) {
      const msg = redactSecrets((e && (e.message || e.error)) || "Metadata unavailable");
      syncRepoHeader();
      metaEl.textContent = msg;
      recentSymbols = [];
      recentFiles = [];
      lastSymbol = "";
      renderRecents();
      clearWorkspaceView(msg);
      if (e && String(e.error || "") === "CACHE_NOT_FOUND") {
        showMissingAnalysisState(msg);
      }
      return false;
    }
  }

  async function loadTree() {
    treeStatusEl.textContent = "";
    try {
      const data = await fetchJson("/api/tree");
      const tree = normalizeTree(data);
      treeEl.innerHTML = "";
      const ul = document.createElement("ul");
      treeEl.appendChild(ul);
      renderTreeNode(tree, ul);
      highlightActiveFile();
      return true;
    } catch (e) {
      treeEl.innerHTML = "";
      treeStatusEl.textContent = redactSecrets((e && (e.error || e.message)) || "Failed to load tree");
      if (e && String(e.error || "") === "CACHE_NOT_FOUND") {
        showMissingAnalysisState(redactSecrets((e && (e.message || e.error)) || "Missing analysis"));
      }
      return false;
    }
  }

  function renderSymbolGroup(symbols) {
    const classes = (symbols && symbols.classes) || [];
    const functions = (symbols && symbols.functions) || [];
    const moduleScope = (symbols && symbols.module_scope) || null;
    const hasScriptOnly = moduleScope && classes.length === 0 && functions.length === 0;

    const moduleHtml = moduleScope
      ? `<div class="block">
          <div class="section-title">Module Scope</div>
          <div>
            <span class="symbol-link ${moduleScope.fqn === activeSymbolFqn ? "active" : ""}" data-fqn="${esc(moduleScope.fqn)}">&lt;module&gt;</span>
            <span class="path">(${esc(moduleScope.outgoing_calls_count)} outgoing calls)</span>
          </div>
          ${hasScriptOnly ? "<div class='muted'>This file is a script with module-level code. Select &lt;module&gt; to inspect calls.</div>" : ""}
        </div>`
      : "";

    const classHtml = classes.length
      ? classes.map((c) => `
        <div class="symbol-class" data-class-name="${esc(c.name)}">
          <div class="symbol-name symbol-class-name">${esc(c.name)}</div>
          <div class="symbol-methods">
            ${(c.methods || []).map((m) => `
              <div class="symbol-method-row">
                <span class="method-prefix">|-</span>
                <span class="symbol-link ${m === activeSymbolFqn ? "active" : ""}" data-fqn="${esc(m)}">${esc(m.split(".").slice(-1)[0])}</span>
              </div>
            `).join("")}
          </div>
        </div>`).join("")
      : "<div class='muted'>None</div>";

    const fnHtml = functions.length
      ? functions.map((f) => `<div><span class="symbol-link ${f === activeSymbolFqn ? "active" : ""}" data-fqn="${esc(f)}">${esc(f.split(".").slice(-1)[0])}</span></div>`).join("")
      : "<div class='muted'>None</div>";

    return `
      ${moduleHtml}
      <div class="section-title">Classes</div>
      ${classHtml}
      <div class="section-title">Functions</div>
      ${fnHtml}
    `;
  }

  function bindSymbolLinks(container) {
    container.querySelectorAll(".symbol-link").forEach((el) => {
      el.addEventListener("click", () => loadSymbol(el.getAttribute("data-fqn")));
    });
  }

  function bindConnectionLinks(container) {
    container.querySelectorAll(".connection-link").forEach((el) => {
      el.addEventListener("click", () => loadSymbol(el.getAttribute("data-fqn")));
    });
  }

  function bindBreadcrumbs(container, currentFqn) {
    container.querySelectorAll(".crumb-link").forEach((el) => {
      const action = el.getAttribute("data-action");
      const value = el.getAttribute("data-value");
      el.addEventListener("click", async () => {
        if (action === "file" && value) {
          await loadFile(value);
          return;
        }
        if (action === "class" && value) {
          scrollClassIntoView(value);
          return;
        }
        if (action === "symbol" && value) {
          await loadSymbol(value);
          return;
        }
        if (action === "repo" && activeFilePath) {
          await loadFile(activeFilePath);
          return;
        }
        if (currentFqn) {
          await loadSymbol(currentFqn);
        }
      });
    });
  }

  function bindConnectionChips(container) {
    container.querySelectorAll(".chip").forEach((el) => {
      el.addEventListener("click", () => {
        const targetId = el.getAttribute("data-target");
        const target = targetId ? container.querySelector(`#${targetId}`) : null;
        if (target) target.scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
  }

  function scrollClassIntoView(className) {
    if (!className) return;
    const target = fileViewEl.querySelector(`.symbol-class[data-class-name="${CSS.escape(className)}"]`);
    if (target) {
      target.scrollIntoView({ block: "nearest", behavior: "smooth" });
      const classLabel = target.querySelector(".symbol-class-name");
      if (classLabel) {
        classLabel.classList.add("active-class");
        window.setTimeout(() => classLabel.classList.remove("active-class"), 800);
      }
    }
  }

  function highlightActiveSymbol() {
    const links = fileViewEl.querySelectorAll(".symbol-link");
    links.forEach((el) => {
      const isActive = el.getAttribute("data-fqn") === activeSymbolFqn;
      el.classList.toggle("active", isActive);
      if (isActive) {
        el.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }

  function highlightActiveFile() {
    const links = treeEl.querySelectorAll(".tree-item.file");
    links.forEach((el) => {
      const isActive = el.getAttribute("data-file-path") === activeFilePath;
      el.classList.toggle("active-file", isActive);
      if (isActive) {
        el.scrollIntoView({ block: "nearest", behavior: "smooth" });
      }
    });
  }

  function closeSearchDropdown() {
    searchResultsEl.classList.add("hidden");
    searchResultsEl.innerHTML = "";
    currentSearchResults = [];
  }

  function renderSearchResults(results, truncated) {
    currentSearchResults = results || [];
    if (!currentSearchResults.length) {
      searchResultsEl.classList.add("hidden");
      searchResultsEl.innerHTML = "";
      return;
    }

    const rows = currentSearchResults.map((r) => `
      <button class="search-row" data-fqn="${esc(r.fqn)}" data-file="${esc(r.file)}">
        <div class="search-primary">${esc(r.display)}</div>
        <div class="search-secondary">${esc(r.module)}${r.file ? ` | ${esc(r.file)}:${esc(r.line)}` : ""}</div>
      </button>
    `).join("");

    searchResultsEl.innerHTML = `
      ${rows}
      ${truncated ? "<div class='search-more'>Showing first 20...</div>" : ""}
    `;
    searchResultsEl.classList.remove("hidden");

    searchResultsEl.querySelectorAll(".search-row").forEach((row) => {
      row.addEventListener("click", async () => {
        await selectSearchResult({
          fqn: row.getAttribute("data-fqn"),
          file: row.getAttribute("data-file"),
        });
      });
    });
  }

  async function runSymbolSearch(query) {
    const q = String(query || "").trim();
    if (!q) {
      closeSearchDropdown();
      return;
    }
    try {
      const data = await fetchJson(`/api/search?q=${encodeURIComponent(q)}&limit=20`);
      renderSearchResults(data.results || [], !!data.truncated);
    } catch (_e) {
      closeSearchDropdown();
    }
  }

  async function selectSearchResult(item) {
    closeSearchDropdown();
    if (!item || !item.fqn) return;
    if (item.file) {
      await loadFile(item.file);
    }
    await loadSymbol(item.fqn);
  }

  function bindSearchInput() {
    if (!searchInputEl) return;
    searchInputEl.addEventListener("input", () => {
      if (searchTimer) clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        runSymbolSearch(searchInputEl.value);
      }, 200);
    });

    searchInputEl.addEventListener("keydown", async (e) => {
      if (e.key === "Escape") {
        closeSearchDropdown();
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (currentSearchResults.length > 0) {
          await selectSearchResult(currentSearchResults[0]);
        }
      }
    });
  }

  function bindWorkspaceControls() {
    if (repoSelectEl) {
      repoSelectEl.addEventListener("change", async () => {
        const selected = repoSelectEl.value;
        if (selected && selected !== activeRepoHash) {
          await selectWorkspace(selected);
        }
      });
    }
    if (addRepoBtnEl) {
      addRepoBtnEl.addEventListener("click", async () => {
        await addWorkspaceRepo();
      });
    }
  }

  function bindAiSettingsControls() {
    if (aiSettingsBtnEl) {
      aiSettingsBtnEl.addEventListener("click", async () => {
        await openAiSettingsModal();
      });
    }
    if (aiSettingsCancelEl) {
      aiSettingsCancelEl.addEventListener("click", () => closeAiSettingsModal());
    }
    if (aiSettingsRememberReposEl) {
      aiSettingsRememberReposEl.addEventListener("change", async () => {
        await setRememberRepos(!!aiSettingsRememberReposEl.checked);
      });
    }
    if (aiSettingsClearReposEl) {
      aiSettingsClearReposEl.addEventListener("click", async () => {
        await clearRepositoryList();
      });
    }
    if (aiSettingsModalEl) {
      aiSettingsModalEl.addEventListener("click", (e) => {
        if (e.target === aiSettingsModalEl) closeAiSettingsModal();
      });
    }
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && aiSettingsModalEl && !aiSettingsModalEl.classList.contains("hidden")) {
        closeAiSettingsModal();
      }
    });
  }

  let repoInlineBound = false;
  let repoAddInFlight = false;
  let repoAddAbortController = null;
  const DEBUG_CONFIRM = false;
  if (!window.confirmState || typeof window.confirmState !== "object") {
    window.confirmState = { open: false, actionType: null, payload: null };
  }
  let confirmResolve = null;
  let confirmRunAction = null;
  let confirmKeydownHandler = null;
  let confirmBackdropHandler = null;
  let confirmPanelHandler = null;
  let confirmYesHandler = null;
  let confirmNoHandler = null;

  function showToast(message, type) {
    if (!toastEl) return;
    toastEl.textContent = redactSecrets(String(message || ""));
    toastEl.classList.remove("hidden", "error");
    if (String(type || "") === "error") toastEl.classList.add("error");
    window.setTimeout(() => {
      toastEl.classList.add("hidden");
    }, 2200);
  }

  function confirmLog(label, payload) {
    if (!DEBUG_CONFIRM) return;
    try {
      console.log(`[confirm] ${label}`, payload || {});
    } catch (_e) {
      // no-op
    }
  }

  function teardownConfirmModalHandlers() {
    if (!confirmModalEl) return;
    const panel = confirmModalEl.querySelector(".confirm-card");
    const yesBtn = confirmModalEl.querySelector("#confirm-yes");
    const noBtn = confirmModalEl.querySelector("#confirm-no");
    if (confirmBackdropHandler) {
      confirmModalEl.removeEventListener("click", confirmBackdropHandler);
      confirmBackdropHandler = null;
    }
    if (panel && confirmPanelHandler) {
      panel.removeEventListener("click", confirmPanelHandler);
      confirmPanelHandler = null;
    }
    if (yesBtn && confirmYesHandler) {
      yesBtn.removeEventListener("click", confirmYesHandler);
      confirmYesHandler = null;
    }
    if (noBtn && confirmNoHandler) {
      noBtn.removeEventListener("click", confirmNoHandler);
      confirmNoHandler = null;
    }
    if (confirmKeydownHandler) {
      document.removeEventListener("keydown", confirmKeydownHandler);
      confirmKeydownHandler = null;
    }
  }

  function renderConfirmModal(title, message) {
    if (!confirmModalEl || !confirmTitleEl || !confirmMessageEl) return;
    confirmTitleEl.textContent = String(title || "Confirm action");
    confirmMessageEl.textContent = redactSecrets(String(message || ""));
    const open = !!(window.confirmState && window.confirmState.open);
    confirmModalEl.classList.toggle("hidden", !open);
    document.body.classList.toggle("modal-open", open);
  }

  function closeConfirmModal(result) {
    confirmLog("close", { result });
    if (!confirmModalEl) return;
    teardownConfirmModalHandlers();
    window.confirmState = { open: false, actionType: null, payload: null };
    confirmRunAction = null;
    renderConfirmModal("", "");
    const resolver = confirmResolve;
    confirmResolve = null;
    if (typeof resolver === "function") resolver(!!result);
  }

  function openConfirmModal({ title, message, confirmText, cancelText, actionType, payload, onConfirm }) {
    if (!confirmModalEl) {
      return Promise.resolve(window.confirm(String(message || "Are you sure?")));
    }
    window.confirmState = {
      open: true,
      actionType: actionType || null,
      payload: payload || null,
    };
    confirmRunAction = typeof onConfirm === "function" ? onConfirm : null;
    renderConfirmModal(title, message);
    teardownConfirmModalHandlers();

    const panel = confirmModalEl.querySelector(".confirm-card");
    const yesBtn = confirmModalEl.querySelector("#confirm-yes");
    const noBtn = confirmModalEl.querySelector("#confirm-no");
    if (yesBtn) yesBtn.textContent = String(confirmText || "Yes");
    if (noBtn) noBtn.textContent = String(cancelText || "Cancel");

    confirmNoHandler = () => {
      confirmLog("cancel", { actionType: window.confirmState.actionType });
      closeConfirmModal(false);
    };
    confirmYesHandler = async () => {
      confirmLog("yes", { actionType: window.confirmState.actionType });
      let ok = true;
      try {
        if (confirmRunAction) {
          await confirmRunAction();
        }
      } catch (e) {
        ok = false;
        showToast(redactSecrets((e && (e.message || e.error)) || "Action failed"), "error");
      } finally {
        closeConfirmModal(ok);
      }
    };
    confirmBackdropHandler = (e) => {
      if (e.target === confirmModalEl) {
        confirmLog("backdrop", { actionType: window.confirmState.actionType });
        closeConfirmModal(false);
      }
    };
    confirmPanelHandler = (e) => {
      e.stopPropagation();
    };
    confirmKeydownHandler = (e) => {
      if (e.key === "Escape" && window.confirmState.open) {
        confirmLog("escape", { actionType: window.confirmState.actionType });
        closeConfirmModal(false);
      }
    };

    if (noBtn) noBtn.addEventListener("click", confirmNoHandler);
    if (yesBtn) yesBtn.addEventListener("click", confirmYesHandler);
    confirmModalEl.addEventListener("click", confirmBackdropHandler);
    if (panel) panel.addEventListener("click", confirmPanelHandler);
    document.addEventListener("keydown", confirmKeydownHandler);

    confirmLog("open", {
      actionType: window.confirmState.actionType,
      payload: window.confirmState.payload || {},
    });

    return new Promise((resolve) => {
      // Replace any pending unresolved confirm with a safe cancel.
      if (typeof confirmResolve === "function") {
        try { confirmResolve(false); } catch (_e) {}
      }
      confirmResolve = resolve;
    });
  }

  function updatePrivateModeIndicator() {
    if (!privateModeIndicatorEl) return;
    const hasToken = !!(ghTokenEl && String(ghTokenEl.value || "").trim());
    const checked = !!(ghPrivateModeEl && ghPrivateModeEl.checked);
    privateModeIndicatorEl.classList.toggle("hidden", !(hasToken || checked));
  }

  function setRepoPanelTab(tab) {
    const local = tab !== "github";
    if (repoTabLocalEl) repoTabLocalEl.classList.toggle("active", local);
    if (repoTabGithubEl) repoTabGithubEl.classList.toggle("active", !local);
    if (repoFormLocalEl) repoFormLocalEl.classList.toggle("hidden", !local);
    if (repoFormGithubEl) repoFormGithubEl.classList.toggle("hidden", local);
    validateRepoPanel();
  }

  function resetRepoPanelState() {
    if (localRepoPathEl) localRepoPathEl.value = "";
    if (localDisplayNameEl) localDisplayNameEl.value = "";
    if (ghRepoUrlEl) ghRepoUrlEl.value = "";
    if (ghRefEl) ghRefEl.value = "main";
    if (ghModeEl) ghModeEl.value = "zip";
    if (ghTokenEl) ghTokenEl.value = "";
    if (ghPrivateModeEl) ghPrivateModeEl.checked = false;
    updatePrivateModeIndicator();
    if (repoModalErrorEl) repoModalErrorEl.textContent = "";
    repoAddInFlight = false;
    repoAddAbortController = null;
    setRepoPanelLoading(false);
  }

  function setRepoPanelLoading(isLoading) {
    if (repoAddBtnEl) {
      repoAddBtnEl.disabled = !!isLoading;
      repoAddBtnEl.textContent = isLoading ? "Adding..." : "Add repo";
      repoAddBtnEl.classList.toggle("is-loading", !!isLoading);
    }
    if (repoCancelBtnEl) repoCancelBtnEl.disabled = false;
    if (repoInlineCloseEl) repoInlineCloseEl.disabled = false;
    validateRepoPanel();
  }

  function validateRepoPanel() {
    const githubActive = repoFormGithubEl && !repoFormGithubEl.classList.contains("hidden");
    let valid = false;
    let message = "";
    if (githubActive) {
      const url = String(ghRepoUrlEl && ghRepoUrlEl.value ? ghRepoUrlEl.value : "").trim();
      const ok = /^https:\/\/github\.com\/[^\/\s]+\/[^\/\s]+\/?(\.git)?$/i.test(url) || /^https:\/\/github\.com\/[^\/\s]+\/[^\/\s]+(\.git)?$/i.test(url);
      valid = !!url && ok;
      if (url && !ok) message = "Invalid GitHub URL.";
    } else {
      const path = String(localRepoPathEl && localRepoPathEl.value ? localRepoPathEl.value : "").trim();
      valid = !!path;
      if (!path) message = "Local path is required.";
    }
    if (repoModalErrorEl && !repoAddInFlight) repoModalErrorEl.textContent = redactSecrets(message);
    if (repoAddBtnEl) repoAddBtnEl.disabled = repoAddInFlight || !valid;
    return valid;
  }

  function openRepoPanel(tab) {
    if (!addRepoInlineEl) return;
    resetRepoPanelState();
    addRepoInlineEl.classList.remove("hidden");
    setRepoPanelTab(tab || "local");
    if (localRepoPathEl) localRepoPathEl.focus();
  }

  function closeRepoPanel(force) {
    if (!addRepoInlineEl) return;
    if (repoAddInFlight && !force) {
      const shouldClose = window.confirm("Request in progress. Close anyway?");
      if (!shouldClose) return;
      if (repoAddAbortController) {
        try { repoAddAbortController.abort(); } catch (_e) {}
      }
    }
    addRepoInlineEl.classList.add("hidden");
    resetRepoPanelState();
  }

  async function runAddRepository() {
    if (!validateRepoPanel()) return;
    const githubActive = repoFormGithubEl && !repoFormGithubEl.classList.contains("hidden");

    repoAddInFlight = true;
    repoAddAbortController = new AbortController();
    setRepoPanelLoading(true);
    if (repoModalErrorEl) repoModalErrorEl.textContent = "";

    try {
      let data;
      let privateModeRequested = false;
      if (githubActive) {
        const repoUrl = String(ghRepoUrlEl && ghRepoUrlEl.value ? ghRepoUrlEl.value : "").trim();
        const ref = String(ghRefEl && ghRefEl.value ? ghRefEl.value : "main").trim() || "main";
        const mode = String(ghModeEl && ghModeEl.value ? ghModeEl.value : "zip").trim() || "zip";
        const token = String(ghTokenEl && ghTokenEl.value ? ghTokenEl.value : "").trim();
        privateModeRequested = !!(token || (ghPrivateModeEl && ghPrivateModeEl.checked));
        const displayName = "";
        data = await fetchJson("/api/registry/repos/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            source: "github",
            repo_url: repoUrl,
            ref,
            mode,
            display_name: displayName,
            open_after_add: true,
            private_mode: privateModeRequested,
          }),
          signal: repoAddAbortController.signal,
        });
      } else {
        const repoPath = String(localRepoPathEl && localRepoPathEl.value ? localRepoPathEl.value : "").trim();
        const displayName = String(localDisplayNameEl && localDisplayNameEl.value ? localDisplayNameEl.value : "").trim();
        data = await fetchJson("/api/registry/repos/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ source: "filesystem", repo_path: repoPath, display_name: displayName, open_after_add: true }),
          signal: repoAddAbortController.signal,
        });
      }

      const addedName = (data && data.repo && data.repo.name) ? data.repo.name : "Repository";
      showToast(`Repo added: ${addedName}`, "success");
      closeRepoPanel(true);

      // Refresh/selection updates run after close so modal never blocks app interaction.
      try {
        await loadWorkspace();
        await loadRepoRegistry();
        if (data.repo_hash) await selectWorkspace(data.repo_hash);
        setActiveTab("details");
        if (data.repo_hash && privateModeRequested) {
          showToast("Private mode enabled. Default retention set to 7 days after analysis.", "success");
        }
      } catch (_postSuccessErr) {
        // Keep app usable; repo add already succeeded.
      }
    } catch (e) {
      if (repoModalErrorEl) repoModalErrorEl.textContent = redactSecrets((e && (e.message || e.error)) || "Failed to add repository.");
      showToast(redactSecrets((e && (e.message || e.error)) || "Failed to add repository."), "error");
    } finally {
      if (ghTokenEl) ghTokenEl.value = "";
      updatePrivateModeIndicator();
      repoAddInFlight = false;
      repoAddAbortController = null;
      setRepoPanelLoading(false);
    }
  }

  function bindDataPrivacyControls() {
    try {
      autoCleanOnRemove = window.localStorage.getItem("codemap_auto_clean_on_remove") === "1";
    } catch (_e) {
      autoCleanOnRemove = false;
    }
    if (autoCleanOnRemoveEl) {
      autoCleanOnRemoveEl.checked = !!autoCleanOnRemove;
      if (autoCleanNoteEl) autoCleanNoteEl.classList.toggle("hidden", !autoCleanOnRemove);
      autoCleanOnRemoveEl.addEventListener("change", () => {
        autoCleanOnRemove = !!autoCleanOnRemoveEl.checked;
        if (autoCleanNoteEl) autoCleanNoteEl.classList.toggle("hidden", !autoCleanOnRemove);
        try {
          window.localStorage.setItem("codemap_auto_clean_on_remove", autoCleanOnRemove ? "1" : "0");
        } catch (_e) {
          // ignore
        }
      });
    }
    if (repoRetentionSaveBtnEl) {
      repoRetentionSaveBtnEl.addEventListener("click", () => {
        setActiveRepoRetention();
      });
    }
    if (cleanupDryBtnEl) {
      cleanupDryBtnEl.addEventListener("click", () => {
        runRetentionCleanup(true, false);
      });
    }
    if (cleanupNowBtnEl) {
      cleanupNowBtnEl.addEventListener("click", () => {
        runRetentionCleanup(true, true);
      });
    }
    if (deleteRepoCacheBtnEl) {
      deleteRepoCacheBtnEl.addEventListener("click", () => {
        deleteActiveRepoCache();
      });
    }
    if (deleteAllCachesBtnEl) {
      deleteAllCachesBtnEl.addEventListener("click", () => {
        deleteAllCaches();
      });
    }
  }

  function bindRepoInlineControls() {
    if (repoInlineBound) return;
    repoInlineBound = true;
    if (repoInlineCloseEl) repoInlineCloseEl.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      closeRepoPanel(false);
    });
    if (repoCancelBtnEl) repoCancelBtnEl.addEventListener("click", (e) => {
      e.preventDefault();
      closeRepoPanel(false);
    });
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && addRepoInlineEl && !addRepoInlineEl.classList.contains("hidden")) {
        closeRepoPanel(false);
      }
    });
    if (repoTabLocalEl) repoTabLocalEl.addEventListener("click", () => setRepoPanelTab("local"));
    if (repoTabGithubEl) repoTabGithubEl.addEventListener("click", () => setRepoPanelTab("github"));
    if (repoAddBtnEl) repoAddBtnEl.addEventListener("click", () => runAddRepository());
    if (localRepoPathEl) localRepoPathEl.addEventListener("input", () => validateRepoPanel());
    if (ghRepoUrlEl) ghRepoUrlEl.addEventListener("input", () => validateRepoPanel());
    if (ghTokenEl) ghTokenEl.addEventListener("input", () => updatePrivateModeIndicator());
    if (ghPrivateModeEl) ghPrivateModeEl.addEventListener("change", () => updatePrivateModeIndicator());
  }

  function bindGraphControls() {
    if (tabDetailsEl) tabDetailsEl.addEventListener("click", () => setActiveTab("details"));
    if (tabImpactEl) tabImpactEl.addEventListener("click", () => setActiveTab("impact"));
    if (tabGraphEl) tabGraphEl.addEventListener("click", () => setActiveTab("graph"));
    if (tabArchitectureEl) tabArchitectureEl.addEventListener("click", () => setActiveTab("architecture"));
    const rerender = () => {
      graphDataCache.clear();
      if (activeTab === "graph") loadGraph();
    };
    if (graphModeEl) graphModeEl.addEventListener("change", rerender);
    if (graphDepthEl) graphDepthEl.addEventListener("change", rerender);
    if (graphHideBuiltinsEl) graphHideBuiltinsEl.addEventListener("change", rerender);
    if (graphHideExternalEl) graphHideExternalEl.addEventListener("change", rerender);
    if (graphSearchEl) graphSearchEl.addEventListener("input", () => {
      if (activeTab === "graph") {
        const p = graphParams();
        const graphMode = p.mode === "file" ? "file" : "symbol";
        const anchor = graphMode === "file" ? activeFilePath : activeSymbolFqn;
        const key = `${graphMode}|${anchor}|${p.depth}|${p.hideBuiltins}|${p.hideExternal}`;
        const cached = graphDataCache.get(key);
        if (cached) renderGraphData(cached);
      }
    });
    const rerenderImpact = () => {
      impactDataCache.clear();
      if (activeTab === "impact") loadImpact();
    };
    if (impactDepthEl) impactDepthEl.addEventListener("change", rerenderImpact);
    if (impactMaxNodesEl) impactMaxNodesEl.addEventListener("change", rerenderImpact);
  }

  async function loadFile(relFilePath) {
    activeFilePath = relFilePath;
    highlightActiveFile();
    graphDataCache.clear();
    impactDataCache.clear();
    fileViewEl.classList.remove("muted");
    fileViewEl.textContent = "Loading file intelligence...";
    try {
      let data = fileCache.get(relFilePath);
      if (!data) {
        data = await fetchJson(`/api/file?path=${encodeURIComponent(relFilePath)}`);
        fileCache.set(relFilePath, data);
      }

      fileViewEl.innerHTML = `
        <div class="card">
          <div class="line"><span class="label">File</span><span class="path">${esc(data.file)}</span></div>
          <div class="line"><span class="label">Incoming usages</span><span>${data.incoming_usages_count}</span></div>
          <div class="line"><span class="label">Outgoing calls</span><span>${data.outgoing_calls_count}</span></div>
        </div>
        <div class="card">
          ${renderSymbolGroup(data.symbols)}
        </div>
      `;

      bindSymbolLinks(fileViewEl);
      highlightActiveSymbol();
      highlightActiveFile();
      await updateUiState({ opened_file: relFilePath });
      if (activeTab === "graph" && graphParams().mode === "file") {
        await loadGraph();
      }
    } catch (e) {
      const errCode = String((e && e.error) || "");
      if (errCode === "MISSING_ANALYSIS" || errCode === "CACHE_NOT_FOUND") {
        fileViewEl.classList.remove("muted");
        fileViewEl.innerHTML = renderMissingAnalysisCta("Run Analyze first to load file intelligence.");
        bindRunAnalysisNowButton();
        return;
      }
      fileViewEl.classList.add("muted");
      fileViewEl.textContent = redactSecrets((e && (e.error || e.message)) || "Failed to load file intelligence");
    }
  }

  function delay(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  function renderEmptyState(text) {
    return `<div class="empty-state">OK ${esc(text)}</div>`;
  }

  function showSymbolLoading() {
    symbolViewEl.classList.remove("muted");
    symbolViewEl.innerHTML = `
      <div class="card shimmer-card">
        <div class="shimmer-line w60"></div>
        <div class="shimmer-line w90"></div>
        <div class="shimmer-line w75"></div>
      </div>
    `;
    const panel = symbolViewEl.closest(".panel");
    if (panel) panel.scrollTo({ top: 0, behavior: "smooth" });
  }

  function renderConnectionBlock(items, renderer, emptyText) {
    if (!items || !items.length) {
      return renderEmptyState(emptyText);
    }
    return items.map(renderer).join("");
  }


  async function loadSymbol(fqn) {
    activeSymbolFqn = fqn;
    highlightActiveSymbol();
    graphDataCache.clear();
    impactDataCache.clear();
    showSymbolLoading();
    try {
      const symbolPromise = (async () => {
        let symbolData = symbolCache.get(fqn);
        if (!symbolData) {
          symbolData = await fetchJson(`/api/symbol?fqn=${encodeURIComponent(fqn)}`);
          symbolCache.set(fqn, symbolData);
        }
        return symbolData;
      })();

      const [symbolData] = await Promise.all([symbolPromise, delay(150)]);

      const result = symbolData.result || {};
      const loc = result.location || {};
      const relFile = relPath(loc.file || "");
      if (relFile && relFile !== activeFilePath) {
        await loadFile(relFile);
      }

      const summary = stripMarkdown(result.one_liner || "");
      const notes = (result.details || []).filter((d) => String(d).startsWith("Returns:")).slice(0, 3).map(stripMarkdown);
      const symbolParts = parseSymbolParts(result.fqn || fqn);
      const locationText = `${relFile}:${loc.start_line || ""}`;
      const connections = result.connections || {};
      const calledBy = connections.called_by || [];
      const calls = connections.calls || [];
      const usedIn = (connections.used_in || []).slice().sort((a, b) => (a.file || "").localeCompare(b.file || ""));

      const crumbs = [
        { label: repoName || "repo", action: "repo", value: "" },
        { label: relFile, action: "file", value: relFile },
      ];
      if (symbolParts.className) {
        crumbs.push({ label: symbolParts.className, action: "class", value: symbolParts.className });
      }
      crumbs.push({ label: symbolParts.symbol, action: "symbol", value: result.fqn || fqn });

      symbolViewEl.innerHTML = `
        <div class="card symbol-card fade-panel">
          <div class="breadcrumbs">
            ${crumbs.map((c) => `<span class="crumb-link" data-action="${esc(c.action)}" data-value="${esc(c.value)}">${esc(c.label)}</span>`).join("<span class='crumb-sep'>></span>")}
          </div>
          <div class="chips">
            <button class="chip" data-target="called-by-section">Called by: ${calledBy.length}</button>
            <button class="chip" data-target="calls-section">Calls: ${calls.length}</button>
            <button class="chip" data-target="used-in-section">Used in: ${usedIn.length}</button>
          </div>
          <div class="symbol-title-main">${esc(symbolParts.display)}</div>
          <div class="path">FQN: ${esc(result.fqn || fqn)}</div>
          <div class="path">${esc(locationText)}</div>
          <div class="divider"></div>
          <div class="section-title">Summary</div>
          <div>${esc(summary)}</div>
          <div id="called-by-section" class="divider"></div>
          <div class="section-title">Called by</div>
          ${renderConnectionBlock(calledBy, (c) => `
            <div>
              <span class="conn-arrow">-></span><span class="connection-link" data-fqn="${esc(c.fqn)}">${esc(c.fqn)}</span>
              <span class="path">${esc(c.file)}:${esc(c.line)}</span>
            </div>
          `, "No callers found")}
          <div id="calls-section" class="divider"></div>
          <div class="section-title">Calls</div>
          ${renderConnectionBlock(calls, (c) => `
            <div>
              ${c.clickable
                ? `<span class="conn-arrow">-></span><span class="connection-link" data-fqn="${esc(c.fqn)}">${esc(c.name)}</span>`
                : `<span class="connection-muted">${esc(c.name)}</span>`
              }
              <span class="path">(${esc(c.count)}x)</span>
            </div>
          `, "No calls found")}
          <div class="divider"></div>
          <div class="section-title">Top Callees</div>
          ${renderConnectionBlock(calls.slice(0, 10), (c) => `
            <div>
              <span class="${c.clickable ? "connection-link" : "connection-muted"}" ${c.clickable ? `data-fqn="${esc(c.fqn)}"` : ""}>${esc(c.name)}</span>
              <span class="path">(${esc(c.count)}x)</span>
            </div>
          `, "No callees found")}
          <div id="used-in-section" class="divider"></div>
          <div class="section-title">Used in</div>
          ${renderConnectionBlock(usedIn, (u) => `
            <div>
              <span class="conn-arrow">-></span><span class="connection-link" data-fqn="${esc(u.fqn)}">${esc(u.fqn)}</span>
              <span class="path">${esc(u.file)}:${esc(u.line)}</span>
            </div>
          `, "No usages found")}
          <div class="divider"></div>
          <div class="section-title">Notes</div>
          ${notes.length ? notes.map((n) => `<div>${esc(n)}</div>`).join("") : "<div class='muted'>None</div>"}
        </div>
      `;

      bindConnectionLinks(symbolViewEl);
      bindBreadcrumbs(symbolViewEl, result.fqn || fqn);
      bindConnectionChips(symbolViewEl);
      highlightActiveSymbol();
      await updateUiState({ opened_symbol: (result.fqn || fqn), last_symbol: (result.fqn || fqn) });
      if (activeTab === "graph" && graphParams().mode === "symbol") {
        await loadGraph(result.fqn || fqn);
      }
      if (activeTab === "impact") {
        await loadImpact(result.fqn || fqn);
      }
    } catch (e) {
      const errCode = String((e && e.error) || "");
      if (errCode === "MISSING_ANALYSIS" || errCode === "CACHE_NOT_FOUND") {
        symbolViewEl.classList.remove("muted");
        symbolViewEl.innerHTML = renderMissingAnalysisCta("Run Analyze first to unlock symbol intelligence.");
        bindRunAnalysisNowButton();
        return;
      }
      symbolViewEl.classList.add("muted");
      symbolViewEl.textContent = redactSecrets((e && (e.error || e.message)) || "Failed to load symbol intelligence");
    }
  }

  async function refreshForActiveRepo() {
    clearWorkspaceView("Loading workspace...");
    architectureCache = null;
    symbolAiSummaryCache.clear();
    repoSummary = null;
    repoSummaryUpdatedAt = "";
    repoSummaryStatus = "idle";
    repoSummaryError = "";
    riskRadar = null;
    riskRadarUpdatedAt = "";
    riskRadarStatus = "idle";
    riskRadarError = "";
    await loadRepoRegistry();
    const okMeta = await loadMeta();
    await loadDataPrivacy();
    if (!okMeta) return;
    await loadTree();
    await loadUiState();
    if (lastSymbol) {
      await loadSymbol(lastSymbol);
      return;
    }
    if (recentFiles.length) {
      await loadFile(recentFiles[0]);
    }
  }

  async function init() {
    bindSearchInput();
    bindWorkspaceControls();
    bindAiSettingsControls();
    bindRepoInlineControls();
    bindDataPrivacyControls();
    bindGraphControls();
    setActiveTab("details");
    try {
      await loadWorkspace();
      await refreshForActiveRepo();
    } catch (e) {
      metaEl.textContent = redactSecrets((e && (e.message || e.error)) || "Workspace unavailable");
      clearWorkspaceView(metaEl.textContent);
    }
  }

  init();
})();

