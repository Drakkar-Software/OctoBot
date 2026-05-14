import React, {useState, type ReactNode} from 'react';
import {translate} from '@docusaurus/Translate';
import styles from './AdminRows.module.css';

/*
 * Page-local "you own the desk" disclosure list — icon rows that expand on
 * click to reveal a detail paragraph. Bespoke layout (icon + name + sub +
 * chevron), kept with the /market-making page.
 */

const ROWS = [
  {
    icon: '⚙',
    name: translate({
      id: 'pages.marketMaking.adminRows.configure.name',
      message: 'You configure everything',
      description: 'Market making admin row name',
    }),
    sub: translate({
      id: 'pages.marketMaking.adminRows.configure.sub',
      message: 'Spreads · inventory · skew · venues',
      description: 'Market making admin row sub',
    }),
    body: translate({
      id: 'pages.marketMaking.adminRows.configure.body',
      message:
        'Every parameter is yours to set, change, and audit — in the dashboard or by API. We can review your config; we can’t change it.',
      description: 'Market making admin row body',
    }),
  },
  {
    icon: '⌥',
    name: translate({
      id: 'pages.marketMaking.adminRows.keys.name',
      message: 'You hold the keys',
      description: 'Market making admin row name',
    }),
    sub: translate({
      id: 'pages.marketMaking.adminRows.keys.sub',
      message: 'Your venues. Your sub-accounts. Revoke any time.',
      description: 'Market making admin row sub',
    }),
    body: translate({
      id: 'pages.marketMaking.adminRows.keys.body',
      message:
        'The engine quotes from your sub-account on your exchange. We never custody, never withdraw, never move funds.',
      description: 'Market making admin row body',
    }),
  },
  {
    icon: '∅',
    name: translate({
      id: 'pages.marketMaking.adminRows.noToken.name',
      message: 'No token. No spread cut.',
      description: 'Market making admin row name',
    }),
    sub: translate({
      id: 'pages.marketMaking.adminRows.noToken.sub',
      message: 'Zero allocation, zero loan, zero profit-share.',
      description: 'Market making admin row sub',
    }),
    body: translate({
      id: 'pages.marketMaking.adminRows.noToken.body',
      message:
        'Your liquidity, your PnL, your inventory — fully yours. No clauses about earned rebates, no claims on directional gains.',
      description: 'Market making admin row body',
    }),
  },
  {
    icon: '€',
    name: translate({
      id: 'pages.marketMaking.adminRows.flatFee.name',
      message: 'Flat fee. That’s it.',
      description: 'Market making admin row name',
    }),
    sub: translate({
      id: 'pages.marketMaking.adminRows.flatFee.sub',
      message: 'One retainer. Cancel monthly. No clawback.',
      description: 'Market making admin row sub',
    }),
    body: translate({
      id: 'pages.marketMaking.adminRows.flatFee.body',
      message:
        'One monthly fee for the engine, the infra, and a human on Signal when you need one. No success fees, no hidden rebate splits.',
      description: 'Market making admin row body',
    }),
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
