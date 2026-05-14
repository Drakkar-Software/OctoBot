import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
import HeroStage from '@site/src/components/pages/home/HeroStage';
import WeekTimeline from '@site/src/components/pages/home/WeekTimeline';
import styles from './index.module.css';

/*
 * OctoBot App — full custom marketing page, route: / (the site homepage).
 *
 * Built the same way as src/pages/welcome.tsx: a navbar-less LandingLayout
 * composed from the reusable Neo Glass Dark landing toolkit. Page-specific
 * visuals (the phone mockup hero stage and the animated week timeline) are
 * colocated as underscore-prefixed files so Docusaurus ignores them as routes.
 */

const PRIVACY: Feature[] = [
  {
    icon: '⚿',
    title: translate({
      id: 'pages.index.privacy.keys.title',
      message: 'Keys stay on device',
      description: 'Home page privacy feature title',
    }),
    description: translate({
      id: 'pages.index.privacy.keys.description',
      message:
        'Sealed in the secure enclave. Your API keys and wallets are never uploaded.',
      description: 'Home page privacy feature description',
    }),
  },
  {
    icon: '◇',
    title: translate({
      id: 'pages.index.privacy.openSource.title',
      message: 'Open source, yours forever',
      description: 'Home page privacy feature title',
    }),
    description: translate({
      id: 'pages.index.privacy.openSource.description',
      message:
        'MIT-licensed core. If we vanish tomorrow, the app keeps working.',
      description: 'Home page privacy feature description',
    }),
  },
  {
    icon: '⊘',
    title: translate({
      id: 'pages.index.privacy.cloud.title',
      message: 'Nothing in the cloud',
      description: 'Home page privacy feature title',
    }),
    description: translate({
      id: 'pages.index.privacy.cloud.description',
      message:
        'No server holds your balances. There is simply nothing to leak.',
      description: 'Home page privacy feature description',
    }),
  },
];

const PRICING: PriceCell[] = [
  {
    tag: translate({
      id: 'pages.index.pricing.free.tag',
      message: 'Free · forever',
      description: 'Home page pricing tag',
    }),
    price: '€0',
    label: translate({
      id: 'pages.index.pricing.free.label',
      message: 'The base app',
      description: 'Home page pricing label',
    }),
    note: translate({
      id: 'pages.index.pricing.free.note',
      message:
        'Track every account. Two strategies running. No trial, no card.',
      description: 'Home page pricing note',
    }),
  },
  {
    tag: translate({
      id: 'pages.index.pricing.unlock.tag',
      message: 'One-time unlock',
      description: 'Home page pricing tag',
    }),
    price: '€39',
    priceSuffix: '–89',
    label: translate({
      id: 'pages.index.pricing.unlock.label',
      message: 'Power features, owned',
      description: 'Home page pricing label',
    }),
    note: translate({
      id: 'pages.index.pricing.unlock.note',
      message:
        'Advanced strategies, unlimited rules. Bought once, yours for good.',
      description: 'Home page pricing note',
    }),
    variant: 'feat',
  },
  {
    tag: translate({
      id: 'pages.index.pricing.never.tag',
      message: 'Never',
      description: 'Home page pricing tag',
    }),
    price: '€/mo',
    label: translate({
      id: 'pages.index.pricing.never.label',
      message: 'No subscription',
      description: 'Home page pricing label',
    }),
    note: translate({
      id: 'pages.index.pricing.never.note',
      message: 'No recurring tax. No pro wall. No countdown.',
      description: 'Home page pricing note',
    }),
    variant: 'muted',
  },
];

const FEATURED_TESTIMONIAL: Testimonial = {
  quote: translate({
    id: 'pages.index.testimonials.featured.quote',
    message:
      'Six years of holding, three exchanges, two banks, one spreadsheet I dreaded updating. I moved it all into OctoBot in an afternoon. The Sunday ritual is gone.',
    description: 'Home page featured testimonial quote',
  }),
  name: 'Maël K.',
  role: translate({
    id: 'pages.index.testimonials.featured.role',
    message: 'Long-time HODLer · Paris',
    description: 'Home page featured testimonial role',
  }),
  avatar: 'linear-gradient(135deg, #65e7cf, #4893f1)',
};

