import React, {type ReactNode} from 'react';
import styles from './styles.module.css';

interface LogoRibbonProps {
  /** Cell contents — exchange names, logos, or any short node. */
  items: ReactNode[];
  /** Minimum cell width in px before wrapping. Default 140. */
  minCellWidth?: number;
}

/**
 * Flex-wrap ribbon of equal-weight cells — exchange names, integration logos,
 * trust marks. Cells share hairline dividers and lift to frost on hover.
 */
export default function LogoRibbon({
  items,
  minCellWidth = 140,
}: LogoRibbonProps): ReactNode {
  return (
    <div className={styles.ribbon}>
      {items.map((item, i) => (
        <div
          key={i}
          className={styles.cell}
          style={{minWidth: `${minCellWidth}px`}}>
          {item}
        </div>
      ))}
    </div>
  );
}
