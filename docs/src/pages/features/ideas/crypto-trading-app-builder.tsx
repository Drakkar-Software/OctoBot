import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/crypto-trading-app-builder
 * Angle: build your own branded crypto trading app on top of OctoBot — engine, execution and a reskinnable frontend, instead of building one from scratch. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.appBuilder.meta.title',
      message: 'Crypto Trading App Builder — Ship your own branded trading app',
      description: 'App builder page meta title',
    }),
    description: translate({
      id: 'pages.ideas.appBuilder.meta.description',
      message:
        'Build a branded crypto trading app on top of OctoBot. You get the engine, execution and a frontend to reskin — and skip building matching, exchange connectors and a strategy engine from scratch.',
      description: 'App builder page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.appBuilder.hero.eyebrow',
      message: 'Whitelabel · App builder',
      description: 'App builder hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.appBuilder.hero.title"
        description="App builder hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.appBuilder.hero.title.accent',
                message: 'without building one.',
                description: 'App builder hero title accent',
              })}
            </span>
          ),
        }}>
        {'Ship your own crypto trading app, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.appBuilder.hero.subtitle',
      message:
        'A trading app is mostly the parts users never see — execution, exchange connectors, a strategy engine, risk controls. OctoBot brings all of that, plus a frontend you reskin, so what you build is your brand and your product decisions, not the plumbing.',
      description: 'App builder hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.appBuilder.hero.action.demo',
          message: 'Book a demo',
          description: 'App builder hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.appBuilder.hero.action.whitelabel',
          message: 'See whitelabel options',
          description: 'App builder hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.appBuilder.visual.label',
          message: 'Your branded app',
          description: 'App builder visual label',
        })}
        note="reskinned frontend"
        lines={[
          {width: 52, accent: true},
          {width: 84},
          {width: 68},
          {width: 90},
          {width: 60},
          {width: 76},
        ]}
        cta={translate({
          id: 'pages.ideas.appBuilder.visual.cta',
          message: 'Start trading',
          description: 'App builder visual CTA',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.appBuilder.how.eyebrow',
        message: 'How it works',
        description: 'App builder section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.appBuilder.how.title',
        message: 'From engine to your app in three steps',
        description: 'App builder section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.appBuilder.how.provision.title',
            message: 'Provision the engine',
            description: 'App builder step title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.how.provision.description',
            message:
              'Deploy the OctoBot engine into your own infrastructure. It carries execution, exchange connectivity and the strategy engine out of the box.',
            description: 'App builder step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.appBuilder.how.reskin.title',
            message: 'Reskin a frontend',
            description: 'App builder step title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.how.reskin.description',
            message:
              'Start from the provided frontend and make it yours — layout, branding, copy and the screens your users actually need.',
            description: 'App builder step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.appBuilder.how.ship.title',
            message: 'Ship under your brand',
            description: 'App builder step title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.how.ship.description',
            message:
              'Launch it as your own standalone app, at your own domain, with your name on it — the engine stays invisible behind it.',
            description: 'App builder step description',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.appBuilder.skip.eyebrow',
        message: 'What you do not have to build',
        description: 'App builder section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.appBuilder.skip.title',
        message: 'The hard parts come with the engine',
        description: 'App builder section title',
      }),
      columns: 2,
      items: [
        {
          icon: '⇄',
          title: translate({
            id: 'pages.ideas.appBuilder.skip.execution.title',
            message: 'Matching & execution',
            description: 'App builder feature title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.skip.execution.description',
            message:
              'Order routing, fills and position tracking are handled by the engine — you do not write an execution layer.',
            description: 'App builder feature description',
          }),
        },
        {
          icon: '🔌',
          title: translate({
            id: 'pages.ideas.appBuilder.skip.connectors.title',
            message: 'Exchange connectors',
            description: 'App builder feature title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.skip.connectors.description',
            message:
              'Connectivity to a wide range of exchanges ships with the engine, so you skip integrating and maintaining each venue yourself.',
            description: 'App builder feature description',
          }),
        },
        {
          icon: '⌗',
          title: translate({
            id: 'pages.ideas.appBuilder.skip.strategy.title',
            message: 'Strategy engine',
            description: 'App builder feature title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.skip.strategy.description',
            message:
              'Strategy configuration, evaluation and scheduling are already there — your app exposes them rather than implementing them.',
            description: 'App builder feature description',
          }),
        },
        {
          icon: '🛡️',
          title: translate({
            id: 'pages.ideas.appBuilder.skip.risk.title',
            message: 'Risk controls',
            description: 'App builder feature title',
          }),
          description: translate({
            id: 'pages.ideas.appBuilder.skip.risk.description',
            message:
              'Limits and safeguards around how strategies trade come built in, so you do not have to design risk handling from zero.',
            description: 'App builder feature description',
          }),
        },
      ],
    },
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.appBuilder.build.eyebrow',
        message: 'What you build',
        description: 'App builder section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.appBuilder.build.title',
        message: 'You build the product, not the platform',
        description: 'App builder section title',
      }),
      body: translate({
        id: 'pages.ideas.appBuilder.build.body',
        message:
          'Because the engine owns the trading internals, your work is the part that makes the app yours: the brand, the experience, the screens your users see and the decisions about what to expose. The app builder route is for a full standalone app — if instead you only want to add automated trading to a product you already run, the embeddable widget drops a smaller piece into an existing page.',
        description: 'App builder callout body',
      }),
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.appBuilder.faq.title',
        message: 'App builder questions',
        description: 'App builder FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.appBuilder.faq.q1',
            message: 'Where does the app run?',
            description: 'App builder FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.appBuilder.faq.a1',
            message:
              'In your own infrastructure. The engine is deployed on your side and the frontend you reskin talks to it — nothing is hosted by us.',
            description: 'App builder FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.appBuilder.faq.q2',
            message: 'How much of the frontend do I have to write?',
            description: 'App builder FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.appBuilder.faq.a2',
            message:
              'You start from a provided frontend and reskin it. How far you take the customization is up to you — the engine and its API stay the same underneath.',
            description: 'App builder FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.appBuilder.faq.q3',
            message: 'When should I use the widget instead?',
            description: 'App builder FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.appBuilder.faq.a3',
            message:
              'Use the embeddable widget when you already have a product and just want to add automated trading to it. Use the app builder when you want a full, standalone branded trading app of your own.',
            description: 'App builder FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.appBuilder.cta.title',
      message: 'Build your trading app on a ready engine',
      description: 'App builder CTA title',
    }),
    description: translate({
      id: 'pages.ideas.appBuilder.cta.description',
      message:
        'Book a demo and we will walk through provisioning the engine, reskinning a frontend, and shipping it under your brand.',
      description: 'App builder CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.appBuilder.cta.action.demo',
          message: 'Book a demo',
          description: 'App builder CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.appBuilder.cta.action.widget',
          message: 'Compare the embeddable widget',
          description: 'App builder CTA action label',
        }),
        to: '/features/ideas/embeddable-trading-widget',
        variant: 'ghost',
      },
    ],
  },
};

export default function CryptoTradingAppBuilderPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
