import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  BeforeAfter,
  LogoRibbon,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type FAQItem,
} from '@site/src/components/landing';

/*
 * Market Making product feature page — route: /features/market-making.
 *
 * Migrated from the OctoBot Market Making marketing site into the Neo Glass
 * Dark landing toolkit. Built the same way as src/pages/welcome.tsx: a
 * navbar-less LandingLayout composed entirely from reusable components.
 */

const CALL_URL = 'https://cal.com/octobot.cloud/market-making-30min';
const CONTACT_MAIL = 'mailto:contact@octobot.cloud';

const STEPS: Step[] = [
  {
    icon: '🔍',
    title: translate({
      id: 'features.marketMaking.steps.analyze.title',
      message: "Analyze your market's liquidity",
      description: 'Step title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.steps.analyze.description',
      message:
        'Find the markets that need a liquidity boost using the Liquidity Score.',
      description: 'Step description on market making page',
    }),
  },
  {
    icon: '🎯',
    title: translate({
      id: 'features.marketMaking.steps.configure.title',
      message: 'Configure your liquidity target',
      description: 'Step title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.steps.configure.description',
      message:
        'Let the platform guide you to your target, or bring your own configuration.',
      description: 'Step description on market making page',
    }),
  },
  {
    icon: '📖',
    title: translate({
      id: 'features.marketMaking.steps.preview.title',
      message: 'Preview your market making strategy',
      description: 'Step title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.steps.preview.description',
      message:
        'View and adapt the order book your bot will maintain before it goes live.',
      description: 'Step description on market making page',
    }),
  },
];

const FEATURES: Feature[] = [
  {
    icon: '📊',
    title: translate({
      id: 'features.marketMaking.features.orderBook.title',
      message: 'Advanced order book management',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.orderBook.description',
      message:
        'Maintain optimal liquidity depth with intelligent order placement and rebalancing algorithms.',
      description: 'Feature description on market making page',
    }),
  },
  {
    icon: '🛡️',
    title: translate({
      id: 'features.marketMaking.features.risk.title',
      message: 'Risk management system',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.risk.description',
      message:
        'Set volatility limits and dedicated budgets to protect your capital.',
      description: 'Feature description on market making page',
    }),
  },
  {
    icon: '🧩',
    title: translate({
      id: 'features.marketMaking.features.openSource.title',
      message: 'Open-source engine',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.openSource.description',
      message:
        'Always be in control. OctoBot Market Making is open source — no black box.',
      description: 'Feature description on market making page',
    }),
  },
  {
    icon: '🔗',
    title: translate({
      id: 'features.marketMaking.features.multiExchange.title',
      message: 'Multi-exchange integration',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.multiExchange.description',
      message:
        'Connect to more than 15 major exchanges through a single platform.',
      description: 'Feature description on market making page',
    }),
  },
  {
    icon: '🔄',
    title: translate({
      id: 'features.marketMaking.features.rebalancing.title',
      message: 'Automated rebalancing',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.rebalancing.description',
      message:
        'Keep your inventory optimally positioned across markets and exchanges with smart rebalancing.',
      description: 'Feature description on market making page',
    }),
  },
  {
    icon: '⚙️',
    title: translate({
      id: 'features.marketMaking.features.customizable.title',
      message: 'Customizable strategies',
      description: 'Feature title on market making page',
    }),
    description: translate({
      id: 'features.marketMaking.features.customizable.description',
      message:
        'Fine-tune the market making algorithm parameters to meet your goals.',
      description: 'Feature description on market making page',
    }),
  },
];

