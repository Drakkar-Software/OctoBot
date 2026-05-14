import type {ReactNode} from 'react';
import {LandingLayout, Hero, Section, CTABand} from '@site/src/components/landing';
import ScalpingSignalCards from '@site/src/components/pages/tools/scalping-signals/ScalpingSignalCards';
import styles from './scalping-signals.module.css';

/*
 * Scalping signals tool page — route: /tools/scalping-signals.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the feature pages: a navbar-less
 * LandingLayout composed from reusable components, plus a page-local
 * _ScalpingSignalCards mock for the sample-signal grid.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

export default function ScalpingSignalsTool(): ReactNode {
  return (
    <LandingLayout
      title="Scalping signals"
      description="Real-time crypto scalping signals — many small transactions to capitalize on slight price movements for frequent, modest profits.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Scalping signals"
        title={
          <>
            Scalping signals,{' '}
            <span className="ng-text-gradient">in real time.</span>
          </>
        }
        subtitle="Scalping is a quick trading technique involving many small transactions to capitalize on slight price movements. The goal is to make frequent, modest profits."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Real-time signals', dot: true},
          {label: 'Long & short setups'},
          {label: 'No account required'},
        ]}
      />

      <Section
        eyebrow="Latest signals"
        title="Fresh scalping signals"
        lead="A sample of the scalping signals OctoBot surfaces — entry, take profit, stop loss and expected profit at a glance. Live signals refresh continuously on OctoBot Cloud.">
        <ScalpingSignalCards />
      </Section>

      <CTABand
        title="Trade scalping signals on autopilot"
        description="Create your trading bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
