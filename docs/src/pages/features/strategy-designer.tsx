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
    title: translate({
      id: 'features.strategyDesigner.capabilities.visual.title',
      message: 'Visual strategy building',
      description: 'Capability title on strategy designer page',
    }),
    description: translate({
      id: 'features.strategyDesigner.capabilities.visual.description',
      message:
        'Compose evaluators and trading modes into a strategy without writing code.',
      description: 'Capability description on strategy designer page',
    }),
  },
  {
    icon: '⏪',
    title: translate({
      id: 'features.strategyDesigner.capabilities.backtests.title',
      message: 'Instant backtests',
      description: 'Capability title on strategy designer page',
    }),
    description: translate({
      id: 'features.strategyDesigner.capabilities.backtests.description',
      message:
        'Run a strategy against historical data and read the performance report in seconds.',
      description: 'Capability description on strategy designer page',
    }),
  },
  {
    icon: '🔧',
    title: translate({
      id: 'features.strategyDesigner.capabilities.tune.title',
      message: 'Fine-tune every parameter',
      description: 'Capability title on strategy designer page',
    }),
    description: translate({
      id: 'features.strategyDesigner.capabilities.tune.description',
      message:
        'Adjust risk, timeframes and indicator settings, then re-test until it fits.',
      description: 'Capability description on strategy designer page',
    }),
  },
];

export default function StrategyDesignerFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.strategyDesigner.layout.title',
        message: 'Strategy Designer',
        description: 'Page meta title for strategy designer page',
      })}
      description={translate({
        id: 'features.strategyDesigner.layout.description',
        message:
          'Design, backtest and fine-tune automated trading strategies visually with the OctoBot Strategy Designer.',
        description: 'Page meta description for strategy designer page',
      })}>
      <Hero
        eyebrow={translate({
          id: 'features.strategyDesigner.hero.eyebrow',
          message: 'Feature',
          description: 'Hero eyebrow on strategy designer page',
        })}
        title={translate({
          id: 'features.strategyDesigner.hero.title',
          message: 'Design strategies visually',
          description: 'Hero title on strategy designer page',
        })}
        subtitle={translate({
          id: 'features.strategyDesigner.hero.subtitle',
          message:
            'The Strategy Designer turns trading ideas into running automation — build, backtest and refine, all in one place.',
          description: 'Hero subtitle on strategy designer page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.strategyDesigner.hero.action.guide',
              message: 'Open the guide',
              description: 'Hero action label on strategy designer page',
            }),
            to: '/guides/octobot-usage/strategy-designer',
          },
          {
            label: translate({
              id: 'features.strategyDesigner.hero.action.overview',
              message: 'Back to overview',
              description: 'Hero action label on strategy designer page',
            }),
            to: '/welcome',
            variant: 'ghost',
          },
        ]}
        visual={
          <GlassCard variant="hero" padded>
            <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
              <span className="ng-eyebrow">
                <Translate
                  id="features.strategyDesigner.visual.livePreview"
                  description="Live preview eyebrow on strategy designer page">
                  Live preview
                </Translate>
              </span>
              <div style={{fontFamily: 'var(--ng-font-mono)', fontSize: '0.85rem', color: 'var(--ng-ink-muted)', lineHeight: 1.7}}>
                <Translate
                  id="features.strategyDesigner.visual.strategyLabel"
                  description="Strategy label in strategy designer preview card">
                  strategy:
                </Translate>{' '}
                <span style={{color: 'var(--ng-frost)'}}>RSI + DCA</span>
                <br />
                <Translate
                  id="features.strategyDesigner.visual.timeframeLabel"
                  description="Timeframe label in strategy designer preview card">
                  timeframe:
                </Translate>{' '}
                <span style={{color: 'var(--ng-frost)'}}>4h</span>
                <br />
                <Translate
                  id="features.strategyDesigner.visual.backtestLabel"
                  description="Backtest PnL label in strategy designer preview card">
                  backtest pnl:
                </Translate>{' '}
                <span style={{color: 'var(--ng-pos)'}}>+18.4%</span>
              </div>
            </div>
          </GlassCard>
        }
      />

      <Section
        eyebrow={translate({
          id: 'features.strategyDesigner.what.eyebrow',
          message: 'What it does',
          description: 'Section eyebrow on strategy designer page',
        })}
        title={translate({
          id: 'features.strategyDesigner.what.title',
          message: 'From idea to automation',
          description: 'Section title on strategy designer page',
        })}
        lead={translate({
          id: 'features.strategyDesigner.what.lead',
          message:
            'Three steps: build the strategy, backtest it, fine-tune it — then let OctoBot run it.',
          description: 'Section lead on strategy designer page',
        })}>
        <FeatureGrid features={CAPABILITIES} columns={3} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.strategyDesigner.cta.title',
          message: 'Build your first strategy',
          description: 'CTA band title on strategy designer page',
        })}
        description={translate({
          id: 'features.strategyDesigner.cta.description',
          message:
            'The strategy designer guide walks through creating, testing and deploying a strategy end to end.',
          description: 'CTA band description on strategy designer page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.strategyDesigner.cta.action.guide',
              message: 'Read the guide',
              description: 'CTA action label on strategy designer page',
            }),
            to: '/guides/octobot-usage/strategy-designer',
          },
          {
            label: translate({
              id: 'features.strategyDesigner.cta.action.allGuides',
              message: 'See all guides',
              description: 'CTA action label on strategy designer page',
            }),
            to: '/guides/octobot',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
