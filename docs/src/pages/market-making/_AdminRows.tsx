import React, {useState, type ReactNode} from 'react';
import styles from './_AdminRows.module.css';

/*
 * Page-local "you own the desk" disclosure list — icon rows that expand on
 * click to reveal a detail paragraph. Bespoke layout (icon + name + sub +
 * chevron), kept with the /market-making page.
 */

const ROWS = [
  {
    icon: '⚙',
    name: 'You configure everything',
    sub: 'Spreads · inventory · skew · venues',
    body: 'Every parameter is yours to set, change, and audit — in the dashboard or by API. We can review your config; we can’t change it.',
  },
  {
    icon: '⌥',
    name: 'You hold the keys',
    sub: 'Your venues. Your sub-accounts. Revoke any time.',
    body: 'The engine quotes from your sub-account on your exchange. We never custody, never withdraw, never move funds.',
  },
  {
    icon: '∅',
    name: 'No token. No spread cut.',
    sub: 'Zero allocation, zero loan, zero profit-share.',
    body: 'Your liquidity, your PnL, your inventory — fully yours. No clauses about earned rebates, no claims on directional gains.',
  },
  {
    icon: '€',
    name: 'Flat fee. That’s it.',
    sub: 'One retainer. Cancel monthly. No clawback.',
    body: 'One monthly fee for the engine, the infra, and a human on Signal when you need one. No success fees, no hidden rebate splits.',
  },
];

export default function AdminRows(): ReactNode {
  const [open, setOpen] = useState<number[]>([]);

  const toggle = (index: number) =>
    setOpen((current) =>
      current.includes(index)
        ? current.filter((i) => i !== index)
        : [...current, index],
    );

  return (
    <div className={styles.rows}>
      {ROWS.map((row, index) => {
        const isOpen = open.includes(index);
        return (
          <button
            key={row.name}
            type="button"
            aria-expanded={isOpen}
            onClick={() => toggle(index)}
            className={`ng-card-strong ${styles.row} ${isOpen ? styles.open : ''}`}>
            <span className={styles.icon} aria-hidden="true">
              {row.icon}
            </span>
            <span className={styles.text}>
              <span className={styles.name}>{row.name}</span>
              <span className={styles.sub}>{row.sub}</span>
            </span>
            <span className={styles.chev} aria-hidden="true">
              ›
            </span>
            {isOpen && <span className={styles.body}>{row.body}</span>}
          </button>
        );
      })}
    </div>
  );
}
