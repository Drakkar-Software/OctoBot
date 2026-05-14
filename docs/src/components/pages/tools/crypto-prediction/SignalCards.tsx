import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './SignalCards.module.css';

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
    rationale: translate({
      id: 'tools.cryptoPrediction.signal.btc.rationale',
      message:
        'Momentum and sentiment point to continued upside on Bitcoin.',
      description: 'Crypto prediction sample signal rationale for BTC',
    }),
  },
  {
    side: 'SELL',
    pair: 'ETH/USDT',
    exchange: 'Kraken',
    rationale: translate({
      id: 'tools.cryptoPrediction.signal.eth.rationale',
      message:
        'Cooling momentum suggests taking profit on Ethereum here.',
      description: 'Crypto prediction sample signal rationale for ETH',
    }),
  },
  {
    side: 'BUY',
    pair: 'SOL/USDT',
    exchange: 'Bybit',
    rationale: translate({
      id: 'tools.cryptoPrediction.signal.sol.rationale',
      message:
        'Trend detection flags a fresh entry opportunity on Solana.',
      description: 'Crypto prediction sample signal rationale for SOL',
    }),
  },
  {
    side: 'BUY',
    pair: 'BNB/USDT',
    exchange: 'Binance',
    rationale: translate({
      id: 'tools.cryptoPrediction.signal.bnb.rationale',
      message:
        'Market data reads constructive — ChatGPT favors a long on BNB.',
      description: 'Crypto prediction sample signal rationale for BNB',
    }),
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
            <div className={styles.signalExchange}>
              <Translate
                id="tools.cryptoPrediction.signal.onExchange"
                description="Crypto prediction signal exchange label"
                values={{exchange: signal.exchange}}>
                {'On {exchange}'}
              </Translate>
            </div>
            <p className={styles.signalRationale}>{signal.rationale}</p>
          </div>
        </GlassCard>
      ))}
    </div>
  );
}
