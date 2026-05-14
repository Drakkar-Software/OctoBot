import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import styles from './styles.module.css';

interface HeroAction {
  label: string;
  to: string;
  variant?: 'primary' | 'ghost' | 'surface';
}

interface HeroMetaItem {
  label: string;
  /** Show a leading turquoise status dot. */
  dot?: boolean;
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
  /** Trust / stat chips rendered as a pill row under the actions. */
  meta?: HeroMetaItem[];
  /** Free-form block rendered at the bottom of the copy column (e.g. stats). */
  aside?: ReactNode;
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
  meta = [],
  aside,
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
          {meta.length > 0 && (
            <div className={styles.meta}>
              {meta.map((item) => (
                <span key={item.label} className="ng-chip-static">
                  {item.dot && (
                    <span className="ng-chip-static__dot" aria-hidden="true" />
                  )}
                  {item.label}
                </span>
              ))}
            </div>
          )}
          {note && <p className={styles.note}>{note}</p>}
          {aside && <div className={styles.aside}>{aside}</div>}
        </div>
        {visual && <div className={styles.visual}>{visual}</div>}
      </div>
    </section>
  );
}
