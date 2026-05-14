import React, {type ReactNode} from 'react';

type BadgeTone = 'default' | 'frost' | 'pos' | 'neg' | 'warn';

interface BadgeProps {
  children: ReactNode;
  /** Semantic color tone — maps to .ng-badge--* in theme-tokens.css. */
  tone?: BadgeTone;
  /** Show a leading status dot in the tone color. */
  dot?: boolean;
  className?: string;
}

const TONE_CLASS: Record<BadgeTone, string> = {
  default: '',
  frost: 'ng-badge--frost',
  pos: 'ng-badge--pos',
  neg: 'ng-badge--neg',
  warn: 'ng-badge--warn',
};

/**
 * Neo Glass Dark pill badge — status labels, tags, counts. Tone drives the
 * background / text / border color triplet.
 */
export default function Badge({
  children,
  tone = 'default',
  dot,
  className,
}: BadgeProps): ReactNode {
  const classes = ['ng-badge', TONE_CLASS[tone], className]
    .filter(Boolean)
    .join(' ');

  return (
    <span className={classes}>
      {dot && <span className="ng-badge__dot" aria-hidden="true" />}
      {children}
    </span>
  );
}
