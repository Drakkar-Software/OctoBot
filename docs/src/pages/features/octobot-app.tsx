import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  StatStrip,
  PricingStrip,
  Testimonials,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type Stat,
  type PriceCell,
  type Testimonial,
  type FAQItem,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';

/*
 * OctoBot App product feature page — route: /features/octobot-app.
 *
 * Migrated from the OctoBot consumer-investing marketing site into the
 * Neo Glass Dark landing toolkit. Built the same way as src/pages/welcome.tsx:
 * a navbar-less LandingLayout composed entirely from reusable components.
 */

const CLOUD_URL = 'https://www.octobot.cloud';

const FEATURES: Feature[] = [
  {
    icon: '🧠',
    title: 'AI trading strategies',
    description:
      'Let AI models analyze the market and manage your funds — no ChatGPT subscription, paper-trade first.',
    to: '/guides/octobot-trading-modes/chatgpt-trading',
  },
  {
    icon: '🧺',
    title: 'Crypto baskets',
    description:
      'Theme-based portfolios that diversify your investments and auto-rebalance as the market moves.',
    to: '/guides/octobot-usage/strategy-designer',
  },
  {
    icon: '📈',
    title: 'TradingView automation',
    description:
      'Automate any TradingView strategy, or generate a Pine Script strategy from a plain-language prompt.',
    to: '/guides/octobot-interfaces/tradingview',
  },
  {
    icon: '🔒',
    title: 'Self-custody first',
    description:
      'Your API keys and wallets never leave your device. You stay in control, always.',
    to: '/blog/how-to-use-a-self-custody-crypto-trading-bot',
  },
  {
    icon: '🧪',
    title: 'Paper trading',
    description:
      'Try any basket or strategy with virtual money before risking a single real coin.',
    to: '/guides/octobot-usage/simulator',
  },
  {
    icon: '🧩',
    title: 'Open source',
    description:
      'MIT-licensed and community-driven since 2018. Read, audit and shape the code yourself.',
    to: 'https://github.com/Drakkar-Software/OctoBot',
  },
];

const STEPS: Step[] = [
  {
    icon: '⚡',
    title: 'Pick your strategy',
    description:
      'Choose a ready-made investment strategy or crypto basket — or design your own.',
  },
  {
    icon: '🔗',
    title: 'Select your exchange',
    description:
      'Connect one of the leading exchanges OctoBot partners with in a couple of clicks.',
  },
  {
    icon: '📊',
    title: 'Follow your gains',
    description:
      'Watch performance from any browser or your phone while OctoBot runs on autopilot.',
  },
];

const STATS: Stat[] = [
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: 'OctoBots running worldwide',
    sub: 'self-hosted · global',
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: 'Trades executed',
    sub: 'cumulative to date',
  },
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: 'GitHub stars',
    sub: 'since 2018 · organic',
  },
];

const PRICING: PriceCell[] = [
  {
    tag: 'Investor',
    price: '€0',
    label: 'Free forever',
    note: 'Run automated strategies at no cost. Unlock extra features through missions.',
  },
  {
    tag: 'Investor Plus',
    price: '14d',
    priceSuffix: ' free',
    label: 'The full experience',
    note: 'Advanced strategies, more simultaneous bots, portfolio fine-tuning and AI.',
    variant: 'feat',
  },
  {
    tag: 'Pro',
    price: 'Pro',
    label: 'For power users',
    note: 'Everything in Plus, futures trading, personalized arbitrage and priority support.',
  },
];

const FEATURED_TESTIMONIAL: Testimonial = {
  quote:
    "I've been using OctoBot with these settings for a while now, tweaking them. Over the past year I'm at an overall profit of about 1000% (3K → 30K). Insane.",
  name: 'OctoBot user',
  role: 'Community member since 2022',
  avatar: 'linear-gradient(135deg, #65e7cf, #4893f1)',
};

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      'I have been using OctoBot for a couple of years now and it has been an incredible journey. The fact that it is open source means the possibilities are endless.',
    name: 'Tim Hermans',
    role: 'Community member since 2021',
    avatar: 'linear-gradient(135deg, #85d6d7, #6cb596)',
  },
  {
    quote:
      'OctoBot is an exceptional open-source crypto trading bot. It seamlessly integrates with exchanges and is a valuable asset to the crypto ecosystem.',
    name: 'Adrian Pollard',
    role: 'Co-founder of HollaEx',
    avatar: 'linear-gradient(135deg, #9b85d7, #4893f1)',
  },
  {
    quote:
      'I wanted something and the devs brought it within a few weeks. I like devs who are active and working on community ideas.',
    name: 'OctoBot user',
    role: 'Senior community member',
    avatar: 'linear-gradient(135deg, #f0c53b, #e8a44e)',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What can I do with the OctoBot App?',
    answer:
      'Track every account in one place and automate investment strategies — AI, crypto baskets, DCA, grid and TradingView — on the exchanges you already use.',
  },
  {
    question: 'Is it really free?',
    answer:
      'Yes. The Investor plan is free forever and lets you run automated strategies at no cost. Paid plans add advanced features, more simultaneous bots and AI tooling.',
  },
  {
    question: 'Can I test strategies before risking real money?',
    answer:
      'Every basket and strategy can be run with virtual funds first through paper trading, so you can validate an idea before committing real capital.',
  },
  {
    question: 'Does OctoBot take a cut of my trades?',
    answer:
      'No. OctoBot only charges a subscription on paid plans — there is no per-trade fee and no hidden cost.',
  },
  {
    question: 'Is OctoBot open source?',
    answer: (
      <>
        Yes — the code is on{' '}
        <a href="https://github.com/Drakkar-Software/OctoBot">GitHub</a>. You
        can read it, audit it and contribute to it.
      </>
    ),
  },
];

