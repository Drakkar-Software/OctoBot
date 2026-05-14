import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/token-liquidity
 * Angle: why a thin order book hurts a token, and how managed market making deepens it.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.tokenLiquidity.meta.title',
      message: 'Token Liquidity — Deepen your order book with market making',
      description: 'Token liquidity page meta title',
    }),
    description: translate({
      id: 'pages.ideas.tokenLiquidity.meta.description',
      message:
        'A thin order book gives your token wide spreads and painful slippage. OctoBot Market Making quotes both sides continuously to deepen liquidity on your exchange listings.',
      description: 'Token liquidity page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.tokenLiquidity.hero.eyebrow',
      message: 'For token projects · Liquidity',
      description: 'Token liquidity hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.tokenLiquidity.hero.title"
        description="Token liquidity hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.tokenLiquidity.hero.title.accent',
                message: 'a thin order book.',
                description: 'Token liquidity hero title accent',
              })}
            </span>
          ),
        }}>
        {"Don't let buyers meet {accent}"}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.tokenLiquidity.hero.subtitle',
      message:
        'When your token has only a handful of resting orders, every trade moves the price and the spread looks broken. Market making fills that book with two-sided quotes so the next buyer gets a fair price instead of a warning sign.',
      description: 'Token liquidity hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.hero.action.talk',
          message: 'Talk to our team',
          description: 'Token liquidity hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.hero.action.mm',
          message: 'See OctoBot Market Making',
          description: 'Token liquidity hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.tokenLiquidity.visual.label',
          message: 'Order book — after market making',
          description: 'Token liquidity visual label',
        })}
        note="TOKEN/USDT"
        asks={[
          {price: '1.024', size: '8.2k', depth: 70},
          {price: '1.018', size: '6.4k', depth: 55},
          {price: '1.012', size: '5.1k', depth: 44},
          {price: '1.006', size: '4.0k', depth: 34},
        ]}
        bids={[
          {price: '0.994', size: '4.1k', depth: 35},
          {price: '0.988', size: '5.3k', depth: 46},
          {price: '0.982', size: '6.6k', depth: 57},
          {price: '0.976', size: '8.0k', depth: 69},
        ]}
        mid="1.000"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.tokenLiquidity.what.eyebrow',
        message: 'The problem',
        description: 'Token liquidity section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tokenLiquidity.what.title',
        message: 'A thin book is a tax on everyone who trades your token',
        description: 'Token liquidity section title',
      }),
      body: translate({
        id: 'pages.ideas.tokenLiquidity.what.body',
        message:
          'Liquidity is just how many orders are resting near the current price. When that book is thin, the gap between the best bid and best ask widens, and even a modest buy walks the price up several percent before it fills. A trader who opens your market sees a jagged spread and shallow depth — and reads it, fairly, as risk. The token itself can be sound; the order book is what makes the first impression.',
        description: 'Token liquidity callout body',
      }),
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.tokenLiquidity.how.eyebrow',
        message: 'How we deepen it',
        description: 'Token liquidity section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tokenLiquidity.how.title',
        message: 'From a shallow market to a market people trust',
        description: 'Token liquidity section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.tokenLiquidity.how.assess.title',
            message: 'Assess your current depth',
            description: 'Token liquidity step title',
          }),
          description: translate({
            id: 'pages.ideas.tokenLiquidity.how.assess.description',
            message:
              'We measure the spread and how much size sits within a few percent of mid on each exchange you are listed on — the real starting point, not a guess.',
            description: 'Token liquidity step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.tokenLiquidity.how.budget.title',
            message: 'Set a budget and spread targets',
            description: 'Token liquidity step title',
          }),
          description: translate({
            id: 'pages.ideas.tokenLiquidity.how.budget.description',
            message:
              'You decide how much inventory the bot quotes with and how tight the spread should be. Those numbers are yours to set and adjust as the market matures.',
            description: 'Token liquidity step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.tokenLiquidity.how.quote.title',
            message: 'Quote both sides continuously',
            description: 'Token liquidity step title',
          }),
          description: translate({
            id: 'pages.ideas.tokenLiquidity.how.quote.description',
            message:
              'OctoBot Market Making places and refreshes buy and sell orders around the price around the clock, connected through your exchange API keys — it never takes custody of your funds.',
            description: 'Token liquidity step description',
          }),
        },
      ],
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.tokenLiquidity.compare.eyebrow',
        message: 'Thin vs deep',
        description: 'Token liquidity section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.tokenLiquidity.compare.title',
        message: 'What changes when the book fills out',
        description: 'Token liquidity section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.compare.before.label',
          message: 'Thin order book',
          description: 'Token liquidity before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.before.1',
            message: 'Wide, jumpy spread between bid and ask',
            description: 'Token liquidity before item',
          }),
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.before.2',
            message: 'A normal-sized buy slips the price several percent',
            description: 'Token liquidity before item',
          }),
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.before.3',
            message: 'New buyers read the chart as risky and walk away',
            description: 'Token liquidity before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.compare.after.label',
          message: 'Deep order book',
          description: 'Token liquidity after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.after.1',
            message: 'Tight spread that holds through normal flow',
            description: 'Token liquidity after item',
          }),
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.after.2',
            message: 'Size near mid absorbs trades with little slippage',
            description: 'Token liquidity after item',
          }),
          translate({
            id: 'pages.ideas.tokenLiquidity.compare.after.3',
            message: 'The market looks healthy enough to trade with confidence',
            description: 'Token liquidity after item',
          }),
        ],
      },
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.tokenLiquidity.faq.title',
        message: 'Token liquidity questions',
        description: 'Token liquidity FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.tokenLiquidity.faq.q1',
            message: 'Does market making create real volume?',
            description: 'Token liquidity FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tokenLiquidity.faq.a1',
            message:
              'It creates depth — genuine resting buy and sell orders that real traders can fill. The goal is a healthier book and a tighter spread, not inflated trade counts.',
            description: 'Token liquidity FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.tokenLiquidity.faq.q2',
            message: 'Where does my token inventory sit?',
            description: 'Token liquidity FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tokenLiquidity.faq.a2',
            message:
              'On your own exchange account. OctoBot Market Making connects through API keys on centralized order-book exchanges and never holds your funds.',
            description: 'Token liquidity FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.tokenLiquidity.faq.q3',
            message: 'We are about to list — when should we start?',
            description: 'Token liquidity FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.tokenLiquidity.faq.a3',
            message:
              'Ideally before the first buyers arrive, so day one shows a deep book. If you are still planning the listing itself, start with our token listing guide.',
            description: 'Token liquidity FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.tokenLiquidity.cta.title',
      message: 'Give your token a book worth trading on',
      description: 'Token liquidity CTA title',
    }),
    description: translate({
      id: 'pages.ideas.tokenLiquidity.cta.description',
      message:
        'Tell us which exchanges you are listed on and the depth you want. We will map out a market-making setup that fits your token.',
      description: 'Token liquidity CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.cta.action.talk',
          message: 'Book a call',
          description: 'Token liquidity CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.tokenLiquidity.cta.action.listing',
          message: 'Planning a listing? Start here',
          description: 'Token liquidity CTA action label',
        }),
        to: '/features/token-listing',
        variant: 'ghost',
      },
    ],
  },
};

export default function TokenLiquidityPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
