import type {ReactNode} from 'react';
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
    title: 'AI-assisted strategies',
    description:
      'Build, backtest and run strategies that adapt to the market — no code required.',
    to: '/guides/octobot-trading-modes/chatgpt-trading',
  },
  {
    icon: '🔒',
    title: 'Self-custody first',
    description:
      'Your API keys and wallets never leave your machine. You stay in control.',
    to: '/blog/how-to-use-a-self-custody-crypto-trading-bot',
  },
  {
    icon: '🧩',
    title: 'Tentacle plugin system',
    description:
      'Extend every part of the bot — evaluators, trading modes, interfaces — with tentacles.',
    to: '/developers/getting-started',
  },
  {
    icon: '📊',
    title: 'Backtesting & paper trading',
    description:
      'Validate ideas on historical data or live conditions before risking real funds.',
    to: '/guides/octobot-usage/backtesting',
  },
  {
    icon: '☁️',
    title: 'Run anywhere',
    description:
      'Self-host on your computer, a Raspberry Pi or a server — or use OctoBot Cloud.',
    to: '/guides/octobot-installation/install-octobot-on-your-computer',
  },
  {
    icon: '🌍',
    title: 'Open source',
    description:
      'MIT-licensed and community-driven since 2018. Read, audit and shape the code.',
    to: 'https://github.com/Drakkar-Software/OctoBot',
  },
];

export default function Welcome(): ReactNode {
  return (
    <LandingLayout
      title="Welcome to OctoBot"
      description="OctoBot is an open-source, self-custody cryptocurrency trading bot. Automate strategies on centralized and decentralized exchanges.">
      <Hero
        eyebrow="Open-source crypto trading"
        title={
          <>
            Automate your crypto strategies,
            <br />
            keep your keys.
          </>
        }
        subtitle="OctoBot is a free, open-source trading bot you fully control — from your computer, a server, or the cloud."
        actions={[
          {label: 'Read the guides', to: '/guides/octobot'},
          {label: 'Explore features', to: '/features/strategy-designer', variant: 'ghost'},
          {label: 'View on GitHub', to: 'https://github.com/Drakkar-Software/OctoBot', variant: 'surface'},
        ]}
        note="MIT licensed · Self-hosted or cloud · Trusted since 2018"
      />

      <Section
        eyebrow="Why OctoBot"
        title="Everything you need to trade on autopilot"
        lead="A complete toolkit for building, testing and running automated strategies — without giving up custody.">
        <FeatureGrid features={FEATURES} />
      </Section>

      <Section
        eyebrow="Built to extend"
        title="One bot, every layer customizable"
        lead="Tentacles let you replace or add behavior at every stage of the trading loop."
        spacing="sm">
        <GlassCard variant="strong" padded>
          <div style={{display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center'}}>
            <Badge tone="frost" dot>Evaluators</Badge>
            <Badge tone="frost" dot>Trading modes</Badge>
            <Badge tone="frost" dot>Interfaces</Badge>
            <Badge tone="frost" dot>Exchanges</Badge>
            <Badge tone="pos" dot>Backtesting</Badge>
            <Badge tone="warn" dot>Notifications</Badge>
          </div>
        </GlassCard>
      </Section>

      <CTABand
        title="Start automating in minutes"
        description="Follow the getting-started guide, or jump straight into the developer docs to build your own tentacle."
        actions={[
          {label: 'Get started', to: '/guides/octobot'},
          {label: 'Developer docs', to: '/developers/getting-started', variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
