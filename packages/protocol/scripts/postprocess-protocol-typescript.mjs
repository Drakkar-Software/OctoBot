#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import url from "node:url";

const protocolDir = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
const modelsDir = path.join(protocolDir, "octobot_protocol_ts", "models");

const HTTP_IMPORT = /^import \{ HttpFile \} from '\.\.\/http\/http';\n/m;
const DATE_FIELD = /^(\s*'[^']+'?\??:\s*)Date\b/gm;
const ENUM_BLOCK = /export enum (\w+) \{([^}]+)\}/g;

function enumBodyToUnion(body) {
  return body
    .split(",")
    .map((line) => {
      const match = line.match(/=\s*'([^']*)'/);
      return match ? `'${match[1]}'` : null;
    })
    .filter(Boolean)
    .join(" | ");
}

const files = fs.readdirSync(modelsDir).filter((f) => f.endsWith(".ts") && f !== "index.ts");
for (const file of files) {
  const full = path.join(modelsDir, file);
  const src = fs.readFileSync(full, "utf8");
  let next = src.replace(HTTP_IMPORT, "").replace(DATE_FIELD, "$1string");
  next = next.replace(ENUM_BLOCK, (whole, name, body) => {
    const union = enumBodyToUnion(body);
    return union ? `export type ${name} = ${union}` : whole;
  });
  if (next !== src) fs.writeFileSync(full, next);
}

const barrel = files
  .map((f) => path.basename(f, ".ts"))
  .sort()
  .map((name) => `export * from "./${name}";`)
  .join("\n") + "\n";
fs.writeFileSync(path.join(modelsDir, "index.ts"), barrel);