const EXCHANGES = [
  'BINANCE',
  'KUCOIN',
  'MEXC',
  'COINEX',
  'COINBASE',
  'CRYPTO.COM',
  'HTX',
  'BITMART',
  'ASCENDEX',
  'BITGET',
  'HOLLAEX',
  '+ MORE',
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.marketMaking.faq.q1.question',
      message: 'What is a market maker in crypto?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q1.answer',
      message:
        'A market maker in crypto is a person or organization that provides liquidity to crypto markets by creating buy and sell orders simultaneously on the order books. It helps reduce spreads, increases trading volume, and improves market efficiency by ensuring there are always orders available for traders to buy from and sell to.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q2.question',
      message: 'What exchanges are supported by OctoBot Market Making?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q2.answer',
      message:
        'OctoBot Market Making supports most popular centralized exchanges including Binance, Kucoin, MEXC, CoinEx, Coinbase, Crypto.com, HTX, BitMart, Ascendex, Bitget, all HollaEx-powered exchanges and more.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q3.question',
      message: 'How much capital is required for effective market making?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q3.answer',
      message:
        "Capital requirements depend on the asset's typical trading volume and desired market impact. In general, effective market making requires enough capital to contain at least 2% of the exchange's daily trading volume within the top of the order book. The OctoBot Market Making team can provide specific recommendations based on your token's trading profile.",
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q4.question',
      message: 'What is a market making strategy?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q4.answer',
      message:
        'A market making strategy is the process of providing liquidity to trading markets by simultaneously placing limit buy and sell orders to populate the order book and facilitate the execution of trades on that market.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q5.question',
      message: 'How to become a market maker in crypto?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q5.answer',
      message:
        'To become a crypto market maker you need an automated market making strategy and initial capital to deploy with it. OctoBot Market Making is a platform to simply automate a market making strategy and can help you get started with minimum capital requirements.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q6.question',
      message: 'How do crypto market makers make money?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q6.answer',
      message:
        'Crypto market makers make money by extracting profit from the trades they facilitate, similar to an advanced and large-scale grid trading strategy.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q7.question',
      message: 'What are the risks of market making?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q7.answer',
      message:
        'The main risk of a market maker is holding an asset that may decline in value. As a market facilitator, a market maker mostly buys when others are selling, and might therefore hold large amounts of an asset if its price declines dramatically.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q8.question',
      message: 'Can anyone be a market maker?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q8.answer',
      message:
        'Yes — a market maker can be an individual or an organization, as long as they are legally allowed to be market participants of the market they want to make.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q9.question',
      message: 'What does OctoBot Market Making do?',
      description: 'FAQ question on market making page',
    }),
    answer: translate({
      id: 'features.marketMaking.faq.q9.answer',
      message:
        'OctoBot Market Making makes automated market making strategies accessible by offering a self-service platform to create, configure, monitor and improve market making strategies on most centralized cryptocurrency exchanges.',
      description: 'FAQ answer on market making page',
    }),
  },
  {
    question: translate({
      id: 'features.marketMaking.faq.q10.question',
      message: 'Is OctoBot open source?',
      description: 'FAQ question on market making page',
    }),
    answer: (
      <Translate
        id="features.marketMaking.faq.q10.answer"
        description="FAQ answer on market making page"
        values={{
          githubLink: (
            <a href="https://github.com/Drakkar-Software/OctoBot">GitHub</a>
          ),
        }}>
        {
          'Yes — the code is on {githubLink}. OctoBot Market Making is based on the market making distribution of OctoBot to execute its strategies.'
        }
      </Translate>
    ),
  },
];

