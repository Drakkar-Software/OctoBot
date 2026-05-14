import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/trading-platform-for-fintechs
 * Angle: audience page for fintechs — speaks to fintech-specific concerns, then defers full platform detail to /whitelabel. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.forFintechs.meta.title',
      message: 'Trading Platform for Fintechs — Run it in your own infrastructure',
      description: 'Fintechs page meta title',
    }),
    description: translate({
      id: 'pages.ideas.forFintechs.meta.description',
      message:
        'A trading platform built for fintechs — open-source, deployed in your own VPC, under your brand, with no vendor in the hot path.',
      description: 'Fintechs page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.forFintechs.hero.eyebrow',
      message: 'For fintechs',
      description: 'Fintechs hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.forFintechs.hero.title"
        description="Fintechs hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.forFintechs.hero.title.accent',
                message: 'on your terms.',
                description: 'Fintechs hero title accent',
              })}
            </span>
          ),
        }}>
        {'A trading platform that runs {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.forFintechs.hero.subtitle',
      message:
        'Adding automated trading to a fintech product raises questions a SaaS vendor can’t answer well: where does it run, who can read the code, whose brand is on it. OctoBot is open-source and deploys inside your own infrastructure — so the answers are yours.',
      description: 'Fintechs hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forFintechs.hero.action.demo',
          message: 'Book a demo',
          description: 'Fintechs hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forFintechs.hero.action.whitelabel',
          message: 'See the full platform',
          description: 'Fintechs hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.forFintechs.visual.label',
          message: 'Inside your VPC',
          description: 'Fintechs visual label',
        })}
        note={translate({
          id: 'pages.ideas.forFintechs.visual.note',
          message: 'your tenancy · your brand',
          description: 'Fintechs visual note',
        })}
        lines={[
          {width: 60},
          {width: 88, accent: true},
          {width: 50},
          {width: 74, accent: true},
        ]}
        cta={translate({
          id: 'pages.ideas.forFintechs.visual.cta',
          message: 'Deploy in your cloud',
          description: 'Fintechs visual CTA',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'icons',
      eyebrow: translate({
        id: 'pages.ideas.forFintechs.needs.eyebrow',
        message: 'What fintechs actually ask',
        description: 'Fintechs section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forFintechs.needs.title',
        message: 'The concerns that decide whether you can ship it',
        description: 'Fintechs section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🔍',
          text: translate({
            id: 'pages.ideas.forFintechs.needs.source',
            message:
              'Compliance can read the source. The core is open-source — auditable before you sign anything, not a black box you have to take on trust.',
            description: 'Fintechs icon item',
          }),
        },
        {
          icon: '🏗️',
          text: translate({
            id: 'pages.ideas.forFintechs.needs.vpc',
            message:
              'It runs in your own VPC and tenancy. No multi-tenant SaaS, no customer data crossing a vendor boundary.',
            description: 'Fintechs icon item',
          }),
        },
        {
          icon: '🏷️',
          text: translate({
            id: 'pages.ideas.forFintechs.needs.brand',
            message:
              'Your brand, end to end. Users see your product — the engine behind it stays invisible.',
            description: 'Fintechs icon item',
          }),
        },
        {
          icon: '⚡',
          text: translate({
            id: 'pages.ideas.forFintechs.needs.hotPath',
            message:
              'No vendor in the hot path. Order execution doesn’t depend on a third party’s uptime or rate limits.',
            description: 'Fintechs icon item',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      variant: 'strong',
      eyebrow: translate({
        id: 'pages.ideas.forFintechs.more.eyebrow',
        message: 'Where to go next',
        description: 'Fintechs section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.forFintechs.more.title',
        message: 'The full platform breakdown lives on the Whitelabel page',
        description: 'Fintechs section title',
      }),
      body: (
        <Translate
          id="pages.ideas.forFintechs.more.body"
          description="Fintechs callout body deferring to whitelabel"
          values={{
            link: (
              <a href="/whitelabel">
                {translate({
                  id: 'pages.ideas.forFintechs.more.body.link',
                  message: 'the Whitelabel page',
                  description: 'Fintechs callout link text',
                })}
              </a>
            ),
          }}>
          {
            'This page only covers the fintech-specific concerns. The engine, execution layer, frontend modes, deployment model and commercials are all laid out in full on {link} — start there for the complete picture.'
          }
        </Translate>
      ),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.forFintechs.faq.title',
        message: 'Fintech questions',
        description: 'Fintechs FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.forFintechs.faq.q1',
            message: 'Where does it run?',
            description: 'Fintechs FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forFintechs.faq.a1',
            message:
              'Inside your own infrastructure — cloud, bare-metal or air-gapped. It is not a hosted service you call out to.',
            description: 'Fintechs FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forFintechs.faq.q2',
            message: 'Can our compliance team review it?',
            description: 'Fintechs FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forFintechs.faq.a2',
            message:
              'Yes. OctoBot’s core is open-source, so your compliance and security teams can audit the code directly before any commitment.',
            description: 'Fintechs FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.forFintechs.faq.q3',
            message: 'Where do I see the whole platform?',
            description: 'Fintechs FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.forFintechs.faq.a3',
            message:
              'The Whitelabel page covers the engine, execution, frontend options, deployment and commercials in full. This page is just the fintech-focused entry point to it.',
            description: 'Fintechs FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.forFintechs.cta.title',
      message: 'Bring automated trading to your fintech',
      description: 'Fintechs CTA title',
    }),
    description: translate({
      id: 'pages.ideas.forFintechs.cta.description',
      message:
        'Book a demo, or read the full whitelabel platform breakdown to see exactly what deploys in your infrastructure.',
      description: 'Fintechs CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.forFintechs.cta.action.demo',
          message: 'Book a demo',
          description: 'Fintechs CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.forFintechs.cta.action.whitelabel',
          message: 'Read the whitelabel platform page',
          description: 'Fintechs CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function TradingPlatformForFintechsPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
