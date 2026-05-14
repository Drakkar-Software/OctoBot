import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  FAQ,
  CTABand,
  type Feature,
  type FAQItem,
} from '@site/src/components/landing';
import ConverterCard from './_ConverterCard';
import styles from './converter.module.css';

/*
 * Crypto converters tool page — route: /tools/converter.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the feature pages: a navbar-less
 * LandingLayout composed from reusable components, plus a page-local
 * _ConverterCard mock for the live-price visual.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

const PAIRS: Feature[] = [
  {
    icon: '₿',
    title: 'BTC → USD',
    description: 'Live Bitcoin price, market cap and conversion table.',
    to: CLOUD,
  },
  {
    icon: 'Ξ',
    title: 'ETH → USD',
    description: 'Live Ethereum price, market cap and conversion table.',
    to: CLOUD,
  },
  {
    icon: '◎',
    title: 'SOL → USD',
    description: 'Live Solana price, market cap and conversion table.',
    to: CLOUD,
  },
  {
    icon: '🔶',
    title: 'BNB → USD',
    description: 'Live BNB price, market cap and conversion table.',
    to: CLOUD,
  },
  {
    icon: '✕',
    title: 'XRP → USD',
    description: 'Live XRP price, market cap and conversion table.',
    to: CLOUD,
  },
  {
    icon: '₳',
    title: 'ADA → USD',
    description: 'Live Cardano price, market cap and conversion table.',
    to: CLOUD,
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is a crypto ticker?',
    answer:
      'A ticker is the short symbol used to identify a cryptocurrency on exchanges — for example BTC for Bitcoin or ETH for Ethereum.',
  },
  {
    question: 'Is it possible to earn money with crypto investments?',
    answer:
      'Yes, it is possible to earn money with crypto, but it also carries significant risk. You should do your own research and use risk-management tools like OctoBot.',
  },
  {
    question: 'How can I check the live price of a crypto?',
    answer:
      'You can check live crypto prices on platforms like TradingView, or through cryptocurrency exchange platforms.',
  },
  {
    question: "How is a crypto's market cap calculated?",
    answer:
      "A crypto's market cap is calculated by multiplying the current price of one coin by the total number of coins in circulation.",
  },
];

export default function CryptoConverter(): ReactNode {
  return (
    <LandingLayout
      title="Crypto converters"
      description="Real-time price conversion between any cryptocurrency and fiat — with market data and conversion tables.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Crypto converters"
        title={
          <>
            Convert crypto at the{' '}
            <span className="ng-text-gradient">live price.</span>
          </>
        }
        subtitle="Real-time price conversion between any cryptocurrency and fiat — with market data and conversion tables."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Live prices', dot: true},
          {label: 'Any crypto / fiat pair'},
          {label: 'Conversion tables'},
        ]}
      />

      <Section eyebrow="Live price" title="A converter for every pair">
        <ConverterCard />
      </Section>

      <Section
        eyebrow="Popular"
        title="Popular conversion pairs"
        lead="The pairs traders check most — each one opens a live converter with current price, market cap and a full conversion table.">
        <FeatureGrid features={PAIRS} columns={3} />
      </Section>

      <Section eyebrow="FAQ" title="Crypto converter FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Convert, then put your crypto to work"
        description="Create your trading bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
