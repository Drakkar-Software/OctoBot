import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

export interface Feature {
  /** Emoji or short glyph rendered in the icon circle. */
  icon: ReactNode;
  title: string;
  description: ReactNode;
  /** Optional — makes the whole card a link. */
  to?: string;
}

interface FeatureGridProps {
  features: Feature[];
  /** Columns at desktop width. Default 3. */
  columns?: 2 | 3;
}

/** Responsive grid of glass feature cards. */
export default function FeatureGrid({
  features,
  columns = 3,
}: FeatureGridProps): ReactNode {
  return (
    <div
      className={styles.grid}
      style={{'--cols': columns} as React.CSSProperties}>
      {features.map((feature) => (
        <GlassCard
          key={feature.title}
          variant="strong"
          to={feature.to}
          className={styles.card}>
          <div className={`ng-icon-circle ${styles.icon}`} aria-hidden="true">
            {feature.icon}
          </div>
          <h3 className={styles.title}>{feature.title}</h3>
          <p className={styles.description}>{feature.description}</p>
        </GlassCard>
      ))}
    </div>
  );
}
