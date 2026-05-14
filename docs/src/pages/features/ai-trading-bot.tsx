import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
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
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the other feature pages: a
 * navbar-less LandingLayout composed entirely from reusable components.
 */

const CLOUD = 'https://www.octobot.cloud';
const AI_GUIDE = '/guides/octobot-trading-modes/chatgpt-trading';

const WHY: IconListItem[] = [
  {
    icon: '💸',
    text: (
      <>
        <strong>No cost:</strong> don&apos;t pay ChatGPT when using AI trading
        strategies.
      </>
    ),
  },
  {
    icon: '🧪',
    text: (
      <>
        <strong>Paper trading:</strong> test AI strategies before using your
        real funds.
      </>
    ),
  },
  {
    icon: '⚡',
    text: (
      <>
        <strong>Speed:</strong> AI rapidly makes trading decisions based on
        massive information.
      </>
    ),
  },
  {
    icon: '🤖',
    text: (
      <>
        <strong>Easy:</strong> let the best AI models (like ChatGPT) manage
        your funds.
      </>
    ),
  },
];

const STRATEGIES: Feature[] = [
  {
    icon: '📊',
    title: 'Technical & AI indicators',
    description:
      'Blend classic technical analysis with AI predictions to time entries and exits.',
  },
  {
    icon: '🧠',
    title: 'ChatGPT-driven strategies',
    description:
      'Let large language models read the market and drive your trading decisions.',
  },
  {
    icon: '🎛️',
    title: 'Your own AI strategy',
    description:
      'Fine-tune AI strategies in the strategy editor, or integrate your own model.',
  },
];

const PREDICTIONS: Feature[] = [
  {
    icon: '₿',
    title: 'BTC · price outlook',
    description:
      'ChatGPT analyzes Bitcoin market data and flags the likely next move.',
  },
  {
    icon: 'Ξ',
    title: 'ETH · momentum read',
    description:
      'Ethereum sentiment and momentum, distilled into a buy / sell signal.',
  },
  {
    icon: '◎',
    title: 'SOL · trend signal',
    description:
      'Solana trend detection, refreshed as new market information lands.',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is an AI trading bot?',
    answer:
      'An AI trading bot is software that leverages artificial intelligence to analyze market data and execute cryptocurrency trades automatically. It is used to optimize trading decisions and potentially increase profits by reacting to market changes faster than humans.',
  },
  {
    question: 'How to set up an AI trading bot?',
    answer: (
      <>
        You can easily create an AI trading bot for free on OctoBot Cloud.{' '}
        <Link to={AI_GUIDE}>Check out this guide to get started.</Link>
      </>
    ),
  },
  {
    question: 'How to use an AI trading bot?',
    answer: (
      <>
        Once you have started an AI trading bot on OctoBot Cloud, you can
        easily follow its activity.{' '}
        <Link to={AI_GUIDE}>Check out this guide for more details.</Link>
      </>
    ),
  },
  {
    question: 'What is the best AI trading bot?',
    answer: (
      <>
        Choosing the right artificial-intelligence crypto trading bot from the
        many options available can be tough. We&apos;ve compiled a list of the
        best AI crypto trading bots <Link to="/blog">in our blog.</Link>
      </>
    ),
  },
];

export default function AITradingBotFeature(): ReactNode {
  return (
    <LandingLayout
      title="AI Trading Bot"
      description="Automate your crypto trading with AI for free. OctoBot uses AI models like ChatGPT to detect market movements, paper-trade strategies and run them on autopilot.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="AI trading bot"
        title={
          <>
            AI crypto trading,{' '}
            <span className="ng-text-gradient">now on autopilot.</span>
          </>
        }
        subtitle="Unleash the power of AI for smart crypto trading — detect market movements, predict price fluctuations and let the bot act."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the AI guide', to: AI_GUIDE, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Free AI strategies', dot: true},
          {label: 'Paper trading included'},
          {label: 'Powered by ChatGPT'},
        ]}
      />

      <Section
        align="left"
        eyebrow="Why AI"
        title="Why using AI?"
        lead="OctoBot uses AI models to detect and predict upcoming movements in the crypto market, identifying profit opportunities.">
        <IconList items={WHY} />
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            Start AI trading for free
          </Link>
        </div>
      </Section>

      <Section
        eyebrow="Strategies"
        title="Discover AI trading strategies"
        lead="Explore a variety of AI trading and investment strategies. View performance history, understand how they work and start trading with ease.">
        <FeatureGrid features={STRATEGIES} columns={3} />
      </Section>

      <Section
        eyebrow="Predictions"
        title="AI crypto predictions"
        lead="OctoBot leverages ChatGPT to analyze the cryptocurrency market and predict potential price fluctuations.">
        <FeatureGrid features={PREDICTIONS} columns={3} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={AI_GUIDE}>
            See all predictions
          </Link>
        </div>
      </Section>

      <Section eyebrow="FAQ" title="AI trading bot FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Put AI to work on your portfolio"
        description="Create your AI trading bot for free on OctoBot Cloud, or read the guide first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the AI guide', to: AI_GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
