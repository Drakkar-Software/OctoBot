import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  BeforeAfter,
  LogoRibbon,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type FAQItem,
} from '@site/src/components/landing';

/*
 * Market Making product feature page — route: /features/market-making.
 *
 * Migrated from the OctoBot Market Making marketing site into the Neo Glass
 * Dark landing toolkit. Built the same way as src/pages/welcome.tsx: a
 * navbar-less LandingLayout composed entirely from reusable components.
 */

const CALL_URL = 'https://cal.com/octobot.cloud/market-making-30min';
const CONTACT_MAIL = 'mailto:contact@octobot.cloud';

const STEPS: Step[] = [
  {
    icon: '🔍',
    title: "Analyze your market's liquidity",
    description:
      'Find the markets that need a liquidity boost using the Liquidity Score.',
  },
  {
    icon: '🎯',
    title: 'Configure your liquidity target',
    description:
      'Let the platform guide you to your target, or bring your own configuration.',
  },
  {
    icon: '📖',
    title: 'Preview your market making strategy',
    description:
      'View and adapt the order book your bot will maintain before it goes live.',
  },
];

const FEATURES: Feature[] = [
  {
    icon: '📊',
    title: 'Advanced order book management',
    description:
      'Maintain optimal liquidity depth with intelligent order placement and rebalancing algorithms.',
  },
  {
    icon: '🛡️',
    title: 'Risk management system',
    description:
      'Set volatility limits and dedicated budgets to protect your capital.',
  },
  {
    icon: '🧩',
    title: 'Open-source engine',
    description:
      'Always be in control. OctoBot Market Making is open source — no black box.',
  },
  {
    icon: '🔗',
    title: 'Multi-exchange integration',
    description:
      'Connect to more than 15 major exchanges through a single platform.',
  },
  {
    icon: '🔄',
    title: 'Automated rebalancing',
    description:
      'Keep your inventory optimally positioned across markets and exchanges with smart rebalancing.',
  },
  {
    icon: '⚙️',
    title: 'Customizable strategies',
    description:
      'Fine-tune the market making algorithm parameters to meet your goals.',
  },
];

const EXCHANGES = [
  'BINANCE',
  'KUCOIN',
  'MEXC',
  'COINEX',
  'COINBASE',
  'CRYPTO.COM',
  'HTX',
  'BITMART',
  'ASCENDEX',
  'BITGET',
  'HOLLAEX',
  '+ MORE',
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is a market maker in crypto?',
    answer:
      'A market maker in crypto is a person or organization that provides liquidity to crypto markets by creating buy and sell orders simultaneously on the order books. It helps reduce spreads, increases trading volume, and improves market efficiency by ensuring there are always orders available for traders to buy from and sell to.',
  },
  {
    question: 'What exchanges are supported by OctoBot Market Making?',
    answer:
      'OctoBot Market Making supports most popular centralized exchanges including Binance, Kucoin, MEXC, CoinEx, Coinbase, Crypto.com, HTX, BitMart, Ascendex, Bitget, all HollaEx-powered exchanges and more.',
  },
  {
    question: 'How much capital is required for effective market making?',
    answer:
      "Capital requirements depend on the asset's typical trading volume and desired market impact. In general, effective market making requires enough capital to contain at least 2% of the exchange's daily trading volume within the top of the order book. The OctoBot Market Making team can provide specific recommendations based on your token's trading profile.",
  },
  {
    question: 'What is a market making strategy?',
    answer:
      'A market making strategy is the process of providing liquidity to trading markets by simultaneously placing limit buy and sell orders to populate the order book and facilitate the execution of trades on that market.',
  },
  {
    question: 'How to become a market maker in crypto?',
    answer:
      'To become a crypto market maker you need an automated market making strategy and initial capital to deploy with it. OctoBot Market Making is a platform to simply automate a market making strategy and can help you get started with minimum capital requirements.',
  },
  {
    question: 'How do crypto market makers make money?',
    answer:
      'Crypto market makers make money by extracting profit from the trades they facilitate, similar to an advanced and large-scale grid trading strategy.',
  },
  {
    question: 'What are the risks of market making?',
    answer:
      'The main risk of a market maker is holding an asset that may decline in value. As a market facilitator, a market maker mostly buys when others are selling, and might therefore hold large amounts of an asset if its price declines dramatically.',
  },
  {
    question: 'Can anyone be a market maker?',
    answer:
      'Yes — a market maker can be an individual or an organization, as long as they are legally allowed to be market participants of the market they want to make.',
  },
  {
    question: 'What does OctoBot Market Making do?',
    answer:
      'OctoBot Market Making makes automated market making strategies accessible by offering a self-service platform to create, configure, monitor and improve market making strategies on most centralized cryptocurrency exchanges.',
  },
  {
    question: 'Is OctoBot open source?',
    answer: (
      <>
        Yes — the code is on{' '}
        <a href="https://github.com/Drakkar-Software/OctoBot">GitHub</a>. OctoBot
        Market Making is based on the market making distribution of OctoBot to
        execute its strategies.
      </>
    ),
  },
];

