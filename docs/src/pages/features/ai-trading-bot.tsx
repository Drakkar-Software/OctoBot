import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  IconList,
  FAQ,
  CTABand,
  type Feature,
  type IconListItem,
  type FAQItem,
} from '@site/src/components/landing';
import styles from './_styles.module.css';

/*
 * AI Trading Bot feature page — route: /features/ai-trading-bot.
 *
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the other feature pages: a
 * navbar-less LandingLayout composed entirely from reusable components.
 */

const CLOUD = 'https://www.octobot.cloud';
const AI_GUIDE = '/guides/octobot-trading-modes/chatgpt-trading';

const WHY: IconListItem[] = [
  {
    icon: '💸',
    text: (
      <Translate
        id="features.aiTradingBot.why.noCost"
        description="Why-AI list item on AI trading bot page"
        values={{label: <strong>No cost:</strong>}}>
        {
          "{label} don't pay ChatGPT when using AI trading strategies."
        }
      </Translate>
    ),
  },
  {
    icon: '🧪',
    text: (
      <Translate
        id="features.aiTradingBot.why.paperTrading"
        description="Why-AI list item on AI trading bot page"
        values={{label: <strong>Paper trading:</strong>}}>
        {'{label} test AI strategies before using your real funds.'}
      </Translate>
    ),
  },
  {
    icon: '⚡',
    text: (
      <Translate
        id="features.aiTradingBot.why.speed"
        description="Why-AI list item on AI trading bot page"
        values={{label: <strong>Speed:</strong>}}>
        {
          '{label} AI rapidly makes trading decisions based on massive information.'
        }
      </Translate>
    ),
  },
  {
    icon: '🤖',
    text: (
      <Translate
        id="features.aiTradingBot.why.easy"
        description="Why-AI list item on AI trading bot page"
        values={{label: <strong>Easy:</strong>}}>
        {
          '{label} let the best AI models (like ChatGPT) manage your funds.'
        }
      </Translate>
    ),
  },
];

const STRATEGIES: Feature[] = [
  {
    icon: '📊',
    title: translate({
      id: 'features.aiTradingBot.strategies.indicators.title',
      message: 'Technical & AI indicators',
      description: 'Strategy title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.strategies.indicators.description',
      message:
        'Blend classic technical analysis with AI predictions to time entries and exits.',
      description: 'Strategy description on AI trading bot page',
    }),
  },
  {
    icon: '🧠',
    title: translate({
      id: 'features.aiTradingBot.strategies.chatgpt.title',
      message: 'ChatGPT-driven strategies',
      description: 'Strategy title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.strategies.chatgpt.description',
      message:
        'Let large language models read the market and drive your trading decisions.',
      description: 'Strategy description on AI trading bot page',
    }),
  },
  {
    icon: '🎛️',
    title: translate({
      id: 'features.aiTradingBot.strategies.own.title',
      message: 'Your own AI strategy',
      description: 'Strategy title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.strategies.own.description',
      message:
        'Fine-tune AI strategies in the strategy editor, or integrate your own model.',
      description: 'Strategy description on AI trading bot page',
    }),
  },
];

