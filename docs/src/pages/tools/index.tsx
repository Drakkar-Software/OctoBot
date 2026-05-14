import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  CTABand,
  type Feature,
} from '@site/src/components/landing';
import styles from './index.module.css';

/*
 * Crypto tools hub — route: /tools.
 *
 * Landing page for the OctoBot free tools, migrated from the OctoBot Cloud
 * marketing site into the Neo Glass Dark landing toolkit. Built the same way
 * as the feature pages: a navbar-less LandingLayout composed entirely from
 * reusable components.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

const TOOLS: Feature[] = [
  {
    icon: '🧠',
    title: 'ChatGPT crypto predictions',
    description:
      'OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals.',
    to: '/tools/crypto-prediction',
  },
  {
    icon: '🔺',
    title: 'Crypto triangular arbitrage',
    description:
      'Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades.',
    to: '/tools/triangular-arbitrage-crypto',
  },
  {
    icon: '⚡',
    title: 'Scalping signals',
    description:
      'Scalping is a quick trading technique involving many small transactions to capitalize on slight price movements — frequent, modest profits.',
    to: '/tools/scalping-signals',
  },
  {
    icon: '🏆',
    title: 'Cryptocurrencies ranking',
    description: 'Cryptocurrency rankings by market cap, powered by Coingecko data.',
    to: '/tools/crypto-ranking',
  },
  {
    icon: '💱',
    title: 'Crypto converters',
    description:
      'Convert between any crypto and fiat with live prices, market data and conversion tables.',
    to: '/tools/converter',
  },
];

export default function ToolsHub(): ReactNode {
  return (
    <LandingLayout
      title="Crypto tools"
      description="A set of free crypto tools to research the market and sharpen your strategy — ChatGPT predictions, scalping signals, rankings, arbitrage and converters.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Free crypto tools"
        title={
          <>
            Free crypto tools to{' '}
            <span className="ng-text-gradient">sharpen your strategy.</span>
          </>
        }
        subtitle="A set of free tools to research the market and sharpen your strategy — predictions, signals, rankings and converters."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Free to use', dot: true},
          {label: 'Live market data'},
          {label: 'No account required'},
        ]}
      />

      <Section
        eyebrow="Toolbox"
        title="Five tools to research the market"
        lead="Each tool digs into a different corner of the crypto market — from AI predictions to live price conversion. Pick one and start exploring.">
        <FeatureGrid features={TOOLS} columns={3} />
      </Section>

      <CTABand
        title="Put these tools to work on your portfolio"
        description="Create your trading bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
