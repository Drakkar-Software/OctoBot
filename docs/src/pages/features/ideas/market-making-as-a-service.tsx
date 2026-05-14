import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/market-making-as-a-service
 * Angle: market-making-as-a-service — professional liquidity delivered as a managed service, not a desk you build.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.mmaas.meta.title',
      message: 'Market Making as a Service — Managed crypto liquidity',
      description: 'MMaaS page meta title',
    }),
    description: translate({
      id: 'pages.ideas.mmaas.meta.description',
      message:
        'Market-making-as-a-service for crypto projects and exchanges — OctoBot quotes both sides of your order book continuously, with institutional-grade spreads and risk controls, and never takes custody of funds.',
      description: 'MMaaS page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.mmaas.hero.eyebrow',
      message: 'For projects & exchanges · Managed liquidity',
      description: 'MMaaS hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.mmaas.hero.title"
        description="MMaaS hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.mmaas.hero.title.accent',
                message: 'not a desk you build.',
                description: 'MMaaS hero title accent',
              })}
            </span>
          ),
        }}>
        {'Market making as a service — {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.mmaas.hero.subtitle',
      message:
        'Standing up an in-house market-making desk means hiring quants, writing quoting infrastructure and babysitting it around the clock. Market-making-as-a-service hands you the outcome instead: a healthy, two-sided order book on your listing venues, run by software that quotes continuously against your own exchange accounts.',
      description: 'MMaaS hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.mmaas.hero.action.contact',
          message: 'Talk to our team',
          description: 'MMaaS hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.mmaas.hero.action.feature',
          message: 'See OctoBot Market Making',
          description: 'MMaaS hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.mmaas.visual.label',
          message: 'Live order book',
          description: 'MMaaS visual label',
        })}
        note="Both sides · continuous"
        asks={[
          {price: '1.0042', size: '8,200', depth: 70},
          {price: '1.0028', size: '6,400', depth: 55},
          {price: '1.0014', size: '4,100', depth: 38},
        ]}
        bids={[
          {price: '0.9986', size: '4,300', depth: 40},
          {price: '0.9972', size: '6,600', depth: 58},
          {price: '0.9958', size: '8,500', depth: 72},
        ]}
        mid="1.0000"
      />
    ),
  },
  sections: [
    {
      kind: 'callout',
      eyebrow: translate({
        id: 'pages.ideas.mmaas.what.eyebrow',
        message: 'What it means',
        description: 'MMaaS section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmaas.what.title',
        message: 'Liquidity, delivered as a service — and who needs it',
        description: 'MMaaS section title',
      }),
      body: translate({
        id: 'pages.ideas.mmaas.what.body',
        message:
          'A token with no resting orders looks broken: wide spreads, gaps in the book, prices that lurch on small trades. Market making is the work of constantly posting bids and asks so buyers and sellers can transact at a fair price. Delivered as a service, that work becomes a configuration rather than a build — the people who need it are token projects defending a healthy listing, and exchanges that want depth on their newer pairs without running a desk per market.',
        description: 'MMaaS callout body',
      }),
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.mmaas.how.eyebrow',
        message: 'How it works',
        description: 'MMaaS section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmaas.how.title',
        message: 'From a thin book to continuous quotes',
        description: 'MMaaS section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.mmaas.how.connect.title',
            message: 'Connect the venue',
            description: 'MMaaS step title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.how.connect.description',
            message:
              'Add API keys for the centralized exchange where your pair is listed. Funds stay in your own exchange account — OctoBot quotes against them but never takes custody.',
            description: 'MMaaS step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.mmaas.how.set.title',
            message: 'Set budget, spread and risk limits',
            description: 'MMaaS step title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.how.set.description',
            message:
              'Decide how much inventory to commit, how tight to quote, and the boundaries the bot must respect — maximum exposure, price bands and stop conditions.',
            description: 'MMaaS step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.mmaas.how.quote.title',
            message: 'The bot quotes both sides continuously',
            description: 'MMaaS step title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.how.quote.description',
            message:
              'OctoBot keeps bids and asks posted around the reference price, refreshing them as the market moves so the book stays two-sided through the day and night.',
            description: 'MMaaS step description',
          }),
        },
      ],
    },
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.mmaas.grade.eyebrow',
        message: 'Institutional-grade',
        description: 'MMaaS section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.mmaas.grade.title',
        message: 'What a managed service is held to',
        description: 'MMaaS section title',
      }),
      columns: 2,
      items: [
        {
          icon: '📐',
          title: translate({
            id: 'pages.ideas.mmaas.grade.spread.title',
            message: 'Tight, defensible spreads',
            description: 'MMaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.grade.spread.description',
            message:
              'Quotes sit close to the reference price instead of leaving a wide no-trade gap, so the pair reads as a real, tradable market.',
            description: 'MMaaS feature description',
          }),
        },
        {
          icon: '📊',
          title: translate({
            id: 'pages.ideas.mmaas.grade.depth.title',
            message: 'Depth on both sides',
            description: 'MMaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.grade.depth.description',
            message:
              'Multiple order levels above and below the mid mean a normal-sized trade clears without knocking the price around.',
            description: 'MMaaS feature description',
          }),
        },
        {
          icon: '🕒',
          title: translate({
            id: 'pages.ideas.mmaas.grade.uptime.title',
            message: 'Around-the-clock uptime',
            description: 'MMaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.grade.uptime.description',
            message:
              'Crypto markets never close. The bot keeps quoting through weekends and overnight, when a thin book is most visible.',
            description: 'MMaaS feature description',
          }),
        },
        {
          icon: '🛡️',
          title: translate({
            id: 'pages.ideas.mmaas.grade.risk.title',
            message: 'Risk controls that hold',
            description: 'MMaaS feature title',
          }),
          description: translate({
            id: 'pages.ideas.mmaas.grade.risk.description',
            message:
              'Inventory caps, price bands and stop conditions are enforced by the bot, so a fast move pulls quotes instead of draining the budget.',
            description: 'MMaaS feature description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.mmaas.faq.title',
        message: 'Market-making-as-a-service questions',
        description: 'MMaaS FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.mmaas.faq.q1',
            message: 'Do you take custody of our funds?',
            description: 'MMaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmaas.faq.a1',
            message:
              'No. OctoBot Market Making works on centralized order-book exchanges by connecting through your exchange API keys. The inventory stays in your own exchange account at all times — the bot only places and cancels orders.',
            description: 'MMaaS FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.mmaas.faq.q2',
            message: 'Which markets does it work on?',
            description: 'MMaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmaas.faq.a2',
            message:
              'Centralized exchanges with a standard order book. If your pair is listed on an exchange OctoBot can connect to via API, the service can quote it.',
            description: 'MMaaS FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.mmaas.faq.q3',
            message: 'How is this different from running the bot ourselves?',
            description: 'MMaaS FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.mmaas.faq.a3',
            message:
              'It is the same OctoBot Market Making engine — as a service, you get help sizing the budget, setting spreads and tuning risk limits for your pair, rather than working it out alone. You can also self-host and configure it yourself if you prefer.',
            description: 'MMaaS FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.mmaas.cta.title',
      message: 'Give your pair a real, two-sided market',
      description: 'MMaaS CTA title',
    }),
    description: translate({
      id: 'pages.ideas.mmaas.cta.description',
      message:
        'Tell us about your token or exchange and we will help you scope budget, spreads and risk limits for managed liquidity.',
      description: 'MMaaS CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.mmaas.cta.action.contact',
          message: 'Book a call',
          description: 'MMaaS CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.mmaas.cta.action.provider',
          message: 'Crypto liquidity provider',
          description: 'MMaaS CTA action label',
        }),
        to: '/features/ideas/crypto-liquidity-provider',
        variant: 'ghost',
      },
    ],
  },
};

export default function MarketMakingAsAServicePage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
