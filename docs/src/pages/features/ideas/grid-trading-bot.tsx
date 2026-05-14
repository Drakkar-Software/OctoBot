import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, BarsVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/grid-trading-bot
 * Angle: the grid mechanic itself — laddered orders that harvest range volatility.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.gridBot.meta.title',
      message: 'Grid Trading Bot — Automate range trading on crypto',
      description: 'Grid bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.gridBot.meta.description',
      message:
        'Run a grid trading bot with OctoBot — a ladder of buy and sell orders that turns sideways price action into repeated small profits, on your own exchange account.',
      description: 'Grid bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.gridBot.hero.eyebrow',
      message: 'Strategy · Grid trading',
      description: 'Grid bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.gridBot.hero.title"
        description="Grid bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.gridBot.hero.title.accent',
                message: 'every swing.',
                description: 'Grid bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'Trade the range, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.gridBot.hero.subtitle',
      message:
        'A grid bot places a ladder of orders above and below the price. Each time the market crosses a rung it books a small profit and resets — so a market that goes nowhere still does something.',
      description: 'Grid bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.gridBot.hero.action.create',
          message: 'Create your grid bot',
          description: 'Grid bot hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.gridBot.hero.action.designer',
          message: 'Open the strategy designer',
          description: 'Grid bot hero action label',
        }),
        to: '/features/strategy-designer',
        variant: 'ghost',
      },
    ],
    visual: (
      <BarsVisual
        label={translate({
          id: 'pages.ideas.gridBot.visual.label',
          message: 'Grid fills',
          description: 'Grid bot visual label',
        })}
        note="24h · range-bound"
        bars={[
          {height: 40},
          {height: 64, muted: true},
          {height: 32},
          {height: 70, muted: true},
          {height: 48},
          {height: 80, muted: true},
          {height: 38},
          {height: 60, muted: true},
          {height: 52},
        ]}
        leftCaption={translate({
          id: 'pages.ideas.gridBot.visual.caption',
          message: '38 round-trips',
          description: 'Grid bot visual caption',
        })}
        pnl="+ 2.1%"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.gridBot.what.eyebrow',
        message: 'The mechanic',
        description: 'Grid bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.gridBot.what.title',
        message: 'Buy low, sell high — many times, automatically',
        description: 'Grid bot section title',
      }),
      body: translate({
        id: 'pages.ideas.gridBot.what.body',
        message:
          'You pick a price range and a number of grid levels. The bot fills the range with limit orders: buys below the price, sells above it. When a buy fills, a sell is placed one rung up; when that sell fills, the buy goes back. The profit is the gap between rungs, captured over and over as price oscillates inside the range.',
        description: 'Grid bot callout body',
      }),
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.gridBot.compare.eyebrow',
        message: 'Manual vs bot',
        description: 'Grid bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.gridBot.compare.title',
        message: 'Why a grid is a job for software',
        description: 'Grid bot section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.gridBot.compare.before.label',
          message: 'Doing it by hand',
          description: 'Grid bot before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.gridBot.compare.before.1',
            message: 'Re-placing dozens of orders after every fill',
            description: 'Grid bot before item',
          }),
          translate({
            id: 'pages.ideas.gridBot.compare.before.2',
            message: 'Missing rungs while you sleep',
            description: 'Grid bot before item',
          }),
          translate({
            id: 'pages.ideas.gridBot.compare.before.3',
            message: 'No clean record of what the range actually returned',
            description: 'Grid bot before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.gridBot.compare.after.label',
          message: 'Running a grid bot',
          description: 'Grid bot after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.gridBot.compare.after.1',
            message: 'Orders re-armed the instant they fill',
            description: 'Grid bot after item',
          }),
          translate({
            id: 'pages.ideas.gridBot.compare.after.2',
            message: 'Runs 24/7 across every rung',
            description: 'Grid bot after item',
          }),
          translate({
            id: 'pages.ideas.gridBot.compare.after.3',
            message: 'Every round-trip logged and backtestable',
            description: 'Grid bot after item',
          }),
        ],
      },
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.gridBot.tune.eyebrow',
        message: 'Tuning it',
        description: 'Grid bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.gridBot.tune.title',
        message: 'The knobs that decide how a grid behaves',
        description: 'Grid bot section title',
      }),
      columns: 3,
      items: [
        {
          icon: '📏',
          title: translate({
            id: 'pages.ideas.gridBot.tune.range.title',
            message: 'Range width',
            description: 'Grid bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.gridBot.tune.range.description',
            message:
              'Wider ranges survive bigger moves; tighter ranges trade more often.',
            description: 'Grid bot feature description',
          }),
        },
        {
          icon: '🪜',
          title: translate({
            id: 'pages.ideas.gridBot.tune.levels.title',
            message: 'Grid levels',
            description: 'Grid bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.gridBot.tune.levels.description',
            message:
              'More rungs means smaller, more frequent profits per crossing.',
            description: 'Grid bot feature description',
          }),
        },
        {
          icon: '🛡️',
          title: translate({
            id: 'pages.ideas.gridBot.tune.exit.title',
            message: 'Range exit',
            description: 'Grid bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.gridBot.tune.exit.description',
            message:
              'Set what happens when price leaves the grid — stop, hold, or re-center.',
            description: 'Grid bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.gridBot.faq.title',
        message: 'Grid trading bot questions',
        description: 'Grid bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.gridBot.faq.q1',
            message: 'When does a grid bot work best?',
            description: 'Grid bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.gridBot.faq.a1',
            message:
              'In sideways or choppy markets. A strong sustained trend will eventually push price out of the range, which is why the range-exit setting matters.',
            description: 'Grid bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.gridBot.faq.q2',
            message: 'Can I backtest a grid before running it?',
            description: 'Grid bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.gridBot.faq.a2',
            message:
              'Yes — OctoBot can replay a grid configuration against historical data so you can see how the range and level count would have performed.',
            description: 'Grid bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.gridBot.faq.q3',
            message: 'Where do my funds sit?',
            description: 'Grid bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.gridBot.faq.a3',
            message:
              'On your own exchange account. OctoBot connects through an API key and never takes custody.',
            description: 'Grid bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.gridBot.cta.title',
      message: 'Put a grid to work on your range',
      description: 'Grid bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.gridBot.cta.description',
      message:
        'Configure a grid, backtest it, and let OctoBot keep the ladder armed around the clock.',
      description: 'Grid bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.gridBot.cta.action.create',
          message: 'Create your grid bot',
          description: 'Grid bot CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.gridBot.cta.action.backtest',
          message: 'Learn about backtesting',
          description: 'Grid bot CTA action label',
        }),
        to: '/features/ideas/backtesting',
        variant: 'ghost',
      },
    ],
  },
};

export default function GridTradingBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
