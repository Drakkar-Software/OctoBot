import type {ReactNode} from 'react';
import styles from './ExchangeTable.module.css';

/*
 * Page-local supported-exchanges table — used by the /supported-exchanges
 * page. A styled, horizontally-scrollable table of representative sample
 * exchanges (rank, name, trust score, 24h volume). The values are a static
 * marketing mock; the live ranking lives on octobot.cloud.
 */

interface ExchangeRow {
  rank: number;
  name: string;
  trustScore: number;
  volumeUsd: string;
}

const EXCHANGES: ExchangeRow[] = [
  {rank: 1, name: 'Binance', trustScore: 10, volumeUsd: '$14,820,000,000'},
  {rank: 2, name: 'Coinbase', trustScore: 10, volumeUsd: '$3,560,000,000'},
  {rank: 3, name: 'Kraken', trustScore: 9, volumeUsd: '$1,240,000,000'},
  {rank: 4, name: 'OKX', trustScore: 9, volumeUsd: '$2,910,000,000'},
  {rank: 5, name: 'Bybit', trustScore: 8, volumeUsd: '$2,180,000,000'},
  {rank: 6, name: 'KuCoin', trustScore: 8, volumeUsd: '$1,070,000,000'},
  {rank: 7, name: 'Bitget', trustScore: 8, volumeUsd: '$1,640,000,000'},
  {rank: 8, name: 'Gate.io', trustScore: 7, volumeUsd: '$1,390,000,000'},
  {rank: 9, name: 'HTX', trustScore: 7, volumeUsd: '$980,000,000'},
  {rank: 10, name: 'MEXC', trustScore: 7, volumeUsd: '$1,510,000,000'},
];

export default function ExchangeTable(): ReactNode {
  return (
    <>
      <div className={`ng-card ${styles.wrap}`}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.alignRight}>#</th>
              <th>Name</th>
              <th>Trust score</th>
              <th className={styles.alignRight}>24h volume (USD)</th>
            </tr>
          </thead>
          <tbody>
            {EXCHANGES.map((exchange) => (
              <tr key={exchange.name}>
                <td className={`${styles.num} ${styles.alignRight}`}>
                  {exchange.rank}
                </td>
                <td className={styles.name}>{exchange.name}</td>
                <td className={styles.num}>{exchange.trustScore}/10</td>
                <td className={`${styles.num} ${styles.alignRight}`}>
                  {exchange.volumeUsd}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className={styles.note}>
        Trust scores and normalized trading volumes are provided by Coingecko.
        Coingecko is not related to OctoBot.
      </p>
    </>
  );
}
