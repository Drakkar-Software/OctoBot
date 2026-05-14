import type {ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './_styles.module.css';

/*
 * Page-local sample-data grid for /tools/crypto-prediction.
 * Underscore prefix keeps Docusaurus from treating this as a route.
 *
 * Static marketing mock — live ChatGPT predictions are served from
 * octobot.cloud. The sample set below is representative only.
 */

type SignalSide = 'BUY' | 'SELL';

interface Signal {
  side: SignalSide;
  pair: string;
  exchange: string;
  rationale: string;
}

const SIGNALS: Signal[] = [
  {
    side: 'BUY',
    pair: 'BTC/USDT',
    exchange: 'Binance',
    rationale:
      'Momentum and sentiment point to continued upside on Bitcoin.',
  },
  {
    side: 'SELL',
    pair: 'ETH/USDT',
    exchange: 'Kraken',
    rationale:
      'Cooling momentum suggests taking profit on Ethereum here.',
  },
  {
    side: 'BUY',
    pair: 'SOL/USDT',
    exchange: 'Bybit',
    rationale:
      'Trend detection flags a fresh entry opportunity on Solana.',
  },
  {
    side: 'BUY',
    pair: 'BNB/USDT',
    exchange: 'Binance',
    rationale:
      'Market data reads constructive — ChatGPT favors a long on BNB.',
  },
];

export default function SignalCards(): ReactNode {
  return (
    <div className={styles.cardGrid}>
      {SIGNALS.map((signal) => (
        <GlassCard key={`${signal.pair}-${signal.exchange}`} variant="strong">
          <div className={styles.signalCard}>
            <div className={styles.signalHead}>
              <span className={styles.signalPair}>{signal.pair}</span>
              <Badge tone={signal.side === 'BUY' ? 'pos' : 'neg'} dot>
                {signal.side}
              </Badge>
            </div>
            <div className={styles.signalExchange}>On {signal.exchange}</div>
            <p className={styles.signalRationale}>{signal.rationale}</p>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
