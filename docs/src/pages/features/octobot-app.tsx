import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  StatStrip,
  PricingStrip,
  Testimonials,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type Stat,
  type PriceCell,
  type Testimonial,
  type FAQItem,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';

/*
 * OctoBot App product feature page — route: /features/octobot-app.
 *
 * Migrated from the OctoBot consumer-investing marketing site into the
 * Neo Glass Dark landing toolkit. Built the same way as src/pages/welcome.tsx:
 * a navbar-less LandingLayout composed entirely from reusable components.
 */

const CLOUD_URL = 'https://www.octobot.cloud';

const FEATURES: Feature[] = [
  {
    icon: '🧠',
    title: translate({
      id: 'features.octobotApp.features.ai.title',
      message: 'AI trading strategies',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.ai.description',
      message:
        'Let AI models analyze the market and manage your funds — no ChatGPT subscription, paper-trade first.',
      description: 'Feature description on OctoBot App page',
    }),
    to: '/guides/octobot-trading-modes/chatgpt-trading',
  },
  {
    icon: '🧺',
    title: translate({
      id: 'features.octobotApp.features.baskets.title',
      message: 'Crypto baskets',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.baskets.description',
      message:
        'Theme-based portfolios that diversify your investments and auto-rebalance as the market moves.',
      description: 'Feature description on OctoBot App page',
    }),
    to: '/guides/octobot-usage/strategy-designer',
  },
  {
    icon: '📈',
    title: translate({
      id: 'features.octobotApp.features.tradingview.title',
      message: 'TradingView automation',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.tradingview.description',
      message:
        'Automate any TradingView strategy, or generate a Pine Script strategy from a plain-language prompt.',
      description: 'Feature description on OctoBot App page',
    }),
    to: '/guides/octobot-interfaces/tradingview',
  },
  {
    icon: '🔒',
    title: translate({
      id: 'features.octobotApp.features.selfCustody.title',
      message: 'Self-custody first',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.selfCustody.description',
      message:
        'Your API keys and wallets never leave your device. You stay in control, always.',
      description: 'Feature description on OctoBot App page',
    }),
    to: '/blog/how-to-use-a-self-custody-crypto-trading-bot',
  },
  {
    icon: '🧪',
    title: translate({
      id: 'features.octobotApp.features.paperTrading.title',
      message: 'Paper trading',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.paperTrading.description',
      message:
        'Try any basket or strategy with virtual money before risking a single real coin.',
      description: 'Feature description on OctoBot App page',
    }),
    to: '/guides/octobot-usage/simulator',
  },
  {
    icon: '🧩',
    title: translate({
      id: 'features.octobotApp.features.openSource.title',
      message: 'Open source',
      description: 'Feature title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.features.openSource.description',
      message:
        'MIT-licensed and community-driven since 2018. Read, audit and shape the code yourself.',
      description: 'Feature description on OctoBot App page',
    }),
    to: 'https://github.com/Drakkar-Software/OctoBot',
  },
];

const STEPS: Step[] = [
  {
    icon: '⚡',
    title: translate({
      id: 'features.octobotApp.steps.strategy.title',
      message: 'Pick your strategy',
      description: 'Step title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.steps.strategy.description',
      message:
        'Choose a ready-made investment strategy or crypto basket — or design your own.',
      description: 'Step description on OctoBot App page',
    }),
  },
  {
    icon: '🔗',
    title: translate({
      id: 'features.octobotApp.steps.exchange.title',
      message: 'Select your exchange',
      description: 'Step title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.steps.exchange.description',
      message:
        'Connect one of the leading exchanges OctoBot partners with in a couple of clicks.',
      description: 'Step description on OctoBot App page',
    }),
  },
  {
    icon: '📊',
    title: translate({
      id: 'features.octobotApp.steps.gains.title',
      message: 'Follow your gains',
      description: 'Step title on OctoBot App page',
    }),
    description: translate({
      id: 'features.octobotApp.steps.gains.description',
      message:
        'Watch performance from any browser or your phone while OctoBot runs on autopilot.',
      description: 'Step description on OctoBot App page',
    }),
  },
];

