import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/market-making-bot
 * Angle: the open-source market-making bot as a tool — software that quotes both sides of a book for you.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.mmBot.meta.title',
      message: 'Market Making Bot — Open-source two-sided quoting software',
      description: 'Market making bot page meta title',
    }),
    description: translate({
      id: 'pages.ideas.mmBot.meta.description',
      message:
        'An open-source market-making bot that quotes buy and sell orders around the price, manages spread and inventory, and re-quotes on every fill — running on your own exchange account.',
      description: 'Market making bot page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.mmBot.hero.eyebrow',
      message: 'Tool · Market making bot',
      description: 'Market making bot hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.mmBot.hero.title"
        description="Market making bot hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.mmBot.hero.title.accent',
                message: 'a bot does it.',
                description: 'Market making bot hero title accent',
              })}
            </span>
          ),
        }}>
        {'Quote both sides of the book — {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.mmBot.hero.subtitle',
      message:
        'A market-making bot is software that keeps a buy order and a sell order live around the current price at all times. It re-prices them as the market moves and replaces them the moment one fills — work no human can do by hand for long. OctoBot is that software, open source and running on your own account.',
      description: 'Market making bot hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.mmBot.hero.action.talk',
          message: 'Talk to our team',
          description: 'Market making bot hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.mmBot.hero.action.feature',
          message: 'See market making on OctoBot',
          description: 'Market making bot hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.mmBot.visual.label',
          message: 'Live quotes',
          description: 'Market making bot visual label',
        })}
        note="BTC/USDT · auto-requoted"
        asks={[
          {price: '64,180', size: '0.12', depth: 50},
          {price: '64,140', size: '0.18', depth: 72},
          {price: '64,110', size: '0.20', depth: 88},
        ]}
        mid="64,090"
        bids={[
          {price: '64,070', size: '0.20', depth: 88},
          {price: '64,040', size: '0.18', depth: 72},
          {price: '64,000', size: '0.12', depth: 50},
        ]}
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.mmBot.what.eyebrow',
        message: 'What it is',
        description: 'Market making bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmBot.what.title',
        message: 'A market-making bot, in plain terms',
        description: 'Market making bot section title',
      }),
      body: translate({
        id: 'pages.ideas.mmBot.what.body',
        message:
          'A market-making bot posts a price it will buy at and a price it will sell at, slightly apart from each other. The gap between them is the spread, and that spread is the income: whenever someone trades against the buy quote and someone else trades against the sell quote, the bot has bought low and sold high. Doing this profitably means keeping both quotes live, accurate and balanced second after second — which is exactly the kind of repetitive, never-sleep job software exists for.',
        description: 'Market making bot callout body',
      }),
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.mmBot.handles.eyebrow',
        message: 'What the bot handles',
        description: 'Market making bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmBot.handles.title',
        message: 'The work the bot takes off your hands',
        description: 'Market making bot section title',
      }),
      columns: 2,
      items: [
        {
          icon: '↕️',
          title: translate({
            id: 'pages.ideas.mmBot.handles.quoting.title',
            message: 'Two-sided quoting',
            description: 'Market making bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.handles.quoting.description',
            message:
              'It always keeps a bid and an ask in the book, so the market can trade against you in either direction.',
            description: 'Market making bot feature description',
          }),
        },
        {
          icon: '📐',
          title: translate({
            id: 'pages.ideas.mmBot.handles.spread.title',
            message: 'Spread management',
            description: 'Market making bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.handles.spread.description',
            message:
              'You set how far apart the quotes sit; the bot holds that distance as the reference price drifts.',
            description: 'Market making bot feature description',
          }),
        },
        {
          icon: '⚖️',
          title: translate({
            id: 'pages.ideas.mmBot.handles.inventory.title',
            message: 'Inventory and risk limits',
            description: 'Market making bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.handles.inventory.description',
            message:
              'Caps on how much of each asset it will hold keep the bot from drifting into a one-sided position you never wanted.',
            description: 'Market making bot feature description',
          }),
        },
        {
          icon: '🔄',
          title: translate({
            id: 'pages.ideas.mmBot.handles.requote.title',
            message: 'Re-quoting on fills',
            description: 'Market making bot feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.handles.requote.description',
            message:
              'The instant a quote is hit, the bot cancels the stale side and posts fresh orders around the new price.',
            description: 'Market making bot feature description',
          }),
        },
      ],
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.mmBot.run.eyebrow',
        message: 'Running it',
        description: 'Market making bot section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmBot.run.title',
        message: 'From download to live quotes',
        description: 'Market making bot section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.mmBot.run.configure.title',
            message: 'Configure the bot',
            description: 'Market making bot step title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.run.configure.description',
            message:
              'Choose the pair, the spread you want to quote, and the inventory limits the bot must respect.',
            description: 'Market making bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.mmBot.run.connect.title',
            message: 'Connect a venue',
            description: 'Market making bot step title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.run.connect.description',
            message:
              'Add a trade-only API key for your exchange. The bot places orders on your account and never holds your funds.',
            description: 'Market making bot step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.mmBot.run.start.title',
            message: 'Run it',
            description: 'Market making bot step title',
          }),
          description: translate({
            id: 'pages.ideas.mmBot.run.start.description',
            message:
              'The bot posts its first pair of quotes and keeps them maintained around the clock — pause or re-tune whenever you want.',
            description: 'Market making bot step description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.mmBot.faq.title',
        message: 'Market making bot questions',
        description: 'Market making bot FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.mmBot.faq.q1',
            message: 'Do I need to write code to run the bot?',
            description: 'Market making bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmBot.faq.a1',
            message:
              'No. The market-making bot is configured through settings — pair, spread, inventory limits — not by editing source. It is open source, so the code is there to read and extend if you want to, but running it does not require that.',
            description: 'Market making bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.mmBot.faq.q2',
            message: 'Where does the bot keep my funds?',
            description: 'Market making bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmBot.faq.a2',
            message:
              'On your own exchange account. The bot connects through an API key and only places and cancels orders — it never takes custody of your balance.',
            description: 'Market making bot FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.mmBot.faq.q3',
            message: 'What happens when the price moves sharply?',
            description: 'Market making bot FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmBot.faq.a3',
            message:
              'The bot re-quotes around the new reference price and respects the inventory limits you set, so a fast move does not leave stale orders sitting in the book or push your position past its cap.',
            description: 'Market making bot FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.mmBot.cta.title',
      message: 'Put a market-making bot on your book',
      description: 'Market making bot CTA title',
    }),
    description: translate({
      id: 'pages.ideas.mmBot.cta.description',
      message:
        'Tell us about the pair and venue you want to quote, and we will walk you through setting the bot up.',
      description: 'Market making bot CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.mmBot.cta.action.book',
          message: 'Book a call',
          description: 'Market making bot CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.mmBot.cta.action.cex',
          message: 'How CEX market making works',
          description: 'Market making bot CTA action label',
        }),
        to: '/features/ideas/cex-market-making',
        variant: 'ghost',
      },
    ],
  },
};

export default function MarketMakingBotPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
