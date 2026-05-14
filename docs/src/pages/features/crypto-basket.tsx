import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
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
import GlassCard from '@site/src/components/GlassCard';
import YouTube from '@site/src/components/YouTube';
import styles from './_styles.module.css';

/*
 * Crypto Basket feature page — route: /features/crypto-basket.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components.
 */

const CLOUD = 'https://www.octobot.cloud';
const BASKET_GUIDE = '/guides/octobot-usage/strategy-designer';

const ADVANTAGES: Feature[] = [
  {
    icon: '🧺',
    title: 'Diversify in one move',
    description:
      'A basket groups several cryptocurrencies around a theme, spreading risk across many coins instead of one bet.',
  },
  {
    icon: '🔄',
    title: 'Automatic rebalancing',
    description:
      'When a coin runs up, its gains are distributed across the basket; when it dips, OctoBot buys to hold the target ratio.',
  },
  {
    icon: '🌱',
    title: 'Beginner-friendly',
    description:
      'Pick a theme you believe in — OctoBot handles selection, weighting and rebalancing for you.',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is a crypto basket?',
    answer:
      'A crypto basket is a collection of various cryptocurrencies grouped together based on a specific theme. It helps you diversify your portfolio to reduce risk.',
  },
  {
    question: 'Are crypto baskets suitable for beginners?',
    answer:
      'Crypto baskets can be suitable for beginners. When using OctoBot, you just need to choose a theme and OctoBot handles the rest.',
  },
  {
    question: 'What are the advantages of using a crypto basket?',
    answer:
      'Using a crypto basket offers two main advantages: it reduces risk by investing in multiple cryptocurrencies, and through automatic rebalancing you can benefit from the growth of one or more cryptocurrencies and realize gains.',
  },
  {
    question:
      'Can I test crypto baskets with virtual funds before investing real money?',
    answer:
      'Yes — with OctoBot you can experiment with any basket using virtual funds first.',
  },
  {
    question: 'Can I customize my crypto basket?',
    answer:
      'Yes — with OctoBot you can customize an existing basket or even create your own custom baskets.',
  },
  {
    question: 'How often are crypto baskets rebalanced?',
    answer:
      'The frequency of rebalancing varies depending on the specific basket. Some baskets are rebalanced periodically, while others may adjust dynamically based on market conditions or predefined criteria.',
  },
  {
    question: 'What happens if the price of a coin changes a lot?',
    answer:
      "When the price of a coin in a basket increases by a lot, its gains are distributed among the other coins of the basket. If its price drops, OctoBot buys more to maintain the basket's target ratio — but if a coin drops too far, it is removed from the basket and sold.",
  },
  {
    question: 'How are crypto baskets made?',
    answer:
      'Crypto baskets follow Coingecko categories and market-capitalization ranking. They may vary on each exchange according to the availability of coins. Note: coingecko.com is a website that specializes in ranking cryptocurrencies and is not related to OctoBot.',
  },
];

export default function CryptoBasketFeature(): ReactNode {
  return (
    <LandingLayout
      title="Crypto Basket"
      description="Invest in crypto following themes you believe in and easily diversify your portfolio with customizable, auto-rebalancing crypto baskets.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Crypto baskets"
        title={
          <>
            Invest in themes you love,{' '}
            <span className="ng-text-gradient">
              diversify with ease.
            </span>
          </>
        }
        subtitle="Thematic portfolios for every crypto investor — fine-tune your portfolio with customizable baskets."
        actions={[
          {label: 'Invest in a basket', to: CLOUD},
          {label: 'Read the guide', to: BASKET_GUIDE, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Auto-rebalancing', dot: true},
          {label: 'Fully customizable'},
          {label: 'Paper trading included'},
        ]}
      />

      <Section
        align="left"
        eyebrow="Customize"
        title="Make your own crypto basket"
        lead="Customize baskets to match your goals — or create your very own from scratch.">
        <GlassCard variant="strong" padded={false} className={styles.mix}>
          <div className={styles.mixLabel}>EXAMPLE BASKET · TARGET WEIGHTS</div>
          <div className={styles.mixBar}>
            <span style={{flex: 50, background: '#f7931a'}} />
            <span style={{flex: 30, background: '#8aa1f0'}} />
            <span style={{flex: 20, background: 'var(--ng-turquoise)'}} />
          </div>
          <div className={styles.mixLegend}>
            <span>
              <span style={{color: '#f7931a'}}>●</span> BTC 50%
            </span>
            <span>
              <span style={{color: '#8aa1f0'}}>●</span> ETH 30%
            </span>
            <span>
              <span style={{color: 'var(--ng-turquoise)'}}>●</span> SOL 20%
            </span>
          </div>
        </GlassCard>
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            Create my own crypto basket
          </Link>
        </div>
      </Section>

      <Section
        eyebrow="The best crypto"
        title="Invest in the best crypto"
        lead="Profit from the best crypto and trends of the market using crypto baskets.">
        <YouTube id="WOgS-VhUyIY" title="Investing in the best crypto" />
      </Section>

      <Section
        align="left"
        eyebrow="Why baskets"
        title="Diversification, done for you"
        lead="Crypto baskets spread risk and capture trends without you watching every coin.">
        <FeatureGrid features={ADVANTAGES} columns={3} />
      </Section>

      <Section eyebrow="FAQ" title="Crypto basket FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Build a basket around what you believe in"
        description="Pick a theme, set your weights, and let OctoBot keep it balanced."
        actions={[
          {label: 'Invest in a basket', to: CLOUD},
          {label: 'Read the guide', to: BASKET_GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