const STATS: Stat[] = [
  {
    value: <span className="ng-text-gradient">50K</span>,
    label: translate({
      id: 'features.octobotApp.stats.running.label',
      message: 'OctoBots running worldwide',
      description: 'Stat label on OctoBot App page',
    }),
    sub: translate({
      id: 'features.octobotApp.stats.running.sub',
      message: 'self-hosted · global',
      description: 'Stat sub-label on OctoBot App page',
    }),
  },
  {
    value: <span className="ng-text-gradient">10M+</span>,
    label: translate({
      id: 'features.octobotApp.stats.trades.label',
      message: 'Trades executed',
      description: 'Stat label on OctoBot App page',
    }),
    sub: translate({
      id: 'features.octobotApp.stats.trades.sub',
      message: 'cumulative to date',
      description: 'Stat sub-label on OctoBot App page',
    }),
  },
  {
    value: <span className="ng-text-gradient">6K+</span>,
    label: translate({
      id: 'features.octobotApp.stats.stars.label',
      message: 'GitHub stars',
      description: 'Stat label on OctoBot App page',
    }),
    sub: translate({
      id: 'features.octobotApp.stats.stars.sub',
      message: 'since 2018 · organic',
      description: 'Stat sub-label on OctoBot App page',
    }),
  },
];

const PRICING: PriceCell[] = [
  {
    tag: translate({
      id: 'features.octobotApp.pricing.investor.tag',
      message: 'Investor',
      description: 'Pricing plan tag on OctoBot App page',
    }),
    price: translate({
      id: 'features.octobotApp.pricing.investor.price',
      message: '€0',
      description: 'Pricing plan price on OctoBot App page',
    }),
    label: translate({
      id: 'features.octobotApp.pricing.investor.label',
      message: 'Free forever',
      description: 'Pricing plan label on OctoBot App page',
    }),
    note: translate({
      id: 'features.octobotApp.pricing.investor.note',
      message:
        'Run automated strategies at no cost. Unlock extra features through missions.',
      description: 'Pricing plan note on OctoBot App page',
    }),
  },
  {
    tag: translate({
      id: 'features.octobotApp.pricing.investorPlus.tag',
      message: 'Investor Plus',
      description: 'Pricing plan tag on OctoBot App page',
    }),
    price: translate({
      id: 'features.octobotApp.pricing.investorPlus.price',
      message: '14d',
      description: 'Pricing plan price on OctoBot App page',
    }),
    priceSuffix: translate({
      id: 'features.octobotApp.pricing.investorPlus.priceSuffix',
      message: ' free',
      description: 'Pricing plan price suffix on OctoBot App page',
    }),
    label: translate({
      id: 'features.octobotApp.pricing.investorPlus.label',
      message: 'The full experience',
      description: 'Pricing plan label on OctoBot App page',
    }),
    note: translate({
      id: 'features.octobotApp.pricing.investorPlus.note',
      message:
        'Advanced strategies, more simultaneous bots, portfolio fine-tuning and AI.',
      description: 'Pricing plan note on OctoBot App page',
    }),
    variant: 'feat',
  },
  {
    tag: translate({
      id: 'features.octobotApp.pricing.pro.tag',
      message: 'Pro',
      description: 'Pricing plan tag on OctoBot App page',
    }),
    price: translate({
      id: 'features.octobotApp.pricing.pro.price',
      message: 'Pro',
      description: 'Pricing plan price on OctoBot App page',
    }),
    label: translate({
      id: 'features.octobotApp.pricing.pro.label',
      message: 'For power users',
      description: 'Pricing plan label on OctoBot App page',
    }),
    note: translate({
      id: 'features.octobotApp.pricing.pro.note',
      message:
        'Everything in Plus, futures trading, personalized arbitrage and priority support.',
      description: 'Pricing plan note on OctoBot App page',
    }),
  },
];

const FEATURED_TESTIMONIAL: Testimonial = {
  quote: translate({
    id: 'features.octobotApp.testimonials.featured.quote',
    message:
      "I've been using OctoBot with these settings for a while now, tweaking them. Over the past year I'm at an overall profit of about 1000% (3K → 30K). Insane.",
    description: 'Featured testimonial quote on OctoBot App page',
  }),
  name: translate({
    id: 'features.octobotApp.testimonials.featured.name',
    message: 'OctoBot user',
    description: 'Featured testimonial name on OctoBot App page',
  }),
  role: translate({
    id: 'features.octobotApp.testimonials.featured.role',
    message: 'Community member since 2022',
    description: 'Featured testimonial role on OctoBot App page',
  }),
  avatar: 'linear-gradient(135deg, #65e7cf, #4893f1)',
};

