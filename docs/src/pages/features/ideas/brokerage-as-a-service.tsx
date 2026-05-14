import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/brokerage-as-a-service
 * Angle: trading & brokerage infrastructure fintechs embed instead of building the engine, execution and risk stack themselves. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.braas.meta.title',
      message: 'Brokerage as a Service — Embed automated trading in your product',
      description: 'BaaS page meta title',
    }),
    description: translate({
      id: 'pages.ideas.braas.meta.description',
      message:
        'Brokerage-as-a-service infrastructure from OctoBot — strategy engine, order execution, exchange connectivity and risk controls your fintech can embed without building a trading stack.',
      description: 'BaaS page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.braas.hero.eyebrow',
      message: 'Infrastructure · Brokerage as a service',
      description: 'BaaS hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.braas.hero.title"
        description="BaaS hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.braas.hero.title.accent',
                message: 'without building the engine.',
                description: 'BaaS hero title accent',
              })}
            </span>
          ),
        }}>
        {'Ship an automated-trading product, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.braas.hero.subtitle',
      message:
        'Your users want an automated-trading or wealth feature. Building the trading engine, execution layer, exchange connectivity and risk controls behind it is a multi-year project. OctoBot is that stack — proven, open-source, and ready to sit behind your brand.',
      description: 'BaaS hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.braas.hero.action.demo',
          message: 'Book a demo',
          description: 'BaaS hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.braas.hero.action.whitelabel',
          message: 'See the whitelabel platform',
          description: 'BaaS hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.braas.visual.label',
          message: 'Your app · powered by OctoBot',
          description: 'BaaS visual label',
        })}
        note={translate({
          id: 'pages.ideas.braas.visual.note',
          message: 'your brand · our engine',
          description: 'BaaS visual note',
        })}
        lines={[
          {width: 68},
          {width: 92, accent: true},
          {width: 54},
          {width: 80, accent: true},
          {width: 44},
        ]}
        cta={translate({
          id: 'pages.ideas.braas.visual.cta',
          message: 'Start automated investing',
          description: 'BaaS visual CTA',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.braas.covers.eyebrow',
        message: 'What the infrastructure covers',
        description: 'BaaS section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.braas.covers.title',
        message: 'The whole trading stack, behind one integration',
        description: 'BaaS section title',
      }),
      lead: translate({
        id: 'pages.ideas.braas.covers.lead',
        message:
          'Everything between a user pressing a button and an order resting on an exchange is already built, tested and running in production elsewhere.',
        description: 'BaaS section lead',
      }),
      columns: 2,
      items: [
        {
          icon: '⌗',
          title: translate({
            id: 'pages.ideas.braas.covers.strategy.title',
            message: 'Strategy engine',
            description: 'BaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.braas.covers.strategy.description',
            message:
              'A library of trading strategies plus an SDK to author your own — DCA, grid, signal-driven and more — so the product has something real to offer on day one.',
            description: 'BaaS feature description',
          }),
        },
        {
          icon: '⇄',
          title: translate({
            id: 'pages.ideas.braas.covers.execution.title',
            message: 'Order execution',
            description: 'BaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.braas.covers.execution.description',
            message:
              'Order routing, position tracking and fee accounting that turn a strategy decision into a placed, monitored and reconciled order.',
            description: 'BaaS feature description',
          }),
        },
        {
          icon: '🔌',
          title: translate({
            id: 'pages.ideas.braas.covers.connectivity.title',
            message: 'Exchange connectivity',
            description: 'BaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.braas.covers.connectivity.description',
            message:
              'Dozens of venues integrated behind one interface, so adding or swapping an exchange is a configuration change, not another integration project.',
            description: 'BaaS feature description',
          }),
        },
        {
          icon: '↯',
          title: translate({
            id: 'pages.ideas.braas.covers.risk.title',
            message: 'Risk & audit',
            description: 'BaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.braas.covers.risk.description',
            message:
              'Position caps, kill-switches and a full audit log of every decision and order — the controls your risk and compliance teams will ask for.',
            description: 'BaaS feature description',
          }),
        },
      ],
    },
    {
      kind: 'stats',
      eyebrow: translate({
        id: 'pages.ideas.braas.stats.eyebrow',
        message: 'What you build on',
        description: 'BaaS section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.braas.stats.title',
        message: 'Mature infrastructure, not a prototype',
        description: 'BaaS section title',
      }),
      items: [
        {
          value: '100%',
          label: translate({
            id: 'pages.ideas.braas.stats.infra.label',
            message: 'Runs on your own infrastructure',
            description: 'BaaS stat label',
          }),
          sub: translate({
            id: 'pages.ideas.braas.stats.infra.sub',
            message: 'No vendor in the hot path',
            description: 'BaaS stat sub',
          }),
        },
        {
          value: '24',
          label: translate({
            id: 'pages.ideas.braas.stats.venues.label',
            message: 'Exchange venues built in',
            description: 'BaaS stat label',
          }),
          sub: translate({
            id: 'pages.ideas.braas.stats.venues.sub',
            message: 'One interface for all of them',
            description: 'BaaS stat sub',
          }),
        },
        {
          value: '3',
          label: translate({
            id: 'pages.ideas.braas.stats.modes.label',
            message: 'Frontend modes to embed',
            description: 'BaaS stat label',
          }),
          sub: translate({
            id: 'pages.ideas.braas.stats.modes.sub',
            message: 'Widget, web app, native mobile',
            description: 'BaaS stat sub',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.braas.faq.title',
        message: 'Brokerage-as-a-service questions',
        description: 'BaaS FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.braas.faq.q1',
            message: 'Does OctoBot ever hold our users’ funds?',
            description: 'BaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.braas.faq.a1',
            message:
              'No. The engine connects to exchange accounts through API keys and places orders there. Custody stays wherever you and your users already keep it — OctoBot is the execution layer, not a custodian.',
            description: 'BaaS FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.braas.faq.q2',
            message: 'How is this different from a trading API?',
            description: 'BaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.braas.faq.a2',
            message:
              'A raw exchange API gives you order endpoints and nothing else. Brokerage-as-a-service gives you the layer above that — strategies, scheduling, position tracking, risk controls and audit — so you embed a working product instead of assembling one.',
            description: 'BaaS FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.braas.faq.q3',
            message: 'Can our brand and our compliance team own it end to end?',
            description: 'BaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.braas.faq.a3',
            message:
              'Yes. OctoBot is open-source and deploys inside your own infrastructure, under your brand. Your compliance team can read the source before signing, and nothing phones home. The whitelabel page covers the deployment model in full.',
            description: 'BaaS FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.braas.cta.title',
      message: 'Put a trading engine behind your product',
      description: 'BaaS CTA title',
    }),
    description: translate({
      id: 'pages.ideas.braas.cta.description',
      message:
        'Tell us what you want your users to do, and we’ll walk through how OctoBot’s infrastructure gets you there.',
      description: 'BaaS CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.braas.cta.action.demo',
          message: 'Book a demo',
          description: 'BaaS CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.braas.cta.action.whitelabel',
          message: 'Explore the whitelabel platform',
          description: 'BaaS CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function BrokerageAsAServicePage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
