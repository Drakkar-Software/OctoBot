import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {
  LandingLayout,
  Hero,
  Section,
  CTABand,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import styles from './_styles.module.css';
import OpportunityCards from '@site/src/components/pages/tools/triangular-arbitrage-crypto/OpportunityCards';

/*
 * Crypto triangular arbitrage tool page —
 * route: /tools/triangular-arbitrage-crypto.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components, with a page-local sample-opportunity grid (_OpportunityCards).
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

export default function TriangularArbitrageTool(): ReactNode {
  return (
    <LandingLayout
      title="Crypto triangular arbitrage"
      description="Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Triangular arbitrage"
        title={
          <>
            <span className="ng-text-gradient">
              Crypto triangular arbitrage.
            </span>
          </>
        }
        subtitle="Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Three-leg trades', dot: true},
          {label: 'Multi-exchange'},
          {label: 'Paper trading included'},
        ]}
      />

      <Section
        eyebrow="Opportunities"
        title="Latest opportunities detected by OctoBot"
        lead="A snapshot of the three-leg paths OctoBot scans for price gaps. Live opportunities are detected on OctoBot Cloud.">
        <OpportunityCards />
        <p className={styles.note}>
          Please note that the results do not include transaction fees to be
          paid for each trade or any price fluctuations that may occur during
          the trades.
        </p>
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h2 className={styles.panelTitle}>
            Do you want to trade using triangular arbitrage?
          </h2>
          <p className={styles.panelText}>
            Be one of the first to use our new triangular arbitrage strategy.
          </p>
          <Link
            className={`ng-btn ng-btn--primary ${styles.panelCta}`}
            to={CLOUD}>
            Join the early access
          </Link>
        </GlassCard>
      </Section>

      <CTABand
        title="Catch price gaps across three cryptocurrencies"
        description="Start a triangular arbitrage bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
