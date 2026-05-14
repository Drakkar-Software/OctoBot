import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/cex-market-making
 * Angle: market making on centralized order-book exchanges — how CEX order-book MM actually works.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.cexMm.meta.title',
      message: 'CEX Market Making — How order-book market making works on exchanges',
      description: 'CEX market making page meta title',
    }),
    description: translate({
      id: 'pages.ideas.cexMm.meta.description',
      message:
        'Market making on centralized, order-book exchanges: post limit orders around the mid price, capture the spread, and manage inventory — with OctoBot connecting through trade-only API keys.',
      description: 'CEX market making page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.cexMm.hero.eyebrow',
      message: 'Context · Centralized exchanges',
      description: 'CEX market making hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.cexMm.hero.title"
        description="CEX market making hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.cexMm.hero.title.accent',
                message: 'on a centralized exchange.',
                description: 'CEX market making hero title accent',
              })}
            </span>
          ),
        }}>
        {'Market making {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.cexMm.hero.subtitle',
      message:
        'On a centralized exchange, the order book is the whole game: every trade is a limit order matched against another. Market making here means posting your own limit orders on both sides of the mid price and earning the spread as the book trades through them. OctoBot does this on your exchange account through a trade-only API key.',
      description: 'CEX market making hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.cexMm.hero.action.talk',
          message: 'Talk to our team',
          description: 'CEX market making hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.cexMm.hero.action.feature',
          message: 'See market making on OctoBot',
          description: 'CEX market making hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.cexMm.visual.label',
          message: 'Order book',
          description: 'CEX market making visual label',
        })}
        note="ETH/USDT · spot"
        asks={[
          {price: '3,218.40', size: '1.4', depth: 46},
          {price: '3,217.10', size: '2.1', depth: 70},
          {price: '3,216.20', size: '2.6', depth: 92},
        ]}
        mid="3,215.50 · mid"
        bids={[
          {price: '3,214.80', size: '2.6', depth: 92},
          {price: '3,213.90', size: '2.1', depth: 70},
          {price: '3,212.60', size: '1.4', depth: 46},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.cexMm.what.eyebrow',
        message: 'The mechanics',
        description: 'CEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.cexMm.what.title',
        message: 'How order-book market making works on a CEX',
        description: 'CEX market making section title',
      }),
      body: translate({
        id: 'pages.ideas.cexMm.what.body',
        message:
          'A centralized exchange matches buyers and sellers through a single shared order book. The mid price sits between the best bid and the best ask. To make a market, you place a limit buy a little below the mid and a limit sell a little above it. When a taker hits your sell and another hits your buy, you have captured the difference — the spread — and you re-post around the new mid. Your edge comes from quoting tight enough to get filled, while inventory limits keep you from ending up heavily long or short when the book trades mostly one way.',
        description: 'CEX market making callout body',
      }),
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.cexMm.specifics.eyebrow',
        message: 'What is specific to a CEX',
        description: 'CEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.cexMm.specifics.title',
        message: 'What changes when you make markets on an exchange',
        description: 'CEX market making section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🔑',
          title: translate({
            id: 'pages.ideas.cexMm.specifics.keys.title',
            message: 'Trade-only API keys',
            description: 'CEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.cexMm.specifics.keys.description',
            message:
              'You connect with a key that can place and cancel orders but cannot withdraw — funds never leave your exchange account.',
            description: 'CEX market making feature description',
          }),
        },
        {
          icon: '🪙',
          title: translate({
            id: 'pages.ideas.cexMm.specifics.spot.title',
            message: 'Spot pairs',
            description: 'CEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.cexMm.specifics.spot.description',
            message:
              'You quote real spot markets, so your inventory is the two actual assets in the pair — not a leveraged position.',
            description: 'CEX market making feature description',
          }),
        },
        {
          icon: '🌐',
          title: translate({
            id: 'pages.ideas.cexMm.specifics.venues.title',
            message: 'Multiple venues at once',
            description: 'CEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.cexMm.specifics.venues.description',
            message:
              'The same pair lives on many exchanges. You can quote it across several of them in parallel, each on its own book.',
            description: 'CEX market making feature description',
          }),
        },
        {
          icon: '🎟️',
          title: translate({
            id: 'pages.ideas.cexMm.specifics.maker.title',
            message: 'Maker programs',
            description: 'CEX market making feature title',
          }),
          description: translate({
            id: 'pages.ideas.cexMm.specifics.maker.description',
            message:
              'Because your limit orders add liquidity, exchanges often charge lower maker fees or run rebate programs that improve the economics.',
            description: 'CEX market making feature description',
          }),
        },
      ],
    },
    {
      kind: 'icons',
      eyebrow: translate({
        id: 'pages.ideas.cexMm.need.eyebrow',
        message: 'Before you start',
        description: 'CEX market making section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.cexMm.need.title',
        message: 'What you need to make markets on a CEX',
        description: 'CEX market making section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🏦',
          text: translate({
            id: 'pages.ideas.cexMm.need.account',
            message:
              'An account on a centralized exchange that supports API trading',
            description: 'CEX market making icon item',
          }),
        },
        {
          icon: '🔐',
          text: translate({
            id: 'pages.ideas.cexMm.need.key',
            message:
              'A trade-only API key — order permissions on, withdrawals off',
            description: 'CEX market making icon item',
          }),
        },
        {
          icon: '💰',
          text: translate({
            id: 'pages.ideas.cexMm.need.balance',
            message:
              'A balance of both assets in the pair, so the bot can quote each side',
            description: 'CEX market making icon item',
          }),
        },
        {
          icon: '🎯',
          text: translate({
            id: 'pages.ideas.cexMm.need.pair',
            message:
              'A spot pair you want to quote, plus the spread and inventory limits to run it',
            description: 'CEX market making icon item',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.cexMm.faq.title',
        message: 'CEX market making questions',
        description: 'CEX market making FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.cexMm.faq.q1',
            message: 'Why limit orders and not market orders?',
            description: 'CEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.cexMm.faq.a1',
            message:
              'A market maker is the side that posts resting orders for others to trade against. Those are limit orders. Market orders take liquidity and pay the spread instead of earning it, which is the opposite of what you want here.',
            description: 'CEX market making FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.cexMm.faq.q2',
            message: 'Can I run the same pair on more than one exchange?',
            description: 'CEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.cexMm.faq.a2',
            message:
              'Yes. Each exchange has its own order book, so you connect a key per venue and quote them independently. OctoBot manages the orders on each account separately.',
            description: 'CEX market making FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.cexMm.faq.q3',
            message: 'Does OctoBot ever hold the funds I quote with?',
            description: 'CEX market making FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.cexMm.faq.a3',
            message:
              'No. Everything stays on your centralized exchange account. OctoBot connects through a trade-only API key and only places and cancels orders on the book.',
            description: 'CEX market making FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.cexMm.cta.title',
      message: 'Make markets on your exchange',
      description: 'CEX market making CTA title',
    }),
    description: translate({
      id: 'pages.ideas.cexMm.cta.description',
      message:
        'Tell us which exchange and spot pair you want to quote, and we will help you get set up.',
      description: 'CEX market making CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.cexMm.cta.action.book',
          message: 'Book a call',
          description: 'CEX market making CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.cexMm.cta.action.bot',
          message: 'About the market making bot',
          description: 'CEX market making CTA action label',
        }),
        to: '/features/ideas/market-making-bot',
        variant: 'ghost',
      },
    ],
  },
};

export default function CexMarketMakingPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