const TESTIMONIALS: Testimonial[] = [
  {
    quote: translate({
      id: 'pages.index.testimonials.sarah.quote',
      message:
        'The fact that nothing leaves the device is the only reason I trust it with an API key.',
      description: 'Home page testimonial quote',
    }),
    name: 'Sarah R.',
    role: translate({
      id: 'pages.index.testimonials.sarah.role',
      message: 'DevOps · Berlin',
      description: 'Home page testimonial role',
    }),
    avatar: 'linear-gradient(135deg, #85d6d7, #6cb596)',
  },
  {
    quote: translate({
      id: 'pages.index.testimonials.diego.quote',
      message:
        "I used to lag my trader by 20 minutes. Now I'm in the same candle.",
      description: 'Home page testimonial quote',
    }),
    name: 'Diego M.',
    role: translate({
      id: 'pages.index.testimonials.diego.role',
      message: 'Part-time trader · Madrid',
      description: 'Home page testimonial role',
    }),
    avatar: 'linear-gradient(135deg, #f0c53b, #e8a44e)',
  },
];

const TRACTION: Stat[] = [
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: translate({
      id: 'pages.index.traction.stars.label',
      message: 'GitHub stars',
      description: 'Home page traction stat label',
    }),
    sub: translate({
      id: 'pages.index.traction.stars.sub',
      message: 'since 2018 · organic',
      description: 'Home page traction stat sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: translate({
      id: 'pages.index.traction.installs.label',
      message: 'Active installs',
      description: 'Home page traction stat label',
    }),
    sub: translate({
      id: 'pages.index.traction.installs.sub',
      message: 'self-hosted · global',
      description: 'Home page traction stat sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: translate({
      id: 'pages.index.traction.trades.label',
      message: 'Trades executed',
      description: 'Home page traction stat label',
    }),
    sub: translate({
      id: 'pages.index.traction.trades.sub',
      message: 'cumulative to date',
      description: 'Home page traction stat sub',
    }),
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
  translate({
    id: 'pages.index.exchanges.more',
    message: '+ 20 more',
    description: 'Logo ribbon "and more" entry',
  }),
];

const TRACK_BARS = [40, 52, 48, 64, 70, 82, 95];

