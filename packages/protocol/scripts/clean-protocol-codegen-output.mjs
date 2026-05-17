#!/usr/bin/env node
/**
 * Removes generated artifacts under octobot_protocol / octobot_protocol_ts /
 * octobot_protocol_rs / test (Python model tests)
 * before openapi-generator runs so stale files do not linger.
 */

import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const protocolDir = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));

const targets = {
  python: {
    dir: path.join(protocolDir, "octobot_protocol"),
    keep: new Set(),
  },
  typescript: {
    dir: path.join(protocolDir, "octobot_protocol_ts"),
    keep: new Set(["package.json"]),
  },
  rust: {
    dir: path.join(protocolDir, "octobot_protocol_rs"),
    keep: new Set(),
  },
  test: {
    dir: path.join(protocolDir, "test"),
    keep: new Set(),
    keepPredicate: (name) => name.endsWith(".mjs"),
  },
};

function cleanTarget(key) {
  const config = targets[key];
  if (!config) {
    console.error(
      "Usage: clean-protocol-codegen-output.mjs <python|typescript|rust|test|all>",
    );
    process.exit(1);
  }
  const { dir, keep, keepPredicate } = config;
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
    return;
  }
  for (const entryName of fs.readdirSync(dir)) {
    if (keep.has(entryName)) continue;
    if (keepPredicate && keepPredicate(entryName)) continue;
    fs.rmSync(path.join(dir, entryName), { recursive: true, force: true });
  }
}

const mode = process.argv[2] ?? "all";
if (mode === "all") {
  cleanTarget("python");
  cleanTarget("typescript");
  cleanTarget("rust");
  cleanTarget("test");
} else if (mode === "python") {
  cleanTarget("python");
  cleanTarget("test");
} else {
  cleanTarget(mode);
}
