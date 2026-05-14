import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, MetricVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/free-crypto-trading-bot
 * Angle: genuinely free and open source — no paywalled core, you only pay your exchange's normal fees.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.freeBot.meta.title',
      message: 'Free Crypto Trading Bot — Open source, no paywalled features',
      description: 'Free bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.freeBot.meta.description',
      message:
        'OctoBot is a genuinely free, open-source crypto trading bot — no paywalled core features, no subscription to trade. You only ever pay your exchange its normal fees.',
      description: 'Free bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.freeBot.hero.eyebrow',
      message: 'Open source · Free to run',
      description: 'Free bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.freeBot.hero.title"
        description="Free bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.freeBot.hero.title.accent',
                message: 'free, and open source.',
                description: 'Free bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'A crypto trading bot that is actually {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.freeBot.hero.subtitle',
      message:
        'No paywalled core, no subscription to place a trade, no "free trial" that expires. OctoBot is open source — you can read every line, run it yourself, and the only money that ever leaves your account is your exchange\'s normal trading fee.',
      description: 'Free bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.freeBot.hero.action.create',
          message: 'Start for free',
          description: 'Free bot hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.freeBot.hero.action.app',
          message: 'See the OctoBot App',
          description: 'Free bot hero action label',
        }),
        to: '/features/octobot-app',
        variant: 'ghost',
      },
    ],
    visual: (
      <MetricVisual
        label={translate({
          id: 'pages.ideas.freeBot.visual.label',
          message: 'What OctoBot costs',
          description: 'Free bot visual label',
        })}
        note="self-hosted"
        value="$0"
        unit="/mo"
        caption={translate({
          id: 'pages.ideas.freeBot.visual.caption',
          message: 'Every trading feature included — nothing locked behind a plan.',
          description: 'Free bot visual caption',
        })}
        rows={[
          {
            label: translate({
              id: 'pages.ideas.freeBot.visual.row1.label',
              message: 'Software license',
              description: 'Free bot visual row label',
            }),
            value: translate({
              id: 'pages.ideas.freeBot.visual.row1.value',
              message: 'Free · open source',
              description: 'Free bot visual row value',
            }),
          },
          {
            label: translate({
              id: 'pages.ideas.freeBot.visual.row2.label',
              message: 'Strategies & backtesting',
              description: 'Free bot visual row label',
            }),
            value: translate({
              id: 'pages.ideas.freeBot.visual.row2.value',
              message: 'Included',
              description: 'Free bot visual row value',
            }),
          },
          {
            label: translate({
              id: 'pages.ideas.freeBot.visual.row3.label',
              message: 'Exchange trading fees',
              description: 'Free bot visual row label',
            }),
            value: translate({
              id: 'pages.ideas.freeBot.visual.row3.value',
              message: "Your exchange's normal rate",
              description: 'Free bot visual row value',
            }),
          },
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'icons',
      eyebrow: translate({
        id: 'pages.ideas.freeBot.free.eyebrow',
        message: "What's free",
        description: 'Free bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.freeBot.free.title',
        message: 'Free means the whole thing, not a teaser',
        description: 'Free bot section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🧠',
          text: translate({
            id: 'pages.ideas.freeBot.free.item1',
            message:
              'Every trading strategy — DCA, grid, signal-based and custom — with no premium tier gating the good ones.',
            description: 'Free bot icon item',
          }),
        },
        {
          icon: '📊',
          text: translate({
            id: 'pages.ideas.freeBot.free.item2',
            message:
              'Full backtesting and paper trading, so you can test as much as you want before going live.',
            description: 'Free bot icon item',
          }),
        },
        {
          icon: '🔌',
          text: translate({
            id: 'pages.ideas.freeBot.free.item3',
            message:
              'Connections to every supported exchange — no per-exchange unlock, no add-on fee.',
            description: 'Free bot icon item',
          }),
        },
        {
          icon: '♾️',
          text: translate({
            id: 'pages.ideas.freeBot.free.item4',
            message:
              'No trade limits, no order caps, and no expiring trial — run it as long as you like.',
            description: 'Free bot icon item',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.freeBot.open.eyebrow',
        message: 'Open source',
        description: 'Free bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.freeBot.open.title',
        message: 'Why open source matters for a money bot',
        description: 'Free bot section title',
      }),
      columns: 3,
      items: [
        {
          icon: '🔍',
          title: translate({
            id: 'pages.ideas.freeBot.open.audit.title',
            message: 'Auditable',
            description: 'Free bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.freeBot.open.audit.description',
            message:
              'The full source is public. You — or anyone you trust — can read exactly what the bot does with your API keys and your orders.',
            description: 'Free bot feature description',
          }),
        },
        {
          icon: '🏠',
          title: translate({
            id: 'pages.ideas.freeBot.open.selfhost.title',
            message: 'Self-hostable',
            description: 'Free bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.freeBot.open.selfhost.description',
            message:
              'Run it on your own machine or server. Your keys and your config never have to leave hardware you control.',
            description: 'Free bot feature description',
          }),
        },
        {
          icon: '🤝',
          title: translate({
            id: 'pages.ideas.freeBot.open.community.title',
            message: 'Community-driven',
            description: 'Free bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.freeBot.open.community.description',
            message:
              'Strategies, exchange support and fixes come from a public contributor base — improvements are shared, not sold back to you.',
            description: 'Free bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.freeBot.compare.eyebrow',
        message: 'The honest comparison',
        description: 'Free bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.freeBot.compare.title',
        message: 'How "free" usually works vs how it works here',
        description: 'Free bot section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.freeBot.compare.before.label',
          message: 'Typical paid, closed-source bots',
          description: 'Free bot before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.freeBot.compare.before.1',
            message: 'Core strategies locked behind a monthly subscription',
            description: 'Free bot before item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.before.2',
            message: 'Closed code — you have to trust the vendor with your keys',
            description: 'Free bot before item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.before.3',
            message: 'Free tier is a time-limited or feature-limited trial',
            description: 'Free bot before item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.before.4',
            message: 'Often a custodial setup, or extra fees layered on trades',
            description: 'Free bot before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.freeBot.compare.after.label',
          message: 'OctoBot',
          description: 'Free bot after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.freeBot.compare.after.1',
            message: 'Every strategy free — no premium trading tier',
            description: 'Free bot after item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.after.2',
            message: 'Open source — read and audit the code yourself',
            description: 'Free bot after item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.after.3',
            message: 'No expiry and no feature gate — the free version is the bot',
            description: 'Free bot after item',
          }),
          translate({
            id: 'pages.ideas.freeBot.compare.after.4',
            message: 'Self-custody and zero added trade fees — you pay only your exchange',
            description: 'Free bot after item',
          }),
        ],
      },
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.freeBot.faq.title',
        message: 'Free crypto trading bot questions',
        description: 'Free bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.freeBot.faq.q1',
            message: 'Is it really free, or is there a catch?',
            description: 'Free bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.freeBot.faq.a1',
            message:
              'The bot itself is free and open source — there is no paid tier that unlocks the real trading features. The only cost is your exchange\'s standard trading fee, which you would pay placing those orders by hand anyway. Optional hosted convenience services exist, but you never need them to run the bot.',
            description: 'Free bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.freeBot.faq.q2',
            message: 'What does open source actually get me?',
            description: 'Free bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.freeBot.faq.a2',
            message:
              'It means nothing about the bot is hidden. You can inspect how it handles your exchange API keys, confirm it never takes custody of your funds, run it on your own hardware, and even modify it. With a closed-source bot you have to take all of that on trust.',
            description: 'Free bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.freeBot.faq.q3',
            message: 'Does the free bot hold my crypto?',
            description: 'Free bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.freeBot.faq.a3',
            message:
              'No. OctoBot connects to your exchange through an API key and places orders on your behalf — your funds stay in your own exchange account the whole time. It is self-custody by design.',
            description: 'Free bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.freeBot.cta.title',
      message: 'Start trading with a bot that costs nothing to run',
      description: 'Free bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.freeBot.cta.description',
      message:
        'Create a free OctoBot, connect your exchange, and keep every feature — no subscription, no custody, no catch.',
      description: 'Free bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.freeBot.cta.action.create',
          message: 'Start for free',
          description: 'Free bot CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.freeBot.cta.action.app',
          message: 'See the OctoBot App',
          description: 'Free bot CTA action label',
        }),
        to: '/features/octobot-app',
        variant: 'ghost',
      },
    ],
  },
};

export default function FreeCryptoTradingBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
