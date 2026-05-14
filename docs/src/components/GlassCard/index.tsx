import React, {type ReactNode} from 'react';
import Link from '@docusaurus/Link';
import styles from './styles.module.css';

type GlassCardVariant = 'default' | 'strong' | 'hero' | 'footer';

interface GlassCardProps {
  children: ReactNode;
  /** Surface weight — maps to the .ng-card* primitives in theme-tokens.css. */
  variant?: GlassCardVariant;
  /** Adds the hover-lift treatment. Implied when `to`/`href` is set. */
  interactive?: boolean;
  /** Internal route — renders the card as a Docusaurus <Link>. */
  to?: string;
  /** External URL — renders the card as a Docusaurus <Link>. */
  href?: string;
  /** Apply standard internal padding (18px). Default true. */
  padded?: boolean;
  className?: string;
}

const VARIANT_CLASS: Record<GlassCardVariant, string> = {
  default: 'ng-card',
  strong: 'ng-card-strong',
  hero: 'ng-card-hero',
  footer: 'ng-card-footer',
};

/**
 * Neo Glass Dark surface primitive. Use for any boxed content block — feature
 * cards, callouts, panels. Pass `to`/`href` to make the whole card a link.
 */
export default function GlassCard({
  children,
  variant = 'default',
  interactive,
  to,
  href,
  padded = true,
  className,
}: GlassCardProps): ReactNode {
  const isLink = Boolean(to || href);
  const classes = [
    VARIANT_CLASS[variant],
    (interactive || isLink) && 'ng-card-interactive',
    padded && styles.padded,
    isLink && styles.linkCard,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  if (isLink) {
    return (
      <Link to={to} href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return <div className={classes}>{children}</div>;
}