const PREDICTIONS: Feature[] = [
  {
    icon: '₿',
    title: translate({
      id: 'features.aiTradingBot.predictions.btc.title',
      message: 'BTC · price outlook',
      description: 'Prediction title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.predictions.btc.description',
      message:
        'ChatGPT analyzes Bitcoin market data and flags the likely next move.',
      description: 'Prediction description on AI trading bot page',
    }),
  },
  {
    icon: 'Ξ',
    title: translate({
      id: 'features.aiTradingBot.predictions.eth.title',
      message: 'ETH · momentum read',
      description: 'Prediction title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.predictions.eth.description',
      message:
        'Ethereum sentiment and momentum, distilled into a buy / sell signal.',
      description: 'Prediction description on AI trading bot page',
    }),
  },
  {
    icon: '◎',
    title: translate({
      id: 'features.aiTradingBot.predictions.sol.title',
      message: 'SOL · trend signal',
      description: 'Prediction title on AI trading bot page',
    }),
    description: translate({
      id: 'features.aiTradingBot.predictions.sol.description',
      message:
        'Solana trend detection, refreshed as new market information lands.',
      description: 'Prediction description on AI trading bot page',
    }),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.aiTradingBot.faq.q1.question',
      message: 'What is an AI trading bot?',
      description: 'FAQ question on AI trading bot page',
    }),
    answer: translate({
      id: 'features.aiTradingBot.faq.q1.answer',
      message:
        'An AI trading bot is software that leverages artificial intelligence to analyze market data and execute cryptocurrency trades automatically. It is used to optimize trading decisions and potentially increase profits by reacting to market changes faster than humans.',
      description: 'FAQ answer on AI trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.aiTradingBot.faq.q2.question',
      message: 'How to set up an AI trading bot?',
      description: 'FAQ question on AI trading bot page',
    }),
    answer: (
      <Translate
        id="features.aiTradingBot.faq.q2.answer"
        description="FAQ answer on AI trading bot page"
        values={{
          guideLink: (
            <Link to={AI_GUIDE}>
              <Translate
                id="features.aiTradingBot.faq.q2.answerLink"
                description="FAQ answer link text on AI trading bot page">
                Check out this guide to get started.
              </Translate>
            </Link>
          ),
        }}>
        {
          'You can easily create an AI trading bot for free on OctoBot App. {guideLink}'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.aiTradingBot.faq.q3.question',
      message: 'How to use an AI trading bot?',
      description: 'FAQ question on AI trading bot page',
    }),
    answer: (
      <Translate
        id="features.aiTradingBot.faq.q3.answer"
        description="FAQ answer on AI trading bot page"
        values={{
          guideLink: (
            <Link to={AI_GUIDE}>
              <Translate
                id="features.aiTradingBot.faq.q3.answerLink"
                description="FAQ answer link text on AI trading bot page">
                Check out this guide for more details.
              </Translate>
            </Link>
          ),
        }}>
        {
          'Once you have started an AI trading bot on OctoBot App, you can easily follow its activity. {guideLink}'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.aiTradingBot.faq.q4.question',
      message: 'What is the best AI trading bot?',
      description: 'FAQ question on AI trading bot page',
    }),
    answer: (
      <Translate
        id="features.aiTradingBot.faq.q4.answer"
        description="FAQ answer on AI trading bot page"
        values={{
          blogLink: (
            <Link to="/blog">
              <Translate
                id="features.aiTradingBot.faq.q4.answerLink"
                description="FAQ answer link text on AI trading bot page">
                in our blog.
              </Translate>
            </Link>
          ),
        }}>
        {
          "Choosing the right artificial-intelligence crypto trading bot from the many options available can be tough. We've compiled a list of the best AI crypto trading bots {blogLink}"
        }
      </Translate>
    ),
  },
];

