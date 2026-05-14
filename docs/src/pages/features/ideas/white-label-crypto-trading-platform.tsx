import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/white-label-crypto-trading-platform
 * Angle: a complete rebrandable crypto trading platform deployed in your own infrastructure.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.wlPlatform.meta.title',
      message: 'White-Label Crypto Trading Platform — Your brand, your infra',
      description: 'White-label platform page meta title',
    }),
    description: translate({
      id: 'pages.ideas.wlPlatform.meta.description',
      message:
        'A complete white-label crypto trading platform — strategy engine, execution engine, frontend and risk — deployed in your own infrastructure under your brand.',
      description: 'White-label platform page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.wlPlatform.hero.eyebrow',
      message: 'White-label · on-premise · full-stack',
      description: 'White-label platform hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.wlPlatform.hero.title"
        description="White-label platform hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.wlPlatform.hero.title.accent',
                message: 'your infrastructure.',
                description: 'White-label platform hero title accent',
              })}
            </span>
          ),
        }}>
        {'A crypto trading platform in {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.wlPlatform.hero.subtitle',
      message:
        'Strategy engine, execution engine, frontend and risk controls — the whole stack, rebrandable and deployed inside your own perimeter. Your customers see your product; nothing phones home.',
      description: 'White-label platform hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.wlPlatform.hero.action.demo',
          message: 'Book a demo',
          description: 'White-label platform hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.wlPlatform.hero.action.whitelabel',
          message: 'Explore whitelabel',
          description: 'White-label platform hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.wlPlatform.visual.label',
          message: 'Your branded app',
          description: 'White-label platform visual label',
        })}
        note="your domain · your theme"
        lines={[
          {width: 70, accent: true},
          {width: 92},
          {width: 84},
          {width: 60},
          {width: 78},
        ]}
        cta={translate({
          id: 'pages.ideas.wlPlatform.visual.cta',
          message: 'Powered by your brand',
          description: 'White-label platform visual cta',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.wlPlatform.parts.eyebrow',
        message: 'What you get',
        description: 'White-label platform section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlPlatform.parts.title',
        message: 'A whole platform, not a hosted account',
        description: 'White-label platform section title',
      }),
      lead: translate({
        id: 'pages.ideas.wlPlatform.parts.lead',
        message:
          'Every layer ships to you and runs in your namespace — no vendor in the hot path.',
        description: 'White-label platform section lead',
      }),
      items: [
        {
          icon: '⌗',
          title: translate({
            id: 'pages.ideas.wlPlatform.parts.strategy.title',
            message: 'Strategy engine',
            description: 'White-label platform feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.parts.strategy.description',
            message:
              'Ready-made strategy templates plus an SDK so your team can ship its own logic — backtested before it goes live.',
            description: 'White-label platform feature description',
          }),
        },
        {
          icon: '⇄',
          title: translate({
            id: 'pages.ideas.wlPlatform.parts.execution.title',
            message: 'Execution engine',
            description: 'White-label platform feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.parts.execution.description',
            message:
              'Order routing, position keeping and fee handling across the exchanges your users connect — all through their own API keys.',
            description: 'White-label platform feature description',
          }),
        },
        {
          icon: '▢',
          title: translate({
            id: 'pages.ideas.wlPlatform.parts.frontend.title',
            message: 'Frontend stack',
            description: 'White-label platform feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.parts.frontend.description',
            message:
              'An embeddable widget, a full web app, or native mobile source — yours to theme, brand and ship under your name.',
            description: 'White-label platform feature description',
          }),
        },
        {
          icon: '↯',
          title: translate({
            id: 'pages.ideas.wlPlatform.parts.risk.title',
            message: 'Risk & audit',
            description: 'White-label platform feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.parts.risk.description',
            message:
              'Exposure caps, kill-switches and a full audit log — all stored in your database, inside your perimeter.',
            description: 'White-label platform feature description',
          }),
        },
      ],
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.wlPlatform.deploy.eyebrow',
        message: 'How it ships',
        description: 'White-label platform section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlPlatform.deploy.title',
        message: 'From your cluster to your customers',
        description: 'White-label platform section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.wlPlatform.deploy.provision.title',
            message: 'Provision the engine',
            description: 'White-label platform step title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.deploy.provision.description',
            message:
              'Deploy the strategy and execution engines into your own cloud, cluster or bare metal, with sandbox venues from day one.',
            description: 'White-label platform step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.wlPlatform.deploy.frontend.title',
            message: 'Pick a frontend',
            description: 'White-label platform step title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.deploy.frontend.description',
            message:
              'Drop in the widget, fork the full web app, or build from the mobile source — then apply your brand and theme.',
            description: 'White-label platform step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.wlPlatform.deploy.wire.title',
            message: 'Wire venues & users',
            description: 'White-label platform step title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.deploy.wire.description',
            message:
              'Connect it to your authentication, your user accounts and your observability stack. The platform never takes custody — users trade on their own exchange keys.',
            description: 'White-label platform step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.wlPlatform.deploy.golive.title',
            message: 'Go live',
            description: 'White-label platform step title',
          }),
          description: translate({
            id: 'pages.ideas.wlPlatform.deploy.golive.description',
            message:
              'Flip it on under your own domain and brand. Source-level support and regular releases keep it current.',
            description: 'White-label platform step description',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      variant: 'strong',
      eyebrow: translate({
        id: 'pages.ideas.wlPlatform.own.eyebrow',
        message: 'Why on-premise',
        description: 'White-label platform section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlPlatform.own.title',
        message: 'It runs as your software, not a vendor’s service',
        description: 'White-label platform section title',
      }),
      body: translate({
        id: 'pages.ideas.wlPlatform.own.body',
        message:
          'Because the platform is deployed inside your infrastructure, your data stays in your perimeter, compliance can read the source before you sign, and there is no third party in the trading path. OctoBot is open-source at its core — you are licensing a stack to run yourself, not renting access to someone else’s.',
        description: 'White-label platform callout body',
      }),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.wlPlatform.faq.title',
        message: 'White-label platform questions',
        description: 'White-label platform FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.wlPlatform.faq.q1',
            message: 'Where does the platform run?',
            description: 'White-label platform FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlPlatform.faq.a1',
            message:
              'In your own infrastructure — cloud, your own cluster, or bare metal. The engine, frontend and database all sit inside your perimeter; nothing is hosted by us.',
            description: 'White-label platform FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.wlPlatform.faq.q2',
            message: 'How much can we rebrand?',
            description: 'White-label platform FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlPlatform.faq.a2',
            message:
              'The whole frontend is yours to theme — name, colours, domain, and the native mobile app under your own store listings. Customers experience it as your product.',
            description: 'White-label platform FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.wlPlatform.faq.q3',
            message: 'Who holds customer funds?',
            description: 'White-label platform FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlPlatform.faq.a3',
            message:
              'Nobody in the platform does. Users connect their own exchange accounts through API keys, so trading happens on venues they already control — the platform orchestrates, it never takes custody.',
            description: 'White-label platform FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.wlPlatform.cta.title',
      message: 'Launch a trading platform under your brand',
      description: 'White-label platform CTA title',
    }),
    description: translate({
      id: 'pages.ideas.wlPlatform.cta.description',
      message:
        'Book a demo and we’ll walk through deployment, theming and how the engine wires into your stack.',
      description: 'White-label platform CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.wlPlatform.cta.action.demo',
          message: 'Book a demo',
          description: 'White-label platform CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.wlPlatform.cta.action.whitelabel',
          message: 'Explore whitelabel',
          description: 'White-label platform CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function WhiteLabelCryptoTradingPlatformPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
