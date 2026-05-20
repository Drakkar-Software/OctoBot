import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
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
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components, with a page-local sample-signal grid (_SignalCards).
 */

const CLOUD = 'https://www.octobot.cloud';
const AI_GUIDE = '/guides/octobot-trading-modes/chatgpt-trading';

export default function CryptoPredictionTool(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'tools.cryptoPrediction.layout.title',
        message: 'ChatGPT crypto predictions',
        description: 'Crypto prediction page meta title',
      })}
      description={translate({
        id: 'tools.cryptoPrediction.layout.description',
        message:
          'OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals.',
        description: 'Crypto prediction page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.cryptoPrediction.hero.eyebrow',
          message: 'ChatGPT predictions',
          description: 'Crypto prediction hero eyebrow',
        })}
        title={
          <span className="ng-text-gradient">
            <Translate
              id="tools.cryptoPrediction.hero.title"
              description="Crypto prediction hero title">
              ChatGPT crypto predictions.
            </Translate>
          </span>
        }
        subtitle={translate({
          id: 'tools.cryptoPrediction.hero.subtitle',
          message:
            'OctoBot ChatGPT trading is an AI-powered strategy that uses OpenAI ChatGPT to analyze crypto market trends and generate trading signals.',
          description: 'Crypto prediction hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.cryptoPrediction.hero.action.invest',
              message: 'Invest for free',
              description: 'Crypto prediction hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.cryptoPrediction.hero.action.guide',
              message: 'Read the AI guide',
              description: 'Crypto prediction hero AI guide action label',
            }),
            to: AI_GUIDE,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.cryptoPrediction.hero.meta.poweredBy',
              message: 'Powered by ChatGPT',
              description: 'Crypto prediction hero meta: powered by ChatGPT',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.cryptoPrediction.hero.meta.freeStrategy',
              message: 'Free AI strategy',
              description: 'Crypto prediction hero meta: free AI strategy',
            }),
          },
          {
            label: translate({
              id: 'tools.cryptoPrediction.hero.meta.paperTrading',
              message: 'Paper trading included',
              description: 'Crypto prediction hero meta: paper trading',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.cryptoPrediction.signals.eyebrow',
          message: 'Latest predictions',
          description: 'Crypto prediction signals section eyebrow',
        })}
        title={translate({
          id: 'tools.cryptoPrediction.signals.title',
          message: 'Fresh signals from ChatGPT',
          description: 'Crypto prediction signals section title',
        })}
        lead={translate({
          id: 'tools.cryptoPrediction.signals.lead',
          message:
            'A snapshot of the kind of trading signals ChatGPT generates as it reads the crypto market. Live predictions run on OctoBot App.',
          description: 'Crypto prediction signals section lead',
        })}>
        <SignalCards />
      </Section>

      <Section>
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h2 className={styles.panelTitle}>
            <Translate
              id="tools.cryptoPrediction.panel.title"
              description="Crypto prediction early access panel title">
              Do you want to trade crypto using ChatGPT?
            </Translate>
          </h2>
          <p className={styles.panelText}>
            <Translate
              id="tools.cryptoPrediction.panel.text"
              description="Crypto prediction early access panel text">
              Be one of the first to experience our new strategy. It allows you
              to automatically trade crypto from ChatGPT predictions.
            </Translate>
          </p>
          <Link
            className={`ng-btn ng-btn--primary ${styles.panelCta}`}
            to={CLOUD}>
            <Translate
              id="tools.cryptoPrediction.panel.cta"
              description="Crypto prediction early access panel CTA">
              Join the early access
            </Translate>
          </Link>
        </GlassCard>
      </Section>

      <CTABand
        title={translate({
          id: 'tools.cryptoPrediction.cta.title',
          message: 'Put ChatGPT to work on your portfolio',
          description: 'Crypto prediction CTA band title',
        })}
        description={translate({
          id: 'tools.cryptoPrediction.cta.description',
          message:
            'Create your ChatGPT trading bot for free on OctoBot App, or read the guide first.',
          description: 'Crypto prediction CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.cryptoPrediction.cta.action.invest',
              message: 'Invest for free',
              description: 'Crypto prediction CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.cryptoPrediction.cta.action.guide',
              message: 'Read the AI guide',
              description: 'Crypto prediction CTA AI guide action label',
            }),
            to: AI_GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
