import React, {type ReactNode} from 'react';
import styles from './styles.module.css';

export interface InlineStat {
  /** Large mono figure, e.g. "62" or "$1.8B". */
  value: ReactNode;
  /** Supporting label under the figure. */
  label: string;
}

interface InlineStatsProps {
  stats: InlineStat[];
}

/**
 * Compact inline stat row — figure + label pairs in a wrapping flex line.
 * Lighter than `StatStrip`; meant to sit inside a hero or section, not as a
 * standalone panel.
 */
export default function InlineStats({stats}: InlineStatsProps): ReactNode {
  return (
    <div className={styles.row}>
      {stats.map((stat) => (
        <div key={stat.label} className={styles.item}>
          <div className={styles.value}>{stat.value}</div>
          <div className={styles.label}>{stat.label}</div>
        </div>
      ))}
    </div>
  );
}
