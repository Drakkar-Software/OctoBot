// collect-infra-docs.mjs
//
// Collects documentation from infra/*/docs/ directories
// and falls back to infra/*/README.md into docs/content/developers/infrastructure/.
// Mirrors the packages/* docs pattern for infrastructure components.

import {readdir, readFile, writeFile, mkdir, stat} from 'node:fs/promises';
import {join, basename, dirname, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const INFRA_DIR = join(ROOT, 'infra');
const OUTPUT_DIR = join(__dirname, '..', 'content', 'developers', 'infrastructure');

/**
 * Convert a name to a URL-friendly slug.
 */
function toSlug(name) {
  return name
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/[_\s]+/g, '-')
    .toLowerCase();
}

/**
 * Generate a human-readable title from a directory name.
 */
function toTitle(name) {
  return name
    .replace(/[-_]+/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

/**
 * Build frontmatter for an infrastructure doc page.
 */
function buildFrontmatter(title, slug, description) {
  return `---
title: "${title}"
description: "${description.replace(/"/g, '\\"')}"
keywords: ["octobot", "developers", "infrastructure", "${slug}"]
slug: /developers/infrastructure/${slug}
format: md
---`;
}

/**
 * Extract a description from markdown content (first non-heading paragraph, max 160 chars).
 */
function extractDescription(content, title) {
  // Take only the first contiguous paragraph (stop at first blank line after content starts)
  const paragraphLines = [];
  let started = false;
  for (const line of content.split('\n')) {
    const trimmed = line.trim();
    if (!started) {
      if (trimmed && !trimmed.startsWith('#') && !trimmed.startsWith('---')) {
        started = true;
        paragraphLines.push(trimmed);
      }
    } else {
      if (!trimmed || trimmed.startsWith('#')) break;
      paragraphLines.push(trimmed);
    }
  }
  const firstParagraph = paragraphLines.join(' ').replace(/\s+/g, ' ').trim();

  if (firstParagraph.length > 10 && firstParagraph.length <= 160) {
    return firstParagraph;
  }
  if (firstParagraph.length > 160) {
    return firstParagraph.substring(0, 157) + '...';
  }
  return `${title} - OctoBot infrastructure documentation`;
}

/**
 * Check if a path exists.
 */
async function exists(path) {
  try {
    await stat(path);
    return true;
  } catch {
    return false;
  }
}

/**
 * Collect .md files from a docs/ directory.
 */
async function collectDocsDir(docsDir, componentName) {
  const results = [];
  const entries = await readdir(docsDir, {withFileTypes: true});

  for (const entry of entries) {
    if (entry.isFile() && entry.name.endsWith('.md')) {
      results.push({
        path: join(docsDir, entry.name),
        name: entry.name === 'index.md' ? componentName : basename(entry.name, '.md'),
        isIndex: entry.name === 'index.md',
      });
    }
  }

  return results;
}

async function main() {
  console.log('Collecting infrastructure documentation...');

  if (!(await exists(INFRA_DIR))) {
    console.warn(`Warning: ${INFRA_DIR} not found. Skipping infrastructure collection.`);
    return;
  }

  await mkdir(OUTPUT_DIR, {recursive: true});

  const components = await readdir(INFRA_DIR, {withFileTypes: true});
  let processed = 0;

  for (const component of components) {
    if (!component.isDirectory()) continue;

    const componentName = component.name;
    const componentDir = join(INFRA_DIR, componentName);
    const docsDir = join(componentDir, 'docs');
    const readmePath = join(componentDir, 'README.md');

    let files = [];

    // Priority 1: infra/<name>/docs/*.md
    if (await exists(docsDir)) {
      files = await collectDocsDir(docsDir, componentName);
    }
    // Priority 2: infra/<name>/README.md as fallback
    else if (await exists(readmePath)) {
      files = [{path: readmePath, name: componentName, isIndex: true}];
    }

    if (files.length === 0) {
      console.log(`  Skipping ${componentName}: no docs/ or README.md found.`);
      continue;
    }

    for (const file of files) {
      let content = await readFile(file.path, 'utf-8');

      // Strip existing frontmatter
      if (content.startsWith('---')) {
        const endIdx = content.indexOf('---', 3);
        if (endIdx !== -1) {
          content = content.substring(endIdx + 3).trim();
        }
      }

      const title = toTitle(file.name);
      const slug = toSlug(file.name);
      const description = extractDescription(content, title);
      const frontmatter = buildFrontmatter(title, slug, description);

      const output = `${frontmatter}\n\n${content}\n`;
      const outputPath = join(OUTPUT_DIR, `${slug}.md`);
      await writeFile(outputPath, output, 'utf-8');
      console.log(`  infra/${componentName}/${relative(componentDir, file.path)} → content/developers/infrastructure/${slug}.md`);
      processed++;
    }
  }

  // Write _category_.json for sidebar
  const categoryJson = JSON.stringify(
    {
      label: 'Infrastructure',
      position: 4,
      link: {type: 'generated-index', description: 'OctoBot infrastructure components documentation.'},
    },
    null,
    2,
  );
  await writeFile(join(OUTPUT_DIR, '_category_.json'), categoryJson, 'utf-8');

  console.log(`Processed ${processed} infrastructure docs.`);
}

main().catch(err => {
  console.error('Failed to collect infrastructure docs:', err);
  process.exit(1);
});
