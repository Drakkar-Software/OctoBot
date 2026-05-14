import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type FAQItem,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './_styles.module.css';

/*
 * TradingView Bot feature page — route: /features/tradingview-bot.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components.
 */

const CLOUD = 'https://www.octobot.cloud';
const TV_GUIDE = '/guides/octobot-interfaces/tradingview';

const STEPS: Step[] = [
  {
    icon: '📐',
    title: 'Define your strategy on TradingView',
    description:
      'Use a built-in indicator or your own Pine Script strategy on TradingView.',
  },
  {
    icon: '🔗',
    title: 'Connect OctoBot',
    description:
      'Link your TradingView account to OctoBot with a webhook integration.',
  },
  {
    icon: '🎯',
    title: 'Enter the amount to trade',
    description:
      'Set how much of your holdings each alert should trade — OctoBot does the rest.',
  },
];

const STRATEGIES: Feature[] = [
  {
    icon: '✖',
    title: 'Golden Cross on ETH/USDT',
    description:
      'Buying the base asset when moving-average indicators show a Golden Cross.',
  },
  {
    icon: '〰',
    title: 'RSI thresholds on ADA/USDT',
    description:
      'Selling the base asset when the RSI indicator signals an overbought market.',
  },
  {
    icon: '📉',
    title: 'Bearish Supports on BTC/USDT',
    description:
      'Selling the base asset as soon as a price support zone is broken.',
  },
  {
    icon: '🚀',
    title: 'Altcoins Bullmarket on SOL/USDT',
    description:
      'Buying the base asset when the price rises by more than 5% within 4 hours.',
  },
  {
    icon: '📜',
    title: 'Pine Script Strategy on ADA/BTC',
    description:
      'Using a Pine Script strategy on TradingView to automate your trades.',
  },
  {
    icon: '💡',
    title: 'Any other great idea',
    description:
      'Automate trades from any of TradingView’s tools — price moves, indicators or Pine Script.',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is TradingView?',
    answer:
      'TradingView is a popular online charting platform and social network for traders and investors to analyze financial markets and share trading ideas.',
  },
  {
    question: 'Why automating TradingView?',
    answer:
      'Automating TradingView allows traders to execute trades based on predefined strategies and alerts, reducing the need for manual intervention and enabling consistent strategy implementation.',
  },
  {
    question: 'What are the charges?',
    answer:
      "You need an OctoBot Cloud plan that allows running a TradingView OctoBot. Additionally, you'll need a paid TradingView account to use webhooks.",
  },
  {
    question: 'How to trade automatically with TradingView?',
    answer: (
      <>
        Start a TradingView OctoBot on your exchange account, link your
        TradingView account through a webhook integration, then create an alert
        based on your strategy. When the alert fires, OctoBot executes the
        corresponding trades.{' '}
        <Link to={TV_GUIDE}>
          Here is a dedicated guide on TradingView alerts automation.
        </Link>
      </>
    ),
  },
  {
    question: 'How to automate a TradingView strategy?',
    answer: (
      <>
        Update the Pine Script code of the strategy and add alert statements
        that trigger when your conditions are met. Those alerts are sent to your
        TradingView OctoBot, which executes the trades automatically.{' '}
        <Link to={TV_GUIDE}>
          Here is a dedicated guide on automating a TradingView strategy.
        </Link>
      </>
    ),
  },
  {
    question: 'Can I combine an RSI and an EMA in Pine Script?',
    answer: (
      <>
        Yes — you can combine indicators like the Relative Strength Index (RSI)
        and Exponential Moving Average (EMA) in Pine Script to build a custom
        strategy that generates alerts for your TradingView OctoBot.{' '}
        <Link to={TV_GUIDE}>
          Here is a dedicated guide on automating a TradingView indicator.
        </Link>
      </>
    ),
  },
  {
    question: 'How to use AI to create a TradingView strategy?',
    answer:
      'On OctoBot Cloud you can generate a TradingView strategy from a textual description of your trading ideas — the AI translates your concept into ready-to-use Pine Script code.',
  },
];

export default function TradingViewBotFeature(): ReactNode {
  return (
    <LandingLayout
      title="TradingView Bot"
      description="Easily automate any TradingView strategy, or leverage AI to create custom strategies for automated crypto trading without coding.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="TradingView bot"
        title={
          <>
            TradingView automated,{' '}
            <span className="ng-text-gradient">for crypto trading.</span>
          </>
        }
        subtitle="Automate any TradingView strategy, or create your own one with AI."
        actions={[
          {label: 'Automate my strategy', to: CLOUD},
          {label: 'Read the guide', to: TV_GUIDE, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Any indicator or strategy', dot: true},
          {label: 'Pine Script supported'},
          {label: 'AI strategy generation'},
        ]}
      />

      <Section
        eyebrow="How it works"
        title="Automate your strategies directly from TradingView"
        lead="Three steps from a TradingView alert to a live trade on your exchange.">
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow="Strategies"
        title="Automate any TradingView strategy"
        lead="From built-in indicators to your own Pine Script — a few examples of what you can wire up.">
        <FeatureGrid features={STRATEGIES} columns={3} />
      </Section>

      <Section
        align="left"
        eyebrow="AI generation"
        title={
          <>
            Generate your strategy with AI{' '}
            <Badge tone="frost">Early access</Badge>
          </>
        }
        lead="Describe the strategy you want — the AI turns it into ready-to-use Pine Script.">
        <GlassCard variant="strong" padded={false} className={styles.pineDemo}>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>Prompt</div>
            <p className={styles.pinePrompt}>
              Create a Bollinger Bands trading strategy that identifies buy and
              sell signals based on price movements relative to the upper and
              lower bands.
            </p>
          </div>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>Pine Script™</div>
            <pre className={styles.pineCode}>{`//@version=5
strategy("BB signals", overlay=true)
[mid, upper, lower] = ta.bb(close, 20, 2)
if ta.crossunder(close, lower)
    strategy.entry("Long", strategy.long)
if ta.crossover(close, upper)
    strategy.close("Long")`}</pre>
          </div>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>Result</div>
            <p className={styles.pinePrompt}>
              A ready-to-use TradingView strategy, wired to your OctoBot in a
              couple of clicks.
            </p>
          </div>
        </GlassCard>
      </Section>

      <Section eyebrow="FAQ" title="TradingView bot FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Turn your TradingView alerts into trades"
        description="Start a TradingView OctoBot on OctoBot Cloud, or read the automation guide first."
        actions={[
          {label: 'Automate my strategy', to: CLOUD},
          {label: 'Read the guide', to: TV_GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
