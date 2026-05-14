import type {ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './OpportunityCards.module.css';

/*
 * Page-local sample-data grid for /tools/triangular-arbitrage-crypto.
 * Underscore prefix keeps Docusaurus from treating this as a route.
 *
 * Static marketing mock — live arbitrage opportunities are detected on
 * octobot.cloud. The sample set below is representative only.
 */

interface Opportunity {
  path: string;
  exchange: string;
  spread: string;
}

const OPPORTUNITIES: Opportunity[] = [
  {
    path: 'USDT → BTC → ETH → USDT',
    exchange: 'Binance',
    spread: '+0.42%',
  },
  {
    path: 'USDT → SOL → BTC → USDT',
    exchange: 'Kraken',
    spread: '+0.31%',
  },
  {
    path: 'BTC → ETH → BNB → BTC',
    exchange: 'Bybit',
    spread: '+0.27%',
  },
];

export default function OpportunityCards(): ReactNode {
  return (
    <div className={styles.cardGrid}>
      {OPPORTUNITIES.map((opportunity) => (
        <GlassCard key={opportunity.path} variant="strong">
          <div className={styles.arbCard}>
            <div className={styles.arbPath}>{opportunity.path}</div>
            <div className={styles.arbExchange}>On {opportunity.exchange}</div>
            <div>
              <div className={styles.arbSpreadLabel}>Estimated spread</div>
              <div className={styles.arbSpread}>{opportunity.spread}</div>
            </div>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
