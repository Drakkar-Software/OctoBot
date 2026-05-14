import type {ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './ScalpingSignalCards.module.css';

/*
 * Page-local scalping-signal mock for /tools/scalping-signals.
 *
 * Underscore prefix keeps Docusaurus from treating this as a route. This is a
 * static marketing mock — live signals are served from octobot.cloud. The
 * numbers below are representative samples, not real-time data.
 */

type Side = 'LONG' | 'SHORT';

interface ScalpingSignal {
  side: Side;
  pair: string;
  exchange: string;
  entry: string;
  takeProfit: string;
  stopLoss: string;
  expectedProfit: string;
}

const SIGNALS: ScalpingSignal[] = [
  {
    side: 'LONG',
    pair: 'BTC/USDT',
    exchange: 'Binance',
    entry: '64,280.00',
    takeProfit: '65,140.00',
    stopLoss: '63,920.00',
    expectedProfit: '+1.34%',
  },
  {
    side: 'SHORT',
    pair: 'ETH/USDT',
    exchange: 'Binance',
    entry: '3,142.50',
    takeProfit: '3,094.00',
    stopLoss: '3,168.00',
    expectedProfit: '+1.54%',
  },
  {
    side: 'LONG',
    pair: 'SOL/USDT',
    exchange: 'Binance',
    entry: '148.20',
    takeProfit: '151.60',
    stopLoss: '146.40',
    expectedProfit: '+2.29%',
  },
  {
    side: 'SHORT',
    pair: 'XRP/USDT',
    exchange: 'Binance',
    entry: '0.5280',
    takeProfit: '0.5190',
    stopLoss: '0.5325',
    expectedProfit: '+1.70%',
  },
];

const STAT_ROWS: {key: keyof ScalpingSignal; label: string}[] = [
  {key: 'entry', label: 'Entry price'},
  {key: 'takeProfit', label: 'Take profit'},
  {key: 'stopLoss', label: 'Stop loss'},
  {key: 'expectedProfit', label: 'Expected profit'},
];

export default function ScalpingSignalCards(): ReactNode {
  return (
    <div className={styles.grid}>
      {SIGNALS.map((signal) => (
        <GlassCard
          key={signal.pair}
          variant="strong"
          padded
          className={styles.card}>
          <div className={styles.head}>
            <Badge tone={signal.side === 'LONG' ? 'pos' : 'neg'}>
              {signal.side}
            </Badge>
            <span className={styles.pair}>{signal.pair}</span>
          </div>

          <p className={styles.exchange}>On {signal.exchange}</p>

          <dl className={styles.stats}>
            {STAT_ROWS.map((row) => (
              <div key={row.key} className={styles.stat}>
                <dt className={styles.statLabel}>{row.label}</dt>
                <dd className={styles.statValue}>{signal[row.key]}</dd>
              </div>
            ))}
          </dl>
        </GlassCard>
      ))}
    </div>
  );
}
