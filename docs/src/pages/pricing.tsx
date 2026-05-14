import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
    tag: translate({
      id: 'pages.pricing.plans.investor.tag',
      message: 'Investor',
      description: 'Pricing plan tag',
    }),
    price: '€0',
    label: translate({
      id: 'pages.pricing.plans.investor.label',
      message: 'Free forever',
      description: 'Pricing plan label',
    }),
    note: translate({
      id: 'pages.pricing.plans.investor.note',
      message:
        'Run automated strategies at no cost — unlock extra features through missions.',
      description: 'Pricing plan note',
    }),
  },
  {
    tag: translate({
      id: 'pages.pricing.plans.investorPlus.tag',
      message: 'Investor Plus',
      description: 'Pricing plan tag',
    }),
    price: '14d',
    priceSuffix: translate({
      id: 'pages.pricing.plans.investorPlus.priceSuffix',
      message: ' free',
      description: 'Pricing plan price suffix',
    }),
    label: translate({
      id: 'pages.pricing.plans.investorPlus.label',
      message: 'The full experience',
      description: 'Pricing plan label',
    }),
    note: translate({
      id: 'pages.pricing.plans.investorPlus.note',
      message:
        'Advanced strategies, more simultaneous bots, portfolio fine-tuning and AI.',
      description: 'Pricing plan note',
    }),
    variant: 'feat',
  },
  {
    tag: translate({
      id: 'pages.pricing.plans.pro.tag',
      message: 'Pro',
      description: 'Pricing plan tag',
    }),
    price: translate({
      id: 'pages.pricing.plans.pro.price',
      message: 'Pro',
      description: 'Pricing plan price',
    }),
    label: translate({
      id: 'pages.pricing.plans.pro.label',
      message: 'For power users',
      description: 'Pricing plan label',
    }),
    note: translate({
      id: 'pages.pricing.plans.pro.note',
      message:
        'Everything in Plus, futures trading, personalized arbitrage and priority support.',
      description: 'Pricing plan note',
    }),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'pages.pricing.faq.q1.question',
      message: 'What will happen after the free sign up?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q1.answer',
      message:
        'After you sign up, you can start a 14-day free trial, letting you enjoy the full Investor Plus plan benefits. Once those 14 days are over, your account will either switch to the free Investor plan if you did not enter any payment method, or automatically switch to the selected paid plan using your payment method.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q2.question',
      message: 'What are the supported payment methods?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q2.answer',
      message:
        'You can pay for your monthly and yearly subscriptions using either credit cards or cryptocurrencies.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q3.question',
      message: 'What will happen once my paid plan is over?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q3.answer',
      message:
        'Once your paid plan is over, if you did not renew it, you will be downgraded to the free Investor plan, and any bot or advantage depending on the expired plan will be stopped.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q4.question',
      message: 'How many bots can I use?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q4.answer',
      message:
        'According to your selected plan and reward level, you can use up to 20 simultaneous OctoBots.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q5.question',
      message: 'What are unlockable features?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q5.answer',
      message:
        'The Investor plan is free and contains a few features that become available after succeeding in missions — such as starting an OctoBot, inviting a friend and more.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q6.question',
      message: 'Does OctoBot take any fees from trades?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q6.answer',
      message:
        'No. OctoBot only charges a monthly subscription on paid plans. There is no extra or hidden fee.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q7.question',
      message: 'Can I switch plans?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q7.answer',
      message: 'Yes, you can switch to a different plan at any time.',
      description: 'Pricing FAQ answer',
    }),
  },
  {
    question: translate({
      id: 'pages.pricing.faq.q8.question',
      message: 'Can OctoBot trade stocks or forex markets?',
      description: 'Pricing FAQ question',
    }),
    answer: translate({
      id: 'pages.pricing.faq.q8.answer',
      message:
        'No, OctoBot can only trade crypto markets on the supported exchanges.',
      description: 'Pricing FAQ answer',
    }),
  },
];

export default function PricingPage(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.pricing.meta.title',
        message: 'Plans & pricing',
        description: 'Pricing page metadata title',
      })}
      description={translate({
        id: 'pages.pricing.meta.description',
        message:
          'OctoBot Cloud offers a subscription plan for every type of investor — start free and upgrade only when you need more.',
        description: 'Pricing page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.pricing.hero.eyebrow',
          message: 'Pricing',
          description: 'Pricing hero eyebrow',
        })}
        title={
          <Translate
            id="pages.pricing.hero.title"
            description="Pricing hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  {translate({
                    id: 'pages.pricing.hero.title.accent',
                    message: 'pricing.',
                    description: 'Pricing hero title accent word',
                  })}
                </span>
              ),
            }}>
            {'Plans & {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'pages.pricing.hero.subtitle',
          message:
            'OctoBot Cloud offers a subscription plan for every type of investor — start free and upgrade only when you need more.',
          description: 'Pricing hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.pricing.hero.action.start',
              message: 'Start investing',
              description: 'Pricing hero action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.pricing.hero.action.guides',
              message: 'Read the guides',
              description: 'Pricing hero action label',
            }),
            to: GUIDE,
            variant: 'ghost',
          },
        ]}
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'pages.pricing.plansSection.eyebrow',
          message: 'Plans',
          description: 'Pricing section eyebrow',
        })}
        title={translate({
          id: 'pages.pricing.plansSection.title',
          message: 'Choose the OctoBot that fits your needs',
          description: 'Pricing section title',
        })}>
        <PricingStrip cells={PLANS} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.pricing.compare.eyebrow',
          message: 'Compare',
          description: 'Pricing section eyebrow',
        })}
        title={translate({
          id: 'pages.pricing.compare.title',
          message: 'Compare OctoBot plans',
          description: 'Pricing section title',
        })}>
        <FeatureComparison />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.pricing.faqSection.eyebrow',
          message: 'FAQ',
          description: 'Pricing section eyebrow',
        })}
        title={translate({
          id: 'pages.pricing.faqSection.title',
          message: 'Pricing FAQ',
          description: 'Pricing section title',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'pages.pricing.cta.title',
          message: "Start free, upgrade when you're ready",
          description: 'Pricing CTA title',
        })}
        description={translate({
          id: 'pages.pricing.cta.description',
          message:
            'Create your account on OctoBot Cloud and run your first strategy at no cost.',
          description: 'Pricing CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.pricing.cta.action.start',
              message: 'Start investing',
              description: 'Pricing CTA action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'pages.pricing.cta.action.guides',
              message: 'Read the guides',
              description: 'Pricing CTA action label',
            }),
            to: GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
