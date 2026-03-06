"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.run = run;
const path = require("path");
const Mocha = require("mocha");
const glob_1 = require("glob");
function run() {
    const mocha = new Mocha({
        ui: "tdd",
        color: true
    });
    const testsRoot = path.resolve(__dirname, "..");
    return new Promise((resolve, reject) => {
        try {
            const files = (0, glob_1.globSync)("**/*.test.js", { cwd: testsRoot });
            for (const f of files) {
                mocha.addFile(path.resolve(testsRoot, f));
            }
            mocha.run((failures) => {
                if (failures > 0) {
                    reject(new Error(`${failures} tests failed.`));
                }
                else {
                    resolve();
                }
            });
        }
        catch (e) {
            reject(e);
        }
    });
}
//# sourceMappingURL=index.js.map