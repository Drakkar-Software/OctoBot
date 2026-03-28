/**
 * collect-tentacles.mjs
 *
 * Walks packages/tentacles/ and collects resource .md files into
 * audience-based content directories.
 *
 * Routing:
 *   Trading/Mode       → content/creators/trading-modes/
 *   Trading/Exchange    → content/users/exchanges/
 *   Evaluator/*         → content/creators/evaluators/
 */

import {readdir, readFile, writeFile, mkdir, stat} from 'node:fs/promises';
import {join, basename, dirname, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const TENTACLES_DIR = join(ROOT, 'packages', 'tentacles');
const CONTENT_DIR = join(__dirname, '..', 'content');

/**
 * Maps tentacle directory paths to output categories.
 */
const CATEGORY_MAP = {
  'Trading/Mode': {
    audience: 'creators',
    dir: 'trading-modes',
    label: 'Trading Modes',
    description: 'Trading strategies and modes available in OctoBot',
    keywords: ['trading modes', 'strategies', 'octobot'],
    slugBase: 'creators/trading-modes',
    position: 2,
  },
  'Trading/Exchange': {
    audience: 'users',
    dir: 'exchanges',
    label: 'Exchanges',
    description: 'Supported cryptocurrency exchanges for OctoBot trading',
    keywords: ['exchanges', 'crypto', 'octobot', 'connectors'],
    slugBase: 'users/exchanges',
    position: 4,
  },
  'Evaluator/TA': {
    audience: 'creators',
    dir: 'evaluators/ta',
    label: 'Technical Analysis',
    description: 'Technical analysis evaluators for OctoBot trading signals',
    keywords: ['technical analysis', 'evaluators', 'indicators', 'octobot'],
    slugBase: 'creators/evaluators/ta',
    position: 4,
  },
  'Evaluator/Social': {
    audience: 'creators',
    dir: 'evaluators/social',
    label: 'Social Evaluators',
    description: 'Social signal evaluators including news, sentiment, and trends',
    keywords: ['social evaluators', 'sentiment', 'news', 'octobot'],
    slugBase: 'creators/evaluators/social',
    position: 5,
  },
  'Evaluator/RealTime': {
    audience: 'creators',
    dir: 'evaluators/realtime',
    label: 'Real-Time Evaluators',
    description: 'Real-time market evaluators for instant signal detection',
    keywords: ['realtime evaluators', 'instant', 'octobot'],
    slugBase: 'creators/evaluators/realtime',
    position: 6,
  },
  'Evaluator/Strategies': {
    audience: 'creators',
    dir: 'evaluators/strategies',
    label: 'Strategy Evaluators',
    description: 'Strategy evaluators that combine multiple signals into trading decisions',
    keywords: ['strategy evaluators', 'combined signals', 'octobot'],
    slugBase: 'creators/evaluators/strategies',
    position: 7,
  },
};

/**
 * Convert a PascalCase/camelCase name to a URL-friendly slug.
 */
function toSlug(name) {
  return name
    .replace(/([a-z])([A-Z])/g, '$1-$2')
    .replace(/[_\s]+/g, '-')
    .toLowerCase();
}

/**
 * Generate a human-readable title from a filename.
 * e.g. "GridTradingMode" → "Grid Trading Mode"
 */
function toTitle(name) {
  return name
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_]+/g, ' ')
    .replace(/\b(Evaluator|Mode)\b/g, '$1')
    .trim();
}

/**
 * Truncate or generate a description that fits 150-160 chars for SEO.
 */
function makeDescription(content, title) {
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
  return `${title} - OctoBot tentacle documentation and configuration guide`;
}

/**
 * Recursively find all .md files under a directory matching resources/*.md pattern.
 */
