"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ServerManager = void 0;
exports.parseDashboardPort = parseDashboardPort;
exports.workspaceSecretKey = workspaceSecretKey;
exports.workspaceGithubSecretKey = workspaceGithubSecretKey;
exports.scanDirectoryForMarker = scanDirectoryForMarker;
const crypto = require("crypto");
const fs = require("fs");
const net = require("net");
const path = require("path");
const vscode = require("vscode");
const child_process_1 = require("child_process");
const apiClient_1 = require("../apiClient");
const instanceDir_1 = require("../instanceDir");
const redact_1 = require("../redact");
const pythonBootstrap_1 = require("./pythonBootstrap");
function parseDashboardPort(line) {
    const match = String(line || "").match(/http:\/\/127\.0\.0\.1:(\d+)/i);
    if (!match) {
        return null;
    }
    const parsed = Number(match[1]);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}
function workspaceSecretKey(workspaceHash, name) {
    const hash = String(workspaceHash || "").trim();
    const slot = String(name || "").trim();
    return `codemap.ai.${slot}.${hash}`;
}
function workspaceGithubSecretKey(workspaceHash) {
    const hash = String(workspaceHash || "").trim();
    return `codemap.github.token.${hash}`;
}
function scanDirectoryForMarker(rootDir, marker) {
    const target = String(marker || "").trim();
    if (!target) {
        return false;
    }
    const root = String(rootDir || "").trim();
    if (!root || !fs.existsSync(root) || !fs.statSync(root).isDirectory()) {
        return false;
    }
    const stack = [root];
    while (stack.length) {
        const current = stack.pop();
        let entries = [];
        try {
            entries = fs.readdirSync(current, { withFileTypes: true });
        }
        catch {
            continue;
        }
        for (const entry of entries) {
            const full = path.join(current, entry.name);
            if (entry.isDirectory()) {
                stack.push(full);
                continue;
            }
            if (!entry.isFile()) {
                continue;
            }
            try {
                const data = fs.readFileSync(full, "utf-8");
                if (data.includes(target)) {
                    return true;
                }
            }
            catch {
                // ignore binary or unreadable files
            }
        }
    }
    return false;
}
async function isPortAvailable(port) {
    return new Promise((resolve) => {
        const server = net.createServer();
        server.once("error", () => resolve(false));
        server.once("listening", () => {
            server.close(() => resolve(true));
        });
        server.listen(port, "127.0.0.1");
    });
}
function nowIso() {
    return new Date().toISOString();
}
class ServerManager {
    constructor(context, output, statusBar) {
        this.proc = null;
        this.port = null;
        this.api = null;
        this.logStream = null;
        this.dashboardPanel = null;
        this.context = context;
        this.output = output;
        this.statusBar = statusBar;
        this.repoRoot = path.resolve(context.extensionUri.fsPath, "..");
        this.layout = (0, instanceDir_1.resolveInstanceLayout)(context);
        this.statePath = this.layout.statePath;
        this.logPath = path.join(this.layout.logsDir, "server.log");
        this.sessionId = `vs_${crypto.createHash("sha256").update(`${this.layout.workspaceHash}:session`).digest("hex").slice(0, 24)}`;
        this.clientId = `vscode_${this.layout.workspaceHash.slice(0, 16)}`;
        fs.mkdirSync(this.layout.instanceDir, { recursive: true });
        fs.mkdirSync(this.layout.logsDir, { recursive: true });
        this.updateStatus();
    }
    getState() {
        return {
            running: Boolean(this.proc && this.port),
            port: this.port,
            url: this.port ? `http://127.0.0.1:${this.port}/` : "",
            instanceDir: this.layout.instanceDir,
        };
    }
    workspaceSecretKey(name) {
        return workspaceSecretKey(this.layout.workspaceHash, name);
    }
    githubSecretKey() {
        return workspaceGithubSecretKey(this.layout.workspaceHash);
    }
    async readProvider() {
        const raw = String((await this.context.secrets.get(this.workspaceSecretKey("provider"))) || "none")
            .trim()
            .toLowerCase();
        if (raw === "gemini" || raw === "groq" || raw === "xai" || raw === "copilot") {
            return raw;
        }
        return "none";
    }
    async readModel() {
        return String((await this.context.secrets.get(this.workspaceSecretKey("model"))) || "").trim();
    }
    async keyForProvider(provider) {
        if (provider === "none") {
            return "";
        }
        return String((await this.context.secrets.get(this.workspaceSecretKey(provider))) || "").trim();
    }
    pythonHint() {
        const cfg = vscode.workspace.getConfiguration("codemap");
        const configured = String(cfg.get("pythonPath", "python") || "python").trim();
        return configured || "python";
    }
    async buildEnv(port) {
        const env = { ...process.env };
        delete env.GEMINI_API_KEY;
        delete env.GROQ_API_KEY;
        delete env.XAI_API_KEY;
        delete env.COPILOT_TOKEN;
        delete env.GITHUB_TOKEN;
        delete env.CODEMAP_LLM;
        delete env.CODEMAP_GEMINI_MODEL;
        delete env.CODEMAP_GROQ_MODEL;
        delete env.CODEMAP_XAI_MODEL;
        env.CODEMAP_INSTANCE_DIR = this.layout.instanceDir;
        const workspaceRoot = this.getWorkspacePath();
        if (workspaceRoot) {
            env.CODEMAP_WORKSPACE_ROOT = workspaceRoot;
        }
        env.CODEMAP_PORT = String(port);
        env.CODEMAP_SESSION_MODE = "1";
        env.CODEMAP_RUNTIME_MODE = "vscode";
        const githubToken = String((await this.context.secrets.get(this.githubSecretKey())) || "").trim();
        if (githubToken) {
            env.GITHUB_TOKEN = githubToken;
        }
        return env;
    }
    writeRuntimeState(state) {
        const payload = {
            workspace_hash: state.workspace_hash,
            instance_dir: state.instance_dir,
            port: state.port,
            pid: state.pid,
            python_path: state.python_path,
            python_version: state.python_version,
            updated_at: nowIso(),
        };
        const tmp = `${this.statePath}.tmp.${process.pid}`;
        fs.mkdirSync(path.dirname(this.statePath), { recursive: true });
        fs.writeFileSync(tmp, JSON.stringify(payload, null, 2), "utf-8");
        fs.renameSync(tmp, this.statePath);
    }
    readRuntimeState() {
        try {
            const raw = fs.readFileSync(this.statePath, "utf-8");
            const parsed = JSON.parse(raw);
            const port = Number(parsed.port || 0);
            if (!Number.isFinite(port) || port <= 0) {
                return null;
            }
            return {
                workspace_hash: String(parsed.workspace_hash || ""),
                instance_dir: String(parsed.instance_dir || this.layout.instanceDir),
                port,
                pid: Number(parsed.pid || 0) || undefined,
                python_path: String(parsed.python_path || ""),
                python_version: String(parsed.python_version || ""),
                updated_at: String(parsed.updated_at || ""),
            };
        }
        catch {
            return null;
        }
    }
    async pickPort() {
        const cfg = vscode.workspace.getConfiguration("codemap");
        const configuredStart = Number(cfg.get("port", 8000) || 8000);
        const start = Number.isFinite(configuredStart) && configuredStart > 0 ? configuredStart : 8000;
        const state = this.readRuntimeState();
        if (state && state.port > 0) {
            const free = await isPortAvailable(state.port);
            if (free) {
                return state.port;
            }
        }
        for (let p = start; p <= start + 50; p += 1) {
            // eslint-disable-next-line no-await-in-loop
            if (await isPortAvailable(p)) {
                return p;
            }
        }
        throw new Error(`No available dashboard port in range ${start}-${start + 50}.`);
    }
    updateStatus() {
        if (this.proc && this.port) {
            this.statusBar.text = `CodeMap: Running (port ${this.port})`;
            this.statusBar.tooltip = `CodeMap dashboard: http://127.0.0.1:${this.port}/`;
        }
        else {
            this.statusBar.text = "CodeMap: Stopped";
            this.statusBar.tooltip = "CodeMap dashboard is not running.";
        }
        this.statusBar.command = "codemap.openDashboard";
    }
    appendServerLog(prefix, chunk) {
        const text = (0, redact_1.redactSecrets)(String(chunk || ""));
        if (!text.trim()) {
            return;
        }
        this.output.appendLine(prefix ? `${prefix}${text.trimEnd()}` : text.trimEnd());
        if (!this.logStream) {
            this.logStream = fs.createWriteStream(this.logPath, { flags: "a", encoding: "utf-8" });
        }
        this.logStream.write(`${prefix}${text}`);
    }
    async waitForHealth(port, timeoutMs = 15000) {
        const deadline = Date.now() + timeoutMs;
        const api = new apiClient_1.ApiClient(`http://127.0.0.1:${port}`);
        while (Date.now() < deadline) {
            try {
                // eslint-disable-next-line no-await-in-loop
                const health = await api.health();
                if (health && health.ok) {
                    return;
                }
            }
            catch {
                // retry
            }
            // eslint-disable-next-line no-await-in-loop
            await new Promise((resolve) => setTimeout(resolve, 500));
        }
        throw new Error("Timed out waiting for CodeMap dashboard health check.");
    }
    async applyStoredAiConfig(api) {
        const provider = await this.readProvider();
        const model = await this.readModel();
        const key = await this.keyForProvider(provider);
        if (provider === "none" || !key) {
            await api.clearAiKey("process");
            return;
        }
        const result = await api.setAiKey(provider, key, model);
        if (!result || result.ok === false) {
            const msg = (0, redact_1.redactSecrets)(String(result?.message || result?.error || "Failed to apply AI key from SecretStorage."));
            throw new Error(msg);
        }
    }
    async startDashboard() {
        if (this.proc && this.port) {
            return `http://127.0.0.1:${this.port}/`;
        }
        const bootstrap = new pythonBootstrap_1.PythonBootstrap({
            repoRoot: this.repoRoot,
            instanceDir: this.layout.instanceDir,
            output: this.output,
            pythonHint: this.pythonHint(),
        });
        let runtime;
        try {
            runtime = await bootstrap.ensureReady();
        }
        catch (e) {
            const msg = (0, redact_1.redactSecrets)(String(e?.message || e || "Bootstrap failed."));
            throw new Error(`BOOTSTRAP_FAILED: ${msg}`);
        }
        const port = await this.pickPort();
        const env = await this.buildEnv(port);
        const command = runtime.pythonPath;
        const args = ["-m", "codemap_ai.dashboard", "--host", "127.0.0.1", "--port", String(port)];
        this.output.appendLine(`[CodeMap] Starting dashboard for workspace=${this.layout.workspaceHash}`);
        this.output.appendLine(`[CodeMap] instanceDir=${this.layout.instanceDir}`);
        this.output.appendLine(`[CodeMap] port=${port}`);
        this.output.appendLine(`[CodeMap] launch=${path.basename(command)} ${args.join(" ")}`);
        const child = (0, child_process_1.spawn)(command, args, {
            cwd: this.repoRoot,
            env,
            windowsHide: true,
        });
        this.proc = child;
        this.port = port;
        this.api = new apiClient_1.ApiClient(`http://127.0.0.1:${port}`, {
            "X-CodeMap-Session-Id": this.sessionId,
            "X-Client-Id": this.clientId,
        });
        await this.context.workspaceState.update("codemap.dashboardPort", port);
        this.updateStatus();
        child.stdout?.on("data", (buf) => this.appendServerLog("", buf));
        child.stderr?.on("data", (buf) => this.appendServerLog("[stderr] ", buf));
        child.on("exit", (code) => {
            this.appendServerLog("", Buffer.from(`\n[CodeMap] Dashboard exited with code=${code ?? "unknown"}\n`, "utf-8"));
            this.proc = null;
            this.port = null;
            this.api = null;
            this.updateStatus();
        });
        child.on("error", (err) => {
            this.appendServerLog("[stderr] ", Buffer.from(`${(0, redact_1.redactSecrets)(String(err?.message || err))}\n`, "utf-8"));
            this.proc = null;
            this.port = null;
            this.api = null;
            this.updateStatus();
        });
        try {
            await this.waitForHealth(port, 15000);
            if (this.api) {
                await this.applyStoredAiConfig(this.api);
            }
        }
        catch (e) {
            await this.stopDashboard();
            throw e;
        }
        this.writeRuntimeState({
            workspace_hash: this.layout.workspaceHash,
            instance_dir: this.layout.instanceDir,
            port,
            pid: child.pid,
            python_path: runtime.pythonPath,
            python_version: runtime.pythonVersion,
            updated_at: nowIso(),
        });
        this.updateStatus();
        return `http://127.0.0.1:${port}/?session_id=${encodeURIComponent(this.sessionId)}&client_id=${encodeURIComponent(this.clientId)}`;
    }
    async stopDashboard() {
        const child = this.proc;
        if (!child) {
            return;
        }
        this.output.appendLine("[CodeMap] Stopping dashboard...");
        this.proc = null;
        this.port = null;
        this.api = null;
        await this.context.workspaceState.update("codemap.dashboardPort", undefined);
        this.updateStatus();
        if (this.logStream) {
            try {
                this.logStream.end();
            }
            catch {
                // best effort
            }
            this.logStream = null;
        }
        if (process.platform === "win32" && child.pid) {
            await new Promise((resolve) => {
                const killer = (0, child_process_1.spawn)("taskkill", ["/PID", String(child.pid), "/T", "/F"], { windowsHide: true });
                killer.on("exit", () => resolve());
                killer.on("error", () => resolve());
            });
            return;
        }
        try {
            child.kill("SIGTERM");
        }
        catch {
            // best effort
        }
    }
    async restartDashboard() {
        await this.stopDashboard();
        await this.startDashboard();
    }
    async openDashboard() {
        const url = await this.startDashboard();
        await this.openDashboardWebview(url);
    }
    async openLogs() {
        if (!fs.existsSync(this.logPath)) {
            vscode.window.showInformationMessage("No CodeMap logs yet.");
            return;
        }
        const doc = await vscode.workspace.openTextDocument(vscode.Uri.file(this.logPath));
        await vscode.window.showTextDocument(doc, { preview: false });
    }
    apiClient() {
        if (!this.api || !this.port) {
            throw new Error("Dashboard is not running.");
        }
        return this.api;
    }
    async healthCheck() {
        await this.startDashboard();
        return this.apiClient().health();
    }
    getWorkspacePath() {
        const ws = vscode.workspace.workspaceFolders;
        if (ws && ws.length > 0) {
            return ws[0].uri.fsPath;
        }
        return null;
    }
    async pickWorkspacePath() {
        const current = this.getWorkspacePath();
        if (current) {
            return current;
        }
        const picked = await vscode.window.showOpenDialog({
            canSelectFiles: false,
            canSelectFolders: true,
            canSelectMany: false,
            openLabel: "Select workspace folder",
        });
        if (!picked || !picked.length) {
            return null;
        }
        return picked[0].fsPath;
    }
    async analyzeCurrentWorkspace(repoPath) {
        const target = repoPath || this.getWorkspacePath();
        if (!target) {
            throw new Error("No workspace selected.");
        }
        await this.startDashboard();
        const result = await this.apiClient().analyzeFilesystem(target);
        if (!result.ok) {
            throw new Error((0, redact_1.redactSecrets)(String(result.message || result.error || "Analyze failed.")));
        }
        await this.context.workspaceState.update("codemap.lastRepoPath", target);
        return result;
    }
    async addGithubRepo(repoUrl, ref, mode) {
        await this.startDashboard();
        const result = await this.apiClient().addGithubRepo(repoUrl, ref, mode);
        if (!result.ok) {
            throw new Error((0, redact_1.redactSecrets)(String(result.message || result.error || "GitHub import failed.")));
        }
        return result;
    }
    async clearSessionRepos() {
        await this.startDashboard();
        return this.apiClient().clearSessionRepos();
    }
    async saveAiConfig(provider, key, model) {
        const p = String(provider || "none").trim().toLowerCase();
        await this.context.secrets.store(this.workspaceSecretKey("provider"), p);
        await this.context.secrets.store(this.workspaceSecretKey("model"), String(model || "").trim());
        if (p === "none") {
            await this.clearAiKeys();
            return;
        }
        const trimmed = String(key || "").trim();
        if (!trimmed) {
            throw new Error("API key is required for the selected provider.");
        }
        await this.context.secrets.store(this.workspaceSecretKey(p), trimmed);
    }
    async saveGithubToken(token) {
        const cleaned = String(token || "").trim();
        if (!cleaned) {
            return;
        }
        await this.context.secrets.store(this.githubSecretKey(), cleaned);
    }
    async clearAiKeys() {
        await this.context.secrets.delete(this.workspaceSecretKey("gemini"));
        await this.context.secrets.delete(this.workspaceSecretKey("groq"));
        await this.context.secrets.delete(this.workspaceSecretKey("xai"));
        await this.context.secrets.delete(this.workspaceSecretKey("copilot"));
        await this.context.secrets.delete(this.workspaceSecretKey("provider"));
        await this.context.secrets.delete(this.workspaceSecretKey("model"));
    }
    async openDashboardWebview(url) {
        try {
            if (this.dashboardPanel) {
                this.dashboardPanel.title = `CodeMap Dashboard (${this.layout.workspaceHash})`;
                this.dashboardPanel.webview.html = this.dashboardWebviewHtml(url);
                this.dashboardPanel.reveal(vscode.ViewColumn.Active);
                return;
            }
            const panel = vscode.window.createWebviewPanel("codemapDashboard", `CodeMap Dashboard (${this.layout.workspaceHash})`, vscode.ViewColumn.Active, {
                enableScripts: true,
            });
            this.dashboardPanel = panel;
            panel.onDidDispose(() => {
                this.dashboardPanel = null;
            });
            panel.webview.onDidReceiveMessage(async (msg) => {
                if ((msg && msg.type) === "openExternal") {
                    await vscode.env.openExternal(vscode.Uri.parse(url));
                }
            });
            panel.webview.html = this.dashboardWebviewHtml(url);
        }
        catch {
            await vscode.env.openExternal(vscode.Uri.parse(url));
        }
    }
    dashboardWebviewHtml(url) {
        const safeUrl = String(url || "").replace(/"/g, "&quot;");
        return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>CodeMap Dashboard</title>
  <style>
    html, body { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #111827; color: #e5e7eb; font-family: sans-serif; }
    #container { width: 100%; height: 100%; display: grid; grid-template-rows: auto 1fr; }
    #bar { padding: 8px 12px; font-size: 12px; background: #0f172a; border-bottom: 1px solid #1f2937; }
    #frame { width: 100%; height: 100%; border: 0; }
    a { color: #93c5fd; }
  </style>
</head>
<body>
  <div id="container">
    <div id="bar">Loading CodeMap dashboard... <a href="${safeUrl}" target="_blank" rel="noopener">Open in browser</a></div>
    <iframe id="frame" src="${safeUrl}" referrerpolicy="no-referrer"></iframe>
  </div>
  <script>
    const vscode = acquireVsCodeApi();
    const frame = document.getElementById("frame");
    let loaded = false;
    frame.addEventListener("load", () => { loaded = true; });
    setTimeout(() => {
      if (!loaded) {
        vscode.postMessage({ type: "openExternal" });
      }
    }, 4000);
  </script>
</body>
</html>`;
    }
    async runCommand(command, args, timeoutMs = 60000) {
        return new Promise((resolve) => {
            const child = (0, child_process_1.spawn)(command, args, {
                cwd: this.repoRoot,
                windowsHide: true,
            });
            let stdout = "";
            let stderr = "";
            let done = false;
            const timer = setTimeout(() => {
                if (done) {
                    return;
                }
                done = true;
                try {
                    child.kill();
                }
                catch {
                    // ignore
                }
                resolve({ code: 1, stdout, stderr: `${stderr}\nCommand timed out.`.trim() });
            }, Math.max(1000, timeoutMs));
            child.stdout?.on("data", (d) => {
                const text = (0, redact_1.redactSecrets)(String(d || ""));
                stdout += text;
            });
            child.stderr?.on("data", (d) => {
                const text = (0, redact_1.redactSecrets)(String(d || ""));
                stderr += text;
            });
            child.on("exit", (code) => {
                if (done) {
                    return;
                }
                done = true;
                clearTimeout(timer);
                resolve({ code: Number(code ?? 1), stdout, stderr });
            });
            child.on("error", (err) => {
                if (done) {
                    return;
                }
                done = true;
                clearTimeout(timer);
                resolve({ code: 1, stdout, stderr: (0, redact_1.redactSecrets)(String(err?.message || err)) });
            });
        });
    }
}
exports.ServerManager = ServerManager;
//# sourceMappingURL=ServerManager.js.map