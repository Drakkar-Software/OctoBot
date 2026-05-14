import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  BeforeAfter,
  PricingStrip,
  Testimonials,
  StatStrip,
  LogoRibbon,
  CTABand,
  type Feature,
  type PriceCell,
  type Testimonial,
  type Stat,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import HeroStage from './_HeroStage';
import WeekTimeline from './_WeekTimeline';
import styles from './index.module.css';

/*
 * OctoBot App — full custom marketing page, route: /app.
 *
 * Built the same way as src/pages/welcome.tsx: a navbar-less LandingLayout
 * composed from the reusable Neo Glass Dark landing toolkit. Page-specific
 * visuals (the phone mockup hero stage and the animated week timeline) are
 * colocated as underscore-prefixed files so Docusaurus ignores them as routes.
 */

const PRIVACY: Feature[] = [
  {
    icon: '⚿',
    title: 'Keys stay on device',
    description:
      'Sealed in the secure enclave. Your API keys and wallets are never uploaded.',
  },
  {
    icon: '◇',
    title: 'Open source, yours forever',
    description:
      'MIT-licensed core. If we vanish tomorrow, the app keeps working.',
  },
  {
    icon: '⊘',
    title: 'Nothing in the cloud',
    description:
      'No server holds your balances. There is simply nothing to leak.',
  },
];

const PRICING: PriceCell[] = [
  {
    tag: 'Free · forever',
    price: '€0',
    label: 'The base app',
    note: 'Track every account. Two strategies running. No trial, no card.',
  },
  {
    tag: 'One-time unlock',
    price: '€39',
    priceSuffix: '–89',
    label: 'Power features, owned',
    note: 'Advanced strategies, unlimited rules. Bought once, yours for good.',
    variant: 'feat',
  },
  {
    tag: 'Never',
    price: '€/mo',
    label: 'No subscription',
    note: 'No recurring tax. No pro wall. No countdown.',
    variant: 'muted',
  },
];

const FEATURED_TESTIMONIAL: Testimonial = {
  quote:
    'Six years of holding, three exchanges, two banks, one spreadsheet I dreaded updating. I moved it all into OctoBot in an afternoon. The Sunday ritual is gone.',
  name: 'Maël K.',
  role: 'Long-time HODLer · Paris',
  avatar: 'linear-gradient(135deg, #65e7cf, #4893f1)',
};

const TESTIMONIALS: Testimonial[] = [
  {
    quote:
      'The fact that nothing leaves the device is the only reason I trust it with an API key.',
    name: 'Sarah R.',
    role: 'DevOps · Berlin',
    avatar: 'linear-gradient(135deg, #85d6d7, #6cb596)',
  },
  {
    quote:
      "I used to lag my trader by 20 minutes. Now I'm in the same candle.",
    name: 'Diego M.',
    role: 'Part-time trader · Madrid',
    avatar: 'linear-gradient(135deg, #f0c53b, #e8a44e)',
  },
];

const TRACTION: Stat[] = [
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: 'GitHub stars',
    sub: 'since 2018 · organic',
  },
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: 'Active installs',
    sub: 'self-hosted · global',
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: 'Trades executed',
    sub: 'cumulative to date',
  },
];

const EXCHANGES = [
  'BINANCE',
  'COINBASE',
  'KRAKEN',
  'KUCOIN',
  'BYBIT',
  'OKX',
  'BITGET',
  'GATE.IO',
  'BITFINEX',
  'HUOBI',
  'MEXC',
  '+ 20 more',
];

const TRACK_BARS = [40, 52, 48, 64, 70, 82, 95];

