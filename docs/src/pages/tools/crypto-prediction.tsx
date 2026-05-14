import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import {
  LandingLayout,
  Hero,
  Section,
  CTABand,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import styles from './_styles.module.css';
import SignalCards from '@site/src/components/pages/tools/crypto-prediction/SignalCards';

/*
 * ChatGPT crypto predictions tool page — route: /tools/crypto-prediction.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components, with a page-local sample-signal grid (_SignalCards).
 */

const CLOUD = 'https://www.octobot.cloud';
const AI_GUIDE = '/guides/octobot-trading-modes/chatgpt-trading';

export default function CryptoPredictionTool(): ReactNode {
  return (
    <LandingLayout
      title="ChatGPT crypto predictions"
      description="OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="ChatGPT predictions"
        title={
          <>
            <span className="ng-text-gradient">
              ChatGPT crypto predictions.
            </span>
          </>
        }
        subtitle="OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the AI guide', to: AI_GUIDE, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Powered by ChatGPT', dot: true},
          {label: 'Free AI strategy'},
          {label: 'Paper trading included'},
        ]}
      />

      <Section
        eyebrow="Latest predictions"
        title="Fresh signals from ChatGPT"
        lead="A snapshot of the kind of trading signals ChatGPT generates as it reads the crypto market. Live predictions run on OctoBot Cloud.">
        <SignalCards />
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h2 className={styles.panelTitle}>
            Do you want to trade crypto using ChatGPT?
          </h2>
          <p className={styles.panelText}>
            Be one of the first to experience our new strategy. It allows you
            to automatically trade crypto from ChatGPT predictions.
          </p>
          <Link
            className={`ng-btn ng-btn--primary ${styles.panelCta}`}
            to={CLOUD}>
            Join the early access
          </Link>
        </GlassCard>
      </Section>

      <CTABand
        title="Put ChatGPT to work on your portfolio"
        description="Create your ChatGPT trading bot for free on OctoBot Cloud, or read the guide first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the AI guide', to: AI_GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
