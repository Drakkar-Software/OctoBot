/**
 * <IdeaPage> — shared template for the SEO landing pages under
 * src/pages/features/ideas/.
 *
 * A route file builds one IdeaPageData object and renders <IdeaPage data={…}>.
 * The template composes the navbar-less LandingLayout from the landing toolkit
 * and walks the `sections` discriminated union, picking the matching component
 * per section `kind`. Section order and mix come from the data, so two pages
 * on this template can read structurally differently rather than as the same
 * page with swapped copy.
 */

import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  IconList,
  StatStrip,
  BeforeAfter,
  FAQ,
  CTABand,
  InlineStats,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import type {IdeaPageData, IdeaSection} from './types';
import styles from './styles.module.css';

function SectionBody({section}: {section: IdeaSection}): ReactNode {
  switch (section.kind) {
    case 'features':
      return (
        <FeatureGrid features={section.items} columns={section.columns ?? 3} />
      );
    case 'steps':
      return <StepList steps={section.items} layout={section.layout} />;
    case 'icons':
      return <IconList items={section.items} columns={section.columns ?? 2} />;
    case 'stats':
      return <StatStrip stats={section.items} />;
    case 'beforeAfter':
      return <BeforeAfter before={section.before} after={section.after} />;
    case 'faq':
      return <FAQ items={section.items} />;
    case 'callout':
      return (
        <GlassCard variant={section.variant ?? 'strong'} padded>
          {section.body}
        </GlassCard>
      );
  }
}

export default function IdeaPage({data}: {data: IdeaPageData}): ReactNode {
  const {meta, hero, sections, cta} = data;
  return (
    <LandingLayout title={meta.title} description={meta.description}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={hero.eyebrow}
        title={hero.title}
        subtitle={hero.subtitle}
        actions={hero.actions}
        visual={hero.visual}
        aside={hero.stats ? <InlineStats stats={hero.stats} /> : undefined}
      />

      {sections.map((section, index) => (
        <Section
          key={section.id ?? index}
          id={section.id}
          eyebrow={section.eyebrow}
          title={section.title}
          lead={section.lead}
          align={section.align}>
          <SectionBody section={section} />
        </Section>
      ))}

      <CTABand
        title={cta.title}
        description={cta.description}
        actions={cta.actions}
      />
    </LandingLayout>
  );
}
