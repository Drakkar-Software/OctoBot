import type {ReactNode} from 'react';
import Translate, {translate} from '@docusaurus/Translate';
import GlassCard from '@site/src/components/GlassCard';
import Badge from '@site/src/components/Badge';
import styles from './ConverterCard.module.css';

/*
 * Page-local converter mock for /tools/converter.
 *
 * Underscore prefix keeps Docusaurus from treating this as a route. This is a
 * static marketing mock — live conversion lives on octobot.cloud. The numbers
 * below are representative samples, not real-time data.
 */

interface ConverterRow {
  label: string;
  value: string;
}

const ROWS: ConverterRow[] = [
  {
    label: translate({
      id: 'tools.converter.card.row.price',
      message: 'Price',
      description: 'Converter card row label: price',
    }),
    value: '1 BTC = 64,280.00 USD',
  },
  {
    label: translate({
      id: 'tools.converter.card.row.quantity',
      message: 'Quantity',
      description: 'Converter card row label: quantity',
    }),
    value: '0.25 BTC',
  },
  {
    label: translate({
      id: 'tools.converter.card.row.value',
      message: 'Value',
      description: 'Converter card row label: value',
    }),
    value: '16,070.00 USD',
  },
];

export default function ConverterCard(): ReactNode {
  return (
    <GlassCard variant="hero" padded className={styles.card}>
      <div className={styles.head}>
        <div className={styles.pair}>
          <span className={styles.coin}>BTC</span>
          <span className={styles.arrow} aria-hidden="true">
            →
          </span>
          <span className={styles.coin}>USD</span>
        </div>
        <Badge tone="frost" dot>
          <Translate
            id="tools.converter.card.badge.livePrice"
            description="Converter card badge: live price">
            Live price
          </Translate>
        </Badge>
      </div>

      <dl className={styles.rows}>
        {ROWS.map((row) => (
          <div key={row.label} className={styles.row}>
            <dt className={styles.rowLabel}>{row.label}</dt>
            <dd className={styles.rowValue}>{row.value}</dd>
          </div>
        ))}
      </dl>

      <p className={styles.asOf}>
        <Translate
          id="tools.converter.card.asOf"
          description="Converter card timestamp caption"
          values={{timestamp: 'May 14, 2026 · 14:00 UTC'}}>
          {'As of {timestamp}'}
        </Translate>
      </p>
    </GlassCard>
  );
}
