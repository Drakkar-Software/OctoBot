import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
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
      title={translate({
        id: 'tools.triangularArbitrage.layout.title',
        message: 'Crypto triangular arbitrage',
        description: 'Triangular arbitrage page meta title',
      })}
      description={translate({
        id: 'tools.triangularArbitrage.layout.description',
        message:
          'Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades.',
        description: 'Triangular arbitrage page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.triangularArbitrage.hero.eyebrow',
          message: 'Triangular arbitrage',
          description: 'Triangular arbitrage hero eyebrow',
        })}
        title={
          <span className="ng-text-gradient">
            <Translate
              id="tools.triangularArbitrage.hero.title"
              description="Triangular arbitrage hero title">
              Crypto triangular arbitrage.
            </Translate>
          </span>
        }
        subtitle={translate({
          id: 'tools.triangularArbitrage.hero.subtitle',
          message:
            'Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades.',
          description: 'Triangular arbitrage hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.triangularArbitrage.hero.action.invest',
              message: 'Invest for free',
              description: 'Triangular arbitrage hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.triangularArbitrage.hero.action.guides',
              message: 'Read the guides',
              description: 'Triangular arbitrage hero guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.triangularArbitrage.hero.meta.threeLeg',
              message: 'Three-leg trades',
              description: 'Triangular arbitrage hero meta: three-leg trades',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.triangularArbitrage.hero.meta.multiExchange',
              message: 'Multi-exchange',
              description: 'Triangular arbitrage hero meta: multi-exchange',
            }),
          },
          {
            label: translate({
              id: 'tools.triangularArbitrage.hero.meta.paperTrading',
              message: 'Paper trading included',
              description: 'Triangular arbitrage hero meta: paper trading',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.triangularArbitrage.opportunities.eyebrow',
          message: 'Opportunities',
          description: 'Triangular arbitrage opportunities section eyebrow',
        })}
        title={translate({
          id: 'tools.triangularArbitrage.opportunities.title',
          message: 'Latest opportunities detected by OctoBot',
          description: 'Triangular arbitrage opportunities section title',
        })}
        lead={translate({
          id: 'tools.triangularArbitrage.opportunities.lead',
          message:
            'A snapshot of the three-leg paths OctoBot scans for price gaps. Live opportunities are detected on OctoBot Cloud.',
          description: 'Triangular arbitrage opportunities section lead',
        })}>
        <OpportunityCards />
        <p className={styles.note}>
          <Translate
            id="tools.triangularArbitrage.opportunities.note"
            description="Triangular arbitrage results disclaimer note">
            Please note that the results do not include transaction fees to be
            paid for each trade or any price fluctuations that may occur during
            the trades.
          </Translate>
        </p>
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <Translate
              id="tools.triangularArbitrage.panel.title"
              description="Triangular arbitrage early access panel title">
              Do you want to trade using triangular arbitrage?
            </Translate>
          </h2>
          <p className={styles.panelText}>
            <Translate
              id="tools.triangularArbitrage.panel.text"
              description="Triangular arbitrage early access panel text">
              Be one of the first to use our new triangular arbitrage strategy.
            </Translate>
          </p>
          <Link
            className={`ng-btn ng-btn--primary ${styles.panelCta}`}
            to={CLOUD}>
            <Translate
              id="tools.triangularArbitrage.panel.cta"
              description="Triangular arbitrage early access panel CTA">
              Join the early access
            </Translate>
          </Link>
        </GlassCard>
      </Section>

      <CTABand
        title={translate({
          id: 'tools.triangularArbitrage.cta.title',
          message: 'Catch price gaps across three cryptocurrencies',
          description: 'Triangular arbitrage CTA band title',
        })}
        description={translate({
          id: 'tools.triangularArbitrage.cta.description',
          message:
            'Start a triangular arbitrage bot for free on OctoBot Cloud, or read the guides first.',
          description: 'Triangular arbitrage CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.triangularArbitrage.cta.action.invest',
              message: 'Invest for free',
              description: 'Triangular arbitrage CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.triangularArbitrage.cta.action.guides',
              message: 'Read the guides',
              description: 'Triangular arbitrage CTA guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
