#!/usr/bin/env node
/**
 * Removes generated artifacts before openapi-generator runs.
 * Hand-written compat tests live in test/compat/; test/ only loses root __init__.py and test_*.py.
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const protocolDir = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));

function cleanDirectory(dir, { keep = [], only = null } = {}) {
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    return;
  }
  const keepSet = new Set(keep);
  for (const entryName of fs.readdirSync(dir)) {
    if (keepSet.has(entryName)) continue;
    if (only && !only(entryName)) continue;
    fs.rmSync(path.join(dir, entryName), { recursive: true, force: true });
  }
}

const isGeneratedPythonTest = (entryName) =>
  entryName === "__init__.py" ||
  (entryName.startsWith("test_") && entryName.endsWith(".py"));

const cleaners = {
  python: () => {
    cleanDirectory(path.join(protocolDir, "octobot_protocol"));
    cleanDirectory(path.join(protocolDir, "test"), { only: isGeneratedPythonTest, keep: ["compat"] });
    cleanDirectory(path.join(protocolDir, "docs"));
  },
  typescript: () => {
    cleanDirectory(path.join(protocolDir, "octobot_protocol_ts"), { keep: ["package.json"] });
  },
  rust: () => {
    cleanDirectory(path.join(protocolDir, "octobot_protocol_rs"));
  },
};

const mode = process.argv[2];
if (!mode) {
  for (const runCleaner of Object.values(cleaners)) {
    runCleaner();
  }
} else if (cleaners[mode]) {
  cleaners[mode]();
} else {
  console.error("Usage: clean-protocol-codegen-output.mjs [python|typescript|rust]");
  process.exit(1);
}
