import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
      title={translate({
        id: 'tools.scalpingSignals.layout.title',
        message: 'Scalping signals',
        description: 'Scalping signals page meta title',
      })}
      description={translate({
        id: 'tools.scalpingSignals.layout.description',
        message:
          'Real-time crypto scalping signals — many small transactions to capitalize on slight price movements for frequent, modest profits.',
        description: 'Scalping signals page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.scalpingSignals.hero.eyebrow',
          message: 'Scalping signals',
          description: 'Scalping signals hero eyebrow',
        })}
        title={
          <Translate
            id="tools.scalpingSignals.hero.title"
            description="Scalping signals hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="tools.scalpingSignals.hero.title.accent"
                    description="Scalping signals hero title accent">
                    in real time.
                  </Translate>
                </span>
              ),
            }}>
            {'Scalping signals, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'tools.scalpingSignals.hero.subtitle',
          message:
            'Scalping is a quick trading technique involving many small transactions to capitalize on slight price movements. The goal is to make frequent, modest profits.',
          description: 'Scalping signals hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.scalpingSignals.hero.action.invest',
              message: 'Invest for free',
              description: 'Scalping signals hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.scalpingSignals.hero.action.guides',
              message: 'Read the guides',
              description: 'Scalping signals hero guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.scalpingSignals.hero.meta.realTime',
              message: 'Real-time signals',
              description: 'Scalping signals hero meta: real-time signals',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.scalpingSignals.hero.meta.setups',
              message: 'Long & short setups',
              description: 'Scalping signals hero meta: long and short setups',
            }),
          },
          {
            label: translate({
              id: 'tools.scalpingSignals.hero.meta.noAccount',
              message: 'No account required',
              description: 'Scalping signals hero meta: no account required',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.scalpingSignals.signals.eyebrow',
          message: 'Latest signals',
          description: 'Scalping signals section eyebrow',
        })}
        title={translate({
          id: 'tools.scalpingSignals.signals.title',
          message: 'Fresh scalping signals',
          description: 'Scalping signals section title',
        })}
        lead={translate({
          id: 'tools.scalpingSignals.signals.lead',
          message:
            'A sample of the scalping signals OctoBot surfaces — entry, take profit, stop loss and expected profit at a glance. Live signals refresh continuously on OctoBot Cloud.',
          description: 'Scalping signals section lead',
        })}>
        <ScalpingSignalCards />
      </Section>

      <CTABand
        title={translate({
          id: 'tools.scalpingSignals.cta.title',
          message: 'Trade scalping signals on autopilot',
          description: 'Scalping signals CTA band title',
        })}
        description={translate({
          id: 'tools.scalpingSignals.cta.description',
          message:
            'Create your trading bot for free on OctoBot Cloud, or read the guides first.',
          description: 'Scalping signals CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.scalpingSignals.cta.action.invest',
              message: 'Invest for free',
              description: 'Scalping signals CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.scalpingSignals.cta.action.guides',
              message: 'Read the guides',
              description: 'Scalping signals CTA guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
