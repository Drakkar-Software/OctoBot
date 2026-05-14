import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, BarsVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/paper-trading
 * Angle: risk-free practice — simulated balance, real market data.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.paper.meta.title',
      message: 'Crypto Paper Trading — Practise strategies with zero risk',
      description: 'Paper trading page meta title',
    }),
    description: translate({
      id: 'pages.ideas.paper.meta.description',
      message:
        'Paper trade crypto with OctoBot — run any strategy on a simulated balance against live market prices, with no money on the line, before going live.',
      description: 'Paper trading page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.paper.hero.eyebrow',
      message: 'Mode · Paper trading',
      description: 'Paper trading hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.paper.hero.title"
        description="Paper trading hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.paper.hero.title.accent',
                message: 'before it costs anything.',
                description: 'Paper trading hero title accent',
              })}
            </span>
          ),
        }}>
        {'See how a strategy behaves {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.paper.hero.subtitle',
      message:
        'Paper trading runs a real strategy on a simulated balance, priced off live markets. It is the gap between a backtest and live money — long enough to expose how a strategy feels in real time, with nothing at stake.',
      description: 'Paper trading hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.paper.hero.action.create',
          message: 'Start paper trading',
          description: 'Paper trading hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.paper.hero.action.app',
          message: 'See the OctoBot App',
          description: 'Paper trading hero action label',
        }),
        to: '/features/octobot-app',
        variant: 'ghost',
      },
    ],
    visual: (
      <BarsVisual
        label={translate({
          id: 'pages.ideas.paper.visual.label',
          message: 'Simulated equity',
          description: 'Paper trading visual label',
        })}
        note="paper · 30d"
        bars={[
          {height: 30},
          {height: 38},
          {height: 34},
          {height: 50},
          {height: 46},
          {height: 62},
          {height: 58},
          {height: 74},
        ]}
        leftCaption={translate({
          id: 'pages.ideas.paper.visual.caption',
          message: 'No funds at risk',
          description: 'Paper trading visual caption',
        })}
        pnl="+ 9.7%"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.paper.what.eyebrow',
        message: 'What it is',
        description: 'Paper trading section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.paper.what.title',
        message: 'A live dry run, not a replay',
        description: 'Paper trading section title',
      }),
      body: translate({
        id: 'pages.ideas.paper.what.body',
        message:
          'A backtest tells you how a strategy would have done on history it can see all at once. Paper trading is different: the bot only knows what the market knows right now, and reacts tick by tick. That catches the things history hides — latency, indecision around news, how it feels to watch a drawdown unfold — without a single real order.',
        description: 'Paper trading callout body',
      }),
    },
    {
      kind: 'beforeAfter',
      eyebrow: translate({
        id: 'pages.ideas.paper.compare.eyebrow',
        message: 'Paper vs live',
        description: 'Paper trading section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.paper.compare.title',
        message: 'What stays the same, what changes',
        description: 'Paper trading section title',
      }),
      before: {
        label: translate({
          id: 'pages.ideas.paper.compare.before.label',
          message: 'Paper mode',
          description: 'Paper trading before label',
        }),
        items: [
          translate({
            id: 'pages.ideas.paper.compare.before.1',
            message: 'Real prices, simulated balance',
            description: 'Paper trading before item',
          }),
          translate({
            id: 'pages.ideas.paper.compare.before.2',
            message: 'Same strategy logic and signals as live',
            description: 'Paper trading before item',
          }),
          translate({
            id: 'pages.ideas.paper.compare.before.3',
            message: 'Mistakes cost nothing',
            description: 'Paper trading before item',
          }),
        ],
      },
      after: {
        label: translate({
          id: 'pages.ideas.paper.compare.after.label',
          message: 'Live mode',
          description: 'Paper trading after label',
        }),
        items: [
          translate({
            id: 'pages.ideas.paper.compare.after.1',
            message: 'Real fills, real fees, real slippage',
            description: 'Paper trading after item',
          }),
          translate({
            id: 'pages.ideas.paper.compare.after.2',
            message: 'Exact same configuration — flip the switch',
            description: 'Paper trading after item',
          }),
          translate({
            id: 'pages.ideas.paper.compare.after.3',
            message: 'Funds stay on your own exchange account',
            description: 'Paper trading after item',
          }),
        ],
      },
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.paper.use.eyebrow',
        message: 'When to use it',
        description: 'Paper trading section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.paper.use.title',
        message: 'Good moments to be on paper',
        description: 'Paper trading section title',
      }),
      columns: 3,
      items: [
        {
          icon: '🆕',
          title: translate({
            id: 'pages.ideas.paper.use.new.title',
            message: 'A new strategy',
            description: 'Paper trading feature title',
          }),
          description: translate({
            id: 'pages.ideas.paper.use.new.description',
            message:
              'Let it run for a while before deciding whether it earns real funds.',
            description: 'Paper trading feature description',
          }),
        },
        {
          icon: '🔧',
          title: translate({
            id: 'pages.ideas.paper.use.tweak.title',
            message: 'After a change',
            description: 'Paper trading feature title',
          }),
          description: translate({
            id: 'pages.ideas.paper.use.tweak.description',
            message:
              'Adjusted a parameter? Watch the new version on paper before promoting it.',
            description: 'Paper trading feature description',
          }),
        },
        {
          icon: '🎓',
          title: translate({
            id: 'pages.ideas.paper.use.learn.title',
            message: 'While learning',
            description: 'Paper trading feature title',
          }),
          description: translate({
            id: 'pages.ideas.paper.use.learn.description',
            message:
              'Get used to how the bot reports and behaves with nothing on the line.',
            description: 'Paper trading feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.paper.faq.title',
        message: 'Paper trading questions',
        description: 'Paper trading FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.paper.faq.q1',
            message: 'Does paper trading need an exchange API key?',
            description: 'Paper trading FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.paper.faq.a1',
            message:
              'No. Paper mode only reads public market data, so you can run it without connecting any account.',
            description: 'Paper trading FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.paper.faq.q2',
            message: 'How close is paper performance to live?',
            description: 'Paper trading FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.paper.faq.a2',
            message:
              'Close on signals and timing, but live trading adds fees and slippage. Treat paper results as the optimistic edge of the range.',
            description: 'Paper trading FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.paper.faq.q3',
            message: 'Can I switch a paper bot to live?',
            description: 'Paper trading FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.paper.faq.a3',
            message:
              'Yes — the configuration carries over. You connect an exchange account and switch the mode.',
            description: 'Paper trading FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.paper.cta.title',
      message: 'Try a strategy with nothing at stake',
      description: 'Paper trading CTA title',
    }),
    description: translate({
      id: 'pages.ideas.paper.cta.description',
      message:
        'Create a free OctoBot and run your first strategy in paper mode against live markets.',
      description: 'Paper trading CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.paper.cta.action.create',
          message: 'Start paper trading',
          description: 'Paper trading CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.paper.cta.action.backtest',
          message: 'Compare with backtesting',
          description: 'Paper trading CTA action label',
        }),
        to: '/features/ideas/backtesting',
        variant: 'ghost',
      },
    ],
  },
};

export default function PaperTradingPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
