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
      <Translate
        id="features.selfCustodyTradingBot.why.keys"
        description="Why list item on self custody trading bot page"
        values={{label: <strong>Your keys, your coins:</strong>}}>
        {'{label} your keys never leave your devices.'}
      </Translate>
    ),
  },
  {
    icon: '🔀',
    text: (
      <Translate
        id="features.selfCustodyTradingBot.why.flexible"
        description="Why list item on self custody trading bot page"
        values={{label: <strong>Flexible:</strong>}}>
        {
          '{label} trade on both centralized and decentralized exchanges.'
        }
      </Translate>
    ),
  },
  {
    icon: '🧰',
    text: (
      <Translate
        id="features.selfCustodyTradingBot.why.versatile"
        description="Why list item on self custody trading bot page"
        values={{label: <strong>Versatile:</strong>}}>
        {
          '{label} run strategies based on DCA, AI, grid, crypto baskets, TradingView and more.'
        }
      </Translate>
    ),
  },
  {
    icon: '📱',
    text: (
      <Translate
        id="features.selfCustodyTradingBot.why.anywhere"
        description="Why list item on self custody trading bot page"
        values={{label: <strong>Anytime & anywhere:</strong>}}>
        {'{label} configure and execute strategies from your phone.'}
      </Translate>
    ),
  },
];