export default function AppPage(): ReactNode {
  return (
    <LandingLayout
      title="OctoBot App"
      description="OctoBot App — track every account and automate every strategy. Crypto, stocks, real estate and cash, encrypted on your own device. Open source, paid once.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="A wealth app, only honest · 2026"
        title={
          <>
            Your wealth. <span className="ng-text-gradient">Your device.</span>{' '}
            Your rules.
          </>
        }
        subtitle="One app to track every account and automate every strategy — crypto, stocks, real estate, cash. Encrypted on your phone. Open source. Paid once, owned forever."
        actions={[
          {
            label: 'Get OctoBot — free',
            to: '/guides/octobot-installation/install-octobot-on-your-computer',
          },
          {label: 'See how it works', to: '#two-jobs', variant: 'surface'},
        ]}
        meta={[
          {label: '50K installs', dot: true},
          {label: '6K GitHub stars · since 2018'},
          {label: '10M+ trades executed'},
          {label: 'Zero breaches'},
        ]}
      />

      <HeroStage />

      <Section
        id="two-jobs"
        eyebrow="01 / What it does"
        title="One app. Two jobs."
        lead="Tracking your wealth and automating it — the same surface, running locally on the device you already own.">
        <div className={styles.split}>
          <GlassCard variant="strong" padded={false} className={styles.splitCard}>
            <span className={styles.splitNum}>01 · TRACK</span>
            <h3 className={styles.splitTitle}>Wealth, on autopilot.</h3>
            <p className={styles.splitText}>
              Crypto, stocks, real estate, cash — every account in one
              dashboard. Net worth, IRR, contribution vs. performance,
              hidden-fee detection. Goals with monthly check-ins.
            </p>
            <div className={styles.tags}>
              <span>multi-asset</span>
              <span>net worth · irr</span>
              <span>goal tracking</span>
              <span>fee detection</span>
            </div>
            <div className={styles.illu}>
              <div className={styles.illuLabel}>NET WORTH · 12 WEEKS</div>
              <div className={styles.bars}>
                {TRACK_BARS.map((h, i) => (
                  <span key={i} style={{height: `${h}%`}} />
                ))}
              </div>
            </div>
          </GlassCard>

          <GlassCard variant="strong" padded={false} className={styles.splitCard}>
            <span className={styles.splitNum}>02 · AUTOMATE</span>
            <h3 className={styles.splitTitle}>
              Strategies that run while you sleep.
            </h3>
            <p className={styles.splitText}>
              Visual strategy builder, real-history backtesting, paper trading,
              then live execution — all from your own device. DCA, grid, custom
              signals, copy.
            </p>
            <div className={styles.tags}>
              <span>dca · grid · signals</span>
              <span>backtest</span>
              <span>paper trading</span>
              <span>marketplace</span>
            </div>
            <div className={styles.illu}>
              <div className={styles.illuLabel}>STRATEGY FLOW</div>
              <div className={styles.flow}>
                <div className={styles.flowNode}>
                  <b>Signal</b>RSI &lt; 30
                </div>
                <div className={styles.flowArrow}>→</div>
                <div className={styles.flowNode}>
                  <b>Rule</b>Buy €100
                </div>
                <div className={styles.flowArrow}>→</div>
                <div className={styles.flowNode}>
                  <b>Venue</b>Binance
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </Section>

      <Section
        align="left"
        eyebrow="02 / The switch"
        title={
          <>
            Out with Sunday spreadsheets.{' '}
            <span className="ng-text-frost">In with sleep.</span>
          </>
        }>
        <BeforeAfter
          before={{
            label: 'Before',
            items: [
              <>
                Sunday <strong>spreadsheet</strong> ritual
              </>,
              <>
                <strong>3am alerts</strong> you&apos;ll miss
              </>,
              <>
                Copy-trading <strong>20 min late</strong>
              </>,
            ],
          }}
          after={{
            label: 'With OctoBot',
            items: [
              <>
                <strong>One number</strong>, every account
              </>,
              <>
                <strong>Rules</strong> that run themselves
              </>,
              <>
                <strong>Mirror traders</strong> same candle
              </>,
            ],
          }}
        />
      </Section>

      <Section
        align="right"
        eyebrow="03 / Privacy"
        title={
          <>
            Your wealth,{' '}
            <span className="ng-text-frost">not their database.</span>
          </>
        }>
        <FeatureGrid features={PRIVACY} columns={3} />
      </Section>

      <Section
        eyebrow="04 / A week with OctoBot"
        title={
          <>
            It runs while <span className="ng-text-frost">you don&apos;t.</span>
          </>
        }>
        <WeekTimeline />
      </Section>

      <Section
        id="pricing"
        align="left"
        eyebrow="05 / Pricing"
        title={
          <>
            Pay once. <span className="ng-text-frost">Own it.</span>
          </>
        }
        lead="Subscriptions are a tax on software you already paid for. We don't charge one.">
        <PricingStrip cells={PRICING} />
      </Section>

      <Section
        align="left"
        eyebrow="06 / What users say"
        title={
          <>
            Six years of users we{' '}
            <span className="ng-text-frost">never sold to advertisers.</span>
          </>
        }>
        <Testimonials featured={FEATURED_TESTIMONIAL} items={TESTIMONIALS} />
      </Section>

      <Section>
        <StatStrip
          head={{eyebrow: '07 / Traction', title: 'Six years of receipts.'}}
          stats={TRACTION}
        />
      </Section>

      <Section
        align="right"
        eyebrow="08 / Distribution"
        title={
          <>
            Plug in.{' '}
            <span className="ng-text-frost">Trade in 60 seconds.</span>
          </>
        }>
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <CTABand
        title={
          <>
            The wealth app of the next decade is{' '}
            <span className="ng-text-frost">open, private, and paid once.</span>
          </>
        }
        description="OctoBot — 50K users · 10M trades · 6K stars."
        actions={[
          {
            label: 'Get OctoBot — free',
            to: '/guides/octobot-installation/install-octobot-on-your-computer',
          },
          {
            label: 'See every feature',
            to: '/features/strategy-designer',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
