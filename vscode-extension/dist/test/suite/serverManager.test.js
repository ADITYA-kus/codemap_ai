"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const assert = require("assert");
const fs = require("fs");
const os = require("os");
const path = require("path");
const ServerManager_1 = require("../../server/ServerManager");
suite("serverManager", () => {
    test("parseDashboardPort parses uvicorn output", () => {
        const line = "INFO:     Uvicorn running on http://127.0.0.1:53192 (Press CTRL+C to quit)";
        assert.strictEqual((0, ServerManager_1.parseDashboardPort)(line), 53192);
    });
    test("parseDashboardPort returns null for non-matching output", () => {
        assert.strictEqual((0, ServerManager_1.parseDashboardPort)("random log line"), null);
    });
    test("workspace secret keys are scoped by workspace hash", () => {
        const a = (0, ServerManager_1.workspaceSecretKey)("abcd1234", "gemini");
        const b = (0, ServerManager_1.workspaceSecretKey)("ffffeeee", "gemini");
        assert.ok(a.includes(".abcd1234"));
        assert.ok(b.includes(".ffffeeee"));
        assert.notStrictEqual(a, b);
        assert.strictEqual((0, ServerManager_1.workspaceGithubSecretKey)("abcd1234"), "codemap.github.token.abcd1234");
    });
    test("scanDirectoryForMarker detects leaks and clean directories", () => {
        const root = fs.mkdtempSync(path.join(os.tmpdir(), "codemap-ext-test-"));
        try {
            fs.mkdirSync(path.join(root, "logs"), { recursive: true });
            fs.writeFileSync(path.join(root, "state.json"), JSON.stringify({ port: 8000 }, null, 2), "utf-8");
            fs.writeFileSync(path.join(root, "logs", "server.log"), "dashboard started", "utf-8");
            assert.strictEqual((0, ServerManager_1.scanDirectoryForMarker)(root, "sk_TEST_SHOULD_NOT_PERSIST"), false);
            fs.writeFileSync(path.join(root, "leak.txt"), "sk_TEST_SHOULD_NOT_PERSIST", "utf-8");
            assert.strictEqual((0, ServerManager_1.scanDirectoryForMarker)(root, "sk_TEST_SHOULD_NOT_PERSIST"), true);
        }
        finally {
            fs.rmSync(root, { recursive: true, force: true });
        }
    });
});
//# sourceMappingURL=serverManager.test.js.map