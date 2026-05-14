/**
 * Data shapes for the SEO "ideas" landing pages.
 *
 * Every route under src/pages/features/ideas/ is a thin file: it builds one
 * `IdeaPageData` object (strings wrapped in `translate()`) and hands it to the
 * shared <IdeaPage> template. The template owns all layout so the pages stay
 * consistent with the Neo Glass Dark toolkit — but the `sections` list is a
 * discriminated union, so each page can compose a different mix of section
 * types and avoid the doorway-page look that identical layouts produce.
 */

import type {ReactNode} from 'react';
import type {
  Feature,
  Step,
  IconListItem,
  Stat,
  FAQItem,
} from '@site/src/components/landing';

export interface IdeaAction {
  label: string;
  to: string;
  variant?: 'primary' | 'ghost' | 'surface';
}

export interface IdeaHero {
  eyebrow: string;
  title: ReactNode;
  subtitle: string;
  actions: IdeaAction[];
  /** Optional bespoke visual — usually one of the components in visuals.tsx. */
  visual?: ReactNode;
  /** Rendered as the hero `aside` InlineStats strip when present. */
  stats?: {value: ReactNode; label: string}[];
}

interface SectionBase {
  eyebrow?: string;
  title?: ReactNode;
  lead?: string;
  align?: 'left' | 'center' | 'right';
  id?: string;
}

/**
 * One page section. `kind` selects which landing component renders the body,
 * which is what lets two pages built from this template look structurally
 * different rather than like the same page with swapped copy.
 */
export type IdeaSection =
  | (SectionBase & {kind: 'features'; columns?: 2 | 3; items: Feature[]})
  | (SectionBase & {kind: 'steps'; layout?: 'row' | 'column'; items: Step[]})
  | (SectionBase & {kind: 'icons'; columns?: 1 | 2; items: IconListItem[]})
  | (SectionBase & {kind: 'stats'; items: Stat[]})
  | (SectionBase & {
      kind: 'beforeAfter';
      before: {label: string; items: ReactNode[]};
      after: {label: string; items: ReactNode[]};
    })
  | (SectionBase & {kind: 'faq'; items: FAQItem[]})
  | (SectionBase & {
      kind: 'callout';
      variant?: 'default' | 'strong';
      body: ReactNode;
    });

export interface IdeaCTA {
  title: ReactNode;
  description: string;
  actions: IdeaAction[];
}

export interface IdeaPageData {
  meta: {title: string; description: string};
  hero: IdeaHero;
  sections: IdeaSection[];
  cta: IdeaCTA;
}
