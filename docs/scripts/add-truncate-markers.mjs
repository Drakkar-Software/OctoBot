#!/usr/bin/env node
/**
 * Adds <!--truncate--> markers to blog posts that don't have one.
 *
 * Usage:
 *   node scripts/add-truncate-markers.mjs            # apply changes
 *   node scripts/add-truncate-markers.mjs --dry-run   # preview only
 */

import { readdir, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';

const BLOG_DIR = new URL('../blog', import.meta.url).pathname;
const DRY_RUN = process.argv.includes('--dry-run');

const TRUNCATE_MARKER = '<!--truncate-->';

async function main() {
  const files = (await readdir(BLOG_DIR))
    .filter(f => f.endsWith('.md') || f.endsWith('.mdx'))
    .sort();

  let modified = 0;
  let skipped = 0;

  for (const file of files) {
    const filepath = join(BLOG_DIR, file);
    const content = await readFile(filepath, 'utf-8');

    if (content.includes(TRUNCATE_MARKER)) {
      skipped++;
      continue;
    }

    const result = insertTruncateMarker(content, file);
    if (!result) {
      console.warn(`⚠  Could not find insertion point: ${file}`);
      continue;
    }

    modified++;
    if (DRY_RUN) {
      const lines = result.split('\n');
      const idx = lines.findIndex(l => l.trim() === TRUNCATE_MARKER);
      const start = Math.max(0, idx - 2);
      const end = Math.min(lines.length, idx + 3);
      console.log(`\n📝 ${file} (line ${idx + 1}):`);
      for (let i = start; i < end; i++) {
        const prefix = i === idx ? '>>>' : '   ';
        console.log(`  ${prefix} ${lines[i]}`);
      }
    } else {
      await writeFile(filepath, result, 'utf-8');
      console.log(`✅ ${file}`);
    }
  }

  console.log(`\n${DRY_RUN ? '[DRY RUN] ' : ''}Done: ${modified} modified, ${skipped} already had marker, ${files.length} total`);
}

function isBlank(line) {
  return line?.trim() === '';
}

function isHeading(line) {
  return /^#{1,6}\s/.test(line?.trim() ?? '');
}

function isImage(line) {
  return /^!\[.*\]\(.*\)/.test(line?.trim() ?? '');
}

function isImport(line) {
  return /^import\s/.test(line?.trim() ?? '');
}

function isJsxSelfClosing(line) {
  return /^<\w+[\s/].*\/>/.test(line?.trim() ?? '');
}

function isDivOpen(line) {
  return /<div[\s>]/.test(line?.trim() ?? '');
}

function isBlockquote(line) {
  return /^>/.test(line?.trim() ?? '');
}

function isList(line) {
  return /^[-*\d]/.test(line?.trim() ?? '');
}

function isHr(line) {
  return /^---+\s*$/.test(line?.trim() ?? '');
}

function isFrontmatterLike(line) {
  // Lines that look like YAML keys: "key: value" or "key:" — part of a double frontmatter block
  return /^\w[\w_]*\s*:/.test(line?.trim() ?? '');
}

/**
 * Insert <!--truncate--> after the first real content paragraph.
 */
function insertTruncateMarker(content, filename) {
  const lines = content.split('\n');
  let i = 0;

  // 1. Skip primary frontmatter block
  if (lines[i]?.trim() === '---') {
    i++;
    while (i < lines.length && lines[i]?.trim() !== '---') i++;
    i++; // past closing ---
  }

  // 2. Skip blank lines
  while (i < lines.length && isBlank(lines[i])) i++;

  // 3. Handle double frontmatter (legacy posts like 2024-01-01-*)
  //    If the next non-blank line is another `---`, skip the entire second block
  if (i < lines.length && isHr(lines[i])) {
    i++; // past opening ---
    while (i < lines.length && lines[i]?.trim() !== '---') i++;
    if (i < lines.length) i++; // past closing ---
    while (i < lines.length && isBlank(lines[i])) i++;
  }

  // 4. Skip broken/partial imports (like the lucide-react destructuring without `import {`)
  //    These are lines that are part of a JS destructuring before `from 'module'`
  if (i < lines.length && /^\s*\w+,?\s*$/.test(lines[i]) && !isHeading(lines[i])) {
    // Look ahead to see if there's a `from '...'` line nearby
    let j = i;
    while (j < lines.length && j < i + 15) {
      if (/}\s*from\s+['"]/.test(lines[j]) || /from\s+['"]/.test(lines[j])) {
        i = j + 1;
        while (i < lines.length && isBlank(lines[i])) i++;
        break;
      }
      j++;
    }
  }

  // 5. Collect all import statement positions (for MDX — must place truncate after ALL imports)
  let lastImportEnd = -1;
  for (let j = i; j < lines.length; j++) {
    if (isImport(lines[j])) {
      lastImportEnd = j + 1;
      // Handle multi-line imports
      if (!lines[j].includes('from') || lines[j].trim().endsWith('{')) {
        while (j + 1 < lines.length && !lines[j].includes('from')) j++;
        lastImportEnd = j + 1;
      }
    }
  }

  // Now walk through the content to find the first good truncation point
  // We want to find the first real text paragraph after preamble
  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line?.trim() ?? '';

    // Skip blank lines
    if (isBlank(line)) { i++; continue; }

    // Skip headings (# Title, ## Section, etc.)
    if (isHeading(line)) { i++; continue; }

    // Skip standalone images
    if (isImage(line)) { i++; continue; }

    // Skip import statements
    if (isImport(line)) {
      i++;
      // Skip multi-line imports
      while (i < lines.length && !lines[i - 1].includes('from')) i++;
      continue;
    }

    // Skip self-closing JSX components (<YouTube .../>, etc.)
    if (isJsxSelfClosing(line)) { i++; continue; }

    // Skip div blocks (cover images in divs)
    if (isDivOpen(line)) {
      while (i < lines.length && !lines[i].includes('</div>')) i++;
      if (i < lines.length) i++; // past </div>
      continue;
    }

    // Skip italic captions like _"Not your keys..."_
    if (/^_[""'"].*[""'"]_$/.test(trimmed)) { i++; continue; }

    // Skip horizontal rules
    if (isHr(line)) { i++; continue; }

    // Skip leftover YAML-like lines from double frontmatter
    if (isFrontmatterLike(line) && i < 25) { i++; continue; }

    // Found a real content line — this is the start of a paragraph
    break;
  }

  if (i >= lines.length) return null;

  // Find the end of this paragraph
  const paraStart = i;
  while (i < lines.length && !isBlank(lines[i]) && !isHeading(lines[i])) {
    // Stop at block elements that aren't continuation of the paragraph
    const trimmed = lines[i].trim();
    if (i > paraStart && (isDivOpen(lines[i]) || isImage(lines[i]) || isList(lines[i]))) break;
    i++;
  }

  if (i === paraStart) return null;

  // Ensure marker is placed AFTER all imports (MDX requirement)
  let insertAt = i;
  if (lastImportEnd > insertAt) {
    // Find first paragraph after last import
    insertAt = lastImportEnd;
    while (insertAt < lines.length && isBlank(lines[insertAt])) insertAt++;
    // Find end of that paragraph
    const paraStart2 = insertAt;
    while (insertAt < lines.length && !isBlank(lines[insertAt]) && !isHeading(lines[insertAt])) {
      if (insertAt > paraStart2 && (isDivOpen(lines[insertAt]) || isImage(lines[insertAt]))) break;
      insertAt++;
    }
    if (insertAt === paraStart2) return null;
  }

  lines.splice(insertAt, 0, '', TRUNCATE_MARKER);
  return lines.join('\n');
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
