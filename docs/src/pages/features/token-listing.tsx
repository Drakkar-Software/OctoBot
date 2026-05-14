import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
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
    title: 'Apply to the exchange',
    description:
      'Submit your project: tokenomics, smart contract, team and legal documents. Each exchange has its own application form.',
  },
  {
    icon: '✅',
    title: 'Meet the listing requirements',
    description:
      'Exchanges expect real liquidity, healthy volume and a committed market making plan before — and after — they list.',
  },
  {
    icon: '🌊',
    title: 'Provide liquidity from day one',
    description:
      'A new market with thin order books fails fast. Market making fills the book so the first traders find a real market.',
  },
  {
    icon: '📊',
    title: 'Maintain liquidity to stay listed',
    description:
      'Listing is not the finish line — exchanges monitor liquidity and volume, and delist markets that go quiet.',
  },
];

const REQUIREMENTS: Feature[] = [
  {
    icon: '💧',
    title: 'On-chain & order book liquidity',
    description:
      'Exchanges check that your stated valuation is backed by real liquidity — thin markets read as inactive and unproven.',
  },
  {
    icon: '📈',
    title: 'Sustained trading volume',
    description:
      'Low daily volume signals a dead market. A market making strategy keeps the book active and the spread tight.',
  },
  {
    icon: '🤝',
    title: 'A market making commitment',
    description:
      'Many exchanges — MEXC among them — ask projects to budget for market making as a condition of listing.',
  },
  {
    icon: '🪙',
    title: 'Healthy token distribution',
    description:
      'Concentrated supply reads as rug risk. A working market and transparent tokenomics build the confidence exchanges look for.',
  },
];

const HOW_OCTOBOT_HELPS: IconListItem[] = [
  {
    icon: '⚙️',
    text: (
      <>
        <strong>Meet the requirement yourself:</strong> run professional market
        making in-house instead of paying an opaque third-party desk.
      </>
    ),
  },
  {
    icon: '🔑',
    text: (
      <>
        <strong>Your account, your keys:</strong> the strategy runs on your own
        exchange account — no token cut, no custody handed over.
      </>
    ),
  },
  {
    icon: '🧩',
    text: (
      <>
        <strong>Open source engine:</strong> no black box — inspect exactly how
        your liquidity is being provided.
      </>
    ),
  },
  {
    icon: '📉',
    text: (
      <>
        <strong>Measure and prove it:</strong> a liquidity score shows where
        your markets stand, so you can show exchanges you meet the bar.
      </>
    ),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: 'How do I list a token on a crypto exchange?',
    answer:
      'You submit a listing application to the exchange with your tokenomics, smart contract, team and legal information. If approved, you typically need to provide liquidity and a market making commitment before the market goes live — and maintain it afterwards.',
  },
  {
    question: 'How to list a token on MEXC?',
    answer:
      "MEXC accepts applications through its official listing form. While the listing fee can be zero, MEXC expects a market making budget and a deposit, and projects must show real liquidity and trading activity. OctoBot Market Making lets you run the market making side yourself, on your own MEXC account.",
  },
  {
    question: 'Why do exchanges require market making to list a token?',
    answer:
      'A market with no liquidity is a bad experience: wide spreads, no depth, no fills. Exchanges require market making so that, from the first minute of trading, there is a real order book for traders to interact with — and so the market stays healthy over time.',
  },
  {
    question: 'What are the requirements to get listed on an exchange?',
    answer:
      'They vary by exchange, but commonly include transparent tokenomics, a verifiable team, legal documentation, healthy token distribution, real liquidity, sustained trading volume and a market making plan. The liquidity and market making parts are exactly what OctoBot Market Making addresses.',
  },
  {
    question: 'Can I do my own market making to meet listing requirements?',
    answer: (
      <>
        Yes. OctoBot Market Making is a self-service, open-source platform to
        run professional market making on your own exchange account — so you
        can meet and maintain the listing requirement without handing your
        tokens to an external desk. See the{' '}
        <Link to="/features/market-making">market making feature page</Link>.
      </>
    ),
  },
  {
    question: 'How much capital do I need for market making to get listed?',
    answer:
      "It depends on the token's target volume and the exchange's expectations — effective market making generally needs enough capital to hold a meaningful share of the order book near the top. The OctoBot team can give you a specific range based on your token's profile.",
  },
];

export default function TokenListingFeature(): ReactNode {
  return (
    <LandingLayout
      title="How to List a Token on an Exchange — listing requirements"
      description="Listing a token on a crypto exchange means meeting liquidity and market making requirements. OctoBot Market Making lets you meet and maintain them on your own account.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Token listing"
        title={
          <>
            Listing a token starts with{' '}
            <span className="ng-text-gradient">meeting the requirements.</span>
          </>
        }
        subtitle="Exchanges don't just want an application — they want real liquidity and a market making commitment. OctoBot Market Making is how you meet that bar, and keep meeting it."
        actions={[
          {label: 'Book a free call', to: CALL_URL},
          {label: 'See the engine', to: '/features/market-making', variant: 'ghost'},
        ]}
        meta={[
          {label: '15+ exchanges supported', dot: true},
          {label: 'Run it on your own account'},
          {label: 'Open source engine'},
        ]}
      />

      <Section
        eyebrow="The process"
        title="How listing a token actually works"
        lead="From application to a market that stays alive — and where the liquidity requirement comes in.">
        <StepList steps={STEPS} />
      </Section>

      <Section
        eyebrow="The bar"
        title="What exchanges check before they list you"
        lead="Beyond the paperwork, exchanges want proof your market is real — and that it will stay that way.">
        <FeatureGrid features={REQUIREMENTS} columns={2} />
      </Section>

      <Section
        align="left"
        eyebrow="The solution"
        title="Meet the market making requirement — on your terms"
        lead="OctoBot Market Making turns the hardest listing requirement into something you run yourself, transparently.">
        <IconList items={HOW_OCTOBOT_HELPS} />
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CALL_URL}>
            Book a free call
          </Link>
          <Link className="ng-btn ng-btn--ghost" to="/features/market-making">
            How the engine works
          </Link>
        </div>
      </Section>

      <Section
        align="right"
        eyebrow="Coverage"
        title={
          <>
            Ready for listings on the{' '}
            <span className="ng-text-frost">exchanges that matter.</span>
          </>
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

      <Section eyebrow="FAQ" title="Token listing & exchange requirements FAQ">
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title="Listing soon? Get the liquidity side handled."
        description="Tell us your token and your target exchange — we'll walk through the market making requirements and how to meet them."
        actions={[
          {label: 'Book a free call', to: CALL_URL},
          {label: 'Email us', to: CONTACT_MAIL, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