async function findResourceMdFiles(dir) {
  const results = [];

  async function walk(current) {
    let entries;
    try {
      entries = await readdir(current, {withFileTypes: true});
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = join(current, entry.name);
      if (entry.isDirectory()) {
        await walk(fullPath);
      } else if (entry.isFile() && entry.name.endsWith('.md')) {
        const relPath = relative(TENTACLES_DIR, fullPath);
        if (relPath.includes('/resources/')) {
          results.push(fullPath);
        }
      }
    }
  }

  await walk(dir);
  return results;
}

/**
 * Determine the category for a resource .md file based on its path.
 */
function getCategory(filePath) {
  const rel = relative(TENTACLES_DIR, filePath);
  for (const [prefix, config] of Object.entries(CATEGORY_MAP)) {
    if (rel.startsWith(prefix)) {
      return {prefix, ...config};
    }
  }
  return null;
}

/**
 * Process a single .md file: read content, add frontmatter, write to output.
 */
async function processFile(filePath, category) {
  const rawContent = await readFile(filePath, 'utf-8');
  const name = basename(filePath, '.md');
  const slug = toSlug(name);
  const title = toTitle(name);

  // Strip existing frontmatter if present
  let content = rawContent;
  if (content.startsWith('---')) {
    const endIdx = content.indexOf('---', 3);
    if (endIdx !== -1) {
      content = content.substring(endIdx + 3).trim();
    }
  }

  const description = makeDescription(content, title);

  const frontmatter = `---
title: "${title}"
description: "${description.replace(/"/g, '\\"')}"
keywords: [${category.keywords.map(k => `"${k}"`).join(', ')}, "${slug}"]
slug: /${category.slugBase}/${slug}
format: md
---`;

  const output = `${frontmatter}\n\n${content}\n`;
  const outputDir = join(CONTENT_DIR, category.audience, category.dir);
  await mkdir(outputDir, {recursive: true});
  await writeFile(join(outputDir, `${slug}.md`), output, 'utf-8');

  return {title, slug, category: category.label};
}

/**
 * Generate _category_.json files for sidebar grouping.
 */
async function writeCategoryJson(dir, label, position) {
  await mkdir(dir, {recursive: true});
  const json = JSON.stringify(
    {label, position, link: {type: 'generated-index', description: `${label} available in OctoBot.`}},
    null,
    2
  );
  await writeFile(join(dir, '_category_.json'), json, 'utf-8');
}

async function main() {
  console.log('Collecting tentacle documentation...');

  // Check if tentacles directory exists
  try {
    await stat(TENTACLES_DIR);
  } catch {
    console.warn(`Warning: ${TENTACLES_DIR} not found. Skipping tentacle collection.`);
    return;
  }

  const mdFiles = await findResourceMdFiles(TENTACLES_DIR);
  console.log(`Found ${mdFiles.length} tentacle resource files.`);

  // Write category.json files
  for (const [, config] of Object.entries(CATEGORY_MAP)) {
    const dir = join(CONTENT_DIR, config.audience, config.dir);
    await writeCategoryJson(dir, config.label, config.position);
  }

  // Also create evaluators parent category under creators
  await writeCategoryJson(join(CONTENT_DIR, 'creators', 'evaluators'), 'Evaluators', 3);

  // Process all files
  let processed = 0;
  const errors = [];

  for (const filePath of mdFiles) {
    const category = getCategory(filePath);
    if (!category) {
      console.warn(`  Skipping (no category): ${relative(TENTACLES_DIR, filePath)}`);
      continue;
    }

    try {
      await processFile(filePath, category);
      processed++;
    } catch (err) {
      errors.push({file: filePath, error: err.message});
    }
  }

  console.log(`Processed ${processed} tentacle docs.`);
  if (errors.length > 0) {
    console.warn(`Errors (${errors.length}):`);
    for (const {file, error} of errors) {
      console.warn(`  ${relative(ROOT, file)}: ${error}`);
    }
  }
}

main().catch(err => {
  console.error('Failed to collect tentacles:', err);
  process.exit(1);
});
