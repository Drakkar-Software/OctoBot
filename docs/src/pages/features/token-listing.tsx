import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  StepList,
  IconList,
  LogoRibbon,
  FAQ,
  CTABand,
  type Feature,
  type Step,
  type IconListItem,
  type FAQItem,
} from '@site/src/components/landing';
import styles from './_styles.module.css';

/*
 * Token Listing feature page — route: /features/token-listing.
 *
 * SEO landing page for the "how to list a token on an exchange" /
 * "exchange listing requirements" cluster — a keyword space OctoBot Market
 * Making did not target yet. The angle: exchanges require market making to
 * list (and stay listed), and OctoBot Market Making is how a project meets
 * that requirement. Built from the Neo Glass Dark landing toolkit, same
 * pattern as src/pages/features/market-making.tsx.
 */

const CALL_URL = 'https://cal.com/octobot.cloud/market-making-30min';
const CONTACT_MAIL = 'mailto:contact@octobot.cloud';

const STEPS: Step[] = [
  {
    icon: '📝',
    title: translate({
      id: 'features.tokenListing.steps.apply.title',
      message: 'Apply to the exchange',
      description: 'Step title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.steps.apply.description',
      message:
        'Submit your project: tokenomics, smart contract, team and legal documents. Each exchange has its own application form.',
      description: 'Step description on token listing page',
    }),
  },
  {
    icon: '✅',
    title: translate({
      id: 'features.tokenListing.steps.requirements.title',
      message: 'Meet the listing requirements',
      description: 'Step title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.steps.requirements.description',
      message:
        'Exchanges expect real liquidity, healthy volume and a committed market making plan before — and after — they list.',
      description: 'Step description on token listing page',
    }),
  },
  {
    icon: '🌊',
    title: translate({
      id: 'features.tokenListing.steps.liquidity.title',
      message: 'Provide liquidity from day one',
      description: 'Step title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.steps.liquidity.description',
      message:
        'A new market with thin order books fails fast. Market making fills the book so the first traders find a real market.',
      description: 'Step description on token listing page',
    }),
  },
  {
    icon: '📊',
    title: translate({
      id: 'features.tokenListing.steps.maintain.title',
      message: 'Maintain liquidity to stay listed',
      description: 'Step title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.steps.maintain.description',
      message:
        'Listing is not the finish line — exchanges monitor liquidity and volume, and delist markets that go quiet.',
      description: 'Step description on token listing page',
    }),
  },
];

const REQUIREMENTS: Feature[] = [
  {
    icon: '💧',
    title: translate({
      id: 'features.tokenListing.requirements.liquidity.title',
      message: 'On-chain & order book liquidity',
      description: 'Requirement title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.requirements.liquidity.description',
      message:
        'Exchanges check that your stated valuation is backed by real liquidity — thin markets read as inactive and unproven.',
      description: 'Requirement description on token listing page',
    }),
  },
  {
    icon: '📈',
    title: translate({
      id: 'features.tokenListing.requirements.volume.title',
      message: 'Sustained trading volume',
      description: 'Requirement title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.requirements.volume.description',
      message:
        'Low daily volume signals a dead market. A market making strategy keeps the book active and the spread tight.',
      description: 'Requirement description on token listing page',
    }),
  },
  {
    icon: '🤝',
    title: translate({
      id: 'features.tokenListing.requirements.commitment.title',
      message: 'A market making commitment',
      description: 'Requirement title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.requirements.commitment.description',
      message:
        'Many exchanges — MEXC among them — ask projects to budget for market making as a condition of listing.',
      description: 'Requirement description on token listing page',
    }),
  },
  {
    icon: '🪙',
    title: translate({
      id: 'features.tokenListing.requirements.distribution.title',
      message: 'Healthy token distribution',
      description: 'Requirement title on token listing page',
    }),
    description: translate({
      id: 'features.tokenListing.requirements.distribution.description',
      message:
        'Concentrated supply reads as rug risk. A working market and transparent tokenomics build the confidence exchanges look for.',
      description: 'Requirement description on token listing page',
    }),
  },
];

