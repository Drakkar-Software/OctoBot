import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
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
      title={translate({
        id: 'tools.cryptoRanking.layout.title',
        message: 'Cryptocurrencies ranking',
        description: 'Crypto ranking page meta title',
      })}
      description={translate({
        id: 'tools.cryptoRanking.layout.description',
        message:
          'Cryptocurrency rankings by market cap, powered by Coingecko data — track the top coins by price, market cap and 24h change.',
        description: 'Crypto ranking page meta description',
      })}>
      <div className={styles.gridVeil} aria-hidden="true" />

      <Hero
        eyebrow={translate({
          id: 'tools.cryptoRanking.hero.eyebrow',
          message: 'Crypto ranking',
          description: 'Crypto ranking hero eyebrow',
        })}
        title={
          <span className="ng-text-gradient">
            <Translate
              id="tools.cryptoRanking.hero.title"
              description="Crypto ranking hero title">
              Cryptocurrencies ranking.
            </Translate>
          </span>
        }
        subtitle={translate({
          id: 'tools.cryptoRanking.hero.subtitle',
          message:
            'Cryptocurrency rankings by market cap, powered by Coingecko data.',
          description: 'Crypto ranking hero subtitle',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.cryptoRanking.hero.action.invest',
              message: 'Invest for free',
              description: 'Crypto ranking hero invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.cryptoRanking.hero.action.guides',
              message: 'Read the guides',
              description: 'Crypto ranking hero guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
        meta={[
          {
            label: translate({
              id: 'tools.cryptoRanking.hero.meta.ranking',
              message: 'Market cap ranking',
              description: 'Crypto ranking hero meta: market cap ranking',
            }),
            dot: true,
          },
          {
            label: translate({
              id: 'tools.cryptoRanking.hero.meta.coingecko',
              message: 'Powered by Coingecko',
              description: 'Crypto ranking hero meta: powered by Coingecko',
            }),
          },
          {
            label: translate({
              id: 'tools.cryptoRanking.hero.meta.noAccount',
              message: 'No account required',
              description: 'Crypto ranking hero meta: no account required',
            }),
          },
        ]}
      />

      <Section
        eyebrow={translate({
          id: 'tools.cryptoRanking.market.eyebrow',
          message: 'Market cap',
          description: 'Crypto ranking market cap section eyebrow',
        })}
        title={translate({
          id: 'tools.cryptoRanking.market.title',
          message: 'Top cryptocurrencies by market cap',
          description: 'Crypto ranking market cap section title',
        })}
        lead={translate({
          id: 'tools.cryptoRanking.market.lead',
          message:
            'A sample of the market-cap ranking OctoBot surfaces — price, market cap and 24h change for the largest cryptocurrencies. The live ranking updates continuously on OctoBot Cloud.',
          description: 'Crypto ranking market cap section lead',
        })}>
        <RankingTable />
        <p className={styles.note}>
          <Translate
            id="tools.cryptoRanking.market.note"
            description="Crypto ranking Coingecko attribution note">
            Rankings and market data are provided by Coingecko. Coingecko is not
            related to OctoBot.
          </Translate>
        </p>
      </Section>

      <CTABand
        title={translate({
          id: 'tools.cryptoRanking.cta.title',
          message: 'Put the market ranking to work on your portfolio',
          description: 'Crypto ranking CTA band title',
        })}
        description={translate({
          id: 'tools.cryptoRanking.cta.description',
          message:
            'Create your trading bot for free on OctoBot Cloud, or read the guides first.',
          description: 'Crypto ranking CTA band description',
        })}
        actions={[
          {
            label: translate({
              id: 'tools.cryptoRanking.cta.action.invest',
              message: 'Invest for free',
              description: 'Crypto ranking CTA invest action label',
            }),
            to: CLOUD,
          },
          {
            label: translate({
              id: 'tools.cryptoRanking.cta.action.guides',
              message: 'Read the guides',
              description: 'Crypto ranking CTA guides action label',
            }),
            to: GUIDES,
            variant: 'ghost',
          },
        ]}
      />
    </LandingLayout>
  );
}
