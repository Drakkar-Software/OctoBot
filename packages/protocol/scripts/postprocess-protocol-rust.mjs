#!/usr/bin/env node
/**
 * Regenerates the crate entrypoints that `--global-property models` skips:
 *   - src/models/mod.rs : one `pub mod` + `pub use` line per generated model
 *   - src/lib.rs        : crate root exposing the models module
 * Both are derived from the files present, so they never drift from the schema.
 */
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const protocolDir = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
const crateDir = path.join(protocolDir, "crates", "octobot_protocol_rs");
const modelsDir = path.join(crateDir, "src", "models");

const primaryTypePattern = /^pub (?:struct|enum) (\w+)/m;

// openapi-generator (rust) builds the variant name for an untagged oneOf/anyOf
// array branch by concatenating "Array" + the inner Rust type, producing an
// invalid identifier, e.g. `ArrayVecserde_json::Value(Vec<serde_json::Value>)`.
// Rename such branches to a valid `Array(...)` variant. Untagged enums serialize
// by value, so the variant name never appears on the wire — this is safe.
function fixOneOfArrayVariant(src) {
  return src.replace(/^(\s*)Array\S*?(\(Vec<[^\n]*>\),?)\s*$/gm, "$1Array$2");
}

const modules = fs
  .readdirSync(modelsDir)
  .filter((f) => f.endsWith(".rs") && f !== "mod.rs")
  .map((f) => path.basename(f, ".rs"))
  .sort();

const modLines = modules.map((module) => {
  const modelPath = path.join(modelsDir, `${module}.rs`);
  const original = fs.readFileSync(modelPath, "utf8");
  const fixed = fixOneOfArrayVariant(original);
  if (fixed !== original) fs.writeFileSync(modelPath, fixed);
  const src = fixed;
  const match = src.match(primaryTypePattern);
  if (!match) {
    throw new Error(`No pub struct/enum found in models/${module}.rs`);
  }
  return `pub mod ${module};\npub use self::${module}::${match[1]};`;
});

fs.writeFileSync(path.join(modelsDir, "mod.rs"), modLines.join("\n") + "\n");

const libRs = `#![allow(unused_imports)]
#![allow(clippy::all)]

pub mod models;
`;
fs.writeFileSync(path.join(crateDir, "src", "lib.rs"), libRs);