const HOW_OCTOBOT_HELPS: IconListItem[] = [
  {
    icon: '⚙️',
    text: (
      <Translate
        id="features.tokenListing.help.meetRequirement"
        description="How OctoBot helps list item on token listing page"
        values={{label: <strong>Meet the requirement yourself:</strong>}}>
        {
          '{label} run professional market making in-house instead of paying an opaque third-party desk.'
        }
      </Translate>
    ),
  },
  {
    icon: '🔑',
    text: (
      <Translate
        id="features.tokenListing.help.yourKeys"
        description="How OctoBot helps list item on token listing page"
        values={{label: <strong>Your account, your keys:</strong>}}>
        {
          '{label} the strategy runs on your own exchange account — no token cut, no custody handed over.'
        }
      </Translate>
    ),
  },
  {
    icon: '🧩',
    text: (
      <Translate
        id="features.tokenListing.help.openSource"
        description="How OctoBot helps list item on token listing page"
        values={{label: <strong>Open source engine:</strong>}}>
        {
          '{label} no black box — inspect exactly how your liquidity is being provided.'
        }
      </Translate>
    ),
  },
  {
    icon: '📉',
    text: (
      <Translate
        id="features.tokenListing.help.measure"
        description="How OctoBot helps list item on token listing page"
        values={{label: <strong>Measure and prove it:</strong>}}>
        {
          '{label} a liquidity score shows where your markets stand, so you can show exchanges you meet the bar.'
        }
      </Translate>
    ),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.tokenListing.faq.q1.question',
      message: 'How do I list a token on a crypto exchange?',
      description: 'FAQ question on token listing page',
    }),
    answer: translate({
      id: 'features.tokenListing.faq.q1.answer',
      message:
        'You submit a listing application to the exchange with your tokenomics, smart contract, team and legal information. If approved, you typically need to provide liquidity and a market making commitment before the market goes live — and maintain it afterwards.',
      description: 'FAQ answer on token listing page',
    }),
  },
  {
    question: translate({
      id: 'features.tokenListing.faq.q2.question',
      message: 'How to list a token on MEXC?',
      description: 'FAQ question on token listing page',
    }),
    answer: translate({
      id: 'features.tokenListing.faq.q2.answer',
      message:
        'MEXC accepts applications through its official listing form. While the listing fee can be zero, MEXC expects a market making budget and a deposit, and projects must show real liquidity and trading activity. OctoBot Market Making lets you run the market making side yourself, on your own MEXC account.',
      description: 'FAQ answer on token listing page',
    }),
  },
  {
    question: translate({
      id: 'features.tokenListing.faq.q3.question',
      message: 'Why do exchanges require market making to list a token?',
      description: 'FAQ question on token listing page',
    }),
    answer: translate({
      id: 'features.tokenListing.faq.q3.answer',
      message:
        'A market with no liquidity is a bad experience: wide spreads, no depth, no fills. Exchanges require market making so that, from the first minute of trading, there is a real order book for traders to interact with — and so the market stays healthy over time.',
      description: 'FAQ answer on token listing page',
    }),
  },
  {
    question: translate({
      id: 'features.tokenListing.faq.q4.question',
      message: 'What are the requirements to get listed on an exchange?',
      description: 'FAQ question on token listing page',
    }),
    answer: translate({
      id: 'features.tokenListing.faq.q4.answer',
      message:
        'They vary by exchange, but commonly include transparent tokenomics, a verifiable team, legal documentation, healthy token distribution, real liquidity, sustained trading volume and a market making plan. The liquidity and market making parts are exactly what OctoBot Market Making addresses.',
      description: 'FAQ answer on token listing page',
    }),
  },
  {
    question: translate({
      id: 'features.tokenListing.faq.q5.question',
      message: 'Can I do my own market making to meet listing requirements?',
      description: 'FAQ question on token listing page',
    }),
    answer: (
      <Translate
        id="features.tokenListing.faq.q5.answer"
        description="FAQ answer on token listing page"
        values={{
          marketMakingLink: (
            <Link to="/features/market-making">
              <Translate
                id="features.tokenListing.faq.q5.answerLink"
                description="FAQ answer link text on token listing page">
                market making feature page
              </Translate>
            </Link>
          ),
        }}>
        {
          'Yes. OctoBot Market Making is a self-service, open-source platform to run professional market making on your own exchange account — so you can meet and maintain the listing requirement without handing your tokens to an external desk. See the {marketMakingLink}.'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.tokenListing.faq.q6.question',
      message: 'How much capital do I need for market making to get listed?',
      description: 'FAQ question on token listing page',
    }),
    answer: translate({
      id: 'features.tokenListing.faq.q6.answer',
      message:
        "It depends on the token's target volume and the exchange's expectations — effective market making generally needs enough capital to hold a meaningful share of the order book near the top. The OctoBot team can give you a specific range based on your token's profile.",
      description: 'FAQ answer on token listing page',
    }),
  },
];

