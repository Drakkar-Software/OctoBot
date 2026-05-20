import React, {type ReactNode} from 'react';
import Head from '@docusaurus/Head';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import {useBaseUrlUtils} from '@docusaurus/useBaseUrl';

/**
 * Structured-data (JSON-LD) helpers for the standalone landing / programmatic
 * pages. These pages bypass the docs theme Layout, so they get no schema.org
 * markup beyond the global SoftwareApplication block — these components add
 * the per-page schemas (FAQ, breadcrumbs) that earn rich results.
 *
 * Each schema is emitted into the document head through `@docusaurus/Head`.
 */

export interface FaqJsonLdItem {
  question: string;
  answer: string;
}

export interface BreadcrumbCrumb {
  /** Visible breadcrumb label. */
  name: string;
  /** Site-root-relative path, e.g. `/what-is-bitcoin`. */
  path: string;
}

// Escape `<` so a stray "</script>" inside any string can never close the
// tag early — the canonical way to inline JSON-LD safely.
function serialize(schema: object): string {
  return JSON.stringify(schema).replace(/</g, '\\u003c');
}

export function JsonLd({schema}: {schema: object}): ReactNode {
  return (
    <Head>
      <script type="application/ld+json">{serialize(schema)}</script>
    </Head>
  );
}

/** schema.org FAQPage — only emitted when there is at least one Q&A. */
export function FaqJsonLd({
  items,
}: {
  items: readonly FaqJsonLdItem[];
}): ReactNode {
  if (items.length === 0) {
    return null;
  }
  return (
    <JsonLd
      schema={{
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: items.map((item) => ({
          '@type': 'Question',
          name: item.question,
          acceptedAnswer: {'@type': 'Answer', text: item.answer},
        })),
      }}
    />
  );
}

/**
 * schema.org BreadcrumbList. The site root is prepended automatically, so
 * callers pass only the trailing crumb(s). URLs are resolved to absolute,
 * locale-aware links via `withBaseUrl`.
 */
export function BreadcrumbsJsonLd({
  trail,
}: {
  trail: readonly BreadcrumbCrumb[];
}): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  const {withBaseUrl} = useBaseUrlUtils();
  const crumbs: BreadcrumbCrumb[] = [
    {name: siteConfig.title, path: '/'},
    ...trail,
  ];
  return (
    <JsonLd
      schema={{
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        itemListElement: crumbs.map((crumb, index) => ({
          '@type': 'ListItem',
          position: index + 1,
          name: crumb.name,
          item: withBaseUrl(crumb.path, {absolute: true}),
        })),
      }}
    />
  );
}
