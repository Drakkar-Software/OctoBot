import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import {
  LandingLayout,
  Hero,
  Section,
  LogoRibbon,
  CTABand,
} from '@site/src/components/landing';
import ExchangeTable from '@site/src/components/pages/supported-exchanges/ExchangeTable';
import styles from './supported-exchanges.module.css';

/*
 * OctoBot Market Making supported exchanges page — route: /supported-exchanges.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. A navbar-less LandingLayout: hero, the page-local
 * ExchangeTable, a LogoRibbon of exchange names and a closing CTA band.
 */

const BOOK_A_CALL = 'https://cal.com/octobot.cloud/market-making-30min';
const MARKET_MAKING = '/market-making';
const EMAIL = 'mailto:contact@octobot.cloud';

const EXCHANGE_LOGOS: ReactNode[] = [
  'BINANCE',
  'COINBASE',
  'KRAKEN',
  'OKX',
  'BYBIT',
  'KUCOIN',
  'BITGET',
  'GATE.IO',
  'HTX',
  'MEXC',
  'HOLLAEX',
  translate({
    id: 'pages.supportedExchanges.logos.more',
    message: '+ MORE',
    description: 'Logo ribbon "and more" entry',
  }),
];

export default function SupportedExchanges(): ReactNode {
  return (
    <LandingLayout
      title={translate({
        id: 'pages.supportedExchanges.meta.title',
        message: 'Market Making exchanges',
        description: 'Supported exchanges page metadata title',
      })}
      description={translate({
        id: 'pages.supportedExchanges.meta.description',
        message:
          'OctoBot Market Making supports most centralized exchanges. Discover the exchanges OctoBot Market Making can help you increase your crypto liquidity on.',
        description: 'Supported exchanges page metadata description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'pages.supportedExchanges.hero.eyebrow',
          message: 'Market Making',
          description: 'Supported exchanges hero eyebrow',
        })}
        title={
          <>
            <span className="ng-text-gradient">
              <Translate
                id="pages.supportedExchanges.hero.title"
                description="Supported exchanges hero title">
                OctoBot Market Making exchanges.
              </Translate>
            </span>
          </>
        }
        subtitle={translate({
          id: 'pages.supportedExchanges.hero.subtitle',
          message:
            'OctoBot Market Making supports most centralized exchanges. Here are the exchanges OctoBot Market Making can help you increase your crypto liquidity on.',
          description: 'Supported exchanges hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.supportedExchanges.hero.action.call',
              message: 'Book a free call',
              description: 'Supported exchanges hero action label',
            }),
            to: BOOK_A_CALL,
          },
          {
            label: translate({
              id: 'pages.supportedExchanges.hero.action.overview',
              message: 'Market Making overview',
              description: 'Supported exchanges hero action label',
            }),
            to: MARKET_MAKING,
            variant: 'ghost',
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'pages.supportedExchanges.coverage.eyebrow',
          message: 'Coverage',
          description: 'Supported exchanges section eyebrow',
        })}
        title={translate({
          id: 'pages.supportedExchanges.coverage.title',
          message: 'Supported exchanges',
          description: 'Supported exchanges section title',
        })}>
        <ExchangeTable />
      </Section>

      <Section
        eyebrow={translate({
          id: 'pages.supportedExchanges.glance.eyebrow',
          message: 'At a glance',
          description: 'Supported exchanges section eyebrow',
        })}
        title={translate({
          id: 'pages.supportedExchanges.glance.title',
          message: 'Plug in, trade in 60 seconds',
          description: 'Supported exchanges section title',
        })}>
        <LogoRibbon items={EXCHANGE_LOGOS} minCellWidth={150} />
      </Section>

      <CTABand
        title={translate({
          id: 'pages.supportedExchanges.cta.title',
          message: 'Your exchange is missing?',
          description: 'Supported exchanges CTA title',
        })}
        description={translate({
          id: 'pages.supportedExchanges.cta.description',
          message: 'Talk to our team — we add new exchanges on request.',
          description: 'Supported exchanges CTA description',
        })}
        actions={[
          {
            label: translate({
              id: 'pages.supportedExchanges.cta.action.call',
              message: 'Book a free call',
              description: 'Supported exchanges CTA action label',
            }),
            to: BOOK_A_CALL,
          },
          {
            label: translate({
              id: 'pages.supportedExchanges.cta.action.email',
              message: 'Email us',
              description: 'Supported exchanges CTA action label',
            }),
            to: EMAIL,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
