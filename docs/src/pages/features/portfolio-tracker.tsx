import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StatStrip,
  BeforeAfter,
  IconList,
  LogoRibbon,
  FAQ,
  CTABand,
  type Feature,
  type Stat,
  type IconListItem,
  type FAQItem,
} from '@site/src/components/landing';
import styles from './_styles.module.css';

/*
 * Crypto Portfolio Tracker feature page — route: /features/portfolio-tracker.
 *
 * SEO landing page targeting the "crypto portfolio tracker" cluster:
 * multi-exchange / automated / open-source / real-time PnL. Built the same
 * way as the other src/pages/features/*.tsx pages — a navbar-less
 * LandingLayout composed entirely from the Neo Glass Dark landing toolkit.
 */

const CLOUD = 'https://www.octobot.cloud';
const GITHUB = 'https://github.com/Drakkar-Software/OctoBot';

const TRACKS: Feature[] = [
  {
    icon: '📊',
    title: 'Live portfolio value',
    description:
      'See the total value of every holding across all your connected exchanges, refreshed in real time.',
  },
  {
    icon: '📈',
    title: 'Real-time PnL',
    description:
      'Track profit and loss as it happens — per asset, per strategy and for the whole portfolio.',
  },
  {
    icon: '🧾',
    title: 'Profit history',
    description:
      'A full historical record of your portfolio value and realized profits, charted over time.',
  },
  {
    icon: '🪙',
    title: 'Holdings breakdown',
    description:
      'Every coin you hold, its share of the portfolio and where it sits — no manual spreadsheet.',
  },
  {
    icon: '🔀',
    title: 'Multi-exchange aggregation',
    description:
      'Connect several exchange accounts and watch them as one consolidated portfolio.',
  },
  {
    icon: '🤖',
    title: 'Tied to your strategies',
    description:
      'Because OctoBot also trades, every move is attributed — you see what each strategy did to your balance.',
  },
];

const STATS: Stat[] = [
  {value: '15+', label: 'Exchanges you can connect'},
  {value: 'Real-time', label: 'Portfolio & PnL refresh'},
  {value: '100%', label: 'Open source — audit every line'},
  {value: 'Your keys', label: 'API keys never leave your control'},
];

const WHY: IconListItem[] = [
  {
    icon: '🔑',
    text: (
      <>
        <strong>Self-custody:</strong> you connect read-and-trade API keys you
        own — OctoBot never holds your funds.
      </>
    ),
  },
  {
    icon: '🧩',
    text: (
      <>
        <strong>Open source:</strong> the tracker is part of OctoBot — the whole
        codebase is public on <a href={GITHUB}>GitHub</a>.
      </>
    ),
  },
  {
    icon: '⚡',
    text: (
      <>
        <strong>Automated:</strong> it is not a passive viewer — the same bot
        that tracks your portfolio can also act on it.
      </>
    ),
  },
  {
    icon: '🖥️',
    text: (
      <>
        <strong>Self-hosted or cloud:</strong> run it on your own machine or use
        OctoBot Cloud — the portfolio data stays yours either way.
      </>
    ),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is a crypto portfolio tracker?',
    answer:
      'A crypto portfolio tracker aggregates the assets you hold across exchanges and wallets into a single view, showing total value, allocation and profit or loss over time. OctoBot does this automatically from the exchange accounts you connect.',
  },
  {
    question: 'Is the OctoBot portfolio tracker free?',
    answer: (
      <>
        Yes — OctoBot is free and open source. You can download it from{' '}
        <a href={GITHUB}>GitHub</a> and track your portfolio at no cost, or use
        OctoBot Cloud for a hosted experience.
      </>
    ),
  },
  {
    question: 'Can it track multiple exchanges at once?',
    answer:
      'Yes. Connect several exchange accounts and OctoBot consolidates them into one portfolio view, so you see your total holdings and PnL without switching between exchange apps.',
  },
  {
    question: 'Does it have access to my funds?',
    answer:
      'No. OctoBot connects with the API keys you create on your own exchange account. Your funds and keys stay under your control — OctoBot is self-custody by design.',
  },
  {
    question: 'How is this different from a regular portfolio tracker app?',
    answer:
      'Most trackers only show numbers. OctoBot is a trading bot first, so the portfolio it tracks is the portfolio it can also manage — every change in value is tied to a strategy you can inspect, backtest and adjust.',
  },
  {
    question: 'Which exchanges are supported?',
    answer: (
      <>
        OctoBot connects to 15+ major exchanges including Binance, Kucoin,
        Coinbase, MEXC and more. See the full list on the{' '}
        <Link to="/supported-exchanges">supported exchanges page</Link>.
      </>
    ),
  },
];

