#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import url from "node:url";
import { stripHttpImport, dateFieldsToString, enumBlockToUnion, narrowDiscriminatorField, collectVariantNarrowings } from "./postprocess-protocol-typescript.lib.mjs";

const protocolDir = path.dirname(path.dirname(url.fileURLToPath(import.meta.url)));
const modelsDir = path.join(protocolDir, "octobot_protocol_ts", "models");
const openapiPath = path.join(protocolDir, "openapi.json");

const openapi = JSON.parse(fs.readFileSync(openapiPath, "utf8"));
const narrowings = collectVariantNarrowings(openapi);

const files = fs.readdirSync(modelsDir).filter((f) => f.endsWith(".ts") && f !== "index.ts");
for (const file of files) {
  const full = path.join(modelsDir, file);
  const src = fs.readFileSync(full, "utf8");
  const variant = path.basename(file, ".ts");
  let next = stripHttpImport(src);
  next = dateFieldsToString(next);
  next = enumBlockToUnion(next);
  for (const { field, literal } of narrowings.get(variant) ?? []) {
    next = narrowDiscriminatorField(next, field, literal);
  }
  if (next !== src) fs.writeFileSync(full, next);
}

const barrel = files
  .map((f) => path.basename(f, ".ts"))
  .sort()
  .map((name) => `export * from "./${name}";`)
  .join("\n") + "\n";
fs.writeFileSync(path.join(modelsDir, "index.ts"), barrel);
