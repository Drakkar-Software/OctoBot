import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type FAQItem,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './_styles.module.css';

/*
 * TradingView Bot feature page — route: /features/tradingview-bot.
 *
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components.
 */

const CLOUD = 'https://www.octobot.cloud';
const TV_GUIDE = '/guides/octobot-interfaces/tradingview';

const STEPS: Step[] = [
  {
    icon: '📐',
    title: translate({
      id: 'features.tradingviewBot.steps.define.title',
      message: 'Define your strategy on TradingView',
      description: 'Step title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.steps.define.description',
      message:
        'Use a built-in indicator or your own Pine Script strategy on TradingView.',
      description: 'Step description on TradingView bot page',
    }),
  },
  {
    icon: '🔗',
    title: translate({
      id: 'features.tradingviewBot.steps.connect.title',
      message: 'Connect OctoBot',
      description: 'Step title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.steps.connect.description',
      message:
        'Link your TradingView account to OctoBot with a webhook integration.',
      description: 'Step description on TradingView bot page',
    }),
  },
  {
    icon: '🎯',
    title: translate({
      id: 'features.tradingviewBot.steps.amount.title',
      message: 'Enter the amount to trade',
      description: 'Step title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.steps.amount.description',
      message:
        'Set how much of your holdings each alert should trade — OctoBot does the rest.',
      description: 'Step description on TradingView bot page',
    }),
  },
];

