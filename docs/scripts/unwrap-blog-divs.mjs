#!/usr/bin/env node
/*
 * One-shot codemod: repairs a botched MDX->MD conversion across the docs
 * (English + French) blog and docs content.
 *
 * These are CommonMark .md files (not .mdx), so any raw JSX renders as literal
 * text: a `<div>` starts an HTML passthrough block (its markdown children are
 * not parsed), and unknown components (<Card>, <Rating>, <GoogleStoreButton>,
 * <AppleStoreButton>, ...) are not valid HTML at all.
 *
 * Transforms applied to every *.md file under the directories below:
 *   1. <div ...> wrappers (JSX `style={{}}` or HTML `style=""`, plain, nested)
 *      -> their unwrapped inner content. Centering is handled by CSS in
 *      src/css/custom.css.
 *   2. <Card>...<Rating .../>...</Card> review blocks -> a markdown list, each
 *      <Rating title level tooltipText/> becoming `- **title:** ★★☆ — tooltip`.
 *   3. <a href><GoogleStoreButton/></a> / <AppleStoreButton/> -> markdown link.
 *
 * .mdx files are intentionally skipped — they are real MDX and parse JSX fine.
 * Idempotent. Safe to delete after running; kept in-repo as a record.
 */
import {readFileSync, writeFileSync, readdirSync, statSync} from 'node:fs';
import {join, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const docsRoot = join(dirname(fileURLToPath(import.meta.url)), '..');
const TARGET_DIRS = [
  'blog',
  'content',
  'i18n/fr/docusaurus-plugin-content-blog',
  'i18n/fr/docusaurus-plugin-content-docs',
].map((d) => join(docsRoot, d));

/** Render a 1-3 rating level as filled / empty stars. */
function stars(level) {
  const n = Math.max(0, Math.min(3, Number(level) || 0));
  return '★'.repeat(n) + '☆'.repeat(3 - n);
}

/** Parse a single <Rating .../> tag body into a markdown bullet. */
function ratingToBullet(tag) {
  const title = tag.match(/title="([^"]*)"/)?.[1] ?? '';
  const level = tag.match(/level=\{(\d+)\}/)?.[1] ?? '0';
  const tip = tag.match(/tooltipText="([^"]*)"/)?.[1] ?? '';
  const tail = tip ? ` — ${tip}` : '';
  return `- **${title}:** ${stars(level)}${tail}`;
}

/** Replace every <Card>...</Card> block with a markdown rating list. */
function convertCards(text) {
  return text.replace(/<Card\b[^>]*>([\s\S]*?)<\/Card>/g, (_, inner) => {
    const bullets = [];
    inner.replace(/<Rating\b([\s\S]*?)\/>/g, (__, body) => {
      bullets.push(ratingToBullet(body));
      return '';
    });
    return bullets.join('\n');
  });
}

/** Replace <a ...><GoogleStoreButton/></a> / <AppleStoreButton/> with a link. */
function convertStoreButton(text) {
  return text
    .replace(
      /<a\s+href="([^"]*)"[^>]*>\s*<GoogleStoreButton\s*\/>\s*<\/a>/g,
      (_, href) => `[Get the OctoBot app on Google Play](${href})`,
    )
    .replace(
      /<a\s+href="([^"]*)"[^>]*>\s*<AppleStoreButton\s*\/>\s*<\/a>/g,
      (_, href) => `[Get the OctoBot app on the App Store](${href})`,
    );
}

/** Unwrap a <div ...>...</div> block, returning dedented inner lines. */
const DIV_OPEN = /^\s*<div\b[^>]*>\s*$/;
const DIV_CLOSE = /^\s*<\/div>\s*$/;

function unwrapDivs(text) {
  const lines = text.split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    if (!DIV_OPEN.test(lines[i])) {
      out.push(lines[i]);
      i++;
      continue;
    }
    let depth = 1;
    i++;
    const inner = [];
    while (i < lines.length && depth > 0) {
      const line = lines[i];
      if (DIV_OPEN.test(line)) {
        depth++;
      } else if (DIV_CLOSE.test(line)) {
        depth--;
        if (depth === 0) {
          i++;
          break;
        }
      } else {
        inner.push(line);
      }
      i++;
    }
    const trimmed = inner.map((l) => l.replace(/\s+$/, ''));
    while (trimmed.length && trimmed[0].trim() === '') trimmed.shift();
    while (trimmed.length && trimmed[trimmed.length - 1].trim() === '') {
      trimmed.pop();
    }
    const indents = trimmed
      .filter((l) => l.trim() !== '')
      .map((l) => l.match(/^\s*/)[0].length);
    const minIndent = indents.length ? Math.min(...indents) : 0;
    const dedented = trimmed.map((l) => l.slice(minIndent));
    if (out.length && out[out.length - 1].trim() !== '') out.push('');
    out.push(...dedented, '');
  }
  return out.join('\n');
}

/** Collapse runs of 3+ blank lines down to a single blank line. */
function collapseBlanks(text) {
  return text.replace(/\n{3,}/g, '\n\n');
}

/** Recursively yield every .md file path under a directory. */
function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) {
      yield* walk(full);
    } else if (entry.endsWith('.md')) {
      yield full;
    }
  }
}

let changed = 0;
for (const dir of TARGET_DIRS) {
  for (const path of walk(dir)) {
    const original = readFileSync(path, 'utf8');
    let next = convertCards(original);
    next = convertStoreButton(next);
    next = unwrapDivs(next);
    // Only normalize blank lines on files that actually had JSX repaired —
    // avoids touching files whose only "change" would be whitespace.
    if (next === original) continue;
    next = collapseBlanks(next);
    writeFileSync(path, next);
    changed++;
    console.log(`fixed: ${path.slice(docsRoot.length + 1)}`);
  }
}
console.log(`\n${changed} file(s) changed.`);
