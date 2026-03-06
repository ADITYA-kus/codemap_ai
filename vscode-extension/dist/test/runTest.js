"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const path = require("path");
const test_electron_1 = require("@vscode/test-electron");
async function main() {
    try {
        const extensionDevelopmentPath = path.resolve(__dirname, "../../..");
        const extensionTestsPath = path.resolve(__dirname, "./suite/index");
        await (0, test_electron_1.runTests)({
            extensionDevelopmentPath,
            extensionTestsPath
        });
    }
    catch (err) {
        // eslint-disable-next-line no-console
        console.error("Failed to run extension tests", err);
        process.exit(1);
    }
}
void main();
//# sourceMappingURL=runTest.js.map