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

/*
 * Example feature page — route: /features/strategy-designer
 *
 * Same pattern as src/pages/welcome.tsx, focused on a single feature. Add more
 * files under src/pages/features/ for each feature page; they all share the
 * navbar-less LandingLayout and the Neo Glass Dark section components.
 */

const CAPABILITIES: Feature[] = [
  {
    icon: '🎛️',
    title: 'Visual strategy building',
    description:
      'Compose evaluators and trading modes into a strategy without writing code.',
  },
  {
    icon: '⏪',
    title: 'Instant backtests',
    description:
      'Run a strategy against historical data and read the performance report in seconds.',
  },
  {
    icon: '🔧',
    title: 'Fine-tune every parameter',
    description:
      'Adjust risk, timeframes and indicator settings, then re-test until it fits.',
  },
];

export default function StrategyDesignerFeature(): ReactNode {
  return (
    <LandingLayout
      title="Strategy Designer"
      description="Design, backtest and fine-tune automated trading strategies visually with the OctoBot Strategy Designer.">
      <Hero
        eyebrow="Feature"
        title="Design strategies visually"
        subtitle="The Strategy Designer turns trading ideas into running automation — build, backtest and refine, all in one place."
        actions={[
          {label: 'Open the guide', to: '/guides/octobot-usage/strategy-designer'},
          {label: 'Back to overview', to: '/welcome', variant: 'ghost'},
        ]}
        visual={
          <GlassCard variant="hero" padded>
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
              <span className="ng-eyebrow">Live preview</span>
              <div style={{fontFamily: 'var(--ng-font-mono)', fontSize: '0.85rem', color: 'var(--ng-ink-muted)', lineHeight: 1.7}}>
                strategy: <span style={{color: 'var(--ng-frost)'}}>RSI + DCA</span>
                <br />
                timeframe: <span style={{color: 'var(--ng-frost)'}}>4h</span>
                <br />
                backtest pnl: <span style={{color: 'var(--ng-pos)'}}>+18.4%</span>
              </div>
            </div>
          </GlassCard>
        }
      />

      <Section
        eyebrow="What it does"
        title="From idea to automation"
        lead="Three steps: build the strategy, backtest it, fine-tune it — then let OctoBot run it.">
        <FeatureGrid features={CAPABILITIES} columns={3} />
      </Section>

      <CTABand
        title="Build your first strategy"
        description="The strategy designer guide walks through creating, testing and deploying a strategy end to end."
        actions={[
          {label: 'Read the guide', to: '/guides/octobot-usage/strategy-designer'},
          {label: 'See all guides', to: '/guides/octobot', variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
