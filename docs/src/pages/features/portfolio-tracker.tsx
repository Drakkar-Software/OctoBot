import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StatStrip,
  BeforeAfter,
  IconList,
  LogoRibbon,
  FAQ,
  CTABand,
  type Feature,
  type Stat,
  type IconListItem,
  type FAQItem,
} from '@site/src/components/landing';
import styles from './_styles.module.css';

/*
 * Crypto Portfolio Tracker feature page — route: /features/portfolio-tracker.
 *
 * SEO landing page targeting the "crypto portfolio tracker" cluster:
 * multi-exchange / automated / open-source / real-time PnL. Built the same
 * way as the other src/pages/features/*.tsx pages — a navbar-less
 * LandingLayout composed entirely from the Neo Glass Dark landing toolkit.
 */

const CLOUD = 'https://www.octobot.cloud';
const GITHUB = 'https://github.com/Drakkar-Software/OctoBot';

const TRACKS: Feature[] = [
  {
    icon: '📊',
    title: translate({
      id: 'features.portfolioTracker.tracks.value.title',
      message: 'Live portfolio value',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.value.description',
      message:
        'See the total value of every holding across all your connected exchanges, refreshed in real time.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
  {
    icon: '📈',
    title: translate({
      id: 'features.portfolioTracker.tracks.pnl.title',
      message: 'Real-time PnL',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.pnl.description',
      message:
        'Track profit and loss as it happens — per asset, per strategy and for the whole portfolio.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
  {
    icon: '🧾',
    title: translate({
      id: 'features.portfolioTracker.tracks.history.title',
      message: 'Profit history',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.history.description',
      message:
        'A full historical record of your portfolio value and realized profits, charted over time.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
  {
    icon: '🪙',
    title: translate({
      id: 'features.portfolioTracker.tracks.holdings.title',
      message: 'Holdings breakdown',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.holdings.description',
      message:
        'Every coin you hold, its share of the portfolio and where it sits — no manual spreadsheet.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
  {
    icon: '🔀',
    title: translate({
      id: 'features.portfolioTracker.tracks.multiExchange.title',
      message: 'Multi-exchange aggregation',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.multiExchange.description',
      message:
        'Connect several exchange accounts and watch them as one consolidated portfolio.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
  {
    icon: '🤖',
    title: translate({
      id: 'features.portfolioTracker.tracks.strategies.title',
      message: 'Tied to your strategies',
      description: 'Track feature title on portfolio tracker page',
    }),
    description: translate({
      id: 'features.portfolioTracker.tracks.strategies.description',
      message:
        'Because OctoBot also trades, every move is attributed — you see what each strategy did to your balance.',
      description: 'Track feature description on portfolio tracker page',
    }),
  },
];

const STATS: Stat[] = [
  {
    value: '15+',
    label: translate({
      id: 'features.portfolioTracker.stats.exchanges.label',
      message: 'Exchanges you can connect',
      description: 'Stat label on portfolio tracker page',
    }),
  },
  {
    value: translate({
      id: 'features.portfolioTracker.stats.realtime.value',
      message: 'Real-time',
      description: 'Stat value on portfolio tracker page',
    }),
    label: translate({
      id: 'features.portfolioTracker.stats.realtime.label',
      message: 'Portfolio & PnL refresh',
      description: 'Stat label on portfolio tracker page',
    }),
  },
  {
    value: '100%',
    label: translate({
      id: 'features.portfolioTracker.stats.openSource.label',
      message: 'Open source — audit every line',
      description: 'Stat label on portfolio tracker page',
    }),
  },
  {
    value: translate({
      id: 'features.portfolioTracker.stats.keys.value',
      message: 'Your keys',
      description: 'Stat value on portfolio tracker page',
    }),
    label: translate({
      id: 'features.portfolioTracker.stats.keys.label',
      message: 'API keys never leave your control',
      description: 'Stat label on portfolio tracker page',
    }),
  },
];

const WHY: IconListItem[] = [
  {
    icon: '🔑',
    text: (
      <Translate
        id="features.portfolioTracker.why.selfCustody"
        description="Why list item on portfolio tracker page"
        values={{label: <strong>Self-custody:</strong>}}>
        {
          '{label} you connect read-and-trade API keys you own — OctoBot never holds your funds.'
        }
      </Translate>
    ),
  },
  {
    icon: '🧩',
    text: (
      <Translate
        id="features.portfolioTracker.why.openSource"
        description="Why list item on portfolio tracker page"
        values={{
          label: <strong>Open source:</strong>,
          githubLink: <a href={GITHUB}>GitHub</a>,
        }}>
        {
          '{label} the tracker is part of OctoBot — the whole codebase is public on {githubLink}.'
        }
      </Translate>
    ),
  },
  {
    icon: '⚡',
    text: (
      <Translate
        id="features.portfolioTracker.why.automated"
        description="Why list item on portfolio tracker page"
        values={{label: <strong>Automated:</strong>}}>
        {
          '{label} it is not a passive viewer — the same bot that tracks your portfolio can also act on it.'
        }
      </Translate>
    ),
  },
  {
    icon: '🖥️',
    text: (
      <Translate
        id="features.portfolioTracker.why.selfHosted"
        description="Why list item on portfolio tracker page"
        values={{label: <strong>Self-hosted or cloud:</strong>}}>
        {
          '{label} run it on your own machine or use OctoBot Cloud — the portfolio data stays yours either way.'
        }
      </Translate>
    ),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q1.question',
      message: 'What is a crypto portfolio tracker?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: translate({
      id: 'features.portfolioTracker.faq.q1.answer',
      message:
        'A crypto portfolio tracker aggregates the assets you hold across exchanges and wallets into a single view, showing total value, allocation and profit or loss over time. OctoBot does this automatically from the exchange accounts you connect.',
      description: 'FAQ answer on portfolio tracker page',
    }),
  },
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q2.question',
      message: 'Is the OctoBot portfolio tracker free?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: (
      <Translate
        id="features.portfolioTracker.faq.q2.answer"
        description="FAQ answer on portfolio tracker page"
        values={{githubLink: <a href={GITHUB}>GitHub</a>}}>
        {
          'Yes — OctoBot is free and open source. You can download it from {githubLink} and track your portfolio at no cost, or use OctoBot Cloud for a hosted experience.'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q3.question',
      message: 'Can it track multiple exchanges at once?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: translate({
      id: 'features.portfolioTracker.faq.q3.answer',
      message:
        'Yes. Connect several exchange accounts and OctoBot consolidates them into one portfolio view, so you see your total holdings and PnL without switching between exchange apps.',
      description: 'FAQ answer on portfolio tracker page',
    }),
  },
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q4.question',
      message: 'Does it have access to my funds?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: translate({
      id: 'features.portfolioTracker.faq.q4.answer',
      message:
        'No. OctoBot connects with the API keys you create on your own exchange account. Your funds and keys stay under your control — OctoBot is self-custody by design.',
      description: 'FAQ answer on portfolio tracker page',
    }),
  },
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q5.question',
      message: 'How is this different from a regular portfolio tracker app?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: translate({
      id: 'features.portfolioTracker.faq.q5.answer',
      message:
        'Most trackers only show numbers. OctoBot is a trading bot first, so the portfolio it tracks is the portfolio it can also manage — every change in value is tied to a strategy you can inspect, backtest and adjust.',
      description: 'FAQ answer on portfolio tracker page',
    }),
  },
  {
    question: translate({
      id: 'features.portfolioTracker.faq.q6.question',
      message: 'Which exchanges are supported?',
      description: 'FAQ question on portfolio tracker page',
    }),
    answer: (
      <Translate
        id="features.portfolioTracker.faq.q6.answer"
        description="FAQ answer on portfolio tracker page"
        values={{
          exchangesLink: (
            <Link to="/supported-exchanges">
              <Translate
                id="features.portfolioTracker.faq.q6.answerLink"
                description="FAQ answer link text on portfolio tracker page">
                supported exchanges page
              </Translate>
            </Link>
          ),
        }}>
        {
          'OctoBot connects to 15+ major exchanges including Binance, Kucoin, Coinbase, MEXC and more. See the full list on the {exchangesLink}.'
        }
      </Translate>
    ),
  },
];

export default function PortfolioTrackerFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.portfolioTracker.layout.title',
        message: 'Crypto Portfolio Tracker — open source & multi-exchange',
        description: 'Page meta title for portfolio tracker page',
      })}
      description={translate({
        id: 'features.portfolioTracker.layout.description',
        message:
          'Track your crypto portfolio across every exchange in real time with OctoBot — an open-source, self-custody portfolio tracker tied to automated trading.',
        description: 'Page meta description for portfolio tracker page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.portfolioTracker.hero.eyebrow',
          message: 'Portfolio tracker',
          description: 'Hero eyebrow on portfolio tracker page',
        })}
        title={
          <Translate
            id="features.portfolioTracker.hero.title"
            description="Hero title on portfolio tracker page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.portfolioTracker.hero.accent"
                    description="Accent text in hero title on portfolio tracker page">
                    tracked in real time.
                  </Translate>
                </span>
              ),
            }}>
            {'Your whole crypto portfolio, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.portfolioTracker.hero.subtitle',
          message:
            'OctoBot aggregates every exchange account you connect into one live portfolio — value, holdings and PnL, automatically and open source.',
          description: 'Hero subtitle on portfolio tracker page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.portfolioTracker.hero.action.start',
              message: 'Start tracking',
              description: 'Hero action label on portfolio tracker page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.portfolioTracker.hero.action.github',
              message: 'Get it on GitHub',
              description: 'Hero action label on portfolio tracker page',
            }),
            to: GITHUB,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.portfolioTracker.hero.meta.multiExchange',
              message: 'Multi-exchange',
              description: 'Hero meta label on portfolio tracker page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.portfolioTracker.hero.meta.pnl',
              message: 'Real-time PnL',
              description: 'Hero meta label on portfolio tracker page',
            }),
          },
          {
            label: translate({
              id: 'features.portfolioTracker.hero.meta.openSource',
              message: 'Open source',
              description: 'Hero meta label on portfolio tracker page',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'features.portfolioTracker.tracks.eyebrow',
          message: 'What it tracks',
          description: 'Section eyebrow on portfolio tracker page',
        })}
        title={translate({
          id: 'features.portfolioTracker.tracks.title',
          message: 'Everything you hold, in one view',
          description: 'Section title on portfolio tracker page',
        })}
        lead={translate({
          id: 'features.portfolioTracker.tracks.lead',
          message:
            'OctoBot reads your connected exchange accounts and turns them into a single, always-current portfolio.',
          description: 'Section lead on portfolio tracker page',
        })}>
        <FeatureGrid features={TRACKS} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.portfolioTracker.atAGlance.eyebrow',
          message: 'At a glance',
          description: 'Section eyebrow on portfolio tracker page',
        })}>
        <StatStrip
          head={{
            eyebrow: translate({
              id: 'features.portfolioTracker.atAGlance.head.eyebrow',
              message: 'Why OctoBot',
              description: 'StatStrip eyebrow on portfolio tracker page',
            }),
            title: translate({
              id: 'features.portfolioTracker.atAGlance.head.title',
              message: 'A tracker that does more than watch',
              description: 'StatStrip title on portfolio tracker page',
            }),
          }}
          stats={STATS}
        />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.portfolioTracker.different.eyebrow',
          message: "Why it's different",
          description: 'Section eyebrow on portfolio tracker page',
        })}
        title={translate({
          id: 'features.portfolioTracker.different.title',
          message: 'Not just a dashboard — a tracker you control',
          description: 'Section title on portfolio tracker page',
        })}
        lead={translate({
          id: 'features.portfolioTracker.different.lead',
          message:
            'Most portfolio trackers ask for your keys and show you a number. OctoBot is open source, self-custody, and built around the strategies that move your balance.',
          description: 'Section lead on portfolio tracker page',
        })}>
        <IconList items={WHY} />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'features.portfolioTracker.beforeAfter.eyebrow',
          message: 'The difference',
          description: 'Section eyebrow on portfolio tracker page',
        })}
        title={
          <Translate
            id="features.portfolioTracker.beforeAfter.title"
            description="Section title on portfolio tracker page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.portfolioTracker.beforeAfter.accent"
                    description="Accent text in before-after title on portfolio tracker page">
                    a portfolio that works for you.
                  </Translate>
                </span>
              ),
            }}>
            {'A spreadsheet of balances vs. {accent}'}
          </Translate>
        }>
        <BeforeAfter
          before={{
            label: translate({
              id: 'features.portfolioTracker.beforeAfter.before.label',
              message: 'Typical tracker app',
              description:
                'BeforeAfter before label on portfolio tracker page',
            }),
            items: [
              <Translate
                id="features.portfolioTracker.beforeAfter.before.item1"
                description="BeforeAfter before item on portfolio tracker page"
                values={{strong: <strong>Manual or read-only</strong>}}>
                {'{strong} — you watch, nothing acts'}
              </Translate>,
              <Translate
                id="features.portfolioTracker.beforeAfter.before.item2"
                description="BeforeAfter before item on portfolio tracker page"
                values={{
                  strong: (
                    <strong>API keys live on someone's server</strong>
                  ),
                }}>
                {'Your {strong}'}
              </Translate>,
              <Translate
                id="features.portfolioTracker.beforeAfter.before.item3"
                description="BeforeAfter before item on portfolio tracker page"
                values={{strong: <strong>closed black box</strong>}}>
                {"A {strong} — trust it or don't"}
              </Translate>,
            ],
          }}
          after={{
            label: translate({
              id: 'features.portfolioTracker.beforeAfter.after.label',
              message: 'With OctoBot',
              description:
                'BeforeAfter after label on portfolio tracker page',
            }),
            items: [
              <Translate
                id="features.portfolioTracker.beforeAfter.after.item1"
                description="BeforeAfter after item on portfolio tracker page"
                values={{strong: <strong>Tracks and trades</strong>}}>
                {'{strong} — strategies act on the portfolio'}
              </Translate>,
              <Translate
                id="features.portfolioTracker.beforeAfter.after.item2"
                description="BeforeAfter after item on portfolio tracker page"
                values={{strong: <strong>Self-custody</strong>}}>
                {'{strong} — your keys, your machine or cloud'}
              </Translate>,
              <Translate
                id="features.portfolioTracker.beforeAfter.after.item3"
                description="BeforeAfter after item on portfolio tracker page"
                values={{strong: <strong>Open source</strong>}}>
                {'{strong} — every line is auditable'}
              </Translate>,
            ],
          }}
        />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.portfolioTracker.exchanges.eyebrow',
          message: 'Exchanges',
          description: 'Section eyebrow on portfolio tracker page',
        })}
        title={
          <Translate
            id="features.portfolioTracker.exchanges.title"
            description="Section title on portfolio tracker page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.portfolioTracker.exchanges.accent"
                    description="Accent text in exchanges title on portfolio tracker page">
                    exchanges you already use.
                  </Translate>
                </span>
              ),
            }}>
            {'Track your assets on the {accent}'}
          </Translate>
        }>
        <LogoRibbon
          items={[
            'BINANCE',
            'KUCOIN',
            'COINBASE',
            'MEXC',
            'BITGET',
            'HTX',
            'CRYPTO.COM',
            'OKX',
            '+ MORE',
          ]}
        />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.portfolioTracker.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on portfolio tracker page',
        })}
        title={translate({
          id: 'features.portfolioTracker.faq.title',
          message: 'Crypto portfolio tracker FAQ',
          description: 'FAQ section title on portfolio tracker page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.portfolioTracker.cta.title',
          message: 'Stop checking five exchange apps.',
          description: 'CTA band title on portfolio tracker page',
        })}
        description={translate({
          id: 'features.portfolioTracker.cta.description',
          message:
            'Connect your accounts to OctoBot and watch your whole crypto portfolio in one place — free and open source.',
          description: 'CTA band description on portfolio tracker page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.portfolioTracker.cta.action.start',
              message: 'Start tracking',
              description: 'CTA action label on portfolio tracker page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.portfolioTracker.cta.action.guides',
              message: 'Read the guides',
              description: 'CTA action label on portfolio tracker page',
            }),
            to: '/guides/octobot',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