export default function MarketMakingFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.marketMaking.layout.title',
        message: 'OctoBot Market Making — Liquidity as a service',
        description: 'Page meta title for market making page',
      })}
      description={translate({
        id: 'features.marketMaking.layout.description',
        message:
          'OctoBot Market Making is a professional, open-source market making as a service platform for crypto projects, exchanges and liquidity miners.',
        description: 'Page meta description for market making page',
      })}>
      <Hero
        eyebrow={translate({
          id: 'features.marketMaking.hero.eyebrow',
          message: 'Market Making',
          description: 'Hero eyebrow on market making page',
        })}
        title={
          <Translate
            id="features.marketMaking.hero.title"
            description="Hero title on market making page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.marketMaking.hero.accent"
                    description="Accent text in hero title on market making page">
                    crypto projects.
                  </Translate>
                </span>
              ),
            }}>
            {'Market making as a service for {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.marketMaking.hero.subtitle',
          message:
            "Boost your market's liquidity with OctoBot Market Making — a professional crypto market making as a service platform.",
          description: 'Hero subtitle on market making page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.marketMaking.hero.action.boost',
              message: 'Boost my liquidity',
              description: 'Hero action label on market making page',
            }),
            to: CALL_URL,
          },
          {
            label: translate({
              id: 'features.marketMaking.hero.action.call',
              message: 'Book a free call',
              description: 'Hero action label on market making page',
            }),
            to: CALL_URL,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.marketMaking.hero.meta.exchanges',
              message: '15+ exchanges supported',
              description: 'Hero meta label on market making page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.marketMaking.hero.meta.openSource',
              message: 'Open source engine',
              description: 'Hero meta label on market making page',
            }),
          },
          {
            label: translate({
              id: 'features.marketMaking.hero.meta.selfService',
              message: 'Self-service platform',
              description: 'Hero meta label on market making page',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'features.marketMaking.howItWorks.eyebrow',
          message: 'How it works',
          description: 'Section eyebrow on market making page',
        })}
        title={translate({
          id: 'features.marketMaking.howItWorks.title',
          message: 'Improve your liquidity in 3 simple steps',
          description: 'Section title on market making page',
        })}
        lead={translate({
          id: 'features.marketMaking.howItWorks.lead',
          message:
            'From spotting a thin market to maintaining a healthy order book — guided the whole way.',
          description: 'Section lead on market making page',
        })}>
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.marketMaking.platform.eyebrow',
          message: 'The platform',
          description: 'Section eyebrow on market making page',
        })}
        title={translate({
          id: 'features.marketMaking.platform.title',
          message: 'Institutional-grade market making',
          description: 'Section title on market making page',
        })}
        lead={translate({
          id: 'features.marketMaking.platform.lead',
          message:
            'Professional crypto market making software, available as a self-service platform.',
          description: 'Section lead on market making page',
        })}>
        <FeatureGrid features={FEATURES} columns={3} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.marketMaking.whyItMatters.eyebrow',
          message: 'Why it matters',
          description: 'Section eyebrow on market making page',
        })}
        title={
          <Translate
            id="features.marketMaking.whyItMatters.title"
            description="Section title on market making page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.marketMaking.whyItMatters.accent"
                    description="Accent text in why-it-matters title on market making page">
                    a market that works.
                  </Translate>
                </span>
              ),
            }}>
            {'The cost of poor liquidity vs. {accent}'}
          </Translate>
        }>
        <BeforeAfter
          before={{
            label: translate({
              id: 'features.marketMaking.beforeAfter.before.label',
              message: 'Poor liquidity',
              description: 'BeforeAfter before label on market making page',
            }),
            items: [
              <Translate
                id="features.marketMaking.beforeAfter.before.item1"
                description="BeforeAfter before item on market making page"
                values={{strong: <strong>Delisting risk</strong>}}>
                {'{strong} on popular exchanges'}
              </Translate>,
              <Translate
                id="features.marketMaking.beforeAfter.before.item2"
                description="BeforeAfter before item on market making page"
                values={{strong: <strong>wide spreads</strong>}}>
                {'Thin order books, {strong}'}
              </Translate>,
              <Translate
                id="features.marketMaking.beforeAfter.before.item3"
                description="BeforeAfter before item on market making page"
                values={{strong: <strong>unattractive market</strong>}}>
                {'An {strong} for traders'}
              </Translate>,
            ],
          }}
          after={{
            label: translate({
              id: 'features.marketMaking.beforeAfter.after.label',
              message: 'With OctoBot Market Making',
              description: 'BeforeAfter after label on market making page',
            }),
            items: [
              <Translate
                id="features.marketMaking.beforeAfter.after.item1"
                description="BeforeAfter after item on market making page"
                values={{strong: <strong>Deeper order books</strong>}}>
                {'{strong} attract investors'}
              </Translate>,
              <Translate
                id="features.marketMaking.beforeAfter.after.item2"
                description="BeforeAfter after item on market making page"
                values={{strong: <strong>Tighter spreads</strong>}}>
                {'{strong}, healthier markets'}
              </Translate>,
              <Translate
                id="features.marketMaking.beforeAfter.after.item3"
                description="BeforeAfter after item on market making page"
                values={{strong: <strong>improve liquidity</strong>}}>
                {'Measure & {strong} any time'}
              </Translate>,
            ],
          }}
        />
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'features.marketMaking.distribution.eyebrow',
          message: 'Distribution',
          description: 'Section eyebrow on market making page',
        })}
        title={
          <Translate
            id="features.marketMaking.distribution.title"
            description="Section title on market making page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.marketMaking.distribution.accent"
                    description="Accent text in distribution title on market making page">
                    exchanges that matter.
                  </Translate>
                </span>
              ),
            }}>
            {'Supported on the {accent}'}
          </Translate>
        }>
        <LogoRibbon items={EXCHANGES} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.marketMaking.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on market making page',
        })}
        title={translate({
          id: 'features.marketMaking.faq.title',
          message: 'Frequently asked questions',
          description: 'FAQ section title on market making page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.marketMaking.cta.title',
          message: "Ready to optimize your market's liquidity?",
          description: 'CTA band title on market making page',
        })}
        description={translate({
          id: 'features.marketMaking.cta.description',
          message:
            'Schedule a call with our team to discuss your specific needs — or email us any question.',
          description: 'CTA band description on market making page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.marketMaking.cta.action.call',
              message: 'Book a free call',
              description: 'CTA action label on market making page',
            }),
            to: CALL_URL,
          },
          {
            label: translate({
              id: 'features.marketMaking.cta.action.email',
              message: 'Email us',
              description: 'CTA action label on market making page',
            }),
            to: CONTACT_MAIL,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
