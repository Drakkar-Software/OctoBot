import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

export interface Step {
  /** Optional emoji / glyph rendered in the step's icon circle. */
  icon?: ReactNode;
  title: string;
  description: ReactNode;
}

interface StepListProps {
  steps: Step[];
  /** Layout direction. Default 'row' (numbered cards side by side). */
  layout?: 'row' | 'column';
}

/**
 * Numbered "how it works" steps — auto-numbered glass cards laid out as a
 * row on desktop or a vertical list. Each step shows its index, an optional
 * icon, a title and a description.
 */
export default function StepList({
  steps,
  layout = 'row',
}: StepListProps): ReactNode {
  return (
    <div
      className={`${styles.list} ${layout === 'column' ? styles.column : styles.row}`}
      style={{'--step-count': steps.length} as React.CSSProperties}>
      {steps.map((step, index) => (
        <GlassCard key={step.title} variant="strong" className={styles.step}>
          <div className={styles.head}>
            <span className={styles.number}>
              {String(index + 1).padStart(2, '0')}
            </span>
            {step.icon && (
              <span className={`ng-icon-circle ${styles.icon}`} aria-hidden="true">
                {step.icon}
              </span>
            )}
          </div>
          <h3 className={styles.title}>{step.title}</h3>
          <p className={styles.description}>{step.description}</p>
        </GlassCard>
      ))}
    </div>
  );
}
