import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, MetricVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/* SEO idea page — route: /features/ideas/dex-market-making
 * Angle: explain DEX AMM pool liquidity vs CEX order-book market making, honestly. */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.dexMm.meta.title',
      message: 'DEX Market Making vs Order-Book Market Making — explained',
      description: 'DEX market making page meta title',
    }),
    description: translate({
      id: 'pages.ideas.dexMm.meta.description',
      message:
        'Understand the difference between providing liquidity to a DEX AMM pool and actively quoting an order book. OctoBot Market Making runs on centralized order-book exchanges — here is how to decide what you need.',
      description: 'DEX market making page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.dexMm.hero.eyebrow',
      message: 'Concept · DEX vs order-book liquidity',
      description: 'DEX market making hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.dexMm.hero.title"
        description="DEX market making hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.dexMm.hero.title.accent',
                message: 'are not the same thing.',
                description: 'DEX market making hero title accent',
              })}
            </span>
          ),
        }}>
        {'AMM pool liquidity and market making {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.dexMm.hero.subtitle',
      message:
        'Depositing tokens into a DEX pool is passive — a constant-product curve quotes for you. Order-book market making is active — you place and move bids and asks yourself. This page explains the distinction so you can pick the right tool. OctoBot Market Making is built for centralized order-book venues.',
      description: 'DEX market making hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.dexMm.hero.action.contact',
          message: 'Talk to our team',
          description: 'DEX market making hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.dexMm.hero.action.feature',
          message: 'See OctoBot Market Making',
          description: 'DEX market making hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <MetricVisual
        label={translate({
          id: 'pages.ideas.dexMm.visual.label',
          message: 'Two ways to provide liquidity',
          description: 'DEX market making visual label',
        })}
        note="side by side"
        value="x · y = k"
        caption={translate({
          id: 'pages.ideas.dexMm.visual.caption',
          message:
            'An AMM pool prices trades along a fixed curve. An order book is quoted, rung by rung, by a market maker.',
          description: 'DEX market making visual caption',
        })}
        rows={[
          {label: 'AMM pool', value: 'passive · curve-priced'},
          {label: 'Order book', value: 'active · quote-driven'},
          {label: 'OctoBot fits', value: 'order-book venues'},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.dexMm.what.eyebrow',
        message: 'The core distinction',
        description: 'DEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dexMm.what.title',
        message: 'Pool liquidity provision is not order-book market making',
        description: 'DEX market making section title',
      }),
      body: translate({
        id: 'pages.ideas.dexMm.what.body',
        message:
          'On a DEX, you provide liquidity by depositing a pair of tokens into an automated market maker pool. From then on the pool is passive: a constant-product formula sets the price for every trade, and your position simply rebalances along that curve as people swap. On a centralized exchange there is no curve — liquidity is a list of resting bids and asks, and a market maker is whoever actively places, cancels and re-places those quotes to keep a tight, two-sided spread. One is a deposit; the other is an ongoing quoting operation.',
        description: 'DEX market making callout body',
      }),
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.dexMm.compare.eyebrow',
        message: 'Pool vs order book',
        description: 'DEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dexMm.compare.title',
        message: 'How the two models actually behave',
        description: 'DEX market making section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.dexMm.compare.before.label',
          message: 'DEX AMM pool liquidity',
          description: 'DEX market making before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.dexMm.compare.before.1',
            message: 'You deposit a token pair and the pool quotes for you',
            description: 'DEX market making before item',
          }),
          translate({
            id: 'pages.ideas.dexMm.compare.before.2',
            message: 'Price follows a fixed constant-product curve, not your view',
            description: 'DEX market making before item',
          }),
          translate({
            id: 'pages.ideas.dexMm.compare.before.3',
            message: 'No spread or inventory decisions — and exposure to impermanent loss',
            description: 'DEX market making before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.dexMm.compare.after.label',
          message: 'Order-book market making',
          description: 'DEX market making after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.dexMm.compare.after.1',
            message: 'You actively quote bids and asks around a reference price',
            description: 'DEX market making after item',
          }),
          translate({
            id: 'pages.ideas.dexMm.compare.after.2',
            message: 'Spread, depth and order refresh are all yours to tune',
            description: 'DEX market making after item',
          }),
          translate({
            id: 'pages.ideas.dexMm.compare.after.3',
            message: 'Inventory is managed continuously as fills come in',
            description: 'DEX market making after item',
          }),
        ],
      },
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.dexMm.choose.eyebrow',
        message: 'Choosing',
        description: 'DEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.dexMm.choose.title',
        message: 'What to weigh before you pick a model',
        description: 'DEX market making section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🏷️',
          title: translate({
            id: 'pages.ideas.dexMm.choose.venue.title',
            message: 'Where your token trades',
            description: 'DEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.dexMm.choose.venue.description',
            message:
              'If your volume lives on centralized exchanges, you need order-book quoting. If it lives in a DEX pool, you need pool liquidity.',
            description: 'DEX market making feature description',
          }),
        },
        {
          icon: '🎚️',
          title: translate({
            id: 'pages.ideas.dexMm.choose.control.title',
            message: 'How much control you want',
            description: 'DEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.dexMm.choose.control.description',
            message:
              'A pool runs on autopilot along its curve. Order-book market making lets you steer spread, depth and reference price.',
            description: 'DEX market making feature description',
          }),
        },
        {
          icon: '⚖️',
          title: translate({
            id: 'pages.ideas.dexMm.choose.risk.title',
            message: 'The risk you are signing up for',
            description: 'DEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.dexMm.choose.risk.description',
            message:
              'Pools carry impermanent loss as price diverges. Order-book quoting carries inventory risk you actively manage instead.',
            description: 'DEX market making feature description',
          }),
        },
        {
          icon: '🔑',
          title: translate({
            id: 'pages.ideas.dexMm.choose.custody.title',
            message: 'How funds are held',
            description: 'DEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.dexMm.choose.custody.description',
            message:
              'A pool holds your deposit in a contract. OctoBot connects to a centralized exchange through API keys and never takes custody.',
            description: 'DEX market making feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.dexMm.faq.title',
        message: 'DEX market making questions',
        description: 'DEX market making FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.dexMm.faq.q1',
            message: 'Does OctoBot run market making on on-chain AMM pools?',
            description: 'DEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dexMm.faq.a1',
            message:
              'No. OctoBot Market Making targets centralized order-book exchanges — it actively quotes bids and asks there. It does not deposit into or manage on-chain AMM pools.',
            description: 'DEX market making FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.dexMm.faq.q2',
            message: 'Is providing DEX pool liquidity a substitute for market making?',
            description: 'DEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dexMm.faq.a2',
            message:
              'They solve different problems. A pool gives a DEX passive depth along a curve; order-book market making keeps a tight, actively-managed spread on a centralized exchange. Many projects end up needing both, in different places.',
            description: 'DEX market making FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.dexMm.faq.q3',
            message: 'My token is listed on a centralized exchange — what do I need?',
            description: 'DEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.dexMm.faq.a3',
            message:
              'Order-book market making. OctoBot Market Making can quote two-sided liquidity on that venue through your exchange API keys. Talk to our team about your pairs and target spread.',
            description: 'DEX market making FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.dexMm.cta.title',
      message: 'Not sure which kind of liquidity you need?',
      description: 'DEX market making CTA title',
    }),
    description: translate({
      id: 'pages.ideas.dexMm.cta.description',
      message:
        'If your token trades on centralized order-book venues, OctoBot Market Making can quote it. Tell us about your listing and we will walk you through the options.',
      description: 'DEX market making CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.dexMm.cta.action.contact',
          message: 'Talk to our team',
          description: 'DEX market making CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.dexMm.cta.action.dmm',
          message: 'Read about designated market makers',
          description: 'DEX market making CTA action label',
        }),
        to: '/features/ideas/designated-market-maker',
        variant: 'ghost',
      },
    ],
  },
};

export default function DexMarketMakingPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
