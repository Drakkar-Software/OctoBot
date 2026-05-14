import type {ReactNode} from 'react';
import {LandingLayout, Hero, Section, CTABand} from '@site/src/components/landing';
import RankingTable from '@site/src/components/pages/tools/crypto-ranking/RankingTable';
import styles from './crypto-ranking.module.css';

/*
 * Cryptocurrencies ranking tool page — route: /tools/crypto-ranking.
 *
 * Migrated from the OctoBot Cloud marketing site into the Neo Glass Dark
 * landing toolkit. Built the same way as the feature pages: a navbar-less
 * LandingLayout composed from reusable components, plus a page-local
 * _RankingTable mock for the market-cap ranking grid.
 */

const CLOUD = 'https://www.octobot.cloud';
const GUIDES = '/guides/octobot';

export default function CryptoRankingTool(): ReactNode {
  return (
    <LandingLayout
      title="Cryptocurrencies ranking"
      description="Cryptocurrency rankings by market cap, powered by Coingecko data — track the top coins by price, market cap and 24h change.">
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow="Crypto ranking"
        title={
          <>
            <span className="ng-text-gradient">
              Cryptocurrencies ranking.
            </span>
          </>
        }
        subtitle="Cryptocurrency rankings by market cap, powered by Coingecko data."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
        meta={[
          {label: 'Market cap ranking', dot: true},
          {label: 'Powered by Coingecko'},
          {label: 'No account required'},
        ]}
      />

      <Section
        eyebrow="Market cap"
        title="Top cryptocurrencies by market cap"
        lead="A sample of the market-cap ranking OctoBot surfaces — price, market cap and 24h change for the largest cryptocurrencies. The live ranking updates continuously on OctoBot Cloud.">
        <RankingTable />
        <p className={styles.note}>
          Rankings and market data are provided by Coingecko. Coingecko is not
          related to OctoBot.
        </p>
      </Section>

      <CTABand
        title="Put the market ranking to work on your portfolio"
        description="Create your trading bot for free on OctoBot Cloud, or read the guides first."
        actions={[
          {label: 'Invest for free', to: CLOUD},
          {label: 'Read the guides', to: GUIDES, variant: 'ghost'},
        ]}
      />
    </LandingLayout>
  );
}
