import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
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
    title: translate({
      id: 'pages.releaseWeek.releases.plans.title',
      message: 'New plans',
      description: 'Release week release title',
    }),
    description: translate({
      id: 'pages.releaseWeek.releases.plans.description',
      message:
        'OctoBot plans are evolving and come with more free features.',
      description: 'Release week release description',
    }),
  },
  {
    icon: '🎁',
    title: translate({
      id: 'pages.releaseWeek.releases.rewards.title',
      message: 'The new rewards system',
      description: 'Release week release title',
    }),
    description: translate({
      id: 'pages.releaseWeek.releases.rewards.description',
      message:
        'Discover the OctoBot reward system and unlock paid features for free.',
      description: 'Release week release description',
    }),
  },
  {
    icon: '📰',
    title: translate({
      id: 'pages.releaseWeek.releases.news.title',
      message: 'Customized crypto news',
      description: 'Release week release title',
    }),
    description: translate({
      id: 'pages.releaseWeek.releases.news.description',
      message:
        'Quickly follow all the crypto news you are interested in with OctoBot.',
      description: 'Release week release description',
    }),
  },
  {
    icon: '📊',
    title: translate({
      id: 'pages.releaseWeek.releases.supercharge.title',
      message: 'Supercharge your open-source OctoBot',
      description: 'Release week release title',
    }),
    description: translate({
      id: 'pages.releaseWeek.releases.supercharge.description',
      message:
        'Add the Strategy Designer, crypto baskets and much more to your OctoBot.',
      description: 'Release week release description',
    }),
  },
  {
    icon: '🍏',
    title: translate({
      id: 'pages.releaseWeek.releases.ios.title',
      message: 'New iOS mobile app',
      description: 'Release week release title',
    }),
    description: translate({
      id: 'pages.releaseWeek.releases.ios.description',
      message: 'Announcing the OctoBot iOS mobile app.',
      description: 'Release week release description',
    }),
  },
];

export default function ReleaseWeek(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.releaseWeek.meta.title',
        message: 'Release week',
        description: 'Release week page metadata title',
      })}
      description={translate({
        id: 'pages.releaseWeek.meta.description',
        message:
          'A week of new feature releases to make your crypto investment easier. Discover everything coming to OctoBot during release week.',
        description: 'Release week page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.releaseWeek.hero.eyebrow',
          message: 'Release week',
          description: 'Release week hero eyebrow',
        })}
        title={
          <>
            <span className="ng-text-gradient">
              <Translate
                id="pages.releaseWeek.hero.title"
                description="Release week hero title">
                OctoBot release week.
              </Translate>
            </span>
          </>
        }
        subtitle={translate({
          id: 'pages.releaseWeek.hero.subtitle',
          message:
            'A week of new feature releases to make your crypto investment easier.',
          description: 'Release week hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.releaseWeek.hero.action.join',
              message: 'Join the launch',
              description: 'Release week hero action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.releaseWeek.hero.action.watch',
              message: 'Watch the announcement',
              description: 'Release week hero action label',
            }),
            to: ANNOUNCEMENT,
            variant: 'ghost',
          },
        ]}
        note={translate({
          id: 'pages.releaseWeek.hero.note',
          message:
            'Enter your email on OctoBot App to be among the first notified when the next release week starts.',
          description: 'Release week hero note',
        })}
      />

      <Section
        eyebrow={translate({
          id: 'pages.releaseWeek.announcement.eyebrow',
          message: 'Announcement',
          description: 'Release week section eyebrow',
        })}
        title={translate({
          id: 'pages.releaseWeek.announcement.title',
          message: "What's coming this release week",
          description: 'Release week section title',
        })}>
        <YouTube
          id={ANNOUNCEMENT_ID}
          title={translate({
            id: 'pages.releaseWeek.announcement.videoTitle',
            message: 'OctoBot Release Week Announcement',
            description: 'Release week announcement video title',
          })}
        />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.releaseWeek.five.eyebrow',
          message: 'Five releases',
          description: 'Release week section eyebrow',
        })}
        title={translate({
          id: 'pages.releaseWeek.five.title',
          message: 'Five new features, one week',
          description: 'Release week section title',
        })}
        lead={translate({
          id: 'pages.releaseWeek.five.lead',
          message:
            'One release per day — new plans, a rewards system, customized crypto news, a supercharged open-source OctoBot and a brand-new iOS app.',
          description: 'Release week section lead',
        })}>
        <StepList steps={RELEASES} />
      </Section>

      <CTABand
        title={translate({
          id: 'pages.releaseWeek.cta.title',
          message: "Don't miss the next release week",
          description: 'Release week CTA title',
        })}
        description={translate({
          id: 'pages.releaseWeek.cta.description',
          message:
            'Join the launch on OctoBot App, or read the guides to get the most out of every new feature.',
          description: 'Release week CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.releaseWeek.cta.action.join',
              message: 'Join the launch',
              description: 'Release week CTA action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.releaseWeek.cta.action.guides',
              message: 'Read the guides',
              description: 'Release week CTA action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
