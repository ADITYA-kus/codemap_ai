"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.redactSecrets = redactSecrets;
const TOKEN_PATTERNS = [
    /\bgh[pousr]_[A-Za-z0-9_]{8,}\b/g,
    /\bBearer\s+[^\s]+/gi,
    /\bBasic\s+[^\s]+/gi,
    /\bAIza[0-9A-Za-z\-_]{20,}\b/g,
    /\bsk-[A-Za-z0-9\-_]{10,}\b/g,
    /\bgsk_[A-Za-z0-9\-_]{10,}\b/g,
    /\bxai-[A-Za-z0-9\-_]{10,}\b/g,
    /(https?:\/\/)([^/\s:@]+):([^@\s/]+)@/gi
];
function redactSecrets(text) {
    let out = String(text || "");
    for (const pattern of TOKEN_PATTERNS) {
        out = out.replace(pattern, (m) => {
            if (m.startsWith("http://") || m.startsWith("https://")) {
                return m.replace(/\/\/([^/\s:@]+):([^@\s/]+)@/gi, "//***:***@");
            }
            if (m.toLowerCase().startsWith("bearer ")) {
                return "Bearer ********";
            }
            if (m.toLowerCase().startsWith("basic ")) {
                return "Basic ********";
            }
            if (m.length <= 4) {
                return "****";
            }
            return `${m.slice(0, 4)}********`;
        });
    }
    return out;
}
//# sourceMappingURL=redact.js.map