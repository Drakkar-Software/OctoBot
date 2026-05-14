import React, {type ReactNode} from 'react';
import styles from './styles.module.css';

interface SectionProps {
  children: ReactNode;
  /** Optional small uppercase label above the heading. */
  eyebrow?: string;
  /** Section heading. */
  title?: ReactNode;
  /** Supporting line under the heading. */
  lead?: ReactNode;
  /** Center the header block. Default true. */
  centered?: boolean;
  /** Vertical rhythm. Default 'md'. */
  spacing?: 'sm' | 'md' | 'lg';
  id?: string;
  className?: string;
}

const SPACING: Record<NonNullable<SectionProps['spacing']>, string> = {
  sm: styles.spacingSm,
  md: styles.spacingMd,
  lg: styles.spacingLg,
};

/**
 * Generic landing-page section wrapper — constrained width, consistent
 * vertical rhythm, and an optional eyebrow / title / lead header block.
 */
export default function Section({
  children,
  eyebrow,
  title,
  lead,
  centered = true,
  spacing = 'md',
  id,
  className,
}: SectionProps): ReactNode {
  const hasHeader = eyebrow || title || lead;
  return (
    <section
      id={id}
      className={[styles.section, SPACING[spacing], className]
        .filter(Boolean)
        .join(' ')}>
      <div className={styles.inner}>
        {hasHeader && (
          <header
            className={`${styles.header} ${centered ? styles.centered : ''}`}>
            {eyebrow && <span className="ng-eyebrow">{eyebrow}</span>}
            {title && <h2 className={styles.title}>{title}</h2>}
            {lead && <p className={styles.lead}>{lead}</p>}
          </header>
        )}
        {children}
      </div>
    </section>
  );
}