export default function MarketMakingFeature(): ReactNode {
  return (
    <LandingLayout
      title="OctoBot Market Making — Liquidity as a service"
      description="OctoBot Market Making is a professional, open-source market making as a service platform for crypto projects, exchanges and liquidity miners.">
      <Hero
        eyebrow="Market Making"
        title={
          <>
            Market making as a service for{' '}
            <span className="ng-text-gradient">crypto projects.</span>
          </>
        }
        subtitle="Boost your market's liquidity with OctoBot Market Making — a professional crypto market making as a service platform."
        actions={[
          {label: 'Boost my liquidity', to: CALL_URL},
          {label: 'Book a free call', to: CALL_URL, variant: 'ghost'},
        ]}
        meta={[
          {label: '15+ exchanges supported', dot: true},
          {label: 'Open source engine'},
          {label: 'Self-service platform'},
        ]}
      />

      <Section
        eyebrow="How it works"
        title="Improve your liquidity in 3 simple steps"
        lead="From spotting a thin market to maintaining a healthy order book — guided the whole way.">
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow="The platform"
        title="Institutional-grade market making"
        lead="Professional crypto market making software, available as a self-service platform.">
        <FeatureGrid features={FEATURES} columns={3} />
      </Section>

      <Section
        align="left"
        eyebrow="Why it matters"
        title={
          <>
            The cost of poor liquidity vs.{' '}
            <span className="ng-text-frost">a market that works.</span>
          </>
        }>
        <BeforeAfter
          before={{
            label: 'Poor liquidity',
            items: [
              <>
                <strong>Delisting risk</strong> on popular exchanges
              </>,
              <>
                Thin order books, <strong>wide spreads</strong>
              </>,
              <>
                An <strong>unattractive market</strong> for traders
              </>,
            ],
          }}
          after={{
            label: 'With OctoBot Market Making',
            items: [
              <>
                <strong>Deeper order books</strong> attract investors
              </>,
              <>
                <strong>Tighter spreads</strong>, healthier markets
              </>,
              <>
                Measure &amp; <strong>improve liquidity</strong> any time
              </>,
            ],
          }}
        />
      </Section>

      <Section
        align="right"
        eyebrow="Distribution"
        title={
          <>
            Supported on the{' '}
            <span className="ng-text-frost">exchanges that matter.</span>
          </>
        }>
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <Section eyebrow="FAQ" title="Frequently asked questions">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Ready to optimize your market's liquidity?"
        description="Schedule a call with our team to discuss your specific needs — or email us any question."
        actions={[
          {label: 'Book a free call', to: CALL_URL},
          {label: 'Email us', to: CONTACT_MAIL, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
