import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  StatStrip,
  LogoRibbon,
  InlineStats,
  CTABand,
  type Feature,
  type Step,
  type Stat,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import LiveProof from './_LiveProof';
import AdminRows from './_AdminRows';
import ReportingDashboard from './_ReportingDashboard';
import styles from './index.module.css';

/*
 * OctoBot Market Making — full custom marketing page, route: /market-making.
 *
 * Migrated from the Market Making design bundle into the Neo Glass Dark
 * landing toolkit. Built the same way as src/pages/app: a navbar-less
 * LandingLayout composed from reusable components, with bespoke visuals
 * (live order book, admin disclosure rows, reporting console) colocated as
 * underscore-prefixed files Docusaurus ignores as routes.
 */

const ENGINE: Feature[] = [
  {
    icon: '⇄',
    title: 'Adaptive quoting',
    description: 'Spread and size scale to live volatility.',
  },
  {
    icon: '∑',
    title: 'Inventory hedging',
    description: 'Cross-venue, banded, never directional.',
  },
  {
    icon: '↯',
    title: 'Toxicity detection',
    description: 'Withdraws on adverse-selection signals.',
  },
  {
    icon: '▣',
    title: 'Multi-venue routing',
    description: '14 CEXs and 6 DEXs, one pool of inventory.',
  },
];

const HOW_STEPS: Step[] = [
  {
    title: 'Pull the engine',
    description:
      'Install on your server or cloud. Open-core, no outbound dependencies.',
  },
  {
    title: 'Plug your keys in',
    description:
      'Trade-only API scope, your sub-accounts. Keys never leave your environment.',
  },
  {
    title: 'Set your parameters',
    description:
      'Spreads, depth, inventory, kill switches — you write the policy.',
  },
  {
    title: 'Call us when needed',
    description:
      'Slack, on-call engineer, runbooks. We diagnose; you stay the admin.',
  },
];

const OUTCOMES: Stat[] = [
  {
    value: <span className="ng-text-gradient">−74%</span>,
    label: 'Spread, tightened',
    sub: 'median across programs',
  },
  {
    value: <span className="ng-text-gradient">8×</span>,
    label: 'Depth at ±2%',
    sub: 'vs. baseline',
  },
  {
    value: <span className="ng-text-gradient">5 days</span>,
    label: 'Signed → quoting',
    sub: 'on your first venue',
  },
];

const VENUES = [
  'BINANCE',
  'OKX',
  'BYBIT',
  'KRAKEN',
  'UNISWAP V4',
  'HYPERLIQUID',
  'RAYDIUM',
  '+ 12 MORE',
];

const NEVER: Feature[] = [
  {
    icon: '⊠',
    title: 'No 6-month lock-in',
    description:
      'Monthly opt-out. Miss SLAs two months and the fee is waived — you walk.',
  },
  {
    icon: '⌬',
    title: 'No loaned float',
    description:
      'Fixed-fee by default. Loans, if needed, sit in audited sub-accounts.',
  },
  {
    icon: '◉',
    title: 'No PDF-only proof',
    description:
      'Live dashboard. Spread, depth, share and drift — refreshed in real time.',
  },
];

const SUPPORT_MODELS = [
  {
    tag: '01 · Community',
    title: 'Free, forever, public.',
    text: 'Engine, docs, open issue tracker. The same engine paying teams run.',
    bullets: ['Public Discord & GitHub', 'Full docs, no paywall'],
  },
  {
    tag: '02 · Priority',
    title: 'Direct line to engineers.',
    text: "Private Slack, SLA response. We still don't touch your keys.",
    bullets: ['Named contacts, on-call', 'Month-to-month, no lock-in'],
  },
];

