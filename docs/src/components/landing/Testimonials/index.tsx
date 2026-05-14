import React, {type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './styles.module.css';

export interface Testimonial {
  quote: ReactNode;
  name: string;
  /** Role / location line under the name. */
  role: string;
  /** CSS background for the initials avatar. Defaults to a frost gradient. */
  avatar?: string;
}

interface TestimonialsProps {
  /** Optional large lead testimonial shown beside the smaller ones. */
  featured?: Testimonial;
  /** Supporting testimonials. */
  items: Testimonial[];
}

const DEFAULT_AVATAR = 'linear-gradient(135deg, #65e7cf, #4893f1)';

function Avatar({
  name,
  avatar,
  className,
}: {
  name: string;
  avatar?: string;
  className: string;
}): ReactNode {
  return (
    <span
      className={className}
      style={{background: avatar ?? DEFAULT_AVATAR}}
      aria-hidden="true">
      {name.charAt(0)}
    </span>
  );
}

/**
 * Testimonial layout. With a `featured` entry it renders a large lead quote
 * beside a stack of smaller ones; without it, a plain responsive grid.
 */
export default function Testimonials({
  featured,
  items,
}: TestimonialsProps): ReactNode {
  if (!featured) {
    return (
      <div className={styles.grid}>
        {items.map((t) => (
          <GlassCard key={t.name} className={styles.mini}>
            <p className={styles.quote}>{t.quote}</p>
            <div className={styles.meta}>
              <Avatar name={t.name} avatar={t.avatar} className={styles.avatar} />
              <div className={styles.who}>
                <b>{t.name}</b>
                <span>{t.role}</span>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>
    );
  }

  return (
    <div className={styles.featGrid}>
      <GlassCard variant="strong" className={styles.big}>
        <p className={styles.bigQuote}>{featured.quote}</p>
        <div className={styles.meta}>
          <Avatar
            name={featured.name}
            avatar={featured.avatar}
            className={styles.avatarLg}
          />
          <div className={styles.who}>
            <b>{featured.name}</b>
            <span>{featured.role}</span>
          </div>
        </div>
      </GlassCard>
      <div className={styles.side}>
        {items.map((t) => (
          <GlassCard key={t.name} className={styles.mini}>
            <p className={styles.quote}>{t.quote}</p>
            <div className={styles.meta}>
              <Avatar name={t.name} avatar={t.avatar} className={styles.avatar} />
              <div className={styles.who}>
                <b>{t.name}</b>
                <span>{t.role}</span>
              </div>
            </div>
          </GlassCard>
        ))}
      </div>
    </div>
  );
}
