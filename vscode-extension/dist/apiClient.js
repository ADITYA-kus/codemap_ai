"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.ApiClient = void 0;
const http = require("http");
const url_1 = require("url");
const redact_1 = require("./redact");
class ApiClient {
    constructor(baseUrl, defaultHeaders) {
        this.baseUrl = String(baseUrl || "").replace(/\/+$/, "");
        this.defaultHeaders = { ...(defaultHeaders || {}) };
    }
    requestJson(method, route, body) {
        const url = new url_1.URL(`${this.baseUrl}${route}`);
        const payload = body ? JSON.stringify(body) : "";
        const headers = {
            Accept: "application/json",
            ...this.defaultHeaders,
        };
        if (payload) {
            headers["Content-Type"] = "application/json";
            headers["Content-Length"] = String(Buffer.byteLength(payload));
        }
        return new Promise((resolve, reject) => {
            const req = http.request({
                protocol: url.protocol,
                hostname: url.hostname,
                port: Number(url.port || 80),
                path: `${url.pathname}${url.search}`,
                method,
                headers,
                timeout: 120000
            }, (res) => {
                let raw = "";
                res.setEncoding("utf8");
                res.on("data", (chunk) => {
                    raw += chunk;
                });
                res.on("end", () => {
                    try {
                        const parsed = raw ? JSON.parse(raw) : {};
                        resolve(parsed);
                    }
                    catch {
                        reject(new Error(`Invalid JSON response: ${(0, redact_1.redactSecrets)(raw).slice(0, 300)}`));
                    }
                });
            });
            req.on("timeout", () => {
                req.destroy(new Error("Request timed out"));
            });
            req.on("error", (err) => {
                reject(new Error((0, redact_1.redactSecrets)(String(err?.message || err))));
            });
            if (payload) {
                req.write(payload);
            }
            req.end();
        });
    }
    health() {
        return this.requestJson("GET", "/api/health");
    }
    analyzeFilesystem(repoPath) {
        return this.requestJson("POST", "/api/analyze", {
            source: "filesystem",
            repo_path: repoPath
        });
    }
    addGithubRepo(repoUrl, ref, mode) {
        return this.requestJson("POST", "/api/repo_import/github", {
            repo_url: repoUrl,
            ref,
            mode
        });
    }
    clearSessionRepos() {
        return this.requestJson("POST", "/api/registry/repos/clear", {
            session_only: true
        });
    }
    setAiKey(provider, apiKey, model = "") {
        const key = String(apiKey || "").trim();
        const p = String(provider || "").trim().toLowerCase();
        if (!key || !p) {
            return Promise.resolve({ ok: false, error: "INVALID_AI_CONFIG" });
        }
        const prev = this.defaultHeaders["X-CodeMap-LLM-Key"];
        this.defaultHeaders["X-CodeMap-LLM-Key"] = key;
        return this.requestJson("POST", "/api/ai/set-key", {
            provider: p,
            model: String(model || "").trim(),
            source: "vscode",
            scope: "process",
        }).finally(() => {
            if (prev) {
                this.defaultHeaders["X-CodeMap-LLM-Key"] = prev;
            }
            else {
                delete this.defaultHeaders["X-CodeMap-LLM-Key"];
            }
        });
    }
    clearAiKey(scope = "process") {
        return this.requestJson("POST", "/api/ai/clear", { scope });
    }
}
exports.ApiClient = ApiClient;
//# sourceMappingURL=apiClient.js.map