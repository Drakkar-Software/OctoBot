import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

export interface PriceCell {
  /** Small uppercase tag, e.g. "FREE · FOREVER". */
  tag: string;
  /** Large headline figure, e.g. "€0" or "€39". */
  price: ReactNode;
  /** Optional small suffix rendered next to the figure, e.g. "–89". */
  priceSuffix?: ReactNode;
  /** Bold one-line label under the figure. */
  label: string;
  /** Supporting copy. */
  note: ReactNode;
  /** Visual treatment. 'feat' = highlighted, 'muted' = struck-through. */
  variant?: 'default' | 'feat' | 'muted';
}

interface PricingStripProps {
  cells: PriceCell[];
}

const VARIANT_CLASS: Record<NonNullable<PriceCell['variant']>, string> = {
  default: '',
  feat: styles.feat,
  muted: styles.muted,
};

/**
 * Horizontal pricing strip — equal-weight cells inside one elevated glass
 * panel. Use the 'feat' variant to highlight the recommended tier.
 */
export default function PricingStrip({cells}: PricingStripProps): ReactNode {
  return (
    <GlassCard variant="strong" padded={false} className={styles.strip}>
      {cells.map((cell) => (
        <div
          key={cell.tag}
          className={`${styles.cell} ${VARIANT_CLASS[cell.variant ?? 'default']}`}>
          <span className={styles.tag}>{cell.tag}</span>
          <div className={styles.price}>
            {cell.price}
            {cell.priceSuffix && (
              <small className={styles.suffix}>{cell.priceSuffix}</small>
            )}
          </div>
          <span className={styles.label}>{cell.label}</span>
          <p className={styles.note}>{cell.note}</p>
        </div>
      ))}
    </GlassCard>
  );
}