export default function MarketMakingPage(): ReactNode {
  return (
    <LandingLayout
      title="OctoBot Market Making"
      description="Professional-grade market making for your token — tight spreads, deep books, every venue. You hold the keys, we run the engine. Flat fee, no token cut.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="For token teams & treasuries"
        title={
          <>
            Tight spreads. <span className="ng-text-gradient">Deep books.</span>{' '}
            Every venue.
          </>
        }
        subtitle="Professional-grade market making for your token — without hiring a desk. We run the quotes, manage the inventory, and surface the numbers in a dashboard your whole team can read."
        actions={[
          {label: 'Book a strategy call', to: '#contact'},
          {label: 'See the engine', to: '#engine', variant: 'surface'},
        ]}
        visual={<LiveProof />}
        aside={
          <InlineStats
            stats={[
              {value: '62', label: 'Tokens under quote'},
              {value: '14', label: 'Venues integrated'},
              {value: '$1.8B', label: 'Quoted volume · 90d'},
            ]}
          />
        }
      />

      <Section
        align="left"
        eyebrow="01 / Ownership"
        title={
          <>
            You&apos;re the admin.{' '}
            <span className="ng-text-frost">We&apos;re the engine.</span>
          </>
        }
        lead="No token cut. No spread share. No custody. Flat fee, and you keep the keys.">
        <AdminRows />
      </Section>

      <Section>
        <StatStrip
          head={{eyebrow: '02 / Outcomes', title: 'Measurable from day one.'}}
          stats={OUTCOMES}
        />
      </Section>

      <Section
        id="how"
        align="left"
        eyebrow="03 / How it works"
        title={
          <>
            You deploy it.{' '}
            <span className="ng-text-frost">We&apos;re on the other end.</span>
          </>
        }>
        <GlassCard variant="strong" padded className={styles.callout}>
          <strong>No keys. No tokens. No access.</strong> The engine runs on
          your machine, your API keys, your venues.
        </GlassCard>
        <StepList steps={HOW_STEPS} />
      </Section>

      <Section
        id="engine"
        align="right"
        eyebrow="04 / The engine"
        title={
          <>
            Tight when calm.{' '}
            <span className="ng-text-frost">Wide when wild.</span>
          </>
        }>
        <FeatureGrid features={ENGINE} columns={2} />
      </Section>

      <Section eyebrow="05 / Venues" title="Where we quote.">
        <LogoRibbon items={VENUES} minCellWidth={160} />
      </Section>

      <Section
        eyebrow="06 / Reporting"
        title={
          <>
            Four numbers.{' '}
            <span className="ng-text-frost">That&apos;s the meeting.</span>
          </>
        }>
        <ReportingDashboard />
      </Section>

      <Section
        align="right"
        eyebrow="07 / Support"
        title={
          <>
            A line that{' '}
            <span className="ng-text-frost">actually answers.</span>
          </>
        }>
        <div className={styles.models}>
          {SUPPORT_MODELS.map((model) => (
            <GlassCard
              key={model.tag}
              variant="strong"
              padded={false}
              className={styles.model}>
              <span className={styles.modelTag}>{model.tag}</span>
              <h3 className={styles.modelTitle}>{model.title}</h3>
              <p className={styles.modelText}>{model.text}</p>
              <ul className={styles.modelBullets}>
                {model.bullets.map((bullet) => (
                  <li key={bullet}>{bullet}</li>
                ))}
              </ul>
            </GlassCard>
          ))}
        </div>
      </Section>

      <Section
        eyebrow="08 / If you've been burned"
        title={
          <>
            The three sentences{' '}
            <span className="ng-text-frost">we never make you say.</span>
          </>
        }>
        <FeatureGrid features={NEVER} columns={3} />
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.quoteCard}>
          <div className={styles.quoteMark} aria-hidden="true">
            &ldquo;
          </div>
          <p className={styles.quoteText}>
            From <span className="ng-text-frost">1.4%</span> spread to under{' '}
            <span className="ng-text-frost">7 bps</span> in a week. We stopped
            having liquidity meetings.
          </p>
          <div className={styles.quoteMeta}>
            <b>Head of Treasury</b> · L1 protocol · $180M FDV
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title={
          <>
            A 30-min call.{' '}
            <span className="ng-text-frost">A proposal in 48h.</span>
          </>
        }
        description="Talk to us about your token, your venues and your liquidity targets."
        actions={[
          {label: 'Book a call', to: 'mailto:contact@octobot.cloud'},
          {
            label: 'Read the engine docs',
            to: '/features/market-making',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
