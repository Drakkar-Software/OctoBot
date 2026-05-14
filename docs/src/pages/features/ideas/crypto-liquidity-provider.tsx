import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {IdeaPage, LadderVisual, type IdeaPageData} from '@site/src/components/pages/ideas';

/*
 * SEO idea page — route: /features/ideas/crypto-liquidity-provider
 * Angle: acting as a crypto liquidity provider — continuously posting bids and asks, and what software-driven liquidity provision looks like.
 */

const DATA: IdeaPageData = {
  meta: {
    title: translate({
      id: 'pages.ideas.liquidityProvider.meta.title',
      message: 'Crypto Liquidity Provider — Software-driven market depth',
      description: 'Liquidity provider page meta title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityProvider.meta.description',
      message:
        'Become a crypto liquidity provider with OctoBot — continuously post bids and asks so a market has depth on both sides, run from your own exchange accounts with no custody handover.',
      description: 'Liquidity provider page meta description',
    }),
  },
  hero: {
    eyebrow: translate({
      id: 'pages.ideas.liquidityProvider.hero.eyebrow',
      message: 'For projects & exchanges · Liquidity provision',
      description: 'Liquidity provider hero eyebrow',
    }),
    title: (
      <Translate
        id="pages.ideas.liquidityProvider.hero.title"
        description="Liquidity provider hero title"
        values={{
          accent: (
            <span className="ng-text-gradient">
              {translate({
                id: 'pages.ideas.liquidityProvider.hero.title.accent',
                message: 'run by software.',
                description: 'Liquidity provider hero title accent',
              })}
            </span>
          ),
        }}>
        {'Be a crypto liquidity provider — {accent}'}
      </Translate>
    ),
    subtitle: translate({
      id: 'pages.ideas.liquidityProvider.hero.subtitle',
      message:
        'A liquidity provider is whoever keeps bids and asks resting in the order book so other people can actually trade. Doing it well means quoting both sides continuously and adjusting as the price moves — exactly the kind of repetitive, never-sleeping job software is built for.',
      description: 'Liquidity provider hero subtitle',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityProvider.hero.action.contact',
          message: 'Talk to our team',
          description: 'Liquidity provider hero action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityProvider.hero.action.feature',
          message: 'See OctoBot Market Making',
          description: 'Liquidity provider hero action label',
        }),
        to: '/features/market-making',
        variant: 'ghost',
      },
    ],
    visual: (
      <LadderVisual
        label={translate({
          id: 'pages.ideas.liquidityProvider.visual.label',
          message: 'Resting liquidity',
          description: 'Liquidity provider visual label',
        })}
        note="Bids & asks · always on"
        asks={[
          {price: '1.0039', size: '7,800', depth: 66},
          {price: '1.0026', size: '5,900', depth: 50},
          {price: '1.0013', size: '3,700', depth: 32},
        ]}
        bids={[
          {price: '0.9987', size: '3,900', depth: 34},
          {price: '0.9974', size: '6,100', depth: 52},
          {price: '0.9961', size: '7,900', depth: 68},
        ]}
        mid="1.0000"
      />
    ),
  },
  sections: [
    {
      kind: 'features',
      eyebrow: translate({
        id: 'pages.ideas.liquidityProvider.role.eyebrow',
        message: 'The role',
        description: 'Liquidity provider section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityProvider.role.title',
        message: 'What a liquidity provider actually does',
        description: 'Liquidity provider section title',
      }),
      columns: 2,
      items: [
        {
          icon: '📥',
          title: translate({
            id: 'pages.ideas.liquidityProvider.role.post.title',
            message: 'Posts resting orders',
            description: 'Liquidity provider feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.role.post.description',
            message:
              'Keeps limit orders sitting in the book on both the buy and sell side, so anyone arriving to trade finds a price waiting.',
            description: 'Liquidity provider feature description',
          }),
        },
        {
          icon: '↔️',
          title: translate({
            id: 'pages.ideas.liquidityProvider.role.spread.title',
            message: 'Holds the spread',
            description: 'Liquidity provider feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.role.spread.description',
            message:
              'Keeps the gap between the best bid and best ask narrow, which is what makes a market feel liquid rather than broken.',
            description: 'Liquidity provider feature description',
          }),
        },
        {
          icon: '🔄',
          title: translate({
            id: 'pages.ideas.liquidityProvider.role.refresh.title',
            message: 'Refreshes as price moves',
            description: 'Liquidity provider feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.role.refresh.description',
            message:
              'Cancels and re-places quotes around the new reference price so the book stays centered instead of drifting stale.',
            description: 'Liquidity provider feature description',
          }),
        },
        {
          icon: '⚖️',
          title: translate({
            id: 'pages.ideas.liquidityProvider.role.inventory.title',
            message: 'Manages inventory',
            description: 'Liquidity provider feature title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.role.inventory.description',
            message:
              'Watches how much of each asset it is holding and respects exposure limits, so one-sided flow does not run the budget down.',
            description: 'Liquidity provider feature description',
          }),
        },
      ],
    },
    {
      kind: 'stats',
      eyebrow: translate({
        id: 'pages.ideas.liquidityProvider.stats.eyebrow',
        message: 'Software-driven provision',
        description: 'Liquidity provider section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityProvider.stats.title',
        message: 'What it looks like when a bot does the work',
        description: 'Liquidity provider section title',
      }),
      items: [
        {
          value: '2-sided',
          label: translate({
            id: 'pages.ideas.liquidityProvider.stats.sides.label',
            message: 'Quoting',
            description: 'Liquidity provider stat label',
          }),
          sub: translate({
            id: 'pages.ideas.liquidityProvider.stats.sides.sub',
            message: 'Bids and asks posted together, not one at a time',
            description: 'Liquidity provider stat sub',
          }),
        },
        {
          value: '24/7',
          label: translate({
            id: 'pages.ideas.liquidityProvider.stats.uptime.label',
            message: 'Uptime',
            description: 'Liquidity provider stat label',
          }),
          sub: translate({
            id: 'pages.ideas.liquidityProvider.stats.uptime.sub',
            message: 'Crypto markets never close, so neither does the bot',
            description: 'Liquidity provider stat sub',
          }),
        },
        {
          value: 'Many',
          label: translate({
            id: 'pages.ideas.liquidityProvider.stats.venues.label',
            message: 'Exchanges supported',
            description: 'Liquidity provider stat label',
          }),
          sub: translate({
            id: 'pages.ideas.liquidityProvider.stats.venues.sub',
            message: 'Any centralized order-book exchange OctoBot can connect to',
            description: 'Liquidity provider stat sub',
          }),
        },
        {
          value: '0',
          label: translate({
            id: 'pages.ideas.liquidityProvider.stats.custody.label',
            message: 'Custody handover',
            description: 'Liquidity provider stat label',
          }),
          sub: translate({
            id: 'pages.ideas.liquidityProvider.stats.custody.sub',
            message: 'Funds stay in your own exchange account the whole time',
            description: 'Liquidity provider stat sub',
          }),
        },
      ],
    },
    {
      kind: 'steps',
      eyebrow: translate({
        id: 'pages.ideas.liquidityProvider.start.eyebrow',
        message: 'Getting started',
        description: 'Liquidity provider section eyebrow',
      }),
      title: translate({
        id: 'pages.ideas.liquidityProvider.start.title',
        message: 'Three steps to providing liquidity',
        description: 'Liquidity provider section title',
      }),
      items: [
        {
          title: translate({
            id: 'pages.ideas.liquidityProvider.start.connect.title',
            message: 'Connect your exchange account',
            description: 'Liquidity provider step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.start.connect.description',
            message:
              'Add API keys for the centralized exchange holding the pair you want to support. The bot trades through the keys; the assets never leave your account.',
            description: 'Liquidity provider step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.liquidityProvider.start.define.title',
            message: 'Define spread, depth and limits',
            description: 'Liquidity provider step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.start.define.description',
            message:
              'Choose how tight to quote, how many levels of depth to post on each side, and the exposure and price boundaries the bot must stay within.',
            description: 'Liquidity provider step description',
          }),
        },
        {
          title: translate({
            id: 'pages.ideas.liquidityProvider.start.run.title',
            message: 'Let it provide liquidity',
            description: 'Liquidity provider step title',
          }),
          description: translate({
            id: 'pages.ideas.liquidityProvider.start.run.description',
            message:
              'OctoBot keeps both sides of the book populated and refreshed, and you can adjust spread, depth or limits at any time.',
            description: 'Liquidity provider step description',
          }),
        },
      ],
    },
    {
      kind: 'faq',
      eyebrow: 'FAQ',
      title: translate({
        id: 'pages.ideas.liquidityProvider.faq.title',
        message: 'Crypto liquidity provider questions',
        description: 'Liquidity provider FAQ title',
      }),
      items: [
        {
          question: translate({
            id: 'pages.ideas.liquidityProvider.faq.q1',
            message: 'Do I need to be a professional firm to provide liquidity?',
            description: 'Liquidity provider FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityProvider.faq.a1',
            message:
              'No. Providing liquidity is a matter of keeping orders in the book — software handles the mechanics. Token projects and exchanges use it to keep their own pairs healthy without building a trading desk.',
            description: 'Liquidity provider FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityProvider.faq.q2',
            message: 'Does this work with decentralized exchanges?',
            description: 'Liquidity provider FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityProvider.faq.a2',
            message:
              'OctoBot Market Making works on centralized order-book exchanges. It connects via exchange API keys and posts limit orders into the book — it does not provide liquidity to automated market maker pools.',
            description: 'Liquidity provider FAQ answer',
          }),
        },
        {
          question: translate({
            id: 'pages.ideas.liquidityProvider.faq.q3',
            message: 'Who controls the funds?',
            description: 'Liquidity provider FAQ question',
          }),
          answer: translate({
            id: 'pages.ideas.liquidityProvider.faq.a3',
            message:
              'You do. The inventory stays in your own exchange account and OctoBot only places and cancels orders against it — there is no custody handover.',
            description: 'Liquidity provider FAQ answer',
          }),
        },
      ],
    },
  ],
  cta: {
    title: translate({
      id: 'pages.ideas.liquidityProvider.cta.title',
      message: 'Provide liquidity without building a desk',
      description: 'Liquidity provider CTA title',
    }),
    description: translate({
      id: 'pages.ideas.liquidityProvider.cta.description',
      message:
        'Tell us which pair you want to support and we will help you set spread, depth and risk limits for software-driven liquidity provision.',
      description: 'Liquidity provider CTA description',
    }),
    actions: [
      {
        label: translate({
          id: 'pages.ideas.liquidityProvider.cta.action.contact',
          message: 'Book a call',
          description: 'Liquidity provider CTA action label',
        }),
        to: 'mailto:contact@octobot.cloud',
      },
      {
        label: translate({
          id: 'pages.ideas.liquidityProvider.cta.action.mmaas',
          message: 'Market making as a service',
          description: 'Liquidity provider CTA action label',
        }),
        to: '/features/ideas/market-making-as-a-service',
        variant: 'ghost',
      },
    ],
  },
};

export default function CryptoLiquidityProviderPage(): ReactNode {
  return <IdeaPage data={DATA} />;
}
