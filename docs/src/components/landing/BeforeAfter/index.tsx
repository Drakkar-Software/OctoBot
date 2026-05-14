import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

interface BeforeAfterColumn {
  /** Small uppercase column label, e.g. "Before" / "With OctoBot". */
  label: string;
  /** One entry per row. */
  items: ReactNode[];
}

interface BeforeAfterProps {
  before: BeforeAfterColumn;
  after: BeforeAfterColumn;
}

/**
 * Two-column "before / after" comparison — a muted list of pain points and an
 * elevated glass list of resolutions, joined by an arrow.
 */
export default function BeforeAfter({
  before,
  after,
}: BeforeAfterProps): ReactNode {
  return (
    <div className={styles.grid}>
      <div className={`ng-card ${styles.col} ${styles.before}`}>
        <span className={styles.tag}>{before.label}</span>
        <ul className={styles.list}>
          {before.items.map((item, i) => (
            <li key={i}>
              <span className={`${styles.mark} ${styles.x}`} aria-hidden="true">
                ×
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className={styles.arrow} aria-hidden="true">
        →
      </div>

      <GlassCard variant="strong" padded={false} className={styles.col}>
        <span className={`${styles.tag} ${styles.tagOn}`}>{after.label}</span>
        <ul className={styles.list}>
          {after.items.map((item, i) => (
            <li key={i}>
              <span
                className={`${styles.mark} ${styles.check}`}
                aria-hidden="true">
                ✓
              </span>
              <span>{item}</span>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}