const STRATEGIES: Feature[] = [
  {
    icon: '✖',
    title: translate({
      id: 'features.tradingviewBot.strategies.goldenCross.title',
      message: 'Golden Cross on ETH/USDT',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.goldenCross.description',
      message:
        'Buying the base asset when moving-average indicators show a Golden Cross.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
  {
    icon: '〰',
    title: translate({
      id: 'features.tradingviewBot.strategies.rsi.title',
      message: 'RSI thresholds on ADA/USDT',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.rsi.description',
      message:
        'Selling the base asset when the RSI indicator signals an overbought market.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
  {
    icon: '📉',
    title: translate({
      id: 'features.tradingviewBot.strategies.bearish.title',
      message: 'Bearish Supports on BTC/USDT',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.bearish.description',
      message:
        'Selling the base asset as soon as a price support zone is broken.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
  {
    icon: '🚀',
    title: translate({
      id: 'features.tradingviewBot.strategies.altcoins.title',
      message: 'Altcoins Bullmarket on SOL/USDT',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.altcoins.description',
      message:
        'Buying the base asset when the price rises by more than 5% within 4 hours.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
  {
    icon: '📜',
    title: translate({
      id: 'features.tradingviewBot.strategies.pineScript.title',
      message: 'Pine Script Strategy on ADA/BTC',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.pineScript.description',
      message:
        'Using a Pine Script strategy on TradingView to automate your trades.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
  {
    icon: '💡',
    title: translate({
      id: 'features.tradingviewBot.strategies.other.title',
      message: 'Any other great idea',
      description: 'Strategy title on TradingView bot page',
    }),
    description: translate({
      id: 'features.tradingviewBot.strategies.other.description',
      message:
        'Automate trades from any of TradingView’s tools — price moves, indicators or Pine Script.',
      description: 'Strategy description on TradingView bot page',
    }),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q1.question',
      message: 'What is TradingView?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: translate({
      id: 'features.tradingviewBot.faq.q1.answer',
      message:
        'TradingView is a popular online charting platform and social network for traders and investors to analyze financial markets and share trading ideas.',
      description: 'FAQ answer on TradingView bot page',
    }),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q2.question',
      message: 'Why automating TradingView?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: translate({
      id: 'features.tradingviewBot.faq.q2.answer',
      message:
        'Automating TradingView allows traders to execute trades based on predefined strategies and alerts, reducing the need for manual intervention and enabling consistent strategy implementation.',
      description: 'FAQ answer on TradingView bot page',
    }),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q3.question',
      message: 'What are the charges?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: translate({
      id: 'features.tradingviewBot.faq.q3.answer',
      message:
        "You need an OctoBot App plan that allows running a TradingView OctoBot. Additionally, you'll need a paid TradingView account to use webhooks.",
      description: 'FAQ answer on TradingView bot page',
    }),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q4.question',
      message: 'How to trade automatically with TradingView?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: (
      <Translate
        id="features.tradingviewBot.faq.q4.answer"
        description="FAQ answer on TradingView bot page"
        values={{
          guideLink: (
            <Link to={TV_GUIDE}>
              <Translate
                id="features.tradingviewBot.faq.q4.answerLink"
                description="FAQ answer link text on TradingView bot page">
                Here is a dedicated guide on TradingView alerts automation.
              </Translate>
            </Link>
          ),
        }}>
        {
          'Start a TradingView OctoBot on your exchange account, link your TradingView account through a webhook integration, then create an alert based on your strategy. When the alert fires, OctoBot executes the corresponding trades. {guideLink}'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q5.question',
      message: 'How to automate a TradingView strategy?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: (
      <Translate
        id="features.tradingviewBot.faq.q5.answer"
        description="FAQ answer on TradingView bot page"
        values={{
          guideLink: (
            <Link to={TV_GUIDE}>
              <Translate
                id="features.tradingviewBot.faq.q5.answerLink"
                description="FAQ answer link text on TradingView bot page">
                Here is a dedicated guide on automating a TradingView strategy.
              </Translate>
            </Link>
          ),
        }}>
        {
          'Update the Pine Script code of the strategy and add alert statements that trigger when your conditions are met. Those alerts are sent to your TradingView OctoBot, which executes the trades automatically. {guideLink}'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q6.question',
      message: 'Can I combine an RSI and an EMA in Pine Script?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: (
      <Translate
        id="features.tradingviewBot.faq.q6.answer"
        description="FAQ answer on TradingView bot page"
        values={{
          guideLink: (
            <Link to={TV_GUIDE}>
              <Translate
                id="features.tradingviewBot.faq.q6.answerLink"
                description="FAQ answer link text on TradingView bot page">
                Here is a dedicated guide on automating a TradingView indicator.
              </Translate>
            </Link>
          ),
        }}>
        {
          'Yes — you can combine indicators like the Relative Strength Index (RSI) and Exponential Moving Average (EMA) in Pine Script to build a custom strategy that generates alerts for your TradingView OctoBot. {guideLink}'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.tradingviewBot.faq.q7.question',
      message: 'How to use AI to create a TradingView strategy?',
      description: 'FAQ question on TradingView bot page',
    }),
    answer: translate({
      id: 'features.tradingviewBot.faq.q7.answer',
      message:
        'On OctoBot App you can generate a TradingView strategy from a textual description of your trading ideas — the AI translates your concept into ready-to-use Pine Script code.',
      description: 'FAQ answer on TradingView bot page',
    }),
  },
];

export default function TradingViewBotFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.tradingviewBot.layout.title',
        message: 'TradingView Bot',
        description: 'Page meta title for TradingView bot page',
      })}
      description={translate({
        id: 'features.tradingviewBot.layout.description',
        message:
          'Easily automate any TradingView strategy, or leverage AI to create custom strategies for automated crypto trading without coding.',
        description: 'Page meta description for TradingView bot page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.tradingviewBot.hero.eyebrow',
          message: 'TradingView bot',
          description: 'Hero eyebrow on TradingView bot page',
        })}
        title={
          <Translate
            id="features.tradingviewBot.hero.title"
            description="Hero title on TradingView bot page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.tradingviewBot.hero.accent"
                    description="Accent text in hero title on TradingView bot page">
                    for crypto trading.
                  </Translate>
                </span>
              ),
            }}>
            {'TradingView automated, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.tradingviewBot.hero.subtitle',
          message:
            'Automate any TradingView strategy, or create your own one with AI.',
          description: 'Hero subtitle on TradingView bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.tradingviewBot.hero.action.automate',
              message: 'Automate my strategy',
              description: 'Hero action label on TradingView bot page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.tradingviewBot.hero.action.guide',
              message: 'Read the guide',
              description: 'Hero action label on TradingView bot page',
            }),
            to: TV_GUIDE,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.tradingviewBot.hero.meta.anyStrategy',
              message: 'Any indicator or strategy',
              description: 'Hero meta label on TradingView bot page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.tradingviewBot.hero.meta.pineScript',
              message: 'Pine Script supported',
              description: 'Hero meta label on TradingView bot page',
            }),
          },
          {
            label: translate({
              id: 'features.tradingviewBot.hero.meta.aiGeneration',
              message: 'AI strategy generation',
              description: 'Hero meta label on TradingView bot page',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'features.tradingviewBot.howItWorks.eyebrow',
          message: 'How it works',
          description: 'Section eyebrow on TradingView bot page',
        })}
        title={translate({
          id: 'features.tradingviewBot.howItWorks.title',
          message: 'Automate your strategies directly from TradingView',
          description: 'Section title on TradingView bot page',
        })}
        lead={translate({
          id: 'features.tradingviewBot.howItWorks.lead',
          message:
            'Three steps from a TradingView alert to a live trade on your exchange.',
          description: 'Section lead on TradingView bot page',
        })}>
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.tradingviewBot.strategies.eyebrow',
          message: 'Strategies',
          description: 'Section eyebrow on TradingView bot page',
        })}
        title={translate({
          id: 'features.tradingviewBot.strategies.title',
          message: 'Automate any TradingView strategy',
          description: 'Section title on TradingView bot page',
        })}
        lead={translate({
          id: 'features.tradingviewBot.strategies.lead',
          message:
            'From built-in indicators to your own Pine Script — a few examples of what you can wire up.',
          description: 'Section lead on TradingView bot page',
        })}>
        <FeatureGrid features={STRATEGIES} columns={3} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.tradingviewBot.aiGeneration.eyebrow',
          message: 'AI generation',
          description: 'Section eyebrow on TradingView bot page',
        })}
        title={
          <Translate
            id="features.tradingviewBot.aiGeneration.title"
            description="Section title on TradingView bot page"
            values={{
              badge: (
                <Badge tone="frost">
                  <Translate
                    id="features.tradingviewBot.aiGeneration.badge"
                    description="Early access badge on TradingView bot page">
                    Early access
                  </Translate>
                </Badge>
              ),
            }}>
            {'Generate your strategy with AI {badge}'}
          </Translate>
        }
        lead={translate({
          id: 'features.tradingviewBot.aiGeneration.lead',
          message:
            'Describe the strategy you want — the AI turns it into ready-to-use Pine Script.',
          description: 'Section lead on TradingView bot page',
        })}>
        <GlassCard variant="strong" padded={false} className={styles.pineDemo}>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>
              <Translate
                id="features.tradingviewBot.aiGeneration.promptLabel"
                description="Prompt label on TradingView bot page">
                Prompt
              </Translate>
            </div>
            <p className={styles.pinePrompt}>
              <Translate
                id="features.tradingviewBot.aiGeneration.promptText"
                description="Example prompt text on TradingView bot page">
                Create a Bollinger Bands trading strategy that identifies buy and
                sell signals based on price movements relative to the upper and
                lower bands.
              </Translate>
            </p>
          </div>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>Pine Script™</div>
            <pre className={styles.pineCode}>{`//@version=5
strategy("BB signals", overlay=true)
[mid, upper, lower] = ta.bb(close, 20, 2)
if ta.crossunder(close, lower)
    strategy.entry("Long", strategy.long)
if ta.crossover(close, upper)
    strategy.close("Long")`}</pre>
          </div>
          <div className={styles.pineRow}>
            <div className={styles.pineLabel}>
              <Translate
                id="features.tradingviewBot.aiGeneration.resultLabel"
                description="Result label on TradingView bot page">
                Result
              </Translate>
            </div>
            <p className={styles.pinePrompt}>
              <Translate
                id="features.tradingviewBot.aiGeneration.resultText"
                description="Example result text on TradingView bot page">
                A ready-to-use TradingView strategy, wired to your OctoBot in a
                couple of clicks.
              </Translate>
            </p>
          </div>
        </GlassCard>
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.tradingviewBot.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on TradingView bot page',
        })}
        title={translate({
          id: 'features.tradingviewBot.faq.title',
          message: 'TradingView bot FAQ',
          description: 'FAQ section title on TradingView bot page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.tradingviewBot.cta.title',
          message: 'Turn your TradingView alerts into trades',
          description: 'CTA band title on TradingView bot page',
        })}
        description={translate({
          id: 'features.tradingviewBot.cta.description',
          message:
            'Start a TradingView OctoBot on OctoBot App, or read the automation guide first.',
          description: 'CTA band description on TradingView bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.tradingviewBot.cta.action.automate',
              message: 'Automate my strategy',
              description: 'CTA action label on TradingView bot page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.tradingviewBot.cta.action.guide',
              message: 'Read the guide',
              description: 'CTA action label on TradingView bot page',
            }),
            to: TV_GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
