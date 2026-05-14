import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  LogoRibbon,
  StatStrip,
  IconList,
  CTABand,
  type Feature,
  type Stat,
  type IconListItem,
} from '@site/src/components/landing';
import WhyTabs from '@site/src/components/pages/trading-bot/WhyTabs';
import styles from './trading-bot.module.css';

/*
 * Trading bot marketing page — route: /trading-bot.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit: a navbar-less LandingLayout composed from reusable
 * landing components plus the page-local WhyTabs switcher.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDE = '/guides/octobot';
const REPO = 'https://github.com/Drakkar-Software/OctoBot';

const EXCHANGES: ReactNode[] = [
  'BINANCE',
  'COINBASE',
  'KRAKEN',
  'KUCOIN',
  'BYBIT',
  'OKX',
  'BITGET',
  'GATE.IO',
  'HTX',
  'MEXC',
  '+ MORE',
];

const STRATEGIES: Feature[] = [
  {
    icon: '📊',
    title: 'Technical & AI indicators',
    description:
      'Use technical indicators such as RSI, MACD, moving averages or ADX to configure your strategies, and integrate ChatGPT or custom AI predictions.',
  },
  {
    icon: '💵',
    title: 'Smart DCA trading',
    description:
      'Highly optimized Dollar Cost Averaging — automate entries and exits with as many orders as you want, for long or short-term DCA.',
  },
  {
    icon: '🔲',
    title: 'Advanced grid trading',
    description:
      'Profit from sideways markets with fine-tuned grid strategies on any pair and exchange.',
  },
  {
    icon: '📈',
    title: 'TradingView strategies',
    description:
      'Automate your TradingView strategies or indicator signals on any exchange — create or cancel orders the moment an alert fires.',
  },
];

const STATS: Stat[] = [
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: 'OctoBots running',
    sub: 'self-hosted · global',
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: 'Trades executed',
    sub: 'cumulative',
  },
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: 'GitHub stars',
    sub: 'since 2018',
  },
];

const ROADMAP: IconListItem[] = [
  {icon: '🧠', text: 'Strategies'},
  {icon: '🔗', text: 'Exchanges'},
  {icon: '🔌', text: 'Connectivity'},
  {icon: '✨', text: 'Other'},
];

export default function TradingBotPage(): ReactNode {
  return (
    <LandingLayout
      title="Trading bot"
      description="Automate your crypto trading with OctoBot. Easily create, backtest and optimize algorithmic or TradingView trading strategies.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Trading bot"
        title={
          <>
            Automate your crypto trading with{' '}
            <span className="ng-text-gradient">OctoBot.</span>
          </>
        }
        subtitle="Easily create, backtest and optimize algorithmic or TradingView trading strategies."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDE, variant: 'ghost'},
        ]}
        meta={[
          {label: '12+ exchanges', dot: true},
          {label: 'Backtesting included'},
          {label: 'Open source'},
        ]}
      />

      <Section
        align="left"
        eyebrow="Why OctoBot"
        title="Why using OctoBot?"
        lead="From hands-off investing to fully custom strategies — OctoBot adapts to how you want to trade.">
        <WhyTabs />
      </Section>

      <Section
        eyebrow="Exchanges"
        title="Your bot on the best exchanges"
        lead="OctoBot is compatible with leading exchanges to automate your strategies on more than 12 exchanges.">
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <Section
        eyebrow="Strategies"
        title="Built-in trading strategy bases"
        lead="OctoBot comes with many built-in strategies you can use as-is or as inspiration — and since it's open source, you can read the code to see how they work.">
        <FeatureGrid features={STRATEGIES} columns={2} />
      </Section>

      <Section>
        <StatStrip
          head={{eyebrow: 'Community', title: 'Used by traders worldwide'}}
          stats={STATS}
        />
      </Section>

      <Section
        eyebrow="Roadmap"
        title="Shape the future"
        lead="Influence the development of OctoBot with your ideas.">
        <IconList items={ROADMAP} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={REPO}>
            Open roadmap
          </Link>
        </div>
      </Section>

      <CTABand
        title="Start automating your crypto trading"
        description="Create your trading bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