export default function TokenListingFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.tokenListing.layout.title',
        message: 'How to List a Token on an Exchange — listing requirements',
        description: 'Page meta title for token listing page',
      })}
      description={translate({
        id: 'features.tokenListing.layout.description',
        message:
          'Listing a token on a crypto exchange means meeting liquidity and market making requirements. OctoBot Market Making lets you meet and maintain them on your own account.',
        description: 'Page meta description for token listing page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.tokenListing.hero.eyebrow',
          message: 'Token listing',
          description: 'Hero eyebrow on token listing page',
        })}
        title={
          <Translate
            id="features.tokenListing.hero.title"
            description="Hero title on token listing page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.tokenListing.hero.accent"
                    description="Accent text in hero title on token listing page">
                    meeting the requirements.
                  </Translate>
                </span>
              ),
            }}>
            {'Listing a token starts with {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.tokenListing.hero.subtitle',
          message:
            "Exchanges don't just want an application — they want real liquidity and a market making commitment. OctoBot Market Making is how you meet that bar, and keep meeting it.",
          description: 'Hero subtitle on token listing page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.tokenListing.hero.action.call',
              message: 'Book a free call',
              description: 'Hero action label on token listing page',
            }),
            to: CALL_URL,
          },
          {
            label: translate({
              id: 'features.tokenListing.hero.action.engine',
              message: 'See the engine',
              description: 'Hero action label on token listing page',
            }),
            to: '/features/market-making',
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.tokenListing.hero.meta.exchanges',
              message: '15+ exchanges supported',
              description: 'Hero meta label on token listing page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.tokenListing.hero.meta.ownAccount',
              message: 'Run it on your own account',
              description: 'Hero meta label on token listing page',
            }),
          },
          {
            label: translate({
              id: 'features.tokenListing.hero.meta.openSource',
              message: 'Open source engine',
              description: 'Hero meta label on token listing page',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'features.tokenListing.process.eyebrow',
          message: 'The process',
          description: 'Section eyebrow on token listing page',
        })}
        title={translate({
          id: 'features.tokenListing.process.title',
          message: 'How listing a token actually works',
          description: 'Section title on token listing page',
        })}
        lead={translate({
          id: 'features.tokenListing.process.lead',
          message:
            'From application to a market that stays alive — and where the liquidity requirement comes in.',
          description: 'Section lead on token listing page',
        })}>
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.tokenListing.bar.eyebrow',
          message: 'The bar',
          description: 'Section eyebrow on token listing page',
        })}
        title={translate({
          id: 'features.tokenListing.bar.title',
          message: 'What exchanges check before they list you',
          description: 'Section title on token listing page',
        })}
        lead={translate({
          id: 'features.tokenListing.bar.lead',
          message:
            'Beyond the paperwork, exchanges want proof your market is real — and that it will stay that way.',
          description: 'Section lead on token listing page',
        })}>
        <FeatureGrid features={REQUIREMENTS} columns={2} />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.tokenListing.solution.eyebrow',
          message: 'The solution',
          description: 'Section eyebrow on token listing page',
        })}
        title={translate({
          id: 'features.tokenListing.solution.title',
          message: 'Meet the market making requirement — on your terms',
          description: 'Section title on token listing page',
        })}
        lead={translate({
          id: 'features.tokenListing.solution.lead',
          message:
            'OctoBot Market Making turns the hardest listing requirement into something you run yourself, transparently.',
          description: 'Section lead on token listing page',
        })}>
        <IconList items={HOW_OCTOBOT_HELPS} />
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CALL_URL}>
            <Translate
              id="features.tokenListing.solution.cta.call"
              description="CTA button on token listing page">
              Book a free call
            </Translate>
          </Link>
          <Link className="ng-btn ng-btn--ghost" to="/features/market-making">
            <Translate
              id="features.tokenListing.solution.cta.engine"
              description="CTA button on token listing page">
              How the engine works
            </Translate>
          </Link>
        </div>
      </Section>

      <Section
        align="right"
        eyebrow={translate({
          id: 'features.tokenListing.coverage.eyebrow',
          message: 'Coverage',
          description: 'Section eyebrow on token listing page',
        })}
        title={
          <Translate
            id="features.tokenListing.coverage.title"
            description="Section title on token listing page"
            values={{
              accent: (
                <span className="ng-text-frost">
                  <Translate
                    id="features.tokenListing.coverage.accent"
                    description="Accent text in coverage title on token listing page">
                    exchanges that matter.
                  </Translate>
                </span>
              ),
            }}>
            {'Ready for listings on the {accent}'}
          </Translate>
        }>
        <LogoRibbon
          items={[
            'BINANCE',
            'KUCOIN',
            'MEXC',
            'COINEX',
            'COINBASE',
            'CRYPTO.COM',
            'HTX',
            'BITMART',
            'BITGET',
            '+ MORE',
          ]}
        />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.tokenListing.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on token listing page',
        })}
        title={translate({
          id: 'features.tokenListing.faq.title',
          message: 'Token listing & exchange requirements FAQ',
          description: 'FAQ section title on token listing page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.tokenListing.cta.title',
          message: 'Listing soon? Get the liquidity side handled.',
          description: 'CTA band title on token listing page',
        })}
        description={translate({
          id: 'features.tokenListing.cta.description',
          message:
            "Tell us your token and your target exchange — we'll walk through the market making requirements and how to meet them.",
          description: 'CTA band description on token listing page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.tokenListing.cta.action.call',
              message: 'Book a free call',
              description: 'CTA action label on token listing page',
            }),
            to: CALL_URL,
          },
          {
            label: translate({
              id: 'features.tokenListing.cta.action.email',
              message: 'Email us',
              description: 'CTA action label on token listing page',
            }),
            to: CONTACT_MAIL,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
