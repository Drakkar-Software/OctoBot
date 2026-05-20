import type {ReactNode} from 'react';
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
import ConverterCard from '@site/src/components/pages/tools/converter/ConverterCard';
import styles from './converter.module.css';

/*
 * Crypto converters tool page — route: /tools/converter.
 *
 * Migrated from the OctoBot App marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the feature pages: a navbar-less
 * LandingLayout composed from reusable components, plus a page-local
 * _ConverterCard mock for the live-price visual.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

const PAIRS: Feature[] = [
  {
    icon: '₿',
    title: 'BTC → USD',
    description: translate({
      id: 'tools.converter.pairs.btc.description',
      message: 'Live Bitcoin price, market cap and conversion table.',
      description: 'Converter popular pair description for BTC',
    }),
    to: CLOUD,
  },
  {
    icon: 'Ξ',
    title: 'ETH → USD',
    description: translate({
      id: 'tools.converter.pairs.eth.description',
      message: 'Live Ethereum price, market cap and conversion table.',
      description: 'Converter popular pair description for ETH',
    }),
    to: CLOUD,
  },
  {
    icon: '◎',
    title: 'SOL → USD',
    description: translate({
      id: 'tools.converter.pairs.sol.description',
      message: 'Live Solana price, market cap and conversion table.',
      description: 'Converter popular pair description for SOL',
    }),
    to: CLOUD,
  },
  {
    icon: '🔶',
    title: 'BNB → USD',
    description: translate({
      id: 'tools.converter.pairs.bnb.description',
      message: 'Live BNB price, market cap and conversion table.',
      description: 'Converter popular pair description for BNB',
    }),
    to: CLOUD,
  },
  {
    icon: '✕',
    title: 'XRP → USD',
    description: translate({
      id: 'tools.converter.pairs.xrp.description',
      message: 'Live XRP price, market cap and conversion table.',
      description: 'Converter popular pair description for XRP',
    }),
    to: CLOUD,
  },
  {
    icon: '₳',
    title: 'ADA → USD',
    description: translate({
      id: 'tools.converter.pairs.ada.description',
      message: 'Live Cardano price, market cap and conversion table.',
      description: 'Converter popular pair description for ADA',
    }),
    to: CLOUD,
  },
];

const FAQ_ITEMS: FAQItem[] = [
  {
    question: translate({
      id: 'tools.converter.faq.ticker.question',
      message: 'What is a crypto ticker?',
      description: 'Converter FAQ question: crypto ticker',
    }),
    answer: translate({
      id: 'tools.converter.faq.ticker.answer',
      message:
        'A ticker is the short symbol used to identify a cryptocurrency on exchanges — for example BTC for Bitcoin or ETH for Ethereum.',
      description: 'Converter FAQ answer: crypto ticker',
    }),
  },
  {
    question: translate({
      id: 'tools.converter.faq.earn.question',
      message: 'Is it possible to earn money with crypto investments?',
      description: 'Converter FAQ question: earn money',
    }),
    answer: translate({
      id: 'tools.converter.faq.earn.answer',
      message:
        'Yes, it is possible to earn money with crypto, but it also carries significant risk. You should do your own research and use risk-management tools like OctoBot.',
      description: 'Converter FAQ answer: earn money',
    }),
  },
  {
    question: translate({
      id: 'tools.converter.faq.livePrice.question',
      message: 'How can I check the live price of a crypto?',
      description: 'Converter FAQ question: live price',
    }),
    answer: translate({
      id: 'tools.converter.faq.livePrice.answer',
      message:
        'You can check live crypto prices on platforms like TradingView, or through cryptocurrency exchange platforms.',
      description: 'Converter FAQ answer: live price',
    }),
  },
  {
    question: translate({
      id: 'tools.converter.faq.marketCap.question',
      message: "How is a crypto's market cap calculated?",
      description: 'Converter FAQ question: market cap',
    }),
    answer: translate({
      id: 'tools.converter.faq.marketCap.answer',
      message:
        "A crypto's market cap is calculated by multiplying the current price of one coin by the total number of coins in circulation.",
      description: 'Converter FAQ answer: market cap',
    }),
  },
];

export default function CryptoConverter(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'tools.converter.layout.title',
        message: 'Crypto converters',
        description: 'Converter page meta title',
      })}
      description={translate({
        id: 'tools.converter.layout.description',
        message:
          'Real-time price conversion between any cryptocurrency and fiat — with market data and conversion tables.',
        description: 'Converter page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.converter.hero.eyebrow',
          message: 'Crypto converters',
          description: 'Converter hero eyebrow',
        })}
        title={
          <Translate
            id="tools.converter.hero.title"
            description="Converter hero title"
            values={{
              accent: (
                <span className="ng-text-gradient">
                  <Translate
                    id="tools.converter.hero.title.accent"
                    description="Converter hero title accent">
                    live price.
                  </Translate>
                </span>
              ),
            }}>
            {'Convert crypto at the {accent}'}
          </Translate>
        }
        subtitle={translate({
          id: 'tools.converter.hero.subtitle',
          message:
            'Real-time price conversion between any cryptocurrency and fiat — with market data and conversion tables.',
          description: 'Converter hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.converter.hero.action.invest',
              message: 'Invest for free',
              description: 'Converter hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.converter.hero.action.guides',
              message: 'Read the guides',
              description: 'Converter hero guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.converter.hero.meta.livePrices',
              message: 'Live prices',
              description: 'Converter hero meta: live prices',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.converter.hero.meta.anyPair',
              message: 'Any crypto / fiat pair',
              description: 'Converter hero meta: any pair',
            }),
          },
          {
            label: translate({
              id: 'tools.converter.hero.meta.conversionTables',
              message: 'Conversion tables',
              description: 'Converter hero meta: conversion tables',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.converter.live.eyebrow',
          message: 'Live price',
          description: 'Converter live price section eyebrow',
        })}
        title={translate({
          id: 'tools.converter.live.title',
          message: 'A converter for every pair',
          description: 'Converter live price section title',
        })}>
        <ConverterCard />
      </Section>

      <Section
        eyebrow={translate({
          id: 'tools.converter.popular.eyebrow',
          message: 'Popular',
          description: 'Converter popular section eyebrow',
        })}
        title={translate({
          id: 'tools.converter.popular.title',
          message: 'Popular conversion pairs',
          description: 'Converter popular section title',
        })}
        lead={translate({
          id: 'tools.converter.popular.lead',
          message:
            'The pairs traders check most — each one opens a live converter with current price, market cap and a full conversion table.',
          description: 'Converter popular section lead',
        })}>
        <FeatureGrid features={PAIRS} columns={3} />
      </Section>

      <Section
        eyebrow={translate({
          id: 'tools.converter.faq.eyebrow',
          message: 'FAQ',
          description: 'Converter FAQ section eyebrow',
        })}
        title={translate({
          id: 'tools.converter.faq.title',
          message: 'Crypto converter FAQ',
          description: 'Converter FAQ section title',
        })}>
        <FAQ items={FAQ_ITEMS} />
      </Section>

      <CTABand
        title={translate({
          id: 'tools.converter.cta.title',
          message: 'Convert, then put your crypto to work',
          description: 'Converter CTA band title',
        })}
        description={translate({
          id: 'tools.converter.cta.description',
          message:
            'Create your trading bot for free on OctoBot App, or read the guides first.',
          description: 'Converter CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.converter.cta.action.invest',
              message: 'Invest for free',
              description: 'Converter CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.converter.cta.action.guides',
              message: 'Read the guides',
              description: 'Converter CTA guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