export default function AppPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.index.meta.title',
        message: 'OctoBot — Open-source crypto trading',
        description: 'Home page metadata title',
      })}
      description={translate({
        id: 'pages.index.meta.description',
        message:
          'OctoBot App — track every account and automate every strategy. Crypto, stocks, real estate and cash, encrypted on your own device. Open source, paid once.',
        description: 'Home page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.index.hero.eyebrow',
          message: 'A wealth app, only honest · 2026',
          description: 'Home page hero eyebrow',
        })}
        title={
          <Translate
            id="pages.index.hero.title"
            description="Home page hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.index.hero.title.accent',
                    message: 'Your device.',
                    description: 'Home page hero title accent words',
                  })}
                </span>
              ),
            }}>
            {'Your wealth. {accent} Your rules.'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.index.hero.subtitle',
          message:
            'One app to track every account and automate every strategy — crypto, stocks, real estate, cash. Encrypted on your phone. Open source. Paid once, owned forever.',
          description: 'Home page hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.index.hero.action.get',
              message: 'Get OctoBot — free',
              description: 'Home page hero action label',
            }),
            to: '/guides/octobot-installation/install-octobot-on-your-computer',
          },
          {
            label: translate({
              id: 'pages.index.hero.action.how',
              message: 'See how it works',
              description: 'Home page hero action label',
            }),
            to: '#two-jobs',
            variant: 'surface',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'pages.index.hero.meta.installs',
              message: '50K installs',
              description: 'Home page hero meta label',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'pages.index.hero.meta.stars',
              message: '6K GitHub stars · since 2018',
              description: 'Home page hero meta label',
            }),
          },
          {
            label: translate({
              id: 'pages.index.hero.meta.trades',
              message: '10M+ trades executed',
              description: 'Home page hero meta label',
            }),
          },
          {
            label: translate({
              id: 'pages.index.hero.meta.breaches',
              message: 'Zero breaches',
              description: 'Home page hero meta label',
            }),
          },
        ]}
      />

      <HeroStage />

      <Section
        id="two-jobs"
        eyebrow={translate({
          id: 'pages.index.twoJobs.eyebrow',
          message: '01 / What it does',
          description: 'Home page section eyebrow',
        })}
        title={translate({
          id: 'pages.index.twoJobs.title',
          message: 'One app. Two jobs.',
          description: 'Home page section title',
        })}
        lead={translate({
          id: 'pages.index.twoJobs.lead',
          message:
            'Tracking your wealth and automating it — the same surface, running locally on the device you already own.',
          description: 'Home page section lead',
        })}>
        <div className={styles.split}>
          <GlassCard variant="strong" padded={false} className={styles.splitCard}>
            <span className={styles.splitNum}>01 · TRACK</span>
            <h3 className={styles.splitTitle}>
              <Translate
                id="pages.index.twoJobs.track.title"
                description="Home page track card title">
                Wealth, on autopilot.
              </Translate>
            </h3>
            <p className={styles.splitText}>
              <Translate
                id="pages.index.twoJobs.track.text"
                description="Home page track card text">
                Crypto, stocks, real estate, cash — every account in one
                dashboard. Net worth, IRR, contribution vs. performance,
                hidden-fee detection. Goals with monthly check-ins.
              </Translate>
            </p>
            <div className={styles.tags}>
              <span>
                <Translate
                  id="pages.index.twoJobs.track.tag.multiAsset"
                  description="Home page track card tag">
                  multi-asset
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.track.tag.netWorth"
                  description="Home page track card tag">
                  net worth · irr
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.track.tag.goalTracking"
                  description="Home page track card tag">
                  goal tracking
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.track.tag.feeDetection"
                  description="Home page track card tag">
                  fee detection
                </Translate>
              </span>
            </div>
            <div className={styles.illu}>
              <div className={styles.illuLabel}>
                <Translate
                  id="pages.index.twoJobs.track.illuLabel"
                  description="Home page track card illustration label">
                  NET WORTH · 12 WEEKS
                </Translate>
              </div>
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
              <Translate
                id="pages.index.twoJobs.automate.title"
                description="Home page automate card title">
                Strategies that run while you sleep.
              </Translate>
            </h3>
            <p className={styles.splitText}>
              <Translate
                id="pages.index.twoJobs.automate.text"
                description="Home page automate card text">
                Visual strategy builder, real-history backtesting, paper
                trading, then live execution — all from your own device. DCA,
                grid, custom signals, copy.
              </Translate>
            </p>
            <div className={styles.tags}>
              <span>
                <Translate
                  id="pages.index.twoJobs.automate.tag.dca"
                  description="Home page automate card tag">
                  dca · grid · signals
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.automate.tag.backtest"
                  description="Home page automate card tag">
                  backtest
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.automate.tag.paperTrading"
                  description="Home page automate card tag">
                  paper trading
                </Translate>
              </span>
              <span>
                <Translate
                  id="pages.index.twoJobs.automate.tag.marketplace"
                  description="Home page automate card tag">
                  marketplace
                </Translate>
              </span>
            </div>
            <div className={styles.illu}>
              <div className={styles.illuLabel}>
                <Translate
                  id="pages.index.twoJobs.automate.illuLabel"
                  description="Home page automate card illustration label">
                  STRATEGY FLOW
                </Translate>
              </div>
              <div className={styles.flow}>
                <div className={styles.flowNode}>
                  <b>
                    <Translate
                      id="pages.index.twoJobs.automate.flow.signal.label"
                      description="Home page strategy flow node label">
                      Signal
                    </Translate>
                  </b>
                  <Translate
                    id="pages.index.twoJobs.automate.flow.signal.value"
                    description="Home page strategy flow node value">
                    RSI &lt; 30
                  </Translate>
                </div>
                <div className={styles.flowArrow}>→</div>
                <div className={styles.flowNode}>
                  <b>
                    <Translate
                      id="pages.index.twoJobs.automate.flow.rule.label"
                      description="Home page strategy flow node label">
                      Rule
                    </Translate>
                  </b>
                  <Translate
                    id="pages.index.twoJobs.automate.flow.rule.value"
                    description="Home page strategy flow node value">
                    Buy €100
                  </Translate>
                </div>
                <div className={styles.flowArrow}>→</div>
                <div className={styles.flowNode}>
                  <b>
                    <Translate
                      id="pages.index.twoJobs.automate.flow.venue.label"
                      description="Home page strategy flow node label">
                      Venue
                    </Translate>
                  </b>
                  Binance
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.index.switch.eyebrow',
          message: '02 / The switch',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.switch.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.switch.title.accent',
                    message: 'In with sleep.',
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Out with Sunday spreadsheets. {accent}'}
          </Translate>
        }>
        <BeforeAfter
          before={{
            label: translate({
              id: 'pages.index.switch.before.label',
              message: 'Before',
              description: 'Home page before/after label',
            }),
            items: [
              <Translate
                id="pages.index.switch.before.item1"
                description="Home page before item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.before.item1.strong',
                        message: 'spreadsheet',
                        description: 'Home page before item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {'Sunday {strong} ritual'}
              </Translate>,
              <Translate
                id="pages.index.switch.before.item2"
                description="Home page before item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.before.item2.strong',
                        message: '3am alerts',
                        description: 'Home page before item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {"{strong} you'll miss"}
              </Translate>,
              <Translate
                id="pages.index.switch.before.item3"
                description="Home page before item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.before.item3.strong',
                        message: '20 min late',
                        description: 'Home page before item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {'Copy-trading {strong}'}
              </Translate>,
            ],
          }}
          after={{
            label: translate({
              id: 'pages.index.switch.after.label',
              message: 'With OctoBot',
              description: 'Home page before/after label',
            }),
            items: [
              <Translate
                id="pages.index.switch.after.item1"
                description="Home page after item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.after.item1.strong',
                        message: 'One number',
                        description: 'Home page after item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {'{strong}, every account'}
              </Translate>,
              <Translate
                id="pages.index.switch.after.item2"
                description="Home page after item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.after.item2.strong',
                        message: 'Rules',
                        description: 'Home page after item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {'{strong} that run themselves'}
              </Translate>,
              <Translate
                id="pages.index.switch.after.item3"
                description="Home page after item"
                values={{
                  strong: (
                    <strong>
                      {translate({
                        id: 'pages.index.switch.after.item3.strong',
                        message: 'Mirror traders',
                        description: 'Home page after item emphasis',
                      })}
                    </strong>
                  ),
                }}>
                {'{strong} same candle'}
              </Translate>,
            ],
          }}
        />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'pages.index.privacySection.eyebrow',
          message: '03 / Privacy',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.privacySection.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.privacySection.title.accent',
                    message: 'not their database.',
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Your wealth, {accent}'}
          </Translate>
        }>
        <FeatureGrid features={PRIVACY} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.index.week.eyebrow',
          message: '04 / A week with OctoBot',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.week.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.week.title.accent',
                    message: "you don't.",
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'It runs while {accent}'}
          </Translate>
        }>
        <WeekTimeline />
      </Section>

      <Section
        id="pricing"
        align="left"
        eyebrow={translate({
          id: 'pages.index.pricingSection.eyebrow',
          message: '05 / Pricing',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.pricingSection.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.pricingSection.title.accent',
                    message: 'Own it.',
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Pay once. {accent}'}
          </Translate>
        }
        lead={translate({
          id: 'pages.index.pricingSection.lead',
          message:
            "Subscriptions are a tax on software you already paid for. We don't charge one.",
          description: 'Home page section lead',
        })}>
        <PricingStrip cells={PRICING} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.index.users.eyebrow',
          message: '06 / What users say',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.users.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.users.title.accent',
                    message: 'never sold to advertisers.',
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Six years of users we {accent}'}
          </Translate>
        }>
        <Testimonials featured={FEATURED_TESTIMONIAL} items={TESTIMONIALS} />
      </Section>

      <Section>
        <StatStrip
          head={{
            eyebrow: translate({
              id: 'pages.index.traction.eyebrow',
              message: '07 / Traction',
              description: 'Home page section eyebrow',
            }),
            title: translate({
              id: 'pages.index.traction.title',
              message: 'Six years of receipts.',
              description: 'Home page section title',
            }),
          }}
          stats={TRACTION}
        />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'pages.index.distribution.eyebrow',
          message: '08 / Distribution',
          description: 'Home page section eyebrow',
        })}
        title={
          <Translate
            id="pages.index.distribution.title"
            description="Home page section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.distribution.title.accent',
                    message: 'Trade in 60 seconds.',
                    description: 'Home page section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Plug in. {accent}'}
          </Translate>
        }>
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <CTABand
        title={
          <Translate
            id="pages.index.cta.title"
            description="Home page CTA title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.index.cta.title.accent',
                    message: 'open, private, and paid once.',
                    description: 'Home page CTA title accent words',
                  })}
                </span>
              ),
            }}>
            {'The wealth app of the next decade is {accent}'}
          </Translate>
        }
        description={translate({
          id: 'pages.index.cta.description',
          message: 'OctoBot — 50K users · 10M trades · 6K stars.',
          description: 'Home page CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.index.cta.action.get',
              message: 'Get OctoBot — free',
              description: 'Home page CTA action label',
            }),
            to: '/guides/octobot-installation/install-octobot-on-your-computer',
          },
          {
            label: translate({
              id: 'pages.index.cta.action.features',
              message: 'See every feature',
              description: 'Home page CTA action label',
            }),
            to: '/features/strategy-designer',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
