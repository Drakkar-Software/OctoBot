import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  FeatureGrid,
  FAQ,
  CTABand,
  type Feature,
  type FAQItem,
} from '@site/src/components/landing';
import GlassCard from '@site/src/components/GlassCard';
import YouTube from '@site/src/components/YouTube';
import styles from './_styles.module.css';

/*
 * Crypto Basket feature page — route: /features/crypto-basket.
 *
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit. Navbar-less LandingLayout composed from reusable
 * components.
 */

const CLOUD = 'https://www.octobot.cloud';
const BASKET_GUIDE = '/guides/octobot-usage/strategy-designer';

const ADVANTAGES: Feature[] = [
  {
    icon: '🧺',
    title: translate({
      id: 'features.cryptoBasket.advantages.diversify.title',
      message: 'Diversify in one move',
      description: 'Advantage title on crypto basket page',
    }),
    description: translate({
      id: 'features.cryptoBasket.advantages.diversify.description',
      message:
        'A basket groups several cryptocurrencies around a theme, spreading risk across many coins instead of one bet.',
      description: 'Advantage description on crypto basket page',
    }),
  },
  {
    icon: '🔄',
    title: translate({
      id: 'features.cryptoBasket.advantages.rebalancing.title',
      message: 'Automatic rebalancing',
      description: 'Advantage title on crypto basket page',
    }),
    description: translate({
      id: 'features.cryptoBasket.advantages.rebalancing.description',
      message:
        'When a coin runs up, its gains are distributed across the basket; when it dips, OctoBot buys to hold the target ratio.',
      description: 'Advantage description on crypto basket page',
    }),
  },
  {
    icon: '🌱',
    title: translate({
      id: 'features.cryptoBasket.advantages.beginner.title',
      message: 'Beginner-friendly',
      description: 'Advantage title on crypto basket page',
    }),
    description: translate({
      id: 'features.cryptoBasket.advantages.beginner.description',
      message:
        'Pick a theme you believe in — OctoBot handles selection, weighting and rebalancing for you.',
      description: 'Advantage description on crypto basket page',
    }),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q1.question',
      message: 'What is a crypto basket?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q1.answer',
      message:
        'A crypto basket is a collection of various cryptocurrencies grouped together based on a specific theme. It helps you diversify your portfolio to reduce risk.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q2.question',
      message: 'Are crypto baskets suitable for beginners?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q2.answer',
      message:
        'Crypto baskets can be suitable for beginners. When using OctoBot, you just need to choose a theme and OctoBot handles the rest.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q3.question',
      message: 'What are the advantages of using a crypto basket?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q3.answer',
      message:
        'Using a crypto basket offers two main advantages: it reduces risk by investing in multiple cryptocurrencies, and through automatic rebalancing you can benefit from the growth of one or more cryptocurrencies and realize gains.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q4.question',
      message:
        'Can I test crypto baskets with virtual funds before investing real money?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q4.answer',
      message:
        'Yes — with OctoBot you can experiment with any basket using virtual funds first.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q5.question',
      message: 'Can I customize my crypto basket?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q5.answer',
      message:
        'Yes — with OctoBot you can customize an existing basket or even create your own custom baskets.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q6.question',
      message: 'How often are crypto baskets rebalanced?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q6.answer',
      message:
        'The frequency of rebalancing varies depending on the specific basket. Some baskets are rebalanced periodically, while others may adjust dynamically based on market conditions or predefined criteria.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q7.question',
      message: 'What happens if the price of a coin changes a lot?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q7.answer',
      message:
        "When the price of a coin in a basket increases by a lot, its gains are distributed among the other coins of the basket. If its price drops, OctoBot buys more to maintain the basket's target ratio — but if a coin drops too far, it is removed from the basket and sold.",
      description: 'FAQ answer on crypto basket page',
    }),
  },
  {
    question: translate({
      id: 'features.cryptoBasket.faq.q8.question',
      message: 'How are crypto baskets made?',
      description: 'FAQ question on crypto basket page',
    }),
    answer: translate({
      id: 'features.cryptoBasket.faq.q8.answer',
      message:
        'Crypto baskets follow Coingecko categories and market-capitalization ranking. They may vary on each exchange according to the availability of coins. Note: coingecko.com is a website that specializes in ranking cryptocurrencies and is not related to OctoBot.',
      description: 'FAQ answer on crypto basket page',
    }),
  },
];

