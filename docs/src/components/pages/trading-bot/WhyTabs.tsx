import React, {useState, type ReactNode} from 'react';
import GlassCard from '@site/src/components/GlassCard';
import styles from './WhyTabs.module.css';

/*
 * Page-local tab switcher for the /trading-bot page — "Why using OctoBot?"
 * Four tabs, each rendering a glass card with a heading and a bullet list.
 * Bespoke useState picker, kept colocated with the trading-bot page.
 */

interface WhyTab {
  id: string;
  label: string;
  heading: string;
  bullets: string[];
}

const TABS: WhyTab[] = [
  {
    id: 'invest',
    label: 'Invest',
    heading: 'Invest in your crypto with your strategies',
    bullets: [
      'Technical analysis & AI',
      'Smart Dollar Cost Averaging & Grid trading',
      'TradingView automation',
    ],
  },
  {
    id: 'create',
    label: 'Create',
    heading: 'Create, optimize and trade with your own strategies',
    bullets: [
      'Trade SPOT and Futures markets',
      'Use your unique strategy',
      'Optimize it with backtesting',
    ],
  },
  {
    id: 'autopilot',
    label: 'Autopilot',
    heading: 'Profit from well-known strategies',
    bullets: [
      'Run ready-to-use trading strategies to diversify your investments',
      'Totally free: enjoy all trading strategies at no cost',
    ],
  },
  {
    id: 'follow',
    label: 'Follow',
    heading: 'Follow your OctoBots from anywhere',
    bullets: [
      'From any web browser, on mobile or desktop',
      'From your phone with the OctoBot App or Telegram',
    ],
  },
];

export default function WhyTabs(): ReactNode {
  const [active, setActive] = useState(0);
  const tab = TABS[active];

  return (
    <div className={styles.wrap}>
      <div className={styles.tabs} role="tablist" aria-label="Why using OctoBot">
        {TABS.map((t, i) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={i === active}
            className={i === active ? styles.tabOn : styles.tab}
            onClick={() => setActive(i)}>
            {t.label}
          </button>
        ))}
      </div>

      <GlassCard variant="strong" className={styles.panel}>
        <h3 className={styles.heading}>{tab.heading}</h3>
        <ul className={styles.bullets}>
          {tab.bullets.map((bullet) => (
            <li key={bullet} className={styles.bullet}>
              <span className={styles.dot} aria-hidden="true" />
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      </GlassCard>
    </div>
  );
}
