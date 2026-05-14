import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, BarsVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/backtesting
 * Angle: test a strategy on historical data before risking real money — and why a good backtest is not a guarantee.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.backtesting.meta.title',
      message: 'Backtesting — Test a crypto trading strategy on past data',
      description: 'Backtesting page meta title',
    }),
    description: translate({
      id: 'pages.ideas.backtesting.meta.description',
      message:
        'Backtest your crypto strategy with OctoBot — replay it against years of historical market data, read a full performance report, and risk zero funds doing it.',
      description: 'Backtesting page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.backtesting.hero.eyebrow',
      message: 'Method · Backtesting',
      description: 'Backtesting hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.backtesting.hero.title"
        description="Backtesting hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.backtesting.hero.title.accent',
                message: 'before you risk a cent.',
                description: 'Backtesting hero title accent',
              })}
            </span>
          ),
        }}>
        {'Find out if your strategy works {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.backtesting.hero.subtitle',
      message:
        'Backtesting replays your strategy over real historical prices and shows you what it would have done. It turns "I think this works" into a number you can actually look at — without putting any money on the line.',
      description: 'Backtesting hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.backtesting.hero.action.create',
          message: 'Backtest your strategy',
          description: 'Backtesting hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.backtesting.hero.action.paper',
          message: 'See paper trading',
          description: 'Backtesting hero action label',
        }),
        to: '/features/ideas/paper-trading',
        variant: 'ghost',
      },
    ],
    visual: (
      <BarsVisual
        label={translate({
          id: 'pages.ideas.backtesting.visual.label',
          message: 'Backtest run',
          description: 'Backtesting visual label',
        })}
        note="BTC/USDT · 3y replay"
        bars={[
          {height: 30},
          {height: 44},
          {height: 38, muted: true},
          {height: 58},
          {height: 50, muted: true},
          {height: 72},
          {height: 64, muted: true},
          {height: 84},
          {height: 76},
        ]}
        leftCaption={translate({
          id: 'pages.ideas.backtesting.visual.caption',
          message: '1,240 trades simulated',
          description: 'Backtesting visual caption',
        })}
        pnl="+ 31.4%"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.backtesting.what.eyebrow',
        message: 'What it is',
        description: 'Backtesting section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.backtesting.what.title',
        message: 'A rehearsal on real prices — and its limits',
        description: 'Backtesting section title',
      }),
      body: translate({
        id: 'pages.ideas.backtesting.what.body',
        message:
          'A backtest feeds your strategy the price history of a market, candle by candle, and records every trade it would have made. The result is a concrete track record instead of a hunch. But a backtest only describes the past: a strategy tuned until it looks perfect on old data is usually just memorising that data — a trap called overfitting. The honest use of a backtest is to reject ideas that clearly fail and to size your expectations, not to promise a future return.',
        description: 'Backtesting callout body',
      }),
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.backtesting.how.eyebrow',
        message: 'How it works',
        description: 'Backtesting section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.backtesting.how.title',
        message: 'Three steps from strategy to verdict',
        description: 'Backtesting section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.backtesting.how.load.title',
            message: 'Load historical data',
            description: 'Backtesting step title',
          }),
          description: translate({
            id: 'pages.ideas.backtesting.how.load.description',
            message:
              'Pick a pair and a time window. OctoBot pulls the candle history so the test runs on the same prices the market actually printed.',
            description: 'Backtesting step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.backtesting.how.run.title',
            message: 'Run the strategy',
            description: 'Backtesting step title',
          }),
          description: translate({
            id: 'pages.ideas.backtesting.how.run.description',
            message:
              'The same strategy logic that would trade live is replayed over that window, placing simulated orders as the price moves.',
            description: 'Backtesting step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.backtesting.how.read.title',
            message: 'Read the performance report',
            description: 'Backtesting step title',
          }),
          description: translate({
            id: 'pages.ideas.backtesting.how.read.description',
            message:
              'Profit and loss, trade count, drawdown and win rate land in one report — so you can compare configurations on evidence, not feel.',
            description: 'Backtesting step description',
          }),
        },
      ],
    },
    {
      kind: 'stats',
      eyebrow: translate({
        id: 'pages.ideas.backtesting.stats.eyebrow',
        message: 'Why it is worth doing',
        description: 'Backtesting section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.backtesting.stats.title',
        message: 'A lot of testing, none of the risk',
        description: 'Backtesting section title',
      }),
      items: [
        {
          value: translate({
            id: 'pages.ideas.backtesting.stats.years.value',
            message: 'Years',
            description: 'Backtesting stat value',
          }),
          label: translate({
            id: 'pages.ideas.backtesting.stats.years.label',
            message: 'of candle history to replay against',
            description: 'Backtesting stat label',
          }),
          sub: translate({
            id: 'pages.ideas.backtesting.stats.years.sub',
            message: 'as far back as the exchange data goes',
            description: 'Backtesting stat sub',
          }),
        },
        {
          value: translate({
            id: 'pages.ideas.backtesting.stats.seconds.value',
            message: 'Seconds',
            description: 'Backtesting stat value',
          }),
          label: translate({
            id: 'pages.ideas.backtesting.stats.seconds.label',
            message: 'to replay a long window and get a report',
            description: 'Backtesting stat label',
          }),
          sub: translate({
            id: 'pages.ideas.backtesting.stats.seconds.sub',
            message: 'fast enough to test many variations',
            description: 'Backtesting stat sub',
          }),
        },
        {
          value: '0',
          label: translate({
            id: 'pages.ideas.backtesting.stats.risk.label',
            message: 'real funds at risk during a backtest',
            description: 'Backtesting stat label',
          }),
          sub: translate({
            id: 'pages.ideas.backtesting.stats.risk.sub',
            message: 'every order is simulated, nothing is sent',
            description: 'Backtesting stat sub',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.backtesting.faq.title',
        message: 'Backtesting questions',
        description: 'Backtesting FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.backtesting.faq.q1',
            message: 'Does a good backtest mean the strategy will be profitable?',
            description: 'Backtesting FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.backtesting.faq.a1',
            message:
              'No. A backtest shows how a strategy behaved on past prices, not how it will behave next. Markets change, and a result that looks too perfect is often overfitting. Treat a strong backtest as a reason to keep testing — ideally with paper trading next — not as a guarantee.',
            description: 'Backtesting FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.backtesting.faq.q2',
            message: 'How do I avoid overfitting?',
            description: 'Backtesting FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.backtesting.faq.a2',
            message:
              'Keep the strategy simple, test it across several different pairs and time periods rather than tuning to one, and be suspicious of results that only appear with very specific settings. A strategy that holds up in many conditions is more trustworthy than one that is perfect in exactly one.',
            description: 'Backtesting FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.backtesting.faq.q3',
            message: 'What should I do after a backtest looks good?',
            description: 'Backtesting FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.backtesting.faq.a3',
            message:
              'Run it forward in paper trading — the same strategy on live prices with simulated money. That catches problems a historical replay cannot, like how the strategy reacts to conditions it never saw in the test window.',
            description: 'Backtesting FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.backtesting.cta.title',
      message: 'Test it on the past before you trust it with the present',
      description: 'Backtesting CTA title',
    }),
    description: translate({
      id: 'pages.ideas.backtesting.cta.description',
      message:
        'Create a free OctoBot, replay your strategy over years of data, and read the report before a single real order goes out.',
      description: 'Backtesting CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.backtesting.cta.action.create',
          message: 'Backtest your strategy',
          description: 'Backtesting CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.backtesting.cta.action.paper',
          message: 'See paper trading',
          description: 'Backtesting CTA action label',
        }),
        to: '/features/ideas/paper-trading',
        variant: 'ghost',
      },
    ],
  },
};

export default function BacktestingPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