export default function CryptoBasketFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.cryptoBasket.layout.title',
        message: 'Crypto Basket',
        description: 'Page meta title for crypto basket page',
      })}
      description={translate({
        id: 'features.cryptoBasket.layout.description',
        message:
          'Invest in crypto following themes you believe in and easily diversify your portfolio with customizable, auto-rebalancing crypto baskets.',
        description: 'Page meta description for crypto basket page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.cryptoBasket.hero.eyebrow',
          message: 'Crypto baskets',
          description: 'Hero eyebrow on crypto basket page',
        })}
        title={
          <Translate
            id="features.cryptoBasket.hero.title"
            description="Hero title on crypto basket page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.cryptoBasket.hero.accent"
                    description="Accent text in hero title on crypto basket page">
                    diversify with ease.
                  </Translate>
                </span>
              ),
            }}>
            {'Invest in themes you love, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.cryptoBasket.hero.subtitle',
          message:
            'Thematic portfolios for every crypto investor — fine-tune your portfolio with customizable baskets.',
          description: 'Hero subtitle on crypto basket page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.cryptoBasket.hero.action.invest',
              message: 'Invest in a basket',
              description: 'Hero action label on crypto basket page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.cryptoBasket.hero.action.guide',
              message: 'Read the guide',
              description: 'Hero action label on crypto basket page',
            }),
            to: BASKET_GUIDE,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.cryptoBasket.hero.meta.rebalancing',
              message: 'Auto-rebalancing',
              description: 'Hero meta label on crypto basket page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.cryptoBasket.hero.meta.customizable',
              message: 'Fully customizable',
              description: 'Hero meta label on crypto basket page',
            }),
          },
          {
            label: translate({
              id: 'features.cryptoBasket.hero.meta.paperTrading',
              message: 'Paper trading included',
              description: 'Hero meta label on crypto basket page',
            }),
          },
        ]}
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.cryptoBasket.customize.eyebrow',
          message: 'Customize',
          description: 'Section eyebrow on crypto basket page',
        })}
        title={translate({
          id: 'features.cryptoBasket.customize.title',
          message: 'Make your own crypto basket',
          description: 'Section title on crypto basket page',
        })}
        lead={translate({
          id: 'features.cryptoBasket.customize.lead',
          message:
            'Customize baskets to match your goals — or create your very own from scratch.',
          description: 'Section lead on crypto basket page',
        })}>
        <GlassCard variant="strong" padded={false} className={styles.mix}>
          <div className={styles.mixLabel}>
            <Translate
              id="features.cryptoBasket.customize.exampleLabel"
              description="Example basket label on crypto basket page">
              EXAMPLE BASKET · TARGET WEIGHTS
            </Translate>
          </div>
          <div className={styles.mixBar}>
            <span style={{flex: 50, background: '#f7931a'}} />
            <span style={{flex: 30, background: '#8aa1f0'}} />
            <span style={{flex: 20, background: 'var(--ng-turquoise)'}} />
          </div>
          <div className={styles.mixLegend}>
            <span>
              <span style={{color: '#f7931a'}}>●</span> BTC 50%
            </span>
            <span>
              <span style={{color: '#8aa1f0'}}>●</span> ETH 30%
            </span>
            <span>
              <span style={{color: 'var(--ng-turquoise)'}}>●</span> SOL 20%
            </span>
          </div>
        </GlassCard>
        <div className={`${styles.cta} ${styles.ctaLeft}`}>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            <Translate
              id="features.cryptoBasket.customize.cta"
              description="CTA button on crypto basket page">
              Create my own crypto basket
            </Translate>
          </Link>
        </div>
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.cryptoBasket.bestCrypto.eyebrow',
          message: 'The best crypto',
          description: 'Section eyebrow on crypto basket page',
        })}
        title={translate({
          id: 'features.cryptoBasket.bestCrypto.title',
          message: 'Invest in the best crypto',
          description: 'Section title on crypto basket page',
        })}
        lead={translate({
          id: 'features.cryptoBasket.bestCrypto.lead',
          message:
            'Profit from the best crypto and trends of the market using crypto baskets.',
          description: 'Section lead on crypto basket page',
        })}>
        <YouTube
          id="WOgS-VhUyIY"
          title={translate({
            id: 'features.cryptoBasket.bestCrypto.videoTitle',
            message: 'Investing in the best crypto',
            description: 'YouTube video title on crypto basket page',
          })}
        />
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.cryptoBasket.whyBaskets.eyebrow',
          message: 'Why baskets',
          description: 'Section eyebrow on crypto basket page',
        })}
        title={translate({
          id: 'features.cryptoBasket.whyBaskets.title',
          message: 'Diversification, done for you',
          description: 'Section title on crypto basket page',
        })}
        lead={translate({
          id: 'features.cryptoBasket.whyBaskets.lead',
          message:
            'Crypto baskets spread risk and capture trends without you watching every coin.',
          description: 'Section lead on crypto basket page',
        })}>
        <FeatureGrid features={ADVANTAGES} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.cryptoBasket.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on crypto basket page',
        })}
        title={translate({
          id: 'features.cryptoBasket.faq.title',
          message: 'Crypto basket FAQ',
          description: 'FAQ section title on crypto basket page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.cryptoBasket.cta.title',
          message: 'Build a basket around what you believe in',
          description: 'CTA band title on crypto basket page',
        })}
        description={translate({
          id: 'features.cryptoBasket.cta.description',
          message:
            'Pick a theme, set your weights, and let OctoBot keep it balanced.',
          description: 'CTA band description on crypto basket page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.cryptoBasket.cta.action.invest',
              message: 'Invest in a basket',
              description: 'CTA action label on crypto basket page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.cryptoBasket.cta.action.guide',
              message: 'Read the guide',
              description: 'CTA action label on crypto basket page',
            }),
            to: BASKET_GUIDE,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