const TESTIMONIALS: Testimonial[] = [
  {
    quote: translate({
      id: 'features.octobotApp.testimonials.t1.quote',
      message:
        'I have been using OctoBot for a couple of years now and it has been an incredible journey. The fact that it is open source means the possibilities are endless.',
      description: 'Testimonial quote on OctoBot App page',
    }),
    name: 'Tim Hermans',
    role: translate({
      id: 'features.octobotApp.testimonials.t1.role',
      message: 'Community member since 2021',
      description: 'Testimonial role on OctoBot App page',
    }),
    avatar: 'linear-gradient(135deg, #85d6d7, #6cb596)',
  },
  {
    quote: translate({
      id: 'features.octobotApp.testimonials.t2.quote',
      message:
        'OctoBot is an exceptional open-source crypto trading bot. It seamlessly integrates with exchanges and is a valuable asset to the crypto ecosystem.',
      description: 'Testimonial quote on OctoBot App page',
    }),
    name: 'Adrian Pollard',
    role: translate({
      id: 'features.octobotApp.testimonials.t2.role',
      message: 'Co-founder of HollaEx',
      description: 'Testimonial role on OctoBot App page',
    }),
    avatar: 'linear-gradient(135deg, #9b85d7, #4893f1)',
  },
  {
    quote: translate({
      id: 'features.octobotApp.testimonials.t3.quote',
      message:
        'I wanted something and the devs brought it within a few weeks. I like devs who are active and working on community ideas.',
      description: 'Testimonial quote on OctoBot App page',
    }),
    name: translate({
      id: 'features.octobotApp.testimonials.t3.name',
      message: 'OctoBot user',
      description: 'Testimonial name on OctoBot App page',
    }),
    role: translate({
      id: 'features.octobotApp.testimonials.t3.role',
      message: 'Senior community member',
      description: 'Testimonial role on OctoBot App page',
    }),
    avatar: 'linear-gradient(135deg, #f0c53b, #e8a44e)',
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.octobotApp.faq.q1.question',
      message: 'What can I do with the OctoBot App?',
      description: 'FAQ question on OctoBot App page',
    }),
    answer: translate({
      id: 'features.octobotApp.faq.q1.answer',
      message:
        'Track every account in one place and automate investment strategies — AI, crypto baskets, DCA, grid and TradingView — on the exchanges you already use.',
      description: 'FAQ answer on OctoBot App page',
    }),
  },
  {
    question: translate({
      id: 'features.octobotApp.faq.q2.question',
      message: 'Is it really free?',
      description: 'FAQ question on OctoBot App page',
    }),
    answer: translate({
      id: 'features.octobotApp.faq.q2.answer',
      message:
        'Yes. The Investor plan is free forever and lets you run automated strategies at no cost. Paid plans add advanced features, more simultaneous bots and AI tooling.',
      description: 'FAQ answer on OctoBot App page',
    }),
  },
  {
    question: translate({
      id: 'features.octobotApp.faq.q3.question',
      message: 'Can I test strategies before risking real money?',
      description: 'FAQ question on OctoBot App page',
    }),
    answer: translate({
      id: 'features.octobotApp.faq.q3.answer',
      message:
        'Every basket and strategy can be run with virtual funds first through paper trading, so you can validate an idea before committing real capital.',
      description: 'FAQ answer on OctoBot App page',
    }),
  },
  {
    question: translate({
      id: 'features.octobotApp.faq.q4.question',
      message: 'Does OctoBot take a cut of my trades?',
      description: 'FAQ question on OctoBot App page',
    }),
    answer: translate({
      id: 'features.octobotApp.faq.q4.answer',
      message:
        'No. OctoBot only charges a subscription on paid plans — there is no per-trade fee and no hidden cost.',
      description: 'FAQ answer on OctoBot App page',
    }),
  },
  {
    question: translate({
      id: 'features.octobotApp.faq.q5.question',
      message: 'Is OctoBot open source?',
      description: 'FAQ question on OctoBot App page',
    }),
    answer: (
      <Translate
        id="features.octobotApp.faq.q5.answer"
        description="FAQ answer on OctoBot App page"
        values={{
          githubLink: (
            <a href="https://github.com/Drakkar-Software/OctoBot">GitHub</a>
          ),
        }}>
        {
          'Yes — the code is on {githubLink}. You can read it, audit it and contribute to it.'
        }
      </Translate>
    ),
  },
];

