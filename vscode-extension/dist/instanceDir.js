"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.workspaceHash = workspaceHash;
exports.resolveInstanceDir = resolveInstanceDir;
exports.resolveInstanceLayout = resolveInstanceLayout;
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const vscode = require("vscode");
function workspaceSeed() {
    const folders = vscode.workspace.workspaceFolders || [];
    if (!folders.length) {
        return "no-workspace";
    }
    const normalized = folders
        .map((f) => f.uri.fsPath.replace(/\\/g, "/").toLowerCase())
        .sort()
        .join("|");
    return normalized || "no-workspace";
}
function workspaceHash() {
    const seed = workspaceSeed();
    return crypto.createHash("sha256").update(seed).digest("hex").slice(0, 16);
}
function resolveInstanceDir(context) {
    return resolveInstanceLayout(context).instanceDir;
}
function resolveInstanceLayout(context) {
    const baseDir = context.globalStorageUri.fsPath;
    const hash = workspaceHash();
    const instanceDir = path.join(baseDir, "instances", hash);
    const logsDir = path.join(instanceDir, "logs");
    const statePath = path.join(instanceDir, "state.json");
    fs.mkdirSync(logsDir, { recursive: true });
    return {
        workspaceHash: hash,
        baseDir,
        instanceDir,
        logsDir,
        statePath,
    };
}
//# sourceMappingURL=instanceDir.js.map