import React, {type ReactNode} from 'react';
import styles from './styles.module.css';

export interface IconListItem {
  /** Emoji or short glyph rendered in the tinted circle. */
  icon: ReactNode;
  /** Row copy — keep to one or two lines. */
  text: ReactNode;
}

interface IconListProps {
  items: IconListItem[];
  /** Columns at desktop width. Default 2. */
  columns?: 1 | 2;
}

/**
 * Icon + text list — a tinted glyph circle beside a line of copy. Used for
 * "why" / benefit sections where each item is a single statement rather than
 * a full title + description card (use FeatureGrid for those).
 */
export default function IconList({
  items,
  columns = 2,
}: IconListProps): ReactNode {
  return (
    <div
      className={styles.list}
      style={{'--cols': columns} as React.CSSProperties}>
      {items.map((item, i) => (
        <div key={i} className={styles.item}>
          <span className={`ng-icon-circle ${styles.icon}`} aria-hidden="true">
            {item.icon}
          </span>
          <span className={styles.text}>{item.text}</span>
        </div>
      ))}
    </div>
  );
}
