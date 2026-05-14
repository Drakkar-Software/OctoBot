import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import styles from './styles.module.css';

interface CTAAction {
  label: string;
  to: string;
  variant?: 'primary' | 'ghost' | 'surface';
}

interface CTABandProps {
  title: ReactNode;
  description?: ReactNode;
  actions: CTAAction[];
}

/** Closing call-to-action band — a hero-weight glass panel near the page end. */
export default function CTABand({
  title,
  description,
  actions,
}: CTABandProps): ReactNode {
  return (
    <section className={styles.wrap}>
      <div className={`ng-card-hero ${styles.band}`}>
        <h2 className={styles.title}>{title}</h2>
        {description && <p className={styles.description}>{description}</p>}
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
      </div>
    </section>
  );
}
