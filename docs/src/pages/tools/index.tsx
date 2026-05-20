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
import styles from './index.module.css';

/*
 * Crypto tools hub — route: /tools.
 *
 * Landing page for the OctoBot free tools, migrated from the OctoBot App
 * marketing site into the Neo Glass Dark landing toolkit. Built the same way
 * as the feature pages: a navbar-less LandingLayout composed entirely from
 * reusable components.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

const TOOLS: Feature[] = [
  {
    icon: '🧠',
    title: translate({
      id: 'tools.hub.tools.prediction.title',
      message: 'ChatGPT crypto predictions',
      description: 'Tools hub card title for ChatGPT predictions',
    }),
    description: translate({
      id: 'tools.hub.tools.prediction.description',
      message:
        'OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals.',
      description: 'Tools hub card description for ChatGPT predictions',
    }),
    to: '/tools/crypto-prediction',
  },
  {
    icon: '🔺',
    title: translate({
      id: 'tools.hub.tools.arbitrage.title',
      message: 'Crypto triangular arbitrage',
      description: 'Tools hub card title for triangular arbitrage',
    }),
    description: translate({
      id: 'tools.hub.tools.arbitrage.description',
      message:
        'Triangular arbitrage on crypto exchanges is a strategy to profit from price differences between three cryptocurrencies by executing quick trades.',
      description: 'Tools hub card description for triangular arbitrage',
    }),
    to: '/tools/triangular-arbitrage-crypto',
  },
  {
    icon: '⚡',
    title: translate({
      id: 'tools.hub.tools.scalping.title',
      message: 'Scalping signals',
      description: 'Tools hub card title for scalping signals',
    }),
    description: translate({
      id: 'tools.hub.tools.scalping.description',
      message:
        'Scalping is a quick trading technique involving many small transactions to capitalize on slight price movements — frequent, modest profits.',
      description: 'Tools hub card description for scalping signals',
    }),
    to: '/tools/scalping-signals',
  },
  {
    icon: '🏆',
    title: translate({
      id: 'tools.hub.tools.ranking.title',
      message: 'Cryptocurrencies ranking',
      description: 'Tools hub card title for cryptocurrencies ranking',
    }),
    description: translate({
      id: 'tools.hub.tools.ranking.description',
      message: 'Cryptocurrency rankings by market cap, powered by Coingecko data.',
      description: 'Tools hub card description for cryptocurrencies ranking',
    }),
    to: '/tools/crypto-ranking',
  },
  {
    icon: '💱',
    title: translate({
      id: 'tools.hub.tools.converter.title',
      message: 'Crypto converters',
      description: 'Tools hub card title for crypto converters',
    }),
    description: translate({
      id: 'tools.hub.tools.converter.description',
      message:
        'Convert between any crypto and fiat with live prices, market data and conversion tables.',
      description: 'Tools hub card description for crypto converters',
    }),
    to: '/tools/converter',
  },
];

export default function ToolsHub(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'tools.hub.layout.title',
        message: 'Crypto tools',
        description: 'Tools hub page meta title',
      })}
      description={translate({
        id: 'tools.hub.layout.description',
        message:
          'A set of free crypto tools to research the market and sharpen your strategy — ChatGPT predictions, scalping signals, rankings, arbitrage and converters.',
        description: 'Tools hub page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.hub.hero.eyebrow',
          message: 'Free crypto tools',
          description: 'Tools hub hero eyebrow',
        })}
        title={
          <Translate
            id="tools.hub.hero.title"
            description="Tools hub hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="tools.hub.hero.title.accent"
                    description="Tools hub hero title accent">
                    sharpen your strategy.
                  </Translate>
                </span>
              ),
            }}>
            {'Free crypto tools to {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'tools.hub.hero.subtitle',
          message:
            'A set of free tools to research the market and sharpen your strategy — predictions, signals, rankings and converters.',
          description: 'Tools hub hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.hub.hero.action.invest',
              message: 'Invest for free',
              description: 'Tools hub hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.hub.hero.action.guides',
              message: 'Read the guides',
              description: 'Tools hub hero guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.hub.hero.meta.free',
              message: 'Free to use',
              description: 'Tools hub hero meta: free to use',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.hub.hero.meta.liveData',
              message: 'Live market data',
              description: 'Tools hub hero meta: live market data',
            }),
          },
          {
            label: translate({
              id: 'tools.hub.hero.meta.noAccount',
              message: 'No account required',
              description: 'Tools hub hero meta: no account required',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.hub.toolbox.eyebrow',
          message: 'Toolbox',
          description: 'Tools hub toolbox section eyebrow',
        })}
        title={translate({
          id: 'tools.hub.toolbox.title',
          message: 'Five tools to research the market',
          description: 'Tools hub toolbox section title',
        })}
        lead={translate({
          id: 'tools.hub.toolbox.lead',
          message:
            'Each tool digs into a different corner of the crypto market — from AI predictions to live price conversion. Pick one and start exploring.',
          description: 'Tools hub toolbox section lead',
        })}>
        <FeatureGrid features={TOOLS} columns={3} />
      </Section>

      <CTABand
        title={translate({
          id: 'tools.hub.cta.title',
          message: 'Put these tools to work on your portfolio',
          description: 'Tools hub CTA band title',
        })}
        description={translate({
          id: 'tools.hub.cta.description',
          message:
            'Create your trading bot for free on OctoBot App, or read the guides first.',
          description: 'Tools hub CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.hub.cta.action.invest',
              message: 'Invest for free',
              description: 'Tools hub CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.hub.cta.action.guides',
              message: 'Read the guides',
              description: 'Tools hub CTA guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