const UNIQUE: Feature[] = [
  {
    icon: '🛡️',
    title: translate({
      id: 'features.selfCustodyTradingBot.unique.security.title',
      message: 'Maximum security',
      description: 'Unique feature title on self custody trading bot page',
    }),
    description: translate({
      id: 'features.selfCustodyTradingBot.unique.security.description',
      message:
        'You are the only one with access to your crypto keys. No leakage possible — even the OctoBot team cannot access your keys.',
      description:
        'Unique feature description on self custody trading bot page',
    }),
  },
  {
    icon: '🧩',
    title: translate({
      id: 'features.selfCustodyTradingBot.unique.community.title',
      message: 'Open community',
      description: 'Unique feature title on self custody trading bot page',
    }),
    description: translate({
      id: 'features.selfCustodyTradingBot.unique.community.description',
      message:
        'Use the same strategy as your friends for free and in a few clicks, on your favorite centralized or decentralized exchange.',
      description:
        'Unique feature description on self custody trading bot page',
    }),
  },
  {
    icon: '🔄',
    title: translate({
      id: 'features.selfCustodyTradingBot.unique.boost.title',
      message: 'Boost your bot',
      description: 'Unique feature title on self custody trading bot page',
    }),
    description: translate({
      id: 'features.selfCustodyTradingBot.unique.boost.description',
      message:
        'If your phone cannot execute your bot correctly, you can help it with your own personal mini-cloud.',
      description:
        'Unique feature description on self custody trading bot page',
    }),
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q1.question',
      message: 'What is a self custody trading bot?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: (
      <Translate
        id="features.selfCustodyTradingBot.faq.q1.answer"
        description="FAQ answer on self custody trading bot page"
        values={{
          blogLink: (
            <Link to={SELF_CUSTODY_BLOG}>
              <Translate
                id="features.selfCustodyTradingBot.faq.q1.answerLink"
                description="FAQ answer link text on self custody trading bot page">
                dedicated blog post
              </Translate>
            </Link>
          ),
        }}>
        {
          'A self custody trading bot is a trading bot fully controlled by you, its user. It is not controlled by a central authority such as a crypto exchange or a trading-bot platform that holds your API (or wallet) keys. More info on our {blogLink}.'
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q2.question',
      message:
        'What is the difference between a self custody trading bot and another trading bot?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: (
      <Translate
        id="features.selfCustodyTradingBot.faq.q2.answer"
        description="FAQ answer on self custody trading bot page"
        values={{
          blogLink: (
            <Link to={SELF_CUSTODY_BLOG}>
              <Translate
                id="features.selfCustodyTradingBot.faq.q2.answerLink"
                description="FAQ answer link text on self custody trading bot page">
                dedicated blog post
              </Translate>
            </Link>
          ),
        }}>
        {
          "A self custody trading bot is not running on someone else's servers — you always have complete control over your API (or wallet) keys. It makes it much more secure and flexible than other trading bots. More info on our {blogLink}."
        }
      </Translate>
    ),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q3.question',
      message:
        'What is the difference between OctoBot self-custody and OctoBot Cloud or open source?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q3.answer',
      message:
        'OctoBot self-custody is as simple to use as OctoBot Cloud but runs on your own mobile. It gives you complete control over your API (or wallet) keys and works with centralized or decentralized exchanges. It is designed to stay easy to use while remaining very flexible — and it is much easier to use than the open-source OctoBot, which requires more technical knowledge and a computer or server to operate.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q4.question',
      message: 'Are centralized exchanges supported?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q4.answer',
      message:
        'Yes — a self custody trading bot can connect to both centralized and decentralized exchanges, and in both cases it greatly increases the security of your crypto assets.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q5.question',
      message: 'Are decentralized exchanges supported?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q5.answer',
      message:
        'Yes — a self custody trading bot can automate strategies on decentralized exchanges.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q6.question',
      message: 'What kind of strategies can I automate?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q6.answer',
      message:
        'We expect to support all the strategies available on OctoBot Cloud, including DCA, AI, grid trading, crypto baskets, TradingView strategies and more.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q7.question',
      message: 'How can it work on a phone?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q7.answer',
      message:
        'A self custody trading bot can run on any device with an internet connection that allows installing an app. There are many challenges to making it work properly on a phone compared to a regular computer — we are taking care of that for you.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q8.question',
      message: 'What does a personal mini-cloud mean?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q8.answer',
      message:
        'A personal mini-cloud is a secure personal server you can use to execute part of your self custody trading bot, for strategies that some phones cannot run reliably. It may not be necessary — it depends on your phone, your connection and your strategies. It is a server created by you and automatically configured by the app, using an account that belongs to you. It is not owned by the OctoBot team: it is your own server, which you alone have access to.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
  {
    question: translate({
      id: 'features.selfCustodyTradingBot.faq.q9.question',
      message: 'When will it be available?',
      description: 'FAQ question on self custody trading bot page',
    }),
    answer: translate({
      id: 'features.selfCustodyTradingBot.faq.q9.answer',
      message:
        'We are working on it and will launch it very soon. Register for early access to be the first to use it.',
      description: 'FAQ answer on self custody trading bot page',
    }),
  },
];

export default function SelfCustodyTradingBotFeature(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'features.selfCustodyTradingBot.layout.title',
        message: 'Self Custody Trading Bot',
        description: 'Page meta title for self custody trading bot page',
      })}
      description={translate({
        id: 'features.selfCustodyTradingBot.layout.description',
        message:
          'Automate your investment strategies for free, from your phone, on centralized and decentralized exchanges. Your keys stay on your phone, always.',
        description: 'Page meta description for self custody trading bot page',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'features.selfCustodyTradingBot.hero.eyebrow',
          message: 'Self custody trading bot',
          description: 'Hero eyebrow on self custody trading bot page',
        })}
        title={
          <Translate
            id="features.selfCustodyTradingBot.hero.title"
            description="Hero title on self custody trading bot page"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="features.selfCustodyTradingBot.hero.accent"
                    description="Accent text in hero title on self custody trading bot page">
                    on your phone.
                  </Translate>
                </span>
              ),
            }}>
            {'Your investment strategies, {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'features.selfCustodyTradingBot.hero.subtitle',
          message:
            'Automate your investment strategies simply, without sharing your keys — from your phone, on centralized and decentralized exchanges.',
          description: 'Hero subtitle on self custody trading bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.hero.action.learnMore',
              message: 'Learn more',
              description: 'Hero action label on self custody trading bot page',
            }),
            to: SELF_CUSTODY_BLOG,
          },
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.hero.action.guides',
              message: 'Read the guides',
              description: 'Hero action label on self custody trading bot page',
            }),
            to: '/guides/octobot',
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.hero.meta.keys',
              message: 'Keys never leave your device',
              description: 'Hero meta label on self custody trading bot page',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.hero.meta.cexDex',
              message: 'CEX & DEX',
              description: 'Hero meta label on self custody trading bot page',
            }),
          },
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.hero.meta.earlyAccess',
              message: 'Early access soon',
              description: 'Hero meta label on self custody trading bot page',
            }),
          },
        ]}
      />

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.selfCustodyTradingBot.why.eyebrow',
          message: 'Why self-custody',
          description: 'Section eyebrow on self custody trading bot page',
        })}
        title={translate({
          id: 'features.selfCustodyTradingBot.why.title',
          message: "A new kind of trading bot for today's crypto market",
          description: 'Section title on self custody trading bot page',
        })}
        lead={translate({
          id: 'features.selfCustodyTradingBot.why.lead',
          message:
            'With the rise of decentralized exchanges, new strategy opportunities are emerging. The first investors to take advantage of them will make the largest gains.',
          description: 'Section lead on self custody trading bot page',
        })}>
        <IconList items={WHY} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.selfCustodyTradingBot.unique.eyebrow',
          message: "What's unique",
          description: 'Section eyebrow on self custody trading bot page',
        })}
        title={translate({
          id: 'features.selfCustodyTradingBot.unique.title',
          message: 'What makes OctoBot self-custody unique',
          description: 'Section title on self custody trading bot page',
        })}
        lead={translate({
          id: 'features.selfCustodyTradingBot.unique.lead',
          message:
            'Security, community and resilience — without giving up control of your keys.',
          description: 'Section lead on self custody trading bot page',
        })}>
        <FeatureGrid features={UNIQUE} columns={3} />
        <div className={styles.cta}>
          <Link className="ng-btn ng-btn--ghost" to={SELF_CUSTODY_BLOG}>
            <Translate
              id="features.selfCustodyTradingBot.unique.cta"
              description="CTA button on self custody trading bot page">
              Learn more on self-custody trading bots
            </Translate>
          </Link>
        </div>
      </Section>

      <Section
        align="left"
        eyebrow={translate({
          id: 'features.selfCustodyTradingBot.earlyAccess.eyebrow',
          message: 'Early access',
          description: 'Section eyebrow on self custody trading bot page',
        })}>
        <GlassCard variant="hero" padded={false} className={styles.panel}>
          <h3 className={styles.panelTitle}>
            <Translate
              id="features.selfCustodyTradingBot.earlyAccess.title"
              description="Early access panel title on self custody trading bot page">
              Interested in automating your strategies from your phone?
            </Translate>
          </h3>
          <p className={styles.panelText}>
            <Translate
              id="features.selfCustodyTradingBot.earlyAccess.text"
              description="Early access panel text on self custody trading bot page">
              Be one of the first to use our new self custody trading bot mobile
              app. Register for early access to be notified when it is available.
            </Translate>
          </p>
          <Link className="ng-btn ng-btn--primary" to={CLOUD}>
            <Translate
              id="features.selfCustodyTradingBot.earlyAccess.cta"
              description="Early access CTA button on self custody trading bot page">
              Join the early access
            </Translate>
          </Link>
        </GlassCard>
      </Section>

      <Section
        eyebrow={translate({
          id: 'features.selfCustodyTradingBot.faq.eyebrow',
          message: 'FAQ',
          description: 'FAQ section eyebrow on self custody trading bot page',
        })}
        title={translate({
          id: 'features.selfCustodyTradingBot.faq.title',
          message: 'Self custody trading bot FAQ',
          description: 'FAQ section title on self custody trading bot page',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'features.selfCustodyTradingBot.cta.title',
          message: 'Your strategies. Your keys. Your phone.',
          description: 'CTA band title on self custody trading bot page',
        })}
        description={translate({
          id: 'features.selfCustodyTradingBot.cta.description',
          message:
            'Read how a self-custody trading bot works, or register for early access.',
          description: 'CTA band description on self custody trading bot page',
        })}
        actions={[
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.cta.action.earlyAccess',
              message: 'Join the early access',
              description: 'CTA action label on self custody trading bot page',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'features.selfCustodyTradingBot.cta.action.blog',
              message: 'Read the blog post',
              description: 'CTA action label on self custody trading bot page',
            }),
            to: SELF_CUSTODY_BLOG,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
