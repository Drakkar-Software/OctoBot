import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  StepList,
  CTABand,
  type Step,
} from '@site/src/components/landing';
import YouTube from '@site/src/components/YouTube';
import styles from './release-week.module.css';

/*
 * OctoBot release week marketing page — route: /release-week.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. A navbar-less LandingLayout composed from the reusable
 * landing components: hero, announcement video, the five-release StepList
 * and a closing CTA band.
 */

const CLOUD = 'https://www.octobot.cloud';
const ANNOUNCEMENT = 'https://www.youtube.com/watch?v=gdfe5WRieKE';
const ANNOUNCEMENT_ID = 'gdfe5WRieKE';
const GUIDES = '/guides/octobot';

const RELEASES: Step[] = [
  {
    icon: '🪙',
    title: 'New plans',
    description:
      'OctoBot plans are evolving and come with more free features.',
  },
  {
    icon: '🎁',
    title: 'The new rewards system',
    description:
      'Discover the OctoBot reward system and unlock paid features for free.',
  },
  {
    icon: '📰',
    title: 'Customized crypto news',
    description:
      'Quickly follow all the crypto news you are interested in with OctoBot.',
  },
  {
    icon: '📊',
    title: 'Supercharge your open-source OctoBot',
    description:
      'Add the Strategy Designer, crypto baskets and much more to your OctoBot.',
  },
  {
    icon: '🍏',
    title: 'New iOS mobile app',
    description: 'Announcing the OctoBot iOS mobile app.',
  },
];

export default function ReleaseWeek(): ReactNode {
  return (
    <LandingLayout
      title="Release week"
      description="A week of new feature releases to make your crypto investment easier. Discover everything coming to OctoBot during release week.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Release week"
        title={
          <>
            <span className="ng-text-gradient">OctoBot release week.</span>
          </>
        }
        subtitle="A week of new feature releases to make your crypto investment easier."
        actions={[
          {label: 'Join the launch', to: CLOUD},
          {
            label: 'Watch the announcement',
            to: ANNOUNCEMENT,
            variant: 'ghost',
          },
        ]}
        note="Enter your email on OctoBot Cloud to be among the first notified when the next release week starts."
      />

      <Section
        eyebrow="Announcement"
        title="What's coming this release week">
        <YouTube
          id={ANNOUNCEMENT_ID}
          title="OctoBot Release Week Announcement"
        />
      </Section>

      <Section
        eyebrow="Five releases"
        title="Five new features, one week"
        lead="One release per day — new plans, a rewards system, customized crypto news, a supercharged open-source OctoBot and a brand-new iOS app.">
        <StepList steps={RELEASES} />
      </Section>

      <CTABand
        title="Don't miss the next release week"
        description="Join the launch on OctoBot Cloud, or read the guides to get the most out of every new feature."
        actions={[
          {label: 'Join the launch', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
