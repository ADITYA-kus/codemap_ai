"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.PythonBootstrap = void 0;
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const child_process_1 = require("child_process");
const vscode = require("vscode");
const redact_1 = require("../redact");
class PythonBootstrap {
    constructor(opts) {
        this.minMajor = 3;
        this.minMinor = 10;
        this.repoRoot = opts.repoRoot;
        this.instanceDir = opts.instanceDir;
        this.output = opts.output;
        this.pythonHint = String(opts.pythonHint || "python").trim() || "python";
        this.markerPath = path.join(this.instanceDir, "state", "deps_ok.json");
    }
    venvDir() {
        return path.join(this.instanceDir, ".venv");
    }
    venvPythonPath() {
        if (process.platform === "win32") {
            return path.join(this.venvDir(), "Scripts", "python.exe");
        }
        return path.join(this.venvDir(), "bin", "python");
    }
    requirementsPath() {
        return path.join(this.repoRoot, "requirements.txt");
    }
    pyprojectPath() {
        return path.join(this.repoRoot, "pyproject.toml");
    }
    async runCommand(command, args, options) {
        const timeoutMs = Math.max(1000, Number(options?.timeoutMs || 120000));
        const cwd = options?.cwd || this.repoRoot;
        const env = options?.env || process.env;
        return new Promise((resolve) => {
            const child = (0, child_process_1.spawn)(command, args, { cwd, env, windowsHide: true });
            let stdout = "";
            let stderr = "";
            let finished = false;
            const timer = setTimeout(() => {
                if (finished) {
                    return;
                }
                finished = true;
                try {
                    child.kill();
                }
                catch {
                    // best effort
                }
                resolve({ code: 1, stdout, stderr: `${stderr}\nCommand timed out.`.trim() });
            }, timeoutMs);
            child.stdout?.on("data", (chunk) => {
                const text = (0, redact_1.redactSecrets)(String(chunk || ""));
                stdout += text;
                this.output.appendLine(text.trimEnd());
            });
            child.stderr?.on("data", (chunk) => {
                const text = (0, redact_1.redactSecrets)(String(chunk || ""));
                stderr += text;
                this.output.appendLine(`[stderr] ${text.trimEnd()}`);
            });
            child.on("exit", (code) => {
                if (finished) {
                    return;
                }
                finished = true;
                clearTimeout(timer);
                resolve({ code: Number(code ?? 1), stdout, stderr });
            });
            child.on("error", (err) => {
                if (finished) {
                    return;
                }
                finished = true;
                clearTimeout(timer);
                resolve({ code: 1, stdout, stderr: `${stderr}\n${(0, redact_1.redactSecrets)(String(err?.message || err))}`.trim() });
            });
        });
    }
    parsePythonInfo(raw) {
        const lines = String(raw || "")
            .split(/\r?\n/)
            .map((line) => line.trim())
            .filter(Boolean);
        if (lines.length < 2) {
            return null;
        }
        const executable = lines[0];
        const parts = String(lines[1]).split(".");
        if (parts.length < 2) {
            return null;
        }
        const major = Number(parts[0]);
        const minor = Number(parts[1]);
        const patch = Number(parts[2] || 0);
        if (!Number.isFinite(major) || !Number.isFinite(minor)) {
            return null;
        }
        return {
            executable,
            version: `${major}.${minor}.${patch}`,
            major,
            minor,
            patch,
        };
    }
    async detectPython() {
        const probeCode = "import sys; print(sys.executable); print('.'.join(str(x) for x in sys.version_info[:3]))";
        const extensionInterpreter = await this.pythonExtensionInterpreter();
        const candidates = [];
        const pushCandidate = (command, argsPrefix = []) => {
            const cmd = String(command || "").trim();
            if (!cmd) {
                return;
            }
            if (candidates.some((item) => item.command.toLowerCase() === cmd.toLowerCase() && item.argsPrefix.join(" ") === argsPrefix.join(" "))) {
                return;
            }
            candidates.push({ command: cmd, argsPrefix });
        };
        // Required order:
        // 1) codemap.pythonPath
        // 2) VS Code Python extension interpreter
        // 3) python on PATH
        // 4) py launcher on Windows
        pushCandidate(this.pythonHint);
        pushCandidate(extensionInterpreter);
        pushCandidate("python");
        if (process.platform === "win32") {
            pushCandidate("py", ["-3"]);
        }
        const tooOldVersions = [];
        for (const candidate of candidates) {
            // eslint-disable-next-line no-await-in-loop
            const result = await this.runCommand(candidate.command, [...candidate.argsPrefix, "-c", probeCode], { timeoutMs: 20000 });
            if (result.code !== 0) {
                continue;
            }
            const parsed = this.parsePythonInfo(result.stdout);
            if (!parsed) {
                continue;
            }
            if (parsed.major < this.minMajor || (parsed.major === this.minMajor && parsed.minor < this.minMinor)) {
                tooOldVersions.push(parsed.version);
                continue;
            }
            return parsed;
        }
        if (tooOldVersions.length) {
            throw new Error(`PYTHON_TOO_OLD: Found Python ${tooOldVersions.join(", ")}. CodeMap requires Python >= ${this.minMajor}.${this.minMinor}.`);
        }
        throw new Error("PYTHON_NOT_FOUND: Python 3.10+ is required. Install Python or configure codemap.pythonPath.");
    }
    requirementsHash() {
        const req = this.requirementsPath();
        if (!fs.existsSync(req)) {
            return "no-requirements";
        }
        const content = fs.readFileSync(req, "utf-8");
        return crypto.createHash("sha256").update(content, "utf-8").digest("hex");
    }
    projectHash() {
        const pyproject = this.pyprojectPath();
        if (!fs.existsSync(pyproject)) {
            return "no-pyproject";
        }
        const content = fs.readFileSync(pyproject, "utf-8");
        return crypto.createHash("sha256").update(content, "utf-8").digest("hex");
    }
    loadMarker() {
        try {
            const raw = fs.readFileSync(this.markerPath, "utf-8");
            const parsed = JSON.parse(raw);
            return parsed && typeof parsed === "object" ? parsed : {};
        }
        catch {
            return {};
        }
    }
    saveMarker(payload) {
        fs.mkdirSync(path.dirname(this.markerPath), { recursive: true });
        const tmp = `${this.markerPath}.tmp.${process.pid}`;
        fs.writeFileSync(tmp, JSON.stringify(payload, null, 2), "utf-8");
        fs.renameSync(tmp, this.markerPath);
    }
    async ensureVenv(basePython) {
        const venvPython = this.venvPythonPath();
        if (fs.existsSync(venvPython)) {
            return;
        }
        fs.mkdirSync(this.venvDir(), { recursive: true });
        this.output.appendLine(`[CodeMap] Creating virtual environment at ${this.venvDir()}`);
        const result = await this.runCommand(basePython, ["-m", "venv", this.venvDir()], { timeoutMs: 240000 });
        if (result.code !== 0 || !fs.existsSync(venvPython)) {
            throw new Error((0, redact_1.redactSecrets)(result.stderr || result.stdout || "Failed to create virtual environment."));
        }
    }
    async ensureDependencies(venvPython, pythonVersion) {
        const marker = this.loadMarker();
        const reqHash = this.requirementsHash();
        const projectHash = this.projectHash();
        const markerReqHash = String(marker.requirements_hash || "");
        const markerPy = String(marker.python_version || "");
        const markerProjectHash = String(marker.project_hash || "");
        const importCheck = await this.runCommand(venvPython, ["-c", "import codemap_ai"], { timeoutMs: 15000 });
        if (importCheck.code !== 0) {
            const action = await vscode.window.showInformationMessage("CodeMap backend is not installed in this Python environment.", { modal: true }, "Install Now (recommended)", "Cancel");
            if (action !== "Install Now (recommended)") {
                throw new Error("INSTALL_CANCELLED: CodeMap backend install was cancelled.");
            }
            this.output.appendLine("[CodeMap] Installing codemap-ai into workspace virtual environment...");
            let install = await this.runCommand(venvPython, ["-m", "pip", "install", "codemap-ai"], { timeoutMs: 15 * 60 * 1000 });
            if (install.code !== 0 && fs.existsSync(this.pyprojectPath())) {
                this.output.appendLine("[CodeMap] pip install codemap-ai failed, trying editable install from current repo...");
                install = await this.runCommand(venvPython, ["-m", "pip", "install", "-e", this.repoRoot], { timeoutMs: 15 * 60 * 1000 });
            }
            if (install.code !== 0) {
                throw new Error(`BOOTSTRAP_INSTALL_FAILED: ${(0, redact_1.redactSecrets)(install.stderr || install.stdout || "Failed to install codemap-ai.")}`);
            }
            const postCheck = await this.runCommand(venvPython, ["-c", "import codemap_ai"], { timeoutMs: 15000 });
            if (postCheck.code !== 0) {
                throw new Error("BOOTSTRAP_INSTALL_FAILED: codemap_ai import check failed after install.");
            }
        }
        else if (markerReqHash === reqHash && markerPy === pythonVersion && markerProjectHash === projectHash) {
            return false;
        }
        this.saveMarker({
            requirements_hash: reqHash,
            project_hash: projectHash,
            python_version: pythonVersion,
            updated_at: new Date().toISOString(),
        });
        return true;
    }
    async ensureReady() {
        fs.mkdirSync(this.instanceDir, { recursive: true });
        const basePython = await this.detectPython();
        await this.ensureVenv(basePython.executable);
        const venvPython = this.venvPythonPath();
        const venvProbe = await this.runCommand(venvPython, ["-c", "import sys; print(sys.executable); print('.'.join(str(x) for x in sys.version_info[:3]))"], { timeoutMs: 20000 });
        const venvInfo = this.parsePythonInfo(venvProbe.stdout);
        if (venvProbe.code !== 0 || !venvInfo) {
            throw new Error((0, redact_1.redactSecrets)(venvProbe.stderr || "Failed to validate workspace virtual environment."));
        }
        const installed = await this.ensureDependencies(venvInfo.executable, venvInfo.version);
        return {
            pythonPath: venvInfo.executable,
            pythonVersion: venvInfo.version,
            venvDir: this.venvDir(),
            installed,
            markerPath: this.markerPath,
        };
    }
    async pythonExtensionInterpreter() {
        try {
            const ext = vscode.extensions.getExtension("ms-python.python");
            if (!ext) {
                return "";
            }
            if (!ext.isActive) {
                await ext.activate();
            }
            try {
                const viaCommand = await vscode.commands.executeCommand("python.interpreterPath");
                const commandPath = this.extractInterpreterPath(viaCommand);
                if (commandPath) {
                    return commandPath;
                }
            }
            catch {
                // ignore command not available
            }
            try {
                const activeEnv = await vscode.commands.executeCommand("python.environments.getActiveEnvironmentPath");
                const envPath = this.extractInterpreterPath(activeEnv);
                if (envPath) {
                    return envPath;
                }
            }
            catch {
                // ignore command not available
            }
            const pyCfg = vscode.workspace.getConfiguration("python");
            const fromSettings = String(pyCfg.get("defaultInterpreterPath", "") || "").trim();
            if (fromSettings) {
                return fromSettings;
            }
            return "";
        }
        catch {
            return "";
        }
    }
    extractInterpreterPath(value) {
        if (!value) {
            return "";
        }
        if (typeof value === "string") {
            return value.trim();
        }
        if (typeof value === "object") {
            const payload = value;
            const direct = String(payload.path || "").trim();
            if (direct) {
                return direct;
            }
            if (payload.path && typeof payload.path === "object") {
                const nested = payload.path;
                const nestedValue = String(nested.path || "").trim();
                if (nestedValue) {
                    return nestedValue;
                }
            }
        }
        return "";
    }
}
exports.PythonBootstrap = PythonBootstrap;
//# sourceMappingURL=pythonBootstrap.js.map