export default function AITradingBotFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.aiTradingBot.layout.title',
        message: 'AI Trading Bot',
        description: 'Page meta title for AI trading bot page',
      })}
      description={translate({
        id: 'features.aiTradingBot.layout.description',
        message:
          'Automate your crypto trading with AI for free. OctoBot uses AI models like ChatGPT to detect market movements, paper-trade strategies and run them on autopilot.',
        description: 'Page meta description for AI trading bot page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.aiTradingBot.hero.eyebrow',
          message: 'AI trading bot',
          description: 'Hero eyebrow on AI trading bot page',
        })}
        title={
          <Translate
            id="features.aiTradingBot.hero.title"
            description="Hero title on AI trading bot page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.aiTradingBot.hero.accent"
                    description="Accent text in hero title on AI trading bot page">
                    now on autopilot.
                  </Translate>
                </span>
              ),
            }}>
            {'AI crypto trading, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.aiTradingBot.hero.subtitle',
          message:
            'Unleash the power of AI for smart crypto trading — detect market movements, predict price fluctuations and let the bot act.',
          description: 'Hero subtitle on AI trading bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.aiTradingBot.hero.action.invest',
              message: 'Invest for free',
              description: 'Hero action label on AI trading bot page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.aiTradingBot.hero.action.guide',
              message: 'Read the AI guide',
              description: 'Hero action label on AI trading bot page',
            }),
            to: AI_GUIDE,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.aiTradingBot.hero.meta.freeStrategies',
              message: 'Free AI strategies',
              description: 'Hero meta label on AI trading bot page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.aiTradingBot.hero.meta.paperTrading',
              message: 'Paper trading included',
              description: 'Hero meta label on AI trading bot page',
            }),
          },
          {
            label: translate({
              id: 'features.aiTradingBot.hero.meta.chatgpt',
              message: 'Powered by ChatGPT',
              description: 'Hero meta label on AI trading bot page',
            }),
          },
        ]}
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.aiTradingBot.why.eyebrow',
          message: 'Why AI',
          description: 'Section eyebrow on AI trading bot page',
        })}
        title={translate({
          id: 'features.aiTradingBot.why.title',
          message: 'Why using AI?',
          description: 'Section title on AI trading bot page',
        })}
        lead={translate({
          id: 'features.aiTradingBot.why.lead',
          message:
            'OctoBot uses AI models to detect and predict upcoming movements in the crypto market, identifying profit opportunities.',
          description: 'Section lead on AI trading bot page',
        })}>
        <IconList items={WHY} />
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            <Translate
              id="features.aiTradingBot.why.cta"
              description="CTA button on AI trading bot page">
              Start AI trading for free
            </Translate>
          </Link>
        </div>
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.aiTradingBot.strategies.eyebrow',
          message: 'Strategies',
          description: 'Section eyebrow on AI trading bot page',
        })}
        title={translate({
          id: 'features.aiTradingBot.strategies.title',
          message: 'Discover AI trading strategies',
          description: 'Section title on AI trading bot page',
        })}
        lead={translate({
          id: 'features.aiTradingBot.strategies.lead',
          message:
            'Explore a variety of AI trading and investment strategies. View performance history, understand how they work and start trading with ease.',
          description: 'Section lead on AI trading bot page',
        })}>
        <FeatureGrid features={STRATEGIES} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.aiTradingBot.predictions.eyebrow',
          message: 'Predictions',
          description: 'Section eyebrow on AI trading bot page',
        })}
        title={translate({
          id: 'features.aiTradingBot.predictions.title',
          message: 'AI crypto predictions',
          description: 'Section title on AI trading bot page',
        })}
        lead={translate({
          id: 'features.aiTradingBot.predictions.lead',
          message:
            'OctoBot leverages ChatGPT to analyze the cryptocurrency market and predict potential price fluctuations.',
          description: 'Section lead on AI trading bot page',
        })}>
        <FeatureGrid features={PREDICTIONS} columns={3} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={AI_GUIDE}>
            <Translate
              id="features.aiTradingBot.predictions.cta"
              description="CTA button on AI trading bot page">
              See all predictions
            </Translate>
          </Link>
        </div>
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.aiTradingBot.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on AI trading bot page',
        })}
        title={translate({
          id: 'features.aiTradingBot.faq.title',
          message: 'AI trading bot FAQ',
          description: 'FAQ section title on AI trading bot page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.aiTradingBot.cta.title',
          message: 'Put AI to work on your portfolio',
          description: 'CTA band title on AI trading bot page',
        })}
        description={translate({
          id: 'features.aiTradingBot.cta.description',
          message:
            'Create your AI trading bot for free on OctoBot App, or read the guide first.',
          description: 'CTA band description on AI trading bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.aiTradingBot.cta.action.invest',
              message: 'Invest for free',
              description: 'CTA action label on AI trading bot page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.aiTradingBot.cta.action.guide',
              message: 'Read the AI guide',
              description: 'CTA action label on AI trading bot page',
            }),
            to: AI_GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