export default function PortfolioTrackerFeature(): ReactNode {
  return (
    <LandingLayout
      title="Crypto Portfolio Tracker — open source & multi-exchange"
      description="Track your crypto portfolio across every exchange in real time with OctoBot — an open-source, self-custody portfolio tracker tied to automated trading.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Portfolio tracker"
        title={
          <>
            Your whole crypto portfolio,{' '}
            <span className="ng-text-gradient">tracked in real time.</span>
          </>
        }
        subtitle="OctoBot aggregates every exchange account you connect into one live portfolio — value, holdings and PnL, automatically and open source."
        actions={[
          {label: 'Start tracking', to: CLOUD},
          {label: 'Get it on GitHub', to: GITHUB, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Multi-exchange', dot: true},
          {label: 'Real-time PnL'},
          {label: 'Open source'},
        ]}
      />

      <Section
        eyebrow="What it tracks"
        title="Everything you hold, in one view"
        lead="OctoBot reads your connected exchange accounts and turns them into a single, always-current portfolio.">
        <FeatureGrid features={TRACKS} columns={3} />
      </Section>

      <Section eyebrow="At a glance">
        <StatStrip
          head={{
            eyebrow: 'Why OctoBot',
            title: 'A tracker that does more than watch',
          }}
          stats={STATS}
        />
      </Section>

      <Section
        align="left"
        eyebrow="Why it's different"
        title="Not just a dashboard — a tracker you control"
        lead="Most portfolio trackers ask for your keys and show you a number. OctoBot is open source, self-custody, and built around the strategies that move your balance.">
        <IconList items={WHY} />
      </Section>

      <Section
        align="right"
        eyebrow="The difference"
        title={
          <>
            A spreadsheet of balances vs.{' '}
            <span className="ng-text-frost">a portfolio that works for you.</span>
          </>
        }>
        <BeforeAfter
          before={{
            label: 'Typical tracker app',
            items: [
              <>
                <strong>Manual or read-only</strong> — you watch, nothing acts
              </>,
              <>
                Your <strong>API keys live on someone&apos;s server</strong>
              </>,
              <>
                A <strong>closed black box</strong> — trust it or don&apos;t
              </>,
            ],
          }}
          after={{
            label: 'With OctoBot',
            items: [
              <>
                <strong>Tracks and trades</strong> — strategies act on the
                portfolio
              </>,
              <>
                <strong>Self-custody</strong> — your keys, your machine or cloud
              </>,
              <>
                <strong>Open source</strong> — every line is auditable
              </>,
            ],
          }}
        />
      </Section>

      <Section
        eyebrow="Exchanges"
        title={
          <>
            Track your assets on the{' '}
            <span className="ng-text-frost">exchanges you already use.</span>
          </>
        }>
        <LogoRibbon
          items={[
            'BINANCE',
            'KUCOIN',
            'COINBASE',
            'MEXC',
            'BITGET',
            'HTX',
            'CRYPTO.COM',
            'OKX',
            '+ MORE',
          ]}
        />
      </Section>

      <Section eyebrow="FAQ" title="Crypto portfolio tracker FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Stop checking five exchange apps."
        description="Connect your accounts to OctoBot and watch your whole crypto portfolio in one place — free and open source."
        actions={[
          {label: 'Start tracking', to: CLOUD},
          {label: 'Read the guides', to: '/guides/octobot', variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
