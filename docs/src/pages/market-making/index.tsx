import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
import LiveProof from '@site/src/components/pages/market-making/LiveProof';
import AdminRows from '@site/src/components/pages/market-making/AdminRows';
import ReportingDashboard from '@site/src/components/pages/market-making/ReportingDashboard';
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
    title: translate({
      id: 'pages.marketMaking.engine.quoting.title',
      message: 'Adaptive quoting',
      description: 'Market making engine feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.engine.quoting.description',
      message: 'Spread and size scale to live volatility.',
      description: 'Market making engine feature description',
    }),
  },
  {
    icon: '∑',
    title: translate({
      id: 'pages.marketMaking.engine.hedging.title',
      message: 'Inventory hedging',
      description: 'Market making engine feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.engine.hedging.description',
      message: 'Cross-venue, banded, never directional.',
      description: 'Market making engine feature description',
    }),
  },
  {
    icon: '↯',
    title: translate({
      id: 'pages.marketMaking.engine.toxicity.title',
      message: 'Toxicity detection',
      description: 'Market making engine feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.engine.toxicity.description',
      message: 'Withdraws on adverse-selection signals.',
      description: 'Market making engine feature description',
    }),
  },
  {
    icon: '▣',
    title: translate({
      id: 'pages.marketMaking.engine.routing.title',
      message: 'Multi-venue routing',
      description: 'Market making engine feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.engine.routing.description',
      message: '14 CEXs and 6 DEXs, one pool of inventory.',
      description: 'Market making engine feature description',
    }),
  },
];

const HOW_STEPS: Step[] = [
  {
    title: translate({
      id: 'pages.marketMaking.how.pull.title',
      message: 'Pull the engine',
      description: 'Market making step title',
    }),
    description: translate({
      id: 'pages.marketMaking.how.pull.description',
      message:
        'Install on your server or cloud. Open-core, no outbound dependencies.',
      description: 'Market making step description',
    }),
  },
  {
    title: translate({
      id: 'pages.marketMaking.how.keys.title',
      message: 'Plug your keys in',
      description: 'Market making step title',
    }),
    description: translate({
      id: 'pages.marketMaking.how.keys.description',
      message:
        'Trade-only API scope, your sub-accounts. Keys never leave your environment.',
      description: 'Market making step description',
    }),
  },
  {
    title: translate({
      id: 'pages.marketMaking.how.parameters.title',
      message: 'Set your parameters',
      description: 'Market making step title',
    }),
    description: translate({
      id: 'pages.marketMaking.how.parameters.description',
      message:
        'Spreads, depth, inventory, kill switches — you write the policy.',
      description: 'Market making step description',
    }),
  },
  {
    title: translate({
      id: 'pages.marketMaking.how.call.title',
      message: 'Call us when needed',
      description: 'Market making step title',
    }),
    description: translate({
      id: 'pages.marketMaking.how.call.description',
      message:
        'Slack, on-call engineer, runbooks. We diagnose; you stay the admin.',
      description: 'Market making step description',
    }),
  },
];

