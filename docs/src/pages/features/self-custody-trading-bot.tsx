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
import GlassCard from '@site/src/components/GlassCard';
import styles from './_styles.module.css';

/*
 * Self Custody Trading Bot feature page — route:
 * /features/self-custody-trading-bot.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components.
 */

const CLOUD = 'https://www.octobot.cloud';
const SELF_CUSTODY_BLOG = '/blog/how-to-use-a-self-custody-crypto-trading-bot';

const WHY: IconListItem[] = [
  {
    icon: '🔑',
    text: (
      <>
        <strong>Your keys, your coins:</strong> your keys never leave your
        devices.
      </>
    ),
  },
  {
    icon: '🔀',
    text: (
      <>
        <strong>Flexible:</strong> trade on both centralized and decentralized
        exchanges.
      </>
    ),
  },
  {
    icon: '🧰',
    text: (
      <>
        <strong>Versatile:</strong> run strategies based on DCA, AI, grid,
        crypto baskets, TradingView and more.
      </>
    ),
  },
  {
    icon: '📱',
    text: (
      <>
        <strong>Anytime &amp; anywhere:</strong> configure and execute
        strategies from your phone.
      </>
    ),
  },
];

const UNIQUE: Feature[] = [
  {
    icon: '🛡️',
    title: 'Maximum security',
    description:
      'You are the only one with access to your crypto keys. No leakage possible — even the OctoBot team cannot access your keys.',
  },
  {
    icon: '🧩',
    title: 'Open community',
    description:
      'Use the same strategy as your friends for free and in a few clicks, on your favorite centralized or decentralized exchange.',
  },
  {
    icon: '🔄',
    title: 'Boost your bot',
    description:
      'If your phone cannot execute your bot correctly, you can help it with your own personal mini-cloud.',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What is a self custody trading bot?',
    answer: (
      <>
        A self custody trading bot is a trading bot fully controlled by you, its
        user. It is not controlled by a central authority such as a crypto
        exchange or a trading-bot platform that holds your API (or wallet) keys.
        More info on our{' '}
        <Link to={SELF_CUSTODY_BLOG}>dedicated blog post</Link>.
      </>
    ),
  },
  {
    question:
      'What is the difference between a self custody trading bot and another trading bot?',
    answer: (
      <>
        A self custody trading bot is not running on someone else&apos;s
        servers — you always have complete control over your API (or wallet)
        keys. It makes it much more secure and flexible than other trading bots.
        More info on our{' '}
        <Link to={SELF_CUSTODY_BLOG}>dedicated blog post</Link>.
      </>
    ),
  },
  {
    question:
      'What is the difference between OctoBot self-custody and OctoBot Cloud or open source?',
    answer:
      'OctoBot self-custody is as simple to use as OctoBot Cloud but runs on your own mobile. It gives you complete control over your API (or wallet) keys and works with centralized or decentralized exchanges. It is designed to stay easy to use while remaining very flexible — and it is much easier to use than the open-source OctoBot, which requires more technical knowledge and a computer or server to operate.',
  },
  {
    question: 'Are centralized exchanges supported?',
    answer:
      'Yes — a self custody trading bot can connect to both centralized and decentralized exchanges, and in both cases it greatly increases the security of your crypto assets.',
  },
  {
    question: 'Are decentralized exchanges supported?',
    answer:
      'Yes — a self custody trading bot can automate strategies on decentralized exchanges.',
  },
  {
    question: 'What kind of strategies can I automate?',
    answer:
      'We expect to support all the strategies available on OctoBot Cloud, including DCA, AI, grid trading, crypto baskets, TradingView strategies and more.',
  },
  {
    question: 'How can it work on a phone?',
    answer:
      'A self custody trading bot can run on any device with an internet connection that allows installing an app. There are many challenges to making it work properly on a phone compared to a regular computer — we are taking care of that for you.',
  },
  {
    question: 'What does a personal mini-cloud mean?',
    answer:
      'A personal mini-cloud is a secure personal server you can use to execute part of your self custody trading bot, for strategies that some phones cannot run reliably. It may not be necessary — it depends on your phone, your connection and your strategies. It is a server created by you and automatically configured by the app, using an account that belongs to you. It is not owned by the OctoBot team: it is your own server, which you alone have access to.',
  },
  {
    question: 'When will it be available?',
    answer:
      'We are working on it and will launch it very soon. Register for early access to be the first to use it.',
  },
];

export default function SelfCustodyTradingBotFeature(): ReactNode {
  return (
    <LandingLayout
      title="Self Custody Trading Bot"
      description="Automate your investment strategies for free, from your phone, on centralized and decentralized exchanges. Your keys stay on your phone, always.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Self custody trading bot"
        title={
          <>
            Your investment strategies,{' '}
            <span className="ng-text-gradient">on your phone.</span>
          </>
        }
        subtitle="Automate your investment strategies simply, without sharing your keys — from your phone, on centralized and decentralized exchanges."
        actions={[
          {label: 'Learn more', to: SELF_CUSTODY_BLOG},
          {label: 'Read the guides', to: '/guides/octobot', variant: 'ghost'},
        ]}
        meta={[
          {label: 'Keys never leave your device', dot: true},
          {label: 'CEX & DEX'},
          {label: 'Early access soon'},
        ]}
      />

      <Section
        align="left"
        eyebrow="Why self-custody"
        title="A new kind of trading bot for today's crypto market"
        lead="With the rise of decentralized exchanges, new strategy opportunities are emerging. The first investors to take advantage of them will make the largest gains.">
        <IconList items={WHY} />
      </Section>

      <Section
        eyebrow="What's unique"
        title="What makes OctoBot self-custody unique"
        lead="Security, community and resilience — without giving up control of your keys.">
        <FeatureGrid features={UNIQUE} columns={3} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={SELF_CUSTODY_BLOG}>
            Learn more on self-custody trading bots
          </Link>
        </div>
      </Section>

      <Section align="left" eyebrow="Early access">
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h3 className={styles.panelTitle}>
            Interested in automating your strategies from your phone?
          </h3>
          <p className={styles.panelText}>
            Be one of the first to use our new self custody trading bot mobile
            app. Register for early access to be notified when it is available.
          </p>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            Join the early access
          </Link>
        </GlassCard>
      </Section>

      <Section eyebrow="FAQ" title="Self custody trading bot FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Your strategies. Your keys. Your phone."
        description="Read how a self-custody trading bot works, or register for early access."
        actions={[
          {label: 'Join the early access', to: CLOUD},
          {label: 'Read the blog post', to: SELF_CUSTODY_BLOG, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
