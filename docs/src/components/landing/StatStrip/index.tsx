import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

export interface Stat {
  /** Large display figure — wrap part in <span> for the gradient accent. */
  value: ReactNode;
  /** Label under the figure. */
  label: string;
  /** Optional small uppercase sub-line. */
  sub?: string;
}

interface StatStripProps {
  /** Optional leading header cell. */
  head?: {eyebrow?: string; title: ReactNode};
  stats: Stat[];
}

/**
 * Horizontal stat ribbon — an optional header cell followed by evenly
 * divided stat cells, all inside one elevated glass panel.
 */
export default function StatStrip({head, stats}: StatStripProps): ReactNode {
  return (
    <GlassCard
      variant="strong"
      padded={false}
      className={`${styles.strip} ${head ? styles.withHead : ''}`}
      style={{'--stat-count': stats.length} as React.CSSProperties}>
      {head && (
        <div className={styles.head}>
          {head.eyebrow && <span className="ng-eyebrow">{head.eyebrow}</span>}
          <h3 className={styles.headTitle}>{head.title}</h3>
        </div>
      )}
      {stats.map((stat) => (
        <div key={stat.label} className={styles.cell}>
          <div className={styles.value}>{stat.value}</div>
          <div className={styles.label}>{stat.label}</div>
          {stat.sub && <div className={styles.sub}>{stat.sub}</div>}
        </div>
      ))}
    </GlassCard>
  );
}
