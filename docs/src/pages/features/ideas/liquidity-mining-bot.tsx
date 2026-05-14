import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, BarsVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/liquidity-mining-bot
 * Angle: automating participation in exchange liquidity-mining / maker-reward programs.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.liquidityMining.meta.title',
      message: 'Liquidity Mining Bot — Automate exchange maker rewards',
      description: 'Liquidity mining bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityMining.meta.description',
      message:
        'Automate liquidity-mining and maker-reward programs with OctoBot — keep qualifying orders live around the clock to earn exchange rebates, on your own account.',
      description: 'Liquidity mining bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.liquidityMining.hero.eyebrow',
      message: 'Strategy · Liquidity mining',
      description: 'Liquidity mining bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.liquidityMining.hero.title"
        description="Liquidity mining bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.liquidityMining.hero.title.accent',
                message: 'around the clock.',
                description: 'Liquidity mining bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'Earn maker rewards, {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.liquidityMining.hero.subtitle',
      message:
        'Exchanges pay rebates and rewards to traders who post resting liquidity. A liquidity-mining bot keeps the qualifying orders live day and night, so the rewards accrue without you babysitting the order book.',
      description: 'Liquidity mining bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityMining.hero.action.contact',
          message: 'Talk to our team',
          description: 'Liquidity mining bot hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityMining.hero.action.marketMaking',
          message: 'See market making',
          description: 'Liquidity mining bot hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <BarsVisual
        label={translate({
          id: 'pages.ideas.liquidityMining.visual.label',
          message: 'Rewards accruing',
          description: 'Liquidity mining bot visual label',
        })}
        note="30d · maker rebates"
        bars={[
          {height: 18},
          {height: 26},
          {height: 33},
          {height: 41},
          {height: 50},
          {height: 58},
          {height: 67},
          {height: 78},
          {height: 88},
        ]}
        leftCaption={translate({
          id: 'pages.ideas.liquidityMining.visual.caption',
          message: 'Qualifying uptime 99%',
          description: 'Liquidity mining bot visual caption',
        })}
        pnl="+ rebates"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.liquidityMining.what.eyebrow',
        message: 'What it is',
        description: 'Liquidity mining bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityMining.what.title',
        message: 'Get paid for providing liquidity — if you can stay in the program',
        description: 'Liquidity mining bot section title',
      }),
      body: translate({
        id: 'pages.ideas.liquidityMining.what.body',
        message:
          'Many exchanges run liquidity-mining or maker-reward programs: post resting buy and sell orders on a target pair and the venue pays you rebates or token rewards for the depth you add. The catch is the eligibility rules — your orders usually have to sit within a set distance of the mid price, for a minimum size, for a minimum share of the time. Hit those thresholds by hand and a single missed re-quote can drop you below the bar for the whole period. That maintenance work is exactly what a bot is for.',
        description: 'Liquidity mining bot callout body',
      }),
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.liquidityMining.how.eyebrow',
        message: 'How it works',
        description: 'Liquidity mining bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityMining.how.title',
        message: 'From program rules to live qualifying orders',
        description: 'Liquidity mining bot section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.liquidityMining.how.pick.title',
            message: 'Pick a program and venue',
            description: 'Liquidity mining bot step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.how.pick.description',
            message:
              'Choose the exchange and the pair whose maker-reward program you want to farm, and note its eligibility rules — distance from mid, minimum size, uptime.',
            description: 'Liquidity mining bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.liquidityMining.how.configure.title',
            message: 'Set the bot to post qualifying orders',
            description: 'Liquidity mining bot step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.how.configure.description',
            message:
              'Connect a trade-enabled API key and configure the spread, order size and depth so every quote lands inside the program window. Funds stay on your own account.',
            description: 'Liquidity mining bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.liquidityMining.how.maintain.title',
            message: 'It maintains them 24/7',
            description: 'Liquidity mining bot step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.how.maintain.description',
            message:
              'As the price moves the bot re-quotes to keep orders in range, replaces filled orders, and runs through the night so your qualifying uptime stays high.',
            description: 'Liquidity mining bot step description',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.liquidityMining.handles.eyebrow',
        message: 'What the bot handles',
        description: 'Liquidity mining bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityMining.handles.title',
        message: 'The work that keeps you eligible',
        description: 'Liquidity mining bot section title',
      }),
      columns: 3,
      items: [
        {
          icon: '🎯',
          title: translate({
            id: 'pages.ideas.liquidityMining.handles.inRange.title',
            message: 'Keeping orders in range',
            description: 'Liquidity mining bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.handles.inRange.description',
            message:
              'Quotes are anchored to the mid price, so they stay inside the program’s distance window as the market drifts.',
            description: 'Liquidity mining bot feature description',
          }),
        },
        {
          icon: '🔄',
          title: translate({
            id: 'pages.ideas.liquidityMining.handles.requote.title',
            message: 'Re-quoting on every move',
            description: 'Liquidity mining bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.handles.requote.description',
            message:
              'When price shifts or an order fills, the bot cancels and re-posts immediately instead of leaving a gap in your depth.',
            description: 'Liquidity mining bot feature description',
          }),
        },
        {
          icon: '⏱️',
          title: translate({
            id: 'pages.ideas.liquidityMining.handles.eligibility.title',
            message: 'Tracking eligibility',
            description: 'Liquidity mining bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityMining.handles.eligibility.description',
            message:
              'Every order and fill is logged, so you can see how much qualifying time you accumulated against the program thresholds.',
            description: 'Liquidity mining bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.liquidityMining.faq.title',
        message: 'Liquidity mining bot questions',
        description: 'Liquidity mining bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.liquidityMining.faq.q1',
            message: 'Is liquidity mining the same as market making?',
            description: 'Liquidity mining bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityMining.faq.a1',
            message:
              'They overlap. Market making is the activity of posting two-sided quotes; liquidity mining is when an exchange explicitly rewards that activity with rebates or tokens. The bot does the same job either way — it just also targets the program’s eligibility rules.',
            description: 'Liquidity mining bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityMining.faq.q2',
            message: 'Does the bot hold my funds or rewards?',
            description: 'Liquidity mining bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityMining.faq.a2',
            message:
              'No. OctoBot is open source and connects through an exchange API key — your capital and any rewards the exchange pays out stay on your own account.',
            description: 'Liquidity mining bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityMining.faq.q3',
            message: 'What happens if the price moves sharply?',
            description: 'Liquidity mining bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityMining.faq.a3',
            message:
              'The bot re-quotes to follow the mid price and can be bounded with limits on spread and size. Liquidity mining still carries normal market risk — your resting orders can fill against a fast move — so it suits capital you are comfortable having quoted on the book.',
            description: 'Liquidity mining bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.liquidityMining.cta.title',
      message: 'Put a bot on your liquidity-mining program',
      description: 'Liquidity mining bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityMining.cta.description',
      message:
        'Tell us the program and venue you want to farm, and we’ll help you set OctoBot up to keep the qualifying orders live.',
      description: 'Liquidity mining bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityMining.cta.action.contact',
          message: 'Talk to our team',
          description: 'Liquidity mining bot CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityMining.cta.action.marketMaking',
          message: 'See market making',
          description: 'Liquidity mining bot CTA action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
  },
};

export default function LiquidityMiningBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