export default function OctoBotAppFeature(): ReactNode {
  return (
    <LandingLayout
      title="OctoBot App — Automated crypto investing"
      description="OctoBot App puts crypto investment on autopilot — AI strategies, crypto baskets, TradingView automation and paper trading, open source and self-custody.">
      <Hero
        eyebrow="OctoBot App"
        title={
          <>
            Crypto investment,{' '}
            <span className="ng-text-gradient">now on autopilot.</span>
          </>
        }
        subtitle="Easily invest your crypto with OctoBot — automated strategies you fully control, from your browser or your phone."
        actions={[
          {label: 'Invest for free', to: CLOUD_URL},
          {label: 'Read the guides', to: '/guides/octobot', variant: 'ghost'},
        ]}
        meta={[
          {label: '50K installs', dot: true},
          {label: 'Open source · since 2018'},
          {label: 'Paper trading included'},
        ]}
      />

      <Section
        eyebrow="Why OctoBot"
        title="Everything you need to invest on autopilot"
        lead="A complete toolkit for building, testing and running automated strategies — without giving up custody.">
        <FeatureGrid features={FEATURES} columns={3} />
      </Section>

      <Section
        eyebrow="Getting started"
        title="How to start your OctoBot"
        lead="Our goal is to make crypto investment easy to access — we keep it as simple as possible.">
        <StepList steps={STEPS} />
      </Section>

      <Section
        align="left"
        eyebrow="Risk-free first"
        title={
          <>
            Try it with{' '}
            <span className="ng-text-frost">virtual money.</span>
          </>
        }
        lead="Try any crypto basket or investment strategy with simulated funds before investing a single real coin.">
        <GlassCard variant="strong" padded>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1.5rem',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
            <div>
              <div
                style={{
                  fontFamily: 'var(--ng-font-mono)',
                  fontSize: '0.8rem',
                  color: 'var(--ng-ink-faint)',
                  letterSpacing: '0.12em',
                }}>
                EXAMPLE · $2,000 AFTER ONE MONTH
              </div>
              <div
                style={{
                  fontSize: '1.4rem',
                  color: 'var(--ng-ink)',
                  fontWeight: 600,
                  marginTop: '0.5rem',
                }}>
                If the strategy made{' '}
                <span style={{color: 'var(--ng-pos)'}}>+15%</span> — you could
                have earned{' '}
                <span
                  style={{
                    fontFamily: 'var(--ng-font-mono)',
                    color: 'var(--ng-pos)',
                  }}>
                  +$300
                </span>
              </div>
            </div>
            <span className="ng-btn ng-btn--surface" style={{cursor: 'default'}}>
              Switch real ⇄ virtual
            </span>
          </div>
        </GlassCard>
      </Section>

      <Section>
        <StatStrip
          head={{
            eyebrow: 'Community',
            title: 'Trusted by investors worldwide',
          }}
          stats={STATS}
        />
      </Section>

      <Section
        align="left"
        eyebrow="What the community says"
        title="A word from the community">
        <Testimonials featured={FEATURED_TESTIMONIAL} items={TESTIMONIALS} />
      </Section>

      <Section
        id="pricing"
        align="left"
        eyebrow="Pricing"
        title="Choose a plan that fits your needs"
        lead="OctoBot Cloud offers a plan for every type of investor — start free and upgrade only when you need more.">
        <PricingStrip cells={PRICING} />
      </Section>

      <Section eyebrow="FAQ" title="Frequently asked questions">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Start automating in minutes"
        description="Create your OctoBot for free, or dive into the guides to design your own strategy."
        actions={[
          {label: 'Invest for free', to: CLOUD_URL},
          {label: 'Browse the guides', to: '/guides/octobot', variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
