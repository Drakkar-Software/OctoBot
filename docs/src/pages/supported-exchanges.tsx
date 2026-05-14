import type {ReactNode} from 'react';
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
  '+ MORE',
];

export default function SupportedExchanges(): ReactNode {
  return (
    <LandingLayout
      title="Market Making exchanges"
      description="OctoBot Market Making supports most centralized exchanges. Discover the exchanges OctoBot Market Making can help you increase your crypto liquidity on.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Market Making"
        title={
          <>
            <span className="ng-text-gradient">
              OctoBot Market Making exchanges.
            </span>
          </>
        }
        subtitle="OctoBot Market Making supports most centralized exchanges. Here are the exchanges OctoBot Market Making can help you increase your crypto liquidity on."
        actions={[
          {label: 'Book a free call', to: BOOK_A_CALL},
          {
            label: 'Market Making overview',
            to: MARKET_MAKING,
            variant: 'ghost',
          },
        ]}
      />

      <Section eyebrow="Coverage" title="Supported exchanges">
        <ExchangeTable />
      </Section>

      <Section
        eyebrow="At a glance"
        title="Plug in, trade in 60 seconds">
        <LogoRibbon items={EXCHANGE_LOGOS} minCellWidth={150} />
      </Section>

      <CTABand
        title="Your exchange is missing?"
        description="Talk to our team — we add new exchanges on request."
        actions={[
          {label: 'Book a free call', to: BOOK_A_CALL},
          {label: 'Email us', to: EMAIL, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
