/**
 * collect-tentacles.mjs
 *
 * Walks packages/tentacles/ and collects resource .md files into
 * audience-based content directories.
 */

import {readFile, writeFile, mkdir, stat} from 'node:fs/promises';
import {join, basename, dirname, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {extractDescription, escapeYaml, toSlug, stripFrontmatter, findMdFiles} from './shared.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..', '..');
const TENTACLES_DIR = join(ROOT, 'packages', 'tentacles');
const CONTENT_DIR = join(__dirname, '..', 'content');

const CATEGORY_MAP = {
  'Trading/Mode': {
    audience: 'guides/strategies',
    dir: 'trading-modes',
    label: 'Trading Modes',
    description: 'Trading strategies and modes available in OctoBot',
    keywords: ['trading modes', 'strategies', 'octobot'],
    slugBase: 'guides/strategies/trading-modes',
    position: 2,
  },
  'Trading/Exchange': {
    audience: 'guides',
    dir: 'exchanges',
    label: 'Exchanges',
    description: 'Supported cryptocurrency exchanges for OctoBot trading',
    keywords: ['exchanges', 'crypto', 'octobot', 'connectors'],
    slugBase: 'guides/exchanges',
    position: 4,
  },
  'Evaluator/TA': {
    audience: 'guides/strategies',
    dir: 'evaluators/ta',
    label: 'Technical Analysis',
    description: 'Technical analysis evaluators for OctoBot trading signals',
    keywords: ['technical analysis', 'evaluators', 'indicators', 'octobot'],
    slugBase: 'guides/strategies/evaluators/ta',
    position: 4,
  },
  'Evaluator/Social': {
    audience: 'guides/strategies',
    dir: 'evaluators/social',
    label: 'Social Evaluators',
    description: 'Social signal evaluators including news, sentiment, and trends',
    keywords: ['social evaluators', 'sentiment', 'news', 'octobot'],
    slugBase: 'guides/strategies/evaluators/social',
    position: 5,
  },
  'Evaluator/RealTime': {
    audience: 'guides/strategies',
    dir: 'evaluators/realtime',
    label: 'Real-Time Evaluators',
    description: 'Real-time market evaluators for instant signal detection',
    keywords: ['realtime evaluators', 'instant', 'octobot'],
    slugBase: 'guides/strategies/evaluators/realtime',
    position: 6,
  },
  'Evaluator/Strategies': {
    audience: 'guides/strategies',
    dir: 'evaluators/strategies',
    label: 'Strategy Evaluators',
    description: 'Strategy evaluators that combine multiple signals into trading decisions',
    keywords: ['strategy evaluators', 'combined signals', 'octobot'],
    slugBase: 'guides/strategies/evaluators/strategies',
    position: 7,
  },
};

/** Generate a human-readable title from a filename. e.g. "GridTradingMode" -> "Grid Trading Mode" */
function toTitle(name) {
  return name
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/[_]+/g, ' ')
    .trim();
}

function getCategory(filePath) {
  const rel = relative(TENTACLES_DIR, filePath);
  for (const [prefix, config] of Object.entries(CATEGORY_MAP)) {
    if (rel.startsWith(prefix)) {
      return {prefix, ...config};
    }
  }
  return null;
}

async function processFile(filePath, category) {
  const rawContent = await readFile(filePath, 'utf-8');
  const name = basename(filePath, '.md');
  const slug = toSlug(name);
  const title = toTitle(name);
  const content = stripFrontmatter(rawContent);

  const description = extractDescription(content, `${title} - OctoBot tentacle documentation and configuration guide`);

  const frontmatter = `---
title: "${escapeYaml(title)}"
description: "${escapeYaml(description)}"
keywords: [${category.keywords.map(k => `"${k}"`).join(', ')}, "${slug}"]
slug: /${category.slugBase}/${slug}
format: md
---`;

  const output = `${frontmatter}\n\n${content}\n`;
  const outputDir = join(CONTENT_DIR, category.audience, category.dir);
  await mkdir(outputDir, {recursive: true});
  await writeFile(join(outputDir, `${slug}.md`), output, 'utf-8');
}

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

  const mdFiles = await findMdFiles(TENTACLES_DIR, p => relative(TENTACLES_DIR, p).includes('/resources/'));
  console.log(`Found ${mdFiles.length} tentacle resource files.`);

  for (const config of Object.values(CATEGORY_MAP)) {
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
    console.error(`Errors (${errors.length}):`);
    for (const {file, error} of errors) {
      console.error(`  ${relative(ROOT, file)}: ${error}`);
    }
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Failed to collect tentacles:', err);
  process.exit(1);
});
