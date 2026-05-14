import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import styles from './styles.module.css';

interface HeroAction {
  label: string;
  to: string;
  variant?: 'primary' | 'ghost' | 'surface';
}

interface HeroProps {
  eyebrow?: string;
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: HeroAction[];
  /** Optional visual rendered to the right of the copy (≥960px). */
  visual?: ReactNode;
  /** Small trust line under the actions (e.g. "Open source · MIT licensed"). */
  note?: ReactNode;
}

/**
 * Landing-page hero. Single-column centered when no `visual` is passed,
 * two-column (copy + visual) on wide screens when it is.
 */
export default function Hero({
  eyebrow,
  title,
  subtitle,
  actions = [],
  visual,
  note,
}: HeroProps): ReactNode {
  return (
    <section className={`${styles.hero} ${visual ? styles.split : ''}`}>
      <div className={styles.inner}>
        <div className={styles.copy}>
          {eyebrow && <span className="ng-eyebrow">{eyebrow}</span>}
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          {actions.length > 0 && (
            <div className={styles.actions}>
              {actions.map((action) => (
                <Link
                  key={action.to}
                  to={action.to}
                  className={`ng-btn ng-btn--${action.variant ?? 'primary'}`}>
                  {action.label}
                </Link>
              ))}
            </div>
          )}
          {note && <p className={styles.note}>{note}</p>}
        </div>
        {visual && <div className={styles.visual}>{visual}</div>}
      </div>
    </section>
  );
}