const OUTCOMES: Stat[] = [
  {
    value: <span className="ng-text-gradient">−74%</span>,
    label: translate({
      id: 'pages.marketMaking.outcomes.spread.label',
      message: 'Spread, tightened',
      description: 'Market making outcome label',
    }),
    sub: translate({
      id: 'pages.marketMaking.outcomes.spread.sub',
      message: 'median across programs',
      description: 'Market making outcome sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">8×</span>,
    label: translate({
      id: 'pages.marketMaking.outcomes.depth.label',
      message: 'Depth at ±2%',
      description: 'Market making outcome label',
    }),
    sub: translate({
      id: 'pages.marketMaking.outcomes.depth.sub',
      message: 'vs. baseline',
      description: 'Market making outcome sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">5 days</span>,
    label: translate({
      id: 'pages.marketMaking.outcomes.quoting.label',
      message: 'Signed → quoting',
      description: 'Market making outcome label',
    }),
    sub: translate({
      id: 'pages.marketMaking.outcomes.quoting.sub',
      message: 'on your first venue',
      description: 'Market making outcome sub',
    }),
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
  translate({
    id: 'pages.marketMaking.venues.more',
    message: '+ 12 MORE',
    description: 'Logo ribbon "and more" entry',
  }),
];

const NEVER: Feature[] = [
  {
    icon: '⊠',
    title: translate({
      id: 'pages.marketMaking.never.lockIn.title',
      message: 'No 6-month lock-in',
      description: 'Market making "never" feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.never.lockIn.description',
      message:
        'Monthly opt-out. Miss SLAs two months and the fee is waived — you walk.',
      description: 'Market making "never" feature description',
    }),
  },
  {
    icon: '⌬',
    title: translate({
      id: 'pages.marketMaking.never.float.title',
      message: 'No loaned float',
      description: 'Market making "never" feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.never.float.description',
      message:
        'Fixed-fee by default. Loans, if needed, sit in audited sub-accounts.',
      description: 'Market making "never" feature description',
    }),
  },
  {
    icon: '◉',
    title: translate({
      id: 'pages.marketMaking.never.proof.title',
      message: 'No PDF-only proof',
      description: 'Market making "never" feature title',
    }),
    description: translate({
      id: 'pages.marketMaking.never.proof.description',
      message:
        'Live dashboard. Spread, depth, share and drift — refreshed in real time.',
      description: 'Market making "never" feature description',
    }),
  },
];

const SUPPORT_MODELS = [
  {
    tag: translate({
      id: 'pages.marketMaking.support.community.tag',
      message: '01 · Community',
      description: 'Market making support model tag',
    }),
    title: translate({
      id: 'pages.marketMaking.support.community.title',
      message: 'Free, forever, public.',
      description: 'Market making support model title',
    }),
    text: translate({
      id: 'pages.marketMaking.support.community.text',
      message:
        'Engine, docs, open issue tracker. The same engine paying teams run.',
      description: 'Market making support model text',
    }),
    bullets: [
      translate({
        id: 'pages.marketMaking.support.community.bullet1',
        message: 'Public Discord & GitHub',
        description: 'Market making support model bullet',
      }),
      translate({
        id: 'pages.marketMaking.support.community.bullet2',
        message: 'Full docs, no paywall',
        description: 'Market making support model bullet',
      }),
    ],
  },
  {
    tag: translate({
      id: 'pages.marketMaking.support.priority.tag',
      message: '02 · Priority',
      description: 'Market making support model tag',
    }),
    title: translate({
      id: 'pages.marketMaking.support.priority.title',
      message: 'Direct line to engineers.',
      description: 'Market making support model title',
    }),
    text: translate({
      id: 'pages.marketMaking.support.priority.text',
      message: "Private Slack, SLA response. We still don't touch your keys.",
      description: 'Market making support model text',
    }),
    bullets: [
      translate({
        id: 'pages.marketMaking.support.priority.bullet1',
        message: 'Named contacts, on-call',
        description: 'Market making support model bullet',
      }),
      translate({
        id: 'pages.marketMaking.support.priority.bullet2',
        message: 'Month-to-month, no lock-in',
        description: 'Market making support model bullet',
      }),
    ],
  },
];

export default function MarketMakingPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.marketMaking.meta.title',
        message: 'OctoBot Market Making',
        description: 'Market making page metadata title',
      })}
      description={translate({
        id: 'pages.marketMaking.meta.description',
        message:
          'Professional-grade market making for your token — tight spreads, deep books, every venue. You hold the keys, we run the engine. Flat fee, no token cut.',
        description: 'Market making page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.marketMaking.hero.eyebrow',
          message: 'For token teams & treasuries',
          description: 'Market making hero eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.hero.title"
            description="Market making hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.marketMaking.hero.title.accent',
                    message: 'Deep books.',
                    description: 'Market making hero title accent words',
                  })}
                </span>
              ),
            }}>
            {'Tight spreads. {accent} Every venue.'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.marketMaking.hero.subtitle',
          message:
            'Professional-grade market making for your token — without hiring a desk. We run the quotes, manage the inventory, and surface the numbers in a dashboard your whole team can read.',
          description: 'Market making hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.marketMaking.hero.action.call',
              message: 'Book a strategy call',
              description: 'Market making hero action label',
            }),
            to: '#contact',
          },
          {
            label: translate({
              id: 'pages.marketMaking.hero.action.engine',
              message: 'See the engine',
              description: 'Market making hero action label',
            }),
            to: '#engine',
            variant: 'surface',
          },
        ]}
        visual={<LiveProof />}
        aside={
          <InlineStats
            stats={[
              {
                value: '62',
                label: translate({
                  id: 'pages.marketMaking.hero.stat.tokens',
                  message: 'Tokens under quote',
                  description: 'Market making hero stat label',
                }),
              },
              {
                value: '14',
                label: translate({
                  id: 'pages.marketMaking.hero.stat.venues',
                  message: 'Venues integrated',
                  description: 'Market making hero stat label',
                }),
              },
              {
                value: '$1.8B',
                label: translate({
                  id: 'pages.marketMaking.hero.stat.volume',
                  message: 'Quoted volume · 90d',
                  description: 'Market making hero stat label',
                }),
              },
            ]}
          />
        }
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.marketMaking.ownership.eyebrow',
          message: '01 / Ownership',
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.ownership.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.ownership.title.accent',
                    message: "We're the engine.",
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {"You're the admin. {accent}"}
          </Translate>
        }
        lead={translate({
          id: 'pages.marketMaking.ownership.lead',
          message:
            'No token cut. No spread share. No custody. Flat fee, and you keep the keys.',
          description: 'Market making section lead',
        })}>
        <AdminRows />
      </Section>

      <Section>
        <StatStrip
          head={{
            eyebrow: translate({
              id: 'pages.marketMaking.outcomes.eyebrow',
              message: '02 / Outcomes',
              description: 'Market making section eyebrow',
            }),
            title: translate({
              id: 'pages.marketMaking.outcomes.title',
              message: 'Measurable from day one.',
              description: 'Market making section title',
            }),
          }}
          stats={OUTCOMES}
        />
      </Section>

      <Section
        id="how"
        align="left"
        eyebrow={translate({
          id: 'pages.marketMaking.howSection.eyebrow',
          message: '03 / How it works',
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.howSection.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.howSection.title.accent',
                    message: "We're on the other end.",
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {'You deploy it. {accent}'}
          </Translate>
        }>
        <GlassCard variant="strong" padded className={styles.callout}>
          <Translate
            id="pages.marketMaking.howSection.callout"
            description="Market making how-it-works callout"
            values={{
              strong: (
                <strong>
                  {translate({
                    id: 'pages.marketMaking.howSection.callout.strong',
                    message: 'No keys. No tokens. No access.',
                    description: 'Market making callout emphasis',
                  })}
                </strong>
              ),
            }}>
            {
              '{strong} The engine runs on your machine, your API keys, your venues.'
            }
          </Translate>
        </GlassCard>
        <StepList steps={HOW_STEPS} />
      </Section>

      <Section
        id="engine"
        align="right"
        eyebrow={translate({
          id: 'pages.marketMaking.engineSection.eyebrow',
          message: '04 / The engine',
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.engineSection.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.engineSection.title.accent',
                    message: 'Wide when wild.',
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Tight when calm. {accent}'}
          </Translate>
        }>
        <FeatureGrid features={ENGINE} columns={2} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.marketMaking.venuesSection.eyebrow',
          message: '05 / Venues',
          description: 'Market making section eyebrow',
        })}
        title={translate({
          id: 'pages.marketMaking.venuesSection.title',
          message: 'Where we quote.',
          description: 'Market making section title',
        })}>
        <LogoRibbon items={VENUES} minCellWidth={160} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.marketMaking.reporting.eyebrow',
          message: '06 / Reporting',
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.reporting.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.reporting.title.accent',
                    message: "That's the meeting.",
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {'Four numbers. {accent}'}
          </Translate>
        }>
        <ReportingDashboard />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'pages.marketMaking.supportSection.eyebrow',
          message: '07 / Support',
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.supportSection.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.supportSection.title.accent',
                    message: 'actually answers.',
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {'A line that {accent}'}
          </Translate>
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
        eyebrow={translate({
          id: 'pages.marketMaking.burned.eyebrow',
          message: "08 / If you've been burned",
          description: 'Market making section eyebrow',
        })}
        title={
          <Translate
            id="pages.marketMaking.burned.title"
            description="Market making section title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.burned.title.accent',
                    message: 'we never make you say.',
                    description: 'Market making section title accent words',
                  })}
                </span>
              ),
            }}>
            {'The three sentences {accent}'}
          </Translate>
        }>
        <FeatureGrid features={NEVER} columns={3} />
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.quoteCard}>
          <div className={styles.quoteMark} aria-hidden="true">
            &ldquo;
          </div>
          <p className={styles.quoteText}>
            <Translate
              id="pages.marketMaking.quote.text"
              description="Market making customer quote"
              values={{
                from: <span className="ng-text-frost">1.4%</span>,
                to: <span className="ng-text-frost">7 bps</span>,
              }}>
              {
                'From {from} spread to under {to} in a week. We stopped having liquidity meetings.'
              }
            </Translate>
          </p>
          <div className={styles.quoteMeta}>
            <b>
              <Translate
                id="pages.marketMaking.quote.role"
                description="Market making customer quote role">
                Head of Treasury
              </Translate>
            </b>
            <Translate
              id="pages.marketMaking.quote.meta"
              description="Market making customer quote meta">
              {' · L1 protocol · $180M FDV'}
            </Translate>
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title={
          <Translate
            id="pages.marketMaking.cta.title"
            description="Market making CTA title"
            values={{
              accent: (
                <span className="ng-text-frost">
                  {translate({
                    id: 'pages.marketMaking.cta.title.accent',
                    message: 'A proposal in 48h.',
                    description: 'Market making CTA title accent words',
                  })}
                </span>
              ),
            }}>
            {'A 30-min call. {accent}'}
          </Translate>
        }
        description={translate({
          id: 'pages.marketMaking.cta.description',
          message:
            'Talk to us about your token, your venues and your liquidity targets.',
          description: 'Market making CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.marketMaking.cta.action.call',
              message: 'Book a call',
              description: 'Market making CTA action label',
            }),
            to: 'mailto:contact@octobot.cloud',
          },
          {
            label: translate({
              id: 'pages.marketMaking.cta.action.docs',
              message: 'Read the engine docs',
              description: 'Market making CTA action label',
            }),
            to: '/features/market-making',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