export default function OctoBotAppFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.octobotApp.layout.title',
        message: 'OctoBot App — Automated crypto investing',
        description: 'Page meta title for OctoBot App page',
      })}
      description={translate({
        id: 'features.octobotApp.layout.description',
        message:
          'OctoBot App puts crypto investment on autopilot — AI strategies, crypto baskets, TradingView automation and paper trading, open source and self-custody.',
        description: 'Page meta description for OctoBot App page',
      })}>
      <Hero
        eyebrow={translate({
          id: 'features.octobotApp.hero.eyebrow',
          message: 'OctoBot App',
          description: 'Hero eyebrow on OctoBot App page',
        })}
        title={
          <Translate
            id="features.octobotApp.hero.title"
            description="Hero title on OctoBot App page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.octobotApp.hero.accent"
                    description="Accent text in hero title on OctoBot App page">
                    now on autopilot.
                  </Translate>
                </span>
              ),
            }}>
            {'Crypto investment, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.octobotApp.hero.subtitle',
          message:
            'Easily invest your crypto with OctoBot — automated strategies you fully control, from your browser or your phone.',
          description: 'Hero subtitle on OctoBot App page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.octobotApp.hero.action.invest',
              message: 'Invest for free',
              description: 'Hero action label on OctoBot App page',
            }),
            to: CLOUD_URL,
          },
          {
            label: translate({
              id: 'features.octobotApp.hero.action.guides',
              message: 'Read the guides',
              description: 'Hero action label on OctoBot App page',
            }),
            to: '/guides/octobot',
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.octobotApp.hero.meta.installs',
              message: '50K installs',
              description: 'Hero meta label on OctoBot App page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.octobotApp.hero.meta.openSource',
              message: 'Open source · since 2018',
              description: 'Hero meta label on OctoBot App page',
            }),
          },
          {
            label: translate({
              id: 'features.octobotApp.hero.meta.paperTrading',
              message: 'Paper trading included',
              description: 'Hero meta label on OctoBot App page',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'features.octobotApp.why.eyebrow',
          message: 'Why OctoBot',
          description: 'Section eyebrow on OctoBot App page',
        })}
        title={translate({
          id: 'features.octobotApp.why.title',
          message: 'Everything you need to invest on autopilot',
          description: 'Section title on OctoBot App page',
        })}
        lead={translate({
          id: 'features.octobotApp.why.lead',
          message:
            'A complete toolkit for building, testing and running automated strategies — without giving up custody.',
          description: 'Section lead on OctoBot App page',
        })}>
        <FeatureGrid features={FEATURES} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.octobotApp.gettingStarted.eyebrow',
          message: 'Getting started',
          description: 'Section eyebrow on OctoBot App page',
        })}
        title={translate({
          id: 'features.octobotApp.gettingStarted.title',
          message: 'How to start your OctoBot',
          description: 'Section title on OctoBot App page',
        })}
        lead={translate({
          id: 'features.octobotApp.gettingStarted.lead',
          message:
            'Our goal is to make crypto investment easy to access — we keep it as simple as possible.',
          description: 'Section lead on OctoBot App page',
        })}>
        <StepList steps={STEPS} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.octobotApp.riskFree.eyebrow',
          message: 'Risk-free first',
          description: 'Section eyebrow on OctoBot App page',
        })}
        title={
          <Translate
            id="features.octobotApp.riskFree.title"
            description="Section title on OctoBot App page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.octobotApp.riskFree.accent"
                    description="Accent text in risk-free title on OctoBot App page">
                    virtual money.
                  </Translate>
                </span>
              ),
            }}>
            {'Try it with {accent}'}
          </Translate>
        }
        lead={translate({
          id: 'features.octobotApp.riskFree.lead',
          message:
            'Try any crypto basket or investment strategy with simulated funds before investing a single real coin.',
          description: 'Section lead on OctoBot App page',
        })}>
        <GlassCard variant="strong" padded>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: '1.5rem',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
            <div>
              <div
                style={{
                  fontFamily: 'var(--ng-font-mono)',
                  fontSize: '0.8rem',
                  color: 'var(--ng-ink-faint)',
                  letterSpacing: '0.12em',
                }}>
                <Translate
                  id="features.octobotApp.riskFree.exampleLabel"
                  description="Example label on OctoBot App page">
                  EXAMPLE · $2,000 AFTER ONE MONTH
                </Translate>
              </div>
              <div
                style={{
                  fontSize: '1.4rem',
                  color: 'var(--ng-ink)',
                  fontWeight: 600,
                  marginTop: '0.5rem',
                }}>
                <Translate
                  id="features.octobotApp.riskFree.exampleText"
                  description="Example earnings text on OctoBot App page"
                  values={{
                    gain: (
                      <span style={{color: 'var(--ng-pos)'}}>+15%</span>
                    ),
                    earned: (
                      <span
                        style={{
                          fontFamily: 'var(--ng-font-mono)',
                          color: 'var(--ng-pos)',
                        }}>
                        +$300
                      </span>
                    ),
                  }}>
                  {'If the strategy made {gain} — you could have earned {earned}'}
                </Translate>
              </div>
            </div>
            <span className="ng-btn ng-btn--surface" style={{cursor: 'default'}}>
              <Translate
                id="features.octobotApp.riskFree.switch"
                description="Switch real/virtual button on OctoBot App page">
                Switch real ⇄ virtual
              </Translate>
            </span>
          </div>
        </GlassCard>
      </Section>

      <Section>
        <StatStrip
          head={{
            eyebrow: translate({
              id: 'features.octobotApp.community.eyebrow',
              message: 'Community',
              description: 'StatStrip eyebrow on OctoBot App page',
            }),
            title: translate({
              id: 'features.octobotApp.community.title',
              message: 'Trusted by investors worldwide',
              description: 'StatStrip title on OctoBot App page',
            }),
          }}
          stats={STATS}
        />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.octobotApp.testimonials.eyebrow',
          message: 'What the community says',
          description: 'Section eyebrow on OctoBot App page',
        })}
        title={translate({
          id: 'features.octobotApp.testimonials.title',
          message: 'A word from the community',
          description: 'Section title on OctoBot App page',
        })}>
        <Testimonials featured={FEATURED_TESTIMONIAL} items={TESTIMONIALS} />
      </Section>

      <Section
        id="pricing"
        align="left"
        eyebrow={translate({
          id: 'features.octobotApp.pricing.eyebrow',
          message: 'Pricing',
          description: 'Section eyebrow on OctoBot App page',
        })}
        title={translate({
          id: 'features.octobotApp.pricing.title',
          message: 'Choose a plan that fits your needs',
          description: 'Section title on OctoBot App page',
        })}
        lead={translate({
          id: 'features.octobotApp.pricing.lead',
          message:
            'OctoBot Cloud offers a plan for every type of investor — start free and upgrade only when you need more.',
          description: 'Section lead on OctoBot App page',
        })}>
        <PricingStrip cells={PRICING} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.octobotApp.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on OctoBot App page',
        })}
        title={translate({
          id: 'features.octobotApp.faq.title',
          message: 'Frequently asked questions',
          description: 'FAQ section title on OctoBot App page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.octobotApp.cta.title',
          message: 'Start automating in minutes',
          description: 'CTA band title on OctoBot App page',
        })}
        description={translate({
          id: 'features.octobotApp.cta.description',
          message:
            'Create your OctoBot for free, or dive into the guides to design your own strategy.',
          description: 'CTA band description on OctoBot App page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.octobotApp.cta.action.invest',
              message: 'Invest for free',
              description: 'CTA action label on OctoBot App page',
            }),
            to: CLOUD_URL,
          },
          {
            label: translate({
              id: 'features.octobotApp.cta.action.guides',
              message: 'Browse the guides',
              description: 'CTA action label on OctoBot App page',
            }),
            to: '/guides/octobot',
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
