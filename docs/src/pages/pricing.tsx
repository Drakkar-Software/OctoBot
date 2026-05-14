import type {ReactNode} from 'react';
import {
  LandingLayout,
  Hero,
  Section,
  PricingStrip,
  FAQ,
  CTABand,
  type PriceCell,
  type FAQItem,
} from '@site/src/components/landing';
import FeatureComparison from '@site/src/components/pages/pricing/FeatureComparison';
import styles from './pricing.module.css';

/*
 * Pricing marketing page — route: /pricing.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit: a navbar-less LandingLayout composed from reusable
 * landing components plus the page-local FeatureComparison table.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDE = '/guides/octobot';

const PLANS: PriceCell[] = [
  {
    tag: 'Investor',
    price: '€0',
    label: 'Free forever',
    note: 'Run automated strategies at no cost — unlock extra features through missions.',
  },
  {
    tag: 'Investor Plus',
    price: '14d',
    priceSuffix: ' free',
    label: 'The full experience',
    note: 'Advanced strategies, more simultaneous bots, portfolio fine-tuning and AI.',
    variant: 'feat',
  },
  {
    tag: 'Pro',
    price: 'Pro',
    label: 'For power users',
    note: 'Everything in Plus, futures trading, personalized arbitrage and priority support.',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'What will happen after the free sign up?',
    answer:
      'After you sign up, you can start a 14-day free trial, letting you enjoy the full Investor Plus plan benefits. Once those 14 days are over, your account will either switch to the free Investor plan if you did not enter any payment method, or automatically switch to the selected paid plan using your payment method.',
  },
  {
    question: 'What are the supported payment methods?',
    answer:
      'You can pay for your monthly and yearly subscriptions using either credit cards or cryptocurrencies.',
  },
  {
    question: 'What will happen once my paid plan is over?',
    answer:
      'Once your paid plan is over, if you did not renew it, you will be downgraded to the free Investor plan, and any bot or advantage depending on the expired plan will be stopped.',
  },
  {
    question: 'How many bots can I use?',
    answer:
      'According to your selected plan and reward level, you can use up to 20 simultaneous OctoBots.',
  },
  {
    question: 'What are unlockable features?',
    answer:
      'The Investor plan is free and contains a few features that become available after succeeding in missions — such as starting an OctoBot, inviting a friend and more.',
  },
  {
    question: 'Does OctoBot take any fees from trades?',
    answer:
      'No. OctoBot only charges a monthly subscription on paid plans. There is no extra or hidden fee.',
  },
  {
    question: 'Can I switch plans?',
    answer: 'Yes, you can switch to a different plan at any time.',
  },
  {
    question: 'Can OctoBot trade stocks or forex markets?',
    answer:
      'No, OctoBot can only trade crypto markets on the supported exchanges.',
  },
];

export default function PricingPage(): ReactNode {
  return (
    <LandingLayout
      title="Plans & pricing"
      description="OctoBot Cloud offers a subscription plan for every type of investor — start free and upgrade only when you need more.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Pricing"
        title={
          <>
            Plans &amp; <span className="ng-text-gradient">pricing.</span>
          </>
        }
        subtitle="OctoBot Cloud offers a subscription plan for every type of investor — start free and upgrade only when you need more."
        actions={[
          {label: 'Start investing', to: CLOUD},
          {label: 'Read the guides', to: GUIDE, variant: 'ghost'},
        ]}
      />

      <Section
        align="left"
        eyebrow="Plans"
        title="Choose the OctoBot that fits your needs">
        <PricingStrip cells={PLANS} />
      </Section>

      <Section eyebrow="Compare" title="Compare OctoBot plans">
        <FeatureComparison />
      </Section>

      <Section eyebrow="FAQ" title="Pricing FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Start free, upgrade when you're ready"
        description="Create your account on OctoBot Cloud and run your first strategy at no cost."
        actions={[
          {label: 'Start investing', to: CLOUD},
          {label: 'Read the guides', to: GUIDE, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
