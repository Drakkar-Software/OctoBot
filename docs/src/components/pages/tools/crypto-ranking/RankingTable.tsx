import type {ReactNode} from 'react';
import Translate from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import styles from './RankingTable.module.css';

/*
 * Page-local market-cap ranking mock for /tools/crypto-ranking.
 *
 * Underscore prefix keeps Docusaurus from treating this as a route. This is a
 * static marketing mock — the live ranking, powered by Coingecko data, is
 * served from octobot.cloud. The numbers below are representative samples.
 */

interface RankingRow {
  rank: number;
  name: string;
  ticker: string;
  price: string;
  marketCap: string;
  change24h: number;
}

const ROWS: RankingRow[] = [
  {rank: 1, name: 'Bitcoin', ticker: 'BTC', price: '$64,280.00', marketCap: '$1.27T', change24h: 1.84},
  {rank: 2, name: 'Ethereum', ticker: 'ETH', price: '$3,142.50', marketCap: '$377.6B', change24h: -0.92},
  {rank: 3, name: 'Tether', ticker: 'USDT', price: '$1.00', marketCap: '$111.2B', change24h: 0.01},
  {rank: 4, name: 'BNB', ticker: 'BNB', price: '$582.40', marketCap: '$85.9B', change24h: 2.37},
  {rank: 5, name: 'Solana', ticker: 'SOL', price: '$148.20', marketCap: '$68.4B', change24h: 4.12},
  {rank: 6, name: 'XRP', ticker: 'XRP', price: '$0.5280', marketCap: '$29.3B', change24h: -1.46},
  {rank: 7, name: 'USD Coin', ticker: 'USDC', price: '$1.00', marketCap: '$33.1B', change24h: -0.02},
  {rank: 8, name: 'Cardano', ticker: 'ADA', price: '$0.4490', marketCap: '$15.8B', change24h: 3.05},
];

function formatChange(change: number): string {
  return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
}

export default function RankingTable(): ReactNode {
  return (
    <GlassCard variant="strong" padded={false} className={styles.card}>
      <div className={styles.scroll}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th className={styles.rankCol}>#</th>
              <th>
                <Translate
                  id="tools.cryptoRanking.table.header.name"
                  description="Crypto ranking table header: name">
                  Name
                </Translate>
              </th>
              <th className={styles.numCol}>
                <Translate
                  id="tools.cryptoRanking.table.header.price"
                  description="Crypto ranking table header: USD price">
                  USD Price
                </Translate>
              </th>
              <th className={styles.numCol}>
                <Translate
                  id="tools.cryptoRanking.table.header.marketCap"
                  description="Crypto ranking table header: USD market cap">
                  USD Market cap
                </Translate>
              </th>
              <th className={styles.numCol}>
                <Translate
                  id="tools.cryptoRanking.table.header.change24h"
                  description="Crypto ranking table header: 24h change">
                  24h
                </Translate>
              </th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.ticker}>
                <td className={styles.rank}>{row.rank}</td>
                <td>
                  <span className={styles.name}>{row.name}</span>
                  <span className={styles.ticker}>{row.ticker}</span>
                </td>
                <td className={styles.num}>{row.price}</td>
                <td className={styles.num}>{row.marketCap}</td>
                <td
                  className={styles.num}
                  style={{
                    color:
                      row.change24h >= 0 ? 'var(--ng-pos)' : 'var(--ng-neg)',
                  }}>
                  {formatChange(row.change24h)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </GlassCard>
  );
}
