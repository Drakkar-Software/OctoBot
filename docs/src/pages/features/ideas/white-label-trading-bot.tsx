import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/white-label-trading-bot
 * Angle: license just the trading-bot engine and ship it under your own brand. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.wlBot.meta.title',
      message: 'White-Label Trading Bot — License the engine, ship your brand',
      description: 'White-label trading bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.wlBot.meta.description',
      message:
        'License the OctoBot trading-bot engine and ship it under your own brand — strategy templates, order execution and exchange connectors, without building a bot from scratch.',
      description: 'White-label trading bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.wlBot.hero.eyebrow',
      message: 'White-label · Trading-bot engine',
      description: 'White-label trading bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.wlBot.hero.title"
        description="White-label trading bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.wlBot.hero.title.accent',
                message: 'under your brand.',
                description: 'White-label trading bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'Ship a trading bot {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.wlBot.hero.subtitle',
      message:
        'You do not need a whole platform to offer automated trading — sometimes you just need the bot. License the OctoBot engine on its own: the strategies, the execution loop and the exchange connectors, wrapped in your name and your UI.',
      description: 'White-label trading bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.wlBot.hero.action.demo',
          message: 'Book a demo',
          description: 'White-label trading bot hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.wlBot.hero.action.platform',
          message: 'See the full white-label platform',
          description: 'White-label trading bot hero action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.wlBot.visual.label',
          message: 'Your app · powered by OctoBot',
          description: 'White-label trading bot visual label',
        })}
        note="your brand"
        lines={[
          {width: 58, accent: true},
          {width: 92},
          {width: 76},
          {width: 84},
          {width: 64},
        ]}
        cta={translate({
          id: 'pages.ideas.wlBot.visual.cta',
          message: 'Start the bot',
          description: 'White-label trading bot visual CTA',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.wlBot.scope.eyebrow',
        message: 'The narrow choice',
        description: 'White-label trading bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlBot.scope.title',
        message: 'Just the bot — not the whole platform',
        description: 'White-label trading bot section title',
      }),
      body: translate({
        id: 'pages.ideas.wlBot.scope.body',
        message:
          'A full white-label platform gives you an engine, a frontend stack, user management and everything around it. That is a lot to adopt if all you want is to add a trading bot to a product you already have. Licensing the engine on its own is the narrower path: you keep your interface, your accounts and your stack, and slot in a proven bot where the trading logic would otherwise be.',
        description: 'White-label trading bot callout body',
      }),
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.wlBot.get.eyebrow',
        message: 'What you license',
        description: 'White-label trading bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlBot.get.title',
        message: 'A working bot engine, not a blank page',
        description: 'White-label trading bot section title',
      }),
      lead: translate({
        id: 'pages.ideas.wlBot.get.lead',
        message:
          'The engine arrives complete. You point it at exchanges and dress it in your brand — the trading logic is already built and proven in production.',
        description: 'White-label trading bot section lead',
      }),
      columns: 2,
      items: [
        {
          icon: '🧩',
          title: translate({
            id: 'pages.ideas.wlBot.get.strategies.title',
            message: 'Strategy templates',
            description: 'White-label trading bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlBot.get.strategies.description',
            message:
              'A library of ready trading strategies — DCA, grid, signal-driven and more — that your users can pick and configure, plus room to add your own.',
            description: 'White-label trading bot feature description',
          }),
        },
        {
          icon: '⚙️',
          title: translate({
            id: 'pages.ideas.wlBot.get.execution.title',
            message: 'Order execution',
            description: 'White-label trading bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlBot.get.execution.description',
            message:
              'The part that places, tracks and reconciles orders against the live market — position keeping, fills and fee handling included.',
            description: 'White-label trading bot feature description',
          }),
        },
        {
          icon: '🔌',
          title: translate({
            id: 'pages.ideas.wlBot.get.connectors.title',
            message: 'Exchange connectors',
            description: 'White-label trading bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlBot.get.connectors.description',
            message:
              'Connectivity to a wide range of exchanges is built in, so the bot trades wherever your users already hold funds.',
            description: 'White-label trading bot feature description',
          }),
        },
        {
          icon: '🎨',
          title: translate({
            id: 'pages.ideas.wlBot.get.branding.title',
            message: 'Your branding',
            description: 'White-label trading bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.wlBot.get.branding.description',
            message:
              'The engine runs behind your name and your interface. Nothing in front of your users says OctoBot unless you want it to.',
            description: 'White-label trading bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.wlBot.compare.eyebrow',
        message: 'Build vs license',
        description: 'White-label trading bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.wlBot.compare.title',
        message: 'Why not just build the bot in-house',
        description: 'White-label trading bot section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.wlBot.compare.before.label',
          message: 'Building from scratch',
          description: 'White-label trading bot before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.wlBot.compare.before.1',
            message:
              'Months spent on exchange integrations before a single trade runs',
            description: 'White-label trading bot before item',
          }),
          translate({
            id: 'pages.ideas.wlBot.compare.before.2',
            message:
              'Edge cases — partial fills, rate limits, reconnects — discovered in production',
            description: 'White-label trading bot before item',
          }),
          translate({
            id: 'pages.ideas.wlBot.compare.before.3',
            message:
              'A team permanently tied to maintaining trading plumbing instead of your product',
            description: 'White-label trading bot before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.wlBot.compare.after.label',
          message: 'Licensing the engine',
          description: 'White-label trading bot after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.wlBot.compare.after.1',
            message: 'Connectors and execution already battle-tested in the open',
            description: 'White-label trading bot after item',
          }),
          translate({
            id: 'pages.ideas.wlBot.compare.after.2',
            message: 'The hard edge cases are already handled by the engine',
            description: 'White-label trading bot after item',
          }),
          translate({
            id: 'pages.ideas.wlBot.compare.after.3',
            message:
              'Your team builds the brand and the experience, not the trading loop',
            description: 'White-label trading bot after item',
          }),
        ],
      },
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.wlBot.faq.title',
        message: 'White-label trading bot questions',
        description: 'White-label trading bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.wlBot.faq.q1',
            message: 'How is this different from the full white-label platform?',
            description: 'White-label trading bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlBot.faq.a1',
            message:
              'The full platform bundles the engine with a frontend stack, user management and the rest. Here you license just the trading-bot engine and wrap it in whatever interface you already have — a narrower, lighter starting point.',
            description: 'White-label trading bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.wlBot.faq.q2',
            message: 'Where does the engine run?',
            description: 'White-label trading bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlBot.faq.a2',
            message:
              'In your own infrastructure. The engine is deployed inside your perimeter and connects to exchanges with your users’ API keys — funds and credentials never pass through us.',
            description: 'White-label trading bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.wlBot.faq.q3',
            message: 'Can we add our own strategies?',
            description: 'White-label trading bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.wlBot.faq.a3',
            message:
              'Yes. OctoBot is open source, so the included strategies are a starting point — your team can extend them or write new ones against the same engine.',
            description: 'White-label trading bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.wlBot.cta.title',
      message: 'License the engine, ship the bot',
      description: 'White-label trading bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.wlBot.cta.description',
      message:
        'Talk to our team about licensing the OctoBot trading-bot engine for your product.',
      description: 'White-label trading bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.wlBot.cta.action.demo',
          message: 'Talk to our team',
          description: 'White-label trading bot CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.wlBot.cta.action.platform',
          message: 'Explore the white-label platform',
          description: 'White-label trading bot CTA action label',
        }),
        to: '/whitelabel',
        variant: 'ghost',
      },
    ],
  },
};

export default function WhiteLabelTradingBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
