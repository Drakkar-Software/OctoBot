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
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';

/*
 * Example landing page — route: /welcome
 *
 * Fully custom, no Docusaurus navbar/footer. Copy this file as a template for
 * additional landing pages; swap the content, keep the LandingLayout + section
 * composition. All styling comes from the Neo Glass Dark theme tokens.
 */

const FEATURES: Feature[] = [
  {
    icon: '🧠',
    title: translate({
      id: 'pages.welcome.features.ai.title',
      message: 'AI-assisted strategies',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.ai.description',
      message:
        'Build, backtest and run strategies that adapt to the market — no code required.',
      description: 'Welcome page feature description',
    }),
    to: '/guides/octobot-trading-modes/chatgpt-trading',
  },
  {
    icon: '🔒',
    title: translate({
      id: 'pages.welcome.features.selfCustody.title',
      message: 'Self-custody first',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.selfCustody.description',
      message:
        'Your API keys and wallets never leave your machine. You stay in control.',
      description: 'Welcome page feature description',
    }),
    to: '/blog/how-to-use-a-self-custody-crypto-trading-bot',
  },
  {
    icon: '🧩',
    title: translate({
      id: 'pages.welcome.features.tentacle.title',
      message: 'Tentacle plugin system',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.tentacle.description',
      message:
        'Extend every part of the bot — evaluators, trading modes, interfaces — with tentacles.',
      description: 'Welcome page feature description',
    }),
    to: '/developers/getting-started',
  },
  {
    icon: '📊',
    title: translate({
      id: 'pages.welcome.features.backtesting.title',
      message: 'Backtesting & paper trading',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.backtesting.description',
      message:
        'Validate ideas on historical data or live conditions before risking real funds.',
      description: 'Welcome page feature description',
    }),
    to: '/guides/octobot-usage/backtesting',
  },
  {
    icon: '☁️',
    title: translate({
      id: 'pages.welcome.features.runAnywhere.title',
      message: 'Run anywhere',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.runAnywhere.description',
      message:
        'Self-host on your computer, a Raspberry Pi or a server — or use OctoBot App.',
      description: 'Welcome page feature description',
    }),
    to: '/guides/octobot-installation/install-octobot-on-your-computer',
  },
  {
    icon: '🌍',
    title: translate({
      id: 'pages.welcome.features.openSource.title',
      message: 'Open source',
      description: 'Welcome page feature title',
    }),
    description: translate({
      id: 'pages.welcome.features.openSource.description',
      message:
        'MIT-licensed and community-driven since 2018. Read, audit and shape the code.',
      description: 'Welcome page feature description',
    }),
    to: 'https://github.com/Drakkar-Software/OctoBot',
  },
];

export default function Welcome(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.welcome.meta.title',
        message: 'Welcome to OctoBot',
        description: 'Welcome page metadata title',
      })}
      description={translate({
        id: 'pages.welcome.meta.description',
        message:
          'OctoBot is an open-source, self-custody cryptocurrency trading bot. Automate strategies on centralized and decentralized exchanges.',
        description: 'Welcome page metadata description',
      })}>
      <Hero
        eyebrow={translate({
          id: 'pages.welcome.hero.eyebrow',
          message: 'Open-source crypto trading',
          description: 'Welcome page hero eyebrow',
        })}
        title={
          <>
            <Translate
              id="pages.welcome.hero.title"
              description="Welcome page hero title">
              Automate your crypto strategies,
            </Translate>
            <br />
            <Translate
              id="pages.welcome.hero.title2"
              description="Welcome page hero title second line">
              keep your keys.
            </Translate>
          </>
        }
        subtitle={translate({
          id: 'pages.welcome.hero.subtitle',
          message:
            'OctoBot is a free, open-source trading bot you fully control — from your computer, a server, or the cloud.',
          description: 'Welcome page hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.welcome.hero.action.guides',
              message: 'Read the guides',
              description: 'Welcome page hero action label',
            }),
            to: '/guides/octobot',
          },
          {
            label: translate({
              id: 'pages.welcome.hero.action.features',
              message: 'Explore features',
              description: 'Welcome page hero action label',
            }),
            to: '/features/strategy-designer',
            variant: 'ghost',
          },
          {
            label: translate({
              id: 'pages.welcome.hero.action.github',
              message: 'View on GitHub',
              description: 'Welcome page hero action label',
            }),
            to: 'https://github.com/Drakkar-Software/OctoBot',
            variant: 'surface',
          },
        ]}
        note={translate({
          id: 'pages.welcome.hero.note',
          message: 'MIT licensed · Self-hosted or cloud · Trusted since 2018',
          description: 'Welcome page hero note',
        })}
      />

      <Section
        eyebrow={translate({
          id: 'pages.welcome.why.eyebrow',
          message: 'Why OctoBot',
          description: 'Welcome page section eyebrow',
        })}
        title={translate({
          id: 'pages.welcome.why.title',
          message: 'Everything you need to trade on autopilot',
          description: 'Welcome page section title',
        })}
        lead={translate({
          id: 'pages.welcome.why.lead',
          message:
            'A complete toolkit for building, testing and running automated strategies — without giving up custody.',
          description: 'Welcome page section lead',
        })}>
        <FeatureGrid features={FEATURES} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.welcome.extend.eyebrow',
          message: 'Built to extend',
          description: 'Welcome page section eyebrow',
        })}
        title={translate({
          id: 'pages.welcome.extend.title',
          message: 'One bot, every layer customizable',
          description: 'Welcome page section title',
        })}
        lead={translate({
          id: 'pages.welcome.extend.lead',
          message:
            'Tentacles let you replace or add behavior at every stage of the trading loop.',
          description: 'Welcome page section lead',
        })}
        spacing="sm">
        <GlassCard variant="strong" padded>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center'}}>
            <Badge tone="frost" dot>
              <Translate
                id="pages.welcome.extend.badge.evaluators"
                description="Welcome page extend badge">
                Evaluators
              </Translate>
            </Badge>
            <Badge tone="frost" dot>
              <Translate
                id="pages.welcome.extend.badge.tradingModes"
                description="Welcome page extend badge">
                Trading modes
              </Translate>
            </Badge>
            <Badge tone="frost" dot>
              <Translate
                id="pages.welcome.extend.badge.interfaces"
                description="Welcome page extend badge">
                Interfaces
              </Translate>
            </Badge>
            <Badge tone="frost" dot>
              <Translate
                id="pages.welcome.extend.badge.exchanges"
                description="Welcome page extend badge">
                Exchanges
              </Translate>
            </Badge>
            <Badge tone="pos" dot>
              <Translate
                id="pages.welcome.extend.badge.backtesting"
                description="Welcome page extend badge">
                Backtesting
              </Translate>
            </Badge>
            <Badge tone="warn" dot>
              <Translate
                id="pages.welcome.extend.badge.notifications"
                description="Welcome page extend badge">
                Notifications
              </Translate>
            </Badge>
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title={translate({
          id: 'pages.welcome.cta.title',
          message: 'Start automating in minutes',
          description: 'Welcome page CTA title',
        })}
        description={translate({
          id: 'pages.welcome.cta.description',
          message:
            'Follow the getting-started guide, or jump straight into the developer docs to build your own tentacle.',
          description: 'Welcome page CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.welcome.cta.action.getStarted',
              message: 'Get started',
              description: 'Welcome page CTA action label',
            }),
            to: '/guides/octobot',
          },
          {
            label: translate({
              id: 'pages.welcome.cta.action.devDocs',
              message: 'Developer docs',
              description: 'Welcome page CTA action label',
            }),
            to: '/developers/getting-started',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
