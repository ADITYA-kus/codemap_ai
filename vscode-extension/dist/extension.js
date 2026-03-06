"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
const ServerManager_1 = require("./server/ServerManager");
const redact_1 = require("./redact");
let manager = null;
async function activate(context) {
    const output = vscode.window.createOutputChannel("CodeMap");
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.show();
    context.subscriptions.push(output, statusBar);
    manager = new ServerManager_1.ServerManager(context, output, statusBar);
    const withError = (label, fn) => async () => {
        try {
            await fn();
        }
        catch (e) {
            const msg = (0, redact_1.redactSecrets)(String(e?.message || e || "Unknown error"));
            output.appendLine(`[CodeMap] ${label} failed: ${msg}`);
            if (msg.includes("PYTHON_NOT_FOUND") || msg.includes("PYTHON_TOO_OLD")) {
                const action = await vscode.window.showErrorMessage("Python 3.10+ is required. Install Python or configure codemap.pythonPath.", "Open Settings", "Open Python Website");
                if (action === "Open Settings") {
                    await vscode.commands.executeCommand("workbench.action.openSettings", "codemap.pythonPath");
                }
                else if (action === "Open Python Website") {
                    await vscode.env.openExternal(vscode.Uri.parse("https://www.python.org/downloads/"));
                }
                return;
            }
            if (msg.includes("INSTALL_CANCELLED")) {
                void vscode.window.showWarningMessage("CodeMap backend install was cancelled.");
                return;
            }
            if (msg.includes("BOOTSTRAP_FAILED")) {
                const action = await vscode.window.showErrorMessage(`${label} failed: ${msg.replace("BOOTSTRAP_FAILED:", "").trim()}`, "Open Logs", "Retry Bootstrap");
                if (action === "Open Logs") {
                    await manager?.openLogs();
                    return;
                }
                if (action === "Retry Bootstrap") {
                    try {
                        await fn();
                    }
                    catch (retryErr) {
                        const retryMsg = (0, redact_1.redactSecrets)(String(retryErr?.message || retryErr || "Unknown error"));
                        output.appendLine(`[CodeMap] Retry failed: ${retryMsg}`);
                        void vscode.window.showErrorMessage(`Retry failed: ${retryMsg}`, "Open Logs").then((choice) => {
                            if (choice === "Open Logs") {
                                void manager?.openLogs();
                            }
                        });
                    }
                    return;
                }
            }
            void vscode.window.showErrorMessage(`${label} failed: ${msg}`, "Open Logs").then((choice) => {
                if (choice === "Open Logs") {
                    void manager?.openLogs();
                }
            });
        }
    };
    async function configureAiByok() {
        const providerPick = await vscode.window.showQuickPick([
            { label: "Gemini", value: "gemini" },
            { label: "Groq", value: "groq" },
            { label: "xAI", value: "xai" },
            { label: "Copilot Token", value: "copilot" },
            { label: "Disable (None)", value: "none" }
        ], { placeHolder: "Choose AI provider" });
        if (!providerPick) {
            return;
        }
        const provider = providerPick.value;
        let model = "";
        let key = "";
        if (provider !== "none") {
            key =
                (await vscode.window.showInputBox({
                    prompt: `Enter ${providerPick.label} API key`,
                    password: true,
                    ignoreFocusOut: true
                })) || "";
            if (!key.trim()) {
                void vscode.window.showWarningMessage("No key entered. Configuration unchanged.");
                return;
            }
            model =
                (await vscode.window.showInputBox({
                    prompt: "Model (optional). Leave blank for default.",
                    ignoreFocusOut: true
                })) || "";
        }
        await manager.saveAiConfig(provider, key, model.trim());
        if (provider === "none") {
            void vscode.window.showInformationMessage("AI provider disabled for this workspace.");
        }
        else {
            void vscode.window.showInformationMessage(`Stored ${provider} key in VS Code SecretStorage for this workspace.`);
        }
        if (manager) {
            await manager.restartDashboard();
        }
    }
    context.subscriptions.push(vscode.commands.registerCommand("codemap.startDashboard", withError("Start Dashboard", async () => {
        await manager.openDashboard();
        void vscode.window.showInformationMessage("CodeMap dashboard started.");
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.stopDashboard", withError("Stop Dashboard", async () => {
        await manager.stopDashboard();
        void vscode.window.showInformationMessage("CodeMap dashboard stopped.");
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.openDashboard", withError("Open Dashboard", async () => {
        await manager.openDashboard();
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.analyzeCurrentWorkspace", withError("Analyze Current Workspace", async () => {
        const target = await manager.pickWorkspacePath();
        if (!target) {
            return;
        }
        await manager.analyzeCurrentWorkspace(target);
        await manager.openDashboard();
        void vscode.window.showInformationMessage("Analyze completed.");
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.addGithubRepoUrl", withError("Add GitHub Repo", async () => {
        const repoUrl = (await vscode.window.showInputBox({
            prompt: "GitHub repository URL",
            placeHolder: "https://github.com/owner/repo",
            ignoreFocusOut: true
        })) || "";
        if (!repoUrl.trim()) {
            return;
        }
        const ref = (await vscode.window.showInputBox({
            prompt: "Git ref (branch/tag)",
            value: "main",
            ignoreFocusOut: true
        })) || "main";
        const modePick = await vscode.window.showQuickPick([
            { label: "zip", value: "zip" },
            { label: "git", value: "git" }
        ], { placeHolder: "Choose fetch mode" });
        if (!modePick) {
            return;
        }
        const privatePick = await vscode.window.showQuickPick([
            { label: "No (public repo)", value: "no" },
            { label: "Yes (private repo)", value: "yes" }
        ], { placeHolder: "Is this a private repo?" });
        if (privatePick?.value === "yes") {
            const ghToken = (await vscode.window.showInputBox({
                prompt: "GitHub token (stored in SecretStorage)",
                password: true,
                ignoreFocusOut: true
            })) || "";
            if (ghToken.trim()) {
                await manager.saveGithubToken(ghToken);
                await manager.restartDashboard();
            }
        }
        await manager.addGithubRepo(repoUrl.trim(), ref.trim() || "main", modePick.value);
        await manager.openDashboard();
        void vscode.window.showInformationMessage("GitHub repo added.");
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.clearSessionRepos", withError("Clear Session Repos", async () => {
        await manager.clearSessionRepos();
        void vscode.window.showInformationMessage("Session repo list cleared.");
    })));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.configureAiByok", withError("Configure AI", configureAiByok)));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.clearAiKeys", withError("Clear AI Keys", async () => {
        await manager.clearAiKeys();
        await manager.restartDashboard();
        void vscode.window.showInformationMessage("AI keys cleared for this workspace.");
    })));
    // Legacy aliases
    context.subscriptions.push(vscode.commands.registerCommand("codemap.startServer", () => vscode.commands.executeCommand("codemap.startDashboard")));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.stopServer", () => vscode.commands.executeCommand("codemap.stopDashboard")));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.analyzeWorkspace", () => vscode.commands.executeCommand("codemap.analyzeCurrentWorkspace")));
    context.subscriptions.push(vscode.commands.registerCommand("codemap.dataPrivacyClearRepo", () => vscode.commands.executeCommand("codemap.clearSessionRepos")));
}
async function deactivate() {
    if (manager) {
        await manager.stopDashboard();
        manager = null;
    }
}
//# sourceMappingURL=extension.js.map