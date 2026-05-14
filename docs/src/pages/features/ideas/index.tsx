import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  CTABand,
  type Feature,
} from '@site/src/components/landing';
import styles from '@site/src/components/pages/ideas/styles.module.css';

/*
 * Hub page — route: /features/ideas
 *
 * Index for the SEO "ideas" landing pages. Exists so the ~24 leaf pages under
 * this directory are internally linked from one place (the leaf pages also
 * cross-link each other). Grouped by the three product areas they target:
 * the OctoBot App, Market Making, and Whitelabel.
 */

const APP: Feature[] = [
  {
    icon: '📆',
    title: translate({
      id: 'pages.ideas.hub.app.dca.title',
      message: 'DCA bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.dca.description',
      message: 'Automate recurring crypto buys on a fixed schedule.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/dca-bot',
  },
  {
    icon: '▦',
    title: translate({
      id: 'pages.ideas.hub.app.grid.title',
      message: 'Grid trading bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.grid.description',
      message: 'Turn range-bound price action into repeated small profits.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/grid-trading-bot',
  },
  {
    icon: '🎓',
    title: translate({
      id: 'pages.ideas.hub.app.beginners.title',
      message: 'Trading bot for beginners',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.beginners.description',
      message: 'Start with ready-made strategies and no code.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/crypto-trading-bot-for-beginners',
  },
  {
    icon: '🧪',
    title: translate({
      id: 'pages.ideas.hub.app.paper.title',
      message: 'Paper trading',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.paper.description',
      message: 'Practise a strategy on a simulated balance, zero risk.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/paper-trading',
  },
  {
    icon: '⏪',
    title: translate({
      id: 'pages.ideas.hub.app.backtesting.title',
      message: 'Backtesting',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.backtesting.description',
      message: 'Test a strategy on historical data before going live.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/backtesting',
  },
  {
    icon: '🆓',
    title: translate({
      id: 'pages.ideas.hub.app.free.title',
      message: 'Free crypto trading bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.app.free.description',
      message: 'Open source, self-hosted, no paywalled core features.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/free-crypto-trading-bot',
  },
];

const MARKET_MAKING: Feature[] = [
  {
    icon: '💧',
    title: translate({
      id: 'pages.ideas.hub.mm.mmaas.title',
      message: 'Market making as a service',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.mmaas.description',
      message: 'Professional liquidity delivered as a managed service.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/market-making-as-a-service',
  },
  {
    icon: '🤝',
    title: translate({
      id: 'pages.ideas.hub.mm.provider.title',
      message: 'Crypto liquidity provider',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.provider.description',
      message: 'Post continuous two-sided quotes so a market has depth.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/crypto-liquidity-provider',
  },
  {
    icon: '🪙',
    title: translate({
      id: 'pages.ideas.hub.mm.token.title',
      message: 'Token liquidity',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.token.description',
      message: 'Deepen the order book behind your token.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/token-liquidity',
  },
  {
    icon: '📊',
    title: translate({
      id: 'pages.ideas.hub.mm.score.title',
      message: 'Liquidity score',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.score.description',
      message: 'One number for how healthy a market’s liquidity is.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/liquidity-score',
  },
  {
    icon: '🤖',
    title: translate({
      id: 'pages.ideas.hub.mm.bot.title',
      message: 'Market making bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.bot.description',
      message: 'The open-source bot that quotes both sides of a book.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/market-making-bot',
  },
  {
    icon: '🏦',
    title: translate({
      id: 'pages.ideas.hub.mm.cex.title',
      message: 'CEX market making',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.cex.description',
      message: 'Order-book market making on centralized exchanges.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/cex-market-making',
  },
  {
    icon: '🔗',
    title: translate({
      id: 'pages.ideas.hub.mm.dex.title',
      message: 'DEX market making',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.dex.description',
      message: 'How AMM liquidity differs from order-book market making.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/dex-market-making',
  },
  {
    icon: '📌',
    title: translate({
      id: 'pages.ideas.hub.mm.designated.title',
      message: 'Designated market maker',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.designated.description',
      message: 'Formal spread, depth and uptime commitments for a listing.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/designated-market-maker',
  },
  {
    icon: '⛏️',
    title: translate({
      id: 'pages.ideas.hub.mm.mining.title',
      message: 'Liquidity mining bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.mm.mining.description',
      message: 'Keep qualifying orders live for exchange reward programs.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/liquidity-mining-bot',
  },
];

const WHITELABEL: Feature[] = [
  {
    icon: '🏷️',
    title: translate({
      id: 'pages.ideas.hub.wl.platform.title',
      message: 'White label trading platform',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.platform.description',
      message: 'A complete rebrandable platform in your own infrastructure.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/white-label-crypto-trading-platform',
  },
  {
    icon: '🤖',
    title: translate({
      id: 'pages.ideas.hub.wl.bot.title',
      message: 'White label trading bot',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.bot.description',
      message: 'License the bot engine and ship it under your brand.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/white-label-trading-bot',
  },
  {
    icon: '🔌',
    title: translate({
      id: 'pages.ideas.hub.wl.api.title',
      message: 'Trading platform API',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.api.description',
      message: 'Drive the trading engine programmatically from your code.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/trading-platform-api',
  },
  {
    icon: '▢',
    title: translate({
      id: 'pages.ideas.hub.wl.widget.title',
      message: 'Embeddable trading widget',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.widget.description',
      message: 'A drop-in widget for automated trading inside your product.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/embeddable-trading-widget',
  },
  {
    icon: '🛠️',
    title: translate({
      id: 'pages.ideas.hub.wl.builder.title',
      message: 'Crypto trading app builder',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.builder.description',
      message: 'Build your own branded trading app on the engine.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/crypto-trading-app-builder',
  },
  {
    icon: '🏛️',
    title: translate({
      id: 'pages.ideas.hub.wl.braas.title',
      message: 'Brokerage as a service',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.braas.description',
      message: 'Trading infrastructure for fintechs, without building it.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/brokerage-as-a-service',
  },
  {
    icon: '💳',
    title: translate({
      id: 'pages.ideas.hub.wl.fintechs.title',
      message: 'For fintechs',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.fintechs.description',
      message: 'A trading platform that runs in your own tenancy.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/trading-platform-for-fintechs',
  },
  {
    icon: '📈',
    title: translate({
      id: 'pages.ideas.hub.wl.assetManagers.title',
      message: 'For asset managers',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.assetManagers.description',
      message: 'Operate and own the whole trading stack.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/trading-platform-for-asset-managers',
  },
  {
    icon: '🪙',
    title: translate({
      id: 'pages.ideas.hub.wl.neobanks.title',
      message: 'For neobanks',
      description: 'Ideas hub card title',
    }),
    description: translate({
      id: 'pages.ideas.hub.wl.neobanks.description',
      message: 'Ship a polished wealth product inside your perimeter.',
      description: 'Ideas hub card description',
    }),
    to: '/features/ideas/trading-platform-for-neobanks',
  },
];

export default function IdeasHubPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.ideas.hub.meta.title',
        message: 'OctoBot use cases & ideas',
        description: 'Ideas hub page meta title',
      })}
      description={translate({
        id: 'pages.ideas.hub.meta.description',
        message:
          'Explore what you can build with OctoBot — automated trading strategies, crypto market making, and whitelabel trading infrastructure.',
        description: 'Ideas hub page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.ideas.hub.hero.eyebrow',
          message: 'Use cases',
          description: 'Ideas hub hero eyebrow',
        })}
        title={
          <Translate
            id="pages.ideas.hub.hero.title"
            description="Ideas hub hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.ideas.hub.hero.title.accent',
                    message: 'with OctoBot.',
                    description: 'Ideas hub hero title accent',
                  })}
                </span>
              ),
            }}>
            {'Everything you can build {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.ideas.hub.hero.subtitle',
          message:
            'From a first DCA bot to whitelabel trading infrastructure — short, focused pages on each use case OctoBot covers.',
          description: 'Ideas hub hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.ideas.hub.hero.action.create',
              message: 'Create your OctoBot',
              description: 'Ideas hub hero action label',
            }),
            to: 'https://www.octobot.cloud',
          },
          {
            label: translate({
              id: 'pages.ideas.hub.hero.action.app',
              message: 'See the OctoBot App',
              description: 'Ideas hub hero action label',
            }),
            to: '/features/octobot-app',
            variant: 'ghost',
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'pages.ideas.hub.app.eyebrow',
          message: 'Automated investing',
          description: 'Ideas hub section eyebrow',
        })}
        title={translate({
          id: 'pages.ideas.hub.app.title',
          message: 'Trading bots & strategies',
          description: 'Ideas hub section title',
        })}
        lead={translate({
          id: 'pages.ideas.hub.app.lead',
          message:
            'Ways to put your own crypto trading on autopilot with the OctoBot App.',
          description: 'Ideas hub section lead',
        })}>
        <FeatureGrid features={APP} columns={3} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.ideas.hub.mm.eyebrow',
          message: 'Liquidity',
          description: 'Ideas hub section eyebrow',
        })}
        title={translate({
          id: 'pages.ideas.hub.mm.title',
          message: 'Market making & liquidity',
          description: 'Ideas hub section title',
        })}
        lead={translate({
          id: 'pages.ideas.hub.mm.lead',
          message:
            'For crypto projects and exchanges that need depth on their order books.',
          description: 'Ideas hub section lead',
        })}>
        <FeatureGrid features={MARKET_MAKING} columns={3} />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'pages.ideas.hub.wl.eyebrow',
          message: 'Infrastructure',
          description: 'Ideas hub section eyebrow',
        })}
        title={translate({
          id: 'pages.ideas.hub.wl.title',
          message: 'Whitelabel & platform',
          description: 'Ideas hub section title',
        })}
        lead={translate({
          id: 'pages.ideas.hub.wl.lead',
          message:
            'Run the whole trading platform under your own brand and infrastructure.',
          description: 'Ideas hub section lead',
        })}>
        <FeatureGrid features={WHITELABEL} columns={3} />
      </Section>

      <CTABand
        title={translate({
          id: 'pages.ideas.hub.cta.title',
          message: 'Find the OctoBot that fits',
          description: 'Ideas hub CTA title',
        })}
        description={translate({
          id: 'pages.ideas.hub.cta.description',
          message:
            'Create a free OctoBot, or talk to the team about market making and whitelabel deployments.',
          description: 'Ideas hub CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.ideas.hub.cta.action.create',
              message: 'Create your OctoBot',
              description: 'Ideas hub CTA action label',
            }),
            to: 'https://www.octobot.cloud',
          },
          {
            label: translate({
              id: 'pages.ideas.hub.cta.action.contact',
              message: 'Talk to the team',
              description: 'Ideas hub CTA action label',
            }),
            to: 'mailto:contact@octobot.cloud',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
