import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, MetricVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/liquidity-score
 * Angle: explain the liquidity score — one 0-100 metric for how healthy a market's liquidity is.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.liquidityScore.meta.title',
      message: 'Liquidity Score — One number for how healthy a market is',
      description: 'Liquidity score page meta title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityScore.meta.description',
      message:
        'The liquidity score condenses spread, order book depth, two-sided balance and quoting uptime into a single 0-100 metric — so you can see at a glance how healthy your market is.',
      description: 'Liquidity score page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.liquidityScore.hero.eyebrow',
      message: 'Concept · Liquidity score',
      description: 'Liquidity score hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.liquidityScore.hero.title"
        description="Liquidity score hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.liquidityScore.hero.title.accent',
                message: 'one number.',
                description: 'Liquidity score hero title accent',
              })}
            </span>
          ),
        }}>
        {'How healthy is your market? Read it in {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.liquidityScore.hero.subtitle',
      message:
        'Spread, depth, balance and uptime each tell part of the story. The liquidity score rolls them into a single 0-100 figure so you — and anyone you report to — can tell good from bad without reading a full order book.',
      description: 'Liquidity score hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityScore.hero.action.talk',
          message: 'Talk to our team',
          description: 'Liquidity score hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityScore.hero.action.mm',
          message: 'See OctoBot Market Making',
          description: 'Liquidity score hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <MetricVisual
        label={translate({
          id: 'pages.ideas.liquidityScore.visual.label',
          message: 'Liquidity score',
          description: 'Liquidity score visual label',
        })}
        note="TOKEN/USDT"
        value="82"
        unit="/100"
        caption={translate({
          id: 'pages.ideas.liquidityScore.visual.caption',
          message: 'Healthy — tight spread, depth on both sides',
          description: 'Liquidity score visual caption',
        })}
        rows={[
          {
            label: translate({
              id: 'pages.ideas.liquidityScore.visual.row.spread',
              message: 'Spread tightness',
              description: 'Liquidity score visual row label',
            }),
            value: '0.18%',
          },
          {
            label: translate({
              id: 'pages.ideas.liquidityScore.visual.row.depth',
              message: 'Depth within 2%',
              description: 'Liquidity score visual row label',
            }),
            value: 'Strong',
          },
          {
            label: translate({
              id: 'pages.ideas.liquidityScore.visual.row.balance',
              message: 'Bid / ask balance',
              description: 'Liquidity score visual row label',
            }),
            value: 'Even',
          },
          {
            label: translate({
              id: 'pages.ideas.liquidityScore.visual.row.uptime',
              message: 'Quoting uptime',
              description: 'Liquidity score visual row label',
            }),
            value: '99.4%',
          },
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.liquidityScore.what.eyebrow',
        message: 'What it is',
        description: 'Liquidity score section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityScore.what.title',
        message: 'A single 0-100 read on liquidity health',
        description: 'Liquidity score section title',
      }),
      body: translate({
        id: 'pages.ideas.liquidityScore.what.body',
        message:
          'The liquidity score is OctoBot Market Making’s summary metric for a market. Instead of asking you to interpret a spread figure, a depth chart and an uptime log separately, it weighs those signals together into one number that moves up when the book gets healthier and down when it thins out. A single figure is useful because it is comparable — across pairs, across exchanges, and across time — and because it gives a non-trader on your team something they can actually act on.',
        description: 'Liquidity score callout body',
      }),
    },
    {
      kind: 'icons',
      eyebrow: translate({
        id: 'pages.ideas.liquidityScore.inputs.eyebrow',
        message: 'What feeds it',
        description: 'Liquidity score section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityScore.inputs.title',
        message: 'The four signals behind the number',
        description: 'Liquidity score section title',
      }),
      columns: 2,
      items: [
        {
          icon: '↔️',
          text: translate({
            id: 'pages.ideas.liquidityScore.inputs.spread',
            message:
              'Spread tightness — how small the gap is between the best bid and the best ask.',
            description: 'Liquidity score icon item',
          }),
        },
        {
          icon: '📚',
          text: translate({
            id: 'pages.ideas.liquidityScore.inputs.depth',
            message:
              'Order book depth — how much size is resting close to the mid price, ready to absorb trades.',
            description: 'Liquidity score icon item',
          }),
        },
        {
          icon: '⚖️',
          text: translate({
            id: 'pages.ideas.liquidityScore.inputs.balance',
            message:
              'Two-sided balance — whether buy and sell depth are roughly even rather than lopsided.',
            description: 'Liquidity score icon item',
          }),
        },
        {
          icon: '⏱️',
          text: translate({
            id: 'pages.ideas.liquidityScore.inputs.uptime',
            message:
              'Quoting uptime — how consistently quotes are present, not just there in calm moments.',
            description: 'Liquidity score icon item',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.liquidityScore.read.eyebrow',
        message: 'Using it',
        description: 'Liquidity score section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityScore.read.title',
        message: 'How to read a score — and move it up',
        description: 'Liquidity score section title',
      }),
      columns: 3,
      items: [
        {
          icon: '📈',
          title: translate({
            id: 'pages.ideas.liquidityScore.read.bands.title',
            message: 'Read the bands',
            description: 'Liquidity score feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityScore.read.bands.description',
            message:
              'A high score means a tight, deep, balanced book; a low one points to a thin or one-sided market that needs attention.',
            description: 'Liquidity score feature description',
          }),
        },
        {
          icon: '🔍',
          title: translate({
            id: 'pages.ideas.liquidityScore.read.diagnose.title',
            message: 'Diagnose the drop',
            description: 'Liquidity score feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityScore.read.diagnose.description',
            message:
              'Because the score breaks down by signal, a dip tells you whether the spread widened, depth thinned, or quoting lapsed.',
            description: 'Liquidity score feature description',
          }),
        },
        {
          icon: '🎛️',
          title: translate({
            id: 'pages.ideas.liquidityScore.read.tune.title',
            message: 'Tune the bot',
            description: 'Liquidity score feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityScore.read.tune.description',
            message:
              'Adjust the market-making budget and spread targets, then watch the score respond — a clear feedback loop instead of guesswork.',
            description: 'Liquidity score feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.liquidityScore.faq.title',
        message: 'Liquidity score questions',
        description: 'Liquidity score FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.liquidityScore.faq.q1',
            message: 'What counts as a good liquidity score?',
            description: 'Liquidity score FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityScore.faq.a1',
            message:
              'Higher is better, and the right target depends on the market — a major pair can sustain a very high score, a young token starts lower. What matters most is the trend: a score climbing toward the upper bands means the book is getting healthier.',
            description: 'Liquidity score FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityScore.faq.q2',
            message: 'Why use one number instead of the raw metrics?',
            description: 'Liquidity score FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityScore.faq.a2',
            message:
              'The raw metrics are still there when you need them. The score sits on top so you can compare markets and track progress without re-interpreting four charts every time.',
            description: 'Liquidity score FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityScore.faq.q3',
            message: 'How do I improve a low score?',
            description: 'Liquidity score FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityScore.faq.a3',
            message:
              'Deepen the book. Running OctoBot Market Making with a suitable budget and spread targets tightens the spread and adds two-sided depth — the inputs the score is built from. See how a thin book gets deepened in our token liquidity page.',
            description: 'Liquidity score FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.liquidityScore.cta.title',
      message: 'Put a number on your market’s health',
      description: 'Liquidity score CTA title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityScore.cta.description',
      message:
        'Tell us about your market and we will walk you through your current liquidity score and what it would take to raise it.',
      description: 'Liquidity score CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityScore.cta.action.talk',
          message: 'Book a call',
          description: 'Liquidity score CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityScore.cta.action.liquidity',
          message: 'How market making deepens a book',
          description: 'Liquidity score CTA action label',
        }),
        to: '/features/ideas/token-liquidity',
        variant: 'ghost',
      },
    ],
  },
};

export default function LiquidityScorePage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
