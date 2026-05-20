import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, DeviceVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/crypto-trading-bot-for-beginners
 * Angle: the first-bot experience — no code, ready-made strategies, paper mode first.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.beginners.meta.title',
      message: 'Crypto Trading Bot for Beginners — Start with no code',
      description: 'Beginners page meta title',
    }),
    description: translate({
      id: 'pages.ideas.beginners.meta.description',
      message:
        'A beginner-friendly crypto trading bot: pick a ready-made strategy, practise in paper mode, and go live when you are ready — all without writing a line of code.',
      description: 'Beginners page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.beginners.hero.eyebrow',
      message: 'Getting started',
      description: 'Beginners hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.beginners.hero.title"
        description="Beginners hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.beginners.hero.title.accent',
                message: 'no code required.',
                description: 'Beginners hero title accent',
              })}
            </span>
          ),
        }}>
        {'Your first crypto trading bot — {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.beginners.hero.subtitle',
      message:
        'You do not need to be a developer or a trader to start. Pick a strategy that already works, watch it run on simulated money, and only connect real funds once you understand what it does.',
      description: 'Beginners hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.beginners.hero.action.create',
          message: 'Create your first bot',
          description: 'Beginners hero action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.beginners.hero.action.guides',
          message: 'Browse the guides',
          description: 'Beginners hero action label',
        }),
        to: '/guides/octobot',
        variant: 'ghost',
      },
    ],
    visual: (
      <DeviceVisual
        label={translate({
          id: 'pages.ideas.beginners.visual.label',
          message: 'First-run setup',
          description: 'Beginners visual label',
        })}
        note="~ 5 min"
        lines={[
          {width: 70, accent: true},
          {width: 90},
          {width: 55},
          {width: 80},
        ]}
        cta={translate({
          id: 'pages.ideas.beginners.visual.cta',
          message: 'Start in paper mode',
          description: 'Beginners visual CTA',
        })}
      />
    ),
  },
  sections: [
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.beginners.start.eyebrow',
        message: 'Your first hour',
        description: 'Beginners section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.beginners.start.title',
        message: 'A path that does not assume you trade for a living',
        description: 'Beginners section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.beginners.start.pick.title',
            message: 'Pick a ready-made strategy',
            description: 'Beginners step title',
          }),
          description: translate({
            id: 'pages.ideas.beginners.start.pick.description',
            message:
              'Start from a built-in strategy base instead of a blank page. You can read what each one does in plain language.',
            description: 'Beginners step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.beginners.start.paper.title',
            message: 'Run it in paper mode',
            description: 'Beginners step title',
          }),
          description: translate({
            id: 'pages.ideas.beginners.start.paper.description',
            message:
              'The bot trades with simulated money against real prices, so mistakes cost nothing while you learn.',
            description: 'Beginners step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.beginners.start.live.title',
            message: 'Go live when it makes sense',
            description: 'Beginners step title',
          }),
          description: translate({
            id: 'pages.ideas.beginners.start.live.description',
            message:
              'Connect your exchange with a small amount first. You stay in custody of your funds the whole time.',
            description: 'Beginners step description',
          }),
        },
      ],
    },
    {
      kind: 'icons',
      eyebrow: translate({
        id: 'pages.ideas.beginners.skip.eyebrow',
        message: 'What you can skip',
        description: 'Beginners section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.beginners.skip.title',
        message: 'Things people think they need first — and do not',
        description: 'Beginners section title',
      }),
      columns: 2,
      items: [
        {
          icon: '🚫',
          text: translate({
            id: 'pages.ideas.beginners.skip.1',
            message: 'No programming — strategies are configured, not coded',
            description: 'Beginners icon item',
          }),
        },
        {
          icon: '🚫',
          text: translate({
            id: 'pages.ideas.beginners.skip.2',
            message: 'No big balance — paper mode and small live tests come first',
            description: 'Beginners icon item',
          }),
        },
        {
          icon: '🚫',
          text: translate({
            id: 'pages.ideas.beginners.skip.3',
            message: 'No server to manage — run it on OctoBot App',
            description: 'Beginners icon item',
          }),
        },
        {
          icon: '🚫',
          text: translate({
            id: 'pages.ideas.beginners.skip.4',
            message: 'No screen-watching — the bot runs while you do not',
            description: 'Beginners icon item',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.beginners.faq.title',
        message: 'Beginner questions',
        description: 'Beginners FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.beginners.faq.q1',
            message: 'Will a bot make me money?',
            description: 'Beginners FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.beginners.faq.a1',
            message:
              'No bot can promise that — markets move on their own. A bot makes a chosen strategy run consistently. Paper mode and backtesting are there so you can judge a strategy before risking anything.',
            description: 'Beginners FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.beginners.faq.q2',
            message: 'Is it safe to give a bot my exchange keys?',
            description: 'Beginners FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.beginners.faq.a2',
            message:
              'You create a trade-only API key with withdrawals disabled. OctoBot is open source, so the code that uses that key can be inspected.',
            description: 'Beginners FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.beginners.faq.q3',
            message: 'How much time does it take to maintain?',
            description: 'Beginners FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.beginners.faq.a3',
            message:
              'Once a strategy is running you mostly check in on it. Setup is the longest part, and that is measured in minutes.',
            description: 'Beginners FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.beginners.cta.title',
      message: 'Start with a bot you can actually understand',
      description: 'Beginners CTA title',
    }),
    description: translate({
      id: 'pages.ideas.beginners.cta.description',
      message:
        'Create a free OctoBot, try a strategy in paper mode, and learn at your own pace.',
      description: 'Beginners CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.beginners.cta.action.create',
          message: 'Create your first bot',
          description: 'Beginners CTA action label',
        }),
        to: 'https://www.octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.beginners.cta.action.paper',
          message: 'Learn about paper trading',
          description: 'Beginners CTA action label',
        }),
        to: '/features/ideas/paper-trading',
        variant: 'ghost',
      },
    ],
  },
};

export default function CryptoTradingBotForBeginnersPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
