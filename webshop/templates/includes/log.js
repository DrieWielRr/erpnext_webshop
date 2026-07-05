// log.js

const ENABLE_DEBUG = true;

function log(...args) {
	if (ENABLE_DEBUG) {
		console.log("[DEBUG]", ...args);
	}
}

function error(...args) {
	if (ENABLE_DEBUG) {
		console.error("[DEBUG]", ...args);
	}
}

// Expose globally for regular HTML script tags
if (typeof window !== "undefined") {
    window.log = log;
    window.error = error;
}