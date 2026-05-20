import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  LogoRibbon,
  StatStrip,
  IconList,
  CTABand,
  type Feature,
  type Stat,
  type IconListItem,
} from '@site/src/components/landing';
import WhyTabs from '@site/src/components/pages/trading-bot/WhyTabs';
import styles from './trading-bot.module.css';

/*
 * Trading bot marketing page — route: /trading-bot.
 *
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit: a navbar-less LandingLayout composed from reusable
 * landing components plus the page-local WhyTabs switcher.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDE = '/guides/octobot';
const REPO = 'https://github.com/Drakkar-Software/OctoBot';

const EXCHANGES: ReactNode[] = [
  'BINANCE',
  'COINBASE',
  'KRAKEN',
  'KUCOIN',
  'BYBIT',
  'OKX',
  'BITGET',
  'GATE.IO',
  'HTX',
  'MEXC',
  translate({
    id: 'pages.tradingBot.exchanges.more',
    message: '+ MORE',
    description: 'Logo ribbon "and more" entry',
  }),
];

const STRATEGIES: Feature[] = [
  {
    icon: '📊',
    title: translate({
      id: 'pages.tradingBot.strategies.indicators.title',
      message: 'Technical & AI indicators',
      description: 'Trading bot strategy title',
    }),
    description: translate({
      id: 'pages.tradingBot.strategies.indicators.description',
      message:
        'Use technical indicators such as RSI, MACD, moving averages or ADX to configure your strategies, and integrate ChatGPT or custom AI predictions.',
      description: 'Trading bot strategy description',
    }),
  },
  {
    icon: '💵',
    title: translate({
      id: 'pages.tradingBot.strategies.dca.title',
      message: 'Smart DCA trading',
      description: 'Trading bot strategy title',
    }),
    description: translate({
      id: 'pages.tradingBot.strategies.dca.description',
      message:
        'Highly optimized Dollar Cost Averaging — automate entries and exits with as many orders as you want, for long or short-term DCA.',
      description: 'Trading bot strategy description',
    }),
  },
  {
    icon: '🔲',
    title: translate({
      id: 'pages.tradingBot.strategies.grid.title',
      message: 'Advanced grid trading',
      description: 'Trading bot strategy title',
    }),
    description: translate({
      id: 'pages.tradingBot.strategies.grid.description',
      message:
        'Profit from sideways markets with fine-tuned grid strategies on any pair and exchange.',
      description: 'Trading bot strategy description',
    }),
  },
  {
    icon: '📈',
    title: translate({
      id: 'pages.tradingBot.strategies.tradingview.title',
      message: 'TradingView strategies',
      description: 'Trading bot strategy title',
    }),
    description: translate({
      id: 'pages.tradingBot.strategies.tradingview.description',
      message:
        'Automate your TradingView strategies or indicator signals on any exchange — create or cancel orders the moment an alert fires.',
      description: 'Trading bot strategy description',
    }),
  },
];

const STATS: Stat[] = [
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: translate({
      id: 'pages.tradingBot.stats.running.label',
      message: 'OctoBots running',
      description: 'Trading bot stat label',
    }),
    sub: translate({
      id: 'pages.tradingBot.stats.running.sub',
      message: 'self-hosted · global',
      description: 'Trading bot stat sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: translate({
      id: 'pages.tradingBot.stats.trades.label',
      message: 'Trades executed',
      description: 'Trading bot stat label',
    }),
    sub: translate({
      id: 'pages.tradingBot.stats.trades.sub',
      message: 'cumulative',
      description: 'Trading bot stat sub',
    }),
  },
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: translate({
      id: 'pages.tradingBot.stats.stars.label',
      message: 'GitHub stars',
      description: 'Trading bot stat label',
    }),
    sub: translate({
      id: 'pages.tradingBot.stats.stars.sub',
      message: 'since 2018',
      description: 'Trading bot stat sub',
    }),
  },
];

const ROADMAP: IconListItem[] = [
  {
    icon: '🧠',
    text: translate({
      id: 'pages.tradingBot.roadmap.strategies',
      message: 'Strategies',
      description: 'Trading bot roadmap item',
    }),
  },
  {
    icon: '🔗',
    text: translate({
      id: 'pages.tradingBot.roadmap.exchanges',
      message: 'Exchanges',
      description: 'Trading bot roadmap item',
    }),
  },
  {
    icon: '🔌',
    text: translate({
      id: 'pages.tradingBot.roadmap.connectivity',
      message: 'Connectivity',
      description: 'Trading bot roadmap item',
    }),
  },
  {
    icon: '✨',
    text: translate({
      id: 'pages.tradingBot.roadmap.other',
      message: 'Other',
      description: 'Trading bot roadmap item',
    }),
  },
];

export default function TradingBotPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.tradingBot.meta.title',
        message: 'Trading bot',
        description: 'Trading bot page metadata title',
      })}
      description={translate({
        id: 'pages.tradingBot.meta.description',
        message:
          'Automate your crypto trading with OctoBot. Easily create, backtest and optimize algorithmic or TradingView trading strategies.',
        description: 'Trading bot page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.tradingBot.hero.eyebrow',
          message: 'Trading bot',
          description: 'Trading bot hero eyebrow',
        })}
        title={
          <Translate
            id="pages.tradingBot.hero.title"
            description="Trading bot hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.tradingBot.hero.title.accent',
                    message: 'OctoBot.',
                    description: 'Trading bot hero title accent word',
                  })}
                </span>
              ),
            }}>
            {'Automate your crypto trading with {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.tradingBot.hero.subtitle',
          message:
            'Easily create, backtest and optimize algorithmic or TradingView trading strategies.',
          description: 'Trading bot hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.tradingBot.hero.action.invest',
              message: 'Invest for free',
              description: 'Trading bot hero action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.tradingBot.hero.action.guides',
              message: 'Read the guides',
              description: 'Trading bot hero action label',
            }),
            to: GUIDE,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'pages.tradingBot.hero.meta.exchanges',
              message: '12+ exchanges',
              description: 'Trading bot hero meta label',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'pages.tradingBot.hero.meta.backtesting',
              message: 'Backtesting included',
              description: 'Trading bot hero meta label',
            }),
          },
          {
            label: translate({
              id: 'pages.tradingBot.hero.meta.openSource',
              message: 'Open source',
              description: 'Trading bot hero meta label',
            }),
          },
        ]}
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.tradingBot.why.eyebrow',
          message: 'Why OctoBot',
          description: 'Trading bot section eyebrow',
        })}
        title={translate({
          id: 'pages.tradingBot.why.title',
          message: 'Why using OctoBot?',
          description: 'Trading bot section title',
        })}
        lead={translate({
          id: 'pages.tradingBot.why.lead',
          message:
            'From hands-off investing to fully custom strategies — OctoBot adapts to how you want to trade.',
          description: 'Trading bot section lead',
        })}>
        <WhyTabs />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.tradingBot.exchangesSection.eyebrow',
          message: 'Exchanges',
          description: 'Trading bot section eyebrow',
        })}
        title={translate({
          id: 'pages.tradingBot.exchangesSection.title',
          message: 'Your bot on the best exchanges',
          description: 'Trading bot section title',
        })}
        lead={translate({
          id: 'pages.tradingBot.exchangesSection.lead',
          message:
            'OctoBot is compatible with leading exchanges to automate your strategies on more than 12 exchanges.',
          description: 'Trading bot section lead',
        })}>
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.tradingBot.strategiesSection.eyebrow',
          message: 'Strategies',
          description: 'Trading bot section eyebrow',
        })}
        title={translate({
          id: 'pages.tradingBot.strategiesSection.title',
          message: 'Built-in trading strategy bases',
          description: 'Trading bot section title',
        })}
        lead={translate({
          id: 'pages.tradingBot.strategiesSection.lead',
          message:
            "OctoBot comes with many built-in strategies you can use as-is or as inspiration — and since it's open source, you can read the code to see how they work.",
          description: 'Trading bot section lead',
        })}>
        <FeatureGrid features={STRATEGIES} columns={2} />
      </Section>

      <Section>
        <StatStrip
          head={{
            eyebrow: translate({
              id: 'pages.tradingBot.community.eyebrow',
              message: 'Community',
              description: 'Trading bot section eyebrow',
            }),
            title: translate({
              id: 'pages.tradingBot.community.title',
              message: 'Used by traders worldwide',
              description: 'Trading bot section title',
            }),
          }}
          stats={STATS}
        />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.tradingBot.roadmapSection.eyebrow',
          message: 'Roadmap',
          description: 'Trading bot section eyebrow',
        })}
        title={translate({
          id: 'pages.tradingBot.roadmapSection.title',
          message: 'Shape the future',
          description: 'Trading bot section title',
        })}
        lead={translate({
          id: 'pages.tradingBot.roadmapSection.lead',
          message: 'Influence the development of OctoBot with your ideas.',
          description: 'Trading bot section lead',
        })}>
        <IconList items={ROADMAP} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={REPO}>
            <Translate
              id="pages.tradingBot.roadmapSection.openRoadmap"
              description="Trading bot open roadmap button">
              Open roadmap
            </Translate>
          </Link>
        </div>
      </Section>

      <CTABand
        title={translate({
          id: 'pages.tradingBot.cta.title',
          message: 'Start automating your crypto trading',
          description: 'Trading bot CTA title',
        })}
        description={translate({
          id: 'pages.tradingBot.cta.description',
          message:
            'Create your trading bot for free on OctoBot App, or read the guides first.',
          description: 'Trading bot CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.tradingBot.cta.action.invest',
              message: 'Invest for free',
              description: 'Trading bot CTA action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.tradingBot.cta.action.guides',
              message: 'Read the guides',
              description: 'Trading bot CTA action label',
            }),
            to: GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
