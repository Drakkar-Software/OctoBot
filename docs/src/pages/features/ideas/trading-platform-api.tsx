import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, CodeVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/trading-platform-api
 * Angle: the developer API to drive the trading engine programmatically. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.platformApi.meta.title',
      message: 'Trading Platform API — Drive the engine programmatically',
      description: 'Trading platform API page meta title',
    }),
    description: translate({
      id: 'pages.ideas.platformApi.meta.description',
      message:
        'A developer API for the OctoBot trading engine — create and run bots, push strategy configuration, read portfolio and trade data, and wire your own frontend on top.',
      description: 'Trading platform API page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.platformApi.hero.eyebrow',
      message: 'For developers · Trading engine API',
      description: 'Trading platform API hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.platformApi.hero.title"
        description="Trading platform API hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.platformApi.hero.title.accent',
                message: 'from your own code.',
                description: 'Trading platform API hero title accent',
              })}
            </span>
          ),
        }}>
        {'Drive the trading engine {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.platformApi.hero.subtitle',
      message:
        'The trading platform API is how developers control OctoBot without its built-in UI. Spin up bots, push strategy configuration, pull portfolio and trade data, and react to events — then put your own frontend in front of it all.',
      description: 'Trading platform API hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.platformApi.hero.action.demo',
          message: 'Book a demo',
          description: 'Trading platform API hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.platformApi.hero.action.docs',
          message: 'Read the developer docs',
          description: 'Trading platform API hero action label',
        }),
        to: '/developers/getting-started',
        variant: 'ghost',
      },
    ],
    visual: (
      <CodeVisual
        label={translate({
          id: 'pages.ideas.platformApi.visual.label',
          message: 'Drive a bot',
          description: 'Trading platform API visual label',
        })}
        note="illustrative"
        lines={[
          {comment: '// authenticate, then create a bot'},
          'const bot = await octobot.bots.create({',
          '  exchange: "binance",',
          '  strategy: "grid",',
          '});',
          '',
          {comment: '// push config and read its portfolio'},
          'await bot.strategy.update({ levels: 12 });',
          'const portfolio = await bot.portfolio.get();',
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.platformApi.what.eyebrow',
        message: 'What it is',
        description: 'Trading platform API section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.platformApi.what.title',
        message: 'The engine, addressable from your code',
        description: 'Trading platform API section title',
      }),
      body: translate({
        id: 'pages.ideas.platformApi.what.body',
        message:
          'OctoBot ships with its own interface, but underneath it is a trading engine that the API exposes directly. Every bot, every strategy setting and every number the engine tracks becomes something your backend can create, change or read. That turns the engine into a building block: you decide what the product looks like and how users interact with it, and the API handles the trading underneath.',
        description: 'Trading platform API callout body',
      }),
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.platformApi.areas.eyebrow',
        message: 'What the API covers',
        description: 'Trading platform API section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.platformApi.areas.title',
        message: 'Four capability areas, one engine',
        description: 'Trading platform API section title',
      }),
      lead: translate({
        id: 'pages.ideas.platformApi.areas.lead',
        message:
          'Everything the built-in interface does, the API exposes — so you can build a different interface, or no interface at all.',
        description: 'Trading platform API section lead',
      }),
      columns: 2,
      items: [
        {
          icon: '🤖',
          title: translate({
            id: 'pages.ideas.platformApi.areas.lifecycle.title',
            message: 'Bot lifecycle',
            description: 'Trading platform API feature title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.areas.lifecycle.description',
            message:
              'Create bots, start and stop them, and inspect their current state. Each bot is an addressable resource you manage from your own backend.',
            description: 'Trading platform API feature description',
          }),
        },
        {
          icon: '🧠',
          title: translate({
            id: 'pages.ideas.platformApi.areas.strategy.title',
            message: 'Strategy configuration',
            description: 'Trading platform API feature title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.areas.strategy.description',
            message:
              'Choose a strategy and push its parameters programmatically — so users tune their bots through your screens, and the engine applies the changes.',
            description: 'Trading platform API feature description',
          }),
        },
        {
          icon: '📊',
          title: translate({
            id: 'pages.ideas.platformApi.areas.data.title',
            message: 'Portfolio & trade data',
            description: 'Trading platform API feature title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.areas.data.description',
            message:
              'Read current balances, open positions and the history of orders and fills — the numbers you need to render dashboards and reports.',
            description: 'Trading platform API feature description',
          }),
        },
        {
          icon: '🔔',
          title: translate({
            id: 'pages.ideas.platformApi.areas.events.title',
            message: 'Webhooks & events',
            description: 'Trading platform API feature title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.areas.events.description',
            message:
              'Subscribe to what the engine is doing — fills, state changes, errors — so your app reacts as things happen instead of polling for them.',
            description: 'Trading platform API feature description',
          }),
        },
      ],
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.platformApi.start.eyebrow',
        message: 'Getting started',
        description: 'Trading platform API section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.platformApi.start.title',
        message: 'From credentials to your own UI',
        description: 'Trading platform API section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.platformApi.start.credentials.title',
            message: 'Get credentials',
            description: 'Trading platform API step title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.start.credentials.description',
            message:
              'Provision API credentials for your deployment so your backend can authenticate against the engine.',
            description: 'Trading platform API step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.platformApi.start.call.title',
            message: 'Call the engine',
            description: 'Trading platform API step title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.start.call.description',
            message:
              'Create a bot, push a strategy configuration, and read back its portfolio — all from your own service.',
            description: 'Trading platform API step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.platformApi.start.wire.title',
            message: 'Wire your UI',
            description: 'Trading platform API step title',
          }),
          description: translate({
            id: 'pages.ideas.platformApi.start.wire.description',
            message:
              'Render the data in your own frontend and subscribe to events so the interface stays in sync with the engine.',
            description: 'Trading platform API step description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.platformApi.faq.title',
        message: 'Trading platform API questions',
        description: 'Trading platform API FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.platformApi.faq.q1',
            message: 'Do I still need the built-in OctoBot interface?',
            description: 'Trading platform API FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.platformApi.faq.a1',
            message:
              'No. The API is the full control surface for the engine, so you can replace the built-in interface entirely with your own frontend — or run both side by side.',
            description: 'Trading platform API FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.platformApi.faq.q2',
            message: 'Where do the engine and the API run?',
            description: 'Trading platform API FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.platformApi.faq.a2',
            message:
              'In your own infrastructure. The API is served by the engine inside your perimeter, and it connects to exchanges with your users’ keys — nothing routes through a third party.',
            description: 'Trading platform API FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.platformApi.faq.q3',
            message: 'Is the API documented and stable?',
            description: 'Trading platform API FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.platformApi.faq.a3',
            message:
              'Yes. OctoBot is open source, the developer docs cover how to call the engine, and the source itself is the final reference for every capability area.',
            description: 'Trading platform API FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.platformApi.cta.title',
      message: 'Build on the trading engine',
      description: 'Trading platform API CTA title',
    }),
    description: translate({
      id: 'pages.ideas.platformApi.cta.description',
      message:
        'Talk to our team about driving the OctoBot engine through the API, or dive straight into the developer docs.',
      description: 'Trading platform API CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.platformApi.cta.action.demo',
          message: 'Talk to our team',
          description: 'Trading platform API CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.platformApi.cta.action.whitelabel',
          message: 'See the white-label platform',
          description: 'Trading platform API CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function TradingPlatformApiPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
